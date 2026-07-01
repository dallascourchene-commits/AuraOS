"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, aura_dream_retrieval, __future__, ast, re, collections.abc, argparse, typing, os, itertools, time, aura_qdkt, pathlib, collections, dataclasses, hashlib
FUNCTIONS: _hash_payload, _stable_id, _slug, _load_json, _now_iso, _spectral_coordinate, _classify_complexity, _extract_list, _count_by, _viz_radius, build_graph_packet, analyze_diff_impact, export_dashboard_json, export_tour_json, main, __post_init__, to_dict, __post_init__, to_dict, to_dict, to_dict, __init__, build, _reset, _add_node, _add_edge, _ingest_codemap, _ingest_topology, _ingest_tests, _ingest_sidecars, _ingest_verifiers, _ingest_arena_metadata, _ingest_qdkt_events, _ingest_domain_flows, _deduplicate_edges, _build_layers, _project_meta, __init__, analyze, _risk_text, __init__, _compute_fan_in, build_tours, _ranked_nodes, _build_tour, __init__, export, __init__, observe_navigation, observe_correction, _append_jsonl, __init__, score_task, _fallback_score
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import time
from typing import Any

UNDERSTAND_GRAPH_VERSION = "AURA_UNDERSTAND_GRAPH_V1"
UNDERSTAND_GRAPH_PATH = Path(".aura/understand_graph.json")
UNDERSTAND_GRAPH_TOUR_PATH = Path(".aura/understand_graph_tour.json")
UNDERSTAND_GRAPH_DIFF_PATH = Path(".aura/understand_graph_diff.json")
UNDERSTAND_GRAPH_QDKT_PATH = Path(".aura/understand_graph_qdkt.jsonl")

NODE_PREFIXES = frozenset({
    "file", "func", "class", "test", "sidecar", "verifier",
    "capsule", "contract", "qdkt", "dream", "domain", "flow", "step",
})

EDGE_TYPES = frozenset({
    "imports", "contains", "inherits", "calls", "tested_by",
    "configures", "documents", "depends_on", "related",
    "verifies", "triggers", "owns", "leases",
    "cross_domain", "contains_flow", "flow_step",
    "qdkt_observed", "dream_scored", "corrected_by",
})

NODE_TYPE_COLOR = {
    "file": "#3B82F6",
    "func": "#10B981",
    "class": "#F59E0B",
    "test": "#EC4899",
    "sidecar": "#8B5CF6",
    "verifier": "#EF4444",
    "capsule": "#06B6D4",
    "contract": "#F97316",
    "qdkt": "#6366F1",
    "dream": "#14B8A6",
    "domain": "#84CC16",
    "flow": "#A855F7",
    "step": "#64748B",
}

LAYER_Z_INDEX = {
    "substrate": 0,
    "codemap": 1,
    "arena": 2,
    "sidecar": 3,
    "verifier": 4,
    "qdkt": 5,
    "dream": 6,
    "domain": 7,
    "tour": 8,
}


def _hash_payload(payload, *, size=16):
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _stable_id(prefix, name, scope=""):
    if scope:
        return f"{prefix}:{_slug(scope)}:{_slug(name)}"
    return f"{prefix}:{_slug(name)}"


def _slug(text):
    s = re.sub(r"[^\w\-]+", "_", str(text).strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:96]


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _spectral_coordinate(node_id, layer, dims=3):
    seed = hashlib.blake2b(f"{layer}:{node_id}".encode(), digest_size=8).digest()
    coords = []
    for i in range(dims):
        chunk = seed[i * 3 : i * 3 + 3]
        val = int.from_bytes(chunk, "big") / (2 ** 24 - 1)
        coords.append(round(val * 2 - 1, 6))
    z_offset = LAYER_Z_INDEX.get(layer, 0) * 0.5
    coords[-1] = round(coords[-1] + z_offset, 6)
    return coords


