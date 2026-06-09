import re
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.report import Report
from src.services.llm_provider import get_provider
from src.services.retrieval_service import RetrievalService
from src.services.context_builder import ContextBuilder


class AskCache:
    """
    In-memory retrieval cache for repository query answers.
    """
    _cache: Dict[tuple, Dict[str, Any]] = {}

    @classmethod
    def get(cls, repository_id: str, question: str) -> Optional[Dict[str, Any]]:
        key = (repository_id, question.strip().lower())
        return cls._cache.get(key)

    @classmethod
    def set(cls, repository_id: str, question: str, response: Dict[str, Any]) -> None:
        key = (repository_id, question.strip().lower())
        cls._cache[key] = response


class AskService:
    """
    Service coordinating Repository Grounded Q&A pipeline.
    """
    # Regex to match [File: file_path (start_line-end_line)]
    CITATION_REGEX = re.compile(r'\[File:\s*([^\s()\]]+)\s*\((\d+)-(\d+)\)\]')

    @staticmethod
    async def ask(db: AsyncSession, report: Report, question: str) -> Dict[str, Any]:
        """
        Coordinates the Retriever, Context Builder, and LLM to answer a question.
        Returns a grounded answer with citations.
        """
        # 1. Check cache first
        cached = AskCache.get(report.id, question)
        if cached:
            return cached

        # 2. Retrieve top matching code chunks
        provider = get_provider()
        retrieved_chunks = await RetrievalService.retrieve(
            db=db,
            repository_id=report.id,
            question=question,
            provider=provider,
            limit=5
        )

        # 3. Assemble full context
        context = ContextBuilder.build(report, retrieved_chunks)

        # 4. Define Senior-to-Junior System Onboarding Instruction
        system_instruction = (
            "You are a friendly, welcoming Staff Software Engineer onboarding a new junior developer.\n"
            "Your tone should be supportive, clean, plain English, and minimize advanced jargon.\n"
            "Your task is to explain how a mechanism works, why things exist, and answer their question based ONLY on facts in the provided context.\n\n"
            
            "CRITICAL RULES FOR HALLUCINATION PREVENTION:\n"
            "- You must only answer using the provided facts, architecture overview, entry points, and code chunks.\n"
            "- Do not invent behaviors, routes, database tables, or folder structures. If they are not in the context, do not assume they exist.\n"
            "- If the context does not contain enough information to answer the question, you must respond EXACTLY with:\n"
            "  'Information not found in analyzed repository.'\n"
            "- Do not include any speculation, guesses, or external information.\n\n"
            
            "CRITICAL RULES FOR CITATIONS:\n"
            "- You must cite the source files and line ranges for any details you explain.\n"
            "- Use the format tag: [File: file_path (start_line-end_line)] at the end of the sentence or block detailing that code.\n"
            "- Example: 'Database initialization is done in session.py [File: src/database/session.py (8-21)].'\n"
            "- Every single descriptive response about the codebase MUST contain at least one citation. Never return an uncited response."
        )

        prompt = (
            f"Developer Question: {question}\n\n"
            f"Codebase Context:\n{context}\n\n"
            f"Provide your answer following the strict onboarding guidelines."
        )

        # 5. Execute LLM call
        raw_answer = await provider.generate_response(prompt, system_instruction=system_instruction)

        # 6. Check for the missing information fallback
        clean_fallback = "Information not found in analyzed repository."
        if clean_fallback.lower() in raw_answer.lower():
            response = {
                "answer": clean_fallback,
                "citations": [],
                "confidence_score": "Low",
                "confidence_explanation": "The requested information could not be found in the indexed repository database chunks."
            }
            AskCache.set(report.id, question, response)
            return response

        # 7. Parse citations out of the answer
        citations = []
        seen_citations = set()
        
        for match in AskService.CITATION_REGEX.finditer(raw_answer):
            file_path, start, end = match.groups()
            citation_key = (file_path, int(start), int(end))
            
            if citation_key not in seen_citations:
                seen_citations.add(citation_key)
                citations.append({
                    "file_path": file_path,
                    "start_line": int(start),
                    "end_line": int(end)
                })

        # Format citation tags for clean display: [File: file_path (10-20)] -> (file_path:10-20)
        formatted_answer = AskService.CITATION_REGEX.sub(r'(\1:\2-\3)', raw_answer)

        # Handle edge case: if LLM gave an answer but failed to add citations,
        # and it's not the fallback, we enforce safety by using fallback or appending retrieved references.
        if not citations:
            # If the LLM didn't cite but retrieved chunks were returned, we link the top chunks as safety references
            if retrieved_chunks:
                for chunk in retrieved_chunks[:2]:
                    citations.append({
                        "file_path": chunk["file_path"],
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"]
                    })
                formatted_answer += "\n\nSources:\n" + "\n".join([f"- {c['file_path']} ({c['start_line']}-{c['end_line']})" for c in citations])
            else:
                formatted_answer = clean_fallback

        # Determine confidence based on presence of citations
        confidence_score = "High" if citations else "Low"
        confidence_explanation = "Answer is fully supported by direct code citations." if citations else "No direct matching code citations found in database."

        response = {
            "answer": formatted_answer,
            "citations": citations,
            "confidence_score": confidence_score,
            "confidence_explanation": confidence_explanation
        }

        # Cache the response
        AskCache.set(report.id, question, response)
        return response
