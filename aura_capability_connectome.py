"""
Aura Capability Connectome — living graph of Aura's internal capabilities.

Builds a graph where each node is an Aura-native capability (from the Affordance
Directory) and edges connect related capabilities. Each node carries metadata
about purpose, when to use, token savings role, truth boundary, future potentials,
and risks.

This is an advisory/orientation layer — never patch authority.

Dependencies: stdlib only (json, pathlib, re, typing, dataclasses, time).
All Aura imports are lazy (inside functions, wrapped in try/except).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants and invariants
# ---------------------------------------------------------------------------

CONNECTOME_VERSION = "AURA_CAPABILITY_CONNECTOME_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# Token savings role classification by capability tags/keywords.
_TOKEN_SAVINGS_ROLE_MAP = {
    "context_crusher": "compression",
    "context": "compression",
    "compress": "compression",
    "crush": "compression",
    "st3gg": "compression",
    "egress": "compression",
    "codemap": "localization",
    "search": "localization",
    "concept": "localization",
    "workspace": "localization",
    "node_inspector": "localization",
    "inspect": "localization",
    "ai_router": "localization",
    "router": "routing",
    "fst": "routing",
    "routing": "routing",
    "jspace": "routing",
    "intent": "routing",
    "verify": "verification",
    "test": "verification",
    "quality_gate": "verification",
    "patch_quality": "verification",
    "agent_arena": "grounding",
    "bridge": "grounding",
    "grounding": "grounding",
    "architect": "grounding",
    "tokenizer_guard": "safety",
    "guard": "safety",
    "sanitiz": "safety",
    "dream": "advisory",
    "rerank": "advisory",
    "qdkt": "advisory",
    "memory": "advisory",
    "emergent": "advisory",
    "understand_graph": "advisory",
    "research": "advisory",
    "llm_egress": "context_reduction",
}

# Truth boundary classification.
_TRUTH_BOUNDARY_EXACT = frozenset({
    "grounding", "verification", "bridge", "architect",
})
_TRUTH_BOUNDARY_ADVISORY = frozenset({
    "routing", "compression", "advisory", "context_reduction", "localization", "safety",
})

# LEXC slot mapping by token savings role.
_LEXC_SLOT_MAP = {
    "routing": ["DIR", "ASP"],
    "localization": ["CLASS", "SUBJ"],
    "compression": ["STEM"],
    "verification": ["VOICE"],
    "grounding": ["CLASS", "SUBJ"],
    "safety": ["VOICE"],
    "advisory": ["DIR"],
    "context_reduction": ["STEM"],
}

# Routing frame examples by role.
_ROUTING_FRAME_EXAMPLES = {
    "routing": {"intent": "code_refactor", "action": "modify", "scope": "symbol", "route": "BUILDER_PATCH"},
    "localization": {"intent": "localize", "action": "inspect", "scope": "symbol", "route": "LOCALIZE_FIRST"},
    "compression": {"intent": "code_refactor", "action": "modify", "scope": "symbol", "route": "BUILDER_PATCH"},
    "verification": {"intent": "verify", "action": "verify", "scope": "symbol", "route": "VERIFY_ONLY"},
    "grounding": {"intent": "code_refactor", "action": "modify", "scope": "symbol", "route": "BUILDER_PATCH"},
    "safety": {"intent": "verify", "action": "verify", "scope": "symbol", "route": "VERIFY_ONLY"},
    "advisory": {"intent": "research_rank", "action": "rank", "scope": "subsystem", "route": "PLAN_ONLY"},
    "context_reduction": {"intent": "code_refactor", "action": "modify", "scope": "symbol", "route": "BUILDER_PATCH"},
}

# Future potential templates by role.
_FUTURE_POTENTIALS = {
    "routing": [
        "Integrate with external agent routing (Hermes, Codex, Fireworks).",
        "Support multi-model orchestration and failover.",
        "Add thermal-aware VSA-weighted transition updates.",
    ],
    "localization": [
        "Add semantic similarity search beyond keyword matching.",
        "Support cross-repository topology navigation.",
        "Integrate with external code intelligence APIs.",
    ],
    "compression": [
        "Add WASM-accelerated compression for large payloads.",
        "Support streaming compression for real-time agent handoff.",
        "Integrate with model-specific tokenizer-aware compression.",
    ],
    "verification": [
        "Add property-based test generation.",
        "Support mutation testing for patch quality assessment.",
        "Integrate with CI/CD pipeline gates.",
    ],
    "grounding": [
        "Add cross-repository grounding for monorepo support.",
        "Support runtime grounding with live system introspection.",
        "Integrate with external static analysis tools.",
    ],
    "safety": [
        "Add prompt injection detection.",
        "Support adversarial input sanitization.",
        "Integrate with security scanning pipelines.",
    ],
    "advisory": [
        "Add cross-session pattern crystallization.",
        "Support federated learning for retrieval ranking.",
        "Integrate with external research paper databases.",
    ],
    "context_reduction": [
        "Add model-specific token budget optimization.",
        "Support progressive context loading for long conversations.",
        "Integrate with external context window management APIs.",
    ],
}

# Risk templates by role.
_RISK_TEMPLATES = {
    "routing": "Routing decisions may not account for runtime constraints. Always verify with grounding.",
    "localization": "Localization may miss files not in CODEMAP. Refresh CODEMAP after writes.",
    "compression": "Compression may lose information. Verify essential context is preserved.",
    "verification": "Verification is only as good as the test suite. Ensure tests cover edge cases.",
    "grounding": "Grounding depends on CODEMAP accuracy. Stale CODEMAP may produce false grounding.",
    "safety": "Safety checks may not cover all attack vectors. Combine with human review.",
    "advisory": "Advisory layers are never patch authority. Do not act on advisory recommendations without grounding.",
    "context_reduction": "Context reduction may remove information needed for edge cases. Monitor for regressions.",
}


# ---------------------------------------------------------------------------
# CODEMAP loader (lightweight, cached)
# ---------------------------------------------------------------------------

_CODEMAP_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
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
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _CODEMAP_CACHE[key] = (now, data)
        return data
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def _classify_token_savings_role(aff: Any) -> str:
    """Classify a capability's token savings role from its tags and id."""
    tags_lower = set()
    id_lower = ""
    name_lower = ""
    if hasattr(aff, "tags"):
        tags_lower = {t.lower() for t in aff.tags}
        id_lower = (aff.id or "").lower()
        name_lower = (aff.name or "").lower()
    elif isinstance(aff, dict):
        tags_lower = {t.lower() for t in aff.get("tags", [])}
        id_lower = (aff.get("id", "") or "").lower()
        name_lower = (aff.get("name", "") or "").lower()

    # Check id first (most specific)
    for keyword, role in _TOKEN_SAVINGS_ROLE_MAP.items():
        if keyword in id_lower:
            return role

    # Check tags
    for tag in tags_lower:
        for keyword, role in _TOKEN_SAVINGS_ROLE_MAP.items():
            if keyword in tag:
                return role

    # Check name
    for keyword, role in _TOKEN_SAVINGS_ROLE_MAP.items():
        if keyword in name_lower:
            return role

    return "advisory"


