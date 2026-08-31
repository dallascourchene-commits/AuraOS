#!/usr/bin/env python3
"""Bind host-observation evidence to one exact current recursive raw-slice target.

Parent #562 owns the local current recursive target/raw-slice relation. Parent #559 owns
local-temporal -> host-observation admission. This child does not copy or re-execute #559's
lower temporal owner chain. It re-proves #562, integrity-checks one serialized #559 admission
receipt, and requires every resolved host gate to name the deterministic target reference of
that exact #562 consequence.

The bridge is evidence-only. Receipt integrity is not producer authentication; UNKNOWN remains
UNKNOWN; even all host gates PASS does not grant continuation/effect/merge authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_current_recursive_target_raw_slice_binding import (
    admit_current_recursive_target_raw_slice_binding,
    verify_current_recursive_target_raw_slice_binding,
)

VERSION = "AURA_WORKCAPSULE_ARTIFACT_QUALIFIED_HOST_OBSERVATION_V1"
HOST_VERSION = "AURA_WORKCAPSULE_TEMPORAL_HOST_OBSERVATION_ADMISSION_V1"
GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})
LOCAL_PREFIX = "LOCAL_ARTIFACT_"
HOST_PREFIX = "HOST_ADMISSION_"
TARGET_REF_MISMATCH = "RESOLVED_HOST_GATE_TARGET_REF_MISMATCH"

_HOST_FIELDS = {
    "version", "disposition", "local_temporal_closure_proven", "pre_closure_status",
    "post_closure_status", "exact_hold_to_closed_transition", "pre_reentry_receipt_identity",
    "post_closure_receipt_identity", "host_gate_states", "host_gate_resolutions",
    "host_gate_reasons", "fail_mask", "unknown_mask", "candidate_probes_by_unknown_gate",
    "ordered_required_probes", "minimum_cover_computed", "minimum_cover_reason",
    "host_observation_set_complete", "resolver_trust_proven_by_this_module",
    "host_observation_authority_proven_by_this_module", "local_evidence_promoted_to_host_rank",
    "drive_pointer_presence_promoted_to_pass", "cache_or_coordinate_presence_promoted_to_pass",
    "trusted_continuation_ready", "host_effect_ready", "source_currentness_minted",
    "semantic_repair_correctness_minted", "producer_identity_authenticated", "authority",
    "receipt_identity",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def artifact_target_ref(local_receipt: dict[str, Any]) -> str:
    """Deterministic reference to the complete #562 consequence; not semantic authority."""
    return "aura-workcapsule-target-sha256:" + _sha256(local_receipt)


def verify_host_admission_envelope(receipt: dict[str, Any]) -> list[str]:
    """Check #559 receipt integrity/ceiling only; do not re-prove its temporal/host owner."""
    if not isinstance(receipt, dict) or set(receipt) != _HOST_FIELDS:
        return ["MALFORMED_HOST_ADMISSION_ENVELOPE"]
    violations: list[str] = []
    if receipt.get("version") != HOST_VERSION:
        violations.append("HOST_VERSION_MISMATCH")
    if receipt.get("local_temporal_closure_proven") is not True:
        violations.append("LOCAL_TEMPORAL_CLOSURE_NOT_PROVEN")
    if receipt.get("pre_closure_status") != "HOLD" or receipt.get("post_closure_status") != "CLOSED":
        violations.append("TEMPORAL_STATUS_MISMATCH")
    if receipt.get("exact_hold_to_closed_transition") is not True:
        violations.append("TEMPORAL_TRANSITION_NOT_EXACT")

    states = receipt.get("host_gate_states")
    resolutions = receipt.get("host_gate_resolutions")
    if not isinstance(states, dict) or set(states) != set(GATES):
        violations.append("HOST_GATE_STATE_SET_MISMATCH")
        states = {}
    if not isinstance(resolutions, dict) or set(resolutions) != set(GATES):
        violations.append("HOST_GATE_RESOLUTION_SET_MISMATCH")
        resolutions = {}
    for gate in GATES:
        state = states.get(gate)
        if state not in STATES:
            violations.append("HOST_GATE_STATE_INVALID:" + gate)
        resolution = resolutions.get(gate)
        if state == "UNKNOWN" and resolution is not None:
            violations.append("UNKNOWN_GATE_HAS_RESOLUTION:" + gate)
        if state in {"PASS", "FAIL"} and not isinstance(resolution, dict):
            violations.append("RESOLVED_GATE_MISSING_RESOLUTION:" + gate)

    for field in (
        "resolver_trust_proven_by_this_module", "host_observation_authority_proven_by_this_module",
        "local_evidence_promoted_to_host_rank", "drive_pointer_presence_promoted_to_pass",
        "cache_or_coordinate_presence_promoted_to_pass", "trusted_continuation_ready",
        "host_effect_ready", "source_currentness_minted", "semantic_repair_correctness_minted",
        "producer_identity_authenticated",
    ):
        if receipt.get(field) is not False:
            violations.append("HOST_CEILING_VIOLATED:" + field)
    authority = receipt.get("authority")
    if not isinstance(authority, dict) or any(bool(value) for value in authority.values()):
        violations.append("HOST_AUTHORITY_NOT_FALSE")

    identity = receipt.get("receipt_identity")
    if not isinstance(identity, dict):
        violations.append("HOST_RECEIPT_IDENTITY_MISSING")
    else:
        if identity.get("kind") != "DIGEST" or identity.get("algorithm_or_provider") != "sha256":
            violations.append("HOST_RECEIPT_IDENTITY_PROFILE_INVALID")
        supplied = identity.get("value")
        expected_payload = {key: value for key, value in receipt.items() if key != "receipt_identity"}
        if not isinstance(supplied, str) or supplied != _sha256(expected_payload):
            violations.append("HOST_RECEIPT_IDENTITY_MISMATCH")
    return list(dict.fromkeys(violations))


