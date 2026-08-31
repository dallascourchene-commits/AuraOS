#!/usr/bin/env python3
"""Bind PR548's exact scoped portable target to PR541's portable higher-owner chain.

The child proves structural continuity only.  It recursively canonicalizes the PR541
transport according to the exact Rust struct field order, so Python map insertion order
cannot create a second valid payload digest.  It then requires PR548's already-converged
post-edit target to be the exact nested PR537 projection carried by the higher-owner
chain.  Producer authentication, semantic correctness, re-entry closure, invalidation
narrowing, and all effect authority remain false.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_post_repair_source_projection_continuity import (
    verify_portable_canonical_target_projection,
)
from scripts.aura_workcapsule_scoped_portable_target_identity import (
    admit_scoped_portable_target_identity,
    verify_scoped_portable_target_identity,
)

VERSION = "AURA_WORKCAPSULE_SCOPED_HIGHER_OWNER_PORTABLE_CONTINUITY_V1"
OWNER_SCHEMA = "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1"
CANONICALIZATION = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1"
SCOPED_PREFIX = "SCOPED_TARGET_"
OWNER_PREFIX = "HIGHER_OWNER_"
OUTER_DIGEST_MISMATCH = "OUTER_PAYLOAD_DIGEST_MISMATCH"
PROJECTION_DIGEST_MISMATCH = "SCOPED_TARGET_PROJECTION_DIGEST_MISMATCH"
DEPENDENCY_MISMATCH = "SCOPED_TARGET_DEPENDENCY_MISMATCH"
SOURCE_GENERATION_MISMATCH = "SCOPED_TARGET_SOURCE_GENERATION_MISMATCH"
SOURCE_BODY_MISMATCH = "SCOPED_TARGET_SOURCE_BODY_MISMATCH"
SOURCE_LENGTH_MISMATCH = "SCOPED_TARGET_SOURCE_LENGTH_MISMATCH"
SYNTAX_ORDINAL_MISMATCH = "SCOPED_TARGET_SYNTAX_ORDINAL_MISMATCH"
TARGET_SPAN_MISMATCH = "SCOPED_TARGET_SPAN_MISMATCH"
TARGET_HANDLE_MISMATCH = "SCOPED_TARGET_HANDLE_MISMATCH"

NESTED_PAYLOAD_FIELDS = (
    "schema", "version", "canonicalization_profile", "source_generation_domain",
    "source_generation_value", "source_owner_ref", "relative_path", "file_id",
    "source_sha256_hex", "source_byte_len", "selected_target_scope_local_id",
    "selected_target_parent_scope_local_id", "selected_target_syntax_ordinal",
    "selected_target_byte_start", "selected_target_byte_end",
    "selected_target_semantic_handle_digest_hex", "definition_name",
    "definition_owner_scope_local_id", "definition_target_scope_local_id",
    "selected_current_scope_is_binding_target", "binding_owner_is_selected_parent",
    "local_scope_id_is_semantic_identity", "post_edit_profiled_scope_current",
    "canonical_definition_target_current", "runtime_name_resolution_proven",
    "call_graph_proven", "semantic_patch_correctness_proven", "b_minus_approved",
    "producer_authenticated", "review_authorized", "mutation_authorized",
    "execution_authorized", "commit_authorized", "merge_authorized",
    "promotion_authorized", "provider_effect_authorized", "public_effect_authorized",
    "human_authority",
)

OUTER_PAYLOAD_FIELDS = (
    "schema", "version", "canonicalization_profile", "canonical_target_projection",
    "continuous_semantic_handle_digest_hex", "outer_constructor_reproved_by_inner_owner",
    "one_canonical_post_edit_consequence", "higher_owner_semantic_handle_continuity_proven",
    "producer_authenticated", "runtime_name_resolution_proven", "call_graph_proven",
    "semantic_patch_correctness_proven", "b_minus_approved", "review_authorized",
    "mutation_authorized", "execution_authorized", "commit_authorized",
    "merge_authorized", "promotion_authorized", "provider_effect_authorized",
    "public_effect_authorized", "human_authority",
)

_NEGATIVE_OUTER_FIELDS = (
    "producer_authenticated", "runtime_name_resolution_proven", "call_graph_proven",
    "semantic_patch_correctness_proven", "b_minus_approved", "review_authorized",
    "mutation_authorized", "execution_authorized", "commit_authorized",
    "merge_authorized", "promotion_authorized", "provider_effect_authorized",
    "public_effect_authorized", "human_authority",
)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _compact(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_nested_projection(projection: dict[str, Any]) -> dict[str, Any]:
    """Return the exact PR537 Rust-struct-order representation or fail closed."""
    if not isinstance(projection, dict) or set(projection) != {"payload", "payload_sha256"}:
        raise ValueError("MALFORMED_NESTED_PROJECTION_ENVELOPE")
    payload = projection.get("payload")
    if not isinstance(payload, dict) or set(payload) != set(NESTED_PAYLOAD_FIELDS):
        raise ValueError("MALFORMED_NESTED_PROJECTION_PAYLOAD")
    if type(payload.get("version")) is not int or payload["version"] != 1:
        raise ValueError("NESTED_VERSION_NOT_EXACT_INTEGER_ONE")
    violations = verify_portable_canonical_target_projection(projection)
    if violations:
        raise ValueError("NESTED_PROJECTION_INVALID:" + ",".join(violations))
    ordered_payload = {field: payload[field] for field in NESTED_PAYLOAD_FIELDS}
    expected_nested = hashlib.sha256(_compact(ordered_payload)).hexdigest()
    if projection.get("payload_sha256") != expected_nested:
        raise ValueError("NESTED_CANONICAL_DIGEST_MISMATCH")
    return {"payload": ordered_payload, "payload_sha256": expected_nested}


def canonical_portable_higher_owner_payload_bytes(payload: dict[str, Any]) -> bytes:
    """Reproduce PR541 serde_json::to_vec(payload) recursively and deterministically."""
    if not isinstance(payload, dict) or set(payload) != set(OUTER_PAYLOAD_FIELDS):
        raise ValueError("MALFORMED_OUTER_PAYLOAD")
    normalized_nested = canonical_nested_projection(payload["canonical_target_projection"])
    ordered: dict[str, Any] = {}
    for field in OUTER_PAYLOAD_FIELDS:
        ordered[field] = normalized_nested if field == "canonical_target_projection" else payload[field]
    return _compact(ordered)


def verify_portable_higher_owner_projection(projection: dict[str, Any]) -> list[str]:
    if not isinstance(projection, dict) or set(projection) != {"payload", "payload_sha256"}:
        return ["MALFORMED_OUTER_ENVELOPE"]
    payload = projection.get("payload")
    if not isinstance(payload, dict) or set(payload) != set(OUTER_PAYLOAD_FIELDS):
        return ["MALFORMED_OUTER_PAYLOAD"]
    violations: list[str] = []
    if payload.get("schema") != OWNER_SCHEMA or type(payload.get("version")) is not int or payload.get("version") != 1:
        violations.append("OUTER_SCHEMA_VERSION_MISMATCH")
    if payload.get("canonicalization_profile") != CANONICALIZATION:
        violations.append("OUTER_CANONICALIZATION_PROFILE_MISMATCH")
    for field in (
        "outer_constructor_reproved_by_inner_owner",
        "one_canonical_post_edit_consequence",
        "higher_owner_semantic_handle_continuity_proven",
    ):
        if payload.get(field) is not True:
            violations.append("OUTER_PROOF_FLAG_NOT_EXACT_TRUE:" + field)
    for field in _NEGATIVE_OUTER_FIELDS:
        if payload.get(field) is not False:
            violations.append("OUTER_CEILING_VIOLATED:" + field)
    handle = payload.get("continuous_semantic_handle_digest_hex")
    if not _is_sha256(handle):
        violations.append("OUTER_CONTINUOUS_HANDLE_INVALID")
    try:
        normalized_nested = canonical_nested_projection(payload.get("canonical_target_projection"))
    except (KeyError, TypeError, ValueError) as exc:
        violations.append("NESTED_" + str(exc))
        normalized_nested = None
    if normalized_nested is not None:
        projected = normalized_nested["payload"]["selected_target_semantic_handle_digest_hex"]
        if projected != handle:
            violations.append("OUTER_HIGHER_OWNER_HANDLE_MISMATCH")
        try:
            expected = hashlib.sha256(canonical_portable_higher_owner_payload_bytes(payload)).hexdigest()
        except (KeyError, TypeError, ValueError) as exc:
            violations.append("OUTER_CANONICALIZATION_FAILED:" + str(exc))
        else:
            if not _is_sha256(projection.get("payload_sha256")) or projection["payload_sha256"] != expected:
                violations.append(OUTER_DIGEST_MISMATCH)
    return list(dict.fromkeys(violations))


def verify_scoped_higher_owner_portable_continuity(
    *, scoped_target_inputs: dict[str, Any], higher_owner_projection: dict[str, Any]
) -> list[str]:
    """Require PR548 and PR541 transport evidence to name one exact post-edit target."""
    try:
        scoped_violations = verify_scoped_portable_target_identity(**scoped_target_inputs)
    except (KeyError, TypeError, ValueError):
        scoped_violations = ["MALFORMED_PARENT_INPUTS"]
    owner_violations = verify_portable_higher_owner_projection(higher_owner_projection)
    violations = [SCOPED_PREFIX + item for item in scoped_violations]
    violations.extend(OWNER_PREFIX + item for item in owner_violations)
    if violations:
        return list(dict.fromkeys(violations))

    scoped = admit_scoped_portable_target_identity(**scoped_target_inputs)
    nested = canonical_nested_projection(higher_owner_projection["payload"]["canonical_target_projection"])
    target = nested["payload"]
    if scoped.get("portable_projection_payload_sha256") != nested.get("payload_sha256"):
        violations.append(PROJECTION_DIGEST_MISMATCH)
    if scoped.get("dependency_key") != {"file_id": target.get("file_id"), "relative_path": target.get("relative_path")}:
        violations.append(DEPENDENCY_MISMATCH)
    if scoped.get("post_source_generation") != target.get("source_generation_value"):
        violations.append(SOURCE_GENERATION_MISMATCH)
    if scoped.get("post_source_sha256") != target.get("source_sha256_hex"):
        violations.append(SOURCE_BODY_MISMATCH)
    if scoped.get("post_source_byte_len") != target.get("source_byte_len"):
        violations.append(SOURCE_LENGTH_MISMATCH)
    if scoped.get("selected_target_syntax_ordinal") != target.get("selected_target_syntax_ordinal"):
        violations.append(SYNTAX_ORDINAL_MISMATCH)
    if (scoped.get("selected_target_byte_start"), scoped.get("selected_target_byte_end")) != (
        target.get("selected_target_byte_start"), target.get("selected_target_byte_end")
    ):
        violations.append(TARGET_SPAN_MISMATCH)
    if scoped.get("selected_target_semantic_handle_digest_hex") != target.get("selected_target_semantic_handle_digest_hex"):
        violations.append(TARGET_HANDLE_MISMATCH)
    return list(dict.fromkeys(violations))


def admit_scoped_higher_owner_portable_continuity(**kwargs: Any) -> dict[str, Any]:
    violations = verify_scoped_higher_owner_portable_continuity(**kwargs)
    if violations:
        raise ValueError("scoped higher-owner portable continuity failed: " + ",".join(violations))
    scoped = admit_scoped_portable_target_identity(**kwargs["scoped_target_inputs"])
    projection = kwargs["higher_owner_projection"]
    nested = canonical_nested_projection(projection["payload"]["canonical_target_projection"])
    return {
        "version": VERSION,
        "same_scoped_target_as_higher_owner_projection_proven": True,
        "recursive_cross_runtime_canonicalization_proven": True,
        "same_nested_portable_projection_digest_proven": True,
        "higher_owner_handle_equals_scoped_target_handle_proven": True,
        "dependency_key": dict(scoped["dependency_key"]),
        "post_source_generation": int(scoped["post_source_generation"]),
        "post_source_sha256": str(scoped["post_source_sha256"]),
        "post_source_byte_len": int(scoped["post_source_byte_len"]),
        "selected_target_syntax_ordinal": int(scoped["selected_target_syntax_ordinal"]),
        "selected_target_byte_start": int(scoped["selected_target_byte_start"]),
        "selected_target_byte_end": int(scoped["selected_target_byte_end"]),
        "selected_target_semantic_handle_digest_hex": str(scoped["selected_target_semantic_handle_digest_hex"]),
        "nested_projection_payload_sha256": nested["payload_sha256"],
        "higher_owner_payload_sha256": projection["payload_sha256"],
        "producer_authenticated": False,
        "semantic_repair_correctness_proven": False,
        "semantic_truth_minted": False,
        "reentry_closed": False,
        "reentry_scope_narrowed_by_child": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_dependency_cone_proven": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
        "b_minus_approved": False,
        "authority": {
            "review_authorized": False, "mutation_authorized": False,
            "execution_authorized": False, "commit_authorized": False,
            "merge_authorized": False, "promotion_authorized": False,
            "provider_effect_authorized": False, "public_effect_authorized": False,
            "human_authority": False,
        },
    }
