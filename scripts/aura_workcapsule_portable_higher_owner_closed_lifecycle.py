#!/usr/bin/env python3
"""Bind one portable higher-owner ASTGE chain to one exact WorkCapsule POST-CLOSED lifecycle.

PR539 proves that a portable PR537 canonical-target projection describes the exact source instance
consumed by one canonical WorkCapsule POST-CLOSED lifecycle. PR541 wraps that same lower projection
inside a deterministic portable reduced higher-owner chain whose projected target handle equals the
continuous higher-owner handle.

This D0 membrane accepts only the PR541 outer transport envelope. It verifies that envelope, extracts
its exact nested lower projection internally, and delegates source-instance/lifecycle proof to PR539.
A caller cannot supply a second lower ASTGE projection beside the owner-chain envelope.
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

VERSION = "AURA_WORKCAPSULE_PORTABLE_HIGHER_OWNER_CLOSED_LIFECYCLE_V1"
OWNER_CHAIN_SCHEMA = "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1"
OWNER_CHAIN_CANONICALIZATION = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1"

OWNER_CHAIN_PREFIX = "OWNER_CHAIN_"
SOURCE_CONTINUITY_PREFIX = "SOURCE_CONTINUITY_"
POST_NOT_CLOSED = "POST_LIFECYCLE_NOT_CLOSED"
NESTED_PROJECTION_IDENTITY_MISMATCH = "NESTED_PROJECTION_IDENTITY_MISMATCH"
TARGET_HANDLE_MISMATCH = "TARGET_HANDLE_MISMATCH"

_OWNER_CHAIN_PAYLOAD_FIELDS = (
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


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _owner_chain_payload_bytes(payload: dict[str, Any]) -> bytes:
    ordered = {field: payload[field] for field in _OWNER_CHAIN_PAYLOAD_FIELDS}
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_portable_higher_owner_chain_projection(projection: dict[str, Any]) -> list[str]:
    """Validate the stable PR541 transport contract without authenticating its producer."""
    if not isinstance(projection, dict) or set(projection) != {"payload", "payload_sha256"}:
        return ["MALFORMED_OWNER_CHAIN_ENVELOPE"]
    payload = projection.get("payload")
    if not isinstance(payload, dict):
        return ["MALFORMED_OWNER_CHAIN_PAYLOAD"]
    if set(payload) != set(_OWNER_CHAIN_PAYLOAD_FIELDS):
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
            violations.append(f"OWNER_CHAIN_POSITIVE_PROOF_MISSING:{field}")
    for field in _NEGATIVE_OWNER_CHAIN_FIELDS:
        if payload.get(field) is not False:
            violations.append(f"OWNER_CHAIN_CEILING_VIOLATED:{field}")

    nested = payload.get("canonical_target_projection")
    nested_violations = verify_portable_canonical_target_projection(nested)
    violations.extend(f"NESTED_{item}" for item in nested_violations)
    handle = payload.get("continuous_semantic_handle_digest_hex")
    if not _is_sha256(handle):
        violations.append("OWNER_CHAIN_CONTINUOUS_HANDLE_INVALID")
    elif isinstance(nested, dict) and isinstance(nested.get("payload"), dict):
        projected = nested["payload"].get("selected_target_semantic_handle_digest_hex")
        if projected != handle:
            violations.append("OWNER_CHAIN_CONTINUOUS_HANDLE_MISMATCH")

    supplied = projection.get("payload_sha256")
    if not _is_sha256(supplied):
        violations.append("OWNER_CHAIN_PAYLOAD_SHA256_INVALID")
    else:
        expected = hashlib.sha256(_owner_chain_payload_bytes(payload)).hexdigest()
        if supplied != expected:
            violations.append("OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH")
    return list(dict.fromkeys(violations))


def verify_portable_higher_owner_chain_inside_closed_lifecycle(
    *,
    portable_owner_chain_projection: dict[str, Any],
    **lifecycle_kwargs: Any,
) -> list[str]:
    """Require one PR541 envelope to be the exact target/handle evidence used by PR539."""
    owner_chain_violations = verify_portable_higher_owner_chain_projection(
        portable_owner_chain_projection
    )
    if owner_chain_violations:
        return [OWNER_CHAIN_PREFIX + item for item in owner_chain_violations]

    payload = portable_owner_chain_projection["payload"]
    nested = payload["canonical_target_projection"]
    source_violations = verify_post_repair_source_projection_continuity(
        astge_projection=nested,
        **lifecycle_kwargs,
    )
    if source_violations:
        return [SOURCE_CONTINUITY_PREFIX + item for item in source_violations]

    source_admission = admit_post_repair_source_projection_continuity(
        astge_projection=nested,
        **lifecycle_kwargs,
    )
    violations: list[str] = []
    if source_admission.get("post_closure_status") != "CLOSED":
        violations.append(POST_NOT_CLOSED)
    if source_admission.get("portable_projection_payload_sha256") != nested.get("payload_sha256"):
        violations.append(NESTED_PROJECTION_IDENTITY_MISMATCH)
    if (
        source_admission.get("selected_target_semantic_handle_digest_hex")
        != payload.get("continuous_semantic_handle_digest_hex")
    ):
        violations.append(TARGET_HANDLE_MISMATCH)
    return violations


def admit_portable_higher_owner_chain_inside_closed_lifecycle(
    *,
    portable_owner_chain_projection: dict[str, Any],
    **lifecycle_kwargs: Any,
) -> dict[str, Any]:
    """Emit one exact portable owner-chain-in-closed-lifecycle receipt or fail closed."""
    violations = verify_portable_higher_owner_chain_inside_closed_lifecycle(
        portable_owner_chain_projection=portable_owner_chain_projection,
        **lifecycle_kwargs,
    )
    if violations:
        raise ValueError(
            "portable higher-owner closed-lifecycle verification failed: " + ",".join(violations)
        )

    payload = portable_owner_chain_projection["payload"]
    nested = payload["canonical_target_projection"]
    source_admission = admit_post_repair_source_projection_continuity(
        astge_projection=nested,
        **lifecycle_kwargs,
    )
    out: dict[str, Any] = {
        "version": VERSION,
        "post_closure_status": source_admission["post_closure_status"],
        "source_instance_continuity_proven": True,
        "portable_higher_owner_chain_verified": True,
        "same_nested_projection_used_by_lifecycle": True,
        "canonical_target_handle_continuity_inside_closed_lifecycle_proven": True,
        "portable_owner_chain_payload_sha256": portable_owner_chain_projection["payload_sha256"],
        "nested_canonical_target_projection_payload_sha256": nested["payload_sha256"],
        "source_continuity_receipt_identity": source_admission["receipt_identity"],
        "post_source_generation": source_admission["post_source_generation"],
        "post_source_sha256": source_admission["post_source_sha256"],
        "post_source_byte_len": source_admission["post_source_byte_len"],
        "selected_target_scope_local_id": source_admission["selected_target_scope_local_id"],
        "selected_target_parent_scope_local_id": source_admission[
            "selected_target_parent_scope_local_id"
        ],
        "selected_target_syntax_ordinal": source_admission["selected_target_syntax_ordinal"],
        "selected_target_byte_start": source_admission["selected_target_byte_start"],
        "selected_target_byte_end": source_admission["selected_target_byte_end"],
        "continuous_semantic_handle_digest_hex": payload[
            "continuous_semantic_handle_digest_hex"
        ],
        "caller_lower_astge_projection_accepted": False,
        "projection_producer_authenticated": False,
        "canonical_target_producer_authenticated": False,
        "semantic_repair_correctness_minted": False,
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
        "scope_profile": "WORKCAPSULE_PORTABLE_HIGHER_OWNER_CLOSED_LIFECYCLE_V1",
        "value": hashlib.sha256(_canonical_bytes(out)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
