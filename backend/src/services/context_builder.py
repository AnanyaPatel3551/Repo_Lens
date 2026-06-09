from typing import List, Dict, Any
from src.models.report import Report


class ContextBuilder:
    """
    Service to assemble codebase context facts and retrieved code chunks for LLM query execution.
    """

    @staticmethod
    def build(report: Report, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Builds a structured context string from the repository metadata, architecture report,
        important files, entry points, and semantic code chunks.
        """
        # 1. Repository Core Facts
        metrics = report.metrics or {}
        total_files = metrics.get("total_files", 0)
        total_lines = metrics.get("total_lines", 0)

        languages = report.languages or {}
        lang_list = [f"{lang} ({details.get('percentage', 0)}%)" for lang, details in languages.items()]
        langs_str = ", ".join(lang_list)

        frameworks = report.frameworks or {}
        fw_list = [f"{fw} ({int(score * 100)}%)" for fw, score in frameworks.items()]
        fws_str = ", ".join(fw_list)

        summary_data = report.summary or {}
        purpose = summary_data.get("project_purpose", "Not specified.")
        repo_size = summary_data.get("repo_size", f"{total_files} files, {total_lines} lines of code.")

        entry_points = report.entry_points or []
        entry_lines = [f"- `{ep.get('path')}`: {ep.get('description')} ({ep.get('language')})" for ep in entry_points]
        entry_str = "\n".join(entry_lines) if entry_lines else "- No explicit entry points matched."

        repo_facts = (
            f"Project Purpose: {purpose}\n"
            f"Scale: {repo_size}\n"
            f"Primary Tech Stack: {langs_str if langs_str else 'N/A'}\n"
            f"Frameworks Detected: {fws_str if fws_str else 'N/A'}\n"
            f"Application Entry Points:\n{entry_str}\n"
        )

        # 2. Architecture Facts
        arch_data = report.architecture_report or {}
        arch_type = arch_data.get("architecture_type", "Monolith or Uncategorized")
        evidence = arch_data.get("evidence", [])
        evidence_str = "\n".join([f"- {ev}" for ev in evidence]) if evidence else "- No explicit architectural layout identified."

        important_files = report.important_files or []
        files_lines = [f"- `{f.get('path')}` (Priority score {f.get('importance_score')}): {f.get('explanation')}" for f in important_files]
        files_str = "\n".join(files_lines) if files_lines else "- No important files ranked."

        arch_facts = (
            f"Architectural Style: {arch_type}\n"
            f"Architecture Evidence:\n{evidence_str}\n"
            f"Key High-Signal Files:\n{files_str}\n"
        )

        # 3. Retrieved Code Chunks
        chunks_lines = []
        if retrieved_chunks:
            for idx, chunk in enumerate(retrieved_chunks, 1):
                chunks_lines.append(
                    f"--- CODE CHUNK {idx} ---\n"
                    f"File: {chunk.get('file_path')}\n"
                    f"Lines: {chunk.get('start_line')}-{chunk.get('end_line')}\n"
                    f"Code Content:\n```\n{chunk.get('chunk_content')}\n```\n"
                )
            chunks_str = "\n".join(chunks_lines)
        else:
            chunks_str = "No specific code chunks retrieved for this search query."

        # Final context package
        return (
            "==================================================\n"
            "CODELINE FACTS & METADATA\n"
            "==================================================\n"
            f"{repo_facts}\n"
            "==================================================\n"
            "ARCHITECTURE & FOLDER STRUCTURE ANALYSIS\n"
            "==================================================\n"
            f"{arch_facts}\n"
            "==================================================\n"
            "RETRIEVED CODE CHUNKS (SEMANTICALLY SIMILAR)\n"
            "==================================================\n"
            f"{chunks_str}\n"
        )
