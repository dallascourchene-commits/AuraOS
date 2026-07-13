"""Stable digest and execution-trait enrichment for Aura's Capability Connectome.

This module is intentionally a pure compatibility layer. It enriches V1 graph and
path packets without granting patch, route, model, or policy authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from aura_model_cognome import stable_digest

CONNECTOME_ENRICHMENT_VERSION = "AURA_CAPABILITY_CONNECTOME_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

DETERMINISTIC_LOCAL = "DETERMINISTIC_LOCAL"
MODEL_DEPENDENT = "MODEL_DEPENDENT"
UNRESOLVED_EXECUTION = "UNRESOLVED_EXECUTION"

_MODEL_MARKERS = frozenset({
    "llm", "model", "fusion", "research", "dream", "rerank", "agent_handoff",
    "external_agent", "provider", "probe", "judge", "thinker", "worker",
})
_DETERMINISTIC_MARKERS = frozenset({
    "codemap", "topology", "concept_workspace", "node_inspector", "fst",
    "intent_routing", "tokenizer_guard", "quality_gate", "schema", "verify",
    "context_crusher", "st3gg", "capability_connectome", "capability_resolver",
})


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return [str(item) for item in value]
    return [str(value)]


def _stable_list(value: Any) -> list[str]:
    return sorted(dict.fromkeys(item for item in _strings(value) if item))


def _declared_execution(node: Mapping[str, Any]) -> tuple[str | None, dict[str, Any]]:
    traits = node.get("model_execution_traits")
    normalized_traits = dict(traits) if isinstance(traits, Mapping) else {}
    declared = node.get("execution_class") or normalized_traits.get("execution_class")
    if declared in {DETERMINISTIC_LOCAL, MODEL_DEPENDENT, UNRESOLVED_EXECUTION}:
        return str(declared), normalized_traits
    if normalized_traits.get("requires_model") is True:
        return MODEL_DEPENDENT, normalized_traits
    if normalized_traits.get("requires_model") is False:
        return DETERMINISTIC_LOCAL, normalized_traits
    return None, normalized_traits


def classify_execution(node: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    """Classify only strongly declared or strongly indicated execution needs.

    Ambiguous nodes remain unresolved so consequential routing fails closed.
    """
    declared, traits = _declared_execution(node)
    if declared is not None:
        return declared, traits

    searchable = " ".join(
        [
            str(node.get("id", "")),
            str(node.get("name", "")),
            str(node.get("purpose", "")),
            " ".join(_strings(node.get("implemented_by"))),
            " ".join(_strings(node.get("symbols"))),
        ]
    ).lower()
    model_hits = sorted(marker for marker in _MODEL_MARKERS if marker in searchable)
    deterministic_hits = sorted(marker for marker in _DETERMINISTIC_MARKERS if marker in searchable)

    if model_hits and not deterministic_hits:
        return MODEL_DEPENDENT, {
            **traits,
            "requires_model": True,
            "classification_basis": "strong_model_marker",
            "markers": model_hits,
        }
    if deterministic_hits and not model_hits:
        return DETERMINISTIC_LOCAL, {
            **traits,
            "requires_model": False,
            "classification_basis": "strong_deterministic_marker",
            "markers": deterministic_hits,
        }
    return UNRESOLVED_EXECUTION, {
        **traits,
        "requires_model": None,
        "classification_basis": "insufficient_or_conflicting_evidence",
        "model_markers": model_hits,
        "deterministic_markers": deterministic_hits,
    }


def _node_digest_payload(node: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(node.get("id", "")),
        "name": str(node.get("name", "")),
        "purpose": str(node.get("purpose", "")),
        "when_to_use": str(node.get("when_to_use", "")),
        "when_not_to_use": str(node.get("when_not_to_use", "")),
        "implemented_by": _stable_list(node.get("implemented_by")),
        "symbols": _stable_list(node.get("symbols")),
        "tests": _stable_list(node.get("tests")),
        "docs": _stable_list(node.get("docs")),
        "related_capabilities": _stable_list(node.get("related_capabilities")),
        "lexc_slots_if_known": _stable_list(node.get("lexc_slots_if_known")),
        "token_savings_role": str(node.get("token_savings_role", "")),
        "truth_boundary": str(node.get("truth_boundary", "")),
        "risks": node.get("risks", ""),
        "grounding": str(node.get("grounding", "")),
        "codemap_verified_files": _stable_list(node.get("codemap_verified_files")),
        "codemap_unverified_files": _stable_list(node.get("codemap_unverified_files")),
        "execution_class": str(node.get("execution_class", UNRESOLVED_EXECUTION)),
        "model_execution_traits": node.get("model_execution_traits", {}),
    }


def enrich_connectome(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Return a stable, digest-pinned copy of a V1 Connectome graph."""
    result = deepcopy(dict(graph))
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicate_ids: list[str] = []
    for raw in result.get("nodes", []) or []:
        if not isinstance(raw, Mapping):
            continue
        node = deepcopy(dict(raw))
        capability_id = str(node.get("id", "")).strip()
        if not capability_id:
            continue
        if capability_id in seen:
            duplicate_ids.append(capability_id)
            continue
        seen.add(capability_id)
        execution_class, traits = classify_execution(node)
        node["execution_class"] = execution_class
        node["model_execution_traits"] = traits
        node["node_digest"] = stable_digest(_node_digest_payload(node))
        nodes.append(node)
    nodes.sort(key=lambda item: str(item.get("id", "")))

    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for raw in result.get("edges", []) or []:
        if not isinstance(raw, Mapping):
            continue
        edge = {
            "source": str(raw.get("source", "")),
            "target": str(raw.get("target", "")),
            "type": str(raw.get("type", "related")),
        }
        key = (edge["source"], edge["target"], edge["type"])
        if not edge["source"] or not edge["target"] or key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append(edge)
    edges.sort(key=lambda item: (item["source"], item["target"], item["type"]))

    graph_payload = {
        "version": CONNECTOME_ENRICHMENT_VERSION,
        "nodes": [{"id": node["id"], "node_digest": node["node_digest"]} for node in nodes],
        "edges": edges,
    }
    result.update(
        {
            "ok": bool(result.get("ok", True)) and not duplicate_ids,
            "version": CONNECTOME_ENRICHMENT_VERSION,
            "source_version": graph.get("version", ""),
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "graph_digest": stable_digest(graph_payload),
            "duplicate_capability_ids": sorted(set(duplicate_ids)),
            "deterministic_capability_ids": [
                node["id"] for node in nodes if node["execution_class"] == DETERMINISTIC_LOCAL
            ],
            "model_dependent_capability_ids": [
                node["id"] for node in nodes if node["execution_class"] == MODEL_DEPENDENT
            ],
            "unresolved_execution_capability_ids": [
                node["id"] for node in nodes if node["execution_class"] == UNRESOLVED_EXECUTION
            ],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    )
    return result


def capability_node(graph: Mapping[str, Any], capability_id: str) -> dict[str, Any] | None:
    for node in graph.get("nodes", []) or []:
        if isinstance(node, Mapping) and node.get("id") == capability_id:
            return deepcopy(dict(node))
    return None


def enrich_path(path_packet: Mapping[str, Any], graph: Mapping[str, Any]) -> dict[str, Any]:
    """Bind a recommended path to exact Connectome nodes and graph digest."""
    result = deepcopy(dict(path_packet))
    graph_v2 = enrich_connectome(graph) if not graph.get("graph_digest") else deepcopy(dict(graph))
    requested = [str(item) for item in result.get("path", []) or [] if str(item)]
    details: list[dict[str, Any]] = []
    missing: list[str] = []
    for capability_id in requested:
        node = capability_node(graph_v2, capability_id)
        if node is None:
            missing.append(capability_id)
            continue
        details.append(
            {
                "id": capability_id,
                "name": node.get("name", ""),
                "node_digest": node.get("node_digest", ""),
                "purpose": node.get("purpose", ""),
                "implemented_by": _stable_list(node.get("implemented_by")),
                "symbols": _stable_list(node.get("symbols")),
                "tests": _stable_list(node.get("tests")),
                "docs": _stable_list(node.get("docs")),
                "risks": node.get("risks", ""),
                "truth_boundary": node.get("truth_boundary", "advisory"),
                "grounding": node.get("grounding", "NEEDS_GROUNDING"),
                "token_savings_role": node.get("token_savings_role", "advisory"),
                "execution_class": node.get("execution_class", UNRESOLVED_EXECUTION),
                "model_execution_traits": node.get("model_execution_traits", {}),
                "codemap_verified_files": _stable_list(node.get("codemap_verified_files")),
                "codemap_unverified_files": _stable_list(node.get("codemap_unverified_files")),
            }
        )

    admitted_ids = [item["id"] for item in details]
    result.update(
        {
            "ok": bool(result.get("ok", True)) and not missing,
            "version": CONNECTOME_ENRICHMENT_VERSION,
            "source_version": path_packet.get("version", ""),
            "path": admitted_ids,
            "required_capability_ids": admitted_ids,
            "path_details": details,
            "graph_digest": graph_v2.get("graph_digest", ""),
            "path_digest": stable_digest(
                {
                    "graph_digest": graph_v2.get("graph_digest", ""),
                    "nodes": [(item["id"], item["node_digest"]) for item in details],
                }
            ),
            "missing_capability_ids": missing,
            "implemented_by": sorted({path for item in details for path in item["implemented_by"]}),
            "symbols": sorted({symbol for item in details for symbol in item["symbols"]}),
            "tests": sorted({test for item in details for test in item["tests"]}),
            "docs": sorted({doc for item in details for doc in item["docs"]}),
            "truth_boundaries": sorted({str(item["truth_boundary"]) for item in details}),
            "risks": [item["risks"] for item in details if item["risks"]],
            "token_savings_roles": sorted({str(item["token_savings_role"]) for item in details}),
            "deterministic_capability_ids": [
                item["id"] for item in details if item["execution_class"] == DETERMINISTIC_LOCAL
            ],
            "model_dependent_capability_ids": [
                item["id"] for item in details if item["execution_class"] == MODEL_DEPENDENT
            ],
            "unresolved_execution_capability_ids": [
                item["id"] for item in details if item["execution_class"] == UNRESOLVED_EXECUTION
            ],
            "model_execution_requirements": [
                {"capability_id": item["id"], **dict(item["model_execution_traits"])}
                for item in details
                if item["execution_class"] == MODEL_DEPENDENT
            ],
            "has_unverified_files": any(item["codemap_unverified_files"] for item in details),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    )
    return result


def zero_model_eligibility(path_packet: Mapping[str, Any]) -> dict[str, Any]:
    unresolved = _stable_list(path_packet.get("unresolved_execution_capability_ids"))
    model_dependent = _stable_list(path_packet.get("model_dependent_capability_ids"))
    missing = _stable_list(path_packet.get("missing_capability_ids"))
    unverified = bool(path_packet.get("has_unverified_files"))
    eligible = not unresolved and not model_dependent and not missing and not unverified and bool(
        path_packet.get("required_capability_ids")
    )
    reasons: list[str] = []
    if unresolved:
        reasons.append("execution class unresolved: " + ", ".join(unresolved))
    if model_dependent:
        reasons.append("model-dependent capabilities required: " + ", ".join(model_dependent))
    if missing:
        reasons.append("capability IDs missing from graph: " + ", ".join(missing))
    if unverified:
        reasons.append("one or more implementation files are not CODEMAP-verified")
    if not path_packet.get("required_capability_ids"):
        reasons.append("no capability path was admitted")
    return {
        "eligible": eligible,
        "reasons": reasons,
        "graph_digest": path_packet.get("graph_digest", ""),
        "path_digest": path_packet.get("path_digest", ""),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
