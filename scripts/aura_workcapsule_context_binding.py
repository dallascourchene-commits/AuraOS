#!/usr/bin/env python3
"""Witness-preserving context binding for WorkCapsuleV2 2.1.0.

This module is a compatibility membrane, not a WorkCapsule owner and not a
source/graph currentness owner. It consumes upstream currentness witnesses and
serializes the minimum execution-context slice needed by WorkCapsuleV2 while
preserving CURRENT / STALE / UNKNOWN and fail-closing active hydration.

It grants no review, mutation, execution, promotion, or human authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

VERSION = "AURA_WORKCAPSULE_CONTEXT_BINDING_V1"
WORKCAPSULE_SCHEMA_ID = "WorkCapsuleV2"
WORKCAPSULE_SCHEMA_VERSION = "2.1.0"
CURRENT = "CURRENT"
STALE = "STALE"
UNKNOWN = "UNKNOWN"
ACTIVE = "ACTIVE"
COLD = "COLD"
CURRENTNESS = {CURRENT, STALE, UNKNOWN}
ROLES = {ACTIVE, COLD}


def _text(value: Any, *, field: str) -> str:
    out = str(value or "").strip()
    if not out:
        raise ValueError(f"{field} must be nonempty")
    return out


def _uint(value: Any, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be an integer >= 0")
    return value


def _sha256(value: Any, *, field: str) -> str:
    out = str(value or "").strip().lower()
    if len(out) != 64 or any(ch not in "0123456789abcdef" for ch in out):
        raise ValueError(f"{field} must be a 64-character SHA-256 hex digest")
    return out


def _currentness(value: Any, *, field: str) -> str:
    out = _text(value, field=field)
    if out not in CURRENTNESS:
        raise ValueError(f"{field} must be CURRENT, STALE, or UNKNOWN")
    return out


def _typed_identity(raw: Any, *, field: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError(f"{field} must be an object")
    required = (
        "kind",
        "algorithm_or_provider",
        "canonicalization_profile",
        "scope_profile",
        "value",
        "schema_version",
    )
    return {name: _text(raw.get(name), field=f"{field}.{name}") for name in required}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _binding_identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_CONTEXT_BINDING_V1_FULL_PAYLOAD_EXCEPT_BINDING_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def compile_workcapsule_context_binding(
    *,
    capsule: dict[str, Any],
    graph_witness: dict[str, Any],
    source_witnesses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compile a derived WorkCapsule context slice without minting upstream truth.

    Active context is admitted only if the graph witness and every ACTIVE source
    witness are CURRENT. COLD witnesses are retained as reopen state but never
    counted as hydrated active context. Any active STALE/UNKNOWN witness prevents
    current admission while preserving the exact reason and witness identity.
    """
    if not isinstance(capsule, dict):
        raise ValueError("capsule must be an object")
    if not isinstance(graph_witness, dict):
        raise ValueError("graph_witness must be an object")
    if not isinstance(source_witnesses, list):
        raise ValueError("source_witnesses must be a list")

    capsule_id = _text(capsule.get("capsule_id"), field="capsule.capsule_id")
    capsule_generation = _uint(
        capsule.get("capsule_generation"), field="capsule.capsule_generation"
    )
    parent_binding_generation = _uint(
        capsule.get("parent_work_order_interface_binding_generation"),
        field="capsule.parent_work_order_interface_binding_generation",
    )
    execution_basis_identity = _typed_identity(
        capsule.get("execution_basis_identity"), field="capsule.execution_basis_identity"
    )

    graph = {
        "graph_id": _text(graph_witness.get("graph_id"), field="graph_witness.graph_id"),
        "graph_generation": _uint(
            graph_witness.get("graph_generation"), field="graph_witness.graph_generation"
        ),
        "graph_basis_identity": _typed_identity(
            graph_witness.get("graph_basis_identity"),
            field="graph_witness.graph_basis_identity",
        ),
        "currentness": _currentness(
            graph_witness.get("currentness"), field="graph_witness.currentness"
        ),
        "witness_ref": _text(
            graph_witness.get("witness_ref"), field="graph_witness.witness_ref"
        ),
    }

    normalized_sources: list[dict[str, Any]] = []
    seen_file_ids: set[int] = set()
    seen_paths: set[str] = set()
    for index, raw in enumerate(source_witnesses):
        if not isinstance(raw, dict):
            raise ValueError(f"source_witnesses[{index}] must be an object")
        role = _text(raw.get("role"), field=f"source_witnesses[{index}].role")
        if role not in ROLES:
            raise ValueError(f"source_witnesses[{index}].role must be ACTIVE or COLD")
        file_id = _uint(raw.get("file_id"), field=f"source_witnesses[{index}].file_id")
        relative_path = _text(
            raw.get("relative_path"), field=f"source_witnesses[{index}].relative_path"
        )
        if file_id in seen_file_ids:
            raise ValueError(f"duplicate source file_id: {file_id}")
        if relative_path in seen_paths:
            raise ValueError(f"duplicate source relative_path: {relative_path}")
        seen_file_ids.add(file_id)
        seen_paths.add(relative_path)
        normalized_sources.append(
            {
                "role": role,
                "file_id": file_id,
                "relative_path": relative_path,
                "source_generation": _uint(
                    raw.get("source_generation"),
                    field=f"source_witnesses[{index}].source_generation",
                ),
                "source_sha256": _sha256(
                    raw.get("source_sha256"), field=f"source_witnesses[{index}].source_sha256"
                ),
                "source_byte_len": _uint(
                    raw.get("source_byte_len"),
                    field=f"source_witnesses[{index}].source_byte_len",
                ),
                "currentness": _currentness(
                    raw.get("currentness"),
                    field=f"source_witnesses[{index}].currentness",
                ),
                "witness_ref": _text(
                    raw.get("witness_ref"), field=f"source_witnesses[{index}].witness_ref"
                ),
            }
        )

    normalized_sources.sort(key=lambda row: (row["role"], row["file_id"], row["relative_path"]))
    active = [row for row in normalized_sources if row["role"] == ACTIVE]
    active_not_current = [row for row in active if row["currentness"] != CURRENT]

    reasons: list[str] = []
    if graph["currentness"] != CURRENT:
        reasons.append(f"GRAPH_{graph['currentness']}")
    for row in active_not_current:
        reasons.append(f"ACTIVE_SOURCE_{row['file_id']}_{row['currentness']}")
    if not active:
        reasons.append("NO_ACTIVE_SOURCE_WITNESSES")

    context_admitted = not reasons
    if context_admitted:
        binding_status = CURRENT
    elif graph["currentness"] == STALE or any(
        row["currentness"] == STALE for row in active_not_current
    ):
        binding_status = STALE
    else:
        binding_status = "NEEDS_REBIND"

    payload: dict[str, Any] = {
        "version": VERSION,
        "workcapsule_schema_id": WORKCAPSULE_SCHEMA_ID,
        "workcapsule_schema_version": WORKCAPSULE_SCHEMA_VERSION,
        "owner_mode": "DERIVED_EXECUTION_VIEW_COMPATIBILITY_MEMBRANE",
        "capsule": {
            "capsule_id": capsule_id,
            "capsule_generation": capsule_generation,
            "parent_work_order_interface_binding_generation": parent_binding_generation,
            "execution_basis_identity": execution_basis_identity,
        },
        "graph_witness": graph,
        "source_witnesses": normalized_sources,
        "active_source_count": len(active),
        "cold_source_count": len(normalized_sources) - len(active),
        "context_admitted": context_admitted,
        "binding_status": binding_status,
        "reason_codes": reasons or ["EXACT_CURRENT_GRAPH_AND_ACTIVE_SOURCE_WITNESSES"],
        "authority": {
            "semantic_truth_minted": False,
            "review_authorized": False,
            "mutation_authorized": False,
            "execution_authorized": False,
            "promotion_authorized": False,
            "human_authority": False,
        },
        "invalidation": {
            "graph_generation_change_forces_rebind": True,
            "graph_basis_identity_change_forces_rebind": True,
            "active_source_generation_change_forces_rebind": True,
            "active_source_digest_change_forces_rebind": True,
            "unknown_or_stale_active_source_admitted": False,
            "cold_source_is_active_context": False,
        },
    }
    payload["binding_identity"] = _binding_identity(payload)
    return payload


