#!/usr/bin/env python3
"""Bind PR541 portable higher-owner evidence to PR539's exact POST source instance.

PR539 owns cross-runtime continuity between one canonical WorkCapsule POST-CLOSED source instance
and PR537's portable canonical-target projection. PR541 owns a portable envelope over the reduced
PR538 higher-owner chain and nests that same PR537 projection while requiring the projected target
handle to equal the continuous higher-owner semantic handle.

This D0 membrane composes only those public evidence surfaces. It proves that one continuity-bound
portable canonical target belongs to the exact repaired source instance consumed by the canonical
WorkCapsule POST lifecycle. It does not authenticate the projection producer, prove semantic repair
correctness, mint source currentness, narrow invalidation, or grant review/effect authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_post_repair_source_projection_continuity import (
    admit_post_repair_source_projection_continuity,
    verify_portable_canonical_target_projection,
    verify_post_repair_source_projection_continuity,
)

VERSION = "AURA_WORKCAPSULE_POST_SOURCE_PORTABLE_HIGHER_OWNER_CONTINUITY_V1"
OWNER_CHAIN_SCHEMA = "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1"
OWNER_CHAIN_CANONICALIZATION = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1"

OWNER_CHAIN_PREFIX = "OWNER_CHAIN_"
SOURCE_CONTINUITY_PREFIX = "SOURCE_CONTINUITY_"
OWNER_CHAIN_HANDLE_MISMATCH = "OWNER_CHAIN_HANDLE_MISMATCH"
SOURCE_RECEIPT_HANDLE_MISMATCH = "SOURCE_RECEIPT_HANDLE_MISMATCH"
SOURCE_RECEIPT_PROJECTION_DIGEST_MISMATCH = "SOURCE_RECEIPT_PROJECTION_DIGEST_MISMATCH"

_OWNER_CHAIN_FIELDS = (
    "schema",
    "version",
    "canonicalization_profile",
    "canonical_target_projection",
    "continuous_semantic_handle_digest_hex",
    "outer_constructor_reproved_by_inner_owner",
    "one_canonical_post_edit_consequence",
    "higher_owner_semantic_handle_continuity_proven",
    "producer_authenticated",
    "runtime_name_resolution_proven",
    "call_graph_proven",
    "semantic_patch_correctness_proven",
    "b_minus_approved",
    "review_authorized",
    "mutation_authorized",
    "execution_authorized",
    "commit_authorized",
    "merge_authorized",
    "promotion_authorized",
    "provider_effect_authorized",
    "public_effect_authorized",
    "human_authority",
)

_NEGATIVE_OWNER_CHAIN_FIELDS = (
    "producer_authenticated",
    "runtime_name_resolution_proven",
    "call_graph_proven",
    "semantic_patch_correctness_proven",
    "b_minus_approved",
    "review_authorized",
    "mutation_authorized",
    "execution_authorized",
    "commit_authorized",
    "merge_authorized",
    "promotion_authorized",
    "provider_effect_authorized",
    "public_effect_authorized",
    "human_authority",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _owner_chain_payload_bytes(payload: dict[str, Any]) -> bytes:
    ordered = {field: payload[field] for field in _OWNER_CHAIN_FIELDS}
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def verify_portable_higher_owner_owner_chain_projection(projection: dict[str, Any]) -> list[str]:
    """Validate PR541's stable portable owner-chain contract without producer authentication."""
    if not isinstance(projection, dict) or set(projection) != {"payload", "payload_sha256"}:
        return ["MALFORMED_OWNER_CHAIN_ENVELOPE"]
    payload = projection.get("payload")
    if not isinstance(payload, dict):
        return ["MALFORMED_OWNER_CHAIN_PAYLOAD"]
    if set(payload) != set(_OWNER_CHAIN_FIELDS):
        return ["OWNER_CHAIN_SCHEMA_FIELDS_MISMATCH"]

    violations: list[str] = []
    if payload.get("schema") != OWNER_CHAIN_SCHEMA or payload.get("version") != 1:
        violations.append("OWNER_CHAIN_SCHEMA_VERSION_MISMATCH")
    if payload.get("canonicalization_profile") != OWNER_CHAIN_CANONICALIZATION:
        violations.append("OWNER_CHAIN_CANONICALIZATION_PROFILE_MISMATCH")

    for field in (
        "outer_constructor_reproved_by_inner_owner",
        "one_canonical_post_edit_consequence",
        "higher_owner_semantic_handle_continuity_proven",
    ):
        if payload.get(field) is not True:
            violations.append(f"OWNER_CHAIN_PROOF_FLAG_MISSING:{field}")

    for field in _NEGATIVE_OWNER_CHAIN_FIELDS:
        if payload.get(field) is not False:
            violations.append(f"OWNER_CHAIN_CEILING_VIOLATED:{field}")

    continuous_handle = payload.get("continuous_semantic_handle_digest_hex")
    if not _is_sha256(continuous_handle):
        violations.append("OWNER_CHAIN_CONTINUOUS_HANDLE_INVALID")

    nested = payload.get("canonical_target_projection")
    nested_violations = verify_portable_canonical_target_projection(nested)
    violations.extend("NESTED_" + item for item in nested_violations)
    if not nested_violations and _is_sha256(continuous_handle):
        projected = nested["payload"].get("selected_target_semantic_handle_digest_hex")
        if projected != continuous_handle:
            violations.append(OWNER_CHAIN_HANDLE_MISMATCH)

    supplied = projection.get("payload_sha256")
    if not _is_sha256(supplied):
        violations.append("OWNER_CHAIN_PAYLOAD_SHA256_INVALID")
    else:
        expected = hashlib.sha256(_owner_chain_payload_bytes(payload)).hexdigest()
        if supplied != expected:
            violations.append("OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH")
    return list(dict.fromkeys(violations))


