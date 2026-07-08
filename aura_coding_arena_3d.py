"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9ea-[Q-SYS:HUMAN_3D_CODING_ARENA]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Human-First Surgical Context)
DEPENDENCIES: __future__, dataclasses, hashlib, json, pathlib, re, typing, aura_tokenizer_guard
FUNCTIONS: ArenaNode, ArenaLink, WiringFault, TokenCostEstimate, RouteCandidate, RouteDecision, load_arena_topology, select_micro_arena, compile_action_capsule, detect_wiring_faults, estimate_token_costs, simulate_model_route, apply_marked_edge, demo_topology
SYNOPSIS: Deterministic topology truth layer for Aura's human-first 3D Coding Arena. The visual graph is an interface only; compiled capsules carry exact text-native source facts.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Iterable

try:
    from aura_tokenizer_guard import sanitize_tokenizer_channels
except Exception:
    sanitize_tokenizer_channels = None  # type: ignore[assignment]

try:
    from aura_jspace_codec import attach_jspace_to_capsule
except Exception:
    attach_jspace_to_capsule = None  # type: ignore[assignment]


ARENA_TOPOLOGY_VERSION = "AURA_HUMAN_3D_CODING_ARENA_TOPOLOGY_V1"
CAPSULE_VERSION = "AURA_CODING_ARENA_CAPSULE_V1"
DEFAULT_CONSTRAINTS = ["NO_NEW_DEPS", "NO_FAKE_FILES", "VERIFY_AST", "HUMAN_APPROVAL"]
DEFAULT_TOKEN_BUDGET = 8192
DEFAULT_NODE_LIMIT = 640
DEFAULT_FILE_LIMIT = 180
DEFAULT_SYMBOL_LIMIT = 420

NODE_COLORS = {
    "file": "#4f8cff",
    "class": "#f2b84b",
    "function": "#38c98b",
    "method": "#78d9a2",
    "test": "#ef5da8",
    "router": "#c084fc",
    "context": "#22d3ee",
    "research": "#a3e635",
    "verifier": "#ff6b6b",
    "capsule": "#2dd4bf",
    "demo": "#94a3b8",
}


@dataclass
class ArenaNode:
    id: str
    label: str
    node_type: str
    file_path: str = ""
    symbol: str = ""
    kind: str = ""
    line_range: list[int] = field(default_factory=list)
    tokens_est: int = 0
    status: str = "normal"
    color: str = "#94a3b8"
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArenaLink:
    source: str
    target: str
    link_type: str = "related"
    weight: float = 0.5
    status: str = "known"
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.link_type
        return data


@dataclass
class WiringFault:
    kind: str
    severity: str
    node_id: str
    message: str
    candidate: bool = True
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TokenCostEstimate:
    raw_repo_tokens: int
    topology_tokens: int
    micro_arena_tokens: int
    capsule_tokens: int
    savings_vs_raw_pct: float
    savings_vs_topology_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteCandidate:
    route_id: str
    requires_vision: bool
    requires_network: bool
    requires_secrets: bool
    max_input_tokens: int
    best_for: list[str]
    blocked_for: list[str] = field(default_factory=list)
    estimated_cost: float | None = None
    last_success_rate: float | None = None
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteDecision:
    selected_route: str
    candidates: list[RouteCandidate]
    decision_trace: list[str]
    network_calls_made: bool = False
    secrets_required_for_selected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_route": self.selected_route,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "decision_trace": self.decision_trace,
            "network_calls_made": self.network_calls_made,
            "secrets_required_for_selected": self.secrets_required_for_selected,
        }


def load_arena_topology(
    repo_root: str | Path = ".",
    *,
    demo: bool = False,
    node_limit: int = DEFAULT_NODE_LIMIT,
) -> dict[str, Any]:
    """Load Aura topology as a browser-ready graph without making network calls."""
    root = Path(repo_root).resolve()
    if demo:
        return demo_topology(root)
    codemap = _load_json(root / ".aura" / "CODEMAP.json")
    if not codemap:
        return demo_topology(root, reason="codemap_missing")
    graph = _topology_from_codemap(root, codemap, node_limit=node_limit)
    if not graph["nodes"]:
        return demo_topology(root, reason="codemap_empty")
    return graph


