#!/usr/bin/env python3
"""Bind a PR567 causal host-admission envelope to one exact PR565 local artifact.

PR565 remains the local current-recursive/raw-slice artifact owner and now also owns the
canonical derived host-state summary relation. PR567 remains the causal PRE->POST O10 +
five-gate host owner. This membrane validates only the closed transport form of a PR567
admission, delegates generic host-state derivation and target binding to current PR565, and
keeps causal-scar validation local to this causal transport generation.

It does not re-run or authenticate PR567; exact PR567 is independently re-proved in hosted CI.
"""
from __future__ import annotations

from typing import Any

from scripts import aura_workcapsule_artifact_qualified_host_observation as artifact_host_owner
from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    GATES,
    _admit_local,
    _ceiling_violations,
    _gate_maps,
    _gate_shape_violations,
    _host_gate_partition,
    _identity_violations,
    _local_violations,
    _target_binding_violations,
    artifact_target_ref,
)

VERSION = "AURA_WORKCAPSULE_CAUSAL_ARTIFACT_QUALIFIED_HOST_ENVELOPE_V1"
CAUSAL_HOST_VERSION = "AURA_WORKCAPSULE_CAUSAL_TEMPORAL_HOST_OBSERVATION_ADMISSION_V2"
HOST_PREFIX = "CAUSAL_HOST_ADMISSION_"

_CAUSAL_HOST_FIELDS = {
    "version", "disposition", "causal_temporal_owner_reproved",
    "raw_owner_pre_lifecycle_derived", "raw_owner_post_candidate_derived",
    "post_o10_closure_derived", "pre_reentry_receipt_reused_for_post_o10",
    "fresh_post_reentry_receipt_substituted", "local_temporal_closure_proven",
    "pre_closure_status", "post_closure_status", "exact_hold_to_closed_transition",
    "pre_reentry_receipt_identity", "post_closure_receipt_identity",
    "host_gate_states", "host_gate_resolutions", "host_gate_reasons", "fail_mask",
    "unknown_mask", "candidate_probes_by_unknown_gate", "ordered_required_probes",
    "minimum_cover_computed", "minimum_cover_reason", "host_observation_set_complete",
    "resolver_trust_proven_by_this_module", "host_observation_authority_proven_by_this_module",
    "local_evidence_promoted_to_host_rank", "drive_pointer_presence_promoted_to_pass",
    "cache_or_coordinate_presence_promoted_to_pass", "trusted_continuation_ready",
    "host_effect_ready", "source_currentness_minted", "semantic_repair_correctness_minted",
    "producer_identity_authenticated", "authority", "receipt_identity",
}

_CAUSAL_TRUE = (
    "causal_temporal_owner_reproved", "raw_owner_pre_lifecycle_derived",
    "raw_owner_post_candidate_derived", "post_o10_closure_derived",
    "pre_reentry_receipt_reused_for_post_o10", "local_temporal_closure_proven",
    "exact_hold_to_closed_transition",
)

_CAUSAL_FALSE = (
    "fresh_post_reentry_receipt_substituted", "resolver_trust_proven_by_this_module",
    "host_observation_authority_proven_by_this_module", "local_evidence_promoted_to_host_rank",
    "drive_pointer_presence_promoted_to_pass", "cache_or_coordinate_presence_promoted_to_pass",
    "trusted_continuation_ready", "host_effect_ready", "source_currentness_minted",
    "semantic_repair_correctness_minted", "producer_identity_authenticated",
)

_CURRENT_OWNER_DIAGNOSTIC_COMPAT = {
    "HOST_FAIL_MASK_MISMATCH": "FAIL_MASK_MISMATCH",
    "HOST_UNKNOWN_MASK_MISMATCH": "UNKNOWN_MASK_MISMATCH",
    "HOST_DISPOSITION_MISMATCH": "DISPOSITION_MISMATCH",
    "HOST_OBSERVATION_COMPLETENESS_MISMATCH": "HOST_COMPLETENESS_MISMATCH",
}


def _current_host_summary_violations(
    receipt: dict[str, Any], states: dict[str, Any]
) -> list[str]:
    """Delegate generic host-state derivation to current PR565 without changing O32 ABI."""
    return [
        _CURRENT_OWNER_DIAGNOSTIC_COMPAT.get(item, item)
        for item in artifact_host_owner._derived_host_state_violations(receipt, states)
    ]


