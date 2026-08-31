#!/usr/bin/env python3
"""Bind the current recursively canonical WorkCapsule target to one exact raw byte slice.

PR561 owns current recursive scoped/higher-owner target identity against the canonical
shared-coordinate owner. PR560 independently owns revalidated exact raw-source slice
materialization for a PR537 portable target. This D0 membrane joins only coordinates
both artifacts expose. The semantic handle remains opaque structural evidence carried
from the portable owner; it is not derived from or authenticated by the raw bytes.
"""
from __future__ import annotations

from typing import Any

from scripts.aura_workcapsule_scoped_higher_owner_portable_continuity import (
    admit_scoped_higher_owner_portable_continuity,
    verify_scoped_higher_owner_portable_continuity,
)

VERSION = "AURA_WORKCAPSULE_CURRENT_RECURSIVE_TARGET_RAW_SLICE_BINDING_V1"
RAW_SLICE_VERSION = "AURA_K27_ASTGE_PORTABLE_TARGET_RAW_SLICE_V1"
STRUCTURAL_PREFIX = "STRUCTURAL_"
RAW_PREFIX = "RAW_SLICE_"
PROJECTION_DIGEST_MISMATCH = "PROJECTION_PAYLOAD_DIGEST_MISMATCH"
DEPENDENCY_MISMATCH = "DEPENDENCY_KEY_MISMATCH"
SOURCE_GENERATION_MISMATCH = "SOURCE_GENERATION_MISMATCH"
SOURCE_SHA_MISMATCH = "FULL_SOURCE_SHA256_MISMATCH"
SOURCE_LENGTH_MISMATCH = "FULL_SOURCE_BYTE_LENGTH_MISMATCH"
TARGET_SPAN_MISMATCH = "TARGET_SPAN_MISMATCH"
TARGET_HANDLE_MISMATCH = "OPAQUE_TARGET_HANDLE_MISMATCH"

_RAW_FIELDS = {
    "version",
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
}

_RAW_TRUE = (
    "portable_target_bound_to_exact_current_raw_slice",
    "source_currentness_revalidated_at_materialization",
    "synthetic_record_is_materialization_coordinate_only",
    "semantic_handle_carried_from_portable_owner",
)

