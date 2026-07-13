"""Verifier-backed bridge between Aura's Capability Connectome and Model Cognome.

The bridge validates capability IDs and graph freshness before recording or using
model-capability evidence. It never grants patch, action, merge, or policy authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Protocol

from aura_capability_connectome_v2 import (
    MODEL_DEPENDENT,
    UNRESOLVED_EXECUTION,
    capability_node,
    enrich_connectome,
    zero_model_eligibility,
)
from aura_model_cognome import ModelCapabilityEdge, TaskContext

BRIDGE_VERSION = "AURA_MODEL_CONNECTOME_BRIDGE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class CognomeBridgeStore(Protocol):
    def upsert_model_capability_edge(self, edge: ModelCapabilityEdge) -> str: ...
    def query_candidates(self, context: TaskContext) -> list[dict[str, Any]]: ...
    def get_endpoint(self, profile_id: str) -> dict[str, Any] | None: ...


def current_connectome(repo_root: str | Path = ".") -> dict[str, Any]:
    from aura_capability_connectome import build_capability_connectome

    return enrich_connectome(build_capability_connectome(repo_root))


def validate_model_capability_edge(
    edge: ModelCapabilityEdge,
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    graph = current_connectome(repo_root)
    errors: list[str] = []
    node = capability_node(graph, edge.aura_capability_id)
    if node is None:
        errors.append(f"Capability ID is not present in the Connectome: {edge.aura_capability_id}")
    else:
        execution_class = str(node.get("execution_class", UNRESOLVED_EXECUTION))
        if execution_class != MODEL_DEPENDENT:
            errors.append(
                f"Capability {edge.aura_capability_id} is {execution_class}; "
                "model support evidence may only be attached to MODEL_DEPENDENT capabilities"
            )
        if node.get("codemap_unverified_files"):
            errors.append(
                f"Capability {edge.aura_capability_id} has CODEMAP-unverified implementation files"
            )
    if not graph.get("graph_digest"):
        errors.append("Capability Connectome graph has no stable digest")
    if edge.capability_graph_digest != graph.get("graph_digest"):
        errors.append("ModelCapabilityEdge capability_graph_digest is stale or mismatched")
    if edge.status == "VALIDATED":
        if edge.evidence_count <= 0:
            errors.append("VALIDATED edge requires evidence_count > 0")
        if not edge.evidence_digest:
            errors.append("VALIDATED edge requires evidence_digest")
        if edge.last_validated_at <= 0:
            errors.append("VALIDATED edge requires last_validated_at")
    return {
        "ok": not errors,
        "errors": errors,
        "edge_id": edge.edge_id,
        "profile_id": edge.profile_id,
        "capability_id": edge.aura_capability_id,
        "graph_digest": graph.get("graph_digest", ""),
        "node_digest": node.get("node_digest", "") if node else "",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def record_model_capability_edge(
    store: CognomeBridgeStore,
    edge: ModelCapabilityEdge,
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    if store.get_endpoint(edge.profile_id) is None:
        raise ValueError(f"Unknown Cognome profile: {edge.profile_id}")
    validation = validate_model_capability_edge(edge, repo_root=repo_root)
    if not validation["ok"]:
        raise ValueError("; ".join(validation["errors"]))
    edge_id = store.upsert_model_capability_edge(edge)
    return {
        "ok": True,
        "edge_id": edge_id,
        "profile_id": edge.profile_id,
        "capability_id": edge.aura_capability_id,
        "graph_digest": validation["graph_digest"],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def task_context_from_path(
    *,
    objective: str,
    purpose_digest: str,
    path_packet: Mapping[str, Any],
    **fields: Any,
) -> TaskContext:
    if not path_packet.get("ok"):
        raise ValueError("Cannot construct TaskContext from an invalid capability path")
    graph_digest = str(path_packet.get("graph_digest", ""))
    if not graph_digest:
        raise ValueError("Capability path must include graph_digest")
    required_ids = tuple(str(item) for item in path_packet.get("required_capability_ids", []) or [])
    if not required_ids:
        raise ValueError("Capability path must include required_capability_ids")
    defaults = {
        "required_capabilities": required_ids,
        "required_capability_ids": required_ids,
        "capability_path": tuple(str(item) for item in path_packet.get("path", []) or []),
        "capability_truth_boundaries": tuple(
            str(item) for item in path_packet.get("truth_boundaries", []) or []
        ),
        "capability_risks": tuple(str(item) for item in path_packet.get("risks", []) or []),
        "capability_tests": tuple(str(item) for item in path_packet.get("tests", []) or []),
        "capability_token_savings_roles": tuple(
            str(item) for item in path_packet.get("token_savings_roles", []) or []
        ),
    }
    defaults.update(fields)
    return TaskContext.create(
        objective=objective,
        purpose_digest=purpose_digest,
        capability_graph_digest=graph_digest,
        **defaults,
    )


def resolve_candidates_for_path(
    store: CognomeBridgeStore,
    context: TaskContext,
    path_packet: Mapping[str, Any],
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    graph = current_connectome(repo_root)
    errors: list[str] = []
    current_digest = str(graph.get("graph_digest", ""))
    packet_digest = str(path_packet.get("graph_digest", ""))
    if not current_digest:
        errors.append("Current Capability Connectome has no graph digest")
    if context.capability_graph_digest != current_digest:
        errors.append("TaskContext capability graph is stale")
    if packet_digest != current_digest:
        errors.append("Capability path packet is stale")
    path_ids = tuple(str(item) for item in path_packet.get("required_capability_ids", []) or [])
    if tuple(context.required_capability_ids) != path_ids:
        errors.append("TaskContext required capability IDs do not match the admitted path")
    missing = [capability_id for capability_id in path_ids if capability_node(graph, capability_id) is None]
    if missing:
        errors.append("Capability IDs missing from current graph: " + ", ".join(missing))
    unresolved = tuple(str(item) for item in path_packet.get("unresolved_execution_capability_ids", []) or [])
    if unresolved:
        errors.append("Execution class unresolved: " + ", ".join(unresolved))

    candidates: list[dict[str, Any]] = []
    if not errors:
        candidates = store.query_candidates(context)
    zero_model = zero_model_eligibility(path_packet)
    return {
        "ok": not errors,
        "errors": errors,
        "task_context_id": context.task_context_id,
        "graph_digest": current_digest,
        "path_digest": path_packet.get("path_digest", ""),
        "required_capability_ids": list(path_ids),
        "zero_model": zero_model,
        "model_candidates": candidates,
        "candidate_count": len(candidates),
        "status": "ADMITTED" if not errors else "DENIED",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
