"""
Aura Capability Genome Resolver — grounded capability discovery before invention.

Composes (not replaces) existing Aura systems to answer:
  - What already exists for this objective?
  - Which exact functions, tests, docs, commands relate to it?
  - Which capability lanes, plugins, and agent tools cover it?
  - What should be reused?
  - What is genuinely missing?

Sources composed:
  1. CODEMAP files and symbol index
  2. CODEMAP command index
  3. Topology neighbors
  4. Module Manifest
  5. Affordance Directory
  6. Capability Connectome
  7. Capability Lane Registry
  8. Plugin Registry
  9. Concept Workspace
  10. Node Inspector
  11. Agent Arena Bridge tools

Dependencies: stdlib only at module level. All Aura imports are lazy.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
RESOLVER_VERSION = "AURA_CAPABILITY_RESOLUTION_V1"

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "to", "for", "of", "in", "on", "and", "or",
    "with", "by", "from", "that", "this", "it", "as", "at", "be",
})

_CODEMAP_CACHE: dict[str, tuple[float, dict]] = {}
_CODEMAP_TTL = 120.0


def _load_codemap(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".aura" / "CODEMAP.json"
    key = str(path)
    now = time.time()
    if key in _CODEMAP_CACHE:
        ts, data = _CODEMAP_CACHE[key]
        if now - ts < _CODEMAP_TTL:
            return data
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CODEMAP_CACHE[key] = (now, data)
        return data
    except Exception:
        return {}


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip().lstrip("./")


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _objective_hash(objective: str) -> str:
    return hashlib.blake2b(objective.encode(), digest_size=12).hexdigest()


def _codemap_digest(codemap: dict) -> str:
    summary = codemap.get("summary", {})
    payload = json.dumps({
        "file_count": summary.get("file_count", 0),
        "topology_nodes": summary.get("topology_nodes", 0),
        "topology_source": summary.get("topology_source", "unknown"),
    }, sort_keys=True)
    return hashlib.blake2b(payload.encode(), digest_size=8).hexdigest()


def resolve_capabilities(
    objective: str,
    *,
    target_files: list[str] | None = None,
    target_symbols: list[str] | None = None,
    selected_node_ids: list[str] | None = None,
    repo_root: str | Path = ".",
    top_k: int = 12,
    token_budget: int = 2400,
) -> dict[str, Any]:
    """Resolve capabilities for an objective from Aura's shared substrate.

    Returns a CapabilityResolutionPacket with exact matches, related functions,
    existing affordances, capability lanes, reuse plan, and missing capabilities.
    """
    root = Path(repo_root).resolve()
    codemap = _load_codemap(root)
    keywords = _extract_keywords(objective)
    obj_hash = _objective_hash(objective)

    # --- Topology health ---
    from aura_topology_health import topology_health_packet
    topo_health = topology_health_packet(repo_root=root)

    # --- Exact matches from CODEMAP ---
    si = codemap.get("symbol_index", {})
    exact_matches: list[dict[str, Any]] = []
    related_functions: list[dict[str, Any]] = []
    tests: list[str] = []
    docs: list[str] = []
    commands: list[str] = []

    # Target files/symbols first (exact)
    if target_files:
        for fp in target_files[:top_k]:
            fp_norm = _normalize_path(fp)
            exact_matches.append({
                "file": fp_norm, "symbol": None, "kind": "file",
                "line_start": None, "line_end": None,
                "digest8": None, "semantic_id": None, "signature_hash": None,
                "relationship": "exact_target", "grounding_class": "EXACT",
            })

    if target_symbols:
        for sym in target_symbols[:top_k]:
            occ = si.get(sym, [])
            if occ and isinstance(occ[0], dict):
                hit = occ[0]
                exact_matches.append({
                    "file": _normalize_path(hit.get("file", "")),
                    "symbol": sym, "kind": hit.get("kind", "function"),
                    "line_start": hit.get("line"), "line_end": hit.get("end_line"),
                    "digest8": hit.get("digest8"), "semantic_id": hit.get("semantic_id"),
                    "signature_hash": hit.get("signature_hash"),
                    "relationship": "exact_target", "grounding_class": "EXACT",
                })
            else:
                exact_matches.append({
                    "file": None, "symbol": sym, "kind": "unresolved",
                    "line_start": None, "line_end": None,
                    "digest8": None, "semantic_id": None, "signature_hash": None,
                    "relationship": "target_not_found", "grounding_class": "UNRESOLVED",
                })

    # Keyword-matched symbols
    for sym_name, occurrences in si.items():
        if len(related_functions) >= top_k:
            break
        sym_lower = sym_name.lower()
        if any(kw in sym_lower for kw in keywords):
            for occ in occurrences[:1]:
                if isinstance(occ, dict):
                    fp = _normalize_path(occ.get("file", ""))
                    related_functions.append({
                        "file": fp, "symbol": sym_name,
                        "relationship": "keyword_match",
                        "line_range": [occ.get("line", 0), occ.get("end_line", 0)],
                        "tests": [], "docs": [], "commands": [],
                        "risk": "low", "grounding_class": "EXACT",
                    })
                    # Check for tests
                    stem = Path(fp).stem if fp else ""
                    test_candidates = [f"test_{stem}.py", f"tests/test_{stem}.py"]
                    files = codemap.get("files", [])
                    file_paths = {str(f.get("path", "")) for f in files if isinstance(f, dict)} if isinstance(files, list) else set()
                    for tc in test_candidates:
                        if tc in file_paths:
                            tests.append(tc)

    # Command index
    ci = codemap.get("command_index", {})
    for cmd_name in ci:
        cmd_lower = cmd_name.lower()
        if any(kw in cmd_lower for kw in keywords):
            commands.append(cmd_name)

    # --- Affordances ---
    existing_affordances: list[dict[str, Any]] = []
    try:
        from aura_affordance_directory import find_affordances
        aff_result = find_affordances(objective, repo_root=root, top_k=7)
        existing_affordances = aff_result.get("recommended_affordances", [])
    except Exception:
        pass

    # --- Capability lanes ---
    capability_lanes: list[dict[str, Any]] = []
    try:
        from aura_capability_lane_registry import load_capability_lanes
        for lane in load_capability_lanes():
            lane_lower = (lane.lane_id + " " + lane.name + " " + lane.purpose).lower()
            if any(kw in lane_lower for kw in keywords):
                capability_lanes.append({
                    "lane_id": lane.lane_id, "name": lane.name,
                    "purpose": lane.purpose[:100],
                    "advisory_only": lane.advisory_only,
                })
    except Exception:
        pass

    # --- Plugin organs ---
    plugin_organs: list[dict[str, Any]] = []
    try:
        from aura_cockpit_plugin_registration import list_registered_plugins
        plugin_result = list_registered_plugins(repo_root=root)
        plugin_organs = plugin_result.get("plugins", [])
    except Exception:
        pass

    # --- Agent tools ---
    agent_tools: list[dict[str, Any]] = []
    try:
        from aura_agent_workbench_interface import list_agent_actions
        agent_tools = list_agent_actions()
    except Exception:
        pass

    # --- Read-slice commands ---
    read_slice_commands: list[str] = []
    for match in exact_matches[:3]:
        if match.get("file") and match.get("symbol"):
            read_slice_commands.append(
                f"python -m aura_agent_arena_cli read-slice --file {match['file']} --symbol {match['symbol']}"
            )
    for rel in related_functions[:3]:
        if rel.get("file") and rel.get("symbol"):
            read_slice_commands.append(
                f"python -m aura_agent_arena_cli read-slice --file {rel['file']} --symbol {rel['symbol']}"
            )

    # --- Reuse plan ---
    reuse_plan: list[dict[str, Any]] = []
    do_not_reinvent: list[str] = []
    for aff in existing_affordances[:5]:
        reuse_plan.append({
            "capability_id": aff.get("id", ""),
            "name": aff.get("name", ""),
            "action": "reuse",
            "implemented_by": aff.get("implemented_by", []),
        })
        do_not_reinvent.append(
            f"Do not reinvent: {aff.get('name', '')} ({aff.get('id', '')}) "
            f"already handles this. Use: {', '.join(aff.get('implemented_by', [])[:2])}."
        )

    # --- Missing capabilities ---
    missing_capabilities: list[dict[str, Any]] = []
    # Check if topology is degraded
    if topo_health.get("topology_nodes", 0) == 0:
        missing_capabilities.append({
            "capability": "topology_graph",
            "status": "degraded",
            "reason": "Topology has 0 nodes. Graph-based operations unavailable.",
            "impact": "Change graph, refactor candidate detection, and visual topology blocked.",
        })

    # --- Confidence ---
    confidence = 0.0
    if exact_matches:
        confidence += 0.4
    if related_functions:
        confidence += 0.3
    if existing_affordances:
        confidence += 0.2
    if capability_lanes:
        confidence += 0.1
    confidence = min(1.0, confidence)

    # --- Token budget enforcement ---
    # Estimate packet size and trim if over budget
    estimated_tokens = len(json.dumps({
        "exact_matches": exact_matches, "related_functions": related_functions,
        "existing_affordances": existing_affordances, "capability_lanes": capability_lanes,
    }, default=str)) // 4
    if estimated_tokens > token_budget:
        # Trim to fit budget
        max_items = max(1, token_budget // 200)
        exact_matches = exact_matches[:max_items]
        related_functions = related_functions[:max_items]
        existing_affordances = existing_affordances[:max_items]
        capability_lanes = capability_lanes[:max_items]

    # --- Module manifest hash ---
    module_manifest_hash = ""
    try:
        from aura_module_manifest import load_module_manifest
        manifest = load_module_manifest(root)
        module_manifest_hash = hashlib.blake2b(
            json.dumps(manifest, sort_keys=True, default=str).encode(), digest_size=8
        ).hexdigest()
    except Exception:
        pass

    return {
        "version": RESOLVER_VERSION,
        "objective": objective,
        "objective_hash": obj_hash,
        "codemap_digest": _codemap_digest(codemap),
        "module_manifest_hash": module_manifest_hash,
        "topology_health": {
            "topology_nodes": topo_health.get("topology_nodes", 0),
            "topology_edges": topo_health.get("topology_edges", 0),
            "topology_source": topo_health.get("topology_source", "unknown"),
            "next_gate": topo_health.get("next_gate", ""),
        },
        "exact_matches": exact_matches,
        "related_functions": related_functions,
        "existing_affordances": existing_affordances,
        "capability_lanes": capability_lanes,
        "plugin_organs": plugin_organs,
        "agent_tools": agent_tools,
        "commands": commands[:10],
        "tests": tests[:10],
        "docs": docs[:10],
        "reuse_plan": reuse_plan,
        "do_not_reinvent": do_not_reinvent,
        "missing_capabilities": missing_capabilities,
        "recommended_arena_nodes": [],
        "recommended_arena_edges": [],
        "read_slice_commands": read_slice_commands[:5],
        "confidence": round(confidence, 2),
        "truth_boundary": {
            "exact_source": "exact source spans, hashes, CODEMAP facts, tests, verifier gates",
            "advisory": "VSA, DREAM, JSpace, ST3GG, summaries, semantic similarity",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        },
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
