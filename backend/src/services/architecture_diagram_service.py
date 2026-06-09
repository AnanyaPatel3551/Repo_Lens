import re
import json
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.report import Report
from src.services.llm_provider import BaseLLMProvider
from src.repositories.report import ReportRepository

class ArchitectureDiagramService:
    """
    Service to lazily generate and cache codebase Mermaid flowcharts.
    """

    @staticmethod
    async def get_diagrams(db: AsyncSession, report: Report, provider: BaseLLMProvider) -> Dict[str, str]:
        """
        Retrieves the Mermaid diagrams for the report, generating them via LLM if not already cached.
        """
        # Return cached diagrams if they exist
        arch_data = report.architecture_report or {}
        if "diagrams" in arch_data:
            return arch_data["diagrams"]

        # Call LLM to generate diagrams
        system_instruction = (
            "You are a Staff Software Architect who generates clear, accurate, and syntactically valid Mermaid flowcharts.\n"
            "Your job is to generate three different Mermaid flowcharts based on the repository's metadata:\n"
            "1. Request Flow Diagram (how HTTP requests translate through entry points, routers, to controllers/handlers).\n"
            "2. Service Interaction Diagram (how business services, databases, repositories, utilities, and helper modules connect).\n"
            "3. Folder Relationship Diagram (high-level block diagram showing directory structures and their linkages).\n\n"
            "CRITICAL RULES:\n"
            "- Output ONLY a valid JSON object matching the schema below. Do not wrap the JSON in backticks or include any conversational intro/outro text:\n"
            "{\n"
            "  \"request_flow\": \"graph TD\\n  Client[Client] --> router[router.py]\\n  router --> controller[controllers.py]\",\n"
            "  \"service_interaction\": \"graph LR\\n  service[Service] --> db[(Database)]\",\n"
            "  \"folder_relationship\": \"graph TD\\n  src[src] --> api[src/api]\"\n"
            "}\n"
            "- Ensure every Mermaid diagram is syntactically valid and uses valid node connections (e.g. A --> B).\n"
            "- Quote labels containing brackets, parentheses, or special characters to prevent Mermaid syntax errors (e.g., A[\"Router (API)\"] --> B[\"Controller\"])."
        )

        entry_points = report.entry_points or []
        entry_str = "\n".join([f"- {ep.get('path')}: {ep.get('description')}" for ep in entry_points])
        
        important_files = report.important_files or []
        files_str = "\n".join([f"- {f.get('path')}: {f.get('explanation')}" for f in important_files])
        
        arch_type = arch_data.get("architecture_type", "Unknown")
        
        summary_data = report.summary or {}
        purpose = summary_data.get("project_purpose", "Not specified.")
        important_modules = summary_data.get("important_modules", [])

        prompt = (
            f"Generate three Mermaid flowcharts for this codebase:\n\n"
            f"Project Purpose: {purpose}\n"
            f"Architecture Paradigm: {arch_type}\n"
            f"Entry Points:\n{entry_str}\n"
            f"Important Files:\n{files_str}\n"
            f"Key Folder Structures: {important_modules}\n"
        )

        fallback_diagrams = {
            "request_flow": "graph TD\n  Client[\"Client Request\"] --> Entry[\"Entry Point\"]\n  Entry --> Logic[\"Application Logic\"]",
            "service_interaction": "graph LR\n  Service[\"Application Service\"] --> Database[\"Database / Storage\"]",
            "folder_relationship": "graph TD\n  Root[\"Root Folder\"] --> Source[\"Source Files\"]"
        }

        try:
            raw_response = await provider.generate_response(prompt, system_instruction=system_instruction)
            
            # Robust extract/parse JSON
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

            parsed_data = extract_json(raw_response)
            diagrams = {
                "request_flow": parsed_data.get("request_flow", fallback_diagrams["request_flow"]),
                "service_interaction": parsed_data.get("service_interaction", fallback_diagrams["service_interaction"]),
                "folder_relationship": parsed_data.get("folder_relationship", fallback_diagrams["folder_relationship"])
            }
        except Exception as e:
            print(f"Failed to generate architecture diagrams: {e}. Using fallback diagrams.")
            diagrams = fallback_diagrams

        # Cache diagrams in the database report
        repo_model = ReportRepository(db)
        arch_data = dict(arch_data)
        arch_data["diagrams"] = diagrams
        
        # We need to update the report in-place
        await repo_model.update(report, {"architecture_report": arch_data})
        await db.commit()

        return diagrams
