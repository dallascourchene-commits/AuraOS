#!/usr/bin/env python3
"""Verify closure of a selective WorkCapsule re-entry plan.

O8 decides the minimum dependency-class scope to reopen. O9 preserves source
identity across rejected currentness. This module answers the next lifecycle
question: when may that re-entry be considered closed without silently changing
unaffected context?

Closure is deliberately conservative. The post-reentry candidate must itself be
an admitted O7 binding. Dependency membership and roles cannot change here;
that requires a higher owner. Previously retained CURRENT ACTIVE sources must
remain byte/generation-identical. A SELECTED_SOURCES closure must keep graph
identity unchanged. A FULL_GRAPH closure may re-establish the same graph
identity or a new one, but it still grants no semantic/review/effect authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, verify_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_invalidation import (
    FULL_GRAPH,
    NONE,
    SELECTED_SOURCES,
    verify_reentry_invalidation,
)

VERSION = "AURA_WORKCAPSULE_REENTRY_CLOSURE_V1"
CLOSED = "CLOSED"
HOLD = "HOLD"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_REENTRY_CLOSURE_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _key(row: dict[str, Any]) -> tuple[int, str]:
    return int(row["file_id"]), str(row["relative_path"])


def _binding_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        left.get(field) == right.get(field)
        for field in ("file_id", "relative_path", "role", "source_generation", "source_sha256", "source_byte_len")
    )


def _graph_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        left.get(field) == right.get(field)
        for field in ("graph_id", "graph_generation", "graph_basis_identity")
    )


def compile_reentry_closure(
    *,
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    candidate_binding: dict[str, Any],
) -> dict[str, Any]:
    """Emit CLOSED only when the O8 re-entry consequence is exactly discharged."""
    previous_violations = verify_workcapsule_context_binding(previous_binding)
    if previous_violations:
        raise ValueError("previous_binding is not coherent: " + ",".join(previous_violations))
    candidate_violations = verify_workcapsule_context_binding(candidate_binding)
    if candidate_violations:
        raise ValueError("candidate_binding is not coherent: " + ",".join(candidate_violations))
    reentry_violations = verify_reentry_invalidation(reentry_receipt)
    if reentry_violations:
        raise ValueError("reentry_receipt is not coherent: " + ",".join(reentry_violations))
    if previous_binding.get("context_admitted") is not True:
        raise ValueError("previous_binding must be admitted")
    if candidate_binding.get("context_admitted") is not True:
        raise ValueError("candidate_binding must independently re-establish admitted CURRENT context")
    if reentry_receipt.get("previous_binding_identity") != previous_binding.get("binding_identity"):
        raise ValueError("reentry_receipt does not bind the supplied previous_binding")
    if candidate_binding.get("capsule") != previous_binding.get("capsule"):
        raise ValueError("candidate_binding changed capsule identity/basis outside re-entry owner")

    scope = str(reentry_receipt["minimum_reentry_scope"])
    reasons: list[str] = []

    previous_rows = previous_binding["source_witnesses"]
    candidate_rows = candidate_binding["source_witnesses"]
    previous_by_key = {_key(row): row for row in previous_rows}
    candidate_by_key = {_key(row): row for row in candidate_rows}

    previous_membership = {(key, str(row["role"])) for key, row in previous_by_key.items()}
    candidate_membership = {(key, str(row["role"])) for key, row in candidate_by_key.items()}
    if candidate_membership != previous_membership:
        reasons.append("DEPENDENCY_MEMBERSHIP_OR_ROLE_CHANGED")

    selected_keys = {
        (int(row["file_id"]), str(row["relative_path"]))
        for row in reentry_receipt.get("minimum_reentry_source_keys", [])
    }
    retained_keys = {
        (int(row["file_id"]), str(row["relative_path"]))
        for row in reentry_receipt.get("retained_current_active_sources", [])
    }

    for key in sorted(retained_keys):
        prior = previous_by_key.get(key)
        candidate = candidate_by_key.get(key)
        if prior is None or candidate is None or not _binding_equal(prior, candidate):
            reasons.append(f"RETAINED_ACTIVE_SOURCE_CHANGED:{key[0]}:{key[1]}")

    for key in sorted(selected_keys):
        candidate = candidate_by_key.get(key)
        if candidate is None:
            reasons.append(f"SELECTED_SOURCE_NOT_REBOUND:{key[0]}:{key[1]}")
            continue
        if candidate.get("role") != ACTIVE or candidate.get("currentness") != CURRENT:
            reasons.append(f"SELECTED_SOURCE_NOT_CURRENT_ACTIVE:{key[0]}:{key[1]}")

    previous_graph = previous_binding["graph_witness"]
    candidate_graph = candidate_binding["graph_witness"]
    if scope in {NONE, SELECTED_SOURCES} and not _graph_equal(previous_graph, candidate_graph):
        reasons.append("GRAPH_CHANGED_OUTSIDE_FULL_GRAPH_REENTRY")
    if candidate_graph.get("currentness") != CURRENT:
        reasons.append("CANDIDATE_GRAPH_NOT_CURRENT")

    # NONE means no ACTIVE dependency required re-entry. Candidate may contain a
    # changed COLD frontier, but graph and ACTIVE source basis must be invariant.
    if scope == NONE:
        for key, prior in sorted(previous_by_key.items()):
            if prior["role"] != ACTIVE:
                continue
            candidate = candidate_by_key.get(key)
            if candidate is None or not _binding_equal(prior, candidate):
                reasons.append(f"ACTIVE_SOURCE_CHANGED_WITH_NONE_SCOPE:{key[0]}:{key[1]}")

    # A selected-source plan cannot close if O8 still had unresolved selected
    # identity whose key is not present in the candidate. Presence/currentness
    # above discharges identity once a higher owner has rebound the same key.
    unresolved_keys = {
        (
            int(row["prior"]["file_id"]),
            str(row["prior"]["relative_path"]),
        )
        for row in reentry_receipt.get("unresolved_active_sources", [])
        if isinstance(row, dict) and isinstance(row.get("prior"), dict)
    }
    for key in sorted(unresolved_keys):
        if key not in candidate_by_key:
            reasons.append(f"UNRESOLVED_ACTIVE_IDENTITY_NOT_DISCHARGED:{key[0]}:{key[1]}")

    status = CLOSED if not reasons else HOLD
    payload: dict[str, Any] = {
        "version": VERSION,
        "closure_status": status,
        "minimum_reentry_scope": scope,
        "previous_binding_identity": previous_binding["binding_identity"],
        "reentry_receipt_identity": reentry_receipt["receipt_identity"],
        "candidate_binding_identity": candidate_binding["binding_identity"],
        "selected_source_keys": [
            {"file_id": file_id, "relative_path": path} for file_id, path in sorted(selected_keys)
        ],
        "retained_active_source_keys": [
            {"file_id": file_id, "relative_path": path} for file_id, path in sorted(retained_keys)
        ],
        "closure_reasons": reasons,
        "dependency_membership_preserved": candidate_membership == previous_membership,
        "unaffected_active_basis_preserved": not any(
            reason.startswith("RETAINED_ACTIVE_SOURCE_CHANGED")
            or reason.startswith("ACTIVE_SOURCE_CHANGED_WITH_NONE_SCOPE")
            for reason in reasons
        ),
        "graph_identity_preserved_when_required": not any(
            reason == "GRAPH_CHANGED_OUTSIDE_FULL_GRAPH_REENTRY" for reason in reasons
        ),
        "candidate_context_independently_current": candidate_binding["context_admitted"] is True,
        "source_to_graph_dependency_map_proven": False,
        "node_level_dependency_cone_proven": False,
        "authority": {
            "semantic_truth_minted": False,
            "review_authorized": False,
            "mutation_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }
    payload["receipt_identity"] = _identity(payload)
    return payload


def verify_reentry_closure(receipt: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if receipt.get("version") != VERSION:
        violations.append("UNSUPPORTED_VERSION")
    status = receipt.get("closure_status")
    reasons = receipt.get("closure_reasons")
    if status not in {CLOSED, HOLD}:
        violations.append("INVALID_CLOSURE_STATUS")
    if not isinstance(reasons, list):
        violations.append("MALFORMED_CLOSURE_REASONS")
        reasons = []
    if status == CLOSED and reasons:
        violations.append("CLOSED_WITH_UNRESOLVED_REASONS")
    if status == HOLD and not reasons:
        violations.append("HOLD_WITHOUT_REASON")
    if receipt.get("source_to_graph_dependency_map_proven") is not False:
        violations.append("UNPROVEN_SOURCE_GRAPH_MAP_PROMOTED")
    if receipt.get("node_level_dependency_cone_proven") is not False:
        violations.append("UNPROVEN_NODE_CONE_PROMOTED")
    authority = receipt.get("authority")
    if not isinstance(authority, dict) or any(bool(value) for value in authority.values()):
        violations.append("AUTHORITY_MINTED_BY_REENTRY_CLOSURE")
    supplied = receipt.get("receipt_identity")
    without = dict(receipt)
    without.pop("receipt_identity", None)
    if supplied != _identity(without):
        violations.append("RECEIPT_IDENTITY_MISMATCH")
    return violations
