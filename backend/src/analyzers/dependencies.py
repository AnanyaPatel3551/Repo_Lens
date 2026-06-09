import os
import re
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

try:
    import tomli as toml  # Fallback for Python <3.11
except ImportError:
    import tomllib as toml  # type: ignore

class DependencyAnalyzer:
    @staticmethod
    def analyze(root_dir: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scans for dependency manifest files and extracts dependencies.
        Returns:
            Dict[str, List[Dict[str, Any]]]: Mapping of file path to list of parsed dependencies.
        """
        extracted = {}

        for dirpath, _, filenames in os.walk(root_dir):
            # Exclude standard directory paths
            if any(ignored in dirpath for ignored in ["node_modules", "dist", "build", ".git", ".next", "coverage"]):
                continue

            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')

                if filename == "package.json":
                    extracted[rel_path] = DependencyAnalyzer._parse_package_json(full_path)
                elif filename == "requirements.txt":
                    extracted[rel_path] = DependencyAnalyzer._parse_requirements_txt(full_path)
                elif filename == "pyproject.toml":
                    extracted[rel_path] = DependencyAnalyzer._parse_pyproject_toml(full_path)
                elif filename == "Cargo.toml":
                    extracted[rel_path] = DependencyAnalyzer._parse_cargo_toml(full_path)
                elif filename == "go.mod":
                    extracted[rel_path] = DependencyAnalyzer._parse_go_mod(full_path)
                elif filename == "pom.xml":
                    extracted[rel_path] = DependencyAnalyzer._parse_pom_xml(full_path)

        return extracted

    @staticmethod
    def _parse_package_json(filepath: str) -> List[Dict[str, Any]]:
        dependencies = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Production dependencies
                if "dependencies" in data and isinstance(data["dependencies"], dict):
                    for name, version in data["dependencies"].items():
                        dependencies.append({"name": name, "version": str(version), "scope": "prod"})
                
                # Development dependencies
                if "devDependencies" in data and isinstance(data["devDependencies"], dict):
                    for name, version in data["devDependencies"].items():
                        dependencies.append({"name": name, "version": str(version), "scope": "dev"})
        except Exception:
            pass  # Fail-safe logic
        return dependencies

    @staticmethod
    def _parse_requirements_txt(filepath: str) -> List[Dict[str, Any]]:
        dependencies = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#') or line.startswith('-r') or line.startswith('-e'):
                        continue
                    
                    # Split package name and version info (e.g. fastapi==0.110.0 or flask>=2.0)
                    match = re.match(r"^([a-zA-Z0-9_\-\[\]]+)(?:[=<>~!@]+(.*))?$", line)
                    if match:
                        name, version = match.groups()
                        dependencies.append({
                            "name": name,
                            "version": version.strip() if version else "any",
                            "scope": "prod"
                        })
        except Exception:
            pass
        return dependencies

    @staticmethod
    def _parse_pyproject_toml(filepath: str) -> List[Dict[str, Any]]:
        dependencies = []
        try:
            with open(filepath, 'rb') as f:
                data = toml.load(f)
                
                # Check Poetry PEP format
                poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                if isinstance(poetry_deps, dict):
                    for name, val in poetry_deps.items():
                        if name == "python":
                            continue
                        ver = val.get("version") if isinstance(val, dict) else val
                        dependencies.append({"name": name, "version": str(ver), "scope": "prod"})
                
                # Poetry group dev
                poetry_dev = data.get("tool", {}).get("poetry", {}).get("group", {}).get("dev", {}).get("dependencies", {})
                if isinstance(poetry_dev, dict):
                    for name, val in poetry_dev.items():
                        ver = val.get("version") if isinstance(val, dict) else val
                        dependencies.append({"name": name, "version": str(ver), "scope": "dev"})
                        
                # Check PEP 621 Standard dependencies
                project_deps = data.get("project", {}).get("dependencies", [])
                if isinstance(project_deps, list):
                    for dep in project_deps:
                        match = re.match(r"^([a-zA-Z0-9_\-\[\]]+)(?:[=<>~!@\s]+(.*))?$", dep)
                        if match:
                            name, version = match.groups()
                            dependencies.append({
                                "name": name,
                                "version": version.strip() if version else "any",
                                "scope": "prod"
                            })
        except Exception:
            pass
        return dependencies

    @staticmethod
    def _parse_cargo_toml(filepath: str) -> List[Dict[str, Any]]:
        dependencies = []
        try:
            with open(filepath, 'rb') as f:
                data = toml.load(f)
                
                # Main dependencies
                cargo_deps = data.get("dependencies", {})
                if isinstance(cargo_deps, dict):
                    for name, val in cargo_deps.items():
                        ver = val.get("version") if isinstance(val, dict) else val
                        dependencies.append({"name": name, "version": str(ver) if ver else "any", "scope": "prod"})
                
                # Dev dependencies
                cargo_dev = data.get("dev-dependencies", {})
                if isinstance(cargo_dev, dict):
                    for name, val in cargo_dev.items():
                        ver = val.get("version") if isinstance(val, dict) else val
                        dependencies.append({"name": name, "version": str(ver) if ver else "any", "scope": "dev"})
        except Exception:
            pass
        return dependencies

    @staticmethod
    def _parse_go_mod(filepath: str) -> List[Dict[str, Any]]:
        dependencies = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 1. Match require block: require ( ... )
                block_matches = re.findall(r"require\s*\((.*?)\)", content, re.DOTALL)
                for block in block_matches:
                    for line in block.splitlines():
                        line = line.strip()
                        if not line or line.startswith('//'):
                            continue
                        parts = line.split()
                        if len(parts) >= 2:
                            name, version = parts[0], parts[1]
                            scope = "dev" if "indirect" in line else "prod"
                            dependencies.append({"name": name, "version": version, "scope": scope})
                            
                # 2. Match single line requires: require github.com/xxx v1.x.y
                single_matches = re.findall(r"^require\s+([^\s]+)\s+([^\s\n]+)", content, re.MULTILINE)
                for name, version in single_matches:
                    dependencies.append({"name": name, "version": version, "scope": "prod"})
        except Exception:
            pass
        return dependencies

    @staticmethod
    def _parse_pom_xml(filepath: str) -> List[Dict[str, Any]]:
        dependencies = []
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Remove namespace prefixes from XML tags to simplify xpath matching
            for elem in root.iter():
                if elem.tag.startswith('{'):
                    elem.tag = elem.tag.split('}', 1)[1]
            
            # Find all <dependency> tags in the document
            for dep in root.findall(".//dependency"):
                group_id_el = dep.find("groupId")
                artifact_id_el = dep.find("artifactId")
                version_el = dep.find("version")
                scope_el = dep.find("scope")
                
                if artifact_id_el is not None and group_id_el is not None:
                    name = f"{group_id_el.text}:{artifact_id_el.text}"
                    version = version_el.text if version_el is not None else "any"
                    scope = scope_el.text if scope_el is not None else "prod"
                    dependencies.append({
                        "name": name,
                        "version": version,
                        "scope": "prod" if scope in ["compile", "runtime", "prod"] else "dev"
                    })
        except Exception:
            pass
        return dependencies
