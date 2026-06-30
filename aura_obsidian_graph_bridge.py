"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f1-[Q-SYS:OBSIDIAN_GRAPH_BRIDGE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Resonant Recall)
DEPENDENCIES: json, pathlib, typing, dataclasses, time, re, sqlite3, hashlib, aura_graphify_schema, aura_topology_sync
FUNCTIONS: ObsidianGraphBridge, export_vault, export_graph_json, build_packet, note_filename, wikilink, yaml_frontmatter, main
SYNOPSIS: First-class Obsidian + Graphify bridge. Exports Aura's machine truth into a
human-readable Obsidian vault (Markdown notes with YAML frontmatter + Wikilinks) and a
machine-queryable typed graph (Graphify JSON). Obsidian is an export/review surface, not
source of truth. Graphify is a typed graph schema/export/query layer. Exact truth remains
in sidecars, CODEMAP, QDKT databases, files, tests, and verifier reports. Every note and
graph node carries a source_ref pointing to its authoritative record.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any

from aura_graphify_schema import (
    EDGE_TYPES,
    NODE_TYPES,
    EdgeType,
    GraphifyEdge,
    GraphifyNode,
    GraphifyPacket,
    GraphifyValidator,
    NodeType,
    SourceRef,
    SourceRefKind,
    edge_id_for,
    node_id_for,
    packet_to_json,
    validate_packet,
)
from aura_topology_sync import (
    ChangeSet,
    SyncState,
    TopologySync,
    detect_changes,
    load_sync_state,
    save_sync_state,
)

BRIDGE_VERSION = "AURA_OBSIDIAN_GRAPH_BRIDGE_V1"
DEFAULT_VAULT_DIR = Path("Aura_Vault")
DEFAULT_GRAPH_PATH = Path(".aura/graphify_graph.json")
DEFAULT_SYNC_STATE_PATH = Path(".aura/obsidian_graph_sync_state.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _slug(text: str) -> str:
    """Obsidian-safe note slug."""
    s = re.sub(r"[^\w\-.]+", "_", str(text).strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:128]


def note_filename(node_type: str, key: str) -> str:
    """Deterministic Obsidian note filename (without extension)."""
    return f"{node_type.lower()}_{_slug(key)}"


def wikilink(node_type: str, key: str) -> str:
    """Render an Obsidian Wikilink to a note."""
    return f"[[{note_filename(node_type, key)}]]"


def _yaml_escape(value: Any) -> str:
    s = str(value)
    if s == "":
        return '""'
    if any(ch in s for ch in (":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", "<", ">", "=", "!", "%", "@", "`", "\"", "'")):
        return json.dumps(s)
    return s


def yaml_frontmatter(meta: dict[str, Any]) -> str:
    """Render a YAML frontmatter block from a flat dict."""
    lines = ["---"]
    for key in sorted(meta):
        value = meta[key]
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_yaml_escape(item)}")
        elif isinstance(value, dict):
            if not value:
                lines.append(f"{key}: {{}}")
            else:
                lines.append(f"{key}:")
                for sub_key, sub_value in sorted(value.items()):
                    lines.append(f"  {sub_key}: {_yaml_escape(sub_value)}")
        else:
            lines.append(f"{key}: {_yaml_escape(value)}")
    lines.append("---")
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

@dataclass
class ExportResult:
    vault_dir: Path
    graph_path: Path
    notes_written: int = 0
    notes_removed: int = 0
    nodes: int = 0
    edges: int = 0
    validation_issues: int = 0
    change_summary: str = ""
    full_resync: bool = False