@dataclass
class GraphNode:
    id: str
    type: str
    name: str
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    complexity: str = "simple"
    file_path: str = ""
    line_range: list[int] = field(default_factory=list)
    layer: str = "substrate"
    spectral_coordinate: list[float] = field(default_factory=list)
    color_hex: str = "#64748B"
    aura_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.type not in NODE_TYPE_COLOR:
            self.color_hex = "#64748B"
        else:
            self.color_hex = NODE_TYPE_COLOR[self.type]
        if not self.spectral_coordinate:
            self.spectral_coordinate = _spectral_coordinate(self.id, self.layer)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    direction: str = "forward"
    weight: float = 0.5
    description: str = ""

    def __post_init__(self):
        if self.type not in EDGE_TYPES:
            self.type = "related"
        self.weight = max(0.0, min(1.0, self.weight))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphLayer:
    id: str
    name: str
    description: str
    node_ids: list[str] = field(default_factory=list)
    z_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphPacket:
    version: str
    generated_at: str
    project: dict[str, Any]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    layers: list[GraphLayer]
    tours: list[dict[str, Any]]
    diff_impact: dict[str, Any]
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "project": self.project,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "layers": [l.to_dict() for l in self.layers],
            "tours": self.tours,
            "diff_impact": self.diff_impact,
            "meta": self.meta,
        }

