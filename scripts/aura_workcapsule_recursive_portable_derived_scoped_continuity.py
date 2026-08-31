#!/usr/bin/env python3
"""Lower-input recursive portable higher-owner continuity.

PR549 deterministically derives the PR532-shaped scoped post-edit witness from one
portable higher-owner target plus preserved PRE rejected-currentness evidence. PR561
re-proves PR558 recursive cross-runtime canonicalization against PR555's current
canonical shared-target coordinate owner.

This membrane composes those earned surfaces without reopening the legacy PR548
caller ``scoped_target_inputs`` bundle. PR555 remains the sole owner of shared target
coordinate equality. PR558/561 remains the recursive transport/canonicalization owner.
The child only derives a normalized scoped receipt view from PR549's already-admitted
result and asks those owners to re-prove the relation.

No producer authentication, semantic correctness, raw-byte semantic-handle derivation,
re-entry closure, invalidation narrowing, or effect authority is minted.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_portable_derived_scoped_rebind import (
    admit_portable_derived_scoped_rebind,
    derive_post_edit_witness_from_portable_target,
    verify_portable_derived_scoped_rebind,
)
from scripts.aura_workcapsule_post_source_portable_higher_owner_continuity import (
    admit_post_source_portable_higher_owner_continuity,
)
from scripts.aura_workcapsule_scoped_higher_owner_portable_continuity import (
    canonical_nested_projection,
    verify_portable_higher_owner_projection,
)
from scripts import aura_workcapsule_scoped_portable_target_identity as shared_owner

VERSION = "AURA_WORKCAPSULE_RECURSIVE_PORTABLE_DERIVED_SCOPED_CONTINUITY_V1"
DERIVED_PREFIX = "DERIVED_SCOPED_"
RECURSIVE_PREFIX = "RECURSIVE_OWNER_"
SHARED_PREFIX = "SHARED_OWNER_"
NESTED_PROJECTION_DIGEST_MISMATCH = "NESTED_PROJECTION_DIGEST_MISMATCH"
OWNER_CHAIN_DIGEST_MISMATCH = "OWNER_CHAIN_DIGEST_MISMATCH"
DERIVED_OWNER_CHAIN_DIGEST_MISMATCH = "DERIVED_OWNER_CHAIN_DIGEST_MISMATCH"
CONTINUOUS_HANDLE_MISMATCH = "CONTINUOUS_HANDLE_MISMATCH"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _portable_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "pre_root": kwargs["pre_root"],
        "pre_codemap": kwargs["pre_codemap"],
        "pre_anchor_manifest": kwargs["pre_anchor_manifest"],
        "pre_witness_manifest": kwargs["pre_witness_manifest"],
        "previous_binding": kwargs["previous_binding"],
        "pre_graph_witness": kwargs["pre_graph_witness"],
        "reentry_receipt": kwargs["reentry_receipt"],
        "pre_observation_closure_receipt": kwargs["pre_observation_closure_receipt"],
        "post_root": kwargs["post_root"],
        "post_codemap": kwargs["post_codemap"],
        "post_anchor_manifest": kwargs["post_anchor_manifest"],
        "post_witness_manifest": kwargs["post_witness_manifest"],
        "post_graph_witness": kwargs["post_graph_witness"],
        "post_observation_bound_receipt": kwargs["post_observation_bound_receipt"],
        "portable_higher_owner_projection": kwargs["portable_higher_owner_projection"],
    }


def _normalized_scoped_receipt(
    derived: dict[str, Any], witness: dict[str, Any]
) -> dict[str, Any]:
    """Expose only the coordinate fields PR555 owns; mint no new semantic receipt."""
    return {
        "dependency_key": dict(derived["dependency_key"]),
        "post_source_generation": derived["post_source_generation"],
        "post_body_sha256": derived["post_body_sha256"],
        "post_byte_len": derived["post_byte_len"],
        "syntax_ordinal": witness["syntax_ordinal"],
        "byte_start": witness["byte_start"],
        "byte_end": witness["byte_end"],
        "semantic_handle_digest": derived["semantic_handle_digest"],
    }


def verify_recursive_portable_derived_scoped_continuity(
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
    portable_higher_owner_projection: dict[str, Any],
    reentry_admission: dict[str, Any],
    source_observation: dict[str, Any],
    dependency_key: dict[str, Any],
) -> list[str]:
    """Prove recursive higher-owner continuity without caller-scoped evidence."""
    kwargs = locals()
    derived_violations = verify_portable_derived_scoped_rebind(**kwargs)
    recursive_violations = verify_portable_higher_owner_projection(
        portable_higher_owner_projection
    )
    violations = [DERIVED_PREFIX + item for item in derived_violations]
    violations.extend(RECURSIVE_PREFIX + item for item in recursive_violations)
    if violations:
        return list(dict.fromkeys(violations))

    derived = admit_portable_derived_scoped_rebind(**kwargs)
    witness = derive_post_edit_witness_from_portable_target(
        portable_higher_owner_projection=portable_higher_owner_projection,
        source_observation=source_observation,
    )
    source = admit_post_source_portable_higher_owner_continuity(**_portable_kwargs(kwargs))
    scoped_receipt = _normalized_scoped_receipt(derived, witness)

    shared_violations = shared_owner.verify_shared_target_coordinates(
        scoped_receipt=scoped_receipt,
        source_receipt=source,
    )
    violations.extend(SHARED_PREFIX + item for item in shared_violations)
    if violations:
        return list(dict.fromkeys(violations))

    nested = canonical_nested_projection(
        portable_higher_owner_projection["payload"]["canonical_target_projection"]
    )
    if source.get("nested_canonical_target_projection_payload_sha256") != nested.get(
        "payload_sha256"
    ):
        violations.append(NESTED_PROJECTION_DIGEST_MISMATCH)
    if source.get("portable_owner_chain_payload_sha256") != portable_higher_owner_projection.get(
        "payload_sha256"
    ):
        violations.append(OWNER_CHAIN_DIGEST_MISMATCH)
    if derived.get("portable_owner_chain_payload_sha256") != portable_higher_owner_projection.get(
        "payload_sha256"
    ):
        violations.append(DERIVED_OWNER_CHAIN_DIGEST_MISMATCH)
    if derived.get("semantic_handle_digest") != portable_higher_owner_projection["payload"].get(
        "continuous_semantic_handle_digest_hex"
    ):
        violations.append(CONTINUOUS_HANDLE_MISMATCH)
    return list(dict.fromkeys(violations))


def admit_recursive_portable_derived_scoped_continuity(**kwargs: Any) -> dict[str, Any]:
    violations = verify_recursive_portable_derived_scoped_continuity(**kwargs)
    if violations:
        raise ValueError(
            "recursive portable-derived scoped continuity failed: " + ",".join(violations)
        )

    derived = admit_portable_derived_scoped_rebind(**kwargs)
    witness = derive_post_edit_witness_from_portable_target(
        portable_higher_owner_projection=kwargs["portable_higher_owner_projection"],
        source_observation=kwargs["source_observation"],
    )
    nested = canonical_nested_projection(
        kwargs["portable_higher_owner_projection"]["payload"]["canonical_target_projection"]
    )
    payload: dict[str, Any] = {
        "version": VERSION,
        "portable_derived_scoped_rebind_consumed": True,
        "caller_scoped_target_inputs_accepted": False,
        "caller_post_edit_witness_accepted": False,
        "one_portable_higher_owner_projection_used": True,
        "current_shared_coordinate_owner_reused": True,
        "second_shared_coordinate_owner_minted": False,
        "recursive_cross_runtime_canonicalization_reused": True,
        "dependency_key": dict(derived["dependency_key"]),
        "post_source_generation": int(derived["post_source_generation"]),
        "post_source_sha256": str(derived["post_body_sha256"]),
        "post_source_byte_len": int(derived["post_byte_len"]),
        "selected_target_syntax_ordinal": int(witness["syntax_ordinal"]),
        "selected_target_byte_start": int(witness["byte_start"]),
        "selected_target_byte_end": int(witness["byte_end"]),
        "selected_target_semantic_handle_digest_hex": str(derived["semantic_handle_digest"]),
        "nested_projection_payload_sha256": nested["payload_sha256"],
        "higher_owner_payload_sha256": kwargs["portable_higher_owner_projection"][
            "payload_sha256"
        ],
        "derived_scoped_receipt_identity": derived["receipt_identity"],
        "structural_handle_bound_to_raw_bytes": False,
        "producer_authenticated": False,
        "semantic_repair_correctness_proven": False,
        "semantic_truth_minted": False,
        "reentry_closed": False,
        "reentry_scope_narrowed": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
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
