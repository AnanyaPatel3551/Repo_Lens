from typing import Dict, Any

from src.models.report import Report
from src.services.llm_provider import BaseLLMProvider


class ArchitectureWalkthroughService:
    """
    Service to generate codebase request, service, and data flow walkthroughs using LLM synthesis.
    """

    @staticmethod
    async def generate_walkthrough(report: Report, provider: BaseLLMProvider) -> Dict[str, Any]:
        """
        Generates an Architecture Walkthrough for junior onboarding,
        covering request, service, and data flows, plus directory details.
        """
        system_instruction = (
            "You are a friendly senior software engineer onboarding a junior developer to a codebase.\n"
            "Your task is to generate a comprehensive 'Architecture Walkthrough' covering:\n"
            "1. Request Flow (how external HTTP/API requests navigate through the system)\n"
            "2. Service Flow (how business logic and internal services are structured)\n"
            "3. Data Flow (how data is read, modified, and stored in the database)\n"
            "4. Folder Responsibilities (what each main directory does)\n\n"
            "Use clear headings, plain English, and bullet points. Explain WHY things exist."
        )

        entry_points = report.entry_points or []
        entry_str = "\n".join([f"- `{ep.get('path')}`: {ep.get('description')}" for ep in entry_points])

        important_files = report.important_files or []
        files_str = "\n".join([f"- `{f.get('path')}`: {f.get('explanation')}" for f in important_files])

        arch_data = report.architecture_report or {}
        arch_type = arch_data.get("architecture_type", "Unknown")
        evidence = arch_data.get("evidence", [])
        evidence_str = "\n".join([f"- {ev}" for ev in evidence])

        summary_data = report.summary or {}
        purpose = summary_data.get("project_purpose", "Not specified.")
        modules = summary_data.get("important_modules", [])
        modules_str = ", ".join([f"{m}/" for m in modules])

        prompt = (
            f"Here are the facts about the repository:\n"
            f"Project Purpose: {purpose}\n"
            f"Architecture Paradigm: {arch_type}\n"
            f"Architecture Evidence:\n{evidence_str}\n"
            f"Primary Modules:\n{modules_str}\n"
            f"Key Entry Points:\n{entry_str}\n"
            f"Important Files:\n{files_str}\n\n"
            f"Generate the Architecture Walkthrough following the instructions."
        )

        walkthrough_text = await provider.generate_response(prompt, system_instruction=system_instruction)
        
        return {
            "walkthrough": walkthrough_text
        }
