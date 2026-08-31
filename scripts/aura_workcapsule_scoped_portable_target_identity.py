#!/usr/bin/env python3
"""Canonical shared-target coordinate owner for scoped + portable WorkCapsule evidence.

PR548 originally joined PR532 scoped post-repair evidence with PR539 portable target
evidence by independently invoking both parents and comparing the exact coordinate
intersection they both own.  The receipt-level comparator below is now the canonical
owner of that coordinate relation.  The legacy two-bundle API remains stable as a
wrapper: it validates/adopts its parents and then delegates all cross-parent equality
to the receipt-level owner.

The comparator is intentionally polymorphic over the stronger PR542 receipt: PR539
exposes ``selected_target_semantic_handle_digest_hex`` while PR542 exposes the same
continuity-bound target as ``continuous_semantic_handle_digest_hex``.  No semantic,
producer, re-entry, invalidation, runtime, review, or effect authority follows.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_post_repair_source_projection_continuity import (
    admit_post_repair_source_projection_continuity,
    verify_post_repair_source_projection_continuity,
)
from scripts.aura_workcapsule_scoped_post_repair_rebind import (
    admit_scoped_post_repair_rebind,
    verify_scoped_post_repair_rebind,
)

VERSION = "AURA_WORKCAPSULE_SCOPED_PORTABLE_TARGET_IDENTITY_V1"
SCOPED_PREFIX = "SCOPED_"
SOURCE_PREFIX = "SOURCE_"
DEPENDENCY_IDENTITY_MISMATCH = "DEPENDENCY_IDENTITY_MISMATCH"
SOURCE_GENERATION_MISMATCH = "SOURCE_GENERATION_MISMATCH"
SOURCE_BODY_SHA_MISMATCH = "SOURCE_BODY_SHA_MISMATCH"
SOURCE_BYTE_LEN_MISMATCH = "SOURCE_BYTE_LEN_MISMATCH"
SYNTAX_ORDINAL_MISMATCH = "SYNTAX_ORDINAL_MISMATCH"
TARGET_SPAN_MISMATCH = "TARGET_SPAN_MISMATCH"
SEMANTIC_HANDLE_MISMATCH = "SEMANTIC_HANDLE_MISMATCH"
MALFORMED_SCOPED_RECEIPT = "MALFORMED_SCOPED_RECEIPT"
MALFORMED_SOURCE_RECEIPT = "MALFORMED_SOURCE_RECEIPT"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_SCOPED_PORTABLE_TARGET_IDENTITY_V1_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _source_semantic_handle(source_receipt: dict[str, Any]) -> Any:
    """Return the canonical target handle from PR539 or stronger PR542 evidence."""
    if "selected_target_semantic_handle_digest_hex" in source_receipt:
        return source_receipt.get("selected_target_semantic_handle_digest_hex")
    return source_receipt.get("continuous_semantic_handle_digest_hex")


def verify_shared_target_coordinates(
    *,
    scoped_receipt: dict[str, Any],
    source_receipt: dict[str, Any],
) -> list[str]:
    """Own the shared post-edit target coordinate relation at receipt level.

    ``scoped_receipt`` is a PR532-shaped admission. ``source_receipt`` may be the
    PR539 source-continuity admission used by the legacy PR548 API or the stronger
    PR542 portable-higher-owner admission. The function compares only the relation
    both evidence planes expose: dependency identity, SOURCE generation/body/length,
    syntax ordinal, exact target span, and semantic handle.
    """
    if not isinstance(scoped_receipt, dict):
        return [MALFORMED_SCOPED_RECEIPT]
    if not isinstance(source_receipt, dict):
        return [MALFORMED_SOURCE_RECEIPT]

    violations: list[str] = []
    if scoped_receipt.get("dependency_key") != source_receipt.get("repaired_dependency_key"):
        violations.append(DEPENDENCY_IDENTITY_MISMATCH)
    if scoped_receipt.get("post_source_generation") != source_receipt.get("post_source_generation"):
        violations.append(SOURCE_GENERATION_MISMATCH)
    if scoped_receipt.get("post_body_sha256") != source_receipt.get("post_source_sha256"):
        violations.append(SOURCE_BODY_SHA_MISMATCH)
    if scoped_receipt.get("post_byte_len") != source_receipt.get("post_source_byte_len"):
        violations.append(SOURCE_BYTE_LEN_MISMATCH)
    if scoped_receipt.get("syntax_ordinal") != source_receipt.get("selected_target_syntax_ordinal"):
        violations.append(SYNTAX_ORDINAL_MISMATCH)
    if (
        scoped_receipt.get("byte_start"),
        scoped_receipt.get("byte_end"),
    ) != (
        source_receipt.get("selected_target_byte_start"),
        source_receipt.get("selected_target_byte_end"),
    ):
        violations.append(TARGET_SPAN_MISMATCH)
    if scoped_receipt.get("semantic_handle_digest") != _source_semantic_handle(source_receipt):
        violations.append(SEMANTIC_HANDLE_MISMATCH)
    return list(dict.fromkeys(violations))


def verify_scoped_portable_target_identity(
    *,
    scoped_rebind_inputs: dict[str, Any],
    post_source_inputs: dict[str, Any],
) -> list[str]:
    """Legacy PR548 API: validate both parents, then delegate coordinate ownership."""
    if not isinstance(scoped_rebind_inputs, dict):
        return [SCOPED_PREFIX + "MALFORMED_PARENT_INPUTS"]
    if not isinstance(post_source_inputs, dict):
        return [SOURCE_PREFIX + "MALFORMED_PARENT_INPUTS"]

    try:
        scoped_violations = verify_scoped_post_repair_rebind(**scoped_rebind_inputs)
    except (KeyError, TypeError, ValueError):
        scoped_violations = ["MALFORMED_PARENT_INPUTS"]
    try:
        source_violations = verify_post_repair_source_projection_continuity(**post_source_inputs)
    except (KeyError, TypeError, ValueError):
        source_violations = ["MALFORMED_PARENT_INPUTS"]

    violations = [SCOPED_PREFIX + item for item in scoped_violations]
    violations.extend(SOURCE_PREFIX + item for item in source_violations)
    if violations:
        return list(dict.fromkeys(violations))

    scoped = admit_scoped_post_repair_rebind(**scoped_rebind_inputs)
    source = admit_post_repair_source_projection_continuity(**post_source_inputs)
    return verify_shared_target_coordinates(scoped_receipt=scoped, source_receipt=source)


def admit_scoped_portable_target_identity(
    *,
    scoped_rebind_inputs: dict[str, Any],
    post_source_inputs: dict[str, Any],
) -> dict[str, Any]:
    """Emit the legacy identity receipt while using one canonical coordinate owner."""
    violations = verify_scoped_portable_target_identity(
        scoped_rebind_inputs=scoped_rebind_inputs,
        post_source_inputs=post_source_inputs,
    )
    if violations:
        raise ValueError("scoped/portable target identity failed: " + ",".join(violations))

    scoped = admit_scoped_post_repair_rebind(**scoped_rebind_inputs)
    source = admit_post_repair_source_projection_continuity(**post_source_inputs)
    payload: dict[str, Any] = {
        "version": VERSION,
        "same_post_edit_target_coordinate_proven": True,
        "same_dependency_identity_proven": True,
        "same_post_source_instance_proven": True,
        "same_syntax_ordinal_proven": True,
        "same_target_span_proven": True,
        "same_semantic_handle_proven": True,
        "canonical_shared_target_coordinate_owner": "verify_shared_target_coordinates",
        "dependency_key": dict(scoped["dependency_key"]),
        "post_source_generation": int(scoped["post_source_generation"]),
        "post_source_sha256": str(scoped["post_body_sha256"]),
        "post_source_byte_len": int(scoped["post_byte_len"]),
        "selected_target_syntax_ordinal": int(scoped["syntax_ordinal"]),
        "selected_target_byte_start": int(scoped["byte_start"]),
        "selected_target_byte_end": int(scoped["byte_end"]),
        "selected_target_semantic_handle_digest_hex": str(scoped["semantic_handle_digest"]),
        "scoped_rebind_receipt_identity": scoped["receipt_identity"],
        "post_source_continuity_receipt_identity": source["receipt_identity"],
        "portable_projection_payload_sha256": source["portable_projection_payload_sha256"],
        "portable_canonical_owner_parent_relation_carried_by_pr539": True,
        "scoped_witness_owner_parent_relation_proven": False,
        "cross_parent_owner_parent_equality_proven": False,
        "reentry_closed": False,
        "reentry_scope_narrowed_by_child": False,
        "source_currentness_minted_by_child": False,
        "semantic_repair_correctness_proven": False,
        "semantic_truth_minted": False,
        "producer_authenticated": False,
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
    payload["receipt_identity"] = _identity(payload)
    return payload
