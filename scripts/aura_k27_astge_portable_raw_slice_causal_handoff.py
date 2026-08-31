#!/usr/bin/env python3
"""Verify the portable PR560 raw-slice envelope for a PR556-side causal consumer.

This is a cross-runtime compatibility membrane, not a second source or lifecycle owner.
The Rust owner remains PR560. A PR556-shaped POST source witness may be compared to the
portable envelope only for exact source-coordinate compatibility. This module does not
authenticate the witness producer, derive a causal closure, or derive semantic identity
from raw bytes. Exact PR556 re-execution belongs to hosted integration or a higher owner.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "AURA_K27_ASTGE_PORTABLE_TARGET_RAW_SLICE_PROJECTION_V1"
RAW_SLICE_VERSION = "AURA_K27_ASTGE_PORTABLE_TARGET_RAW_SLICE_V1"
CANONICALIZATION = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1"
CURRENT = "CURRENT"

PAYLOAD_FIELDS = (
    "schema",
    "version",
    "canonicalization_profile",
    "raw_slice_version",
    "projection_payload_sha256",
    "file_id",
    "relative_path",
    "source_generation",
    "full_source_sha256_hex",
    "full_source_byte_len",
    "target_byte_start",
    "target_byte_end",
    "target_slice_byte_len",
    "target_slice_sha256_hex",
    "selected_target_semantic_handle_digest_hex",
    "portable_target_bound_to_exact_current_raw_slice",
    "source_currentness_revalidated_at_materialization",
    "synthetic_record_is_materialization_coordinate_only",
    "storage_node_identity_minted",
    "semantic_handle_carried_from_portable_owner",
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
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

POSITIVE_FLAGS = (
    "portable_target_bound_to_exact_current_raw_slice",
    "source_currentness_revalidated_at_materialization",
    "synthetic_record_is_materialization_coordinate_only",
    "semantic_handle_carried_from_portable_owner",
)

NEGATIVE_FLAGS = (
    "storage_node_identity_minted",
    "semantic_handle_derived_from_raw_slice",
    "semantic_identity_proven_by_raw_slice",
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


def _exact_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _exact_bool(value: Any) -> bool:
    return type(value) is bool


def _digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def canonical_raw_slice_payload_bytes(payload: dict[str, Any]) -> bytes:
    ordered = {field: payload[field] for field in PAYLOAD_FIELDS}
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_portable_raw_slice_projection(projection: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if not isinstance(projection, dict) or set(projection) != {"payload", "payload_sha256"}:
        return ["PROJECTION_CLOSED_SCHEMA_VIOLATION"]
    payload = projection.get("payload")
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_FIELDS):
        return ["PAYLOAD_CLOSED_SCHEMA_VIOLATION"]

    if payload.get("schema") != SCHEMA:
        violations.append("WRONG_SCHEMA")
    if type(payload.get("version")) is not int or payload.get("version") != 1:
        violations.append("WRONG_VERSION")
    if payload.get("canonicalization_profile") != CANONICALIZATION:
        violations.append("WRONG_CANONICALIZATION_PROFILE")
    if payload.get("raw_slice_version") != RAW_SLICE_VERSION:
        violations.append("WRONG_RAW_SLICE_VERSION")

    for field in (
        "projection_payload_sha256",
        "full_source_sha256_hex",
        "target_slice_sha256_hex",
        "selected_target_semantic_handle_digest_hex",
    ):
        if not _digest(payload.get(field)):
            violations.append(f"INVALID_DIGEST:{field}")

    integer_fields = (
        "file_id",
        "source_generation",
        "full_source_byte_len",
        "target_byte_start",
        "target_byte_end",
        "target_slice_byte_len",
    )
    for field in integer_fields:
        if not _exact_int(payload.get(field)):
            violations.append(f"INVALID_INTEGER:{field}")

    if not isinstance(payload.get("relative_path"), str) or not payload["relative_path"].strip():
        violations.append("INVALID_RELATIVE_PATH")

    if all(_exact_int(payload.get(field)) for field in integer_fields):
        if payload["target_byte_start"] >= payload["target_byte_end"]:
            violations.append("INVALID_TARGET_SPAN")
        elif payload["target_byte_end"] > payload["full_source_byte_len"]:
            violations.append("TARGET_SPAN_OUT_OF_SOURCE_BOUNDS")
        elif payload["target_slice_byte_len"] != payload["target_byte_end"] - payload["target_byte_start"]:
            violations.append("TARGET_SLICE_LENGTH_MISMATCH")

    for field in POSITIVE_FLAGS:
        if not _exact_bool(payload.get(field)) or payload[field] is not True:
            violations.append(f"REQUIRED_TRUE_FLAG:{field}")
    for field in NEGATIVE_FLAGS:
        if not _exact_bool(payload.get(field)) or payload[field] is not False:
            violations.append(f"CEILING_VIOLATION:{field}")

    supplied = projection.get("payload_sha256")
    if not _digest(supplied):
        violations.append("INVALID_OUTER_DIGEST")
    else:
        expected = hashlib.sha256(canonical_raw_slice_payload_bytes(payload)).hexdigest()
        if supplied.lower() != expected:
            violations.append("PAYLOAD_DIGEST_MISMATCH")
    return list(dict.fromkeys(violations))


def verify_raw_slice_against_causal_post_source(
    *,
    raw_slice_projection: dict[str, Any],
    post_source_witness: dict[str, Any],
) -> list[str]:
    """Compare only exact source coordinates; producer/lifecycle proof remains external."""
    violations = verify_portable_raw_slice_projection(raw_slice_projection)
    if violations:
        return [f"RAW_SLICE_{item}" for item in violations]
    if not isinstance(post_source_witness, dict):
        return ["POST_SOURCE_WITNESS_MALFORMED"]

    required = {
        "role",
        "file_id",
        "relative_path",
        "source_generation",
        "source_sha256",
        "source_byte_len",
        "currentness",
        "witness_ref",
    }
    if set(post_source_witness) != required:
        return ["POST_SOURCE_WITNESS_CLOSED_SCHEMA_VIOLATION"]
    if type(post_source_witness.get("file_id")) is not int:
        violations.append("POST_SOURCE_FILE_ID_TYPE_INVALID")
    if type(post_source_witness.get("source_generation")) is not int:
        violations.append("POST_SOURCE_GENERATION_TYPE_INVALID")
    if type(post_source_witness.get("source_byte_len")) is not int:
        violations.append("POST_SOURCE_BYTE_LEN_TYPE_INVALID")
    if post_source_witness.get("currentness") != CURRENT:
        violations.append("POST_SOURCE_NOT_CURRENT")
    if not _digest(post_source_witness.get("source_sha256")):
        violations.append("POST_SOURCE_DIGEST_INVALID")
    if violations:
        return list(dict.fromkeys(violations))

    payload = raw_slice_projection["payload"]
    comparisons = (
        ("file_id", "file_id", "FILE_ID_MISMATCH"),
        ("relative_path", "relative_path", "RELATIVE_PATH_MISMATCH"),
        ("source_generation", "source_generation", "SOURCE_GENERATION_MISMATCH"),
        ("full_source_sha256_hex", "source_sha256", "FULL_SOURCE_DIGEST_MISMATCH"),
        ("full_source_byte_len", "source_byte_len", "FULL_SOURCE_LENGTH_MISMATCH"),
    )
    for left, right, code in comparisons:
        if payload[left] != post_source_witness[right]:
            violations.append(code)
    return list(dict.fromkeys(violations))


def admit_raw_slice_causal_handoff(
    *,
    raw_slice_projection: dict[str, Any],
    post_source_witness: dict[str, Any],
) -> dict[str, Any]:
    violations = verify_raw_slice_against_causal_post_source(
        raw_slice_projection=raw_slice_projection,
        post_source_witness=post_source_witness,
    )
    if violations:
        raise ValueError("raw-slice causal handoff failed: " + ",".join(violations))
    payload = raw_slice_projection["payload"]
    return {
        "version": "AURA_K27_ASTGE_RAW_SLICE_CAUSAL_HANDOFF_V1",
        "raw_slice_projection_verified": True,
        "post_source_coordinate_compatible": True,
        "causal_post_owner_reproved_by_this_function": False,
        "producer_authenticated": False,
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "semantic_repair_correctness_proven": False,
        "reentry_closed_by_this_function": False,
        "effect_authority": False,
        "file_id": payload["file_id"],
        "relative_path": payload["relative_path"],
        "source_generation": payload["source_generation"],
        "full_source_sha256_hex": payload["full_source_sha256_hex"],
        "full_source_byte_len": payload["full_source_byte_len"],
        "target_byte_start": payload["target_byte_start"],
        "target_byte_end": payload["target_byte_end"],
        "target_slice_sha256_hex": payload["target_slice_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": payload[
            "selected_target_semantic_handle_digest_hex"
        ],
    }
