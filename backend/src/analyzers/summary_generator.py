import os
import json
import re
from typing import List, Dict, Any

class SummaryGenerator:
    @staticmethod
    async def generate(
        file_records: List[Dict[str, Any]],
        languages: Dict[str, Any],
        frameworks: Dict[str, float],
        entry_points: List[Dict[str, Any]],
        dependencies: Dict[str, Any],
        architecture_report: Dict[str, Any],
        important_files: List[Dict[str, Any]],
        provider: Any = None
    ) -> Dict[str, Any]:
        """
        Generates grounded codebase summaries and developer onboarding guides
        using facts extracted by the scans. Calls LLM if provider is available.
        """
        total_files = len(file_records)
        total_lines = sum(rec["line_count"] for rec in file_records)

        # 1. Size evaluation
        if total_lines > 100000:
            size_descr = f"The codebase consists of {total_files:,} files and {total_lines:,} lines of code, indicating a large repository."
        elif total_lines > 15000:
            size_descr = f"The codebase consists of {total_files:,} files and {total_lines:,} lines of code, indicating a medium-sized repository."
        else:
            size_descr = f"The codebase consists of {total_files:,} files and {total_lines:,} lines of code, indicating a compact repository."

        # 2. Tech list formatting
        tech_list = list(languages.keys())
        framework_list = list(frameworks.keys())

        # 3. Purpose inference based on framework confidences and manifest files
        main_tech = tech_list[0] if tech_list else "Unknown"
        purpose = f"A codebase primarily written in {main_tech}."

        if "Next.js" in frameworks and "FastAPI" in frameworks:
            purpose = "A full-stack application combining a modern Next.js/React frontend with a high-performance, asynchronous FastAPI backend."
        elif "Next.js" in frameworks:
            purpose = "A modern web application built using the Next.js React framework, deploying React App Router paradigms."
        elif "React" in frameworks and "Express" in frameworks:
            purpose = "A full-stack JavaScript application integrating a React frontend client with an Express node.js server."
        elif "FastAPI" in frameworks:
            purpose = "A modern Python API backend built on the FastAPI framework, implementing ASGI routing and Pydantic schemas."
        elif "Django" in frameworks:
            purpose = "A Python web application powered by the Django framework, utilizing ORM and management commands."
        elif "Flask" in frameworks:
            purpose = "A Python web service built on the Flask micro-framework, deploying routes and request controllers."
        elif "Spring Boot" in frameworks:
            purpose = "A Java enterprise application powered by the Spring Boot framework."

        # 4. Folder structure mapping
        unique_dirs = set()
        for record in file_records:
            parts = record["path"].split("/")
            if len(parts) > 1:
                # Include first level and second level directories (e.g. src/, app/, src/api/)
                unique_dirs.add(parts[0])
                if len(parts) > 2:
                    unique_dirs.add(f"{parts[0]}/{parts[1]}")

        # Filter and keep relevant high-signal directories
        target_dirs = {
            "src", "app", "pages", "components", "lib", "services", 
            "repositories", "models", "controllers", "api", "database", 
            "utils", "workers", "tests", "packages", "apps", "domain", 
            "entities", "usecases", "infrastructure"
        }
        important_dirs = sorted([d for d in unique_dirs if d in target_dirs or any(d.startswith(t + "/") for t in target_dirs)])

        # 5. Compile Architecture Overview paragraph
        arch_type = architecture_report["architecture_type"]
        arch_conf = int(architecture_report["confidence_score"] * 100)
        arch_evidence = " ".join(architecture_report["evidence"])
        
        arch_overview = f"The repository is categorized as a {arch_type} (confidence score: {arch_conf}%). Evidence: {arch_evidence}"

        # Try calling LLM provider for repository-specific summary
        llm_summary = None
        try:
            if provider is None:
                from src.services.llm_provider import get_provider
                try:
                    provider = get_provider()
                except Exception:
                    provider = None
            
            if provider:
                system_instruction = (
                    "You are a Principal Software Engineer and Staff Architect who writes clear, jargon-free documentation.\n"
                    "Your job is to analyze the metadata of a repository and generate a structured JSON summary to help onboarding developers understand it in 60 seconds.\n"
                    "You must return ONLY a raw JSON object matching this schema:\n"
                    "{\n"
                    "  \"project_purpose\": \"A plain English definition of what the repository does, why it exists, and where it fits in the architecture.\",\n"
                    "  \"intended_contributors\": \"Who this repository is designed for (e.g. Fullstack developers, API engineers, ML engineers).\",\n"
                    "  \"major_subsystems\": [\"List of key subsystems/folders and what they do in plain English.\"],\n"
                    "  \"unique_concepts\": [\"List of unique patterns or frameworks used in this repo, e.g. App Router, dependency injection.\"],\n"
                    "  \"confidence_score\": \"High|Medium|Low\",\n"
                    "  \"confidence_explanation\": \"Explanation of why this confidence level was chosen based on the file hierarchy and contents.\"\n"
                    "}\n"
                    "Do not include any explanation or markdown formatting outside of the JSON block."
                )
                
                prompt = (
                    f"Analyze this repository metadata and generate the onboarding JSON summary:\n\n"
                    f"Languages: {list(languages.keys())}\n"
                    f"Frameworks: {list(frameworks.items())}\n"
                    f"Entry Points: {[ep['path'] for ep in entry_points]}\n"
                    f"Important Files: {[{'path': f['path'], 'explanation': f['explanation']} for f in important_files[:5]]}\n"
                    f"Architecture Report: {architecture_report}\n"
                    f"Directory Structures: {important_dirs}\n"
                )
                
                raw_response = await provider.generate_response(prompt, system_instruction=system_instruction)
                
                def extract_json(text: str) -> Dict[str, Any]:
                    try:
                        return json.loads(text.strip())
                    except Exception:
                        pass
                    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                    if match:
                        try:
                            return json.loads(match.group(1).strip())
                        except Exception:
                            pass
                    first_brace = text.find('{')
                    last_brace = text.rfind('}')
                    if first_brace != -1 and last_brace != -1:
                        try:
                            return json.loads(text[first_brace:last_brace+1])
                        except Exception:
                            pass
                    raise ValueError("Failed to parse JSON")

                llm_summary = extract_json(raw_response)
        except Exception as e:
            print(f"SummaryGenerator LLM call failed or skipped: {e}. Using heuristics fallback.")

        # Resolve LLM provider name to save in summary metadata
        from src.utils.config import settings
        llm_provider_name = settings.LLM_PROVIDER
        if llm_provider_name == "ollama":
            llm_provider_name = f"ollama ({settings.OLLAMA_MODEL})"
        elif llm_provider_name == "gemini":
            llm_provider_name = "gemini-2.5-flash"
        elif llm_provider_name == "openai":
            llm_provider_name = "gpt-4o-mini"
        else:
            llm_provider_name = settings.LLM_PROVIDER

        # Combine into Repository Summary
        summary = {
            "project_purpose": purpose,
            "main_technologies": tech_list,
            "main_frameworks": [f"{fw} ({int(score * 100)}%)" for fw, score in frameworks.items()],
            "repo_size": size_descr,
            "important_modules": important_dirs,
            "architecture_overview": arch_overview,
            "llm_provider": llm_provider_name
        }

        # Override/Extend with LLM results if available
        if llm_summary:
            # Normalize LLM outputs: ensure list fields are plain strings, not dicts
            def normalize_str_list(raw: Any) -> List[str]:
                """Coerces a list of unknown LLM items to plain strings."""
                if not isinstance(raw, list):
                    return []
                normalized = []
                for item in raw:
                    if isinstance(item, str):
                        normalized.append(item)
                    elif isinstance(item, dict):
                        # Handle {name, description}, {name}, {title}, {text}, {description}
                        if "name" in item and "description" in item:
                            normalized.append(f"{item['name']}: {item['description']}")
                        elif "name" in item:
                            normalized.append(str(item["name"]))
                        elif "title" in item:
                            normalized.append(str(item["title"]))
                        elif "description" in item:
                            normalized.append(str(item["description"]))
                        elif "text" in item:
                            normalized.append(str(item["text"]))
                        else:
                            normalized.append(str(item))
                    else:
                        normalized.append(str(item))
                return normalized

            summary.update({
                "project_purpose": llm_summary.get("project_purpose", purpose),
                "intended_contributors": llm_summary.get("intended_contributors", "Developers looking to understand the codebase structure."),
                "major_subsystems": normalize_str_list(llm_summary.get("major_subsystems", [])),
                "unique_concepts": normalize_str_list(llm_summary.get("unique_concepts", [])),
                "confidence_score": llm_summary.get("confidence_score", "High"),
                "confidence_explanation": llm_summary.get("confidence_explanation", "Inferred using static file and dependency analysis heuristics.")
            })
        else:
            summary.update({
                "intended_contributors": "Developers looking to understand the codebase structure.",
                "major_subsystems": [f"{d}: Module containing code structures." for d in important_dirs[:5]],
                "unique_concepts": ["Layered logic separation" if "Layered" in arch_overview else "Standard application structure"],
                "confidence_score": "Medium",
                "confidence_explanation": "Inferred using static file and dependency analysis heuristics."
            })

        # -----------------------------
        # ONBOARDING GUIDE GENERATION
        # -----------------------------
        
        # Where to start
        main_entry = entry_points[0]["path"] if entry_points else "No entry points detected"
        readme_file = next((f["path"] for f in important_files if "readme" in f["path"].lower()), None)
        
        start_desc = f"Begin by reading the project documentation "
        if readme_file:
            start_desc += f"([README.md]({readme_file})), which provides high-level setup steps. "
        else:
            start_desc += "in the README file in the root directory. "
            
        if entry_points:
            start_desc += f"Next, inspect the main application entry point at [{main_entry}]({main_entry}) to understand how the application boots up."
        else:
            start_desc += "Locate the primary source files to explore the application lifecycle."

        # Folders breakdown
        folders_breakdown = []
        for folder in important_dirs:
            desc = "Source module containing application implementation."
            if folder == "app" or folder == "pages":
                desc = "Routing and pages directory containing the frontend screen layouts."
            elif folder == "components":
                desc = "Sleek reusable user interface components."
            elif folder == "src/api" or folder == "api":
                desc = "FastAPI endpoints mapping HTTP request payloads to handlers."
            elif folder == "src/services" or folder == "services":
                desc = "Core service layer encapsulating business logic rules and workflows."
            elif folder == "src/repositories" or folder == "repositories":
                desc = "Data access repository layer executing SQL database operations."
            elif folder == "src/models" or folder == "models":
                desc = "SQLAlchemy database schemas declaring database entity properties."
            elif folder == "tests" or folder == "src/tests":
                desc = "Unit and integration test suites validating backend and frontend systems."
                
            folders_breakdown.append({
                "path": folder,
                "description": desc
            })

        # Recommended Reading Order
        reading_order = []
        entry_paths = {ep["path"] for ep in entry_points}
        # Add readme first
        readme_item = next((f for f in important_files if "readme" in f["path"].lower()), None)
        if readme_item:
            reading_order.append({
                "step": 1,
                "path": readme_item["path"],
                "reason": "Offers installation steps, local run procedures, and project outline."
            })
            
        # Add manifests next
        manifest_item = next((f for f in important_files if f["path"].endswith(("package.json", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml"))), None)
        if manifest_item:
            reading_order.append({
                "step": len(reading_order) + 1,
                "path": manifest_item["path"],
                "reason": "Shows third-party packages, libraries, and compilation configurations."
            })
            
        # Add entry point
        entry_item = next((f for f in important_files if f["path"] in entry_paths or f["path"] == main_entry), None)
        if entry_item:
            reading_order.append({
                "step": len(reading_order) + 1,
                "path": entry_item["path"],
                "reason": "Application bootstrap entry point where routing and database setups occur."
            })
            
        # Add routes/schema files
        route_item = next((f for f in important_files if "route" in f["path"].lower() or "api/" in f["path"] or "controllers" in f["path"].lower()), None)
        if route_item:
            reading_order.append({
                "step": len(reading_order) + 1,
                "path": route_item["path"],
                "reason": "Defines endpoints and shows how HTTP parameters map to core functions."
            })
            
        # Add service files
        service_item = next((f for f in important_files if "service" in f["path"].lower() or "usecases" in f["path"].lower() or "models" in f["path"].lower()), None)
        if service_item:
            reading_order.append({
                "step": len(reading_order) + 1,
                "path": service_item["path"],
                "reason": "Implements core business operations and logic handlers."
            })

        # Ensure we have at least some reading list
        if not reading_order:
            for i, f in enumerate(important_files[:3]):
                reading_order.append({
                    "step": i + 1,
                    "path": f["path"],
                    "reason": f["explanation"]
                })

        onboarding_guide = {
            "where_to_start": start_desc,
            "entry_points": [
                {"path": ep["path"], "language": ep["language"], "description": ep["description"]} 
                for ep in entry_points
            ],
            "important_folders": folders_breakdown,
            "recommended_reading_order": reading_order,
            "key_technologies": tech_list + framework_list
        }

        return {
            "summary": summary,
            "onboarding_guide": onboarding_guide
        }
