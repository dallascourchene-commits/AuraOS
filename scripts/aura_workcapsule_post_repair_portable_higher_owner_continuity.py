#!/usr/bin/env python3
"""Bind one portable higher-owner chain to the exact WorkCapsule POST source instance.

PR539 proves that one PR537 portable canonical-target projection describes the exact ACTIVE/CURRENT
source instance consumed by a canonical WorkCapsule POST CLOSED lifecycle. PR541 proves that the
same transport shape can be nested inside a portable higher-owner owner-chain envelope whose
semantic handle is continuous with the reduced higher-owner chain.

This D0 membrane accepts only the PR541-shaped outer portable envelope at the ASTGE boundary. It
extracts that envelope's one nested canonical-target projection and delegates source-instance
continuity unchanged to PR539. A caller cannot provide a second nested projection to make the two
proofs disagree. Transport integrity, source-instance continuity, and higher-owner handle
continuity remain distinct from producer authentication, semantic repair correctness, review, or
operational authority.
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

VERSION = "AURA_WORKCAPSULE_POST_REPAIR_PORTABLE_HIGHER_OWNER_CONTINUITY_V1"
OWNER_CHAIN_SCHEMA = "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1"
CANONICALIZATION_PROFILE = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1"

OWNER_CHAIN_PREFIX = "OWNER_CHAIN_"
POST_SOURCE_PREFIX = "POST_SOURCE_"
MALFORMED_OWNER_CHAIN_ENVELOPE = "MALFORMED_OWNER_CHAIN_ENVELOPE"
MALFORMED_OWNER_CHAIN_PAYLOAD = "MALFORMED_OWNER_CHAIN_PAYLOAD"
OWNER_CHAIN_FIELDS_MISMATCH = "OWNER_CHAIN_FIELDS_MISMATCH"
OWNER_CHAIN_SCHEMA_MISMATCH = "OWNER_CHAIN_SCHEMA_MISMATCH"
OWNER_CHAIN_CANONICALIZATION_MISMATCH = "OWNER_CHAIN_CANONICALIZATION_MISMATCH"
OWNER_CHAIN_CONSEQUENCE_NOT_PROVEN = "OWNER_CHAIN_CONSEQUENCE_NOT_PROVEN"
OWNER_CHAIN_HANDLE_INVALID = "OWNER_CHAIN_HANDLE_INVALID"
OWNER_CHAIN_HANDLE_MISMATCH = "OWNER_CHAIN_HANDLE_MISMATCH"
OWNER_CHAIN_CEILING_VIOLATED = "OWNER_CHAIN_CEILING_VIOLATED"
OWNER_CHAIN_PAYLOAD_SHA256_INVALID = "OWNER_CHAIN_PAYLOAD_SHA256_INVALID"
OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH = "OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH"

_TARGET_PAYLOAD_FIELDS = (
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

_OWNER_CHAIN_POSITIVE_FIELDS = (
    "outer_constructor_reproved_by_inner_owner",
    "one_canonical_post_edit_consequence",
    "higher_owner_semantic_handle_continuity_proven",
)

_OWNER_CHAIN_NEGATIVE_FIELDS = (
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


def _canonical_target_envelope(projection: dict[str, Any]) -> dict[str, Any]:
    payload = projection["payload"]
    return {
        "payload": {field: payload[field] for field in _TARGET_PAYLOAD_FIELDS},
        "payload_sha256": projection["payload_sha256"],
    }


def _owner_chain_payload_bytes(payload: dict[str, Any]) -> bytes:
    ordered: dict[str, Any] = {}
    for field in _OWNER_CHAIN_FIELDS:
        if field == "canonical_target_projection":
            ordered[field] = _canonical_target_envelope(payload[field])
        else:
            ordered[field] = payload[field]
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_portable_higher_owner_chain(projection: dict[str, Any]) -> list[str]:
    """Validate PR541's stable portable owner-chain transport shape and claim ceiling."""
    if not isinstance(projection, dict) or set(projection) != {"payload", "payload_sha256"}:
        return [MALFORMED_OWNER_CHAIN_ENVELOPE]
    payload = projection.get("payload")
    if not isinstance(payload, dict):
        return [MALFORMED_OWNER_CHAIN_PAYLOAD]
    if set(payload) != set(_OWNER_CHAIN_FIELDS):
        return [OWNER_CHAIN_FIELDS_MISMATCH]

    violations: list[str] = []
    if payload.get("schema") != OWNER_CHAIN_SCHEMA or payload.get("version") != 1:
        violations.append(OWNER_CHAIN_SCHEMA_MISMATCH)
    if payload.get("canonicalization_profile") != CANONICALIZATION_PROFILE:
        violations.append(OWNER_CHAIN_CANONICALIZATION_MISMATCH)

    nested = payload.get("canonical_target_projection")
    if not isinstance(nested, dict):
        violations.append(MALFORMED_OWNER_CHAIN_PAYLOAD)
    else:
        nested_violations = verify_portable_canonical_target_projection(nested)
        violations.extend("NESTED_" + item for item in nested_violations)

    for field in _OWNER_CHAIN_POSITIVE_FIELDS:
        if payload.get(field) is not True:
            violations.append(f"{OWNER_CHAIN_CONSEQUENCE_NOT_PROVEN}:{field}")
    for field in _OWNER_CHAIN_NEGATIVE_FIELDS:
        if payload.get(field) is not False:
            violations.append(f"{OWNER_CHAIN_CEILING_VIOLATED}:{field}")

    handle = payload.get("continuous_semantic_handle_digest_hex")
    if not _is_sha256(handle):
        violations.append(OWNER_CHAIN_HANDLE_INVALID)
    elif isinstance(nested, dict) and isinstance(nested.get("payload"), dict):
        nested_handle = nested["payload"].get("selected_target_semantic_handle_digest_hex")
        if handle != nested_handle:
            violations.append(OWNER_CHAIN_HANDLE_MISMATCH)

    supplied = projection.get("payload_sha256")
    if not _is_sha256(supplied):
        violations.append(OWNER_CHAIN_PAYLOAD_SHA256_INVALID)
    elif not any(
        item in violations
        for item in (MALFORMED_OWNER_CHAIN_PAYLOAD, OWNER_CHAIN_FIELDS_MISMATCH)
    ):
        try:
            expected = hashlib.sha256(_owner_chain_payload_bytes(payload)).hexdigest()
        except (KeyError, TypeError, ValueError):
            violations.append(MALFORMED_OWNER_CHAIN_PAYLOAD)
        else:
            if supplied != expected:
                violations.append(OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH)
    return list(dict.fromkeys(violations))


