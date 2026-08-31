#!/usr/bin/env python3
"""Two-phase raw-source-bound exact WorkCapsule re-entry lifecycle verification.

PR514 proves an O8 re-entry receipt is exactly derived from raw source-currentness
owner evidence for the *pre-reentry* state. PR513 proves an O10 closure receipt is
exactly derived from the previous binding, re-entry receipt, and supplied candidate
binding. This membrane joins those independently green owners without collapsing
time: pre-reentry evidence and post-repair evidence are separate raw inputs.

The post-repair candidate binding is derived internally by rerunning PR509 against
post-repair raw source evidence. A caller cannot supply the candidate binding or a
source witness list. Graph witnesses remain explicit higher-owner inputs and their
producer identity is not authenticated here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_context_binding import compile_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_closure_exact_verifier import (
    admit_exact_reentry_closure,
    verify_exact_reentry_closure,
)
from scripts.aura_workcapsule_source_bound_exact_reentry import (
    admit_source_bound_exact_reentry,
    verify_source_bound_exact_reentry,
)
from scripts.aura_workcapsule_source_reentry_observation import (
    compile_source_reentry_observations,
    verify_source_reentry_observations,
)

VERSION = "AURA_WORKCAPSULE_TWO_PHASE_SOURCE_BOUND_CLOSURE_V1"


def derive_post_reentry_candidate(
    *,
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    post_graph_witness: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive the post-repair O7 candidate from post-phase raw source evidence."""
    projection = compile_source_reentry_observations(
        root=post_root,
        codemap=post_codemap,
        anchor_manifest=post_anchor_manifest,
        witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
    )
    violations = verify_source_reentry_observations(projection)
    if violations:
        raise ValueError("post source observation is not coherent: " + ",".join(violations))
    candidate = compile_workcapsule_context_binding(
        capsule=previous_binding["capsule"],
        graph_witness=post_graph_witness,
        source_witnesses=projection["o7_source_witnesses"],
    )
    return projection, candidate


def verify_two_phase_source_bound_exact_closure(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> list[str]:
    """Verify exact re-entry and exact closure against distinct raw phase evidence."""
    violations: list[str] = []
    if pre_root.resolve() == post_root.resolve():
        return ["PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT"]

    pre_violations = verify_source_bound_exact_reentry(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        receipt=reentry_receipt,
    )
    violations.extend(f"PRE_{item}" for item in pre_violations)
    if pre_violations:
        return list(dict.fromkeys(violations))

    try:
        post_projection, candidate = derive_post_reentry_candidate(
            post_root=post_root,
            post_codemap=post_codemap,
            post_anchor_manifest=post_anchor_manifest,
            post_witness_manifest=post_witness_manifest,
            previous_binding=previous_binding,
            post_graph_witness=post_graph_witness,
        )
    except ValueError as exc:
        return list(dict.fromkeys(violations + [f"POST_SOURCE_PROJECTION_INVALID:{exc}"]))

    if candidate.get("context_admitted") is not True:
        violations.append("POST_DERIVED_CANDIDATE_NOT_CURRENT")
        return list(dict.fromkeys(violations))
    if post_projection.get("source_generation_domain") != "SOURCE":
        violations.append("POST_SOURCE_GENERATION_DOMAIN_LOST")

    violations.extend(
        verify_exact_reentry_closure(
            previous_binding=previous_binding,
            reentry_receipt=reentry_receipt,
            candidate_binding=candidate,
            closure_receipt=closure_receipt,
        )
    )
    return list(dict.fromkeys(violations))


def admit_two_phase_source_bound_exact_closure(
    *,
    pre_root: Path,
    pre_codemap: dict[str, Any],
    pre_anchor_manifest: dict[str, Any],
    pre_witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    pre_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
    post_root: Path,
    post_codemap: dict[str, Any],
    post_anchor_manifest: dict[str, Any],
    post_witness_manifest: dict[str, Any],
    post_graph_witness: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Admit a two-phase exact lifecycle witness or fail closed."""
    violations = verify_two_phase_source_bound_exact_closure(
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
        closure_receipt=closure_receipt,
    )
    if violations:
        raise ValueError("two-phase source-bound closure verification failed: " + ",".join(violations))

    pre_admission = admit_source_bound_exact_reentry(
        root=pre_root,
        codemap=pre_codemap,
        anchor_manifest=pre_anchor_manifest,
        witness_manifest=pre_witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=pre_graph_witness,
        receipt=reentry_receipt,
    )
    post_projection, candidate = derive_post_reentry_candidate(
        post_root=post_root,
        post_codemap=post_codemap,
        post_anchor_manifest=post_anchor_manifest,
        post_witness_manifest=post_witness_manifest,
        previous_binding=previous_binding,
        post_graph_witness=post_graph_witness,
    )
    closure_admission = admit_exact_reentry_closure(
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_binding=candidate,
        closure_receipt=closure_receipt,
    )
    return {
        "version": VERSION,
        "two_phase_raw_source_bound_exact_lifecycle": True,
        "pre_and_post_evidence_are_distinct_phases": True,
        "pre_source_owner_bound_exact_reentry": pre_admission,
        "post_source_projection_receipt_identity": post_projection["receipt_identity"],
        "post_derived_candidate_binding_identity": candidate["binding_identity"],
        "exact_closure_admission": closure_admission,
        "closure_status": closure_admission["closure_status"],
        "caller_source_witnesses_accepted": False,
        "caller_candidate_binding_accepted": False,
        "source_generation_domain_preserved": post_projection.get("source_generation_domain") == "SOURCE",
        "pre_graph_producer_authenticated": False,
        "post_graph_producer_authenticated": False,
        "source_observation_producer_authenticated": False,
        "semantic_truth_minted": False,
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
