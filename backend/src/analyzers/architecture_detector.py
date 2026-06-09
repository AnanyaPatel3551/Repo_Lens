import os
from typing import List, Dict, Any

class ArchitectureDetector:
    @staticmethod
    def analyze(file_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determines the architectural pattern of a repository using heuristics.
        Checks for Clean Architecture, MVC, Layered Architecture, Monolith, or Microservices.
        """
        # Collect all directory names (segments) in the codebase
        folder_segments = set()
        for record in file_records:
            parts = record["path"].split("/")
            # Exclude the file name itself, keep parent folders
            for part in parts[:-1]:
                if part:
                    folder_segments.add(part.lower())

        # Collect manifest files to identify microservice/monorepo patterns
        manifest_files = [
            record["path"] for record in file_records
            if os.path.basename(record["path"]) in {"package.json", "go.mod", "Cargo.toml", "pom.xml", "requirements.txt", "pyproject.toml"}
        ]
        unique_manifest_folders = {os.path.dirname(path) for path in manifest_files}

        # Rules definitions and candidate scoring
        candidates = []

        # 1. Clean Architecture Heuristics
        clean_keywords = {"domain", "entities", "usecases", "use_cases", "infrastructure", "presenters", "adapters", "interactors"}
        matched_clean = folder_segments.intersection(clean_keywords)
        if matched_clean:
            # Scale score: 2 matches = 0.5, 3+ matches = 0.85+
            conf = min(0.3 + (len(matched_clean) * 0.20), 0.95)
            evidence = [f"Found folders mapping Clean Architecture layers: {', '.join(sorted(list(matched_clean)))}"]
            candidates.append({
                "type": "Clean Architecture",
                "confidence": conf,
                "evidence": evidence
            })

        # 2. MVC Heuristics
        mvc_keywords = {"controllers", "models", "views", "templates"}
        matched_mvc = folder_segments.intersection(mvc_keywords)
        # Avoid MVC collision if 'models' is present alongside layered repositories
        if matched_mvc and not folder_segments.intersection({"repositories", "services"}):
            conf = min(0.3 + (len(matched_mvc) * 0.20), 0.90)
            evidence = [f"Found MVC folder keywords: {', '.join(sorted(list(matched_mvc)))}"]
            candidates.append({
                "type": "MVC",
                "confidence": conf,
                "evidence": evidence
            })

        # 3. Layered Architecture Heuristics
        layered_keywords = {"services", "repositories", "database", "dao", "dto", "db", "api", "routes", "handlers"}
        matched_layered = folder_segments.intersection(layered_keywords)
        if matched_layered:
            conf = min(0.3 + (len(matched_layered) * 0.15), 0.90)
            evidence = [f"Found service/repository layer folders: {', '.join(sorted(list(matched_layered)))}"]
            candidates.append({
                "type": "Layered Architecture",
                "confidence": conf,
                "evidence": evidence
            })

        # 4. Microservice-like / Monorepo Heuristics
        if len(unique_manifest_folders) >= 3:
            conf = min(0.4 + (len(unique_manifest_folders) * 0.10), 0.95)
            evidence = [f"Detected {len(unique_manifest_folders)} separate project workspaces containing dependency manifests."]
            candidates.append({
                "type": "Microservice-like",
                "confidence": conf,
                "evidence": evidence
            })

        # 5. Fallback Monolith Heuristic
        # If there's only one root workspace and we did not find strong MVC, layered, or clean patterns
        has_structural_pattern = any(c["type"] in {"Clean Architecture", "MVC", "Layered Architecture", "Microservice-like"} and c["confidence"] >= 0.50 for c in candidates)
        if len(unique_manifest_folders) <= 1 and not has_structural_pattern:
            monolith_evidence = ["Code is centered around a single project manifest workspace."]
            if len(file_records) > 0:
                monolith_evidence.append(f"Contains {len(file_records)} source/asset files under a unified codebase.")
            candidates.append({
                "type": "Monolith",
                "confidence": 0.80,
                "evidence": monolith_evidence
            })

        # Select candidate with highest confidence
        if not candidates:
            return {
                "architecture_type": "Unknown",
                "confidence_score": 0.0,
                "evidence": ["No standard folder patterns detected in the repository structure."]
            }

        # Sort candidates by confidence descending
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        best_candidate = candidates[0]

        return {
            "architecture_type": best_candidate["type"],
            "confidence_score": round(best_candidate["confidence"], 2),
            "evidence": best_candidate["evidence"]
        }
