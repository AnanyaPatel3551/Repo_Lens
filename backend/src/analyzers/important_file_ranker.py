import os
from typing import List, Dict, Any

class ImportantFileRanker:
    @staticmethod
    def rank(
        file_records: List[Dict[str, Any]], 
        entry_points: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Ranks files based on their structural importance in the codebase.
        Returns the top 10 files with paths, importance scores, and onboarding reasons.
        """
        ranked_files = []
        entry_paths = {ep["path"] for ep in entry_points}

        # Onboarding folder scoring heuristics (Improvement 2)
        penalize_dirs = {"examples", "sample", "samples", "demo", "demos", "fixtures", "fixture", "test", "tests", "mock", "mocks", "docs/examples"}
        boost_dirs = {"src", "core", "app", "packages", "services", "server", "framework", "runtime"}

        for record in file_records:
            path = record["path"]
            filename = os.path.basename(path)
            ext = record["extension"]
            
            score = 0
            reason = "Standard source/asset file."
            is_critical = False

            # 1. README / Documentation (Highest Signal for initial read)
            if filename.lower() == "readme.md":
                score = 100
                reason = "Primary project documentation. Provides architecture details, installation steps, and usage guides. Read first!"
            
            # 2. Entry points
            elif path in entry_paths or filename in {"main.py", "app.py", "index.js", "server.js", "main.ts", "main.go", "main.rs"}:
                score = 95
                reason = "Application bootstrap file. Responsible for setting up the server, runtime context, and initializing dependencies."
                is_critical = True

            # 3. Dependency Manifests
            elif filename in {"package.json", "go.mod", "Cargo.toml", "pom.xml", "requirements.txt", "pyproject.toml"}:
                score = 90
                reason = "Dependency manifest file. Lists external libraries, project versioning, and build/run command scripts."
                is_critical = True

            # 4. Database Schemas / Models
            elif filename in {"schema.prisma", "schema.sql"} or "models/" in path or filename == "models.py" or "db/" in path:
                score = 85
                reason = "Data model or database schema file. Defines the application tables, entity structures, and relationships."

            # 5. Core Configuration
            elif filename in {"docker-compose.yml", "tsconfig.json", "vite.config.ts", "next.config.ts", "next.config.js", "webpack.config.js", "settings.py"}:
                score = 80
                reason = "Configuration file. Specifies compiler flags, environment setups, or build compiler parameters."
                is_critical = True

            # 6. Route definitions
            elif "routes" in path.lower() or "controllers/" in path or "api/" in path or filename == "routes.py":
                score = 75
                reason = "Routing layer. Maps HTTP request endpoints (endpoints) to business logic controllers."
                is_critical = True

            # 7. Core Services / Domain Logic
            elif "services/" in path or "repositories/" in path or "usecases/" in path:
                score = 70
                reason = "Core service/use-case layer. Encapsulates business domain logic, workflows, or CRUD actions."
            
            # 8. Standard Code File weighting based on size
            else:
                if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cs"}:
                    # Add tiny weight for larger code files to differentiate them, max 45 points
                    size_bonus = min(record["line_count"] // 50, 15)
                    score = 30 + size_bonus
                    reason = f"Source code file containing application implementation logic (~{record['line_count']} lines)."
                else:
                    score = 15
                    reason = "Static asset or minor source file."

            # Apply Critical Boost
            if is_critical:
                score = min(99, score + 30)

            # Apply Path Penalties and Boosts (Improvement 2)
            path_parts = set(p.lower() for p in path.split("/"))
            
            has_penalty = False
            for part in path_parts:
                if part in penalize_dirs:
                    has_penalty = True
                    break
            
            if has_penalty:
                # Deduct 60 points and cap the score at 10
                score = max(0, min(10, score - 60))
                reason = f"[Non-production file] {reason}"
            else:
                has_boost = False
                for part in path_parts:
                    if part in boost_dirs:
                        has_boost = True
                        break
                if has_boost:
                    score = min(99, score + 25)
                    reason = f"[Core Module] {reason}"

            ranked_files.append({
                "path": path,
                "importance_score": score,
                "explanation": reason
            })

        # Sort files by importance score descending, and by line count descending as tie breaker
        record_map = {rec["path"]: rec for rec in file_records}
        ranked_files.sort(
            key=lambda x: (x["importance_score"], record_map.get(x["path"], {}).get("line_count", 0)), 
            reverse=True
        )

        return ranked_files[:10]