def verify_workcapsule_context_binding(binding: dict[str, Any]) -> list[str]:
    """Return deterministic violations; an empty list means the membrane is coherent."""
    violations: list[str] = []
    if binding.get("version") != VERSION:
        violations.append("UNSUPPORTED_VERSION")
    if binding.get("workcapsule_schema_id") != WORKCAPSULE_SCHEMA_ID:
        violations.append("WRONG_WORKCAPSULE_SCHEMA_ID")
    if binding.get("workcapsule_schema_version") != WORKCAPSULE_SCHEMA_VERSION:
        violations.append("WRONG_WORKCAPSULE_SCHEMA_VERSION")

    graph = binding.get("graph_witness")
    sources = binding.get("source_witnesses")
    authority = binding.get("authority")
    if not isinstance(graph, dict) or not isinstance(sources, list) or not isinstance(authority, dict):
        return violations + ["MALFORMED_BINDING"]

    active = [row for row in sources if isinstance(row, dict) and row.get("role") == ACTIVE]
    expected_admitted = bool(active) and graph.get("currentness") == CURRENT and all(
        row.get("currentness") == CURRENT for row in active
    )
    if binding.get("context_admitted") is not expected_admitted:
        violations.append("ACTIVE_CURRENTNESS_LAUNDERING")
    if any(bool(value) for value in authority.values()):
        violations.append("AUTHORITY_MINTED_BY_CONTEXT_BINDING")

    supplied_identity = binding.get("binding_identity")
    without_identity = dict(binding)
    without_identity.pop("binding_identity", None)
    expected_identity = _binding_identity(without_identity)
    if supplied_identity != expected_identity:
        violations.append("BINDING_IDENTITY_MISMATCH")
    return violations


def roundtrip_binding(binding: dict[str, Any]) -> dict[str, Any]:
    """Canonical serialize + deserialize used by tests and future runtime adapters."""
    return json.loads(_canonical_bytes(binding).decode("utf-8"))
