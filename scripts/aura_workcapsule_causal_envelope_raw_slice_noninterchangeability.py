#!/usr/bin/env python3
"""Keep causal artifact-qualified host evidence distinct from raw-slice evidence.

PR573 owns the current causal artifact-qualified host consequence. PR574 owns the
causal-current raw-slice/host-plane separation consequence. This evidence-only
consumer validates their closed consequence shapes and proves that a valid PR574
raw-slice separation receipt cannot impersonate the PR567 causal host-admission
envelope type consumed by PR573.

The relation is deliberately negative: stronger local evidence is not a host
transport object. It adds no producer authentication, semantic truth, resolver
trust, host authority, or effect authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    verify_causal_host_admission_envelope,
)

VERSION = "AURA_WORKCAPSULE_CAUSAL_ENVELOPE_RAW_SLICE_NONINTERCHANGEABILITY_V1"
PR573_VERSION = "AURA_WORKCAPSULE_CAUSAL_ARTIFACT_QUALIFIED_HOST_ENVELOPE_V1"
PR574_VERSION = "AURA_WORKCAPSULE_CAUSAL_RAW_SLICE_HOST_SEPARATION_V1"
GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})

_PR573_FIELDS = {
    "version",
    "current_recursive_raw_target_reproved",
    "artifact_target_ref",
    "causal_host_admission_integrity_checked",
    "causal_host_admission_reproved_by_child",
    "causal_host_admission_producer_authenticated",
    "causal_temporal_owner_claim_carried",
    "pre_reentry_receipt_reused_for_post_o10",
    "fresh_post_reentry_receipt_substituted",
    "current_pr565_host_summary_owner_reused",
    "resolved_host_gates_bound_to_exact_artifact",
    "resolved_host_gate_count",
    "resolved_host_gates",
    "unknown_host_gates",
    "host_gate_states",
    "host_observation_set_complete",
    "all_host_gates_pass_for_exact_artifact",
    "target_slice_sha256_hex",
    "target_slice_byte_len",
    "dependency_key",
    "source_generation",
    "full_source_sha256_hex",
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

_PR574_FIELDS = {
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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _valid_gate_map(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(GATES)
        and all(isinstance(value[gate], str) and value[gate] in STATES for gate in GATES)
    )


def _all_false_authority(value: Any) -> bool:
    return isinstance(value, dict) and bool(value) and not any(bool(item) for item in value.values())


def _verify_pr573(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != _PR573_FIELDS:
        return ["PR573_CONSEQUENCE_SCHEMA_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR573_VERSION:
        violations.append("PR573_VERSION_MISMATCH")
    for field in (
        "current_recursive_raw_target_reproved",
        "causal_host_admission_integrity_checked",
        "causal_temporal_owner_claim_carried",
        "pre_reentry_receipt_reused_for_post_o10",
        "current_pr565_host_summary_owner_reused",
        "resolved_host_gates_bound_to_exact_artifact",
    ):
        if receipt.get(field) is not True:
            violations.append("PR573_REQUIRED_PROOF_MISSING:" + field)
    for field in (
        "causal_host_admission_reproved_by_child",
        "causal_host_admission_producer_authenticated",
        "fresh_post_reentry_receipt_substituted",
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
            violations.append("PR573_CEILING_VIOLATED:" + field)
    if not _valid_gate_map(receipt.get("host_gate_states")):
        violations.append("PR573_HOST_GATE_MAP_INVALID")
    if not _all_false_authority(receipt.get("authority")):
        violations.append("PR573_AUTHORITY_NOT_FALSE")
    target_ref = receipt.get("artifact_target_ref")
    if not isinstance(target_ref, str) or not target_ref.startswith("aura-workcapsule-target-sha256:"):
        violations.append("PR573_ARTIFACT_TARGET_REF_INVALID")
    return violations


def _verify_pr574(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != _PR574_FIELDS:
        return ["PR574_CONSEQUENCE_SCHEMA_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR574_VERSION:
        violations.append("PR574_VERSION_MISMATCH")
    if receipt.get("raw_slice_exact_current_local_evidence_validated") is not True:
        violations.append("PR574_RAW_SLICE_NOT_VALIDATED")
    if receipt.get("causal_temporal_owner_reproved") is not True:
        violations.append("PR574_CAUSAL_OWNER_NOT_REPROVED")
    if receipt.get("pre_reentry_receipt_reused_for_post_o10") is not True:
        violations.append("PR574_PRE_REENTRY_NOT_REUSED")
    for field in (
        "fresh_post_reentry_receipt_substituted",
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


def verify_causal_envelope_raw_slice_noninterchangeability(
    *,
    causal_artifact_host_receipt: Mapping[str, Any],
    causal_raw_slice_host_separation_receipt: Mapping[str, Any],
) -> list[str]:
    host = dict(causal_artifact_host_receipt)
    raw = dict(causal_raw_slice_host_separation_receipt)
    violations = _verify_pr573(host) + _verify_pr574(raw)
    if violations:
        return list(dict.fromkeys(violations))
    cross_cast = verify_causal_host_admission_envelope(raw)
    if cross_cast != ["MALFORMED_CAUSAL_HOST_ADMISSION_ENVELOPE"]:
        violations.append("RAW_SLICE_CAUSAL_ENVELOPE_CROSS_CAST_NOT_REJECTED")
    return list(dict.fromkeys(violations))


def admit_causal_envelope_raw_slice_noninterchangeability(**kwargs: Any) -> dict[str, Any]:
    violations = verify_causal_envelope_raw_slice_noninterchangeability(**kwargs)
    if violations:
        raise ValueError("causal-envelope/raw-slice separation failed: " + ",".join(violations))
    host = dict(kwargs["causal_artifact_host_receipt"])
    raw = dict(kwargs["causal_raw_slice_host_separation_receipt"])
    payload = {
        "version": VERSION,
        "causal_artifact_host_receipt_ref": "sha256:" + _sha(host),
        "causal_raw_slice_host_separation_receipt_ref": "sha256:" + _sha(raw),
        "artifact_target_ref": host["artifact_target_ref"],
        "causal_artifact_host_integrity_checked": True,
        "causal_raw_slice_local_evidence_validated": True,
        "raw_slice_causal_host_envelope_cross_cast_rejected": True,
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
