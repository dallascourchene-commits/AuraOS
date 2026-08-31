#!/usr/bin/env python3
"""Bind one exact pre-repair HOLD to one exact two-phase post-repair CLOSED lifecycle.

PR519 proves an observation-bound WorkCapsule closure receipt is the exact
consequence of pinned raw source-currentness inputs, previous binding, O8 receipt,
and candidate graph witness. PR518 independently proves a two-phase raw-source
lifecycle across distinct PRE and POST evidence roots and exactly verifies the
post closure against the internally derived post candidate.

This D0 membrane owns only their temporal relation. It requires the PR519
before-state to be exact HOLD on the same PRE raw inputs / previous binding / O8
receipt consumed by PR518, then requires PR518 to end in exact CLOSED on distinct
POST raw evidence. It does not prove that the repair is semantically correct,
authenticate either producer, derive a source->graph-node map, or grant any
review/mutation/execution/commit/merge/promotion/provider/public/human authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_observation_bound_exact_verifier import (
    admit_exact_observation_bound_reentry_closure,
    verify_exact_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_reentry_closure import CLOSED, HOLD
from scripts.aura_workcapsule_two_phase_source_bound_closure import (
    admit_two_phase_source_bound_exact_closure,
    verify_two_phase_source_bound_exact_closure,
)

VERSION = "AURA_WORKCAPSULE_EXACT_HOLD_TO_CLOSED_TRANSITION_V1"
PRE_PREFIX = "PRE_EXACT_OBSERVATION_"
LIFECYCLE_PREFIX = "TWO_PHASE_"
PRE_NOT_HOLD = "PRE_EXACT_OBSERVATION_NOT_HOLD"
POST_NOT_CLOSED = "POST_EXACT_LIFECYCLE_NOT_CLOSED"
PREVIOUS_BINDING_IDENTITY_MISMATCH = "TRANSITION_PREVIOUS_BINDING_IDENTITY_MISMATCH"
REENTRY_RECEIPT_IDENTITY_MISMATCH = "TRANSITION_REENTRY_RECEIPT_IDENTITY_MISMATCH"


def verify_exact_hold_to_closed_transition(
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
    post_closure_receipt: dict[str, Any],
) -> list[str]:
    """Verify one exact PRE HOLD -> distinct-evidence POST CLOSED transition."""
    violations: list[str] = []

    pre_violations = verify_exact_observation_bound_reentry_closure(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=pre_graph_witness,
        receipt=pre_observation_closure_receipt,
    )
    violations.extend(PRE_PREFIX + item for item in pre_violations)
    if pre_violations:
        return list(dict.fromkeys(violations))

    if pre_observation_closure_receipt.get("closure_status") != HOLD:
        violations.append(PRE_NOT_HOLD)
    if pre_observation_closure_receipt.get("previous_binding_identity") != previous_binding.get(
        "binding_identity"
    ):
        violations.append(PREVIOUS_BINDING_IDENTITY_MISMATCH)
    if pre_observation_closure_receipt.get("reentry_receipt_identity") != reentry_receipt.get(
        "receipt_identity"
    ):
        violations.append(REENTRY_RECEIPT_IDENTITY_MISMATCH)
    if violations:
        return list(dict.fromkeys(violations))

    lifecycle_violations = verify_two_phase_source_bound_exact_closure(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        closure_receipt=post_closure_receipt,
    )
    violations.extend(LIFECYCLE_PREFIX + item for item in lifecycle_violations)
    if lifecycle_violations:
        return list(dict.fromkeys(violations))

    if post_closure_receipt.get("closure_status") != CLOSED:
        violations.append(POST_NOT_CLOSED)
    return list(dict.fromkeys(violations))


def admit_exact_hold_to_closed_transition(
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
    post_closure_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Admit only the exact temporal transition consequence or fail closed."""
    violations = verify_exact_hold_to_closed_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        pre_observation_closure_receipt=pre_observation_closure_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        post_closure_receipt=post_closure_receipt,
    )
    if violations:
        raise ValueError("exact HOLD-to-CLOSED transition verification failed: " + ",".join(violations))

    pre_admission = admit_exact_observation_bound_reentry_closure(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_graph_witness=pre_graph_witness,
        receipt=pre_observation_closure_receipt,
    )
    lifecycle_admission = admit_two_phase_source_bound_exact_closure(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=reentry_receipt,
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        closure_receipt=post_closure_receipt,
    )

    return {
        "version": VERSION,
        "transition_status": "EXACT_PRE_HOLD_TO_POST_CLOSED",
        "exact_pre_observation_reproduction": True,
        "exact_two_phase_lifecycle": True,
        "pre_closure_status": pre_admission["closure_status"],
        "post_closure_status": lifecycle_admission["closure_status"],
        "previous_binding_identity": previous_binding["binding_identity"],
        "reentry_receipt_identity": reentry_receipt["receipt_identity"],
        "pre_observation_bound_receipt_identity": pre_admission[
            "observation_bound_receipt_identity"
        ],
        "post_exact_closure_receipt_identity": lifecycle_admission[
            "exact_closure_admission"
        ]["o10_closure_receipt_identity"],
        "pre_and_post_evidence_are_distinct_phases": lifecycle_admission[
            "pre_and_post_evidence_are_distinct_phases"
        ],
        "semantic_repair_correctness_minted": False,
        "producer_identity_authenticated": False,
        "pre_graph_producer_authenticated": False,
        "post_graph_producer_authenticated": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_dependency_cone_proven": False,
        "caller_candidate_binding_accepted": False,
        "caller_source_witnesses_accepted": False,
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
