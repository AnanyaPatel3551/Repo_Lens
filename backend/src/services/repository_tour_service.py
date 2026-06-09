import re
from typing import Dict, Any

from src.models.report import Report
from src.services.llm_provider import BaseLLMProvider


class RepositoryTourService:
    """
    Service to generate step-by-step repository onboarding tours using LLM synthesis.
    """

    @staticmethod
    async def generate_tour(report: Report, provider: BaseLLMProvider) -> Dict[str, Any]:
        """
        Generates a 60-second step-by-step onboarding tour of the repository
        using the LLM based on entry points, architecture, and important files.
        """
        system_instruction = (
            "You are a friendly senior software engineer onboarding a new developer to a codebase.\n"
            "Your task is to generate a '60 Second Repository Tour'.\n"
            "Explain the codebase structure step-by-step for a beginner.\n"
            "Target: plain English, minimal jargon, explaining WHY things exist.\n"
            "Format the tour EXACTLY as a list of steps in this markdown format:\n\n"
            "Step 1\n"
            "File: [file_path]\n"
            "Reason: [explanation of why this file is important, what it does, and how it fits in]\n\n"
            "Step 2\n"
            "File: [file_path]\n"
            "Reason: [explanation of the next file in request flow/startup]\n"
            "...\n"
            "Do not include any other conversational intro/outro text. Just output the steps."
        )

        entry_points = report.entry_points or []
        entry_str = "\n".join([f"- `{ep.get('path')}`: {ep.get('description')} ({ep.get('language')})" for ep in entry_points])

        important_files = report.important_files or []
        files_str = "\n".join([f"- `{f.get('path')}`: {f.get('explanation')} (Score: {f.get('importance_score')})" for f in important_files])

        arch_data = report.architecture_report or {}
        arch_type = arch_data.get("architecture_type", "Unknown")
        evidence = arch_data.get("evidence", [])
        evidence_str = ", ".join(evidence)

        summary_data = report.summary or {}
        purpose = summary_data.get("project_purpose", "Not specified.")

        prompt = (
            f"Here are the facts about the repository:\n"
            f"Project Purpose: {purpose}\n"
            f"Architecture Paradigm: {arch_type} (Evidence: {evidence_str})\n"
            f"Key Entry Points:\n{entry_str}\n"
            f"Important Files:\n{files_str}\n\n"
            f"Generate the 60 Second Repository Tour following the instructions."
        )

        try:
            tour_text = await provider.generate_response(prompt, system_instruction=system_instruction)
        except Exception as llm_err:
            err_msg = str(llm_err)
            # Rate limit or quota error — generate a heuristic fallback tour from static data
            if "429" in err_msg or "quota" in err_msg.lower() or "rate" in err_msg.lower():
                print(f"Tour LLM rate-limited, falling back to heuristic tour. Error: {err_msg[:120]}")
                fallback_steps = []
                # Add readme first
                readme = next((f for f in important_files if "readme" in f.get("path", "").lower()), None)
                if readme:
                    fallback_steps.append({"step": 1, "file": readme["path"], "reason": "Start here — this file explains what the project is and how to get it running locally."})
                # Add top entry point
                if entry_points:
                    ep = entry_points[0]
                    fallback_steps.append({"step": len(fallback_steps) + 1, "file": ep.get("path", ""), "reason": f"Main application entry point ({ep.get('language', '')}) — follow the boot sequence to understand how everything wires together."})
                # Add remaining important files (up to 6 total)
                for f in important_files:
                    if len(fallback_steps) >= 6:
                        break
                    if any(s["file"] == f.get("path") for s in fallback_steps):
                        continue
                    fallback_steps.append({"step": len(fallback_steps) + 1, "file": f.get("path", ""), "reason": f.get("explanation", "Key file identified by the importance scorer.")})
                return {
                    "tour_steps": fallback_steps,
                    "raw_text": "Tour generated from static heuristics (LLM quota exceeded)."
                }
            raise

        # Parse the tour_text into structured steps for the API/frontend
        steps = []
        parts = re.split(r'Step\s+\d+\s*', tour_text)
        step_idx = 1
        for part in parts:
            part = part.strip()
            if not part:
                continue

            file_match = re.search(r'File:\s*([^\n]+)', part, re.IGNORECASE)
            reason_match = re.search(r'Reason:\s*(.+)', part, re.IGNORECASE | re.DOTALL)

            file_path = file_match.group(1).strip() if file_match else "Unknown file"
            reason = reason_match.group(1).strip() if reason_match else ""

            # Remove any wrapping markdown formatting on file paths (like backticks or brackets)
            file_path = file_path.strip("`[]()")

            steps.append({
                "step": step_idx,
                "file": file_path,
                "reason": reason
            })
            step_idx += 1

        return {
            "tour_steps": steps,
            "raw_text": tour_text
        }