class AuraUnderstandGraph:
    def __init__(self, repo_root="."):
        self.root = Path(repo_root).resolve()
        self.codemap_path = self.root / ".aura" / "CODEMAP.json"
        self.topology_path = self.root / "Aura_Memory" / "live_topology_ast.json"
        self.nodes = {}
        self.edges = []
        self.layers = {}
        self._node_map_by_file = {}

    def build(self, *, include_arena=True, include_qdkt=True):
        self._reset()
        self._ingest_codemap()
        self._ingest_topology()
        self._ingest_tests()
        self._ingest_sidecars()
        self._ingest_verifiers()
        if include_arena:
            self._ingest_arena_metadata()
        if include_qdkt:
            self._ingest_qdkt_events()
        self._ingest_domain_flows()
        self._deduplicate_edges()
        self._build_layers()
        return GraphPacket(
            version=UNDERSTAND_GRAPH_VERSION,
            generated_at=_now_iso(),
            project=self._project_meta(),
            nodes=list(self.nodes.values()),
            edges=self.edges,
            layers=list(self.layers.values()),
            tours=[],
            diff_impact={},
            meta={
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "total_layers": len(self.layers),
                "deterministic": True,
                "llm_enriched": False,
            },
        )

    def _reset(self):
        self.nodes.clear()
        self.edges.clear()
        self.layers.clear()
        self._node_map_by_file.clear()

    def _add_node(self, node):
        if node.id in self.nodes:
            existing = self.nodes[node.id]
            if not existing.summary and node.summary:
                existing.summary = node.summary
            if not existing.tags and node.tags:
                existing.tags = node.tags
            if not existing.file_path and node.file_path:
                existing.file_path = node.file_path
            if not existing.aura_metadata and node.aura_metadata:
                existing.aura_metadata = node.aura_metadata
            return existing
        self.nodes[node.id] = node
        return node

    def _add_edge(self, edge):
        self.edges.append(edge)


    def _ingest_codemap(self):
        codemap = _load_json(self.codemap_path)
        if not codemap:
            return
        files = codemap.get("files", [])
        symbol_index = codemap.get("symbol_index", {})
        if isinstance(files, dict):
            files = [{"path": k, **v} for k, v in files.items()]
        for item in files:
            path_str = item.get("path", "")
            if not path_str:
                continue
            node_id = _stable_id("file", path_str)
            tags = []
            if path_str.startswith("test_"):
                tags.append("test")
            if path_str.endswith(".py"):
                tags.append("python")
            elif path_str.endswith(".rs"):
                tags.append("rust")
            elif path_str.endswith(".md"):
                tags.append("documentation")
            role = item.get("role", "")
            summary = role.replace("_", " ").capitalize() if role else f"File {path_str}"
            node = GraphNode(
                id=node_id, type="file", name=Path(path_str).name,
                summary=summary, tags=tags,
                complexity=_classify_complexity(item), file_path=path_str,
                layer="codemap",
                aura_metadata={
                    "role": role,
                    "bytes": item.get("bytes", 0),
                    "lines": item.get("lines", 0),
                    "symbol_count": item.get("symbol_count", 0),
                    "topology": item.get("topology", {}),
                },
            )
            self._add_node(node)
            self._node_map_by_file[path_str] = node_id
            sym_names = item.get("topology", {}).get("symbols", [])
            for sym_name in sym_names:
                occurrences = symbol_index.get(sym_name, [])
                for occ in occurrences:
                    if occ.get("file") != path_str:
                        continue
                    kind = occ.get("kind", "")
                    if kind in ("function", "FunctionDef", "AsyncFunctionDef"):
                        sym_type = "func"
                    elif kind in ("class", "ClassDef"):
                        sym_type = "class"
                    else:
                        continue
                    sym_id = _stable_id(sym_type, f"{path_str}:{sym_name}")
                    self._add_node(GraphNode(
                        id=sym_id, type=sym_type, name=sym_name,
                        summary=f"{sym_type} {sym_name} in {path_str}", tags=[sym_type],
                        complexity="moderate", file_path=path_str,
                        line_range=[occ.get("line", 0), occ.get("end_line", 0)],
                        layer="codemap",
                        aura_metadata={"semantic_id": occ.get("semantic_id", ""), "signature_hash": occ.get("signature_hash", "")},
                    ))
                    self._add_edge(GraphEdge(source=node_id, target=sym_id, type="contains", weight=1.0))
                    break

    def _ingest_topology(self):
        topo = _load_json(self.topology_path)
        if not topo:
            return
        for tnode in topo.get("nodes", []):
            name = tnode.get("name", "") or tnode.get("id", "")
            node_id = _stable_id("file", tnode.get("id", name))
            if node_id not in self.nodes:
                self._add_node(GraphNode(
                    id=node_id, type="file", name=name,
                    summary=tnode.get("label", "") or "", tags=["topology"],
                    complexity="simple", file_path=tnode.get("id", ""), layer="codemap",
                ))
        for tedge in topo.get("edges", []):
            src = _stable_id("file", tedge.get("source", ""))
            tgt = _stable_id("file", tedge.get("target", ""))
            self._add_edge(GraphEdge(
                source=src, target=tgt, type=tedge.get("type", "depends_on"),
                weight=tedge.get("weight", 0.5), direction=tedge.get("direction", "forward"),
            ))


    def _ingest_tests(self):
        for test_file in sorted(self.root.glob("test_*.py")):
            rel = test_file.relative_to(self.root).as_posix()
            node_id = _stable_id("test", rel)
            self._add_node(GraphNode(
                id=node_id, type="test", name=test_file.name,
                summary=f"Test module {test_file.name}", tags=["test", "python"],
                complexity="moderate", file_path=rel, layer="codemap",
            ))
            stem = test_file.stem
            if stem.startswith("test_"):
                target_name = stem[5:] + ".py"
                target_id = _stable_id("file", target_name)
                if target_id in self.nodes:
                    self._add_edge(GraphEdge(source=node_id, target=target_id, type="tested_by", weight=0.9))

    def _ingest_sidecars(self):
        sidecar_files = [
            "travel_price_sidecar.py", "travel_price_verifier.py",
            "travel_vsa_pointer_index.py", "travel_media_assets.py",
            "travel_package_arena.py", "travel_scraper_core.py",
            "travel_source_registry.py",
        ]
        for name in sidecar_files:
            path = self.root / name
            if not path.exists():
                continue
            rel = path.relative_to(self.root).as_posix()
            node_id = _stable_id("sidecar", rel)
            self._add_node(GraphNode(
                id=node_id, type="sidecar", name=name,
                summary=f"Sidecar: {name}", tags=["sidecar", "travel"],
                complexity="moderate", file_path=rel, layer="sidecar",
            ))
            if "verifier" in name:
                continue
            verifier_id = _stable_id("verifier", "travel_price_verifier.py")
            if verifier_id in self.nodes:
                self._add_edge(GraphEdge(source=verifier_id, target=node_id, type="verifies", weight=0.8))

    def _ingest_verifiers(self):
        for name in ("travel_price_verifier.py", "aura_tokenizer_guard.py"):
            path = self.root / name
            if not path.exists():
                continue
            rel = path.relative_to(self.root).as_posix()
            node_id = _stable_id("verifier", rel)
            self._add_node(GraphNode(
                id=node_id, type="verifier", name=name,
                summary=f"Verifier gate: {name}", tags=["verifier"],
                complexity="complex", file_path=rel, layer="verifier",
            ))


    def _ingest_arena_metadata(self):
        arena_dirs = [self.root / "Aura_Memory" / "arenas", self.root / "Aura_Memory" / "icm_workspaces"]
        for arena_dir in arena_dirs:
            if not arena_dir.exists():
                continue
            for json_file in arena_dir.rglob("*.json"):
                try:
                    payload = _load_json(json_file)
                    if not payload:
                        continue
                    capsules = _extract_list(payload, "action_capsules", "capsules")
                    contracts = _extract_list(payload, "boundary_contracts", "contracts")
                    for cap in capsules:
                        cid = cap.get("capsule_id") or cap.get("id") or "unknown"
                        cap_id = _stable_id("capsule", cid)
                        self._add_node(GraphNode(
                            id=cap_id, type="capsule", name=cid,
                            summary=cap.get("role", "") or cap.get("objective", "") or f"Capsule {cid}",
                            tags=["capsule", cap.get("domain", "")],
                            complexity="moderate", layer="arena",
                            aura_metadata={"domain": cap.get("domain", "")},
                        ))
                    for con in contracts:
                        cid = con.get("contract_id") or con.get("id") or "unknown"
                        con_id = _stable_id("contract", cid)
                        self._add_node(GraphNode(
                            id=con_id, type="contract", name=cid,
                            summary=con.get("invariant", "") or f"BoundaryContract {cid}",
                            tags=["contract", con.get("domain", "")],
                            complexity="complex", layer="arena",
                            aura_metadata={"domain": con.get("domain", "")},
                        ))
                        cap_ref = con.get("capsule_id")
                        if cap_ref:
                            cap_node_id = _stable_id("capsule", cap_ref)
                            if cap_node_id in self.nodes:
                                self._add_edge(GraphEdge(source=cap_node_id, target=con_id, type="triggers", weight=0.9))
                except Exception:
                    continue

    def _ingest_qdkt_events(self):
        qdkt_path = self.root / "Aura_Memory" / "qdkt_index.db"
        if not qdkt_path.exists():
            return
        for qdkt_file in (self.root / "Aura_Memory").rglob("qdkt_*.jsonl"):
            try:
                with open(qdkt_file, "r", encoding="utf-8") as f:
                    for line in itertools.islice(f, 200):
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        event_id = row.get("event_id", "")
                        if not event_id:
                            continue
                        node_id = _stable_id("qdkt", event_id)
                        self._add_node(GraphNode(
                            id=node_id, type="qdkt", name=event_id[:32],
                            summary=row.get("rationale", "") or row.get("concept", "") or "QDKT event",
                            tags=["qdkt", row.get("event_type", "")],
                            complexity="simple", layer="qdkt",
                        ))
                        file_path = row.get("file_path") or row.get("payload", {}).get("file_path", "")
                        if file_path:
                            file_node_id = _stable_id("file", file_path)
                            if file_node_id in self.nodes:
                                self._add_edge(GraphEdge(source=node_id, target=file_node_id, type="qdkt_observed", weight=0.5))
            except Exception:
                continue


    def _ingest_domain_flows(self):
        travel_domain_id = _stable_id("domain", "travel")
        self._add_node(GraphNode(
            id=travel_domain_id, type="domain", name="Travel",
            summary="Travel domain: sidecars, verifiers, scrapers, VSA pointers, and package arena.",
            tags=["travel", "domain"], complexity="complex", layer="domain",
        ))
        for node in list(self.nodes.values()):
            if node.type == "sidecar" and "travel" in node.tags:
                self._add_edge(GraphEdge(source=travel_domain_id, target=node.id, type="contains_flow", weight=0.7))
        civic_domain_id = _stable_id("domain", "civic")
        self._add_node(GraphNode(
            id=civic_domain_id, type="domain", name="Civic",
            summary="Civic domain: governance, planning, and civic arena adapters.",
            tags=["civic", "domain"], complexity="moderate", layer="domain",
        ))
        code_domain_id = _stable_id("domain", "code")
        self._add_node(GraphNode(
            id=code_domain_id, type="domain", name="Code",
            summary="Core codebase domain: substrate, node, topology, VSA, DREAM, QDKT.",
            tags=["code", "domain"], complexity="complex", layer="domain",
        ))
        for node in list(self.nodes.values()):
            if node.type in ("file", "func", "class", "test") and not any(t in node.tags for t in ("travel", "civic")):
                self._add_edge(GraphEdge(source=code_domain_id, target=node.id, type="contains_flow", weight=0.3))
        self._add_edge(GraphEdge(
            source=code_domain_id, target=travel_domain_id, type="cross_domain", weight=0.4,
            description="Travel sidecars depend on core substrate modules",
        ))

    def _deduplicate_edges(self):
        seen = set()
        unique = []
        for e in self.edges:
            key = (e.source, e.target, e.type)
            if key in seen:
                continue
            seen.add(key)
            unique.append(e)
        self.edges = unique

    def _build_layers(self):
        layer_nodes = defaultdict(list)
        for nid, node in self.nodes.items():
            layer_nodes[node.layer].append(nid)
        for layer_name, nids in layer_nodes.items():
            self.layers[layer_name] = GraphLayer(
                id=f"layer:{layer_name}", name=layer_name.capitalize(),
                description=f"Aura {layer_name} layer", node_ids=nids,
                z_index=LAYER_Z_INDEX.get(layer_name, 0),
            )

    def _project_meta(self):
        return {
            "name": "AuraOS",
            "description": "Aura Polysynthetic Cognitive Substrate for Edge Orchestration",
            "root": str(self.root),
            "languages": ["Python", "Rust"],
            "frameworks": ["asyncio", "numpy", "SQLite", "VSA"],
        }


