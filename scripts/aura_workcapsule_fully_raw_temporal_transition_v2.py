#!/usr/bin/env python3
"""Derive an exact PRE HOLD -> POST CLOSED transition with one preserved PRE O8 identity.

PR527 derives the rejected-currentness PRE lifecycle entirely from raw owner evidence,
including the canonical O8 re-entry receipt and exact observation-bound HOLD. PR516
derives a POST candidate and closure from fresh POST raw currentness evidence when
provided one exact O8 receipt. PR531 is reused as an independent temporal oracle.

The crucial polarity is temporal: the repaired POST closure is derived from POST raw
evidence, but it remains bound to the PRE rejected-currentness O8. A separately
re-derived POST-world O8 is a different fact and is not interchangeable.

This membrane accepts no caller lifecycle intermediate and mints no producer trust,
semantic correctness, dependency cone, review authority, or external effect.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_exact_hold_to_closed_transition import (
    admit_exact_hold_to_closed_transition,
    verify_exact_hold_to_closed_transition,
)
from scripts.aura_workcapsule_observation_bound_closure import (
    compile_observation_bound_reentry_closure,
    verify_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_raw_owner_end_to_end_stale_lifecycle import (
    compile_raw_owner_end_to_end_stale_lifecycle,
    verify_raw_owner_end_to_end_stale_lifecycle,
)
from scripts.aura_workcapsule_reentry_closure import CLOSED, HOLD

VERSION = "AURA_WORKCAPSULE_FULLY_RAW_TEMPORAL_TRANSITION_V2"
PRE_PREFIX = "PRE_RAW_OWNER_"
POST_PREFIX = "POST_OBSERVATION_BOUND_"
ORACLE_PREFIX = "TEMPORAL_ORACLE_"
PRE_NOT_HOLD = "PRE_RAW_OWNER_LIFECYCLE_NOT_HOLD"
POST_NOT_CLOSED = "POST_OBSERVATION_BOUND_CLOSURE_NOT_CLOSED"
PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT = "PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT"
POST_REENTRY_IDENTITY_MISMATCH = "POST_CLOSURE_NOT_BOUND_TO_PRE_REJECTED_O8"
ORACLE_REENTRY_IDENTITY_MISMATCH = "ORACLE_REENTRY_IDENTITY_MISMATCH"
ORACLE_POST_CLOSURE_IDENTITY_MISMATCH = "ORACLE_POST_CLOSURE_IDENTITY_MISMATCH"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _identity(payload_without_identity: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "WORKCAPSULE_FULLY_RAW_TEMPORAL_TRANSITION_V2_FULL_PAYLOAD_EXCEPT_RECEIPT_IDENTITY",
        "value": hashlib.sha256(_canonical_bytes(payload_without_identity)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }


def _derive_pre(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
) -> dict[str, Any]:
    pre = compile_raw_owner_end_to_end_stale_lifecycle(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
    )
    violations = verify_raw_owner_end_to_end_stale_lifecycle(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
        lifecycle_receipt=pre,
    )
    if violations:
        raise ValueError("PRE raw-owner lifecycle is not exact: " + ",".join(violations))
    if pre.get("closure_status") != HOLD:
        raise ValueError(PRE_NOT_HOLD)
    return pre


def _derive_post(
    *,
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    post_graph_witness: dict[str, Any],
    pre_reentry_receipt: dict[str, Any],
) -> dict[str, Any]:
    post = compile_observation_bound_reentry_closure(
        root=post_root,
        codemap=post_codemap,
        anchor_manifest=post_anchor_manifest,
        witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=pre_reentry_receipt,
        candidate_graph_witness=post_graph_witness,
    )
    violations = verify_observation_bound_reentry_closure(post)
    if violations:
        raise ValueError("POST observation-bound closure is not coherent: " + ",".join(violations))
    if post.get("reentry_receipt_identity") != pre_reentry_receipt.get("receipt_identity"):
        raise ValueError(POST_REENTRY_IDENTITY_MISMATCH)
    if post.get("closure_status") != CLOSED:
        raise ValueError(POST_NOT_CLOSED)
    closure = post.get("closure_receipt")
    if not isinstance(closure, dict) or closure.get("closure_status") != CLOSED:
        raise ValueError(POST_NOT_CLOSED)
    return post


def verify_fully_raw_temporal_transition_v2(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
) -> list[str]:
    """Verify one fully derived transition while preserving the PRE O8 identity."""
    if pre_root.resolve() == post_root.resolve():
        return [PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT]

    try:
        pre = _derive_pre(
            pre_root=pre_root,
            pre_codemap=pre_codemap,
            pre_anchor_manifest=pre_anchor_manifest,
            pre_witness_manifest=pre_witness_manifest,
            previous_binding=previous_binding,
            pre_graph_witness=pre_graph_witness,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"{PRE_PREFIX}DERIVATION_FAILED:{exc}"]

    pre_reentry = pre.get("derived_reentry_receipt")
    pre_hold = pre.get("closure_receipt")
    if not isinstance(pre_reentry, dict) or not isinstance(pre_hold, dict):
        return [f"{PRE_PREFIX}DERIVED_EVIDENCE_MISSING"]

    try:
        post = _derive_post(
            post_root=post_root,
            post_codemap=post_codemap,
            post_anchor_manifest=post_anchor_manifest,
            post_witness_manifest=post_witness_manifest,
            previous_binding=previous_binding,
            post_graph_witness=post_graph_witness,
            pre_reentry_receipt=pre_reentry,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"{POST_PREFIX}DERIVATION_FAILED:{exc}"]

    post_closure = post["closure_receipt"]
    oracle_violations = verify_exact_hold_to_closed_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=pre_reentry,
        pre_observation_closure_receipt=pre_hold,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        post_closure_receipt=post_closure,
    )
    return [ORACLE_PREFIX + item for item in oracle_violations]


def admit_fully_raw_temporal_transition_v2(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
) -> dict[str, Any]:
    """Admit one no-caller-intermediate temporal consequence or fail closed."""
    violations = verify_fully_raw_temporal_transition_v2(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
    )
    if violations:
        raise ValueError("fully raw temporal transition V2 failed: " + ",".join(violations))

    pre = _derive_pre(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
    )
    pre_reentry = pre["derived_reentry_receipt"]
    pre_hold = pre["closure_receipt"]
    post = _derive_post(
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        post_graph_witness=post_graph_witness,
        pre_reentry_receipt=pre_reentry,
    )
    post_closure = post["closure_receipt"]
    oracle = admit_exact_hold_to_closed_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=pre_reentry,
        pre_observation_closure_receipt=pre_hold,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        post_closure_receipt=post_closure,
    )

    if oracle.get("reentry_receipt_identity") != pre_reentry.get("receipt_identity"):
        raise ValueError(ORACLE_REENTRY_IDENTITY_MISMATCH)
    if oracle.get("post_exact_closure_receipt_identity") != post_closure.get("receipt_identity"):
        raise ValueError(ORACLE_POST_CLOSURE_IDENTITY_MISMATCH)

    payload: dict[str, Any] = {
        "version": VERSION,
        "exact_hold_to_closed_transition": True,
        "pre_raw_owner_lifecycle_reproduced": True,
        "post_candidate_and_closure_derived_from_raw_evidence": True,
        "pre_and_post_evidence_are_distinct_phases": True,
        "pre_closure_status": pre["closure_status"],
        "post_closure_status": post["closure_status"],
        "pre_rejected_reentry_receipt_identity": pre_reentry["receipt_identity"],
        "post_observation_bound_reentry_receipt_identity": post["reentry_receipt_identity"],
        "pre_observation_bound_receipt_identity": pre_hold["receipt_identity"],
        "post_observation_bound_receipt_identity": post["receipt_identity"],
        "post_derived_candidate_binding_identity": post["derived_candidate_binding_identity"],
        "post_derived_closure_receipt_identity": post_closure["receipt_identity"],
        "temporal_oracle_post_closure_receipt_identity": oracle[
            "post_exact_closure_receipt_identity"
        ],
        "same_pre_rejected_o8_drives_post_closure": True,
        "caller_reentry_receipt_accepted": False,
        "caller_pre_observation_receipt_accepted": False,
        "caller_post_closure_receipt_accepted": False,
        "caller_source_observation_receipt_accepted": False,
        "caller_source_witnesses_accepted": False,
        "caller_candidate_binding_accepted": False,
        "source_currentness_minted": False,
        "producer_identity_authenticated": False,
        "semantic_repair_correctness_minted": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_dependency_cone_proven": False,
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
