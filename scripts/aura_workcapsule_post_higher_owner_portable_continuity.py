#!/usr/bin/env python3
"""Bind one canonical WorkCapsule POST source instance to one portable higher-owner owner chain.

PR539 proves that a portable canonical-target projection names the exact ACTIVE/CURRENT source
instance consumed by one canonical POST CLOSED WorkCapsule lifecycle. PR541 wraps that exact
canonical-target projection in a deterministic portable higher-owner envelope whose semantic-handle
digest is continuous with the reduced higher-owner owner chain.

This D0 membrane accepts only the PR541-shaped outer envelope. It verifies that envelope, extracts
its single nested canonical-target projection, and delegates all temporal/source-instance checks to
PR539 using that exact nested object. There is deliberately no second caller-supplied projection
slot, so a locally valid source projection and a different locally valid higher-owner projection
cannot be joined by the child.

Transport integrity and cross-owner continuity are not producer authentication, semantic repair
correctness, review approval, mutation authority, or external-effect authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_post_repair_source_projection_continuity import (
    admit_post_repair_source_projection_continuity,
    verify_portable_canonical_target_projection,
    verify_post_repair_source_projection_continuity,
)

VERSION = "AURA_WORKCAPSULE_POST_HIGHER_OWNER_PORTABLE_CONTINUITY_V1"
OWNER_CHAIN_SCHEMA = "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1"
CANONICALIZATION_PROFILE = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1"
OWNER_PREFIX = "HIGHER_OWNER_"
SOURCE_PREFIX = "SOURCE_INSTANCE_"

_OUTER_FIELDS = (
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

_NEGATIVE_OUTER_FIELDS = (
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


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _outer_payload_bytes(payload: dict[str, Any]) -> bytes:
    ordered = {field: payload[field] for field in _OUTER_FIELDS}
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_portable_higher_owner_projection(projection: dict[str, Any]) -> list[str]:
    """Validate PR541's stable portable envelope without authenticating its producer."""
    if not isinstance(projection, dict) or set(projection) != {"payload", "payload_sha256"}:
        return ["MALFORMED_HIGHER_OWNER_ENVELOPE"]
    payload = projection.get("payload")
    if not isinstance(payload, dict):
        return ["MALFORMED_HIGHER_OWNER_PAYLOAD"]
    if set(payload) != set(_OUTER_FIELDS):
        return ["HIGHER_OWNER_SCHEMA_FIELDS_MISMATCH"]

    violations: list[str] = []
    if payload.get("schema") != OWNER_CHAIN_SCHEMA or payload.get("version") != 1:
        violations.append("HIGHER_OWNER_SCHEMA_VERSION_MISMATCH")
    if payload.get("canonicalization_profile") != CANONICALIZATION_PROFILE:
        violations.append("HIGHER_OWNER_CANONICALIZATION_PROFILE_MISMATCH")

    for field in (
        "outer_constructor_reproved_by_inner_owner",
        "one_canonical_post_edit_consequence",
        "higher_owner_semantic_handle_continuity_proven",
    ):
        if payload.get(field) is not True:
            violations.append(f"HIGHER_OWNER_REQUIRED_CLAIM_FALSE:{field}")
    for field in _NEGATIVE_OUTER_FIELDS:
        if payload.get(field) is not False:
            violations.append(f"HIGHER_OWNER_CEILING_VIOLATED:{field}")

    nested = payload.get("canonical_target_projection")
    if not isinstance(nested, dict):
        violations.append("HIGHER_OWNER_NESTED_PROJECTION_MISSING")
    else:
        for item in verify_portable_canonical_target_projection(nested):
            violations.append("NESTED_" + item)
        handle = payload.get("continuous_semantic_handle_digest_hex")
        nested_handle = nested.get("payload", {}).get("selected_target_semantic_handle_digest_hex")
        if not _is_sha256(handle):
            violations.append("HIGHER_OWNER_CONTINUOUS_HANDLE_INVALID")
        elif nested_handle != handle:
            violations.append("HIGHER_OWNER_CONTINUOUS_HANDLE_MISMATCH")

    supplied = projection.get("payload_sha256")
    if not _is_sha256(supplied):
        violations.append("HIGHER_OWNER_PAYLOAD_SHA256_INVALID")
    else:
        expected = hashlib.sha256(_outer_payload_bytes(payload)).hexdigest()
        if supplied != expected:
            violations.append("HIGHER_OWNER_PAYLOAD_DIGEST_MISMATCH")
    return list(dict.fromkeys(violations))


def verify_post_higher_owner_portable_continuity(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    pre_observation_closure_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    post_observation_bound_receipt: dict[str, Any],
    higher_owner_projection: dict[str, Any],
) -> list[str]:
    """Require one exact nested projection to satisfy both PR539 and PR541 consequence planes."""
    owner_violations = verify_portable_higher_owner_projection(higher_owner_projection)
    if owner_violations:
        return [OWNER_PREFIX + item for item in owner_violations]

    nested = higher_owner_projection["payload"]["canonical_target_projection"]
    source_violations = verify_post_repair_source_projection_continuity(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        pre_observation_closure_receipt=pre_observation_closure_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        post_observation_bound_receipt=post_observation_bound_receipt,
        astge_projection=nested,
    )
    return [SOURCE_PREFIX + item for item in source_violations]


def admit_post_higher_owner_portable_continuity(**kwargs: Any) -> dict[str, Any]:
    """Emit a narrow shared-pivot continuity witness or fail closed."""
    violations = verify_post_higher_owner_portable_continuity(**kwargs)
    if violations:
        raise ValueError("post higher-owner portable continuity failed: " + ",".join(violations))

    source_kwargs = dict(kwargs)
    higher_owner_projection = source_kwargs.pop("higher_owner_projection")
    nested = higher_owner_projection["payload"]["canonical_target_projection"]
    source_kwargs["astge_projection"] = nested
    source_admission = admit_post_repair_source_projection_continuity(**source_kwargs)
    outer_payload = higher_owner_projection["payload"]

    out: dict[str, Any] = {
        "version": VERSION,
        "post_source_instance_continuity_proven": True,
        "portable_higher_owner_owner_chain_verified": True,
        "same_nested_canonical_target_projection_bound": True,
        "nested_projection_payload_sha256": nested["payload_sha256"],
        "higher_owner_projection_payload_sha256": higher_owner_projection["payload_sha256"],
        "continuous_semantic_handle_digest_hex": outer_payload["continuous_semantic_handle_digest_hex"],
        "post_closure_status": source_admission["post_closure_status"],
        "repaired_dependency_key": source_admission["repaired_dependency_key"],
        "post_source_generation": source_admission["post_source_generation"],
        "post_source_sha256": source_admission["post_source_sha256"],
        "post_source_byte_len": source_admission["post_source_byte_len"],
        "higher_owner_semantic_handle_continuity_proven": True,
        "projection_producer_authenticated": False,
        "higher_owner_projection_producer_authenticated": False,
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
        "scope_profile": "WORKCAPSULE_POST_HIGHER_OWNER_PORTABLE_CONTINUITY_V1",
        "value": hashlib.sha256(_canonical_bytes(out)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