class DiffImpactAnalyzer:
    def __init__(self, graph, packet):
        self.graph = graph
        self.packet = packet
        self.node_map = {n.id: n for n in packet.nodes}
        self.edge_map = defaultdict(list)
        for e in packet.edges:
            self.edge_map[e.source].append(e)
            self.edge_map[e.target].append(e)

    def analyze(self, changed_files):
        changed_node_ids = set()
        unmapped = []
        for f in changed_files:
            mapped = False
            for node in self.packet.nodes:
                if node.file_path == f or node.name == Path(f).name:
                    changed_node_ids.add(node.id)
                    mapped = True
            if not mapped:
                unmapped.append(f)
        for e in self.packet.edges:
            if e.type == "contains" and e.source in changed_node_ids:
                changed_node_ids.add(e.target)
        changed_nodes = [self.node_map[nid] for nid in changed_node_ids if nid in self.node_map]
        affected_ids = set()
        impacted_edges = []
        for e in self.packet.edges:
            src_changed = e.source in changed_node_ids
            tgt_changed = e.target in changed_node_ids
            if src_changed or tgt_changed:
                impacted_edges.append(e)
                if src_changed and e.target not in changed_node_ids:
                    affected_ids.add(e.target)
                if tgt_changed and e.source not in changed_node_ids:
                    affected_ids.add(e.source)
        affected_nodes = [self.node_map[nid] for nid in affected_ids if nid in self.node_map]
        affected_by_type = defaultdict(list)
        for node in affected_nodes:
            affected_by_type[node.type].append(node.name)
        complex_changes = sum(1 for n in changed_nodes if n.complexity == "complex")
        cross_layer = len({n.layer for n in changed_nodes + affected_nodes})
        risk = min(1.0, 0.1 * len(changed_nodes) + 0.2 * complex_changes + 0.15 * cross_layer + 0.05 * len(affected_nodes))
        return {
            "changed_files": changed_files,
            "changed_nodes": [n.to_dict() for n in changed_nodes],
            "affected_nodes": [n.to_dict() for n in affected_nodes],
            "affected_by_type": dict(affected_by_type),
            "impacted_edges": [e.to_dict() for e in impacted_edges],
            "unmapped_files": unmapped,
            "risk_score": round(risk, 3),
            "risk_assessment": self._risk_text(risk, complex_changes, cross_layer, len(affected_ids)),
            "timestamp": _now_iso(),
        }

    @staticmethod
    def _risk_text(risk, complex_changes, cross_layer, affected_count):
        parts = []
        if risk > 0.7:
            parts.append("High risk: changes are deep and cross-layer.")
        elif risk > 0.4:
            parts.append("Moderate risk: localized but with downstream impact.")
        else:
            parts.append("Low risk: changes are localized with limited blast radius.")
        if complex_changes:
            parts.append(f" {complex_changes} complex component(s) changed.")
        if cross_layer > 1:
            parts.append(f" Impact spans {cross_layer} architectural layers.")
        if affected_count > 5:
            parts.append(f" Wide blast radius: {affected_count} affected nodes.")
        return " ".join(parts)


