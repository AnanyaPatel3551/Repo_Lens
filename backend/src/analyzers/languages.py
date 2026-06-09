from typing import List, Dict, Any

LANGUAGE_MAP = {
    # Extensions mapped to official language keys
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hh": "C++",
    ".h": "C++",
    ".cs": "C#"
}

class LanguageAnalyzer:
    @staticmethod
    def analyze(file_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates language breakdowns (files, line count, percentage) for scanned files.
        Returns:
            Dict[str, Any]: Mapping of language name to its metrics.
        """
        breakdown = {}
        total_lines_sum = 0
        total_files_sum = 0

        # Initialize counts
        for lang in set(LANGUAGE_MAP.values()):
            breakdown[lang] = {
                "files": 0,
                "lines": 0,
                "percentage": 0.0
            }

        # Count languages
        for record in file_records:
            ext = record["extension"]
            lang = LANGUAGE_MAP.get(ext)
            if lang:
                breakdown[lang]["files"] += 1
                breakdown[lang]["lines"] += record["line_count"]
                total_lines_sum += record["line_count"]
                total_files_sum += 1

        # Calculate percentages based on lines (fallback to files if lines == 0)
        if total_lines_sum > 0:
            for lang in breakdown:
                breakdown[lang]["percentage"] = round(
                    (breakdown[lang]["lines"] / total_lines_sum) * 100, 2
                )
        elif total_files_sum > 0:
            for lang in breakdown:
                breakdown[lang]["percentage"] = round(
                    (breakdown[lang]["files"] / total_files_sum) * 100, 2
                )

        # Remove languages with zero files/lines to return clean output
        filtered_breakdown = {
            lang: metrics for lang, metrics in breakdown.items() 
            if metrics["files"] > 0
        }

        # Sort by line count descending
        sorted_breakdown = dict(
            sorted(
                filtered_breakdown.items(), 
                key=lambda item: item[1]["lines"], 
                reverse=True
            )
        )

        return sorted_breakdown