def verify_causal_host_admission_envelope(receipt: dict[str, Any]) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != _CAUSAL_HOST_FIELDS:
        return ["MALFORMED_CAUSAL_HOST_ADMISSION_ENVELOPE"]
    violations: list[str] = []
    if receipt.get("version") != CAUSAL_HOST_VERSION:
        violations.append("CAUSAL_HOST_VERSION_MISMATCH")
    for field in _CAUSAL_TRUE:
        if receipt.get(field) is not True:
            violations.append("CAUSAL_REQUIRED_TRUE:" + field)
    for field in _CAUSAL_FALSE:
        if receipt.get(field) is not False:
            violations.append("CAUSAL_CEILING_VIOLATED:" + field)
    if (receipt.get("pre_closure_status"), receipt.get("post_closure_status")) != ("HOLD", "CLOSED"):
        violations.append("CAUSAL_TEMPORAL_STATUS_MISMATCH")
    states, resolutions, gate_violations = _gate_maps(receipt)
    violations.extend(gate_violations)
    if not gate_violations:
        violations.extend(_gate_shape_violations(states, resolutions))
        violations.extend(_current_host_summary_violations(receipt, states))
    violations.extend(_ceiling_violations(receipt))
    violations.extend(_identity_violations(receipt))
    identity = receipt.get("receipt_identity")
    if isinstance(identity, dict) and identity.get("scope_profile") != CAUSAL_HOST_VERSION:
        violations.append("CAUSAL_HOST_RECEIPT_SCOPE_PROFILE_MISMATCH")
    return list(dict.fromkeys(violations))


def verify_causal_artifact_qualified_host_envelope(
    *,
    scoped_target_inputs: dict[str, Any],
    higher_owner_projection: dict[str, Any],
    raw_slice_receipt: dict[str, Any],
    causal_host_admission_receipt: dict[str, Any],
) -> list[str]:
    local_kwargs = {
        "scoped_target_inputs": scoped_target_inputs,
        "higher_owner_projection": higher_owner_projection,
        "raw_slice_receipt": raw_slice_receipt,
    }
    violations = _local_violations(**local_kwargs)
    violations.extend(
        HOST_PREFIX + item
        for item in verify_causal_host_admission_envelope(causal_host_admission_receipt)
    )
    if violations:
        return list(dict.fromkeys(violations))
    expected_ref = artifact_target_ref(_admit_local(**local_kwargs))
    violations.extend(
        _target_binding_violations(
            host_receipt=causal_host_admission_receipt,
            expected_ref=expected_ref,
        )
    )
    return list(dict.fromkeys(violations))


def admit_causal_artifact_qualified_host_envelope(**kwargs: Any) -> dict[str, Any]:
    violations = verify_causal_artifact_qualified_host_envelope(**kwargs)
    if violations:
        raise ValueError(
            "causal artifact-qualified host envelope failed: " + ",".join(violations)
        )
    local = _admit_local(
        scoped_target_inputs=kwargs["scoped_target_inputs"],
        higher_owner_projection=kwargs["higher_owner_projection"],
        raw_slice_receipt=kwargs["raw_slice_receipt"],
    )
    host = kwargs["causal_host_admission_receipt"]
    states = dict(host["host_gate_states"])
    resolved, unknown = _host_gate_partition(states)
    derived = artifact_host_owner._derived_host_state(states)
    assert derived is not None
    return {
        "version": VERSION,
        "current_recursive_raw_target_reproved": True,
        "artifact_target_ref": artifact_target_ref(local),
        "causal_host_admission_integrity_checked": True,
        "causal_host_admission_reproved_by_child": False,
        "causal_host_admission_producer_authenticated": False,
        "causal_temporal_owner_claim_carried": True,
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "current_pr565_host_summary_owner_reused": True,
        "resolved_host_gates_bound_to_exact_artifact": True,
        "resolved_host_gate_count": len(resolved),
        "resolved_host_gates": resolved,
        "unknown_host_gates": unknown,
        "host_gate_states": states,
        "host_observation_set_complete": derived["host_observation_set_complete"],
        "all_host_gates_pass_for_exact_artifact": all(
            states[gate] == "PASS" for gate in GATES
        ),
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
