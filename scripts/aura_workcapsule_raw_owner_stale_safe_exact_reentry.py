#!/usr/bin/env python3
"""Compose raw-source-owner exact WorkCapsule re-entry with rejected-currentness safety.

Parent 1 (PR514) derives WorkCapsule source observations from raw ASTGE currentness
inputs and constructs the canonical O8 re-entry receipt. Parent 2 (PR517) proves
that exact O8 reproduction over rejected STALE/UNKNOWN observations authenticates
only the decision to re-enter and cannot mint source CURRENTness.

This membrane performs one raw-owner derivation, then feeds only that internally
derived observation into the stale-safe exact verifier. Callers cannot inject an
observed source-witness list or a source-observation receipt.

Claim ceiling: raw-owner-bound rejected-currentness re-entry only. No producer
signature, semantic truth, review/mutation/execution/commit/merge/promotion,
provider/public/human effect, source->graph dependency map, node-level cone,
production mmap claim, hidden/model KV mutation, or Gate-10 authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_source_bound_exact_reentry import (
    compile_expected_source_bound_reentry,
)
from scripts.aura_workcapsule_stale_exact_reentry import (
    admit_stale_safe_exact_reentry,
    verify_stale_safe_exact_reentry,
)

VERSION = "AURA_WORKCAPSULE_RAW_OWNER_STALE_SAFE_EXACT_REENTRY_V1"
RAW_OWNER_EXPECTED_REENTRY_MISMATCH = "RAW_OWNER_EXPECTED_REENTRY_MISMATCH"
RAW_OWNER_REPLAY_FAILED = "RAW_OWNER_REPLAY_FAILED"
STALE_SAFE_INVALID_PREFIX = "STALE_SAFE_"


def _derive(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the raw source-currentness owner exactly once for this invocation."""
    return compile_expected_source_bound_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
    )


def _check_derived(
    *,
    projected: dict[str, Any],
    expected_reentry: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    if reentry_receipt != expected_reentry:
        violations.append(RAW_OWNER_EXPECTED_REENTRY_MISMATCH)

    violations.extend(
        STALE_SAFE_INVALID_PREFIX + item
        for item in verify_stale_safe_exact_reentry(
            source_observation_receipt=projected,
            previous_binding=previous_binding,
            observed_graph_witness=observed_graph_witness,
            reentry_receipt=reentry_receipt,
        )
    )
    return list(dict.fromkeys(violations))


def verify_raw_owner_stale_safe_exact_reentry(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
) -> list[str]:
    """Verify rejected-currentness exact re-entry from raw owner evidence.

    The public boundary deliberately has neither ``source_observation_receipt`` nor
    ``observed_source_witnesses``. Those are derived internally from raw currentness
    evidence through the PR514 owner path.
    """
    try:
        projected, expected = _derive(
            root=root,
            codemap=codemap,
            anchor_manifest=anchor_manifest,
            witness_manifest=witness_manifest,
            previous_binding=previous_binding,
            observed_graph_witness=observed_graph_witness,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"{RAW_OWNER_REPLAY_FAILED}:{type(exc).__name__}:{exc}"]

    return _check_derived(
        projected=projected,
        expected_reentry=expected,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )


def admit_raw_owner_stale_safe_exact_reentry(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Admit only the raw-owner-bound rejected-currentness re-entry consequence."""
    projected, expected = _derive(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
    )
    violations = _check_derived(
        projected=projected,
        expected_reentry=expected,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )
    if violations:
        raise ValueError(
            "raw-owner stale-safe exact re-entry verification failed: "
            + ",".join(violations)
        )

    stale_safe = admit_stale_safe_exact_reentry(
        source_observation_receipt=projected,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )

    return {
        "version": VERSION,
        "raw_source_owner_recompiled": True,
        "source_observation_receipt_accepted_from_caller": False,
        "observed_source_witnesses_accepted_from_caller": False,
        "source_projection_receipt_identity": projected["receipt_identity"],
        "source_owner_bound_exact_reproduction": True,
        "rejected_currentness_invariant_proven": True,
        "exact_input_reproduction": stale_safe["exact_input_reproduction"],
        "previous_binding_identity": stale_safe["previous_binding_identity"],
        "observed_binding_identity": stale_safe["observed_binding_identity"],
        "o8_receipt_identity": stale_safe["o8_receipt_identity"],
        "minimum_reentry_scope": stale_safe["minimum_reentry_scope"],
        "minimum_reentry_source_keys": stale_safe["minimum_reentry_source_keys"],
        "rejected_dependency_keys": stale_safe["rejected_dependency_keys"],
        "stale_source_count": stale_safe["stale_source_count"],
        "unresolved_source_count": stale_safe["unresolved_source_count"],
        "reentry_required": stale_safe["reentry_required"],
        "stale_observed_bytes_bound_to_source_generation": False,
        "current_source_evidence_admitted": False,
        "source_currentness_minted_by_exact_reproduction": False,
        "graph_witness_producer_authenticated": False,
        "source_observation_producer_authenticated": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "semantic_truth_minted": False,
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
