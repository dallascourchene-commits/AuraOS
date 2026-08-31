#!/usr/bin/env python3
"""Prove exact raw-slice evidence cannot impersonate a live-artifact host envelope.

PR575 owns host-observation target qualification for the exact PR568 live-causal
artifact. PR574 owns causal-owner current raw-slice/host-plane separation. This
consumer accepts only their closed consequence objects, preserves both owners, and
proves a narrow negative relation: a valid PR574 raw-slice separation receipt is not
an admissible PR559/PR565 host-admission envelope and therefore cannot satisfy the
host object required by PR575 merely because it concerns strong current evidence.

Receipt integrity and corroborating evidence are not producer authentication,
semantic truth, resolver trust, host authority, or effect authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    verify_host_admission_envelope,
)

VERSION = "AURA_WORKCAPSULE_LIVE_ARTIFACT_RAW_SLICE_NONINTERCHANGEABILITY_V1"
PR575_VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_ARTIFACT_HOST_OBSERVATION_V1"
PR574_VERSION = "AURA_WORKCAPSULE_CAUSAL_RAW_SLICE_HOST_SEPARATION_V1"
GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})

_LIVE_FIELDS = {
    "version",
    "live_causal_raw_slice_reproved",
    "live_causal_artifact_target_ref",
    "host_admission_integrity_checked",
    "host_admission_reproved_by_child",
    "host_admission_producer_authenticated",
    "resolved_host_gates_bound_to_live_causal_artifact",
    "resolved_host_gate_count",
    "resolved_host_gates",
    "unknown_host_gates",
    "host_gate_states",
    "host_observation_set_complete",
    "all_host_gates_pass_for_live_causal_artifact",
    "causal_post_owner_reproved_from_raw_evidence",
    "same_exact_post_source_instance_proven",
    "same_exact_raw_target_slice_proven",
    "causal_post_closure_receipt_identity",
    "dependency_key",
    "source_generation",
    "full_source_sha256_hex",
    "full_source_byte_len",
    "target_byte_start",
    "target_byte_end",
    "target_slice_sha256_hex",
    "selected_target_semantic_handle_digest_hex",
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
    "host_resolver_trust_proven",
    "host_observation_authority_proven",
    "trusted_continuation_ready",
    "host_effect_ready",
    "semantic_repair_correctness_proven",
    "producer_authenticated",
    "authority",
}

_RAW_FIELDS = {
    "version",
    "raw_slice_contract_owner",
    "causal_host_owner",
    "raw_slice_receipt_digest",
    "raw_slice_exact_current_local_evidence_validated",
    "causal_temporal_owner_reproved",
    "pre_reentry_receipt_reused_for_post_o10",
    "fresh_post_reentry_receipt_substituted",
    "host_gate_states",
    "host_disposition",
    "host_observation_set_complete",
    "raw_slice_promoted_to_host_rank",
    "raw_slice_used_as_host_resolution",
    "raw_slice_semantic_identity_proven",
    "raw_slice_producer_authenticated",
    "host_observation_authority_proven",
    "host_resolver_trust_proven",
    "trusted_continuation_ready",
    "host_effect_ready",
    "semantic_repair_correctness_minted",
    "authority",
    "receipt_identity",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _all_false_authority(value: Any) -> bool:
    return isinstance(value, dict) and bool(value) and not any(
        bool(item) for item in value.values()
    )


def _valid_gate_map(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(GATES)
        and all(isinstance(value[gate], str) and value[gate] in STATES for gate in GATES)
    )


def _verify_live(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != _LIVE_FIELDS:
        return ["PR575_LIVE_RECEIPT_SCHEMA_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR575_VERSION:
        violations.append("PR575_VERSION_MISMATCH")
    for field in (
        "live_causal_raw_slice_reproved",
        "host_admission_integrity_checked",
        "resolved_host_gates_bound_to_live_causal_artifact",
        "causal_post_owner_reproved_from_raw_evidence",
        "same_exact_post_source_instance_proven",
        "same_exact_raw_target_slice_proven",
    ):
        if receipt.get(field) is not True:
            violations.append("PR575_REQUIRED_PROOF_MISSING:" + field)
    for field in (
        "host_admission_reproved_by_child",
        "host_admission_producer_authenticated",
        "semantic_handle_derived_from_raw_slice",
        "semantic_identity_proven_by_raw_slice",
        "host_resolver_trust_proven",
        "host_observation_authority_proven",
        "trusted_continuation_ready",
        "host_effect_ready",
        "semantic_repair_correctness_proven",
        "producer_authenticated",
    ):
        if receipt.get(field) is not False:
            violations.append("PR575_CEILING_VIOLATED:" + field)
    target_ref = receipt.get("live_causal_artifact_target_ref")
    if not isinstance(target_ref, str) or not target_ref.startswith(
        "aura-workcapsule-target-sha256:"
    ):
        violations.append("PR575_ARTIFACT_TARGET_REF_INVALID")
    if not _valid_gate_map(receipt.get("host_gate_states")):
        violations.append("PR575_HOST_GATE_MAP_INVALID")
    if not _all_false_authority(receipt.get("authority")):
        violations.append("PR575_AUTHORITY_NOT_FALSE")
    return violations


def _verify_raw(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != _RAW_FIELDS:
        return ["PR574_RAW_RECEIPT_SCHEMA_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR574_VERSION:
        violations.append("PR574_VERSION_MISMATCH")
    if receipt.get("raw_slice_exact_current_local_evidence_validated") is not True:
        violations.append("PR574_RAW_SLICE_NOT_VALIDATED")
    if receipt.get("causal_temporal_owner_reproved") is not True:
        violations.append("PR574_CAUSAL_OWNER_NOT_REPROVED")
    if receipt.get("pre_reentry_receipt_reused_for_post_o10") is not True:
        violations.append("PR574_PRE_REENTRY_NOT_REUSED")
    if receipt.get("fresh_post_reentry_receipt_substituted") is not False:
        violations.append("PR574_FRESH_POST_REENTRY_SUBSTITUTED")
    for field in (
        "raw_slice_promoted_to_host_rank",
        "raw_slice_used_as_host_resolution",
        "raw_slice_semantic_identity_proven",
        "raw_slice_producer_authenticated",
        "host_observation_authority_proven",
        "host_resolver_trust_proven",
        "trusted_continuation_ready",
        "host_effect_ready",
        "semantic_repair_correctness_minted",
    ):
        if receipt.get(field) is not False:
            violations.append("PR574_CEILING_VIOLATED:" + field)
    if not _valid_gate_map(receipt.get("host_gate_states")):
        violations.append("PR574_HOST_GATE_MAP_INVALID")
    if not _all_false_authority(receipt.get("authority")):
        violations.append("PR574_AUTHORITY_NOT_FALSE")
    identity = receipt.get("receipt_identity")
    if not isinstance(identity, dict):
        violations.append("PR574_RECEIPT_IDENTITY_MISSING")
    else:
        payload = {key: value for key, value in receipt.items() if key != "receipt_identity"}
        if (
            identity.get("kind") != "DIGEST"
            or identity.get("algorithm_or_provider") != "sha256"
            or identity.get("scope_profile") != PR574_VERSION
            or identity.get("value") != _sha(payload)
        ):
            violations.append("PR574_RECEIPT_IDENTITY_MISMATCH")
    return violations


def verify_live_artifact_raw_slice_noninterchangeability(
    *,
    live_artifact_host_receipt: Mapping[str, Any],
    causal_raw_slice_host_separation_receipt: Mapping[str, Any],
) -> list[str]:
    """Require exact parent ceilings and reject raw-slice->host-envelope cross-cast."""
    live = dict(live_artifact_host_receipt)
    raw = dict(causal_raw_slice_host_separation_receipt)
    violations = _verify_live(live) + _verify_raw(raw)
    if violations:
        return list(dict.fromkeys(violations))
    cross_cast = verify_host_admission_envelope(raw)
    if cross_cast != ["MALFORMED_HOST_ADMISSION_ENVELOPE"]:
        violations.append("RAW_SLICE_HOST_ENVELOPE_CROSS_CAST_NOT_REJECTED")
    if raw.get("raw_slice_used_as_host_resolution") is not False:
        violations.append("RAW_SLICE_USED_AS_HOST_RESOLUTION")
    return list(dict.fromkeys(violations))


def admit_live_artifact_raw_slice_noninterchangeability(
    **kwargs: Any,
) -> dict[str, Any]:
    violations = verify_live_artifact_raw_slice_noninterchangeability(**kwargs)
    if violations:
        raise ValueError("live-artifact/raw-slice separation failed: " + ",".join(violations))
    live = dict(kwargs["live_artifact_host_receipt"])
    raw = dict(kwargs["causal_raw_slice_host_separation_receipt"])
    payload = {
        "version": VERSION,
        "live_artifact_target_ref": live["live_causal_artifact_target_ref"],
        "live_artifact_host_receipt_ref": "sha256:" + _sha(live),
        "causal_raw_slice_host_separation_receipt_ref": "sha256:" + _sha(raw),
        "raw_slice_exact_current_local_evidence_validated": True,
        "resolved_host_gates_bound_to_live_artifact": True,
        "raw_slice_host_envelope_cross_cast_rejected": True,
        "raw_slice_promoted_to_host_rank": False,
        "raw_slice_used_as_host_resolution": False,
        "proof_artifacts_interchangeable": False,
        "producer_authenticated": False,
        "semantic_equivalence_proven": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "host_effect_ready": False,
        "authority": {
            "review_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }
    out = dict(payload)
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": _sha(payload),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
