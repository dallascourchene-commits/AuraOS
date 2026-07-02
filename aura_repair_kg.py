"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c4-[Q-SYS:REPAIR_KG]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Graph-Grounded Context / Knowledge Representation)
DEPENDENCIES: json, pathlib, typing
FUNCTIONS: RepositoryKnowledgeGraph, build_repair_kg
SYNOPSIS: Queryable knowledge graph linking files, AST symbols, call graphs, tests, and error traces.
Leverages the existing .aura/CODEMAP.json for topological relationships.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Optional


class RepositoryKnowledgeGraph:
    """Queryable repository knowledge graph that integrates CODEMAP and trace events."""
    
    def __init__(self, repo_root: str | Path) -> None:
        self.root = Path(repo_root).resolve()
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, list[dict[str, Any]]] = {}
        self._load_from_codemap()
        
    def _load_from_codemap(self) -> None:
        codemap_path = self.root / ".aura" / "CODEMAP.json"
        if not codemap_path.exists():
            return
            
        try:
            codemap = json.loads(codemap_path.read_text(encoding="utf-8"))
            
            # Load files as nodes
            if "files" in codemap:
                for file_entry in codemap["files"]:
                    path = file_entry.get("path", "")
                    if not path:
                        continue
                    node_id = f"file:{path}"
                    self.nodes[node_id] = {
                        "type": "file",
                        "path": path,
                        "role": file_entry.get("role", "unknown"),
                        "lines": file_entry.get("lines", 0),
                        "bytes": file_entry.get("bytes", 0),
                        "tokens_est": file_entry.get("tokens_est", 0)
                    }
                    
                    # Add topological links (neighbor files, etc.)
                    topology = file_entry.get("topology", {})
                    if topology and isinstance(topology, dict):
                        neighbors = topology.get("neighbor_files", []) or []
                        for nb in neighbors:
                            self.add_edge(node_id, f"file:{nb}", "neighbor")
                            
            # Load symbols as nodes and link to files
            if "symbol_index" in codemap:
                for sym_name, occurrences in codemap["symbol_index"].items():
                    for occ in occurrences:
                        file_path = occ.get("file", "")
                        if not file_path:
                            continue
                        node_id = f"symbol:{sym_name}@{file_path}"
                        self.nodes[node_id] = {
                            "type": "symbol",
                            "name": sym_name,
                            "kind": occ.get("kind", "unknown"),
                            "line": occ.get("line", 0),
                            "end_line": occ.get("end_line", 0)
                        }
                        self.add_edge(node_id, f"file:{file_path}", "declared_in")
                        self.add_edge(f"file:{file_path}", node_id, "declares")
                        
        except Exception as exc:
            print(f"[-] Repair Knowledge Graph load failed: {exc}")
            
    def add_node(self, node_id: str, properties: dict[str, Any]) -> None:
        self.nodes[node_id] = properties
        
    def add_edge(self, source_id: str, target_id: str, edge_type: str, metadata: dict[str, Any] | None = None) -> None:
        if source_id not in self.edges:
            self.edges[source_id] = []
        self.edges[source_id].append({
            "target": target_id,
            "type": edge_type,
            "metadata": metadata or {}
        })
        
    def get_related_nodes(self, node_id: str, edge_type: str | None = None) -> list[tuple[str, str, dict[str, Any]]]:
        """Find adjacent nodes, optionally filtering by edge type."""
        results = []
        out_edges = self.edges.get(node_id, [])
        for edge in out_edges:
            if edge_type is None or edge["type"] == edge_type:
                target_id = edge["target"]
                target_props = self.nodes.get(target_id, {})
                results.append((target_id, edge["type"], target_props))
        return results

    def trace_dependencies(self, start_file: str, max_depth: int = 2) -> set[str]:
        """Trace import/dependency chain starting from a specific file."""
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(f"file:{start_file}", 0)]
        
        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited or depth > max_depth:
                continue
            visited.add(node_id)
            
            # Find neighbors and imports
            for target_id, edge_type, _ in self.get_related_nodes(node_id):
                if edge_type in {"neighbor", "imports"}:
                    queue.append((target_id, depth + 1))
                    
        return {nid.split("file:", 1)[1] for nid in visited if nid.startswith("file:")}


def build_repair_kg(repo_root: str | Path) -> RepositoryKnowledgeGraph:
    return RepositoryKnowledgeGraph(repo_root)
