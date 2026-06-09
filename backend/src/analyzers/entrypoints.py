import os
import re
from typing import List, Dict, Any

# Standard filename rules
STANDARD_ENTRIES = {
    # Node/JS
    "index.js": ("JavaScript", "Standard Node/JS index file", 0.9),
    "server.js": ("JavaScript", "Standard Express/Node server file", 1.0),
    "main.ts": ("TypeScript", "Standard NestJS/TypeScript application entry point", 0.95),
    "app.js": ("JavaScript", "Standard Node application file", 0.8),
    "app.ts": ("TypeScript", "Standard TypeScript application file", 0.8),
    # Python
    "__main__.py": ("Python", "Standard Python module execution entry point", 1.0),
    "app.py": ("Python", "Standard Flask/FastAPI application file", 0.9),
    "manage.py": ("Python", "Django management commands and execution entry point", 1.0),
    "main.py": ("Python", "Standard Python main entry point", 0.9),
    "wsgi.py": ("Python", "WSGI gateway interface server entry point", 0.85),
    "asgi.py": ("Python", "ASGI async gateway interface server entry point", 0.85),
    # Go
    "main.go": ("Go", "Standard Go command source file", 1.0),
    # Rust
    "main.rs": ("Rust", "Standard Rust binary crate entry point", 1.0),
    "lib.rs": ("Rust", "Standard Rust library crate entry point", 0.9),
}

class EntryPointAnalyzer:
    @staticmethod
    def analyze(file_records: List[Dict[str, Any]], root_dir: str) -> List[Dict[str, Any]]:
        """
        Scans files and detects probable entry points.
        Returns:
            List[Dict[str, Any]]: List of entry points with path, language, description, and confidence.
        """
        entry_points = []

        for record in file_records:
            path = record["path"]
            filename = os.path.basename(path)
            ext = record["extension"]
            
            # 1. Match by standard entry point filenames
            if filename in STANDARD_ENTRIES:
                lang, desc, conf = STANDARD_ENTRIES[filename]
                entry_points.append({
                    "path": path,
                    "language": lang,
                    "description": desc,
                    "confidence": conf
                })
                continue
                
            # 2. Content scan for other languages (Java, Go, C++, etc.)
            if ext in [".java", ".go", ".cpp", ".cc", ".cxx", ".c"] and record["line_count"] > 0:
                try:
                    filepath = os.path.join(root_dir, path)
                    # Read first 100 lines/bytes to avoid reading huge source files
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = [f.readline() for _ in range(150)]
                        content = "".join(lines)
                        
                        # Java: public static void main
                        if ext == ".java":
                            if "public static void main" in content or "static void main(" in content:
                                entry_points.append({
                                    "path": path,
                                    "language": "Java",
                                    "description": "Contains Java application entry method 'public static void main'",
                                    "confidence": 1.0
                                })
                        
                        # Go: package main and func main
                        elif ext == ".go":
                            # If not named main.go, check if it defines package main and func main
                            if "package main" in content and "func main()" in content:
                                entry_points.append({
                                    "path": path,
                                    "language": "Go",
                                    "description": "Defines package main with entry function 'func main()'",
                                    "confidence": 0.95
                                })
                                
                        # C/C++: int main(...)
                        elif ext in [".cpp", ".cc", ".cxx", ".c"]:
                            if re.search(r"\bint\s+main\s*\(", content) or re.search(r"\bvoid\s+main\s*\(", content):
                                entry_points.append({
                                    "path": path,
                                    "language": "C/C++",
                                    "description": "Contains entry function 'main()'",
                                    "confidence": 0.95
                                })
                except Exception:
                    pass

        # Sort entry points by confidence descending
        entry_points.sort(key=lambda x: x["confidence"], reverse=True)
        return entry_points