def _classify_truth_boundary(role: str) -> str:
    """Classify the truth boundary for a token savings role."""
    if role in _TRUTH_BOUNDARY_EXACT:
        return "exact_source"
    return "advisory"


def _get_lexc_slots(role: str) -> list[str]:
    """Get LEXC slots for a token savings role."""
    return list(_LEXC_SLOT_MAP.get(role, ["DIR"]))


def _get_routing_frame_example(role: str) -> dict[str, Any]:
    """Get a routing frame example for a token savings role."""
    return dict(_ROUTING_FRAME_EXAMPLES.get(role, {
        "intent": "explain", "action": "inspect", "scope": "symbol", "route": "PLAN_ONLY",
    }))


def _get_future_potentials(role: str, aff: Any) -> list[str]:
    """Get future potentials for a capability."""
    base = list(_FUTURE_POTENTIALS.get(role, []))
    # Add related-affordance-based potentials
    related = []
    if hasattr(aff, "related_affordances"):
        related = aff.related_affordances
    elif isinstance(aff, dict):
        related = aff.get("related_affordances", [])
    if related:
        base.append(f"Compose with {', '.join(related[:3])} for multi-capability workflows.")
    return base


def _get_risks(role: str) -> str:
    """Get risk description for a token savings role."""
    return _RISK_TEMPLATES.get(role, "Advisory layer — never patch authority.")


# ---------------------------------------------------------------------------
# Node builder
# ---------------------------------------------------------------------------