def verify_artifact_qualified_host_observation(
    *,
    scoped_target_inputs: dict[str, Any],
    higher_owner_projection: dict[str, Any],
    raw_slice_receipt: dict[str, Any],
    host_admission_receipt: dict[str, Any],
) -> list[str]:
    """Require every resolved host gate to concern the exact #562 target consequence."""
    local_violations = verify_current_recursive_target_raw_slice_binding(
        scoped_target_inputs=scoped_target_inputs,
        higher_owner_projection=higher_owner_projection,
        raw_slice_receipt=raw_slice_receipt,
    )
    violations = [LOCAL_PREFIX + item for item in local_violations]
    host_violations = verify_host_admission_envelope(host_admission_receipt)
    violations.extend(HOST_PREFIX + item for item in host_violations)
    if violations:
        return list(dict.fromkeys(violations))

    local = admit_current_recursive_target_raw_slice_binding(
        scoped_target_inputs=scoped_target_inputs,
        higher_owner_projection=higher_owner_projection,
        raw_slice_receipt=raw_slice_receipt,
    )
    expected_ref = artifact_target_ref(local)
    states = host_admission_receipt["host_gate_states"]
    resolutions = host_admission_receipt["host_gate_resolutions"]
    for gate in GATES:
        if states[gate] in {"PASS", "FAIL"}:
            resolution = resolutions[gate]
            if resolution.get("target_ref") != expected_ref:
                violations.append(f"{TARGET_REF_MISMATCH}:{gate}")
    return list(dict.fromkeys(violations))


def admit_artifact_qualified_host_observation(**kwargs: Any) -> dict[str, Any]:
    violations = verify_artifact_qualified_host_observation(**kwargs)
    if violations:
        raise ValueError("artifact-qualified host observation failed: " + ",".join(violations))
    local = admit_current_recursive_target_raw_slice_binding(
        scoped_target_inputs=kwargs["scoped_target_inputs"],
        higher_owner_projection=kwargs["higher_owner_projection"],
        raw_slice_receipt=kwargs["raw_slice_receipt"],
    )
    host = kwargs["host_admission_receipt"]
    states = dict(host["host_gate_states"])
    resolved = [gate for gate in GATES if states[gate] in {"PASS", "FAIL"}]
    unknown = [gate for gate in GATES if states[gate] == "UNKNOWN"]
    target_ref = artifact_target_ref(local)
    return {
        "version": VERSION,
        "current_recursive_raw_target_reproved": True,
        "artifact_target_ref": target_ref,
        "host_admission_integrity_checked": True,
        "host_admission_reproved_by_child": False,
        "host_admission_producer_authenticated": False,
        "resolved_host_gates_bound_to_exact_artifact": True,
        "resolved_host_gate_count": len(resolved),
        "resolved_host_gates": resolved,
        "unknown_host_gates": unknown,
        "host_gate_states": states,
        "host_observation_set_complete": bool(host["host_observation_set_complete"]),
        "all_host_gates_pass_for_exact_artifact": all(states[gate] == "PASS" for gate in GATES),
        "target_slice_sha256_hex": local["target_slice_sha256_hex"],
        "target_slice_byte_len": local["target_slice_byte_len"],
        "dependency_key": dict(local["dependency_key"]),
        "source_generation": local["source_generation"],
        "full_source_sha256_hex": local["full_source_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": local["selected_target_semantic_handle_digest_hex"],
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_repair_correctness_proven": False,
        "producer_authenticated": False,
        "authority": {
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