class GuidedTourBuilder:
    TOUR_DOMAINS = [
        ("codemap", "CODEMAP"),
        ("arena", "Liquid Arena"),
        ("travel", "Travel Arena"),
        ("civic", "Social Arena"),
        ("fintech", "Fintech Arena"),
        ("qdkt", "QDKT"),
        ("verifier", "Verifier Gates"),
    ]

    def __init__(self, packet):
        self.packet = packet
        self.node_map = {n.id: n for n in packet.nodes}
        self._compute_fan_in()

    def _compute_fan_in(self):
        self.fan_in = defaultdict(int)
        for e in self.packet.edges:
            self.fan_in[e.target] += 1

    def build_tours(self):
        tours = []
        codemap_nodes = self._ranked_nodes("codemap")
        tours.append(self._build_tour("CODEMAP Overview", "codemap", codemap_nodes[:10]))
        for layer_key, title in self.TOUR_DOMAINS[1:]:
            nodes = self._ranked_nodes(layer_key)
            if nodes:
                tours.append(self._build_tour(title, layer_key, nodes[:8]))
        return tours

    def _ranked_nodes(self, layer):
        candidates = [n for n in self.packet.nodes if n.layer == layer or layer in n.tags]
        candidates.sort(key=lambda n: (self.fan_in.get(n.id, 0), n.name), reverse=True)
        return candidates

    def _build_tour(self, title, layer, nodes):
        steps = []
        for idx, node in enumerate(nodes, start=1):
            step = {
                "order": idx,
                "title": node.name,
                "description": node.summary or f"Aura {node.type} {node.name}",
                "node_ids": [node.id],
                "complexity": node.complexity,
                "layer": node.layer,
            }
            if node.aura_metadata.get("language_lesson"):
                step["languageLesson"] = node.aura_metadata["language_lesson"]
            steps.append(step)
        return {
            "tour_id": _stable_id("tour", f"{layer}:{title}"),
            "title": title,
            "layer": layer,
            "description": f"Guided tour through the {title} layer, ordered by dependency fan-in.",
            "steps": steps,
            "step_count": len(steps),
        }


