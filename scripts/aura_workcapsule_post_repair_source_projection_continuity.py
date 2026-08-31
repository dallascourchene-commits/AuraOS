#!/usr/bin/env python3
"""Bind a portable ASTGE canonical-target projection to one exact WorkCapsule POST source instance.

PR536 proves canonical temporal lifecycle equivalence across independently green WorkCapsule
owners: exact rejected-currentness PRE state and distinct POST CLOSED state expose one canonical
identity tuple. PR537 defines a deterministic cross-language serialized projection of the typed
ASTGE post-edit canonical definition-target receipt.

This D0 compatibility membrane validates the stable PR537 transport schema and requires its
source coordinate to be the exact ACTIVE/CURRENT source body consumed by PR536's canonical POST
candidate and to refer to a source dependency that was rejected in PRE. It proves source-instance
continuity only. A digest-valid portable projection is not producer authentication, and binding it
to a CLOSED lifecycle does not prove semantic repair correctness, a source-to-graph dependency
map, review approval, or effect authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_canonical_temporal_lifecycle_equivalence import (
    admit_canonical_temporal_lifecycle_equivalence,
    verify_canonical_temporal_lifecycle_equivalence,
)

VERSION = "AURA_WORKCAPSULE_POST_REPAIR_SOURCE_PROJECTION_CONTINUITY_V1"
PROJECTION_SCHEMA = "AURA_ASTGE_POST_EDIT_CANONICAL_DEFINITION_TARGET_PROJECTION_V1"
PROJECTION_CANONICALIZATION_PROFILE = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1"
SOURCE_DOMAIN = "SOURCE"
CURRENT = "CURRENT"
ACTIVE = "ACTIVE"
SELECTED_SOURCES = "SELECTED_SOURCES"
FULL_GRAPH = "FULL_GRAPH"

TEMPORAL_PREFIX = "TEMPORAL_"
PROJECTION_PREFIX = "PROJECTION_"
POST_NOT_CLOSED = "POST_LIFECYCLE_NOT_CLOSED"
PROJECTION_SOURCE_NOT_REJECTED_PRE = "PROJECTION_SOURCE_NOT_REJECTED_PRE"
PROJECTION_SOURCE_NOT_SELECTED_PRE = "PROJECTION_SOURCE_NOT_SELECTED_PRE"
POST_SOURCE_MISSING = "POST_SOURCE_MISSING_FROM_CANONICAL_CANDIDATE"
POST_SOURCE_NOT_ACTIVE_CURRENT = "POST_SOURCE_NOT_ACTIVE_CURRENT"
POST_SOURCE_GENERATION_MISMATCH = "POST_SOURCE_GENERATION_MISMATCH"
POST_SOURCE_BODY_SHA_MISMATCH = "POST_SOURCE_BODY_SHA_MISMATCH"
POST_SOURCE_BODY_LENGTH_MISMATCH = "POST_SOURCE_BODY_LENGTH_MISMATCH"
POST_CANDIDATE_IDENTITY_MISMATCH = "POST_CANDIDATE_IDENTITY_MISMATCH"

_PAYLOAD_FIELDS = (
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

_NEGATIVE_PROJECTION_FIELDS = (
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


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _projection_payload_bytes(payload: dict[str, Any]) -> bytes:
    ordered = {field: payload[field] for field in _PAYLOAD_FIELDS}
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def verify_portable_canonical_target_projection(projection: dict[str, Any]) -> list[str]:
    """Validate the stable PR537 transport contract without authenticating its producer."""
    violations: list[str] = []
    if not isinstance(projection, dict) or set(projection) != {"payload", "payload_sha256"}:
        return ["MALFORMED_PROJECTION_ENVELOPE"]
    payload = projection.get("payload")
    if not isinstance(payload, dict):
        return ["MALFORMED_PROJECTION_PAYLOAD"]
    if set(payload) != set(_PAYLOAD_FIELDS):
        violations.append("PROJECTION_SCHEMA_FIELDS_MISMATCH")
        return violations

    if payload.get("schema") != PROJECTION_SCHEMA or payload.get("version") != 1:
        violations.append("PROJECTION_SCHEMA_VERSION_MISMATCH")
    if payload.get("canonicalization_profile") != PROJECTION_CANONICALIZATION_PROFILE:
        violations.append("PROJECTION_CANONICALIZATION_PROFILE_MISMATCH")
    if payload.get("source_generation_domain") != SOURCE_DOMAIN:
        violations.append("PROJECTION_SOURCE_GENERATION_DOMAIN_MISMATCH")
    if type(payload.get("source_generation_value")) is not int or payload["source_generation_value"] < 0:
        violations.append("PROJECTION_SOURCE_GENERATION_INVALID")
    if type(payload.get("file_id")) is not int or payload["file_id"] < 0:
        violations.append("PROJECTION_FILE_ID_INVALID")
    if not isinstance(payload.get("relative_path"), str) or not payload["relative_path"].strip():
        violations.append("PROJECTION_RELATIVE_PATH_MISSING")
    if not _is_sha256(payload.get("source_sha256_hex")):
        violations.append("PROJECTION_SOURCE_SHA256_INVALID")
    if type(payload.get("source_byte_len")) is not int or payload["source_byte_len"] < 0:
        violations.append("PROJECTION_SOURCE_BYTE_LEN_INVALID")
    if not _is_sha256(payload.get("selected_target_semantic_handle_digest_hex")):
        violations.append("PROJECTION_SEMANTIC_HANDLE_INVALID")

    for field in (
        "selected_target_scope_local_id",
        "selected_target_parent_scope_local_id",
        "selected_target_syntax_ordinal",
        "definition_owner_scope_local_id",
        "definition_target_scope_local_id",
    ):
        if type(payload.get(field)) is not int or payload[field] < 0:
            violations.append(f"PROJECTION_INTEGER_COORDINATE_INVALID:{field}")
    start = payload.get("selected_target_byte_start")
    end = payload.get("selected_target_byte_end")
    if type(start) is not int or type(end) is not int or start < 0 or end <= start:
        violations.append("PROJECTION_TARGET_SPAN_INVALID")
    elif isinstance(payload.get("source_byte_len"), int) and end > payload["source_byte_len"]:
        violations.append("PROJECTION_TARGET_SPAN_OUTSIDE_SOURCE")

    if payload.get("selected_current_scope_is_binding_target") is not True:
        violations.append("PROJECTION_SELECTED_SCOPE_NOT_BINDING_TARGET")
    if payload.get("binding_owner_is_selected_parent") is not True:
        violations.append("PROJECTION_BINDING_OWNER_NOT_SELECTED_PARENT")
    if payload.get("local_scope_id_is_semantic_identity") is not False:
        violations.append("PROJECTION_LOCAL_SCOPE_ID_PROMOTED")
    if payload.get("post_edit_profiled_scope_current") is not True:
        violations.append("PROJECTION_POST_EDIT_SCOPE_NOT_CURRENT")
    if payload.get("canonical_definition_target_current") is not True:
        violations.append("PROJECTION_CANONICAL_TARGET_NOT_CURRENT")
    if payload.get("definition_target_scope_local_id") != payload.get("selected_target_scope_local_id"):
        violations.append("PROJECTION_TARGET_RELATION_MISMATCH")
    if payload.get("definition_owner_scope_local_id") != payload.get("selected_target_parent_scope_local_id"):
        violations.append("PROJECTION_OWNER_RELATION_MISMATCH")
    for field in _NEGATIVE_PROJECTION_FIELDS:
        if payload.get(field) is not False:
            violations.append(f"PROJECTION_CEILING_VIOLATED:{field}")

    supplied = projection.get("payload_sha256")
    if not _is_sha256(supplied):
        violations.append("PROJECTION_PAYLOAD_SHA256_INVALID")
    else:
        expected = hashlib.sha256(_projection_payload_bytes(payload)).hexdigest()
        if supplied != expected:
            violations.append("PROJECTION_PAYLOAD_DIGEST_MISMATCH")
    return list(dict.fromkeys(violations))


def _source_key(row: dict[str, Any], *, prior: bool = False) -> tuple[int, str]:
    file_field = "prior_file_id" if prior else "file_id"
    return int(row[file_field]), str(row["relative_path"])


def _rejected_pre_keys(pre_observation_closure_receipt: dict[str, Any]) -> set[tuple[int, str]]:
    source_observation = pre_observation_closure_receipt.get("source_observation", {})
    keys: set[tuple[int, str]] = set()
    for row in source_observation.get("source_observations", []):
        if row.get("currentness") == "STALE" and isinstance(row.get("expected_source_identity"), dict):
            keys.add((int(row["expected_source_identity"]["file_id"]), str(row["relative_path"])))
    for row in source_observation.get("unresolved_prior_sources", []):
        if row.get("currentness") in {"STALE", "UNKNOWN"}:
            keys.add(_source_key(row, prior=True))
    return keys


def _selected_pre_keys(reentry_receipt: dict[str, Any]) -> set[tuple[int, str]]:
    out: set[tuple[int, str]] = set()
    for row in reentry_receipt.get("minimum_reentry_source_keys", []):
        try:
            out.add(_source_key(row))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _find_post_source(post_observation_bound_receipt: dict[str, Any], key: tuple[int, str]) -> dict[str, Any] | None:
    candidate = post_observation_bound_receipt.get("derived_candidate_binding")
    if not isinstance(candidate, dict):
        return None
    for row in candidate.get("source_witnesses", []):
        try:
            if _source_key(row) == key:
                return row
        except (KeyError, TypeError, ValueError):
            continue
    return None


def verify_post_repair_source_projection_continuity(
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
    astge_projection: dict[str, Any],
) -> list[str]:
    """Require the portable ASTGE projection to describe the exact canonical POST source body."""
    temporal_kwargs = {
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
    }
    temporal_violations = verify_canonical_temporal_lifecycle_equivalence(**temporal_kwargs)
    if temporal_violations:
        return [TEMPORAL_PREFIX + item for item in temporal_violations]

    projection_violations = verify_portable_canonical_target_projection(astge_projection)
    if projection_violations:
        return [PROJECTION_PREFIX + item for item in projection_violations]

    lifecycle = admit_canonical_temporal_lifecycle_equivalence(**temporal_kwargs)
    violations: list[str] = []
    if lifecycle.get("post_closure_status") != "CLOSED":
        violations.append(POST_NOT_CLOSED)

    payload = astge_projection["payload"]
    key = (int(payload["file_id"]), str(payload["relative_path"]))
    if key not in _rejected_pre_keys(pre_observation_closure_receipt):
        violations.append(PROJECTION_SOURCE_NOT_REJECTED_PRE)

    scope = reentry_receipt.get("minimum_reentry_scope")
    if scope == SELECTED_SOURCES and key not in _selected_pre_keys(reentry_receipt):
        violations.append(PROJECTION_SOURCE_NOT_SELECTED_PRE)
    elif scope not in {SELECTED_SOURCES, FULL_GRAPH}:
        violations.append(PROJECTION_SOURCE_NOT_SELECTED_PRE)

    candidate = post_observation_bound_receipt.get("derived_candidate_binding", {})
    if candidate.get("binding_identity") != lifecycle.get("post_derived_candidate_binding_identity"):
        violations.append(POST_CANDIDATE_IDENTITY_MISMATCH)

    post_source = _find_post_source(post_observation_bound_receipt, key)
    if post_source is None:
        violations.append(POST_SOURCE_MISSING)
    else:
        if post_source.get("role") != ACTIVE or post_source.get("currentness") != CURRENT:
            violations.append(POST_SOURCE_NOT_ACTIVE_CURRENT)
        if post_source.get("source_generation") != payload.get("source_generation_value"):
            violations.append(POST_SOURCE_GENERATION_MISMATCH)
        if post_source.get("source_sha256") != payload.get("source_sha256_hex"):
            violations.append(POST_SOURCE_BODY_SHA_MISMATCH)
        if post_source.get("source_byte_len") != payload.get("source_byte_len"):
            violations.append(POST_SOURCE_BODY_LENGTH_MISMATCH)

    return list(dict.fromkeys(violations))


def admit_post_repair_source_projection_continuity(**kwargs: Any) -> dict[str, Any]:
    """Emit only a cross-runtime source-instance continuity witness or fail closed."""
    violations = verify_post_repair_source_projection_continuity(**kwargs)
    if violations:
        raise ValueError("post-repair source projection continuity failed: " + ",".join(violations))

    temporal_kwargs = dict(kwargs)
    projection = temporal_kwargs.pop("astge_projection")
    lifecycle = admit_canonical_temporal_lifecycle_equivalence(**temporal_kwargs)
    payload = projection["payload"]
    key = {"file_id": int(payload["file_id"]), "relative_path": str(payload["relative_path"])}
    out: dict[str, Any] = {
        "version": VERSION,
        "canonical_temporal_lifecycle_equivalence_proven": True,
        "post_closure_status": lifecycle["post_closure_status"],
        "post_source_projection_receipt_identity": lifecycle["post_source_projection_receipt_identity"],
        "post_derived_candidate_binding_identity": lifecycle["post_derived_candidate_binding_identity"],
        "post_inner_closure_receipt_identity": lifecycle["post_inner_closure_receipt_identity"],
        "repaired_dependency_key": key,
        "portable_projection_schema_verified": True,
        "portable_projection_payload_sha256": projection["payload_sha256"],
        "source_instance_continuity_proven": True,
        "pre_rejected_dependency_matches_projection_source": True,
        "post_active_current_source_matches_projection": True,
        "post_source_generation": int(payload["source_generation_value"]),
        "post_source_sha256": str(payload["source_sha256_hex"]),
        "post_source_byte_len": int(payload["source_byte_len"]),
        "canonical_target_claim_carried_by_projection": True,
        "selected_target_scope_local_id": int(payload["selected_target_scope_local_id"]),
        "selected_target_parent_scope_local_id": int(payload["selected_target_parent_scope_local_id"]),
        "selected_target_syntax_ordinal": int(payload["selected_target_syntax_ordinal"]),
        "selected_target_byte_start": int(payload["selected_target_byte_start"]),
        "selected_target_byte_end": int(payload["selected_target_byte_end"]),
        "selected_target_semantic_handle_digest_hex": str(payload["selected_target_semantic_handle_digest_hex"]),
        "projection_producer_authenticated": False,
        "canonical_target_producer_authenticated": False,
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
        "scope_profile": "WORKCAPSULE_POST_REPAIR_SOURCE_PROJECTION_CONTINUITY_V1",
        "value": hashlib.sha256(_canonical_bytes(out)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
