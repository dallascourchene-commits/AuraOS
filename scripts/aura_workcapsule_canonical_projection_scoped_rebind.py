#!/usr/bin/env python3
"""Bind WorkCapsule scoped post-repair evidence to the repository-owned ASTGE V1 projection.

The transport boundary is the serialized projection emitted/verified by the Rust
`aura-k27-astge-post-edit-canonical-projection` owner. This membrane validates that exact schema,
canonical compact-JSON payload digest, canonical definition owner->target relation and negative
claim ceiling, then derives the narrower PR532 post-edit witness internally and delegates the
WorkCapsule dependency/re-entry checks to PR532.

The projection remains portable evidence, not producer authentication. This membrane does not
close re-entry, narrow invalidation, prove semantics, or grant review/mutation/execution/effect
authority.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from collections import OrderedDict
from typing import Any

from scripts.aura_workcapsule_scoped_post_repair_rebind import (
    POST_EDIT_VERSION,
    SOURCE_DOMAIN,
    admit_scoped_post_repair_rebind,
)

VERSION = "AURA_WORKCAPSULE_CANONICAL_PROJECTION_SCOPED_REBIND_V1"
PROJECTION_SCHEMA = "AURA_ASTGE_POST_EDIT_CANONICAL_DEFINITION_TARGET_PROJECTION_V1"
PROJECTION_VERSION = 1
CANONICALIZATION_PROFILE = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1"

PAYLOAD_FIELDS = (
    "schema",
    "version",
    "canonicalization_profile",
    "source_generation_domain",
    "source_generation_value",
    "source_owner_ref",
    "relative_path",
    "file_id",
    "source_sha256_hex",
    "source_byte_len",
    "selected_target_scope_local_id",
    "selected_target_parent_scope_local_id",
    "selected_target_syntax_ordinal",
    "selected_target_byte_start",
    "selected_target_byte_end",
    "selected_target_semantic_handle_digest_hex",
    "definition_name",
    "definition_owner_scope_local_id",
    "definition_target_scope_local_id",
    "selected_current_scope_is_binding_target",
    "binding_owner_is_selected_parent",
    "local_scope_id_is_semantic_identity",
    "post_edit_profiled_scope_current",
    "canonical_definition_target_current",
    "runtime_name_resolution_proven",
    "call_graph_proven",
    "semantic_patch_correctness_proven",
    "b_minus_approved",
    "producer_authenticated",
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

REQUIRED_FALSE_FIELDS = (
    "local_scope_id_is_semantic_identity",
    "runtime_name_resolution_proven",
    "call_graph_proven",
    "semantic_patch_correctness_proven",
    "b_minus_approved",
    "producer_authenticated",
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


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _is_int(value: Any) -> bool:
    return type(value) is int


def _is_lower_hex(value: Any, length: int = 64) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    """Reconstruct Rust serde struct declaration order; never trust caller key order."""
    ordered = OrderedDict((field, payload[field]) for field in PAYLOAD_FIELDS)
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _parse_and_verify_projection(canonical_projection_json: str) -> tuple[dict[str, Any] | None, list[str]]:
    violations: list[str] = []
    if not isinstance(canonical_projection_json, str):
        return None, ["PROJECTION_JSON_NOT_STRING"]
    try:
        projection = json.loads(canonical_projection_json, object_pairs_hook=_object_without_duplicates)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None, ["PROJECTION_JSON_INVALID"]
    if not isinstance(projection, dict):
        return None, ["PROJECTION_TOP_LEVEL_NOT_OBJECT"]
    if set(projection) != {"payload", "payload_sha256"}:
        violations.append("PROJECTION_TOP_LEVEL_SCHEMA_DRIFT")
    payload = projection.get("payload")
    if not isinstance(payload, dict):
        violations.append("PROJECTION_PAYLOAD_NOT_OBJECT")
        return None, violations
    if set(payload) != set(PAYLOAD_FIELDS):
        violations.append("PROJECTION_PAYLOAD_SCHEMA_DRIFT")
        return None, violations

    if payload.get("schema") != PROJECTION_SCHEMA or payload.get("version") != PROJECTION_VERSION:
        violations.append("PROJECTION_SCHEMA_VERSION_MISMATCH")
    if payload.get("canonicalization_profile") != CANONICALIZATION_PROFILE:
        violations.append("PROJECTION_CANONICALIZATION_PROFILE_MISMATCH")
    if payload.get("source_generation_domain") != SOURCE_DOMAIN:
        violations.append("PROJECTION_SOURCE_GENERATION_DOMAIN_MISMATCH")

    integer_fields = (
        "source_generation_value",
        "file_id",
        "source_byte_len",
        "selected_target_scope_local_id",
        "selected_target_parent_scope_local_id",
        "selected_target_syntax_ordinal",
        "selected_target_byte_start",
        "selected_target_byte_end",
        "definition_owner_scope_local_id",
        "definition_target_scope_local_id",
    )
    for field in integer_fields:
        if not _is_int(payload.get(field)) or payload[field] < 0:
            violations.append(f"PROJECTION_INTEGER_INVALID:{field}")
    for field in ("source_owner_ref", "relative_path", "definition_name"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            violations.append(f"PROJECTION_STRING_INVALID:{field}")
    if not _is_lower_hex(payload.get("source_sha256_hex")):
        violations.append("PROJECTION_SOURCE_SHA256_INVALID")
    if not _is_lower_hex(payload.get("selected_target_semantic_handle_digest_hex")):
        violations.append("PROJECTION_SEMANTIC_HANDLE_INVALID")
    if not _is_lower_hex(projection.get("payload_sha256")):
        violations.append("PROJECTION_PAYLOAD_SHA256_INVALID")

    if payload.get("selected_current_scope_is_binding_target") is not True:
        violations.append("PROJECTION_SELECTED_SCOPE_NOT_BINDING_TARGET")
    if payload.get("binding_owner_is_selected_parent") is not True:
        violations.append("PROJECTION_BINDING_OWNER_NOT_SELECTED_PARENT")
    if payload.get("post_edit_profiled_scope_current") is not True:
        violations.append("PROJECTION_POST_EDIT_SCOPE_NOT_CURRENT")
    if payload.get("canonical_definition_target_current") is not True:
        violations.append("PROJECTION_CANONICAL_TARGET_NOT_CURRENT")
    for field in REQUIRED_FALSE_FIELDS:
        if payload.get(field) is not False:
            violations.append(f"PROJECTION_CEILING_VIOLATED:{field}")

    if (
        _is_int(payload.get("selected_target_scope_local_id"))
        and _is_int(payload.get("definition_target_scope_local_id"))
        and payload["selected_target_scope_local_id"] != payload["definition_target_scope_local_id"]
    ):
        violations.append("PROJECTION_TARGET_RELATION_MISMATCH")
    if (
        _is_int(payload.get("selected_target_parent_scope_local_id"))
        and _is_int(payload.get("definition_owner_scope_local_id"))
        and payload["selected_target_parent_scope_local_id"]
        != payload["definition_owner_scope_local_id"]
    ):
        violations.append("PROJECTION_OWNER_RELATION_MISMATCH")
    if (
        _is_int(payload.get("selected_target_byte_start"))
        and _is_int(payload.get("selected_target_byte_end"))
        and payload["selected_target_byte_start"] >= payload["selected_target_byte_end"]
    ):
        violations.append("PROJECTION_TARGET_SPAN_INVALID")
    if _is_int(payload.get("source_byte_len")) and payload["source_byte_len"] <= 0:
        violations.append("PROJECTION_SOURCE_LENGTH_INVALID")

    if set(projection) == {"payload", "payload_sha256"} and set(payload) == set(PAYLOAD_FIELDS):
        digest = hashlib.sha256(_canonical_payload_bytes(payload)).hexdigest()
        if projection.get("payload_sha256") != digest:
            violations.append("PROJECTION_DIGEST_MISMATCH")

    return projection, list(dict.fromkeys(violations))


def verify_canonical_projection_scoped_rebind(
    *,
    closure_admission: dict[str, Any],
    reentry_admission: dict[str, Any],
    source_observation: dict[str, Any],
    dependency_key: dict[str, Any],
    canonical_projection_json: str,
) -> list[str]:
    projection, violations = _parse_and_verify_projection(canonical_projection_json)
    if projection is None or violations:
        return violations
    payload = projection["payload"]

    status = source_observation.get("currentness")
    pre_generation: int | None
    if status == "STALE":
        expected = source_observation.get("expected_source_identity")
        coordinate = expected.get("source_generation_coordinate") if isinstance(expected, dict) else None
        pre_generation = coordinate.get("value") if isinstance(coordinate, dict) else None
    elif status == "UNKNOWN":
        pre_generation = None
    else:
        pre_generation = None

    post_edit_witness = {
        "version": POST_EDIT_VERSION,
        "file_id": payload["file_id"],
        "relative_path": payload["relative_path"],
        "pre_source_generation": pre_generation,
        "post_source_generation": payload["source_generation_value"],
        "source_generation_domain": payload["source_generation_domain"],
        "post_body_sha256": payload["source_sha256_hex"],
        "post_byte_len": payload["source_byte_len"],
        "syntax_ordinal": payload["selected_target_syntax_ordinal"],
        "byte_start": payload["selected_target_byte_start"],
        "byte_end": payload["selected_target_byte_end"],
        "semantic_handle_digest": payload["selected_target_semantic_handle_digest_hex"],
        "post_edit_profiled_scope_current": payload["post_edit_profiled_scope_current"],
        # These are compatibility-ceiling defaults, never positive authority claims. The V1
        # canonical projection does not serialize parser-reuse/local-ID authority as evidence.
        "old_local_scope_id_currentness_authority": False,
        "incremental_parser_reuse_used": False,
        "changed_ranges_currentness_authority": False,
        "runtime_name_resolution_proven": payload["runtime_name_resolution_proven"],
        "call_graph_proven": payload["call_graph_proven"],
        "semantic_patch_correctness_proven": payload["semantic_patch_correctness_proven"],
        "b_minus_approved": payload["b_minus_approved"],
        "commit_authorized": payload["commit_authorized"],
        "execution_authorized": payload["execution_authorized"],
        "human_authority": payload["human_authority"],
        "external_effect_authorized": payload["public_effect_authorized"],
        "producer_authenticated": payload["producer_authenticated"],
    }

    try:
        admit_scoped_post_repair_rebind(
            closure_admission=closure_admission,
            reentry_admission=reentry_admission,
            source_observation=source_observation,
            dependency_key=dependency_key,
            post_edit_witness=post_edit_witness,
        )
    except ValueError as error:
        message = str(error)
        marker = "scoped post-repair rebind verification failed: "
        if marker in message:
            violations.extend(item for item in message.split(marker, 1)[1].split(",") if item)
        else:
            violations.append("PR532_REBIND_REJECTED")
    return list(dict.fromkeys(violations))


def admit_canonical_projection_scoped_rebind(
    *,
    closure_admission: dict[str, Any],
    reentry_admission: dict[str, Any],
    source_observation: dict[str, Any],
    dependency_key: dict[str, Any],
    canonical_projection_json: str,
) -> dict[str, Any]:
    """Admit only projection-bound, evidence-only scoped post-repair rebinding."""
    projection, projection_violations = _parse_and_verify_projection(canonical_projection_json)
    if projection is None or projection_violations:
        raise ValueError(
            "canonical projection scoped rebind verification failed: "
            + ",".join(projection_violations)
        )
    violations = verify_canonical_projection_scoped_rebind(
        closure_admission=closure_admission,
        reentry_admission=reentry_admission,
        source_observation=source_observation,
        dependency_key=dependency_key,
        canonical_projection_json=canonical_projection_json,
    )
    if violations:
        raise ValueError(
            "canonical projection scoped rebind verification failed: " + ",".join(violations)
        )

    payload = projection["payload"]
    status = source_observation.get("currentness")
    if status == "STALE":
        pre_generation = source_observation["expected_source_identity"]["source_generation_coordinate"][
            "value"
        ]
    else:
        pre_generation = None
    post_edit_witness = {
        "version": POST_EDIT_VERSION,
        "file_id": payload["file_id"],
        "relative_path": payload["relative_path"],
        "pre_source_generation": pre_generation,
        "post_source_generation": payload["source_generation_value"],
        "source_generation_domain": payload["source_generation_domain"],
        "post_body_sha256": payload["source_sha256_hex"],
        "post_byte_len": payload["source_byte_len"],
        "syntax_ordinal": payload["selected_target_syntax_ordinal"],
        "byte_start": payload["selected_target_byte_start"],
        "byte_end": payload["selected_target_byte_end"],
        "semantic_handle_digest": payload["selected_target_semantic_handle_digest_hex"],
        "post_edit_profiled_scope_current": True,
        "old_local_scope_id_currentness_authority": False,
        "incremental_parser_reuse_used": False,
        "changed_ranges_currentness_authority": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
        "semantic_patch_correctness_proven": False,
        "b_minus_approved": False,
        "commit_authorized": False,
        "execution_authorized": False,
        "human_authority": False,
        "external_effect_authorized": False,
        "producer_authenticated": False,
    }
    scoped = admit_scoped_post_repair_rebind(
        closure_admission=closure_admission,
        reentry_admission=reentry_admission,
        source_observation=source_observation,
        dependency_key=dependency_key,
        post_edit_witness=post_edit_witness,
    )
    authority = {key: False for key in scoped["authority"]}
    return {
        "version": VERSION,
        "projection_schema": payload["schema"],
        "projection_version": payload["version"],
        "projection_canonicalization_profile": payload["canonicalization_profile"],
        "projection_payload_sha256": projection["payload_sha256"],
        "projection_digest_verified": True,
        "repository_owned_projection_schema_bound": True,
        "caller_authored_post_edit_witness_accepted": False,
        "projection_producer_authenticated": False,
        "definition_name": payload["definition_name"],
        "definition_owner_scope_local_id": payload["definition_owner_scope_local_id"],
        "definition_target_scope_local_id": payload["definition_target_scope_local_id"],
        "canonical_definition_target_current": True,
        "scoped_post_repair_rebind": scoped,
        "reentry_closed": False,
        "reentry_scope_narrowed": False,
        "semantic_truth_minted": False,
        "authority": authority,
    }


# Mechanical guard for review/CI: the public admission must never regain the old free-form witness slot.
assert "post_edit_witness" not in inspect.signature(admit_canonical_projection_scoped_rebind).parameters