def verify_post_source_portable_higher_owner_continuity(
    *,
    pre_root,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    pre_observation_closure_receipt: dict[str, Any],
    post_root,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    post_observation_bound_receipt: dict[str, Any],
    portable_higher_owner_projection: dict[str, Any],
) -> list[str]:
    """Require PR541 continuity-bound portable evidence to describe PR539's exact POST source."""
    owner_violations = verify_portable_higher_owner_owner_chain_projection(
        portable_higher_owner_projection
    )
    if owner_violations:
        return [OWNER_CHAIN_PREFIX + item for item in owner_violations]

    owner_payload = portable_higher_owner_projection["payload"]
    nested_projection = owner_payload["canonical_target_projection"]
    source_kwargs = {
        "pre_root": pre_root,
        "pre_codemap": pre_codemap,
        "pre_anchor_manifest": pre_anchor_manifest,
        "pre_witness_manifest": pre_witness_manifest,
        "previous_binding": previous_binding,
        "pre_graph_witness": pre_graph_witness,
        "reentry_receipt": reentry_receipt,
        "pre_observation_closure_receipt": pre_observation_closure_receipt,
        "post_root": post_root,
        "post_codemap": post_codemap,
        "post_anchor_manifest": post_anchor_manifest,
        "post_witness_manifest": post_witness_manifest,
        "post_graph_witness": post_graph_witness,
        "post_observation_bound_receipt": post_observation_bound_receipt,
        "astge_projection": nested_projection,
    }
    source_violations = verify_post_repair_source_projection_continuity(**source_kwargs)
    if source_violations:
        return [SOURCE_CONTINUITY_PREFIX + item for item in source_violations]

    source_receipt = admit_post_repair_source_projection_continuity(**source_kwargs)
    violations: list[str] = []
    continuous_handle = owner_payload["continuous_semantic_handle_digest_hex"]
    if source_receipt.get("selected_target_semantic_handle_digest_hex") != continuous_handle:
        violations.append(SOURCE_RECEIPT_HANDLE_MISMATCH)
    if source_receipt.get("portable_projection_payload_sha256") != nested_projection.get(
        "payload_sha256"
    ):
        violations.append(SOURCE_RECEIPT_PROJECTION_DIGEST_MISMATCH)
    return violations


def admit_post_source_portable_higher_owner_continuity(**kwargs: Any) -> dict[str, Any]:
    """Emit one exact POST-source + portable-higher-owner continuity receipt or fail closed."""
    violations = verify_post_source_portable_higher_owner_continuity(**kwargs)
    if violations:
        raise ValueError("post-source portable higher-owner continuity failed: " + ",".join(violations))

    owner_projection = kwargs["portable_higher_owner_projection"]
    nested_projection = owner_projection["payload"]["canonical_target_projection"]
    source_kwargs = dict(kwargs)
    source_kwargs.pop("portable_higher_owner_projection")
    source_kwargs["astge_projection"] = nested_projection
    source_receipt = admit_post_repair_source_projection_continuity(**source_kwargs)

    out: dict[str, Any] = {
        "version": VERSION,
        "source_instance_continuity_proven": True,
        "portable_higher_owner_owner_chain_verified": True,
        "higher_owner_semantic_handle_continuity_proven": True,
        "post_closure_status": source_receipt["post_closure_status"],
        "repaired_dependency_key": source_receipt["repaired_dependency_key"],
        "post_source_generation": source_receipt["post_source_generation"],
        "post_source_sha256": source_receipt["post_source_sha256"],
        "post_source_byte_len": source_receipt["post_source_byte_len"],
        "selected_target_scope_local_id": source_receipt["selected_target_scope_local_id"],
        "selected_target_parent_scope_local_id": source_receipt[
            "selected_target_parent_scope_local_id"
        ],
        "selected_target_syntax_ordinal": source_receipt["selected_target_syntax_ordinal"],
        "selected_target_byte_start": source_receipt["selected_target_byte_start"],
        "selected_target_byte_end": source_receipt["selected_target_byte_end"],
        "continuous_semantic_handle_digest_hex": owner_projection["payload"][
            "continuous_semantic_handle_digest_hex"
        ],
        "portable_owner_chain_payload_sha256": owner_projection["payload_sha256"],
        "nested_canonical_target_projection_payload_sha256": nested_projection["payload_sha256"],
        "source_continuity_receipt_identity": source_receipt["receipt_identity"],
        "projection_producer_authenticated": False,
        "source_currentness_minted_by_child": False,
        "semantic_repair_correctness_minted": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_dependency_cone_proven": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
        "b_minus_approved": False,
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
