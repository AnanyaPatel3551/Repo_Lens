import os
from typing import List, Dict, Any

class FrameworkAnalyzer:
    @staticmethod
    def analyze(
        file_records: List[Dict[str, Any]], 
        dependencies_by_file: Dict[str, List[Dict[str, Any]]],
        root_dir: str
    ) -> Dict[str, float]:
        """
        Detects frameworks (React, Next.js, Vue, Express, FastAPI, Django, Flask, Spring Boot)
        and computes confidence scores (0.0 - 1.0).
        """
        scores = {
            "React": 0.0,
            "Next.js": 0.0,
            "Vue": 0.0,
            "Express": 0.0,
            "FastAPI": 0.0,
            "Django": 0.0,
            "Flask": 0.0,
            "Spring Boot": 0.0
        }

        # Flatten all dependencies for easy lookup
        all_deps = set()
        for deps in dependencies_by_file.values():
            for dep in deps:
                all_deps.add(dep["name"].lower())

        # Collect extension subsets
        extensions = {rec["extension"] for rec in file_records}
        filenames = {os.path.basename(rec["path"]) for rec in file_records}
        relative_paths = {rec["path"] for rec in file_records}

        # 1. REACT DETECTION
        if "react" in all_deps:
            scores["React"] = 1.0
        elif "react-dom" in all_deps:
            scores["React"] = 0.8
        elif any(ext in extensions for ext in [".jsx", ".tsx"]):
            scores["React"] = 0.5

        # 2. NEXT.JS DETECTION
        if "next" in all_deps:
            scores["Next.js"] = 1.0
        elif any(f in filenames for f in ["next.config.js", "next.config.mjs", "next.config.ts"]):
            scores["Next.js"] = 1.0
        elif scores["React"] > 0.0 and any(p.startswith("app/") or p.startswith("pages/") for p in relative_paths):
            scores["Next.js"] = 0.7

        # 3. VUE DETECTION
        if "vue" in all_deps:
            scores["Vue"] = 1.0
        elif ".vue" in extensions:
            scores["Vue"] = 0.9

        # 4. EXPRESS DETECTION
        if "express" in all_deps:
            scores["Express"] = 1.0

        # 5. FASTAPI DETECTION
        if "fastapi" in all_deps:
            scores["FastAPI"] = 1.0
        else:
            # Look for "import FastAPI" or "from fastapi import" in python files
            for record in file_records:
                if record["extension"] in [".py"] and record["line_count"] > 0:
                    try:
                        filepath = os.path.join(root_dir, record["path"])
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if "FastAPI(" in content or "from fastapi" in content:
                                scores["FastAPI"] = 0.9
                                break
                    except Exception:
                        pass

        # 6. Django DETECTION
        if "django" in all_deps:
            scores["Django"] = 1.0
        elif "manage.py" in filenames:
            scores["Django"] = 0.9

        # 7. FLASK DETECTION
        if "flask" in all_deps:
            scores["Flask"] = 1.0
        else:
            # Check for Flask importing
            for record in file_records:
                if record["extension"] in [".py"] and record["line_count"] > 0:
                    try:
                        filepath = os.path.join(root_dir, record["path"])
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if "Flask(__name__)" in content or "import flask" in content:
                                scores["Flask"] = 0.8
                                break
                    except Exception:
                        pass

        # 8. SPRING BOOT DETECTION
        if any("spring-boot" in dep for dep in all_deps):
            scores["Spring Boot"] = 1.0
        else:
            # Scan Java files for @SpringBootApplication
            for record in file_records:
                if record["extension"] in [".java"] and record["line_count"] > 0:
                    try:
                        filepath = os.path.join(root_dir, record["path"])
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if "@SpringBootApplication" in content:
                                scores["Spring Boot"] = 0.9
                                break
                    except Exception:
                        pass

        # Filter out frameworks with 0 score and round to 2 decimals
        detected_frameworks = {
            fw: round(score, 2) 
            for fw, score in scores.items() 
            if score > 0.0
        }
        
        # Sort by confidence descending
        return dict(
            sorted(
                detected_frameworks.items(),
                key=lambda item: item[1],
                reverse=True
            )
        )