def select_micro_arena(
    topology: dict[str, Any],
    selected_node_ids: Iterable[str],
    *,
    depth: int = 1,
    human_instruction: str = "",
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> dict[str, Any]:
    """Return a bounded local neighborhood for human review and capsule compilation."""
    graph = _normalize_graph(topology)
    selected = [node_id for node_id in _unique(str(item) for item in selected_node_ids) if node_id in graph["node_by_id"]]
    if not selected and graph["nodes"]:
        selected = [graph["nodes"][0]["id"]]
    depth = max(0, min(2, int(depth)))

    node_ids = set(selected)
    frontier = set(selected)
    for _ in range(depth):
        next_frontier: set[str] = set()
        for link in graph["links"]:
            source = str(link.get("source", ""))
            target = str(link.get("target", ""))
            if source in frontier:
                next_frontier.add(target)
            if target in frontier:
                next_frontier.add(source)
        next_frontier -= node_ids
        node_ids.update(next_frontier)
        frontier = next_frontier

    micro_nodes = [graph["node_by_id"][node_id] for node_id in graph["node_order"] if node_id in node_ids]
    micro_links = [
        link
        for link in graph["links"]
        if str(link.get("source", "")) in node_ids and str(link.get("target", "")) in node_ids
    ]
    selected_nodes = [graph["node_by_id"][node_id] for node_id in selected]
    faults = detect_wiring_faults(
        topology,
        selected,
        depth=depth,
        token_budget=token_budget,
    )
    token_cost = estimate_token_costs(topology, micro_nodes=micro_nodes, micro_links=micro_links)
    dependencies = _neighbors_by_direction(graph, selected, "out")
    callers = _neighbors_by_direction(graph, selected, "in")
    tests = _test_neighbors(graph, selected)
    return {
        "version": ARENA_TOPOLOGY_VERSION,
        "selected_node_ids": selected,
        "selected_nodes": selected_nodes,
        "nodes": micro_nodes,
        "links": micro_links,
        "depth": depth,
        "dependencies": dependencies,
        "callers": callers,
        "callees": dependencies,
        "tests": tests,
        "candidate_faults": [fault.to_dict() for fault in faults],
        "missing_or_weak_edges": [fault.to_dict() for fault in faults if "edge" in fault.kind or "route" in fault.kind],
        "token_cost": token_cost.to_dict(),
        "human_instruction": _sanitize_instruction(human_instruction),
    }


def compile_action_capsule(
    topology: dict[str, Any],
    selected_node_ids: Iterable[str],
    *,
    human_instruction: str = "",
    depth: int = 1,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> dict[str, Any]:
    """Compile exact bounded text-native context from selected topology nodes."""
    micro = select_micro_arena(
        topology,
        selected_node_ids,
        depth=depth,
        human_instruction=human_instruction,
        token_budget=token_budget,
    )
    selected_nodes = list(micro.get("selected_nodes", []) or [])
    target_files = _unique(
        node.get("file_path", "")
        for node in selected_nodes
        if _path_exists_in_topology(topology, str(node.get("file_path", "")))
    )
    target_symbols = _unique(node.get("symbol", "") for node in selected_nodes if node.get("symbol"))
    line_ranges = [
        {
            "node_id": node.get("id"),
            "file_path": node.get("file_path"),
            "symbol": node.get("symbol"),
            "line_range": node.get("line_range", []),
        }
        for node in selected_nodes
        if node.get("line_range")
    ]
    capsule_body = {
        "capsule_version": CAPSULE_VERSION,
        "op": _operation_from_instruction(human_instruction),
        "human_instruction": _sanitize_instruction(human_instruction),
        "selected": {
            "node_ids": list(micro.get("selected_node_ids", []) or []),
        },
        "context": {
            "target_files": target_files,
            "target_symbols": target_symbols,
            "line_ranges": line_ranges,
            "dependencies": list(micro.get("dependencies", []) or []),
            "callers": list(micro.get("callers", []) or []),
            "callees": list(micro.get("callees", []) or []),
            "tests": list(micro.get("tests", []) or []),
            "neighbors": [
                {
                    "id": node.get("id"),
                    "file_path": node.get("file_path"),
                    "symbol": node.get("symbol"),
                    "node_type": node.get("node_type"),
                }
                for node in list(micro.get("nodes", []) or [])[:40]
                if node.get("id") not in set(micro.get("selected_node_ids", []) or [])
            ],
        },
        "wiring_faults": list(micro.get("candidate_faults", []) or []),
        "missing_or_weak_edges": list(micro.get("missing_or_weak_edges", []) or []),
        "constraints": list(DEFAULT_CONSTRAINTS),
        "token_cost": dict(micro.get("token_cost", {}) or {}),
        "truth_policy": "Exact local topology/CODEMAP/AST facts are authoritative; visual screenshots are orientation only.",
    }
    route = simulate_model_route(capsule_body, token_budget=token_budget)
    capsule_body["route_decision"] = route.to_dict()
    capsule_body = _attach_jspace_capsule_state(capsule_body, topology)
    capsule_body["capsule_tokens_est"] = _estimate_tokens_json(capsule_body)
    capsule_body["phase_hash"] = _hash_payload(capsule_body)
    return capsule_body


def detect_wiring_faults(
    topology: dict[str, Any],
    selected_node_ids: Iterable[str],
    *,
    depth: int = 1,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> list[WiringFault]:
    """Flag candidate wiring faults in the selected slice without overclaiming correctness."""
    graph = _normalize_graph(topology)
    faults: list[WiringFault] = []
    selected = [node_id for node_id in _unique(str(item) for item in selected_node_ids) if node_id in graph["node_by_id"]]
    selected_set = set(selected)
    incoming, outgoing = _degree_maps(graph["links"])
    for node_id in selected:
        node = graph["node_by_id"][node_id]
        node_type = str(node.get("node_type") or node.get("type") or "")
        file_path = str(node.get("file_path") or "")
        in_count = len(incoming.get(node_id, []))
        out_count = len(outgoing.get(node_id, []))
        tests = _test_neighbors(graph, [node_id])
        if node_type in {"function", "method", "class", "file", "router", "context"} and not tests:
            faults.append(WiringFault(
                kind="missing_test_edge",
                severity="medium",
                node_id=node_id,
                message="Selected node has no known test neighbor in the local topology.",
                evidence={"node_type": node_type, "file_path": file_path},
            ))
        if node_type in {"function", "method", "class"} and in_count == 0:
            faults.append(WiringFault(
                kind="no_known_callers",
                severity="low",
                node_id=node_id,
                message="Selected callable has no known callers in the topology slice.",
                evidence={"incoming_edges": in_count},
            ))
        if in_count >= 25 or out_count >= 25:
            faults.append(WiringFault(
                kind="high_fan_in_out",
                severity="high" if max(in_count, out_count) >= 50 else "medium",
                node_id=node_id,
                message="Selected node has unusually high graph degree; route through human review before patching.",
                evidence={"incoming_edges": in_count, "outgoing_edges": out_count},
            ))
        if file_path and not _path_exists_in_topology(topology, file_path):
            faults.append(WiringFault(
                kind="stale_or_missing_file",
                severity="high",
                node_id=node_id,
                message="Selected node references a file path that is not present in the repository.",
                evidence={"file_path": file_path},
            ))
        if not node.get("metadata", {}).get("codemap_match", True):
            faults.append(WiringFault(
                kind="no_codemap_match",
                severity="medium",
                node_id=node_id,
                message="Selected node has no CODEMAP/MODULE_MANIFEST match.",
                evidence={"node_id": node_id},
            ))
        search_text = " ".join([node_id, file_path, str(node.get("symbol") or ""), str(node.get("label") or "")]).lower()
        if any(term in search_text for term in ("router", "route", "fst")):
            neighbor_text = " ".join(_neighbor_text(graph, [node_id])).lower()
            if not any(term in neighbor_text for term in ("context", "compress", "capsule", "arena")):
                faults.append(WiringFault(
                    kind="candidate_missing_context_route",
                    severity="medium",
                    node_id=node_id,
                    message="Router-like node has no obvious context/capsule/compression neighbor.",
                    evidence={"neighbor_terms_checked": ["context", "compress", "capsule", "arena"]},
                ))
    estimate = estimate_token_costs(
        topology,
        micro_nodes=[graph["node_by_id"][node_id] for node_id in selected if node_id in graph["node_by_id"]],
        micro_links=[],
    )
    if estimate.capsule_tokens > token_budget:
        for node_id in selected:
            faults.append(WiringFault(
                kind="token_budget_exceeded",
                severity="high",
                node_id=node_id,
                message="Selected capsule would exceed the configured token budget.",
                evidence={"budget": token_budget, "capsule_tokens": estimate.capsule_tokens},
            ))
    return _dedupe_faults(faults)


def estimate_token_costs(
    topology: dict[str, Any],
    *,
    micro_nodes: list[dict[str, Any]] | None = None,
    micro_links: list[dict[str, Any]] | None = None,
    capsule_payload: dict[str, Any] | None = None,
) -> TokenCostEstimate:
    meta = topology.get("meta", {}) if isinstance(topology.get("meta"), dict) else {}
    raw_repo_tokens = int(meta.get("raw_repo_tokens") or meta.get("codemap_tokens_est") or 0)
    if raw_repo_tokens <= 0:
        raw_repo_tokens = _estimate_tokens_json(topology)
    topology_tokens = _estimate_tokens_json({"nodes": topology.get("nodes", []), "links": topology.get("links", [])})
    micro_payload = {"nodes": micro_nodes or [], "links": micro_links or []}
    micro_tokens = _estimate_tokens_json(micro_payload)
    capsule_tokens = _estimate_tokens_json(capsule_payload if capsule_payload is not None else micro_payload)
    return TokenCostEstimate(
        raw_repo_tokens=raw_repo_tokens,
        topology_tokens=topology_tokens,
        micro_arena_tokens=micro_tokens,
        capsule_tokens=capsule_tokens,
        savings_vs_raw_pct=_pct_saved(raw_repo_tokens, capsule_tokens),
        savings_vs_topology_pct=_pct_saved(topology_tokens, capsule_tokens),
    )


def simulate_model_route(capsule: dict[str, Any], *, token_budget: int = DEFAULT_TOKEN_BUDGET) -> RouteDecision:
    """Produce a transparent route decision without external API calls."""
    capsule_tokens = int(capsule.get("capsule_tokens_est") or _estimate_tokens_json(capsule))
    faults = list(capsule.get("wiring_faults", []) or [])
    instruction = str(capsule.get("human_instruction") or "").lower()
    patch_like = any(term in instruction for term in ("patch", "fix", "connect", "wire", "send to worker"))
    high_fault = any(str(item.get("severity")) == "high" for item in faults if isinstance(item, dict))
    candidates = [
        RouteCandidate(
            route_id="LOCAL_DETERMINISTIC",
            requires_vision=False,
            requires_network=False,
            requires_secrets=False,
            max_input_tokens=token_budget,
            best_for=["topology_selection", "capsule_compile", "wiring_fault_audit"],
            estimated_cost=0.0,
            score=0.95 if not patch_like else 0.68,
        ),
        RouteCandidate(
            route_id="LOCAL_GEMMA_VISUAL_SUMMARY",
            requires_vision=True,
            requires_network=False,
            requires_secrets=False,
            max_input_tokens=4096,
            best_for=["optional_screenshot_summary", "human_orientation"],
            blocked_for=["exact_identifier_inference", "patch_authority"],
            estimated_cost=0.0,
            score=0.35,
        ),
        RouteCandidate(
            route_id="CODEGEMMA_MICRO_PATCH",
            requires_vision=False,
            requires_network=False,
            requires_secrets=False,
            max_input_tokens=8192,
            best_for=["bounded_code_patch_after_human_approval"],
            blocked_for=["missing_files", "unverified_high_faults"],
            estimated_cost=None,
            score=0.78 if patch_like and not high_fault and capsule_tokens <= 8192 else 0.25,
        ),
        RouteCandidate(
            route_id="FIREWORKS_TEXT_REASONER",
            requires_vision=False,
            requires_network=True,
            requires_secrets=True,
            max_input_tokens=128000,
            best_for=["larger_reasoning_if_user_explicitly_enables_network"],
            blocked_for=["mvp_offline_default", "no_implicit_external_calls"],
            estimated_cost=None,
            score=0.05,
        ),
        RouteCandidate(
            route_id="OPENHANDS_SANDBOX",
            requires_vision=False,
            requires_network=False,
            requires_secrets=False,
            max_input_tokens=16000,
            best_for=["future_sandboxed_patch_execution"],
            blocked_for=["sandbox_adapter_not_wired_in_mvp"],
            estimated_cost=None,
            score=0.1,
        ),
        RouteCandidate(
            route_id="HUMAN_REVIEW",
            requires_vision=False,
            requires_network=False,
            requires_secrets=False,
            max_input_tokens=0,
            best_for=["high_faults", "missing_tests", "approval_gate"],
            estimated_cost=0.0,
            score=0.88 if high_fault or not patch_like else 0.55,
        ),
    ]
    if capsule_tokens > token_budget:
        for candidate in candidates:
            if candidate.route_id not in {"HUMAN_REVIEW", "LOCAL_DETERMINISTIC"}:
                candidate.score = min(candidate.score, 0.05)
                if "token_budget_exceeded" not in candidate.blocked_for:
                    candidate.blocked_for.append("token_budget_exceeded")
    selected = max(candidates, key=lambda item: (item.score, item.route_id))
    trace = [
        "No provider APIs were called; this is a deterministic MVP scorecard.",
        f"capsule_tokens={capsule_tokens}; token_budget={token_budget}; patch_like={patch_like}; high_fault={high_fault}",
        f"selected={selected.route_id} because it has the highest safe offline score.",
    ]
    return RouteDecision(
        selected_route=selected.route_id,
        candidates=candidates,
        decision_trace=trace,
        network_calls_made=False,
        secrets_required_for_selected=selected.requires_secrets,
    )


def apply_marked_edge(
    topology: dict[str, Any],
    source: str,
    target: str,
    *,
    kind: str = "candidate_missing_route",
    status: str = "missing",
) -> dict[str, Any]:
    graph = {
        **topology,
        "nodes": list(topology.get("nodes", []) or []),
        "links": list(topology.get("links", []) or []),
    }
    node_ids = {str(node.get("id")) for node in graph["nodes"] if isinstance(node, dict)}
    if source not in node_ids or target not in node_ids:
        graph.setdefault("warnings", []).append("mark_edge_rejected_unknown_node")
        return graph
    graph["links"].append(
        ArenaLink(
            source=source,
            target=target,
            link_type=kind,
            weight=0.2,
            status=status,
            label="Human-marked candidate wiring fault",
            metadata={"human_marked": True},
        ).to_dict()
    )
    graph["meta"] = dict(graph.get("meta", {}) or {})
    graph["meta"]["marked_edge_count"] = int(graph["meta"].get("marked_edge_count") or 0) + 1
    return graph


def demo_topology(repo_root: str | Path = ".", *, reason: str = "demo_mode") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    nodes = [
        _node("aura_router.py::AutoRouter", "Router", "router", "aura_router.py", "AutoRouter", [1, 1], root, status="normal"),
        _node("aura_context_crusher.py::apply_context_crush_to_prompt", "Context compression", "context", "aura_context_crusher.py", "apply_context_crush_to_prompt", [1, 1], root, status="normal"),
        _node("aura_empirical_software_lab.py::score_candidate", "Empirical lab", "function", "aura_empirical_software_lab.py", "score_candidate", [1, 1], root, status="selected"),
        _node("aura_research_ingest_bridge.py::run_manifest_ingest_bridge", "Research ingest", "research", "aura_research_ingest_bridge.py", "run_manifest_ingest_bridge", [1, 1], root, status="normal"),
        _node("test_aura_empirical_software_lab.py::test_score_candidate", "Regression test", "test", "test_aura_empirical_software_lab.py", "test_score_candidate", [1, 1], root, status="normal"),
    ]
    links = [
        ArenaLink("aura_router.py::AutoRouter", "aura_context_crusher.py::apply_context_crush_to_prompt", "routes_to", 0.8).to_dict(),
        ArenaLink("aura_research_ingest_bridge.py::run_manifest_ingest_bridge", "aura_empirical_software_lab.py::score_candidate", "feeds", 0.7).to_dict(),
        ArenaLink("test_aura_empirical_software_lab.py::test_score_candidate", "aura_empirical_software_lab.py::score_candidate", "tested_by", 0.9).to_dict(),
        ArenaLink("aura_router.py::AutoRouter", "aura_empirical_software_lab.py::score_candidate", "candidate_missing_route", 0.2, status="missing", label="Intentional missing edge").to_dict(),
    ]
    return {
        "version": ARENA_TOPOLOGY_VERSION,
        "source": "offline_demo",
        "reason": reason,
        "nodes": [node.to_dict() for node in nodes],
        "links": links,
        "meta": {
            "repo_root": str(root),
            "raw_repo_tokens": 50000,
            "codemap_tokens_est": 50000,
            "demo": True,
            "truth_policy": "Exact local topology is authoritative; visual graph is a human interface.",
        },
        "warnings": [],
    }


def _topology_from_codemap(root: Path, codemap: dict[str, Any], *, node_limit: int) -> dict[str, Any]:
    files = [item for item in codemap.get("files", []) or [] if isinstance(item, dict)]
    topology_index = codemap.get("topology", {}).get("file_index", {})
    if not isinstance(topology_index, dict):
        topology_index = {}
    py_files = [item for item in files if str(item.get("path", "")).endswith(".py")]
    py_files = sorted(
        py_files,
        key=lambda item: (
            -int((topology_index.get(str(item.get("path", "")), {}) or {}).get("degree") or item.get("topology", {}).get("degree") or 0),
            str(item.get("path", "")),
        ),
    )[:DEFAULT_FILE_LIMIT]
    selected_files = {str(item.get("path", "")) for item in py_files if item.get("path")}
    nodes: dict[str, ArenaNode] = {}
    links: list[dict[str, Any]] = []
    for item in py_files:
        path = str(item.get("path") or "")
        if not path:
            continue
        node_id = f"{path}::global_scope"
        nodes[node_id] = _node(
            node_id,
            Path(path).name,
            _node_type_for_path(path, ""),
            path,
            "global_scope",
            [1, int(item.get("lines") or 1)],
            root,
            tokens_est=int(item.get("tokens_est") or 0),
            metadata={
                "role": item.get("role"),
                "codemap_match": True,
                "digest8": item.get("digest8"),
                "degree": (topology_index.get(path, {}) or {}).get("degree") or item.get("topology", {}).get("degree", 0),
            },
        )
    symbol_index = codemap.get("symbol_index", {})
    symbol_nodes = 0
    if isinstance(symbol_index, dict):
        for symbol, occurrences in sorted(symbol_index.items()):
            if symbol_nodes >= DEFAULT_SYMBOL_LIMIT or len(nodes) >= node_limit:
                break
            if not isinstance(occurrences, list):
                continue
            for occ in occurrences:
                if symbol_nodes >= DEFAULT_SYMBOL_LIMIT or len(nodes) >= node_limit:
                    break
                if not isinstance(occ, dict):
                    continue
                file_path = str(occ.get("file") or "")
                if file_path not in selected_files:
                    continue
                kind = str(occ.get("kind") or "").lower()
                if "class" in kind:
                    node_type = "class"
                elif "method" in kind:
                    node_type = "method"
                elif "function" in kind or "def" in kind:
                    node_type = "function"
                else:
                    continue
                node_type = _node_type_for_path(file_path, symbol, fallback=node_type)
                node_id = f"{file_path}::{symbol}"
                if node_id in nodes:
                    continue
                nodes[node_id] = _node(
                    node_id,
                    symbol,
                    node_type,
                    file_path,
                    symbol,
                    [int(occ.get("line") or 0), int(occ.get("end_line") or occ.get("line") or 0)],
                    root,
                    metadata={
                        "codemap_match": True,
                        "semantic_id": occ.get("semantic_id", ""),
                        "signature_hash": occ.get("signature_hash", ""),
                    },
                )
                links.append(ArenaLink(f"{file_path}::global_scope", node_id, "contains", 1.0).to_dict())
                symbol_nodes += 1
    for path in sorted(selected_files):
        source_id = f"{path}::global_scope"
        topo = topology_index.get(path, {}) or {}
        for neighbor in list(topo.get("neighbor_files", []) or [])[:20]:
            neighbor = str(neighbor)
            target_id = f"{neighbor}::global_scope"
            if source_id in nodes and target_id in nodes:
                links.append(ArenaLink(source_id, target_id, "depends_on", 0.45).to_dict())
        if Path(path).name.startswith("test_"):
            target = Path(path).name[5:]
            for candidate in (target, target.replace("test_", "")):
                target_id = f"{candidate}::global_scope"
                if target_id in nodes:
                    links.append(ArenaLink(source_id, target_id, "tested_by", 0.9).to_dict())
    graph_nodes = list(nodes.values())
    meta = codemap.get("summary", {}) if isinstance(codemap.get("summary"), dict) else {}
    graph = {
        "version": ARENA_TOPOLOGY_VERSION,
        "source": "codemap",
        "nodes": [node.to_dict() for node in graph_nodes],
        "links": _dedupe_links(links),
        "meta": {
            "repo_root": str(root),
            "raw_repo_tokens": int(meta.get("text_tokens_est") or meta.get("tokens_est") or 0),
            "codemap_tokens_est": int(meta.get("text_tokens_est") or 0),
            "codemap_file_count": len(files),
            "projected_file_count": len(selected_files),
            "projected_symbol_count": symbol_nodes,
            "node_limit": node_limit,
            "demo": False,
            "truth_policy": "Exact local topology/CODEMAP/AST facts are authoritative; visual graph is a human interface.",
        },
        "warnings": [],
    }
    graph["meta"]["topology_tokens_est"] = _estimate_tokens_json({"nodes": graph["nodes"], "links": graph["links"]})
    return graph


def _node(
    node_id: str,
    label: str,
    node_type: str,
    file_path: str,
    symbol: str,
    line_range: list[int],
    root: Path,
    *,
    status: str = "normal",
    tokens_est: int = 0,
    metadata: dict[str, Any] | None = None,
) -> ArenaNode:
    x, y, z = _coords(node_id)
    meta = dict(metadata or {})
    meta.setdefault("exists", _safe_repo_path(root, file_path).exists() if file_path else False)
    return ArenaNode(
        id=node_id,
        label=label,
        node_type=node_type,
        file_path=file_path,
        symbol=symbol,
        kind=node_type,
        line_range=[int(line_range[0] or 0), int(line_range[1] or 0)] if line_range else [],
        tokens_est=tokens_est,
        status=status,
        color=NODE_COLORS.get(node_type, NODE_COLORS["demo"]),
        x=x,
        y=y,
        z=z,
        metadata=meta,
    )


def _node_type_for_path(path: str, symbol: str, *, fallback: str = "file") -> str:
    text = f"{path} {symbol}".lower()
    name = Path(path).name.lower()
    if name.startswith("test_") or "/tests/" in f"/{path}".replace("\\", "/").lower():
        return "test"
    if any(term in text for term in ("router", "routing", "fst")):
        return "router"
    if any(term in text for term in ("context", "compression", "compress", "topological")):
        return "context"
    if any(term in text for term in ("research", "ingest", "arxiv")):
        return "research"
    if any(term in text for term in ("verify", "verifier", "guard", "test_gap")):
        return "verifier"
    return fallback


def _normalize_graph(topology: dict[str, Any]) -> dict[str, Any]:
    nodes = [dict(node) for node in topology.get("nodes", []) or [] if isinstance(node, dict)]
    links = [dict(link) for link in topology.get("links", topology.get("edges", [])) or [] if isinstance(link, dict)]
    node_by_id = {str(node.get("id")): node for node in nodes if node.get("id")}
    node_order = [str(node.get("id")) for node in nodes if node.get("id")]
    clean_links = []
    for link in links:
        source = str(link.get("source") or link.get("sourceId") or "")
        target = str(link.get("target") or link.get("targetId") or "")
        if source in node_by_id and target in node_by_id:
            link["source"] = source
            link["target"] = target
            clean_links.append(link)
    return {"nodes": nodes, "links": clean_links, "node_by_id": node_by_id, "node_order": node_order}


def _neighbors_by_direction(graph: dict[str, Any], selected: list[str], direction: str) -> list[dict[str, Any]]:
    selected_set = set(selected)
    output = []
    for link in graph["links"]:
        source = str(link.get("source", ""))
        target = str(link.get("target", ""))
        if direction == "out" and source in selected_set and target in graph["node_by_id"]:
            output.append(_neighbor_record(graph["node_by_id"][target], link))
        elif direction == "in" and target in selected_set and source in graph["node_by_id"]:
            output.append(_neighbor_record(graph["node_by_id"][source], link))
    return _dedupe_records(output, "id")


def _neighbor_record(node: dict[str, Any], link: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id"),
        "file_path": node.get("file_path", ""),
        "symbol": node.get("symbol", ""),
        "node_type": node.get("node_type", node.get("type", "")),
        "edge_type": link.get("link_type", link.get("type", "related")),
        "status": link.get("status", "known"),
    }


def _test_neighbors(graph: dict[str, Any], selected: list[str]) -> list[str]:
    tests: list[str] = []
    for record in [*_neighbors_by_direction(graph, selected, "in"), *_neighbors_by_direction(graph, selected, "out")]:
        node_type = str(record.get("node_type", ""))
        file_path = str(record.get("file_path", ""))
        edge_type = str(record.get("edge_type", ""))
        if node_type == "test" or edge_type == "tested_by" or Path(file_path).name.startswith("test_"):
            tests.append(file_path or str(record.get("id", "")))
    for node_id in selected:
        node = graph["node_by_id"].get(node_id, {})
        file_path = str(node.get("file_path", ""))
        if file_path and not Path(file_path).name.startswith("test_"):
            direct = f"test_{Path(file_path).name}"
            if any(str(candidate.get("file_path")) == direct for candidate in graph["nodes"]):
                tests.append(direct)
    return _unique(item for item in tests if item)


def _degree_maps(links: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    incoming: dict[str, list[dict[str, Any]]] = {}
    outgoing: dict[str, list[dict[str, Any]]] = {}
    for link in links:
        source = str(link.get("source", ""))
        target = str(link.get("target", ""))
        if not source or not target:
            continue
        incoming.setdefault(target, []).append(link)
        outgoing.setdefault(source, []).append(link)
    return incoming, outgoing


def _neighbor_text(graph: dict[str, Any], selected: list[str]) -> list[str]:
    records = [*_neighbors_by_direction(graph, selected, "in"), *_neighbors_by_direction(graph, selected, "out")]
    return [" ".join(str(value) for value in record.values()) for record in records]


def _operation_from_instruction(instruction: str) -> str:
    lowered = str(instruction or "").lower()
    if any(term in lowered for term in ("patch", "fix", "wire", "connect", "send to worker")):
        return "PATCH_OR_ROUTE"
    if any(term in lowered for term in ("test", "verify")):
        return "VERIFY_OR_TEST_GAP"
    return "INSPECT_OR_ROUTE"


def _attach_jspace_capsule_state(capsule: dict[str, Any], topology: dict[str, Any]) -> dict[str, Any]:
    if attach_jspace_to_capsule is None:
        return capsule
    try:
        from aura_fst_routing import AuraCodingArenaRouter, RoutingFrame

        frame = _jspace_routing_frame_from_capsule(capsule, topology, RoutingFrame)
        decision = AuraCodingArenaRouter().route(frame)
        return attach_jspace_to_capsule(capsule, frame=frame, decision=decision)
    except Exception:
        return attach_jspace_to_capsule(capsule)


def _jspace_routing_frame_from_capsule(capsule: dict[str, Any], topology: dict[str, Any], frame_cls: Any) -> Any:
    context = capsule.get("context", {}) if isinstance(capsule.get("context"), dict) else {}
    target_files = list(context.get("target_files", []) or [])
    target_symbols = list(context.get("target_symbols", []) or [])
    tests = list(context.get("tests", []) or [])
    op = str(capsule.get("op") or "")
    instruction = str(capsule.get("human_instruction") or "")
    lowered = f"{op} {instruction}".lower()
    target_file = str(target_files[0]) if target_files else ""
    grounding: list[str] = []
    if target_files:
        grounding.append("file_exists")
    if target_symbols:
        grounding.append("symbol_exists")
    if tests:
        grounding.append("tests_exist")
    if (
        "codemap" in str(capsule.get("truth_policy", "")).lower()
        or str(topology.get("source", "")).lower() == "codemap"
        or context.get("line_ranges")
    ):
        grounding.append("codemap_grounded")
    if {"file_exists", "symbol_exists", "tests_exist", "codemap_grounded"} <= set(grounding):
        grounding.append("full")
    action = "modify" if any(term in lowered for term in ("patch", "fix", "wire", "connect")) else "verify" if any(term in lowered for term in ("test", "verify")) else "inspect"
    intent = "code_refactor" if action == "modify" else "verify" if action == "verify" else "localize"
    return frame_cls(
        intent=intent,
        artifact=_jspace_artifact_for_file(target_file),
        action=action,
        scope="symbol" if target_symbols else "file" if target_files else "repo",
        risk="medium",
        grounding=tuple(grounding or ["none"]),
        tests="existing" if tests else "none",
        quality="verifier_required",
        cost="local_first",
        target_file=target_file or None,
        target_symbol=str(target_symbols[0]) if target_symbols else None,
    )


def _jspace_artifact_for_file(path: str) -> str:
    name = str(path or "")
    if name.endswith(".py") and Path(name).name.startswith("test_"):
        return "test_file"
    if name.endswith(".py") or not name:
        return "python_module"
    if name.endswith((".md", ".rst", ".txt")):
        return "documentation"
    return "python_module"


def _path_exists_in_topology(topology: dict[str, Any], path: str) -> bool:
    if not path:
        return False
    root = Path(topology.get("meta", {}).get("repo_root", ".")).resolve()
    return _safe_repo_path(root, path).exists()


def _safe_repo_path(root: Path, rel_path: str) -> Path:
    normalized = str(rel_path or "").replace("\\", "/").lstrip("/")
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return root / "__aura_rejected_path__"
    return candidate


def _sanitize_instruction(text: str) -> str:
    raw = str(text or "")[:1000]
    if sanitize_tokenizer_channels is None:
        return raw
    return sanitize_tokenizer_channels(raw).sanitized_text


def _estimate_tokens_json(payload: Any) -> int:
    return _estimate_tokens(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))


def _estimate_tokens(text: str) -> int:
    return max(1, (len(str(text or "")) + 3) // 4)


def _pct_saved(baseline: int, candidate: int) -> float:
    if baseline <= 0:
        return 0.0
    return round(max(0.0, min(100.0, (1.0 - candidate / baseline) * 100.0)), 2)


def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _coords(node_id: str) -> tuple[float, float, float]:
    digest = hashlib.blake2b(str(node_id).encode("utf-8"), digest_size=12).digest()
    coords = []
    for index in range(3):
        chunk = digest[index * 4 : index * 4 + 4]
        value = int.from_bytes(chunk, "big") / 0xFFFFFFFF
        coords.append(round((value * 2.0 - 1.0) * 180.0, 4))
    return coords[0], coords[1], coords[2]


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _unique(values: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    output: list[Any] = []
    for value in values:
        if value in (None, ""):
            continue
        key = repr(value)
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _dedupe_records(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output = []
    for record in records:
        value = str(record.get(key, ""))
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(record)
    return output


def _dedupe_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    output: list[dict[str, Any]] = []
    for link in links:
        key = (
            str(link.get("source", "")),
            str(link.get("target", "")),
            str(link.get("link_type", link.get("type", ""))),
            str(link.get("status", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(link)
    return output


def _dedupe_faults(faults: list[WiringFault]) -> list[WiringFault]:
    seen: set[tuple[str, str]] = set()
    output = []
    for fault in faults:
        key = (fault.kind, fault.node_id)
        if key in seen:
            continue
        seen.add(key)
        output.append(fault)
    return output
