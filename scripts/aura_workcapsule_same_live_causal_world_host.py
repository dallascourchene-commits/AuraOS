#!/usr/bin/env python3
"""Require PR568 and PR572 to describe one exact live causal artifact world.

PR568 owns the recursive structural/raw-slice -> exact causal POST consequence.
PR572 independently owns the transported live causal raw-slice -> current host-lattice
consequence. This membrane owns neither lower proof path. It validates only the two
serialized admitted consequence shapes and requires their causal/source/target coordinates
to agree before carrying PR572 host state alongside the PR568 artifact core.

The membrane does not authenticate either receipt producer. Host observation state is not
part of artifact identity. Semantic truth, resolver trust, continuation, effects and all
mutation/merge authority remain unearned.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

VERSION = "AURA_WORKCAPSULE_SAME_LIVE_CAUSAL_WORLD_HOST_V1"
PR568_VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_RAW_SLICE_JOIN_V1"
PR572_VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_RAW_SLICE_HOST_V1"
GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})

PR568_FIELDS = {
    "version",
    "live_recursive_target_raw_slice_reproved",
    "portable_raw_slice_transport_reproved",
    "causal_post_owner_reproved_from_raw_evidence",
    "live_recursive_raw_slice_bound_to_exact_causal_post",
    "same_exact_post_source_instance_proven",
    "same_exact_raw_target_slice_proven",
    "post_source_projection_receipt_identity",
    "causal_post_closure_receipt_identity",
    "dependency_key",
    "source_generation",
    "full_source_sha256_hex",
    "full_source_byte_len",
    "target_byte_start",
    "target_byte_end",
    "target_slice_byte_len",
    "target_slice_sha256_hex",
    "selected_target_semantic_handle_digest_hex",
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
    "raw_slice_projection_producer_authenticated",
    "source_observation_producer_authenticated",
    "semantic_repair_correctness_proven",
    "source_to_graph_dependency_map_proven",
    "node_level_invalidation_cone_proven",
    "runtime_name_resolution_proven",
    "call_graph_proven",
    "b_minus_approved",
    "authority",
}
PR572_FIELDS = {
    "version",
    "live_pr560_to_pr556_causal_slice_join_proven",
    "portable_raw_slice_projection_verified",
    "live_post_source_coordinate_match_proven",
    "causal_post_owner_reproved_by_child",
    "post_source_projection_receipt_identity",
    "matched_live_post_source_witness_ref",
    "raw_slice_projection_payload_sha256",
    "file_id",
    "relative_path",
    "source_generation",
    "full_source_sha256_hex",
    "full_source_byte_len",
    "target_byte_start",
    "target_byte_end",
    "target_slice_sha256_hex",
    "selected_target_semantic_handle_digest_hex",
    "causal_pre_closure_status",
    "causal_post_closure_status",
    "causal_post_o10_receipt_identity",
    "pre_reentry_receipt_reused_for_post_o10",
    "fresh_post_reentry_receipt_substituted",
    "host_disposition",
    "host_gate_states",
    "host_observation_set_complete",
    "host_observation_authority_proven",
    "resolver_trust_proven",
    "trusted_continuation_ready",
    "host_effect_ready",
    "raw_slice_promoted_to_host_rank",
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
    "producer_authenticated",
    "semantic_repair_correctness_proven",
    "source_currentness_minted",
    "authority",
    "receipt_identity",
}

_PR568_TRUE = (
    "live_recursive_target_raw_slice_reproved",
    "portable_raw_slice_transport_reproved",
    "causal_post_owner_reproved_from_raw_evidence",
    "live_recursive_raw_slice_bound_to_exact_causal_post",
    "same_exact_post_source_instance_proven",
    "same_exact_raw_target_slice_proven",
)
_PR568_FALSE = (
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
    "raw_slice_projection_producer_authenticated",
    "source_observation_producer_authenticated",
    "semantic_repair_correctness_proven",
    "source_to_graph_dependency_map_proven",
    "node_level_invalidation_cone_proven",
    "runtime_name_resolution_proven",
    "call_graph_proven",
    "b_minus_approved",
)
_PR572_TRUE = (
    "live_pr560_to_pr556_causal_slice_join_proven",
    "portable_raw_slice_projection_verified",
    "live_post_source_coordinate_match_proven",
    "causal_post_owner_reproved_by_child",
    "pre_reentry_receipt_reused_for_post_o10",
)
_PR572_FALSE = (
    "fresh_post_reentry_receipt_substituted",
    "host_observation_authority_proven",
    "resolver_trust_proven",
    "trusted_continuation_ready",
    "host_effect_ready",
    "raw_slice_promoted_to_host_rank",
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
    "producer_authenticated",
    "semantic_repair_correctness_proven",
    "source_currentness_minted",
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


def _authority_is_false(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and bool(value)
        and all(flag is False for flag in value.values())
    )


def _identity_is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping) and bool(value)


def _require_non_bool_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def verify_pr568_live_causal_artifact_receipt(receipt: Any) -> list[str]:
    if not isinstance(receipt, Mapping):
        return ["PR568_RECEIPT_NOT_MAPPING"]
    if set(receipt) != PR568_FIELDS:
        return ["PR568_RECEIPT_FIELDS_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR568_VERSION:
        violations.append("PR568_VERSION_MISMATCH")
    for field in _PR568_TRUE:
        if receipt.get(field) is not True:
            violations.append("PR568_REQUIRED_TRUE:" + field)
    for field in _PR568_FALSE:
        if receipt.get(field) is not False:
            violations.append("PR568_CEILING_VIOLATED:" + field)
    if not _authority_is_false(receipt.get("authority")):
        violations.append("PR568_AUTHORITY_NOT_FALSE")
    dependency = receipt.get("dependency_key")
    if not isinstance(dependency, Mapping):
        violations.append("PR568_DEPENDENCY_KEY_INVALID")
    else:
        if not _require_non_bool_int(dependency.get("file_id")):
            violations.append("PR568_FILE_ID_INVALID")
        path = dependency.get("relative_path")
        if not isinstance(path, str) or not path:
            violations.append("PR568_RELATIVE_PATH_INVALID")
    for field in (
        "source_generation",
        "full_source_byte_len",
        "target_byte_start",
        "target_byte_end",
        "target_slice_byte_len",
    ):
        if not _require_non_bool_int(receipt.get(field)):
            violations.append("PR568_INTEGER_INVALID:" + field)
    start = receipt.get("target_byte_start")
    end = receipt.get("target_byte_end")
    length = receipt.get("target_slice_byte_len")
    if all(type(value) is int for value in (start, end, length)):
        if start >= end or end - start != length:
            violations.append("PR568_TARGET_SPAN_LENGTH_MISMATCH")
    for field in (
        "full_source_sha256_hex",
        "target_slice_sha256_hex",
        "selected_target_semantic_handle_digest_hex",
    ):
        if not _is_sha256(receipt.get(field)):
            violations.append("PR568_SHA256_INVALID:" + field)
    for field in (
        "post_source_projection_receipt_identity",
        "causal_post_closure_receipt_identity",
    ):
        if not _identity_is_mapping(receipt.get(field)):
            violations.append("PR568_IDENTITY_INVALID:" + field)
    return list(dict.fromkeys(violations))


def _expected_host_metadata(states: Mapping[str, Any]) -> tuple[str, bool] | None:
    if set(states) != set(GATES) or any(states.get(gate) not in STATES for gate in GATES):
        return None
    if any(states[gate] == "FAIL" for gate in GATES):
        return "FAIL_CLOSED", False
    if any(states[gate] == "UNKNOWN" for gate in GATES):
        return "HOST_OBSERVATION_REQUIRED", False
    return "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING", True


def _verify_pr572_receipt_identity(receipt: Mapping[str, Any]) -> bool:
    identity = receipt.get("receipt_identity")
    if not isinstance(identity, Mapping):
        return False
    if identity.get("kind") != "DIGEST" or identity.get("algorithm_or_provider") != "sha256":
        return False
    supplied = identity.get("value")
    payload = {key: value for key, value in receipt.items() if key != "receipt_identity"}
    return _is_sha256(supplied) and supplied == _sha256(payload)


def verify_pr572_live_causal_host_receipt(receipt: Any) -> list[str]:
    if not isinstance(receipt, Mapping):
        return ["PR572_RECEIPT_NOT_MAPPING"]
    if set(receipt) != PR572_FIELDS:
        return ["PR572_RECEIPT_FIELDS_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR572_VERSION:
        violations.append("PR572_VERSION_MISMATCH")
    for field in _PR572_TRUE:
        if receipt.get(field) is not True:
            violations.append("PR572_REQUIRED_TRUE:" + field)
    for field in _PR572_FALSE:
        if receipt.get(field) is not False:
            violations.append("PR572_CEILING_VIOLATED:" + field)
    if not _authority_is_false(receipt.get("authority")):
        violations.append("PR572_AUTHORITY_NOT_FALSE")
    if receipt.get("causal_pre_closure_status") != "HOLD":
        violations.append("PR572_CAUSAL_PRE_NOT_HOLD")
    if receipt.get("causal_post_closure_status") != "CLOSED":
        violations.append("PR572_CAUSAL_POST_NOT_CLOSED")
    for field in (
        "file_id",
        "source_generation",
        "full_source_byte_len",
        "target_byte_start",
        "target_byte_end",
    ):
        if not _require_non_bool_int(receipt.get(field)):
            violations.append("PR572_INTEGER_INVALID:" + field)
    start = receipt.get("target_byte_start")
    end = receipt.get("target_byte_end")
    if type(start) is int and type(end) is int and start >= end:
        violations.append("PR572_TARGET_SPAN_INVALID")
    path = receipt.get("relative_path")
    if not isinstance(path, str) or not path:
        violations.append("PR572_RELATIVE_PATH_INVALID")
    witness_ref = receipt.get("matched_live_post_source_witness_ref")
    if not isinstance(witness_ref, str) or not witness_ref:
        violations.append("PR572_WITNESS_REF_INVALID")
    for field in (
        "raw_slice_projection_payload_sha256",
        "full_source_sha256_hex",
        "target_slice_sha256_hex",
        "selected_target_semantic_handle_digest_hex",
    ):
        if not _is_sha256(receipt.get(field)):
            violations.append("PR572_SHA256_INVALID:" + field)
    for field in (
        "post_source_projection_receipt_identity",
        "causal_post_o10_receipt_identity",
    ):
        if not _identity_is_mapping(receipt.get(field)):
            violations.append("PR572_IDENTITY_INVALID:" + field)
    states = receipt.get("host_gate_states")
    if not isinstance(states, Mapping):
        violations.append("PR572_HOST_GATE_STATES_INVALID")
    else:
        expected = _expected_host_metadata(states)
        if expected is None:
            violations.append("PR572_HOST_GATE_STATES_INVALID")
        else:
            disposition, complete = expected
            if receipt.get("host_disposition") != disposition:
                violations.append("PR572_HOST_DISPOSITION_MISMATCH")
            if receipt.get("host_observation_set_complete") is not complete:
                violations.append("PR572_HOST_COMPLETENESS_MISMATCH")
    if not _verify_pr572_receipt_identity(receipt):
        violations.append("PR572_RECEIPT_IDENTITY_MISMATCH")
    return list(dict.fromkeys(violations))


def _pr568_core(receipt: Mapping[str, Any]) -> dict[str, Any]:
    dependency = receipt["dependency_key"]
    return {
        "post_source_projection_receipt_identity": receipt[
            "post_source_projection_receipt_identity"
        ],
        "causal_post_closure_receipt_identity": receipt[
            "causal_post_closure_receipt_identity"
        ],
        "file_id": dependency["file_id"],
        "relative_path": dependency["relative_path"],
        "source_generation": receipt["source_generation"],
        "full_source_sha256_hex": receipt["full_source_sha256_hex"],
        "full_source_byte_len": receipt["full_source_byte_len"],
        "target_byte_start": receipt["target_byte_start"],
        "target_byte_end": receipt["target_byte_end"],
        "target_slice_byte_len": receipt["target_slice_byte_len"],
        "target_slice_sha256_hex": receipt["target_slice_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": receipt[
            "selected_target_semantic_handle_digest_hex"
        ],
    }


def _pr572_core(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "post_source_projection_receipt_identity": receipt[
            "post_source_projection_receipt_identity"
        ],
        "causal_post_closure_receipt_identity": receipt[
            "causal_post_o10_receipt_identity"
        ],
        "file_id": receipt["file_id"],
        "relative_path": receipt["relative_path"],
        "source_generation": receipt["source_generation"],
        "full_source_sha256_hex": receipt["full_source_sha256_hex"],
        "full_source_byte_len": receipt["full_source_byte_len"],
        "target_byte_start": receipt["target_byte_start"],
        "target_byte_end": receipt["target_byte_end"],
        "target_slice_byte_len": receipt["target_byte_end"] - receipt["target_byte_start"],
        "target_slice_sha256_hex": receipt["target_slice_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": receipt[
            "selected_target_semantic_handle_digest_hex"
        ],
    }


def verify_same_live_causal_world_host(
    *,
    pr568_live_causal_artifact_receipt: Mapping[str, Any],
    pr572_live_causal_host_receipt: Mapping[str, Any],
) -> list[str]:
    violations = [
        "PR568_" + item
        for item in verify_pr568_live_causal_artifact_receipt(
            pr568_live_causal_artifact_receipt
        )
    ]
    violations.extend(
        "PR572_" + item
        for item in verify_pr572_live_causal_host_receipt(pr572_live_causal_host_receipt)
    )
    if violations:
        return list(dict.fromkeys(violations))
    left = _pr568_core(pr568_live_causal_artifact_receipt)
    right = _pr572_core(pr572_live_causal_host_receipt)
    for field in left:
        if left[field] != right[field]:
            violations.append("LIVE_CAUSAL_WORLD_MISMATCH:" + field)
    return violations


def _authority_ceiling() -> dict[str, bool]:
    return {
        "review_authorized": False,
        "mutation_authorized": False,
        "execution_authorized": False,
        "commit_authorized": False,
        "merge_authorized": False,
        "promotion_authorized": False,
        "provider_effect_authorized": False,
        "public_effect_authorized": False,
        "human_authority": False,
    }


def admit_same_live_causal_world_host(
    *,
    pr568_live_causal_artifact_receipt: Mapping[str, Any],
    pr572_live_causal_host_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    violations = verify_same_live_causal_world_host(
        pr568_live_causal_artifact_receipt=pr568_live_causal_artifact_receipt,
        pr572_live_causal_host_receipt=pr572_live_causal_host_receipt,
    )
    if violations:
        raise ValueError("same live causal world host failed: " + ",".join(violations))
    core = _pr568_core(pr568_live_causal_artifact_receipt)
    states = dict(pr572_live_causal_host_receipt["host_gate_states"])
    payload: dict[str, Any] = {
        "version": VERSION,
        "same_live_causal_world_proven": True,
        "same_post_source_projection_identity_proven": True,
        "same_causal_o10_closure_identity_proven": True,
        "same_source_instance_proven": True,
        "same_target_slice_proven": True,
        "same_opaque_semantic_handle_proven": True,
        "live_causal_artifact_core_digest": _sha256(core),
        "host_state_in_artifact_identity": False,
        "host_gate_states": states,
        "host_disposition": pr572_live_causal_host_receipt["host_disposition"],
        "host_observation_set_complete": pr572_live_causal_host_receipt[
            "host_observation_set_complete"
        ],
        "host_state_digest": _sha256(
            {
                "host_gate_states": states,
                "host_disposition": pr572_live_causal_host_receipt["host_disposition"],
                "host_observation_set_complete": pr572_live_causal_host_receipt[
                    "host_observation_set_complete"
                ],
            }
        ),
        "pr568_receipt_producer_authenticated": False,
        "pr572_receipt_producer_authenticated": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "semantic_identity_proven": False,
        "semantic_repair_correctness_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "authority": _authority_ceiling(),
    }
    out = dict(payload)
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": _sha256(payload),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
