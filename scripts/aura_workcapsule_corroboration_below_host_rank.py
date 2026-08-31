#!/usr/bin/env python3
"""Keep corroborated portable raw-slice evidence below host observation rank.

PR569 owns the portable-evidence/host-plane boundary: exact portable raw-slice evidence
remains local evidence and only an explicit host resolver can move a host gate out of
UNKNOWN. PR577 owns a distinct corroboration edge between exact PR568 and PR572
live-causal proof artifacts.

This membrane closes one narrow HyperScale seam: independent corroboration of the same
portable evidence does not create host observation rank by quorum. It binds PR569's
portable projection digest to the exact PR572 projection digest consumed by PR577,
delegates the source/target/POST/O10 relation to PR577 unchanged, and carries PR569's
host state byte-for-byte. Corroboration is never supplied as a host observation or
host-resolution receipt.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_live_causal_corroboration import (
    admit_live_causal_corroboration,
    verify_live_causal_corroboration,
)

VERSION = "AURA_WORKCAPSULE_CORROBORATION_BELOW_HOST_RANK_V1"
PR569_VERSION = "AURA_WORKCAPSULE_PORTABLE_RAW_SLICE_HOST_PLANE_SEPARATION_V1"
GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})
AUTHORITY_FIELDS = {
    "review_authorized",
    "execution_authorized",
    "commit_authorized",
    "merge_authorized",
    "promotion_authorized",
    "provider_effect_authorized",
    "public_effect_authorized",
    "human_authority",
}
PR569_FIELDS = {
    "version",
    "portable_raw_slice_projection_verified",
    "portable_raw_slice_projection_digest",
    "raw_slice_receipt_view_derived",
    "raw_slice_receipt_view_digest",
    "portable_envelope_promoted_to_host_rank",
    "portable_envelope_accepted_as_host_resolution",
    "host_resolution_required_for_rank_change",
    "host_gate_states",
    "host_disposition",
    "host_observation_set_complete",
    "host_observation_authority_proven",
    "producer_authenticated",
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
    "semantic_repair_correctness_proven",
    "trusted_continuation_ready",
    "host_effect_ready",
    "authority",
    "receipt_identity",
}
PR569_TRUE = {
    "portable_raw_slice_projection_verified",
    "raw_slice_receipt_view_derived",
    "host_resolution_required_for_rank_change",
}
PR569_FALSE = {
    "portable_envelope_promoted_to_host_rank",
    "portable_envelope_accepted_as_host_resolution",
    "host_observation_authority_proven",
    "producer_authenticated",
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
    "semantic_repair_correctness_proven",
    "trusted_continuation_ready",
    "host_effect_ready",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _verify_pr569(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != PR569_FIELDS:
        return ["PR569_RECEIPT_SCHEMA_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR569_VERSION:
        violations.append("PR569_VERSION_MISMATCH")
    for field in PR569_TRUE:
        if receipt.get(field) is not True:
            violations.append("PR569_REQUIRED_TRUE:" + field)
    for field in PR569_FALSE:
        if receipt.get(field) is not False:
            violations.append("PR569_REQUIRED_FALSE:" + field)
    for field in ("portable_raw_slice_projection_digest", "raw_slice_receipt_view_digest"):
        if not _is_sha256(receipt.get(field)):
            violations.append("PR569_DIGEST_INVALID:" + field)

    authority = receipt.get("authority")
    if not isinstance(authority, dict) or set(authority) != AUTHORITY_FIELDS:
        violations.append("PR569_AUTHORITY_SCHEMA_MISMATCH")
    elif any(type(authority[field]) is not bool for field in AUTHORITY_FIELDS):
        violations.append("PR569_AUTHORITY_TYPE_MISMATCH")
    elif any(authority.values()):
        violations.append("PR569_AUTHORITY_WIDENED")

    states = receipt.get("host_gate_states")
    if not isinstance(states, dict) or set(states) != set(GATES):
        violations.append("PR569_HOST_GATE_SET_MISMATCH")
    elif any(states[gate] not in STATES for gate in GATES):
        violations.append("PR569_HOST_GATE_STATE_INVALID")
    else:
        complete = all(states[gate] != "UNKNOWN" for gate in GATES)
        if receipt.get("host_observation_set_complete") is not complete:
            violations.append("PR569_HOST_COMPLETENESS_MISMATCH")
        if complete and all(states[gate] == "PASS" for gate in GATES):
            if receipt.get("host_disposition") != "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING":
                violations.append("PR569_HOST_DISPOSITION_MISMATCH")
        elif not complete and receipt.get("host_disposition") != "HOST_OBSERVATION_REQUIRED":
            violations.append("PR569_HOST_DISPOSITION_MISMATCH")

    identity = receipt.get("receipt_identity")
    identity_fields = {
        "kind", "algorithm_or_provider", "canonicalization_profile",
        "scope_profile", "value", "schema_version",
    }
    if not isinstance(identity, dict) or set(identity) != identity_fields:
        violations.append("PR569_RECEIPT_IDENTITY_SCHEMA_MISMATCH")
    elif (
        identity.get("kind") != "DIGEST"
        or identity.get("algorithm_or_provider") != "sha256"
        or identity.get("canonicalization_profile") != "JSON_SORT_KEYS_COMPACT_UTF8_V1"
        or identity.get("scope_profile") != PR569_VERSION
        or identity.get("value") != hashlib.sha256(
            _canonical_bytes({k: v for k, v in receipt.items() if k != "receipt_identity"})
        ).hexdigest()
    ):
        violations.append("PR569_RECEIPT_IDENTITY_MISMATCH")
    return list(dict.fromkeys(violations))


def verify_corroboration_below_host_rank(
    *,
    portable_host_receipt: dict[str, Any],
    pr568_receipt: dict[str, Any],
    pr572_receipt: dict[str, Any],
) -> list[str]:
    violations = _verify_pr569(portable_host_receipt)
    corroboration_violations = verify_live_causal_corroboration(
        pr568_receipt=pr568_receipt,
        pr572_receipt=pr572_receipt,
    )
    violations.extend("CORROBORATION_" + item for item in corroboration_violations)
    if violations:
        return list(dict.fromkeys(violations))

    if portable_host_receipt["portable_raw_slice_projection_digest"] != pr572_receipt[
        "raw_slice_projection_payload_sha256"
    ]:
        violations.append("PORTABLE_EVIDENCE_NOT_PR572_CORROBORATED_PROJECTION")

    # Corroboration may accompany host evidence, but it is never the owner of host rank.
    corroboration = admit_live_causal_corroboration(
        pr568_receipt=pr568_receipt,
        pr572_receipt=pr572_receipt,
    )
    if corroboration.get("host_observation_authority_proven") is not False:
        violations.append("CORROBORATION_HOST_AUTHORITY_WIDENED")
    if corroboration.get("effect_authority_proven") is not False:
        violations.append("CORROBORATION_EFFECT_AUTHORITY_WIDENED")
    if corroboration.get("producer_authentication_proven") is not False:
        violations.append("CORROBORATION_PRODUCER_AUTH_WIDENED")
    return list(dict.fromkeys(violations))


def admit_corroboration_below_host_rank(**kwargs: Any) -> dict[str, Any]:
    violations = verify_corroboration_below_host_rank(**kwargs)
    if violations:
        raise ValueError("corroboration/host-rank separation failed: " + ",".join(violations))

    portable = kwargs["portable_host_receipt"]
    corroboration = admit_live_causal_corroboration(
        pr568_receipt=kwargs["pr568_receipt"],
        pr572_receipt=kwargs["pr572_receipt"],
    )
    host_states = dict(portable["host_gate_states"])
    out = {
        "version": VERSION,
        "portable_host_plane_receipt_integrity_checked": True,
        "corroboration_owner_reproved": True,
        "same_portable_projection_as_pr572_proven": True,
        "independent_corroborating_proof_count": 2,
        "corroboration_added_without_host_rank_change": True,
        "corroboration_used_as_host_observation": False,
        "corroboration_used_as_host_resolution": False,
        "portable_evidence_promoted_to_host_rank": False,
        "explicit_host_resolution_still_required_for_rank_change": True,
        "host_gate_states_before_corroboration": host_states,
        "host_gate_states_after_corroboration": dict(host_states),
        "host_disposition_after_corroboration": portable["host_disposition"],
        "host_observation_set_complete_after_corroboration": portable[
            "host_observation_set_complete"
        ],
        "corroboration_receipt_identity": corroboration["receipt_identity"],
        "pr568_artifact_ref": corroboration["pr568_artifact_ref"],
        "pr572_artifact_ref": corroboration["pr572_artifact_ref"],
        "proof_artifact_refs_distinct": corroboration["proof_artifact_refs_distinct"],
        "portable_projection_digest": portable["portable_raw_slice_projection_digest"],
        "host_observation_authority_proven": False,
        "producer_authentication_proven": False,
        "semantic_equivalence_proven": False,
        "semantic_truth_proven": False,
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
        "value": hashlib.sha256(_canonical_bytes(out)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
