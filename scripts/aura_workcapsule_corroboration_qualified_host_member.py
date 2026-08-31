#!/usr/bin/env python3
"""Bind a PR575 host target to the exact PR568 member of a PR577 corroboration edge.

PR575 owns host-observation target qualification for the exact PR568 live-causal
artifact. PR577 owns the corroboration relation between distinct PR568 and PR572
proof artifacts. This membrane proves only graph membership: the host target names
the PR568 member underlying the corroboration edge. It must not alias the PR572
sibling proof artifact or the corroboration receipt itself.

Reference schemes remain distinct. Matching digest payloads across the
`aura-workcapsule-target-sha256:` and `aura-proof-artifact-sha256:` schemes establish
an explicit adapter relation, not reference identity, producer authentication,
semantic truth, host authority, or effect authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_live_causal_corroboration import (
    VERSION as CORROBORATION_VERSION,
    admit_live_causal_corroboration,
    verify_live_causal_corroboration,
)
from scripts.aura_workcapsule_live_causal_artifact_host_observation import (
    VERSION as LIVE_HOST_VERSION,
)

VERSION = "AURA_WORKCAPSULE_CORROBORATION_QUALIFIED_HOST_MEMBER_V1"
HOST_TARGET_PREFIX = "aura-workcapsule-target-sha256:"
PROOF_ARTIFACT_PREFIX = "aura-proof-artifact-sha256:"
GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})

LIVE_HOST_FIELDS = {
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
LIVE_HOST_TRUE = {
    "live_causal_raw_slice_reproved",
    "host_admission_integrity_checked",
    "resolved_host_gates_bound_to_live_causal_artifact",
    "causal_post_owner_reproved_from_raw_evidence",
    "same_exact_post_source_instance_proven",
    "same_exact_raw_target_slice_proven",
}
LIVE_HOST_FALSE = {
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
}
AUTHORITY_FIELDS = {
    "review_authorized",
    "mutation_authorized",
    "execution_authorized",
    "commit_authorized",
    "merge_authorized",
    "promotion_authorized",
    "provider_effect_authorized",
    "public_effect_authorized",
    "human_authority",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _ref_digest(value: Any, prefix: str) -> str | None:
    if not isinstance(value, str) or not value.startswith(prefix):
        return None
    digest = value[len(prefix):]
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        return None
    return digest


def _verify_live_host(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != LIVE_HOST_FIELDS:
        return ["LIVE_HOST_RECEIPT_SCHEMA_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != LIVE_HOST_VERSION:
        violations.append("LIVE_HOST_VERSION_MISMATCH")
    for field in LIVE_HOST_TRUE:
        if receipt.get(field) is not True:
            violations.append("LIVE_HOST_REQUIRED_TRUE:" + field)
    for field in LIVE_HOST_FALSE:
        if receipt.get(field) is not False:
            violations.append("LIVE_HOST_REQUIRED_FALSE:" + field)

    authority = receipt.get("authority")
    if not isinstance(authority, dict) or set(authority) != AUTHORITY_FIELDS:
        violations.append("LIVE_HOST_AUTHORITY_SCHEMA_MISMATCH")
    elif any(type(authority[field]) is not bool for field in AUTHORITY_FIELDS):
        violations.append("LIVE_HOST_AUTHORITY_TYPE_MISMATCH")
    elif any(authority.values()):
        violations.append("LIVE_HOST_AUTHORITY_WIDENED")

    states = receipt.get("host_gate_states")
    resolved = receipt.get("resolved_host_gates")
    unknown = receipt.get("unknown_host_gates")
    if not isinstance(states, dict) or set(states) != set(GATES):
        violations.append("LIVE_HOST_GATE_STATE_SET_MISMATCH")
    elif any(states[gate] not in STATES for gate in GATES):
        violations.append("LIVE_HOST_GATE_STATE_INVALID")
    else:
        expected_resolved = [gate for gate in GATES if states[gate] in {"PASS", "FAIL"}]
        expected_unknown = [gate for gate in GATES if states[gate] == "UNKNOWN"]
        if resolved != expected_resolved:
            violations.append("LIVE_HOST_RESOLVED_GATE_LIST_MISMATCH")
        if unknown != expected_unknown:
            violations.append("LIVE_HOST_UNKNOWN_GATE_LIST_MISMATCH")
        if receipt.get("resolved_host_gate_count") != len(expected_resolved):
            violations.append("LIVE_HOST_RESOLVED_GATE_COUNT_MISMATCH")
        if receipt.get("host_observation_set_complete") is not (not expected_unknown):
            violations.append("LIVE_HOST_COMPLETENESS_MISMATCH")
        if receipt.get("all_host_gates_pass_for_live_causal_artifact") is not all(
            states[gate] == "PASS" for gate in GATES
        ):
            violations.append("LIVE_HOST_ALL_PASS_DERIVATION_MISMATCH")

    dependency_key = receipt.get("dependency_key")
    if not isinstance(dependency_key, dict) or set(dependency_key) != {"file_id", "relative_path"}:
        violations.append("LIVE_HOST_DEPENDENCY_KEY_SCHEMA_MISMATCH")
    if _ref_digest(receipt.get("live_causal_artifact_target_ref"), HOST_TARGET_PREFIX) is None:
        violations.append("LIVE_HOST_TARGET_REF_INVALID")
    return violations


def _host_matches_pr568(receipt: dict[str, Any], pr568_receipt: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    host_source = (
        receipt["dependency_key"],
        receipt["source_generation"],
        receipt["full_source_sha256_hex"],
        receipt["full_source_byte_len"],
    )
    pr568_source = (
        pr568_receipt["dependency_key"],
        pr568_receipt["source_generation"],
        pr568_receipt["full_source_sha256_hex"],
        pr568_receipt["full_source_byte_len"],
    )
    if host_source != pr568_source:
        violations.append("LIVE_HOST_PR568_SOURCE_INSTANCE_MISMATCH")

    host_target = (
        receipt["target_byte_start"],
        receipt["target_byte_end"],
        receipt["target_slice_sha256_hex"],
        receipt["selected_target_semantic_handle_digest_hex"],
    )
    pr568_target = (
        pr568_receipt["target_byte_start"],
        pr568_receipt["target_byte_end"],
        pr568_receipt["target_slice_sha256_hex"],
        pr568_receipt["selected_target_semantic_handle_digest_hex"],
    )
    if host_target != pr568_target:
        violations.append("LIVE_HOST_PR568_TARGET_SLICE_MISMATCH")
    if receipt["causal_post_closure_receipt_identity"] != pr568_receipt[
        "causal_post_closure_receipt_identity"
    ]:
        violations.append("LIVE_HOST_PR568_CAUSAL_O10_MISMATCH")
    return violations


def verify_corroboration_qualified_host_member(
    *,
    live_host_receipt: dict[str, Any],
    pr568_receipt: dict[str, Any],
    pr572_receipt: dict[str, Any],
) -> list[str]:
    violations = _verify_live_host(live_host_receipt)
    corroboration_violations = verify_live_causal_corroboration(
        pr568_receipt=pr568_receipt,
        pr572_receipt=pr572_receipt,
    )
    violations.extend("CORROBORATION_" + item for item in corroboration_violations)
    if violations:
        return list(dict.fromkeys(violations))

    violations.extend(_host_matches_pr568(live_host_receipt, pr568_receipt))
    corroboration = admit_live_causal_corroboration(
        pr568_receipt=pr568_receipt,
        pr572_receipt=pr572_receipt,
    )

    host_digest = _ref_digest(
        live_host_receipt["live_causal_artifact_target_ref"], HOST_TARGET_PREFIX
    )
    pr568_digest = _ref_digest(corroboration["pr568_artifact_ref"], PROOF_ARTIFACT_PREFIX)
    pr572_digest = _ref_digest(corroboration["pr572_artifact_ref"], PROOF_ARTIFACT_PREFIX)
    assert host_digest is not None and pr568_digest is not None and pr572_digest is not None

    if host_digest != pr568_digest:
        violations.append("HOST_TARGET_NOT_PR568_CORROBORATION_MEMBER")
    if live_host_receipt["live_causal_artifact_target_ref"] == corroboration["pr568_artifact_ref"]:
        violations.append("REFERENCE_SCHEMES_COLLAPSED")
    if host_digest == pr572_digest:
        violations.append("HOST_TARGET_ALIASES_PR572_SIBLING")
    if host_digest == _sha256(corroboration):
        violations.append("HOST_TARGET_ALIASES_CORROBORATION_EDGE")
    return list(dict.fromkeys(violations))


def admit_corroboration_qualified_host_member(**kwargs: Any) -> dict[str, Any]:
    violations = verify_corroboration_qualified_host_member(**kwargs)
    if violations:
        raise ValueError("corroboration-qualified host member failed: " + ",".join(violations))

    host = kwargs["live_host_receipt"]
    corroboration = admit_live_causal_corroboration(
        pr568_receipt=kwargs["pr568_receipt"],
        pr572_receipt=kwargs["pr572_receipt"],
    )
    host_digest = _ref_digest(host["live_causal_artifact_target_ref"], HOST_TARGET_PREFIX)
    pr568_digest = _ref_digest(corroboration["pr568_artifact_ref"], PROOF_ARTIFACT_PREFIX)
    assert host_digest is not None and pr568_digest is not None

    out = {
        "version": VERSION,
        "corroboration_owner_reproved": True,
        "live_host_consequence_shape_checked": True,
        "host_target_is_exact_pr568_corroboration_member": True,
        "same_underlying_pr568_digest_across_reference_schemes": True,
        "reference_scheme_identity_preserved": True,
        "host_target_is_pr572_sibling": False,
        "host_target_is_corroboration_edge": False,
        "host_target_ref": host["live_causal_artifact_target_ref"],
        "pr568_proof_artifact_ref": corroboration["pr568_artifact_ref"],
        "pr572_proof_artifact_ref": corroboration["pr572_artifact_ref"],
        "host_target_digest": host_digest,
        "pr568_member_digest": pr568_digest,
        "corroboration_receipt_identity": corroboration["receipt_identity"],
        "proof_artifact_refs_distinct": corroboration["proof_artifact_refs_distinct"],
        "host_gate_states": dict(host["host_gate_states"]),
        "host_observation_set_complete": host["host_observation_set_complete"],
        "live_host_receipt_producer_authenticated": False,
        "corroboration_parent_receipts_producer_authenticated": False,
        "semantic_equivalence_proven": False,
        "semantic_truth_proven": False,
        "host_observation_authority_proven": False,
        "resolver_trust_proven": False,
        "trusted_continuation_ready": False,
        "effect_authority_proven": False,
        "semantic_k27_authority_proven": False,
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
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": _sha256(out),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
