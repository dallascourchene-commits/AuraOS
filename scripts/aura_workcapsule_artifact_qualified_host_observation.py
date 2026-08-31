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
HOST_RESOLUTION_SCHEMA = "AURA_HOST_OBSERVATION_RESOLUTION_V1"
HOST_RESOLUTION_VERSION = 1
GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")
GATE_INDEX = {gate: index for index, gate in enumerate(GATES)}
GATE_PROBES = {
    "U_HEAD": ("P_HEAD",),
    "U_ROUTE": ("P_ROUTE",),
    "U_F2": ("P_J",),
    "U_CUSTODY": ("P_CUSTODY", "P_ROUTE"),
    "U_CANARY": ("P_CANARY",),
}
PROBE_ORDER = ("P_HEAD", "P_ROUTE", "P_J", "P_CUSTODY", "P_CANARY")
MINIMUM_COVER_REASON = "PROBE_COSTS_AND_WORLD_PAIR_SEPARATION_NOT_MEASURED"
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})
LOCAL_PREFIX = "LOCAL_ARTIFACT_"
HOST_PREFIX = "HOST_ADMISSION_"
TARGET_REF_MISMATCH = "RESOLVED_HOST_GATE_TARGET_REF_MISMATCH"

_HOST_FIELDS = {
    "version",
    "disposition",
    "local_temporal_closure_proven",
    "pre_closure_status",
    "post_closure_status",
    "exact_hold_to_closed_transition",
    "pre_reentry_receipt_identity",
    "post_closure_receipt_identity",
    "host_gate_states",
    "host_gate_resolutions",
    "host_gate_reasons",
    "fail_mask",
    "unknown_mask",
    "candidate_probes_by_unknown_gate",
    "ordered_required_probes",
    "minimum_cover_computed",
    "minimum_cover_reason",
    "host_observation_set_complete",
    "resolver_trust_proven_by_this_module",
    "host_observation_authority_proven_by_this_module",
    "local_evidence_promoted_to_host_rank",
    "drive_pointer_presence_promoted_to_pass",
    "cache_or_coordinate_presence_promoted_to_pass",
    "trusted_continuation_ready",
    "host_effect_ready",
    "source_currentness_minted",
    "semantic_repair_correctness_minted",
    "producer_identity_authenticated",
    "authority",
    "receipt_identity",
}
_HOST_FALSE_FIELDS = (
    "resolver_trust_proven_by_this_module",
    "host_observation_authority_proven_by_this_module",
    "local_evidence_promoted_to_host_rank",
    "drive_pointer_presence_promoted_to_pass",
    "cache_or_coordinate_presence_promoted_to_pass",
    "trusted_continuation_ready",
    "host_effect_ready",
    "source_currentness_minted",
    "semantic_repair_correctness_minted",
    "producer_identity_authenticated",
)
_RESOLUTION_FIELDS = (
    "schema",
    "version",
    "gate",
    "state",
    "observation_ref",
    "producer_ref",
    "producer_generation",
    "currentness_ref",
    "authority_ref",
    "target_ref",
    "resolver_ref",
    "resolver_generation",
    "revoked",
    "resolution_digest",
)
_RESOLUTION_PAYLOAD_FIELDS = tuple(
    field for field in _RESOLUTION_FIELDS if field != "resolution_digest"
)
_RESOLUTION_BINDING_FIELDS = (
    "observation_ref",
    "producer_ref",
    "producer_generation",
    "currentness_ref",
    "authority_ref",
    "target_ref",
    "resolver_ref",
    "resolver_generation",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_state(value: Any) -> bool:
    """Return exact state membership without allowing unhashable inputs to escape."""
    return isinstance(value, str) and value in STATES


def artifact_target_ref(local_receipt: dict[str, Any]) -> str:
    """Return a deterministic evidence reference, not a semantic identifier."""
    return "aura-workcapsule-target-sha256:" + _sha256(local_receipt)


def _temporal_violations(receipt: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if receipt.get("version") != HOST_VERSION:
        violations.append("HOST_VERSION_MISMATCH")
    if receipt.get("local_temporal_closure_proven") is not True:
        violations.append("LOCAL_TEMPORAL_CLOSURE_NOT_PROVEN")
    if (receipt.get("pre_closure_status"), receipt.get("post_closure_status")) != (
        "HOLD",
        "CLOSED",
    ):
        violations.append("TEMPORAL_STATUS_MISMATCH")
    if receipt.get("exact_hold_to_closed_transition") is not True:
        violations.append("TEMPORAL_TRANSITION_NOT_EXACT")
    return violations


def _gate_maps(
    receipt: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    states = receipt.get("host_gate_states")
    resolutions = receipt.get("host_gate_resolutions")
    violations: list[str] = []
    if not isinstance(states, dict) or set(states) != set(GATES):
        violations.append("HOST_GATE_STATE_SET_MISMATCH")
        states = {}
    if not isinstance(resolutions, dict) or set(resolutions) != set(GATES):
        violations.append("HOST_GATE_RESOLUTION_SET_MISMATCH")
        resolutions = {}
    return states, resolutions, violations


def _resolution_digest(resolution: dict[str, Any]) -> str:
    payload = {field: resolution[field] for field in _RESOLUTION_PAYLOAD_FIELDS}
    return _sha256(payload)


def _resolution_integrity_violations(
    *,
    gate: str,
    effective_state: Any,
    resolution: Any,
) -> list[str]:
    if not isinstance(resolution, dict):
        return ["RESOLVED_GATE_MISSING_RESOLUTION:" + gate]
    if set(resolution) != set(_RESOLUTION_FIELDS):
        return ["HOST_RESOLUTION_FIELDS_MISMATCH:" + gate]

    violations: list[str] = []
    if resolution.get("schema") != HOST_RESOLUTION_SCHEMA:
        violations.append("HOST_RESOLUTION_SCHEMA_MISMATCH:" + gate)
    version = resolution.get("version")
    if type(version) is not int or version != HOST_RESOLUTION_VERSION:
        violations.append("HOST_RESOLUTION_VERSION_MISMATCH:" + gate)
    if resolution.get("gate") != gate:
        violations.append("HOST_RESOLUTION_GATE_MISMATCH:" + gate)
    if not _is_state(resolution.get("state")):
        violations.append("HOST_RESOLUTION_STATE_INVALID:" + gate)

    revoked = resolution.get("revoked")
    if not isinstance(revoked, bool):
        violations.append("HOST_RESOLUTION_REVOKED_NOT_BOOL:" + gate)
    else:
        derived_state = "FAIL" if revoked else resolution.get("state")
        if derived_state != effective_state:
            violations.append("HOST_RESOLUTION_EFFECTIVE_STATE_MISMATCH:" + gate)

    for field in _RESOLUTION_BINDING_FIELDS:
        value = resolution.get(field)
        if not isinstance(value, str) or not value.strip():
            violations.append(f"HOST_RESOLUTION_BINDING_MISSING:{gate}:{field}")

    supplied_digest = resolution.get("resolution_digest")
    if not _is_sha256(supplied_digest):
        violations.append("HOST_RESOLUTION_DIGEST_INVALID:" + gate)
    elif supplied_digest != _resolution_digest(resolution):
        violations.append("HOST_RESOLUTION_DIGEST_MISMATCH:" + gate)
    return violations


def _gate_shape_violations(
    states: dict[str, Any],
    resolutions: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    for gate in GATES:
        state = states.get(gate)
        resolution = resolutions.get(gate)
        if not _is_state(state):
            violations.append("HOST_GATE_STATE_INVALID:" + gate)
            continue
        if state == "UNKNOWN":
            if resolution is None:
                continue
            violations.extend(
                _resolution_integrity_violations(
                    gate=gate,
                    effective_state=state,
                    resolution=resolution,
                )
            )
            continue
        violations.extend(
            _resolution_integrity_violations(
                gate=gate,
                effective_state=state,
                resolution=resolution,
            )
        )
    return violations


def _derived_host_state(states: dict[str, Any]) -> dict[str, Any] | None:
    if set(states) != set(GATES) or any(
        not _is_state(states.get(gate)) for gate in GATES
    ):
        return None
    fail_mask = sum(
        1 << GATE_INDEX[gate] for gate in GATES if states[gate] == "FAIL"
    )
    unknown_mask = sum(
        1 << GATE_INDEX[gate] for gate in GATES if states[gate] == "UNKNOWN"
    )
    if fail_mask:
        disposition = "FAIL_CLOSED"
    elif unknown_mask:
        disposition = "HOST_OBSERVATION_REQUIRED"
    else:
        disposition = "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING"
    unknown_gates = [gate for gate in GATES if states[gate] == "UNKNOWN"]
    candidate_probes = {gate: list(GATE_PROBES[gate]) for gate in unknown_gates}
    probe_union = {probe for probes in candidate_probes.values() for probe in probes}
    ordered_required_probes = [probe for probe in PROBE_ORDER if probe in probe_union]
    return {
        "fail_mask": fail_mask,
        "unknown_mask": unknown_mask,
        "disposition": disposition,
        "candidate_probes_by_unknown_gate": candidate_probes,
        "ordered_required_probes": ordered_required_probes,
        "minimum_cover_computed": False,
        "minimum_cover_reason": MINIMUM_COVER_REASON,
        "host_observation_set_complete": fail_mask == 0 and unknown_mask == 0,
    }


def _derived_host_state_violations(
    receipt: dict[str, Any], states: dict[str, Any]
) -> list[str]:
    expected = _derived_host_state(states)
    if expected is None:
        return []
    violations: list[str] = []
    fail_mask = receipt.get("fail_mask")
    if type(fail_mask) is not int or fail_mask != expected["fail_mask"]:
        violations.append("HOST_FAIL_MASK_MISMATCH")
    unknown_mask = receipt.get("unknown_mask")
    if type(unknown_mask) is not int or unknown_mask != expected["unknown_mask"]:
        violations.append("HOST_UNKNOWN_MASK_MISMATCH")
    if receipt.get("disposition") != expected["disposition"]:
        violations.append("HOST_DISPOSITION_MISMATCH")
    if (
        receipt.get("candidate_probes_by_unknown_gate")
        != expected["candidate_probes_by_unknown_gate"]
    ):
        violations.append("HOST_CANDIDATE_PROBES_MISMATCH")
    if receipt.get("ordered_required_probes") != expected["ordered_required_probes"]:
        violations.append("HOST_ORDERED_REQUIRED_PROBES_MISMATCH")
    if receipt.get("minimum_cover_computed") is not False:
        violations.append("HOST_MINIMUM_COVER_COMPUTED_INVALID")
    if receipt.get("minimum_cover_reason") != MINIMUM_COVER_REASON:
        violations.append("HOST_MINIMUM_COVER_REASON_MISMATCH")
    if (
        receipt.get("host_observation_set_complete")
        is not expected["host_observation_set_complete"]
    ):
        violations.append("HOST_OBSERVATION_COMPLETENESS_MISMATCH")
    return violations


def _ceiling_violations(receipt: dict[str, Any]) -> list[str]:
    violations = [
        "HOST_CEILING_VIOLATED:" + field
        for field in _HOST_FALSE_FIELDS
        if receipt.get(field) is not False
    ]
    authority = receipt.get("authority")
    if not isinstance(authority, dict) or any(bool(value) for value in authority.values()):
        violations.append("HOST_AUTHORITY_NOT_FALSE")
    return violations


def _identity_violations(receipt: dict[str, Any]) -> list[str]:
    identity = receipt.get("receipt_identity")
    if not isinstance(identity, dict):
        return ["HOST_RECEIPT_IDENTITY_MISSING"]
    violations: list[str] = []
    if (
        identity.get("kind") != "DIGEST"
        or identity.get("algorithm_or_provider") != "sha256"
    ):
        violations.append("HOST_RECEIPT_IDENTITY_PROFILE_INVALID")
    supplied = identity.get("value")
    payload = {
        key: value for key, value in receipt.items() if key != "receipt_identity"
    }
    if not isinstance(supplied, str) or supplied != _sha256(payload):
        violations.append("HOST_RECEIPT_IDENTITY_MISMATCH")
    return violations


def verify_host_admission_envelope(receipt: dict[str, Any]) -> list[str]:
    """Check #559 envelope and nested/derived integrity, never producer trust."""
    if not isinstance(receipt, dict) or set(receipt) != _HOST_FIELDS:
        return ["MALFORMED_HOST_ADMISSION_ENVELOPE"]
    states, resolutions, violations = _gate_maps(receipt)
    violations.extend(_temporal_violations(receipt))
    violations.extend(_gate_shape_violations(states, resolutions))
    violations.extend(_derived_host_state_violations(receipt, states))
    violations.extend(_ceiling_violations(receipt))
    violations.extend(_identity_violations(receipt))
    return list(dict.fromkeys(violations))


def _local_violations(
    *,
    scoped_target_inputs: dict[str, Any],
    higher_owner_projection: dict[str, Any],
    raw_slice_receipt: dict[str, Any],
) -> list[str]:
    return [
        LOCAL_PREFIX + item
        for item in verify_current_recursive_target_raw_slice_binding(
            scoped_target_inputs=scoped_target_inputs,
            higher_owner_projection=higher_owner_projection,
            raw_slice_receipt=raw_slice_receipt,
        )
    ]


def _admit_local(
    *,
    scoped_target_inputs: dict[str, Any],
    higher_owner_projection: dict[str, Any],
    raw_slice_receipt: dict[str, Any],
) -> dict[str, Any]:
    return admit_current_recursive_target_raw_slice_binding(
        scoped_target_inputs=scoped_target_inputs,
        higher_owner_projection=higher_owner_projection,
        raw_slice_receipt=raw_slice_receipt,
    )


def _target_binding_violations(
    *,
    host_receipt: dict[str, Any],
    expected_ref: str,
) -> list[str]:
    states = host_receipt["host_gate_states"]
    resolutions = host_receipt["host_gate_resolutions"]
    violations: list[str] = []
    for gate in GATES:
        if states[gate] not in {"PASS", "FAIL"}:
            continue
        resolution = resolutions[gate]
        if resolution["target_ref"] != expected_ref:
            violations.append(f"{TARGET_REF_MISMATCH}:{gate}")
    return violations


def verify_artifact_qualified_host_observation(
    *,
    scoped_target_inputs: dict[str, Any],
    higher_owner_projection: dict[str, Any],
    raw_slice_receipt: dict[str, Any],
    host_admission_receipt: dict[str, Any],
) -> list[str]:
    """Require every resolved host gate to concern the exact #562 consequence."""
    local_kwargs = {
        "scoped_target_inputs": scoped_target_inputs,
        "higher_owner_projection": higher_owner_projection,
        "raw_slice_receipt": raw_slice_receipt,
    }
    violations = _local_violations(**local_kwargs)
    violations.extend(
        HOST_PREFIX + item
        for item in verify_host_admission_envelope(host_admission_receipt)
    )
    if violations:
        return list(dict.fromkeys(violations))
    expected_ref = artifact_target_ref(_admit_local(**local_kwargs))
    violations.extend(
        _target_binding_violations(
            host_receipt=host_admission_receipt,
            expected_ref=expected_ref,
        )
    )
    return list(dict.fromkeys(violations))


def _host_gate_partition(states: dict[str, Any]) -> tuple[list[str], list[str]]:
    resolved = [gate for gate in GATES if states[gate] in {"PASS", "FAIL"}]
    unknown = [gate for gate in GATES if states[gate] == "UNKNOWN"]
    return resolved, unknown


def admit_artifact_qualified_host_observation(**kwargs: Any) -> dict[str, Any]:
    violations = verify_artifact_qualified_host_observation(**kwargs)
    if violations:
        raise ValueError(
            "artifact-qualified host observation failed: " + ",".join(violations)
        )
    local = _admit_local(
        scoped_target_inputs=kwargs["scoped_target_inputs"],
        higher_owner_projection=kwargs["higher_owner_projection"],
        raw_slice_receipt=kwargs["raw_slice_receipt"],
    )
    host = kwargs["host_admission_receipt"]
    states = dict(host["host_gate_states"])
    resolved, unknown = _host_gate_partition(states)
    all_pass = all(states[gate] == "PASS" for gate in GATES)
    return {
        "version": VERSION,
        "current_recursive_raw_target_reproved": True,
        "artifact_target_ref": artifact_target_ref(local),
        "host_admission_integrity_checked": True,
        "host_admission_reproved_by_child": False,
        "host_admission_producer_authenticated": False,
        "resolved_host_gates_bound_to_exact_artifact": True,
        "resolved_host_gate_count": len(resolved),
        "resolved_host_gates": resolved,
        "unknown_host_gates": unknown,
        "host_gate_states": states,
        "host_observation_set_complete": all_pass,
        "all_host_gates_pass_for_exact_artifact": all_pass,
        "target_slice_sha256_hex": local["target_slice_sha256_hex"],
        "target_slice_byte_len": local["target_slice_byte_len"],
        "dependency_key": dict(local["dependency_key"]),
        "source_generation": local["source_generation"],
        "full_source_sha256_hex": local["full_source_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": local[
            "selected_target_semantic_handle_digest_hex"
        ],
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