def _build_node(aff: Any) -> dict[str, Any]:
    """Build a capability connectome node from an affordance."""
    if hasattr(aff, "to_dict"):
        aff_dict = aff.to_dict()
    elif isinstance(aff, dict):
        aff_dict = dict(aff)
    else:
        aff_dict = {}

    role = _classify_token_savings_role(aff)
    truth_boundary = _classify_truth_boundary(role)
    lexc_slots = _get_lexc_slots(role)
    routing_example = _get_routing_frame_example(role)
    future_potentials = _get_future_potentials(role, aff)
    risks = _get_risks(role)

    return {
        "id": aff_dict.get("id", ""),
        "name": aff_dict.get("name", ""),
        "purpose": aff_dict.get("description", ""),
        "when_to_use": aff_dict.get("when_to_use", ""),
        "when_not_to_use": aff_dict.get("when_not_to_use", ""),
        "implemented_by": aff_dict.get("implemented_by", []),
        "symbols": aff_dict.get("symbols", []),
        "tests": aff_dict.get("tests", []),
        "docs": aff_dict.get("docs", []),
        "related_capabilities": aff_dict.get("related_affordances", []),
        "lexc_slots_if_known": lexc_slots,
        "routing_frame_examples": routing_example,
        "token_savings_role": role,
        "truth_boundary": truth_boundary,
        "future_potentials": future_potentials,
        "risks": risks,
        "grounding": aff_dict.get("grounding", "NEEDS_GROUNDING"),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_capability_connectome(repo_root: str | Path = ".") -> dict[str, Any]:
    """Build the full capability graph from the Affordance Directory + CODEMAP.

    Returns:
        Dict with ok, nodes, edges, node_count, edge_count, and invariants.
    """
    root = Path(repo_root).resolve()

    # Load affordances
    affordances: list[Any] = []
    try:
        from aura_affordance_directory import load_affordance_directory
        affordances = load_affordance_directory(root)
    except Exception:
        pass

    # Build nodes
    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for aff in affordances:
        node = _build_node(aff)
        if node["id"]:
            nodes.append(node)
            node_ids.add(node["id"])

    # Build edges from related_affordances
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()
    for node in nodes:
        source_id = node["id"]
        for target_id in node.get("related_capabilities", []):
            if target_id in node_ids and target_id != source_id:
                edge_key = (source_id, target_id)
                if edge_key not in seen_edges:
                    edges.append({
                        "source": source_id,
                        "target": target_id,
                        "type": "related",
                    })
                    seen_edges.add(edge_key)

    # Enrich with CODEMAP facts
    codemap = _load_codemap(root)
    codemap_files = set()
    if isinstance(codemap.get("files"), list):
        codemap_files = {str(f.get("path", "")) for f in codemap["files"] if isinstance(f, dict)}
    elif isinstance(codemap.get("files"), dict):
        codemap_files = set(codemap["files"].keys())

    for node in nodes:
        implemented = node.get("implemented_by", [])
        node["codemap_verified_files"] = [f for f in implemented if f in codemap_files]
        node["codemap_unverified_files"] = [f for f in implemented if f not in codemap_files]

    return {
        "ok": True,
        "version": CONNECTOME_VERSION,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def find_capability_path(
    objective: str,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Find the path through capabilities for an objective.

    Uses the Affordance Directory to rank capabilities, then traces
    related-capability edges to build a recommended path.
    """
    root = Path(repo_root).resolve()

    # Get recommended affordances
    recommended: list[dict[str, Any]] = []
    try:
        from aura_affordance_directory import find_affordances
        result = find_affordances(objective, repo_root=root, top_k=7)
        recommended = result.get("recommended_affordances", [])
    except Exception:
        pass

    # Build path from recommended capabilities
    path: list[str] = []
    path_details: list[dict[str, Any]] = []
    token_savings_roles: list[str] = []

    for rec in recommended:
        cap_id = rec.get("id", "")
        if cap_id and cap_id not in path:
            path.append(cap_id)
            role = _classify_token_savings_role(rec)
            token_savings_roles.append(role)
            path_details.append({
                "id": cap_id,
                "name": rec.get("name", ""),
                "token_savings_role": role,
                "score": rec.get("score", 0),
            })

    return {
        "ok": True,
        "version": CONNECTOME_VERSION,
        "objective": objective,
        "path": path,
        "recommended_capabilities": path_details,
        "token_savings_roles": token_savings_roles,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def explain_capability(
    capability_id: str,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Explain a single capability in detail."""
    connectome = build_capability_connectome(repo_root)
    for node in connectome.get("nodes", []):
        if node.get("id") == capability_id:
            return {
                "ok": True,
                "version": CONNECTOME_VERSION,
                "capability": node,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
    return {
        "ok": False,
        "error": f"Capability not found: {capability_id}",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def future_potentials_for_capability(
    capability_id: str,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Return future potentials for a capability."""
    result = explain_capability(capability_id, repo_root)
    if not result.get("ok"):
        return result
    cap = result.get("capability", {})
    return {
        "ok": True,
        "version": CONNECTOME_VERSION,
        "capability_id": capability_id,
        "future_potentials": cap.get("future_potentials", []),
        "related_capabilities": cap.get("related_capabilities", []),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def token_savings_for_capability(
    capability_id: str,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Return the token savings role of a capability."""
    result = explain_capability(capability_id, repo_root)
    if not result.get("ok"):
        return result
    cap = result.get("capability", {})
    role = cap.get("token_savings_role", "advisory")
    return {
        "ok": True,
        "version": CONNECTOME_VERSION,
        "capability_id": capability_id,
        "token_savings_role": role,
        "truth_boundary": cap.get("truth_boundary", "advisory"),
        "lexc_slots": cap.get("lexc_slots_if_known", []),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def capability_graph_packet(repo_root: str | Path = ".") -> dict[str, Any]:
    """Return a compact packet form of the connectome."""
    connectome = build_capability_connectome(repo_root)
    capabilities: list[dict[str, Any]] = []
    for node in connectome.get("nodes", []):
        capabilities.append({
            "id": node.get("id", ""),
            "name": node.get("name", ""),
            "token_savings_role": node.get("token_savings_role", ""),
            "truth_boundary": node.get("truth_boundary", ""),
            "grounding": node.get("grounding", ""),
        })
    return {
        "ok": True,
        "version": CONNECTOME_VERSION,
        "nodes_count": connectome.get("node_count", 0),
        "edges_count": connectome.get("edge_count", 0),
        "capabilities": capabilities,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