class GraphDashboardExport:
    def __init__(self, packet):
        self.packet = packet

    def export(self):
        nodes_out = []
        for n in self.packet.nodes:
            d = n.to_dict()
            if not d.get("spectral_coordinate"):
                d["spectral_coordinate"] = _spectral_coordinate(n.id, n.layer)
            d["layer_z_index"] = LAYER_Z_INDEX.get(n.layer, 0)
            d["viz_radius"] = _viz_radius(n)
            nodes_out.append(d)
        edges_out = []
        for e in self.packet.edges:
            d = e.to_dict()
            d["viz_weight"] = d["weight"]
            edges_out.append(d)
        return {
            "version": UNDERSTAND_GRAPH_VERSION,
            "format": "aura_dashboard_v1",
            "generated_at": _now_iso(),
            "project": self.packet.project,
            "nodes": nodes_out,
            "edges": edges_out,
            "layers": [l.to_dict() for l in self.packet.layers],
            "tours": self.packet.tours,
            "stats": {
                "total_nodes": len(nodes_out),
                "total_edges": len(edges_out),
                "total_layers": len(self.packet.layers),
                "total_tours": len(self.packet.tours),
                "node_type_counts": _count_by(nodes_out, "type"),
                "edge_type_counts": _count_by(edges_out, "type"),
            },
            "spectral_topology": {
                "coordinate_system": "hash_deterministic_3d",
                "layer_stack_z_offset": 0.5,
                "color_map": NODE_TYPE_COLOR,
            },
        }


