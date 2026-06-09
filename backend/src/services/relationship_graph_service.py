import os
from typing import List, Dict, Any
from src.models.report import Report

class RelationshipGraphService:
    """
    Service to compile dependency/call graph representation of entrypoints, routers, services, and databases.
    """

    @staticmethod
    def generate_graph(report: Report) -> Dict[str, Any]:
        """
        Traverses report structures and builds node-edge relationships.
        """
        nodes = []
        edges = []
        seen_nodes = set()

        entry_points = report.entry_points or []
        important_files = report.important_files or []

        # Helper to add node
        def add_node(node_id: str, label: str, node_type: str):
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append({
                    "id": node_id,
                    "label": label,
                    "type": node_type
                })

        # 1. Process entry points
        entry_nodes = []
        for ep in entry_points:
            path = ep.get("path")
            if path:
                label = os.path.basename(path)
                add_node(path, label, "entrypoint")
                entry_nodes.append(path)

        # 2. Process important files into categories
        router_nodes = []
        service_nodes = []
        database_nodes = []

        for f in important_files:
            path = f.get("path")
            if not path:
                continue
            
            # Skip readme
            if path.lower().endswith("readme.md"):
                continue

            label = os.path.basename(path)
            path_lower = path.lower()
            
            if "route" in path_lower or "controller" in path_lower or "api/" in path_lower or "pages/" in path_lower:
                add_node(path, label, "router")
                router_nodes.append(path)
            elif "service" in path_lower or "usecase" in path_lower or "util" in path_lower or "helper" in path_lower or "lib/" in path_lower:
                add_node(path, label, "service")
                service_nodes.append(path)
            elif "model" in path_lower or "db" in path_lower or "schema" in path_lower or "sql" in path_lower or "prisma" in path_lower:
                add_node(path, label, "database")
                database_nodes.append(path)
            else:
                add_node(path, label, "service")
                service_nodes.append(path)

        # Ensure we have at least one database node if models are mentioned but none registered
        if not database_nodes and any("db" in n["id"].lower() for n in nodes):
            # Already mapped above
            pass

        # 3. Establish relationships/edges
        # Link entrypoints -> routers
        for ep_path in entry_nodes:
            for r_path in router_nodes:
                edges.append({
                    "source": ep_path,
                    "target": r_path,
                    "label": "Dispatches to"
                })

        # Link routers -> services
        for r_path in router_nodes:
            # Connect to services
            for s_path in service_nodes[:5]: # cap relationships to keep graph readable
                edges.append({
                    "source": r_path,
                    "target": s_path,
                    "label": "Calls service"
                })

        # Link services -> database
        for s_path in service_nodes:
            for db_path in database_nodes:
                edges.append({
                    "source": s_path,
                    "target": db_path,
                    "label": "Reads/Writes"
                })

        # Fallback edges if none generated
        if not edges and len(nodes) > 1:
            for i in range(len(nodes) - 1):
                edges.append({
                    "source": nodes[i]["id"],
                    "target": nodes[i+1]["id"],
                    "label": "Calls"
                })

        # De-duplicate edges
        unique_edges = []
        seen_edges = set()
        for edge in edges:
            key = (edge["source"], edge["target"])
            if key not in seen_edges and edge["source"] != edge["target"]:
                seen_edges.add(key)
                unique_edges.append(edge)

        return {
            "nodes": nodes[:35],
            "edges": unique_edges[:50]
        }
