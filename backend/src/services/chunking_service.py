import ast
import re
from typing import List, Dict, Any

class ChunkingService:
    """
    Service to split codebase files into semantic chunks dynamically based on language rules.
    """

    @staticmethod
    def chunk_file(filepath: str, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Main entrypoint. Inspects the language and runs the appropriate chunker.
        """
        if not content.strip():
            return []

        lang_lower = language.lower()
        if lang_lower == "python" or filepath.endswith(".py"):
            return ChunkingService._chunk_python(filepath, content)
        elif lang_lower in ("typescript", "javascript") or filepath.endswith((".ts", ".tsx", ".js", ".jsx")):
            return ChunkingService._chunk_typescript(filepath, content)
        elif lang_lower == "java" or filepath.endswith(".java"):
            return ChunkingService._chunk_java(filepath, content)
        elif lang_lower == "go" or filepath.endswith(".go"):
            return ChunkingService._chunk_go(filepath, content)
        else:
            return ChunkingService._chunk_fallback(filepath, content, language)

    @staticmethod
    def _chunk_python(filepath: str, content: str) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        total_lines = len(lines)
        chunks = []

        try:
            tree = ast.parse(content)
        except Exception:
            return ChunkingService._chunk_fallback(filepath, content, "Python")

        class_fn_ranges = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno
                end = getattr(node, "end_lineno", total_lines)
                class_fn_ranges.append((start, end))

                chunk_content = "\n".join(lines[start - 1:end])
                chunks.append({
                    "file_path": filepath,
                    "language": "Python",
                    "chunk_type": "function",
                    "chunk_content": chunk_content,
                    "start_line": start,
                    "end_line": end,
                    "metadata": {"name": node.name}
                })
            elif isinstance(node, ast.ClassDef):
                start = node.lineno
                end = getattr(node, "end_lineno", total_lines)
                class_fn_ranges.append((start, end))

                chunk_content = "\n".join(lines[start - 1:end])
                chunks.append({
                    "file_path": filepath,
                    "language": "Python",
                    "chunk_type": "class",
                    "chunk_content": chunk_content,
                    "start_line": start,
                    "end_line": end,
                    "metadata": {"name": node.name}
                })

        return ChunkingService._fill_missing_ranges(filepath, "Python", chunks, lines)

    @staticmethod
    def _chunk_typescript(filepath: str, content: str) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        chunks = []

        class_pattern = re.compile(r'\bclass\s+([A-Za-z0-9_]+)')
        fn_pattern = re.compile(r'\bfunction\s+([A-Za-z0-9_]+)')
        arrow_pattern = re.compile(r'\b(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>')

        i = 0
        while i < len(lines):
            line = lines[i]

            class_match = class_pattern.search(line)
            fn_match = fn_pattern.search(line)
            arrow_match = arrow_pattern.search(line)

            matched_name = None
            chunk_type = None

            if class_match:
                matched_name = class_match.group(1)
                chunk_type = "class"
            elif fn_match:
                matched_name = fn_match.group(1)
                chunk_type = "component" if matched_name[0].isupper() else "function"
            elif arrow_match:
                matched_name = arrow_match.group(1)
                chunk_type = "component" if matched_name[0].isupper() else "function"

            if chunk_type and matched_name:
                end_line_idx = ChunkingService._find_closing_brace(lines, i)
                start_line = i + 1
                end_line = end_line_idx + 1

                chunk_content = "\n".join(lines[i:end_line_idx + 1])
                chunks.append({
                    "file_path": filepath,
                    "language": "TypeScript" if filepath.endswith((".ts", ".tsx")) else "JavaScript",
                    "chunk_type": chunk_type,
                    "chunk_content": chunk_content,
                    "start_line": start_line,
                    "end_line": end_line,
                    "metadata": {"name": matched_name}
                })
                i += 1
                continue

            i += 1

        lang_name = "TypeScript" if filepath.endswith((".ts", ".tsx")) else "JavaScript"
        return ChunkingService._fill_missing_ranges(filepath, lang_name, chunks, lines)

    @staticmethod
    def _chunk_java(filepath: str, content: str) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        chunks = []

        class_pattern = re.compile(r'\b(?:class|interface)\s+([A-Za-z0-9_]+)')
        method_pattern = re.compile(
            r'\b(?:public|protected|private|static|\s)+\s+[\w<>\[\]]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{'
        )

        i = 0
        while i < len(lines):
            line = lines[i]

            class_match = class_pattern.search(line)
            method_match = method_pattern.search(line)

            matched_name = None
            chunk_type = None

            if class_match:
                matched_name = class_match.group(1)
                chunk_type = "class" if "class" in line else "interface"
            elif method_match:
                matched_name = method_match.group(1)
                if matched_name not in ("if", "for", "while", "switch", "catch", "synchronized"):
                    chunk_type = "method"

            if chunk_type and matched_name:
                end_line_idx = ChunkingService._find_closing_brace(lines, i)
                start_line = i + 1
                end_line = end_line_idx + 1

                chunk_content = "\n".join(lines[i:end_line_idx + 1])
                chunks.append({
                    "file_path": filepath,
                    "language": "Java",
                    "chunk_type": chunk_type,
                    "chunk_content": chunk_content,
                    "start_line": start_line,
                    "end_line": end_line,
                    "metadata": {"name": matched_name}
                })
                i += 1
                continue

            i += 1

        return ChunkingService._fill_missing_ranges(filepath, "Java", chunks, lines)

    @staticmethod
    def _chunk_go(filepath: str, content: str) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        chunks = []

        struct_pattern = re.compile(r'\btype\s+([A-Za-z0-9_]+)\s+struct')
        func_pattern = re.compile(r'\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z0-9_]+)\s*\(')
        package_pattern = re.compile(r'\bpackage\s+([A-Za-z0-9_]+)')

        i = 0
        package_name = None
        while i < len(lines):
            line = lines[i]

            package_match = package_pattern.search(line)
            struct_match = struct_pattern.search(line)
            func_match = func_pattern.search(line)

            if package_match:
                package_name = package_match.group(1)

            matched_name = None
            chunk_type = None

            if struct_match:
                matched_name = struct_match.group(1)
                chunk_type = "struct"
            elif func_match:
                matched_name = func_match.group(1)
                chunk_type = "function"

            if chunk_type and matched_name:
                end_line_idx = ChunkingService._find_closing_brace(lines, i)
                start_line = i + 1
                end_line = end_line_idx + 1

                chunk_content = "\n".join(lines[i:end_line_idx + 1])
                chunks.append({
                    "file_path": filepath,
                    "language": "Go",
                    "chunk_type": chunk_type,
                    "chunk_content": chunk_content,
                    "start_line": start_line,
                    "end_line": end_line,
                    "metadata": {"name": matched_name, "package": package_name or ""}
                })
                i += 1
                continue

            i += 1

        return ChunkingService._fill_missing_ranges(filepath, "Go", chunks, lines)

    @staticmethod
    def _chunk_fallback(filepath: str, content: str, language: str) -> List[Dict[str, Any]]:
        lines = content.splitlines()
        total_lines = len(lines)
        chunks = []

        chunk_size = 60
        overlap = 15

        if total_lines <= chunk_size:
            chunks.append({
                "file_path": filepath,
                "language": language,
                "chunk_type": "file",
                "chunk_content": content,
                "start_line": 1,
                "end_line": max(1, total_lines),
                "metadata": {}
            })
            return chunks

        start = 0
        while start < total_lines:
            end = min(start + chunk_size, total_lines)
            chunk_content = "\n".join(lines[start:end])
            chunks.append({
                "file_path": filepath,
                "language": language,
                "chunk_type": "block",
                "chunk_content": chunk_content,
                "start_line": start + 1,
                "end_line": end,
                "metadata": {}
            })
            if end == total_lines:
                break
            start += chunk_size - overlap

        return chunks

    @staticmethod
    def _find_closing_brace(lines: List[str], start_line_idx: int) -> int:
        brace_count = 0
        found_first_brace = False

        in_single_comment = False
        in_multi_comment = False
        in_string = False
        string_char = None

        for i in range(start_line_idx, len(lines)):
            line = lines[i]
            j = 0
            while j < len(line):
                char = line[j]

                # Multi-line comment state
                if in_multi_comment:
                    if j < len(line) - 1 and line[j:j + 2] == "*/":
                        in_multi_comment = False
                        j += 2
                        continue
                    j += 1
                    continue

                # Single-line comment state
                if in_single_comment:
                    break

                # String state
                if in_string:
                    if char == '\\':
                        j += 2  # skip escaped chars
                        continue
                    if char == string_char:
                        in_string = False
                        string_char = None
                    j += 1
                    continue

                # Detect starts of comments or strings
                if j < len(line) - 1 and line[j:j + 2] == "/*":
                    in_multi_comment = True
                    j += 2
                    continue
                if j < len(line) - 1 and line[j:j + 2] == "//":
                    in_single_comment = True
                    break
                if char in ('"', "'", '`'):
                    in_string = True
                    string_char = char
                    j += 1
                    continue

                # Count braces
                if char == '{':
                    brace_count += 1
                    found_first_brace = True
                elif char == '}':
                    brace_count -= 1

                if found_first_brace and brace_count <= 0:
                    return i

                j += 1

            in_single_comment = False  # Reset at end of line

        return len(lines) - 1

    @staticmethod
    def _fill_missing_ranges(
        filepath: str, language: str, chunks: List[Dict[str, Any]], lines: List[str]
    ) -> List[Dict[str, Any]]:
        covered = set()
        for chunk in chunks:
            for l in range(chunk["start_line"], chunk["end_line"] + 1):
                covered.add(l)

        module_lines = []
        module_start = None
        all_chunks = list(chunks)

        for i, line in enumerate(lines, 1):
            if i not in covered:
                if module_start is None:
                    module_start = i
                module_lines.append(line)
            else:
                if module_lines:
                    chunk_content = "\n".join(module_lines).strip()
                    if chunk_content:
                        all_chunks.append({
                            "file_path": filepath,
                            "language": language,
                            "chunk_type": "module",
                            "chunk_content": "\n".join(module_lines),
                            "start_line": module_start,
                            "end_line": i - 1,
                            "metadata": {}
                        })
                    module_lines = []
                    module_start = None

        if module_lines:
            chunk_content = "\n".join(module_lines).strip()
            if chunk_content:
                all_chunks.append({
                    "file_path": filepath,
                    "language": language,
                    "chunk_type": "module",
                    "chunk_content": "\n".join(module_lines),
                    "start_line": module_start,
                    "end_line": len(lines),
                    "metadata": {}
                })

        if not all_chunks:
            all_chunks.append({
                "file_path": filepath,
                "language": language,
                "chunk_type": "module",
                "chunk_content": "\n".join(lines),
                "start_line": 1,
                "end_line": max(1, len(lines)),
                "metadata": {}
            })

        return all_chunks