def verify_post_repair_portable_higher_owner_continuity(
    *, higher_owner_projection: dict[str, Any], **workcapsule_kwargs: Any
) -> list[str]:
    """Require PR541's nested projection to be the exact PR539 POST source-instance projection."""
    owner_violations = verify_portable_higher_owner_chain(higher_owner_projection)
    if owner_violations:
        return [OWNER_CHAIN_PREFIX + item for item in owner_violations]

    nested = higher_owner_projection["payload"]["canonical_target_projection"]
    source_violations = verify_post_repair_source_projection_continuity(
        astge_projection=nested,
        **workcapsule_kwargs,
    )
    if source_violations:
        return [POST_SOURCE_PREFIX + item for item in source_violations]
    return []


def admit_post_repair_portable_higher_owner_continuity(
    *, higher_owner_projection: dict[str, Any], **workcapsule_kwargs: Any
) -> dict[str, Any]:
    """Emit one source-instance + higher-owner continuity receipt, or fail closed."""
    violations = verify_post_repair_portable_higher_owner_continuity(
        higher_owner_projection=higher_owner_projection,
        **workcapsule_kwargs,
    )
    if violations:
        raise ValueError(
            "post-repair portable higher-owner continuity failed: " + ",".join(violations)
        )

    nested = higher_owner_projection["payload"]["canonical_target_projection"]
    source_admission = admit_post_repair_source_projection_continuity(
        astge_projection=nested,
        **workcapsule_kwargs,
    )
    payload = higher_owner_projection["payload"]
    out: dict[str, Any] = {
        "version": VERSION,
        "post_repair_source_instance_continuity_proven": True,
        "portable_higher_owner_chain_verified": True,
        "same_nested_canonical_target_projection_proven": True,
        "nested_canonical_target_projection_payload_sha256": nested["payload_sha256"],
        "portable_higher_owner_payload_sha256": higher_owner_projection["payload_sha256"],
        "continuous_semantic_handle_digest_hex": payload[
            "continuous_semantic_handle_digest_hex"
        ],
        "higher_owner_semantic_handle_continuity_proven": True,
        "post_closure_status": source_admission["post_closure_status"],
        "post_source_generation": source_admission["post_source_generation"],
        "post_source_sha256": source_admission["post_source_sha256"],
        "post_source_byte_len": source_admission["post_source_byte_len"],
        "projection_producer_authenticated": False,
        "higher_owner_producer_authenticated": False,
        "semantic_repair_correctness_minted": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
        "b_minus_approved": False,
        "authority": {
            "review": False,
            "mutation": False,
            "execution": False,
            "commit": False,
            "merge": False,
            "promotion": False,
            "provider_effect": False,
            "public_effect": False,
            "human": False,
        },
    }
    out["receipt_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()
    return out
