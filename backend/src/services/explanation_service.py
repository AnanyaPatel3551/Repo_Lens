import re
import json
from typing import Dict, Any, List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.chunk import KnowledgeChunk
from src.services.llm_provider import BaseLLMProvider

class ExplanationService:
    """
    Service to generate dynamic, senior-developer explanations for files and folders.
    """

    @staticmethod
    async def _reconstruct_file_content(db: AsyncSession, repository_id: str, file_path: str) -> str:
        """
        Reconstructs the file content from its indexed database chunks.
        """
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.repository_id == repository_id, KnowledgeChunk.file_path == file_path)
            .order_by(KnowledgeChunk.start_line.asc())
        )
        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return ""

        # Reconstruct line-by-line using chunk bounds to resolve overlap
        lines_map = {}
        for chunk in chunks:
            chunk_lines = chunk.chunk_content.splitlines()
            for idx, line in enumerate(chunk_lines):
                line_no = chunk.start_line + idx
                lines_map[line_no] = line

        sorted_lines = [lines_map[l] for l in sorted(lines_map.keys())]
        return "\n".join(sorted_lines)

    @staticmethod
    async def explain_file(
        db: AsyncSession, 
        repository_id: str, 
        file_path: str, 
        provider: BaseLLMProvider
    ) -> Dict[str, Any]:
        """
        Retrieves file content and calls Gemini LLM to generate structured explanations.
        """
        content = await ExplanationService._reconstruct_file_content(db, repository_id, file_path)
        
        # Truncate content to avoid context limit if it's very large
        max_lines = 300
        lines = content.splitlines()
        truncated_content = "\n".join(lines[:max_lines])
        if len(lines) > max_lines:
            truncated_content += f"\n\n... [Truncated {len(lines) - max_lines} lines] ..."

        system_instruction = (
            "You are a Staff Software Engineer onboarding a teammate to a codebase.\n"
            "Your job is to explain the purpose, structure, and value of a file in plain English.\n"
            "You must return ONLY a raw JSON object matching this schema:\n"
            "{\n"
            "  \"purpose\": \"Why this file exists and its role in the system.\",\n"
            "  \"responsibilities\": [\"List of key responsibilities of this file.\"],\n"
            "  \"key_functions\": [\"List of important functions or classes and what they do.\"],\n"
            "  \"dependencies\": [\"List of main internal or external dependencies.\"],\n"
            "  \"related_paths\": [\"List of files or paths closely coupled or related to this file.\"],\n"
            "  \"developer_value\": \"Actionable advice on what a developer must know before modifying this file.\"\n"
            "}\n"
            "Do not include any explanation or markdown formatting outside of the JSON block."
        )

        prompt = (
            f"Explain the following file:\n"
            f"File Path: {file_path}\n"
            f"Content:\n```\n{truncated_content}\n```"
        )

        fallback = {
            "purpose": f"Source code file at {file_path} contributing implementation logic.",
            "responsibilities": ["Implements package modules.", "Executes workflow routines."],
            "key_functions": ["Code exports defined within file."],
            "dependencies": ["Standard module library imports."],
            "related_paths": [],
            "developer_value": "Analyze entrypoints and local imports before modifying."
        }

        if not content:
            return fallback

        try:
            raw_response = await provider.generate_response(prompt, system_instruction=system_instruction)
            return ExplanationService._extract_and_parse_json(raw_response, fallback)
        except Exception as e:
            print(f"Failed to generate file explanation for {file_path}: {e}")
            return fallback

    @staticmethod
    async def explain_folder(
        db: AsyncSession, 
        repository_id: str, 
        folder_path: str, 
        provider: BaseLLMProvider
    ) -> Dict[str, Any]:
        """
        Finds all files in folder and calls Gemini LLM to explain the folder structure.
        """
        # Query all unique file paths in repository
        stmt = (
            select(KnowledgeChunk.file_path)
            .where(KnowledgeChunk.repository_id == repository_id)
            .distinct()
        )
        result = await db.execute(stmt)
        all_paths = result.scalars().all()

        # Filter paths under folder_path
        # Normalize paths to use forward slashes
        norm_folder = folder_path.replace("\\", "/").strip("/")
        folder_files = []
        for path in all_paths:
            norm_path = path.replace("\\", "/").strip("/")
            if norm_path.startswith(norm_folder + "/") or norm_path == norm_folder:
                folder_files.append(path)

        system_instruction = (
            "You are a Staff Software Engineer onboarding a teammate to a codebase.\n"
            "Your job is to explain the purpose and layout of a directory/folder in plain English.\n"
            "You must return ONLY a raw JSON object matching this schema:\n"
            "{\n"
            "  \"purpose\": \"Why this folder exists and its high-level role.\",\n"
            "  \"responsibilities\": [\"Key architectural responsibilities of files under this folder.\"],\n"
            "  \"key_functions\": [\"Main files/components inside and their roles.\"],\n"
            "  \"dependencies\": [\"List of main folders or libraries this directory relies on.\"],\n"
            "  \"related_paths\": [\"List of related directories or paths.\"],\n"
            "  \"developer_value\": \"Actionable context on how code here interacts with the rest of the application.\"\n"
            "}\n"
            "Do not include any explanation or markdown formatting outside of the JSON block."
        )

        prompt = (
            f"Explain the following directory/folder:\n"
            f"Folder Path: {folder_path}\n"
            f"Files in this Folder (subset):\n" + "\n".join([f"- {f}" for f in folder_files[:20]])
        )

        fallback = {
            "purpose": f"Directory module grouping code files under {folder_path}.",
            "responsibilities": ["Organizes local source assets."],
            "key_functions": [os.path.basename(f) for f in folder_files[:10]],
            "dependencies": [],
            "related_paths": [],
            "developer_value": "Inspect subdirectories and import paths to locate specific methods."
        }

        if not folder_files:
            return fallback

        try:
            raw_response = await provider.generate_response(prompt, system_instruction=system_instruction)
            return ExplanationService._extract_and_parse_json(raw_response, fallback)
        except Exception as e:
            print(f"Failed to generate folder explanation for {folder_path}: {e}")
            return fallback

    @staticmethod
    def _extract_and_parse_json(text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to extract JSON object from LLM response blocks robustly.
        """
        try:
            return json.loads(text.strip())
        except Exception:
            pass
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1:
            try:
                return json.loads(text[first_brace:last_brace+1])
            except Exception:
                pass
        return fallback
