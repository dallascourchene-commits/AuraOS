#!/usr/bin/env python3
"""Remove caller-controlled PRE intermediates from exact HOLD -> CLOSED transition.

PR527 owns the complete rejected-currentness PRE lifecycle from raw source-owner
inputs. It internally derives the canonical O8 re-entry receipt and the exact
observation-bound HOLD receipt; callers cannot provide either object. PR531 owns
the temporal relation from one exact PRE HOLD to one exact distinct-evidence POST
CLOSED lifecycle, but deliberately accepts those PRE artifacts as pinned inputs.

This D0 membrane composes the owners at their intended boundary. It recompiles
PR527 from raw PRE evidence, then passes only PR527's internally derived O8 and
HOLD receipts to PR531. The POST closure remains an explicit pinned input because
its derivation belongs to a different downstream boundary.

The result proves exact raw-owner-bound temporal transition only. It does not mint
source currentness, producer identity, semantic repair correctness, review or
execution authority, or any external effect.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_exact_hold_to_closed_transition import (
    admit_exact_hold_to_closed_transition,
    verify_exact_hold_to_closed_transition,
)
from scripts.aura_workcapsule_raw_owner_end_to_end_stale_lifecycle import (
    admit_raw_owner_end_to_end_stale_lifecycle,
    compile_raw_owner_end_to_end_stale_lifecycle,
    verify_raw_owner_end_to_end_stale_lifecycle,
)

VERSION = "AURA_WORKCAPSULE_RAW_OWNER_HOLD_TO_CLOSED_TRANSITION_V1"
PRE_PREFIX = "PRE_RAW_OWNER_"
TRANSITION_PREFIX = "TRANSITION_"
PRE_NOT_HOLD = "PRE_RAW_OWNER_LIFECYCLE_NOT_HOLD"
REENTRY_IDENTITY_MISMATCH = "DERIVED_REENTRY_IDENTITY_MISMATCH"
PRE_CLOSURE_IDENTITY_MISMATCH = "DERIVED_PRE_CLOSURE_IDENTITY_MISMATCH"


def _derive_pre_lifecycle(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
) -> dict[str, Any]:
    return compile_raw_owner_end_to_end_stale_lifecycle(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
    )


def verify_raw_owner_hold_to_closed_transition(
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
    post_closure_receipt: dict[str, Any],
) -> list[str]:
    """Verify a raw-owner-derived PRE HOLD -> distinct POST CLOSED transition."""
    try:
        pre = _derive_pre_lifecycle(
            pre_root=pre_root,
            pre_codemap=pre_codemap,
            pre_anchor_manifest=pre_anchor_manifest,
            pre_witness_manifest=pre_witness_manifest,
            previous_binding=previous_binding,
            pre_graph_witness=pre_graph_witness,
        )
    except ValueError as exc:
        return [f"{PRE_PREFIX}RECOMPILE_FAILED:{exc}"]

    pre_violations = verify_raw_owner_end_to_end_stale_lifecycle(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
        lifecycle_receipt=pre,
    )
    if pre_violations:
        return [PRE_PREFIX + item for item in pre_violations]
    if pre.get("closure_status") != "HOLD":
        return [PRE_NOT_HOLD]

    transition_violations = verify_exact_hold_to_closed_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=pre["derived_reentry_receipt"],
        pre_observation_closure_receipt=pre["closure_receipt"],
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        post_closure_receipt=post_closure_receipt,
    )
    return [TRANSITION_PREFIX + item for item in transition_violations]


def admit_raw_owner_hold_to_closed_transition(
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
    post_closure_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Admit only the exact no-caller-PRE-intermediate temporal transition."""
    violations = verify_raw_owner_hold_to_closed_transition(
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
        post_closure_receipt=post_closure_receipt,
    )
    if violations:
        raise ValueError(
            "raw-owner HOLD-to-CLOSED transition verification failed: " + ",".join(violations)
        )

    pre = _derive_pre_lifecycle(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
    )
    pre_admission = admit_raw_owner_end_to_end_stale_lifecycle(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        candidate_graph_witness=pre_graph_witness,
        lifecycle_receipt=pre,
    )
    transition = admit_exact_hold_to_closed_transition(
        pre_root=pre_root,
        pre_codemap=pre_codemap,
        pre_anchor_manifest=pre_anchor_manifest,
        pre_witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        pre_graph_witness=pre_graph_witness,
        reentry_receipt=pre["derived_reentry_receipt"],
        pre_observation_closure_receipt=pre["closure_receipt"],
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        post_graph_witness=post_graph_witness,
        post_closure_receipt=post_closure_receipt,
    )

    identity_violations: list[str] = []
    if pre_admission.get("derived_reentry_receipt_identity") != transition.get(
        "reentry_receipt_identity"
    ):
        identity_violations.append(REENTRY_IDENTITY_MISMATCH)
    if pre_admission.get("closure_receipt_identity") != transition.get(
        "pre_observation_bound_receipt_identity"
    ):
        identity_violations.append(PRE_CLOSURE_IDENTITY_MISMATCH)
    if identity_violations:
        raise ValueError("raw-owner transition identity continuity failed: " + ",".join(identity_violations))

    return {
        "version": VERSION,
        "raw_owner_pre_lifecycle_derived": True,
        "caller_reentry_receipt_accepted": False,
        "caller_pre_observation_receipt_accepted": False,
        "caller_source_observation_receipt_accepted": False,
        "caller_source_witnesses_accepted": False,
        "caller_candidate_binding_accepted": False,
        "post_closure_receipt_pinned": True,
        "exact_hold_to_closed_transition": True,
        "pre_closure_status": transition["pre_closure_status"],
        "post_closure_status": transition["post_closure_status"],
        "derived_reentry_receipt_identity": pre_admission[
            "derived_reentry_receipt_identity"
        ],
        "derived_pre_closure_receipt_identity": pre_admission["closure_receipt_identity"],
        "post_closure_receipt_identity": transition["post_exact_closure_receipt_identity"],
        "pre_and_post_evidence_are_distinct_phases": transition[
            "pre_and_post_evidence_are_distinct_phases"
        ],
        "source_currentness_minted": False,
        "semantic_repair_correctness_minted": False,
        "producer_identity_authenticated": False,
        "pre_graph_producer_authenticated": False,
        "post_graph_producer_authenticated": False,
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