class ObsidianGraphBridge:
    """Exports Aura's machine truth into an Obsidian vault + Graphify graph JSON.

    Obsidian is an export/review surface, not source of truth.  Graphify is a
    typed graph schema/export/query layer.  Exact truth remains in sidecars,
    CODEMAP, QDKT databases, files, tests, and verifier reports.
    """

    def __init__(
        self,
        root: str | Path = ".",
        *,
        vault_dir: str | Path = DEFAULT_VAULT_DIR,
        graph_path: str | Path = DEFAULT_GRAPH_PATH,
        sync_state_path: str | Path = DEFAULT_SYNC_STATE_PATH,
    ) -> None:
        self.root = Path(root).resolve()
        self.vault_dir = Path(vault_dir)
        if not self.vault_dir.is_absolute():
            self.vault_dir = self.root / self.vault_dir
        self.graph_path = Path(graph_path)
        if not self.graph_path.is_absolute():
            self.graph_path = self.root / self.graph_path
        self.sync_state_path = Path(sync_state_path)
        if not self.sync_state_path.is_absolute():
            self.sync_state_path = self.root / self.sync_state_path
        self.sync = TopologySync(root=self.root, state_path=self.sync_state_path)
        self.validator = GraphifyValidator(root=self.root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(self, *, force_full: bool = False) -> ExportResult:
        """Run an incremental (or full) export and return a summary."""
        changes, state = self.sync.plan(force_full=force_full)

        if not changes.has_changes:
            return ExportResult(
                vault_dir=self.vault_dir,
                graph_path=self.graph_path,
                change_summary="no changes",
            )

        # Build the graph packet for the changed records
        packet = self.build_packet(changes, state)

        # Validate before writing
        issues = self.validator.validate(packet)
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            # Write the issues to a diagnostic file but do not write a broken graph
            diag_path = self.vault_dir / "_graphify_validation_issues.md"
            diag_path.parent.mkdir(parents=True, exist_ok=True)
            lines = ["# Graphify Validation Issues", ""]
            for issue in issues:
                lines.append(
                    f"- **{issue.severity}** `{issue.code}`: {issue.message} "
                    f"(node={issue.node_id}, edge={issue.edge_id})"
                )
            diag_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            raise ValueError(
                f"Graph packet failed validation with {len(errors)} error(s); "
                f"see {diag_path}"
            )

        # Write Obsidian notes
        notes_written, notes_removed = self._write_notes(packet, changes)

        # Write graph JSON
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph_path.write_text(packet_to_json(packet), encoding="utf-8")

        # Commit the sync state
        self.sync.commit(changes, state)

        return ExportResult(
            vault_dir=self.vault_dir,
            graph_path=self.graph_path,
            notes_written=notes_written,
            notes_removed=notes_removed,
            nodes=len(packet.nodes),
            edges=len(packet.edges),
            validation_issues=len(issues),
            change_summary=changes.summary(),
            full_resync=changes.full_resync,
        )

    # ------------------------------------------------------------------
    # Graph packet construction
    # ------------------------------------------------------------------

    def build_packet(self, changes: ChangeSet, state: SyncState) -> GraphifyPacket:
        """Build a GraphifyPacket from the changed records."""
        nodes: list[GraphifyNode] = []
        edges: list[GraphifyEdge] = []
        node_index: dict[str, GraphifyNode] = {}

        def add_node(node: GraphifyNode) -> GraphifyNode:
            if node.id in node_index:
                return node_index[node.id]
            node_index[node.id] = node
            nodes.append(node)
            return node

        def add_edge(source: str, target: str, edge_type: EdgeType,
                     *, source_ref: SourceRef | None = None,
                     properties: dict[str, Any] | None = None) -> None:
            eid = edge_id_for(source, target, edge_type.value)
            edges.append(GraphifyEdge(
                id=eid, source=source, target=target, type=edge_type.value,
                source_ref=source_ref, properties=properties or {},
            ))

        if changes.full_resync:
            self._ingest_files(nodes, add_node, add_edge, None)
            self._ingest_codemap(nodes, add_node, add_edge)
            self._ingest_topology(nodes, add_node, add_edge)
            self._ingest_tests(nodes, add_node, add_edge)
            self._ingest_sidecars(nodes, add_node, add_edge, None)
            self._ingest_verifiers(nodes, add_node, add_edge, None)
            self._ingest_arena(nodes, add_node, add_edge, None)
            self._ingest_qdkt(nodes, add_node, add_edge, None, None)
            self._ingest_dream(nodes, add_node, add_edge, None)
            self._ingest_savings(nodes, add_node, add_edge, None)
            self._ingest_fractal(nodes, add_node, add_edge, None)
            self._ingest_pricing(nodes, add_node, add_edge)
            self._ingest_hot_swap(nodes, add_node, add_edge, None)
        else:
            self._ingest_files(nodes, add_node, add_edge, changes)
            self._ingest_codemap(nodes, add_node, add_edge)
            self._ingest_topology(nodes, add_node, add_edge)
            self._ingest_tests(nodes, add_node, add_edge)
            self._ingest_sidecars(nodes, add_node, add_edge, changes)
            self._ingest_verifiers(nodes, add_node, add_edge, changes)
            self._ingest_arena(nodes, add_node, add_edge, changes)
            self._ingest_qdkt(nodes, add_node, add_edge,
                              changes.new_qdkt_events, changes.new_qdkt_crystals)
            self._ingest_dream(nodes, add_node, add_edge, changes)
            self._ingest_savings(nodes, add_node, add_edge, changes)
            self._ingest_fractal(nodes, add_node, add_edge, changes)
            self._ingest_pricing(nodes, add_node, add_edge)
            self._ingest_hot_swap(nodes, add_node, add_edge, changes)

        return GraphifyPacket(
            version=BRIDGE_VERSION,
            generated_at=_now_iso(),
            project={
                "name": "AuraOS",
                "root": str(self.root),
                "bridge": "aura_obsidian_graph_bridge",
            },
            nodes=nodes,
            edges=edges,
            meta={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "change_summary": changes.summary(),
                "full_resync": changes.full_resync,
                "node_type_counts": self._count_by(nodes, "type"),
                "edge_type_counts": self._count_by(edges, "type"),
            },
        )

    def _count_by(self, items: list, key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            k = str(getattr(item, key, "unknown"))
            counts[k] = counts.get(k, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Ingestors — each reads from the authoritative source and creates
    # Graphify nodes/edges with source_refs pointing to that source.
    # ------------------------------------------------------------------

    def _ingest_files(self, nodes, add_node, add_edge, changes) -> None:
        """Ingest source files as FILE nodes with IMPORTS/DEPENDS_ON edges."""
        codemap = _load_json(self.root / ".aura" / "CODEMAP.json") or {}
        files_by_path = {f.get("path", ""): f for f in codemap.get("files", [])}

        if changes is None:
            # Full resync: ingest all files from CODEMAP
            target_paths = sorted(files_by_path)
        else:
            target_paths = sorted(set(changes.changed_files) | set(files_by_path))

        for rel in target_paths:
            abs_path = self.root / rel
            if not abs_path.exists():
                continue
            card = files_by_path.get(rel, {})
            role = card.get("role", "source_file")
            node_id = node_id_for(NodeType.FILE.value, rel)
            source_ref = SourceRef(
                kind=SourceRefKind.SOURCE_FILE.value,
                path=rel,
                key=rel,
            )
            node = add_node(GraphifyNode(
                id=node_id,
                type=NodeType.FILE.value,
                label=Path(rel).name,
                source_ref=source_ref,
                properties={
                    "path": rel,
                    "role": role,
                    "bytes": card.get("bytes", abs_path.stat().st_size if abs_path.exists() else 0),
                    "lines": card.get("lines", 0),
                    "symbol_count": card.get("symbol_count", 0),
                    "digest8": card.get("digest8", ""),
                },
            ))
            # Ingest symbols from CODEMAP symbol_index
            for sym_name, hits in codemap.get("symbol_index", {}).items():
                for hit in hits:
                    if hit.get("file") != rel:
                        continue
                    kind = hit.get("kind", "")
                    if kind in ("function", "FunctionDef", "AsyncFunctionDef"):
                        sym_type = NodeType.SYMBOL.value
                        sym_kind = "function"
                    elif kind in ("class", "ClassDef"):
                        sym_type = NodeType.SYMBOL.value
                        sym_kind = "class"
                    else:
                        continue
                    sym_key = f"{rel}:{sym_name}:{hit.get('line', 0)}"
                    sym_id = node_id_for(sym_type, sym_key)
                    sym_ref = SourceRef(
                        kind=SourceRefKind.CODEMAP.value,
                        path=".aura/CODEMAP.json",
                        key=f"symbol_index:{sym_name}:{rel}:{hit.get('line', 0)}",
                    )
                    add_node(GraphifyNode(
                        id=sym_id,
                        type=sym_type,
                        label=sym_name,
                        source_ref=sym_ref,
                        properties={
                            "name": sym_name,
                            "kind": sym_kind,
                            "file": rel,
                            "line": hit.get("line", 0),
                            "end_line": hit.get("end_line", 0),
                            "semantic_id": hit.get("semantic_id", ""),
                            "signature_hash": hit.get("signature_hash", ""),
                        },
                    ))
                    # FILE contains SYMBOL — use DEPENDS_ON to link
                    add_edge(node_id, sym_id, EdgeType.DEPENDS_ON,
                             source_ref=SourceRef(
                                 kind=SourceRefKind.CODEMAP.value,
                                 path=".aura/CODEMAP.json",
                                 key=f"symbol_index:{sym_name}",
                             ))

    def _ingest_codemap(self, nodes, add_node, add_edge) -> None:
        """CODEMAP is the source of truth for file/symbol topology."""
        codemap = _load_json(self.root / ".aura" / "CODEMAP.json")
        if not codemap:
            return
        # Import edges from topology
        topology = codemap.get("topology", {})
        file_index = topology.get("file_index", {})
        for file_name, data in file_index.items():
            for neighbor in data.get("neighbor_files", []):
                # Find the FILE node for this file
                for node in nodes:
                    if node.type == NodeType.FILE.value and Path(node.properties.get("path", "")).name == file_name:
                        # Find the neighbor FILE node
                        for target in nodes:
                            if target.type == NodeType.FILE.value and Path(target.properties.get("path", "")).name == neighbor:
                                add_edge(node.id, target.id, EdgeType.IMPORTS,
                                         source_ref=SourceRef(
                                             kind=SourceRefKind.TOPOLOGY.value,
                                             path="Aura_Memory/live_topology_ast.json",
                                             key=f"file_index:{file_name}:{neighbor}",
                                         ))

    def _ingest_topology(self, nodes, add_node, add_edge) -> None:
        """Ingest topology edges (CALLS, IMPORTS) from live_topology_ast.json."""
        topo = _load_json(self.root / "Aura_Memory" / "live_topology_ast.json")
        if not topo:
            return
        # Build a lookup from topology node id to Graphify node id
        topo_to_gf: dict[str, str] = {}
        for tnode in topo.get("nodes", []):
            tnode_id = str(tnode.get("id", ""))
            tnode_file = str(tnode.get("file", ""))
            if not tnode_file:
                continue
            # Match by file path
            for node in nodes:
                if node.type == NodeType.FILE.value and node.properties.get("path", "") == tnode_file:
                    topo_to_gf[tnode_id] = node.id
                    break
        # Add edges
        for tedge in topo.get("edges", []):
            src = topo_to_gf.get(str(tedge.get("source", "")))
            tgt = topo_to_gf.get(str(tedge.get("target", "")))
            if not src or not tgt:
                continue
            edge_kind = str(tedge.get("type", ""))
            if "import" in edge_kind:
                gf_edge = EdgeType.IMPORTS
            elif "call" in edge_kind:
                gf_edge = EdgeType.CALLS
            else:
                gf_edge = EdgeType.DEPENDS_ON
            add_edge(src, tgt, gf_edge,
                     source_ref=SourceRef(
                         kind=SourceRefKind.TOPOLOGY.value,
                         path="Aura_Memory/live_topology_ast.json",
                         key=f"edges:{tedge.get('source')}:{tedge.get('target')}",
                     ))

    def _ingest_tests(self, nodes, add_node, add_edge) -> None:
        """Ingest test files and TESTS edges."""
        for test_file in sorted(self.root.glob("test_*.py")):
            rel = test_file.relative_to(self.root).as_posix()
            node_id = node_id_for(NodeType.FILE.value, rel)
            source_ref = SourceRef(
                kind=SourceRefKind.TEST_FILE.value,
                path=rel,
                key=rel,
            )
            add_node(GraphifyNode(
                id=node_id,
                type=NodeType.FILE.value,
                label=test_file.name,
                source_ref=source_ref,
                properties={"path": rel, "role": "test_file"},
            ))
            # Link test to the module it tests
            stem = test_file.stem
            if stem.startswith("test_"):
                target_name = stem[5:] + ".py"
                for target in nodes:
                    if target.type == NodeType.FILE.value and target.properties.get("path") == target_name:
                        add_edge(node_id, target.id, EdgeType.TESTS,
                                 source_ref=SourceRef(
                                     kind=SourceRefKind.TEST_FILE.value,
                                     path=rel,
                                     key=f"tests:{target_name}",
                                 ))

    def _ingest_sidecars(self, nodes, add_node, add_edge, changes) -> None:
        """Ingest sidecar files as SIDECAR_REF nodes."""
        sidecar_names = [
            "travel_price_sidecar.py", "travel_price_verifier.py",
            "travel_vsa_pointer_index.py", "travel_media_assets.py",
            "travel_package_arena.py", "travel_scraper_core.py",
            "travel_source_registry.py",
        ]
        for name in sidecar_names:
            p = self.root / name
            if not p.exists():
                continue
            rel = p.relative_to(self.root).as_posix()
            if changes is not None and rel not in changes.changed_sidecars and not changes.full_resync:
                continue
            node_id = node_id_for(NodeType.SIDECAR_REF.value, rel)
            source_ref = SourceRef(
                kind=SourceRefKind.SIDECAR_FILE.value,
                path=rel,
                key=rel,
            )
            add_node(GraphifyNode(
                id=node_id,
                type=NodeType.SIDECAR_REF.value,
                label=name,
                source_ref=source_ref,
                properties={"path": rel, "sidecar_type": "travel"},
            ))
            # Ensure the FILE node exists so the STORES_TRUTH_IN edge is valid
            file_node_id = node_id_for(NodeType.FILE.value, rel)
            add_node(GraphifyNode(
                id=file_node_id,
                type=NodeType.FILE.value,
                label=name,
                source_ref=SourceRef(
                    kind=SourceRefKind.SOURCE_FILE.value,
                    path=rel,
                    key=rel,
                ),
                properties={"path": rel, "role": "sidecar_file"},
            ))
            add_edge(node_id, file_node_id, EdgeType.STORES_TRUTH_IN,
                     source_ref=SourceRef(
                         kind=SourceRefKind.SIDECAR_FILE.value,
                         path=rel,
                         key=rel,
                     ))

    def _ingest_verifiers(self, nodes, add_node, add_edge, changes) -> None:
        """Ingest verifier files as VERIFIER_REPORT nodes."""
        verifier_names = ["aura_validation.py", "travel_price_verifier.py",
                          "aura_tokenizer_guard.py", "aura_resonant_test_oracle.py"]
        for name in verifier_names:
            p = self.root / name
            if not p.exists():
                continue
            rel = p.relative_to(self.root).as_posix()
            if changes is not None and rel not in changes.changed_verifiers and not changes.full_resync:
                continue
            node_id = node_id_for(NodeType.VERIFIER_REPORT.value, rel)
            source_ref = SourceRef(
                kind=SourceRefKind.VERIFIER_FILE.value,
                path=rel,
                key=rel,
            )
            add_node(GraphifyNode(
                id=node_id,
                type=NodeType.VERIFIER_REPORT.value,
                label=name,
                source_ref=source_ref,
                properties={"path": rel, "verifier_type": "gate"},
            ))
            # Ensure the FILE node exists so the VERIFIES edge is valid
            file_node_id = node_id_for(NodeType.FILE.value, rel)
            add_node(GraphifyNode(
                id=file_node_id,
                type=NodeType.FILE.value,
                label=name,
                source_ref=SourceRef(
                    kind=SourceRefKind.SOURCE_FILE.value,
                    path=rel,
                    key=rel,
                ),
                properties={"path": rel, "role": "verifier_file"},
            ))
            add_edge(node_id, file_node_id, EdgeType.VERIFIES,
                     source_ref=SourceRef(
                         kind=SourceRefKind.VERIFIER_FILE.value,
                         path=rel,
                         key=rel,
                     ))

    def _ingest_arena(self, nodes, add_node, add_edge, changes) -> None:
        """Ingest Arena runs, ActionCapsules, BoundaryContracts, ArenaLeases."""
        for arena_dir in (self.root / "Aura_Memory" / "arenas",
                          self.root / "Aura_Memory" / "icm_workspaces"):
            if not arena_dir.exists():
                continue
            for json_file in arena_dir.rglob("*.json"):
                data = _load_json(json_file)
                if not data:
                    continue
                arena_id = str(data.get("arena_id") or data.get("id") or json_file.stem)
                if changes is not None and arena_id not in changes.changed_arena_runs and not changes.full_resync:
                    continue
                rel = json_file.relative_to(self.root).as_posix()
                # Arena run node
                arena_node_id = node_id_for(NodeType.ARENA_RUN.value, arena_id)
                add_node(GraphifyNode(
                    id=arena_node_id,
                    type=NodeType.ARENA_RUN.value,
                    label=arena_id,
                    source_ref=SourceRef(
                        kind=SourceRefKind.ARENA_DIR.value,
                        path=rel,
                        key=arena_id,
                    ),
                    properties={
                        "domain": data.get("domain", ""),
                        "intent": data.get("intent", ""),
                        "phase_hash": data.get("phase_hash", ""),
                    },
                ))
                # Action capsules
                for cap in data.get("action_capsules", []):
                    cid = str(cap.get("capsule_id") or cap.get("id") or "unknown")
                    cap_id = node_id_for(NodeType.ACTION_CAPSULE.value, cid)
                    add_node(GraphifyNode(
                        id=cap_id,
                        type=NodeType.ACTION_CAPSULE.value,
                        label=cid,
                        source_ref=SourceRef(
                            kind=SourceRefKind.ARENA_DIR.value,
                            path=rel,
                            key=f"action_capsules:{cid}",
                        ),
                        properties={
                            "domain": cap.get("domain", ""),
                            "role": cap.get("role", ""),
                            "objective": cap.get("objective", ""),
                            "phase_hash": cap.get("phase_hash", ""),
                        },
                    ))
                    # Arena DEPENDS_ON capsule
                    add_edge(arena_node_id, cap_id, EdgeType.DEPENDS_ON,
                             source_ref=SourceRef(
                                 kind=SourceRefKind.ARENA_DIR.value,
                                 path=rel,
                                 key=f"action_capsules:{cid}",
                             ))
                # Boundary contracts
                for con in data.get("boundary_contracts", []):
                    cid = str(con.get("contract_id") or con.get("id") or "unknown")
                    con_id = node_id_for(NodeType.BOUNDARY_CONTRACT.value, cid)
                    add_node(GraphifyNode(
                        id=con_id,
                        type=NodeType.BOUNDARY_CONTRACT.value,
                        label=cid,
                        source_ref=SourceRef(
                            kind=SourceRefKind.ARENA_DIR.value,
                            path=rel,
                            key=f"boundary_contracts:{cid}",
                        ),
                        properties={
                            "domain": con.get("domain", ""),
                            "invariant": con.get("invariant", ""),
                            "status": con.get("status", ""),
                            "phase_hash": con.get("phase_hash", ""),
                        },
                    ))
                    # Contract BLOCKS capsule (boundary)
                    cap_ref = con.get("capsule_id")
                    if cap_ref:
                        cap_node_id = node_id_for(NodeType.ACTION_CAPSULE.value, cap_ref)
                        add_edge(con_id, cap_node_id, EdgeType.BLOCKS,
                                 source_ref=SourceRef(
                                     kind=SourceRefKind.ARENA_DIR.value,
                                     path=rel,
                                     key=f"boundary_contracts:{cid}",
                                 ))
                # Arena leases
                for lease in data.get("agent_leases", []):
                    lid = str(lease.get("lease_id") or "unknown")
                    lease_id = node_id_for(NodeType.ARENA_LEASE.value, lid)
                    add_node(GraphifyNode(
                        id=lease_id,
                        type=NodeType.ARENA_LEASE.value,
                        label=lid,
                        source_ref=SourceRef(
                            kind=SourceRefKind.ARENA_DIR.value,
                            path=rel,
                            key=f"agent_leases:{lid}",
                        ),
                        properties={
                            "holder": lease.get("holder", ""),
                            "status": lease.get("status", ""),
                            "mode": lease.get("mode", ""),
                        },
                    ))
                    # Lease LEASES capsule
                    cap_ref = lease.get("capsule_id")
                    if cap_ref:
                        cap_node_id = node_id_for(NodeType.ACTION_CAPSULE.value, cap_ref)
                        add_edge(lease_id, cap_node_id, EdgeType.LEASES,
                                 source_ref=SourceRef(
                                     kind=SourceRefKind.ARENA_DIR.value,
                                     path=rel,
                                     key=f"agent_leases:{lid}",
                                 ))
                # Verification ledger — APPROVES/REJECTS
                for ventry in data.get("verification_ledger", []):
                    stage = str(ventry.get("stage", ""))
                    status = str(ventry.get("status", ""))
                    if status == "passed":
                        add_edge(arena_node_id, arena_node_id, EdgeType.APPROVES,
                                 source_ref=SourceRef(
                                     kind=SourceRefKind.ARENA_DIR.value,
                                     path=rel,
                                     key=f"verification_ledger:{stage}",
                                 ),
                                 properties={"stage": stage, "status": status})
                    elif status == "blocked":
                        add_edge(arena_node_id, arena_node_id, EdgeType.REJECTS,
                                 source_ref=SourceRef(
                                     kind=SourceRefKind.ARENA_DIR.value,
                                     path=rel,
                                     key=f"verification_ledger:{stage}",
                                 ),
                                 properties={"stage": stage, "status": status})

    def _ingest_qdkt(self, nodes, add_node, add_edge, new_events, new_crystals) -> None:
        """Ingest QDKT events and crystals."""
        workspace_db = self.root / "Aura_Memory" / "qdkt_index.db"
        if not workspace_db.exists():
            return
        try:
            conn = sqlite3.connect(str(workspace_db))
            # Events
            if new_events is None:
                event_rows = conn.execute(
                    "SELECT event_id, event_type, concept, rationale, confidence, ts "
                    "FROM qdkt_events ORDER BY ts"
                ).fetchall()
            else:
                if not new_events:
                    event_rows = []
                else:
                    placeholders = ",".join(["?"] * len(new_events))
                    event_rows = conn.execute(
                        f"SELECT event_id, event_type, concept, rationale, confidence, ts "
                        f"FROM qdkt_events WHERE event_id IN ({placeholders}) ORDER BY ts",
                        new_events,
                    ).fetchall()
            for event_id, event_type, concept, rationale, confidence, ts in event_rows:
                node_id = node_id_for(NodeType.QDKT_EVENT.value, event_id)
                add_node(GraphifyNode(
                    id=node_id,
                    type=NodeType.QDKT_EVENT.value,
                    label=event_id,
                    source_ref=SourceRef(
                        kind=SourceRefKind.QDKT_DB.value,
                        path="Aura_Memory/qdkt_index.db",
                        key=f"qdkt_events:{event_id}",
                    ),
                    properties={
                        "event_type": event_type,
                        "concept": concept,
                        "rationale": rationale,
                        "confidence": confidence,
                        "ts": ts,
                    },
                ))
            # Crystals
            if new_crystals is None:
                crystal_rows = conn.execute(
                    "SELECT concept_key, action, confidence, count, last_confirmed "
                    "FROM qdkt_crystals"
                ).fetchall()
            else:
                if not new_crystals:
                    crystal_rows = []
                else:
                    placeholders = ",".join(["?"] * len(new_crystals))
                    crystal_rows = conn.execute(
                        f"SELECT concept_key, action, confidence, count, last_confirmed "
                        f"FROM qdkt_crystals WHERE concept_key IN ({placeholders})",
                        new_crystals,
                    ).fetchall()
            for concept_key, action, confidence, count, last_confirmed in crystal_rows:
                node_id = node_id_for(NodeType.QDKT_CRYSTAL.value, concept_key)
                add_node(GraphifyNode(
                    id=node_id,
                    type=NodeType.QDKT_CRYSTAL.value,
                    label=concept_key,
                    source_ref=SourceRef(
                        kind=SourceRefKind.QDKT_CRYSTAL_JSON.value,
                        path="Aura_Memory/qdkt_crystal_cache.json",
                        key=f"qdkt_crystals:{concept_key}",
                    ),
                    properties={
                        "action": action,
                        "confidence": confidence,
                        "count": count,
                        "last_confirmed": last_confirmed,
                    },
                ))
            conn.close()
        except Exception:
            pass

    def _ingest_dream(self, nodes, add_node, add_edge, changes) -> None:
        """Ingest DREAM scores and LEARNED_FROM / RETRIEVED_BY edges."""
        ledger = self.root / "Aura_Memory" / "dream_retrieval_ledger.jsonl"
        if not ledger.exists():
            return
        try:
            with ledger.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    phase_hash = str(row.get("phase_hash", ""))
                    if not phase_hash:
                        continue
                    if changes is not None and phase_hash not in changes.changed_dream_scores and not changes.full_resync:
                        continue
                    node_id = node_id_for(NodeType.DREAM_SCORE.value, phase_hash)
                    add_node(GraphifyNode(
                        id=node_id,
                        type=NodeType.DREAM_SCORE.value,
                        label=phase_hash,
                        source_ref=SourceRef(
                            kind=SourceRefKind.DREAM_LEDGER.value,
                            path="Aura_Memory/dream_retrieval_ledger.jsonl",
                            key=f"phase_hash:{phase_hash}",
                        ),
                        properties={
                            "query": row.get("query", ""),
                            "candidate_id": row.get("candidate_id", ""),
                            "candidate_type": row.get("candidate_type", ""),
                            "usefulness_score": row.get("usefulness_score", 0.0),
                            "semantic_score": row.get("semantic_score", 0.0),
                            "verifier_result": row.get("verifier_result"),
                        },
                    ))
                    # DREAM score HELPED the candidate it scored
                    candidate_id = str(row.get("candidate_id", ""))
                    if candidate_id:
                        # Try to find the candidate node
                        for target in nodes:
                            if target.label == candidate_id or target.id.endswith(candidate_id):
                                add_edge(node_id, target.id, EdgeType.HELPED,
                                         source_ref=SourceRef(
                                             kind=SourceRefKind.DREAM_LEDGER.value,
                                             path="Aura_Memory/dream_retrieval_ledger.jsonl",
                                             key=f"phase_hash:{phase_hash}",
                                         ))
                                break
        except Exception:
            pass

    def _ingest_savings(self, nodes, add_node, add_edge, changes) -> None:
        """Ingest savings DB transactions as TRANSACTION nodes."""
        db_path = self.root / "Aura_Memory" / "aura_savings.db"
        if not db_path.exists():
            return
        try:
            conn = sqlite3.connect(str(db_path))
            if changes is None or changes.full_resync:
                # Ingest recent calls only (last 100) to keep the graph manageable
                rows = conn.execute(
                    "SELECT id, ts, provider, model, call_type, task, aspect, "
                    "prompt_tokens, output_tokens, cost_usd, cost_saved_usd "
                    "FROM llm_calls ORDER BY id DESC LIMIT 100"
                ).fetchall()
            else:
                if not changes.new_savings_ids:
                    conn.close()
                    return
                placeholders = ",".join(["?"] * len(changes.new_savings_ids))
                rows = conn.execute(
                    f"SELECT id, ts, provider, model, call_type, task, aspect, "
                    f"prompt_tokens, output_tokens, cost_usd, cost_saved_usd "
                    f"FROM llm_calls WHERE id IN ({placeholders}) ORDER BY id",
                    changes.new_savings_ids,
                ).fetchall()
            conn.close()
            for row in rows:
                (rid, ts, provider, model, call_type, task, aspect,
                 prompt_tokens, output_tokens, cost_usd, cost_saved_usd) = row
                key = f"llm_calls:id={rid}"
                node_id = node_id_for(NodeType.TRANSACTION.value, key)
                add_node(GraphifyNode(
                    id=node_id,
                    type=NodeType.TRANSACTION.value,
                    label=f"call-{rid}",
                    source_ref=SourceRef(
                        kind=SourceRefKind.SAVINGS_DB.value,
                        path="Aura_Memory/aura_savings.db",
                        key=key,
                    ),
                    properties={
                        "id": rid,
                        "ts": ts,
                        "provider": provider,
                        "model": model,
                        "call_type": call_type,
                        "task": task,
                        "aspect": aspect,
                        "prompt_tokens": prompt_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": cost_usd,
                        "cost_saved_usd": cost_saved_usd,
                    },
                ))
        except Exception:
            pass

    def _ingest_fractal(self, nodes, add_node, add_edge, changes) -> None:
        """Ingest fractal ledger blocks as FRACTAL_BLOCK nodes."""
        db_path = self.root / "aura_ledger.db"
        if not db_path.exists():
            return
        try:
            conn = sqlite3.connect(str(db_path))
            if changes is None or changes.full_resync:
                rows = conn.execute(
                    "SELECT block_hash, file_path, content_hash, timestamp, "
                    "ram_stake, node_id FROM ledger_blocks ORDER BY timestamp DESC LIMIT 100"
                ).fetchall()
            else:
                if not changes.new_fractal_blocks:
                    conn.close()
                    return
                placeholders = ",".join(["?"] * len(changes.new_fractal_blocks))
                rows = conn.execute(
                    f"SELECT block_hash, file_path, content_hash, timestamp, "
                    f"ram_stake, node_id FROM ledger_blocks "
                    f"WHERE block_hash IN ({placeholders}) ORDER BY timestamp",
                    changes.new_fractal_blocks,
                ).fetchall()
            conn.close()
            for row in rows:
                block_hash, file_path, content_hash, timestamp, ram_stake, node_id_val = row
                key = f"ledger_blocks:{block_hash}"
                gf_node_id = node_id_for(NodeType.FRACTAL_BLOCK.value, block_hash)
                add_node(GraphifyNode(
                    id=gf_node_id,
                    type=NodeType.FRACTAL_BLOCK.value,
                    label=block_hash[:16],
                    source_ref=SourceRef(
                        kind=SourceRefKind.FRACTAL_LEDGER.value,
                        path="aura_ledger.db",
                        key=key,
                    ),
                    properties={
                        "block_hash": block_hash,
                        "file_path": file_path,
                        "content_hash": content_hash,
                        "timestamp": timestamp,
                        "ram_stake": ram_stake,
                        "node_id": node_id_val,
                    },
                ))
                # Fractal block AFFECTS the file it records
                file_node_id = node_id_for(NodeType.FILE.value, file_path)
                add_edge(gf_node_id, file_node_id, EdgeType.AFFECTS,
                         source_ref=SourceRef(
                             kind=SourceRefKind.FRACTAL_LEDGER.value,
                             path="aura_ledger.db",
                             key=key,
                         ))
        except Exception:
            pass

    def _ingest_pricing(self, nodes, add_node, add_edge) -> None:
        """Ingest pricing as PRICE nodes."""
        pricing = _load_json(self.root / ".aura" / "pricing.json")
        if not pricing:
            return
        prices = pricing.get("prices", {})
        for provider, data in prices.items():
            key = f"pricing:{provider}"
            node_id = node_id_for(NodeType.PRICE.value, key)
            add_node(GraphifyNode(
                id=node_id,
                type=NodeType.PRICE.value,
                label=f"price-{provider}",
                source_ref=SourceRef(
                    kind=SourceRefKind.PRICING_JSON.value,
                    path=".aura/pricing.json",
                    key=key,
                ),
                properties={
                    "provider": provider,
                    "in_per_1k": data.get("in_per_1k", 0.0),
                    "out_per_1k": data.get("out_per_1k", 0.0),
                    "updated": pricing.get("updated", ""),
                },
            ))

    def _ingest_hot_swap(self, nodes, add_node, add_edge, changes) -> None:
        """Ingest hot-swap (phase) capsules as HOT_SWAP_CAPSULE nodes."""
        for pattern in ("Aura_Memory/phase_capsule_*.json",
                        "Aura_Memory/hot_swap_*.json",
                        "Aura_Memory/phase_*.json"):
            for p in self.root.glob(pattern):
                rel = p.relative_to(self.root).as_posix()
                if changes is not None and rel not in changes.changed_hot_swaps and not changes.full_resync:
                    continue
                data = _load_json(p)
                if not data:
                    continue
                run_id = str(data.get("run_id") or data.get("phase_hash") or p.stem)
                key = f"hot_swap:{run_id}"
                node_id = node_id_for(NodeType.HOT_SWAP_CAPSULE.value, key)
                add_node(GraphifyNode(
                    id=node_id,
                    type=NodeType.HOT_SWAP_CAPSULE.value,
                    label=run_id,
                    source_ref=SourceRef(
                        kind=SourceRefKind.SOURCE_FILE.value,
                        path=rel,
                        key=key,
                    ),
                    properties={
                        "run_id": run_id,
                        "previous_agent": data.get("previous_agent", ""),
                        "next_role": data.get("next_role", ""),
                        "target_file": data.get("target_file", ""),
                        "phase_hash": data.get("phase_hash", ""),
                    },
                ))
                # Hot-swap POINTS_TO the target file
                target_file = data.get("target_file")
                if target_file:
                    file_node_id = node_id_for(NodeType.FILE.value, target_file)
                    add_edge(node_id, file_node_id, EdgeType.POINTS_TO,
                             source_ref=SourceRef(
                                 kind=SourceRefKind.SOURCE_FILE.value,
                                 path=rel,
                                 key=key,
                             ))

    # ------------------------------------------------------------------
    # Obsidian note writing
    # ------------------------------------------------------------------

    def _write_notes(self, packet: GraphifyPacket, changes: ChangeSet) -> tuple[int, int]:
        """Write Markdown notes for each node. Returns (written, removed)."""
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        notes_written = 0
        notes_removed = 0

        # Build edge adjacency for Wikilinks
        outgoing: dict[str, list[GraphifyEdge]] = {}
        incoming: dict[str, list[GraphifyEdge]] = {}
        for edge in packet.edges:
            outgoing.setdefault(edge.source, []).append(edge)
            incoming.setdefault(edge.target, []).append(edge)

        # Write a note for each node
        written_files: set[str] = set()
        for node in packet.nodes:
            filename = note_filename(node.type, node.properties.get("path") or node.label)
            md_path = self.vault_dir / f"{filename}.md"
            content = self._render_note(node, outgoing.get(node.id, []), incoming.get(node.id, []))
            md_path.write_text(content, encoding="utf-8")
            written_files.add(md_path.name)
            notes_written += 1

        # Remove notes for deleted files
        if changes.removed_files:
            for rel in changes.removed_files:
                filename = note_filename(NodeType.FILE.value, rel)
                md_path = self.vault_dir / f"{filename}.md"
                if md_path.exists():
                    md_path.unlink()
                    notes_removed += 1

        # Write an index note
        index_path = self.vault_dir / "Aura_Graph_Index.md"
        index_path.write_text(self._render_index(packet), encoding="utf-8")

        return notes_written, notes_removed

    def _render_note(self, node: GraphifyNode,
                     out_edges: list[GraphifyEdge],
                     in_edges: list[GraphifyEdge]) -> str:
        """Render a single Obsidian Markdown note for a node."""
        # YAML frontmatter
        meta: dict[str, Any] = {
            "aura_id": node.id,
            "node_type": node.type,
            "label": node.label,
            "source_ref_kind": node.source_ref.kind,
            "source_ref_path": node.source_ref.path,
            "source_ref_key": node.source_ref.key,
            "source_ref_hash": node.source_ref.hash,
            "exported_at": _now_iso(),
            "bridge_version": BRIDGE_VERSION,
        }
        # Add selected properties to frontmatter
        for key in ("path", "role", "domain", "event_type", "concept",
                     "provider", "call_type", "block_hash", "run_id"):
            if key in node.properties:
                meta[key] = node.properties[key]

        lines = [yaml_frontmatter(meta), ""]

        # Body
        lines.append(f"# {node.label}")
        lines.append("")
        lines.append(f"**Type**: `{node.type}`")
        lines.append("")
        lines.append("## Source of Truth")
        lines.append("")
        lines.append(f"This note is an **export**, not the source of truth. "
                     f"The authoritative record lives in:")
        lines.append("")
        lines.append(f"- **Kind**: `{node.source_ref.kind}`")
        lines.append(f"- **Path**: `{node.source_ref.path}`")
        lines.append(f"- **Key**: `{node.source_ref.key}`")
        if node.source_ref.hash:
            lines.append(f"- **Hash**: `{node.source_ref.hash}`")
        lines.append("")

        # Properties
        if node.properties:
            lines.append("## Properties")
            lines.append("")
            lines.append("| Property | Value |")
            lines.append("|----------|-------|")
            for key in sorted(node.properties):
                value = node.properties[key]
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, default=str)[:200]
                lines.append(f"| `{key}` | {value} |")
            lines.append("")

        # Outgoing links
        if out_edges:
            lines.append("## Outgoing Links")
            lines.append("")
            for edge in out_edges:
                target_node = None
                # Find target node label
                for n in [edge]:  # placeholder
                    pass
                lines.append(f"- {edge.type} → {self._edge_link(edge.target)}")
            lines.append("")

        # Incoming links
        if in_edges:
            lines.append("## Incoming Links")
            lines.append("")
            for edge in in_edges:
                lines.append(f"- {edge.type} ← {self._edge_link(edge.source)}")
            lines.append("")

        return "\n".join(lines) + "\n"

    def _edge_link(self, node_id: str) -> str:
        """Render a Wikilink for a node id by looking it up in the packet."""
        # We don't have direct access to the node here, so we render a
        # best-effort wikilink using the node id. The note filename is
        # derived from the node type and key, which we can parse from the id.
        # Format: gf:<TYPE>:<hash>
        parts = node_id.split(":", 2)
        if len(parts) == 3:
            node_type = parts[1]
            return f"[[{node_type.lower()}_{parts[2]}]]"
        return f"[[{node_id}]]"

    def _render_index(self, packet: GraphifyPacket) -> str:
        """Render the vault index note."""
        meta = {
            "title": "Aura Graph Index",
            "bridge_version": BRIDGE_VERSION,
            "exported_at": _now_iso(),
            "total_nodes": len(packet.nodes),
            "total_edges": len(packet.edges),
        }
        lines = [yaml_frontmatter(meta), ""]
        lines.append("# Aura Graph Index")
        lines.append("")
        lines.append("This vault is an **export** of Aura's machine truth for human review. "
                     "The source of truth remains in sidecars, CODEMAP, QDKT databases, "
                     "files, tests, and verifier reports.")
        lines.append("")

        # Group nodes by type
        by_type: dict[str, list[GraphifyNode]] = {}
        for node in packet.nodes:
            by_type.setdefault(node.type, []).append(node)

        for node_type in sorted(by_type):
            lines.append(f"## {node_type} ({len(by_type[node_type])})")
            lines.append("")
            for node in sorted(by_type[node_type], key=lambda n: n.label):
                filename = note_filename(node.type, node.properties.get("path") or node.label)
                lines.append(f"- [[{filename}]] — {node.label}")
            lines.append("")

        # Edge type summary
        lines.append("## Edge Types")
        lines.append("")
        edge_counts: dict[str, int] = {}
        for edge in packet.edges:
            edge_counts[edge.type] = edge_counts.get(edge.type, 0) + 1
        for etype in sorted(edge_counts):
            lines.append(f"- `{etype}`: {edge_counts[etype]}")
        lines.append("")

        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def export_vault(root: str | Path = ".",
                 *,
                 vault_dir: str | Path = DEFAULT_VAULT_DIR,
                 graph_path: str | Path = DEFAULT_GRAPH_PATH,
                 force_full: bool = False) -> ExportResult:
    """One-shot export convenience function."""
    bridge = ObsidianGraphBridge(root=root, vault_dir=vault_dir, graph_path=graph_path)
    return bridge.export(force_full=force_full)


def export_graph_json(root: str | Path = ".",
                      *,
                      graph_path: str | Path = DEFAULT_GRAPH_PATH,
                      force_full: bool = False) -> Path:
    """Export only the graph JSON (no Obsidian notes)."""
    bridge = ObsidianGraphBridge(root=root, graph_path=graph_path)
    changes, state = bridge.sync.plan(force_full=force_full)
    packet = bridge.build_packet(changes, state)
    issues = bridge.validator.validate(packet)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise ValueError(f"Graph packet failed validation with {len(errors)} error(s)")
    gpath = Path(graph_path)
    if not gpath.is_absolute():
        gpath = Path(root) / gpath
    gpath.parent.mkdir(parents=True, exist_ok=True)
    gpath.write_text(packet_to_json(packet), encoding="utf-8")
    bridge.sync.commit(changes, state)
    return gpath


def build_packet(root: str | Path = ".",
                 *,
                 force_full: bool = False) -> GraphifyPacket:
    """Build (but do not write) a GraphifyPacket."""
    bridge = ObsidianGraphBridge(root=root)
    changes, state = bridge.sync.plan(force_full=force_full)
    return bridge.build_packet(changes, state)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Aura Obsidian + Graphify Bridge")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT_DIR), help="Obsidian vault directory")
    parser.add_argument("--graph", default=str(DEFAULT_GRAPH_PATH), help="Graphify graph JSON path")
    parser.add_argument("--full", action="store_true", help="Force a full resync")
    parser.add_argument("--graph-only", action="store_true", help="Export only the graph JSON")
    args = parser.parse_args()

    if args.graph_only:
        path = export_graph_json(args.root, graph_path=args.graph, force_full=args.full)
        print(f"[+] Graph JSON: {path}")
        return 0

    result = export_vault(args.root, vault_dir=args.vault, graph_path=args.graph,
                          force_full=args.full)
    print(f"[+] Vault: {result.vault_dir}")
    print(f"[+] Graph: {result.graph_path}")
    print(f"[+] Notes written: {result.notes_written}")
    print(f"[+] Notes removed: {result.notes_removed}")
    print(f"[+] Nodes: {result.nodes}")
    print(f"[+] Edges: {result.edges}")
    print(f"[+] Changes: {result.change_summary}")
    if result.full_resync:
        print("[+] Mode: full resync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())