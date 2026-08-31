#!/usr/bin/env python3
"""Bind PR548 scoped target identity through PR545's canonical higher-owner envelope.

PR548 proves a scoped post-repair witness and a PR539 portable target describe one exact
post-edit coordinate, but its public parent bundle still permits the portable target to be
caller-selected inside ``post_source_inputs``. PR545 reduces duplicate portable higher-owner
POST-source ownership to PR542 as the canonical semantic owner.

This D0 membrane accepts one scoped-rebind evidence bundle, one closed WorkCapsule evidence
bundle with no target projection slot, and one canonical portable higher-owner envelope. It
validates/admit the PR542 canonical owner, extracts that exact nested canonical target, feeds
only that target into PR548, and requires both parent admissions to agree on the exact shared
coordinate. It does not derive the scoped post-edit witness (PR549 owns that separate lane),
authenticate producers, prove semantics, narrow re-entry, or grant authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_workcapsule_post_source_portable_higher_owner_continuity import (
    admit_post_source_portable_higher_owner_continuity,
    verify_post_source_portable_higher_owner_continuity,
)
from scripts.aura_workcapsule_scoped_portable_target_identity import (
    admit_scoped_portable_target_identity,
    verify_scoped_portable_target_identity,
)

VERSION = "AURA_WORKCAPSULE_SCOPED_CANONICAL_HIGHER_OWNER_TARGET_V1"
CANONICAL_PREFIX = "CANONICAL_HIGHER_OWNER_"
SCOPED_PREFIX = "SCOPED_TARGET_"
MALFORMED_WORKCAPSULE_INPUTS = "MALFORMED_WORKCAPSULE_INPUTS"
WORKCAPSULE_FIELDS_MISMATCH = "WORKCAPSULE_FIELDS_MISMATCH"
CROSS_OWNER_COORDINATE_MISMATCH = "CROSS_OWNER_COORDINATE_MISMATCH"

_WORKCAPSULE_FIELDS = {
    "pre_root",
    "pre_codemap",
    "pre_anchor_manifest",
    "pre_witness_manifest",
    "previous_binding",
    "pre_graph_witness",
    "reentry_receipt",
    "pre_observation_closure_receipt",
    "post_root",
    "post_codemap",
    "post_anchor_manifest",
    "post_witness_manifest",
    "post_graph_witness",
    "post_observation_bound_receipt",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _parent_inputs(
    *, workcapsule_inputs: dict[str, Any], portable_higher_owner_projection: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(workcapsule_inputs, dict):
        raise ValueError(MALFORMED_WORKCAPSULE_INPUTS)
    if set(workcapsule_inputs) != _WORKCAPSULE_FIELDS:
        raise ValueError(WORKCAPSULE_FIELDS_MISMATCH)
    canonical = dict(workcapsule_inputs)
    canonical["portable_higher_owner_projection"] = portable_higher_owner_projection
    nested = portable_higher_owner_projection.get("payload", {}).get("canonical_target_projection")
    post_source = dict(workcapsule_inputs)
    post_source["astge_projection"] = nested
    return canonical, post_source


def verify_scoped_canonical_higher_owner_target(
    *,
    scoped_rebind_inputs: dict[str, Any],
    workcapsule_inputs: dict[str, Any],
    portable_higher_owner_projection: dict[str, Any],
) -> list[str]:
    """Require one canonical higher-owner envelope to supply PR548's target pivot."""
    try:
        canonical_inputs, post_source_inputs = _parent_inputs(
            workcapsule_inputs=workcapsule_inputs,
            portable_higher_owner_projection=portable_higher_owner_projection,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        return [str(exc)]

    try:
        canonical_violations = verify_post_source_portable_higher_owner_continuity(
            **canonical_inputs
        )
    except (KeyError, TypeError, ValueError):
        canonical_violations = ["MALFORMED_PARENT_INPUTS"]
    if canonical_violations:
        return [CANONICAL_PREFIX + item for item in canonical_violations]

    scoped_violations = verify_scoped_portable_target_identity(
        scoped_rebind_inputs=scoped_rebind_inputs,
        post_source_inputs=post_source_inputs,
    )
    if scoped_violations:
        return [SCOPED_PREFIX + item for item in scoped_violations]

    canonical = admit_post_source_portable_higher_owner_continuity(**canonical_inputs)
    scoped = admit_scoped_portable_target_identity(
        scoped_rebind_inputs=scoped_rebind_inputs,
        post_source_inputs=post_source_inputs,
    )
    shared = (
        canonical.get("repaired_dependency_key") == scoped.get("dependency_key")
        and canonical.get("post_source_generation") == scoped.get("post_source_generation")
        and canonical.get("post_source_sha256") == scoped.get("post_source_sha256")
        and canonical.get("post_source_byte_len") == scoped.get("post_source_byte_len")
        and canonical.get("selected_target_syntax_ordinal") == scoped.get("selected_target_syntax_ordinal")
        and canonical.get("selected_target_byte_start") == scoped.get("selected_target_byte_start")
        and canonical.get("selected_target_byte_end") == scoped.get("selected_target_byte_end")
        and canonical.get("continuous_semantic_handle_digest_hex")
        == scoped.get("selected_target_semantic_handle_digest_hex")
        and canonical.get("nested_canonical_target_projection_payload_sha256")
        == scoped.get("portable_projection_payload_sha256")
    )
    return [] if shared else [CROSS_OWNER_COORDINATE_MISMATCH]


def admit_scoped_canonical_higher_owner_target(**kwargs: Any) -> dict[str, Any]:
    violations = verify_scoped_canonical_higher_owner_target(**kwargs)
    if violations:
        raise ValueError("scoped canonical higher-owner target failed: " + ",".join(violations))

    canonical_inputs, post_source_inputs = _parent_inputs(
        workcapsule_inputs=kwargs["workcapsule_inputs"],
        portable_higher_owner_projection=kwargs["portable_higher_owner_projection"],
    )
    canonical = admit_post_source_portable_higher_owner_continuity(**canonical_inputs)
    scoped = admit_scoped_portable_target_identity(
        scoped_rebind_inputs=kwargs["scoped_rebind_inputs"],
        post_source_inputs=post_source_inputs,
    )
    out: dict[str, Any] = {
        "version": VERSION,
        "canonical_higher_owner_owner_chain_verified": True,
        "same_scoped_post_edit_target_coordinate_proven": True,
        "caller_portable_target_projection_accepted": False,
        "caller_post_edit_witness_accepted_by_this_child": True,
        "post_edit_witness_derivation_claimed": False,
        "dependency_key": scoped["dependency_key"],
        "post_source_generation": scoped["post_source_generation"],
        "post_source_sha256": scoped["post_source_sha256"],
        "post_source_byte_len": scoped["post_source_byte_len"],
        "selected_target_syntax_ordinal": scoped["selected_target_syntax_ordinal"],
        "selected_target_byte_start": scoped["selected_target_byte_start"],
        "selected_target_byte_end": scoped["selected_target_byte_end"],
        "continuous_semantic_handle_digest_hex": canonical[
            "continuous_semantic_handle_digest_hex"
        ],
        "portable_owner_chain_payload_sha256": canonical[
            "portable_owner_chain_payload_sha256"
        ],
        "nested_canonical_target_projection_payload_sha256": canonical[
            "nested_canonical_target_projection_payload_sha256"
        ],
        "canonical_source_continuity_receipt_identity": canonical[
            "source_continuity_receipt_identity"
        ],
        "scoped_target_identity_receipt_identity": scoped["receipt_identity"],
        "reentry_closed": False,
        "reentry_scope_narrowed_by_child": False,
        "source_currentness_minted_by_child": False,
        "producer_authenticated": False,
        "semantic_repair_correctness_proven": False,
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
    out["receipt_identity"] = _identity(out)
    return out