_RAW_FALSE = (
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


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def verify_raw_slice_receipt(receipt: dict[str, Any]) -> list[str]:
    """Validate the closed PR560 serialized evidence shape without authenticating its producer."""
    if not isinstance(receipt, dict) or set(receipt) != _RAW_FIELDS:
        return ["MALFORMED_RECEIPT"]
    violations: list[str] = []
    if receipt.get("version") != RAW_SLICE_VERSION:
        violations.append("VERSION_MISMATCH")
    for field in ("file_id", "source_generation", "full_source_byte_len", "target_byte_start", "target_byte_end", "target_slice_byte_len"):
        if type(receipt.get(field)) is not int or receipt[field] < 0:
            violations.append("NOT_EXACT_NONNEGATIVE_INTEGER:" + field)
    if not isinstance(receipt.get("relative_path"), str) or not receipt["relative_path"]:
        violations.append("RELATIVE_PATH_INVALID")
    for field in (
        "projection_payload_sha256",
        "full_source_sha256_hex",
        "target_slice_sha256_hex",
        "selected_target_semantic_handle_digest_hex",
    ):
        if not _is_sha256(receipt.get(field)):
            violations.append("SHA256_INVALID:" + field)
    for field in _RAW_TRUE:
        if receipt.get(field) is not True:
            violations.append("PROOF_FLAG_NOT_EXACT_TRUE:" + field)
    for field in _RAW_FALSE:
        if receipt.get(field) is not False:
            violations.append("CEILING_VIOLATED:" + field)
    if type(receipt.get("target_byte_start")) is int and type(receipt.get("target_byte_end")) is int:
        if receipt["target_byte_start"] >= receipt["target_byte_end"]:
            violations.append("TARGET_SPAN_EMPTY_OR_REVERSED")
        elif type(receipt.get("target_slice_byte_len")) is int and receipt["target_slice_byte_len"] != receipt["target_byte_end"] - receipt["target_byte_start"]:
            violations.append("TARGET_SLICE_LENGTH_NOT_SPAN_LENGTH")
    return list(dict.fromkeys(violations))


def verify_current_recursive_target_raw_slice_binding(
    *,
    scoped_target_inputs: dict[str, Any],
    higher_owner_projection: dict[str, Any],
    raw_slice_receipt: dict[str, Any],
) -> list[str]:
    """Join current recursive structural evidence to a closed PR560 raw-slice receipt."""
    try:
        structural_violations = verify_scoped_higher_owner_portable_continuity(
            scoped_target_inputs=scoped_target_inputs,
            higher_owner_projection=higher_owner_projection,
        )
    except (KeyError, TypeError, ValueError):
        structural_violations = ["MALFORMED_PARENT_INPUTS"]
    violations = [STRUCTURAL_PREFIX + item for item in structural_violations]
    violations.extend(RAW_PREFIX + item for item in verify_raw_slice_receipt(raw_slice_receipt))
    if violations:
        return list(dict.fromkeys(violations))

    structural = admit_scoped_higher_owner_portable_continuity(
        scoped_target_inputs=scoped_target_inputs,
        higher_owner_projection=higher_owner_projection,
    )
    dependency = structural["dependency_key"]
    if structural["nested_projection_payload_sha256"] != raw_slice_receipt["projection_payload_sha256"]:
        violations.append(PROJECTION_DIGEST_MISMATCH)
    if dependency != {
        "file_id": raw_slice_receipt["file_id"],
        "relative_path": raw_slice_receipt["relative_path"],
    }:
        violations.append(DEPENDENCY_MISMATCH)
    if structural["post_source_generation"] != raw_slice_receipt["source_generation"]:
        violations.append(SOURCE_GENERATION_MISMATCH)
    if structural["post_source_sha256"] != raw_slice_receipt["full_source_sha256_hex"]:
        violations.append(SOURCE_SHA_MISMATCH)
    if structural["post_source_byte_len"] != raw_slice_receipt["full_source_byte_len"]:
        violations.append(SOURCE_LENGTH_MISMATCH)
    if (
        structural["selected_target_byte_start"],
        structural["selected_target_byte_end"],
    ) != (
        raw_slice_receipt["target_byte_start"],
        raw_slice_receipt["target_byte_end"],
    ):
        violations.append(TARGET_SPAN_MISMATCH)
    if structural["selected_target_semantic_handle_digest_hex"] != raw_slice_receipt[
        "selected_target_semantic_handle_digest_hex"
    ]:
        violations.append(TARGET_HANDLE_MISMATCH)
    return list(dict.fromkeys(violations))


def admit_current_recursive_target_raw_slice_binding(**kwargs: Any) -> dict[str, Any]:
    """Emit only the exact relation consequence or fail closed."""
    violations = verify_current_recursive_target_raw_slice_binding(**kwargs)
    if violations:
        raise ValueError("current recursive target/raw-slice binding failed: " + ",".join(violations))
    structural = admit_scoped_higher_owner_portable_continuity(
        scoped_target_inputs=kwargs["scoped_target_inputs"],
        higher_owner_projection=kwargs["higher_owner_projection"],
    )
    raw = kwargs["raw_slice_receipt"]
    return {
        "version": VERSION,
        "current_recursive_target_reproved": True,
        "exact_current_raw_slice_evidence_consumed": True,
        "same_portable_projection_payload_proven": True,
        "same_source_instance_proven": True,
        "same_exact_target_span_proven": True,
        "opaque_semantic_handle_continuity_proven": True,
        "target_slice_byte_len": raw["target_slice_byte_len"],
        "target_slice_sha256_hex": raw["target_slice_sha256_hex"],
        "dependency_key": dict(structural["dependency_key"]),
        "source_generation": structural["post_source_generation"],
        "full_source_sha256_hex": structural["post_source_sha256"],
        "full_source_byte_len": structural["post_source_byte_len"],
        "selected_target_syntax_ordinal": structural["selected_target_syntax_ordinal"],
        "target_byte_start": structural["selected_target_byte_start"],
        "target_byte_end": structural["selected_target_byte_end"],
        "selected_target_semantic_handle_digest_hex": structural[
            "selected_target_semantic_handle_digest_hex"
        ],
        "raw_slice_receipt_producer_authenticated": False,
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "semantic_repair_correctness_proven": False,
        "reentry_closed": False,
        "reentry_scope_narrowed": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
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