class QDKTGraphObserver:
    def __init__(self):
        self._qdkt = None
        try:
            from aura_qdkt import get_qdkt
            self._qdkt = get_qdkt()
        except Exception:
            pass

    def observe_navigation(self, query, node_id, helpful):
        if self._qdkt is None:
            self._append_jsonl({
                "event_type": "graph_navigation",
                "query": query,
                "node_id": node_id,
                "helpful": helpful,
                "ts": time.time(),
            })
            return
        self._qdkt.observe(
            "graph_navigation",
            {"query": query, "node_id": node_id, "helpful": helpful},
            rationale=f"Graph navigation: query='{query}' node='{node_id}' helpful={helpful}",
            concept=f"graph_nav:{node_id}",
            confidence=0.8 if helpful else 0.3,
            subsystem="understand_graph",
        )

    def observe_correction(self, node_id, original_summary, correction):
        if self._qdkt is None:
            self._append_jsonl({
                "event_type": "graph_correction",
                "node_id": node_id,
                "original_summary": original_summary,
                "correction": correction,
                "ts": time.time(),
            })
            return
        self._qdkt.observe(
            "graph_correction",
            {"node_id": node_id, "original_summary": original_summary[:256], "correction": correction[:256]},
            rationale=f"Human corrected graph node {node_id}: {correction}",
            concept=f"graph_correct:{node_id}",
            confidence=1.0,
            subsystem="understand_graph",
        )

    @staticmethod
    def _append_jsonl(record):
        try:
            UNDERSTAND_GRAPH_QDKT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(UNDERSTAND_GRAPH_QDKT_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")
        except Exception:
            pass


class DREAMLiteGraphScorer:
    def __init__(self):
        self._rerank_for_arena = None
        self._DreamCandidate = None
        try:
            from aura_dream_retrieval import DreamCandidate, rerank_for_arena
            self._DreamCandidate = DreamCandidate
            self._rerank_for_arena = rerank_for_arena
        except Exception:
            pass

    def score_task(self, task_query, node_id, node_summary, success):
        if self._rerank_for_arena is None or self._DreamCandidate is None:
            return self._fallback_score(task_query, node_id, success)
        try:
            candidate = self._DreamCandidate(
                candidate_id=node_id,
                candidate_type="graph_node",
                source="understand_graph",
                content=node_summary,
                metadata={"task_query": task_query, "success": success},
                semantic_score=0.7 if success else 0.3,
                truth_boundary="graph_node_summary",
                exact_lookup_required=False,
            )
            result = self._rerank_for_arena(
                task_query,
                [candidate],
                "graph_node",
                arena_domain="understand_graph",
                record=True,
                metadata={"node_id": node_id, "success": success},
            )
            return result
        except Exception:
            return self._fallback_score(task_query, node_id, success)

    @staticmethod
    def _fallback_score(task_query, node_id, success):
        return {
            "query": task_query,
            "candidate_id": node_id,
            "candidate_type": "graph_node",
            "usefulness_score": 0.8 if success else 0.2,
            "semantic_score": 0.7 if success else 0.3,
            "mode": "fallback_heuristic",
            "timestamp": time.time(),
        }


def _classify_complexity(meta):
    count = meta.get("symbol_count", 0)
    if not count:
        topo = meta.get("topology", {})
        count = len(topo.get("symbols", [])) if isinstance(topo, dict) else 0
    if count > 30:
        return "complex"
    if count > 10:
        return "moderate"
    return "simple"


def _extract_list(payload, *keys):
    for k in keys:
        val = payload.get(k)
        if isinstance(val, list):
            return val
    return []


def _count_by(items, key):
    counts = defaultdict(int)
    for item in items:
        counts[str(item.get(key, "unknown"))] += 1
    return dict(counts)


def _viz_radius(node):
    base = {"simple": 0.3, "moderate": 0.5, "complex": 0.8}.get(node.complexity, 0.4)
    jitter = (hash(node.id) % 100) / 1000.0
    return round(base + jitter, 3)


def build_graph_packet(repo_root=".", *, include_arena=True, include_qdkt=True):
    graph = AuraUnderstandGraph(repo_root)
    packet = graph.build(include_arena=include_arena, include_qdkt=include_qdkt)
    tours = GuidedTourBuilder(packet).build_tours()
    packet.tours = tours
    return packet


def analyze_diff_impact(packet, changed_files):
    graph = AuraUnderstandGraph()
    graph.nodes = {n.id: n for n in packet.nodes}
    graph.edges = packet.edges
    analyzer = DiffImpactAnalyzer(graph, packet)
    return analyzer.analyze(changed_files)


def export_dashboard_json(packet, output_path=None):
    exporter = GraphDashboardExport(packet)
    payload = exporter.export()
    path = Path(output_path or UNDERSTAND_GRAPH_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return str(path)


def export_tour_json(packet, output_path=None):
    path = Path(output_path or UNDERSTAND_GRAPH_TOUR_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tours": packet.tours, "version": UNDERSTAND_GRAPH_VERSION}, f, indent=2, default=str)
    return str(path)


def main():
    import argparse
    p = argparse.ArgumentParser(description="Aura Understand Graph Bridge")
    p.add_argument("--build", action="store_true", help="Build graph packet")
    p.add_argument("--diff", nargs="*", default=None, help="Changed files for diff impact")
    p.add_argument("--export", action="store_true", help="Export dashboard JSON")
    p.add_argument("--tours", action="store_true", help="Export guided tours JSON")
    p.add_argument("--root", default=".", help="Repository root")
    p.add_argument("--output", default=str(UNDERSTAND_GRAPH_PATH), help="Output path")
    args = p.parse_args()

    if not (args.build or args.diff or args.export or args.tours):
        p.print_help()
        return 0

    packet = build_graph_packet(args.root)
    print(f"[+] Graph packet: {len(packet.nodes)} nodes, {len(packet.edges)} edges, {len(packet.tours)} tours")

    if args.diff is not None:
        impact = analyze_diff_impact(packet, args.diff)
        diff_path = UNDERSTAND_GRAPH_DIFF_PATH
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        with open(diff_path, "w", encoding="utf-8") as f:
            json.dump(impact, f, indent=2, default=str)
        print(f"[+] Diff impact: {diff_path}")
        print(f"    Risk score: {impact['risk_score']}")
        print(f"    Changed: {len(impact['changed_nodes'])}, Affected: {len(impact['affected_nodes'])}")

    if args.export:
        path = export_dashboard_json(packet, args.output)
        print(f"[+] Dashboard JSON: {path}")

    if args.tours:
        path = export_tour_json(packet)
        print(f"[+] Tours JSON: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


