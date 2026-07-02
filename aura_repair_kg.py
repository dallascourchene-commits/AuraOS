"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c4-[Q-SYS:REPAIR_KG]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Graph-Grounded Context / Knowledge Representation)
DEPENDENCIES: ast, json, pathlib, typing
FUNCTIONS: RepositoryKnowledgeGraph, build_repair_kg
SYNOPSIS: Queryable knowledge graph linking files, AST symbols, tests, patch attempts,
research papers, harness predictions, and verifier failures.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any


NODE_TYPES = {
    "file",
    "symbol",
    "test",
    "patch_attempt",
    "gate_failure",
    "research_paper",
    "harness_prediction",
}

EDGE_TYPES = {
    "declares",
    "declared_in",
    "imports",
    "neighbor",
    "tests",
    "patch_touched",
    "patch_failed_at",
    "patch_fixed",
    "paper_supports",
    "prediction_about",
}

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "Aura_Memory",
    "Aura_Sandbox",
    "node_modules",
    "venv",
    ".venv",
    "ojibwemorph_release",
}


def _normalize_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def _node_id(node_type: str, key: str) -> str:
    return f"{node_type}:{key}"


class RepositoryKnowledgeGraph:
    """Queryable repository knowledge graph that integrates CODEMAP and fallback AST scans."""

    def __init__(self, repo_root: str | Path) -> None:
        self.root = Path(repo_root).resolve()
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, list[dict[str, Any]]] = {}
        if not self._load_from_codemap():
            self._load_from_ast_fallback()

    def _load_codemap_json(self) -> dict[str, Any] | None:
        codemap_path = self.root / ".aura" / "CODEMAP.json"
        if not codemap_path.exists() or codemap_path.stat().st_size == 0:
            return None
        try:
            data = json.loads(codemap_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _codemap_file_entries(self, codemap: dict[str, Any]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for key in ("files", "file_cards"):
            raw = codemap.get(key)
            if isinstance(raw, list):
                entries.extend(item for item in raw if isinstance(item, dict) and item.get("path"))
        return entries

    def _ensure_file_node(self, path: str, **metadata: Any) -> str:
        normalized = _normalize_path(path)
        node_id = _node_id("file", normalized)
        existing = self.nodes.get(node_id, {})
        self.nodes[node_id] = {
            "type": "file",
            "path": normalized,
            **existing,
            **metadata,
        }
        return node_id

    def _ensure_test_node(self, path: str) -> str:
        normalized = _normalize_path(path)
        node_id = _node_id("test", normalized)
        self.nodes.setdefault(node_id, {"type": "test", "path": normalized})
        return node_id

    def _load_from_codemap(self) -> bool:
        codemap = self._load_codemap_json()
        if not codemap:
            return False

        loaded = False
        for file_entry in self._codemap_file_entries(codemap):
            path = _normalize_path(file_entry.get("path", ""))
            if not path:
                continue
            loaded = True
            file_node = self._ensure_file_node(
                path,
                role=file_entry.get("role", "unknown"),
                lines=file_entry.get("lines", 0),
                bytes=file_entry.get("bytes", 0),
                tokens_est=file_entry.get("tokens_est", 0),
                source="codemap",
            )
            if Path(path).name.startswith("test_"):
                test_node = self._ensure_test_node(path)
                self.add_edge(test_node, file_node, "tests")

            topology = file_entry.get("topology", {})
            if isinstance(topology, dict):
                for neighbor in topology.get("neighbor_files", []) or []:
                    neighbor_path = _normalize_path(neighbor)
                    if neighbor_path:
                        neighbor_node = self._ensure_file_node(neighbor_path, source="codemap_neighbor")
                        self.add_edge(file_node, neighbor_node, "neighbor")
                for imported in topology.get("imports", []) or []:
                    imported_path = _normalize_path(imported)
                    if imported_path.endswith(".py"):
                        self.add_edge(file_node, self._ensure_file_node(imported_path), "imports")

            direct_test = Path(path).parent / f"test_{Path(path).name}"
            if (self.root / direct_test).exists():
                test_node = self._ensure_test_node(direct_test.as_posix())
                self.add_edge(test_node, file_node, "tests")

        symbol_index = codemap.get("symbol_index")
        if isinstance(symbol_index, dict):
            for sym_name, occurrences in symbol_index.items():
                if not isinstance(occurrences, list):
                    continue
                for occ in occurrences:
                    file_path = _normalize_path(occ.get("file") or occ.get("path") or "")
                    if not file_path:
                        continue
                    file_node = self._ensure_file_node(file_path, source="codemap_symbol")
                    symbol_node = _node_id("symbol", f"{sym_name}@{file_path}")
                    self.nodes[symbol_node] = {
                        "type": "symbol",
                        "name": sym_name,
                        "kind": occ.get("kind", "unknown"),
                        "file": file_path,
                        "line": occ.get("line", 0),
                        "end_line": occ.get("end_line", 0),
                    }
                    self.add_edge(file_node, symbol_node, "declares")
                    self.add_edge(symbol_node, file_node, "declared_in")
                    loaded = True

        return loaded

    def _load_from_ast_fallback(self) -> None:
        py_files: list[Path] = []
        for path in sorted(self.root.glob("**/*.py")):
            relative = path.relative_to(self.root)
            if any(part in EXCLUDE_DIRS for part in relative.parts):
                continue
            py_files.append(path)
            self._ensure_file_node(relative.as_posix(), source="ast_fallback")

        module_to_file = {path.stem: path.relative_to(self.root).as_posix() for path in py_files}
        for path in py_files:
            relative = path.relative_to(self.root).as_posix()
            file_node = self._ensure_file_node(relative, source="ast_fallback")
            if path.name.startswith("test_"):
                self._ensure_test_node(relative)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
            except Exception as exc:
                self.nodes[file_node]["parse_error"] = str(exc)
                continue

            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    symbol_node = _node_id("symbol", f"{node.name}@{relative}")
                    self.nodes[symbol_node] = {
                        "type": "symbol",
                        "name": node.name,
                        "kind": kind,
                        "file": relative,
                        "line": getattr(node, "lineno", 0),
                        "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                    }
                    self.add_edge(file_node, symbol_node, "declares")
                    self.add_edge(symbol_node, file_node, "declared_in")

            for node in ast.walk(tree):
                imported_names: list[str] = []
                if isinstance(node, ast.Import):
                    imported_names.extend(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_names.append(node.module.split(".", 1)[0])
                for imported in imported_names:
                    imported_file = module_to_file.get(imported)
                    if imported_file:
                        self.add_edge(file_node, self._ensure_file_node(imported_file, source="ast_import"), "imports")

            if path.name.startswith("test_"):
                source_name = path.name.removeprefix("test_")
                source_path = (path.parent / source_name).relative_to(self.root).as_posix()
                if (self.root / source_path).exists():
                    test_node = self._ensure_test_node(relative)
                    source_node = self._ensure_file_node(source_path, source="ast_test_detection")
                    self.add_edge(test_node, source_node, "tests")
            else:
                direct_test = path.parent / f"test_{path.name}"
                if direct_test.exists():
                    test_node = self._ensure_test_node(direct_test.relative_to(self.root).as_posix())
                    self.add_edge(test_node, file_node, "tests")

    def add_node(self, node_id: str, properties: dict[str, Any]) -> None:
        node_type = properties.get("type")
        if node_type is not None and node_type not in NODE_TYPES:
            properties = {**properties, "type": str(node_type)}
        self.nodes[node_id] = properties

    def add_edge(self, source_id: str, target_id: str, edge_type: str, metadata: dict[str, Any] | None = None) -> None:
        if edge_type not in EDGE_TYPES:
            metadata = {"edge_type_alias": edge_type, **(metadata or {})}
        edge = {
            "target": target_id,
            "type": edge_type,
            "metadata": metadata or {},
        }
        bucket = self.edges.setdefault(source_id, [])
        if edge not in bucket:
            bucket.append(edge)

    def get_related_nodes(self, node_id: str, edge_type: str | None = None) -> list[tuple[str, str, dict[str, Any]]]:
        """Find adjacent nodes, optionally filtering by edge type."""
        results = []
        for edge in self.edges.get(node_id, []):
            if edge_type is None or edge["type"] == edge_type:
                target_id = edge["target"]
                target_props = self.nodes.get(target_id, {})
                results.append((target_id, edge["type"], target_props))
        return results

    def trace_dependencies(self, start_file: str, max_depth: int = 2) -> set[str]:
        """Trace import/dependency chain starting from a specific file."""
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(_node_id("file", _normalize_path(start_file)), 0)]

        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited or depth > max_depth:
                continue
            visited.add(node_id)
            for target_id, edge_type, _ in self.get_related_nodes(node_id):
                if edge_type in {"neighbor", "imports"}:
                    queue.append((target_id, depth + 1))

        return {nid.split("file:", 1)[1] for nid in visited if nid.startswith("file:")}

    def add_patch_attempt(
        self,
        *,
        patch_id: str,
        touched_files: list[str],
        gate: str,
        ok: bool,
        failures: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        patch_node = _node_id("patch_attempt", patch_id)
        self.nodes[patch_node] = {
            "type": "patch_attempt",
            "patch_id": patch_id,
            "gate": gate,
            "ok": ok,
            "failure_count": len(failures),
            "metadata": metadata or {},
        }
        for file_path in touched_files:
            file_node = self._ensure_file_node(file_path, source="patch_attempt")
            self.add_edge(patch_node, file_node, "patch_touched")
            if ok:
                self.add_edge(patch_node, file_node, "patch_fixed")
        for index, failure in enumerate(failures):
            failure_id = _node_id("gate_failure", f"{patch_id}:{index}")
            self.nodes[failure_id] = {
                "type": "gate_failure",
                "patch_id": patch_id,
                "gate": gate,
                "message": str(failure),
            }
            self.add_edge(patch_node, failure_id, "patch_failed_at")

    def add_research_paper_support(
        self,
        *,
        arxiv_id: str,
        target_modules: list[str],
        lesson: str,
        acceptance_test: str,
    ) -> None:
        paper_node = _node_id("research_paper", arxiv_id)
        self.nodes[paper_node] = {
            "type": "research_paper",
            "arxiv_id": arxiv_id,
            "lesson": lesson,
            "acceptance_test": acceptance_test,
        }
        for module in target_modules:
            file_node = self._ensure_file_node(module, source="research_manifest")
            self.add_edge(paper_node, file_node, "paper_supports")

    def evidence_packet_for_file(self, path: str, *, depth: int = 1) -> dict[str, Any]:
        """Return compact adjacent evidence for a file node."""
        start = _node_id("file", _normalize_path(path))
        if start not in self.nodes:
            return {"root": start, "nodes": [], "edges": []}

        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(start, 0)]
        packet_nodes: list[dict[str, Any]] = []
        packet_edges: list[dict[str, Any]] = []

        while queue and len(packet_nodes) < 32:
            node_id, distance = queue.pop(0)
            if node_id in visited or distance > depth:
                continue
            visited.add(node_id)
            props = self.nodes.get(node_id, {})
            packet_nodes.append({"id": node_id, **props})
            if distance == depth:
                continue
            for edge in self.edges.get(node_id, [])[:16]:
                target = edge["target"]
                packet_edges.append(
                    {
                        "source": node_id,
                        "target": target,
                        "type": edge["type"],
                        "metadata": edge.get("metadata", {}),
                    }
                )
                if target not in visited:
                    queue.append((target, distance + 1))
            for source, edges in self.edges.items():
                for edge in edges:
                    if edge["target"] == node_id:
                        packet_edges.append(
                            {
                                "source": source,
                                "target": node_id,
                                "type": edge["type"],
                                "metadata": edge.get("metadata", {}),
                            }
                        )
                        if source not in visited:
                            queue.append((source, distance + 1))
        return {
            "root": start,
            "nodes": packet_nodes[:32],
            "edges": packet_edges[:64],
        }


def build_repair_kg(repo_root: str | Path) -> RepositoryKnowledgeGraph:
    return RepositoryKnowledgeGraph(repo_root)
