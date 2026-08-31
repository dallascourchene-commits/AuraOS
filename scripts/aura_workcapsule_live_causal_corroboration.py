#!/usr/bin/env python3
"""Correlate two independently hosted live-causal raw-slice proof artifacts.

PR568 and PR572 close the same bounded source-world relation through different parent
and execution topologies. This membrane proves only that their closed consequence
receipts name the same live source instance, target slice, POST source projection,
and causal O10 closure while preserving distinct proof-artifact identities.

Corroboration is not producer authentication, semantic equivalence, semantic truth,
or effect authority. The child does not reimplement either causal owner.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_CORROBORATION_V1"
PR568_VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_RAW_SLICE_JOIN_V1"
PR572_VERSION = "AURA_WORKCAPSULE_LIVE_CAUSAL_RAW_SLICE_HOST_V1"

PR568_FIELDS = {
    "version", "live_recursive_target_raw_slice_reproved", "portable_raw_slice_transport_reproved",
    "causal_post_owner_reproved_from_raw_evidence", "live_recursive_raw_slice_bound_to_exact_causal_post",
    "same_exact_post_source_instance_proven", "same_exact_raw_target_slice_proven",
    "post_source_projection_receipt_identity", "causal_post_closure_receipt_identity", "dependency_key",
    "source_generation", "full_source_sha256_hex", "full_source_byte_len", "target_byte_start",
    "target_byte_end", "target_slice_byte_len", "target_slice_sha256_hex",
    "selected_target_semantic_handle_digest_hex", "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice", "raw_slice_projection_producer_authenticated",
    "source_observation_producer_authenticated", "semantic_repair_correctness_proven",
    "source_to_graph_dependency_map_proven", "node_level_invalidation_cone_proven",
    "runtime_name_resolution_proven", "call_graph_proven", "b_minus_approved", "authority",
}
PR572_FIELDS = {
    "version", "live_pr560_to_pr556_causal_slice_join_proven", "portable_raw_slice_projection_verified",
    "live_post_source_coordinate_match_proven", "causal_post_owner_reproved_by_child",
    "post_source_projection_receipt_identity", "matched_live_post_source_witness_ref",
    "raw_slice_projection_payload_sha256", "file_id", "relative_path", "source_generation",
    "full_source_sha256_hex", "full_source_byte_len", "target_byte_start", "target_byte_end",
    "target_slice_sha256_hex", "selected_target_semantic_handle_digest_hex", "causal_pre_closure_status",
    "causal_post_closure_status", "causal_post_o10_receipt_identity", "pre_reentry_receipt_reused_for_post_o10",
    "fresh_post_reentry_receipt_substituted", "host_disposition", "host_gate_states",
    "host_observation_set_complete", "host_observation_authority_proven", "resolver_trust_proven",
    "trusted_continuation_ready", "host_effect_ready", "raw_slice_promoted_to_host_rank",
    "semantic_handle_derived_from_raw_slice", "semantic_identity_proven_by_raw_slice",
    "producer_authenticated", "semantic_repair_correctness_proven", "source_currentness_minted",
    "authority", "receipt_identity",
}
PR568_TRUE = {"live_recursive_target_raw_slice_reproved", "portable_raw_slice_transport_reproved", "causal_post_owner_reproved_from_raw_evidence", "live_recursive_raw_slice_bound_to_exact_causal_post", "same_exact_post_source_instance_proven", "same_exact_raw_target_slice_proven"}
PR568_FALSE = {"semantic_handle_derived_from_raw_slice", "semantic_identity_proven_by_raw_slice", "raw_slice_projection_producer_authenticated", "source_observation_producer_authenticated", "semantic_repair_correctness_proven", "source_to_graph_dependency_map_proven", "node_level_invalidation_cone_proven", "runtime_name_resolution_proven", "call_graph_proven", "b_minus_approved"}
PR572_TRUE = {"live_pr560_to_pr556_causal_slice_join_proven", "portable_raw_slice_projection_verified", "live_post_source_coordinate_match_proven", "causal_post_owner_reproved_by_child", "pre_reentry_receipt_reused_for_post_o10"}
PR572_FALSE = {"fresh_post_reentry_receipt_substituted", "host_observation_authority_proven", "resolver_trust_proven", "trusted_continuation_ready", "host_effect_ready", "raw_slice_promoted_to_host_rank", "semantic_handle_derived_from_raw_slice", "semantic_identity_proven_by_raw_slice", "producer_authenticated", "semantic_repair_correctness_proven", "source_currentness_minted"}
PR568_AUTHORITY_FIELDS = {"review_authorized", "mutation_authorized", "execution_authorized", "commit_authorized", "merge_authorized", "promotion_authorized", "provider_effect_authorized", "public_effect_authorized", "human_authority"}
PR572_AUTHORITY_FIELDS = {"review_authorized", "execution_authorized", "commit_authorized", "merge_authorized", "promotion_authorized", "provider_effect_authorized", "public_effect_authorized", "human_authority"}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def artifact_ref(receipt: dict[str, Any]) -> str:
    return "aura-proof-artifact-sha256:" + hashlib.sha256(_canonical_bytes(receipt)).hexdigest()


def _authority_violations(receipt: dict[str, Any], expected_fields: set[str], prefix: str) -> list[str]:
    authority = receipt.get("authority")
    if not isinstance(authority, dict) or set(authority) != expected_fields:
        return [prefix + "AUTHORITY_SCHEMA_MISMATCH"]
    if any(type(authority[field]) is not bool for field in expected_fields):
        return [prefix + "AUTHORITY_TYPE_MISMATCH"]
    if any(authority.values()):
        return [prefix + "AUTHORITY_WIDENED"]
    return []


def _flag_violations(receipt: dict[str, Any], true_fields: set[str], false_fields: set[str], prefix: str) -> list[str]:
    violations: list[str] = []
    for field in true_fields:
        if receipt.get(field) is not True:
            violations.append(prefix + "REQUIRED_TRUE:" + field)
    for field in false_fields:
        if receipt.get(field) is not False:
            violations.append(prefix + "REQUIRED_FALSE:" + field)
    return violations


def _verify_pr568(receipt: dict[str, Any]) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != PR568_FIELDS:
        return ["PR568_RECEIPT_SCHEMA_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR568_VERSION:
        violations.append("PR568_VERSION_MISMATCH")
    dependency_key = receipt.get("dependency_key")
    if not isinstance(dependency_key, dict) or set(dependency_key) != {"file_id", "relative_path"}:
        violations.append("PR568_DEPENDENCY_KEY_SCHEMA_MISMATCH")
    violations.extend(_flag_violations(receipt, PR568_TRUE, PR568_FALSE, "PR568_"))
    violations.extend(_authority_violations(receipt, PR568_AUTHORITY_FIELDS, "PR568_"))
    return violations


def _verify_pr572(receipt: dict[str, Any]) -> list[str]:
    if not isinstance(receipt, dict) or set(receipt) != PR572_FIELDS:
        return ["PR572_RECEIPT_SCHEMA_MISMATCH"]
    violations: list[str] = []
    if receipt.get("version") != PR572_VERSION:
        violations.append("PR572_VERSION_MISMATCH")
    if receipt.get("causal_pre_closure_status") != "HOLD":
        violations.append("PR572_PRE_STATUS_MISMATCH")
    if receipt.get("causal_post_closure_status") != "CLOSED":
        violations.append("PR572_POST_STATUS_MISMATCH")
    violations.extend(_flag_violations(receipt, PR572_TRUE, PR572_FALSE, "PR572_"))
    violations.extend(_authority_violations(receipt, PR572_AUTHORITY_FIELDS, "PR572_"))
    identity = receipt.get("receipt_identity")
    if not isinstance(identity, dict):
        violations.append("PR572_RECEIPT_IDENTITY_MALFORMED")
    else:
        expected_identity_fields = {"kind", "algorithm_or_provider", "canonicalization_profile", "scope_profile", "value", "schema_version"}
        if set(identity) != expected_identity_fields:
            violations.append("PR572_RECEIPT_IDENTITY_SCHEMA_MISMATCH")
        elif identity.get("kind") != "DIGEST" or identity.get("algorithm_or_provider") != "sha256" or identity.get("canonicalization_profile") != "JSON_SORT_KEYS_COMPACT_UTF8_V1" or identity.get("scope_profile") != PR572_VERSION or identity.get("value") != hashlib.sha256(_canonical_bytes({k: v for k, v in receipt.items() if k != "receipt_identity"})).hexdigest():
            violations.append("PR572_RECEIPT_IDENTITY_MISMATCH")
    return violations


def verify_live_causal_corroboration(*, pr568_receipt: dict[str, Any], pr572_receipt: dict[str, Any]) -> list[str]:
    violations = _verify_pr568(pr568_receipt) + _verify_pr572(pr572_receipt)
    if violations:
        return list(dict.fromkeys(violations))
    source568 = (pr568_receipt["dependency_key"]["file_id"], pr568_receipt["dependency_key"]["relative_path"], pr568_receipt["source_generation"], pr568_receipt["full_source_sha256_hex"], pr568_receipt["full_source_byte_len"])
    source572 = (pr572_receipt["file_id"], pr572_receipt["relative_path"], pr572_receipt["source_generation"], pr572_receipt["full_source_sha256_hex"], pr572_receipt["full_source_byte_len"])
    if source568 != source572:
        violations.append("LIVE_SOURCE_INSTANCE_MISMATCH")
    target568 = (pr568_receipt["target_byte_start"], pr568_receipt["target_byte_end"], pr568_receipt["target_slice_sha256_hex"], pr568_receipt["selected_target_semantic_handle_digest_hex"])
    target572 = (pr572_receipt["target_byte_start"], pr572_receipt["target_byte_end"], pr572_receipt["target_slice_sha256_hex"], pr572_receipt["selected_target_semantic_handle_digest_hex"])
    if target568 != target572:
        violations.append("LIVE_TARGET_SLICE_MISMATCH")
    if pr568_receipt["post_source_projection_receipt_identity"] != pr572_receipt["post_source_projection_receipt_identity"]:
        violations.append("POST_SOURCE_PROJECTION_IDENTITY_MISMATCH")
    if pr568_receipt["causal_post_closure_receipt_identity"] != pr572_receipt["causal_post_o10_receipt_identity"]:
        violations.append("CAUSAL_O10_IDENTITY_MISMATCH")
    if artifact_ref(pr568_receipt) == artifact_ref(pr572_receipt):
        violations.append("INDEPENDENT_PROOF_ARTIFACTS_COLLAPSED")
    return list(dict.fromkeys(violations))


def admit_live_causal_corroboration(*, pr568_receipt: dict[str, Any], pr572_receipt: dict[str, Any]) -> dict[str, Any]:
    violations = verify_live_causal_corroboration(pr568_receipt=pr568_receipt, pr572_receipt=pr572_receipt)
    if violations:
        raise ValueError("live causal corroboration failed: " + ",".join(violations))
    out = {
        "version": VERSION,
        "same_live_source_instance_proven": True,
        "same_live_target_slice_proven": True,
        "same_post_source_projection_identity_proven": True,
        "same_causal_o10_identity_proven": True,
        "independent_proof_artifacts_preserved": True,
        "pr568_artifact_ref": artifact_ref(pr568_receipt),
        "pr572_artifact_ref": artifact_ref(pr572_receipt),
        "proof_artifact_refs_distinct": True,
        "source_instance": {"file_id": pr572_receipt["file_id"], "relative_path": pr572_receipt["relative_path"], "source_generation": pr572_receipt["source_generation"], "full_source_sha256_hex": pr572_receipt["full_source_sha256_hex"], "full_source_byte_len": pr572_receipt["full_source_byte_len"]},
        "target_slice": {"target_byte_start": pr572_receipt["target_byte_start"], "target_byte_end": pr572_receipt["target_byte_end"], "target_slice_sha256_hex": pr572_receipt["target_slice_sha256_hex"], "selected_target_semantic_handle_digest_hex": pr572_receipt["selected_target_semantic_handle_digest_hex"]},
        "semantic_equivalence_proven": False,
        "producer_authentication_proven": False,
        "host_observation_authority_proven": False,
        "effect_authority_proven": False,
        "semantic_k27_authority_proven": False,
        "authority": {"review_authorized": False, "mutation_authorized": False, "execution_authorized": False, "commit_authorized": False, "merge_authorized": False, "promotion_authorized": False, "provider_effect_authorized": False, "public_effect_authorized": False, "human_authority": False},
    }
    out["receipt_identity"] = {"kind": "DIGEST", "algorithm_or_provider": "sha256", "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1", "scope_profile": VERSION, "value": hashlib.sha256(_canonical_bytes(out)).hexdigest(), "schema_version": "DigestOrImmutableIdentityV1-compatible"}
    return out
