#!/usr/bin/env python3
"""Converge PR532 scoped post-repair evidence with PR539 portable target evidence.

This D0 membrane invokes both existing owners independently and proves only that the
coordinates they expose identify one post-edit target: dependency file/path, SOURCE
generation/body, canonical syntax ordinal, byte span, and semantic-handle digest.

PR539 independently carries a canonical definition owner/parent relation. PR532 does
not expose that relation, so this child deliberately does not claim cross-parent
owner/parent equality, semantic repair correctness, producer authentication, re-entry
closure, invalidation narrowing, runtime resolution, or authority.
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


def verify_scoped_portable_target_identity(
    *,
    scoped_rebind_inputs: dict[str, Any],
    post_source_inputs: dict[str, Any],
) -> list[str]:
    """Require both parent owners to admit one identical post-edit target coordinate."""
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

    if scoped.get("dependency_key") != source.get("repaired_dependency_key"):
        violations.append(DEPENDENCY_IDENTITY_MISMATCH)
    if scoped.get("post_source_generation") != source.get("post_source_generation"):
        violations.append(SOURCE_GENERATION_MISMATCH)
    if scoped.get("post_body_sha256") != source.get("post_source_sha256"):
        violations.append(SOURCE_BODY_SHA_MISMATCH)
    if scoped.get("post_byte_len") != source.get("post_source_byte_len"):
        violations.append(SOURCE_BYTE_LEN_MISMATCH)
    if scoped.get("syntax_ordinal") != source.get("selected_target_syntax_ordinal"):
        violations.append(SYNTAX_ORDINAL_MISMATCH)
    if (
        scoped.get("byte_start"),
        scoped.get("byte_end"),
    ) != (
        source.get("selected_target_byte_start"),
        source.get("selected_target_byte_end"),
    ):
        violations.append(TARGET_SPAN_MISMATCH)
    if scoped.get("semantic_handle_digest") != source.get(
        "selected_target_semantic_handle_digest_hex"
    ):
        violations.append(SEMANTIC_HANDLE_MISMATCH)

    return list(dict.fromkeys(violations))


def admit_scoped_portable_target_identity(
    *,
    scoped_rebind_inputs: dict[str, Any],
    post_source_inputs: dict[str, Any],
) -> dict[str, Any]:
    """Emit one identity-only convergence receipt or fail closed."""
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
