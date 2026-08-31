#!/usr/bin/env python3
"""Bind exact WorkCapsule re-entry reproduction to raw source-currentness evidence.

PR509 projects the independently owned ASTGE source-currentness result into the
source witnesses consumed by WorkCapsule O8.  PR510 proves that an O8 receipt is
the exact deterministic consequence of the *supplied* previous binding, graph
witness, and source witnesses.  Those are intentionally separate owner
boundaries.

This D0 membrane closes only the source-evidence composition seam: callers may
supply raw ASTGE currentness inputs, but they may not supply the O8 source
witness list directly.  The membrane recompiles PR509 from the raw owner inputs,
verifies that projection, feeds only its O7-compatible witnesses into O8/PR510,
and requires the candidate O8 receipt to be the exact reproduction of those
derived inputs.

Consequently a caller-supplied CURRENT witness cannot launder raw STALE bytes
into a valid SourceGeneration, and UNKNOWN source evidence cannot be guessed
back into the prior dependency identity.  This module does not authenticate the
graph witness or producer, prove semantic truth, or grant review/mutation/
execution/commit/merge/promotion/provider/public/human authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_reentry_exact_verifier import (
    admit_exact_reentry_receipt,
    verify_exact_reentry_receipt,
)
from scripts.aura_workcapsule_reentry_invalidation import compile_reentry_invalidation
from scripts.aura_workcapsule_source_reentry_observation import (
    compile_source_reentry_observations,
    verify_source_reentry_observations,
)

VERSION = "AURA_WORKCAPSULE_SOURCE_BOUND_EXACT_REENTRY_V1"
SOURCE_PROJECTION_INVALID = "SOURCE_REENTRY_PROJECTION_INVALID"
SOURCE_OWNER_BOUND_REPRODUCTION = "SOURCE_OWNER_BOUND_EXACT_REPRODUCTION"


def _projection(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    projected = compile_source_reentry_observations(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
    )
    return projected, verify_source_reentry_observations(projected)


def compile_expected_source_bound_reentry(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recompile PR509 and then the canonical O8 receipt from raw owner inputs."""
    projected, projection_violations = _projection(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
    )
    if projection_violations:
        raise ValueError(
            "source re-entry projection is invalid: " + ",".join(projection_violations)
        )

    receipt = compile_reentry_invalidation(
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        observed_source_witnesses=projected["o7_source_witnesses"],
    )
    return projected, receipt


def verify_source_bound_exact_reentry(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    receipt: dict[str, Any],
) -> list[str]:
    """Verify an O8 receipt against raw source-currentness owner evidence.

    The caller has no ``observed_source_witnesses`` argument.  Those witnesses
    are deterministically derived through PR509, preserving STALE expected
    identity and leaving UNKNOWN identity unresolved.
    """
    projected, projection_violations = _projection(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
    )
    violations = [f"{SOURCE_PROJECTION_INVALID}:{item}" for item in projection_violations]
    if projection_violations:
        return list(dict.fromkeys(violations))

    violations.extend(
        verify_exact_reentry_receipt(
            previous_binding=previous_binding,
            observed_graph_witness=observed_graph_witness,
            observed_source_witnesses=projected["o7_source_witnesses"],
            receipt=receipt,
        )
    )
    return list(dict.fromkeys(violations))


def admit_source_bound_exact_reentry(
    *,
    root: Path,
    codemap: dict[str, Any],
    anchor_manifest: dict[str, Any],
    witness_manifest: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Return a narrow source-owner-bound exact-reproduction admission."""
    projected, expected = compile_expected_source_bound_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
    )

    violations = verify_exact_reentry_receipt(
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        observed_source_witnesses=projected["o7_source_witnesses"],
        receipt=receipt,
    )
    if violations:
        raise ValueError(
            "source-owner-bound exact re-entry verification failed: "
            + ",".join(violations)
        )

    # Reuse PR510's admission after the raw-evidence-derived witness set is
    # frozen.  This deliberately does not widen PR510's authority ceiling.
    exact = admit_exact_reentry_receipt(
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        observed_source_witnesses=projected["o7_source_witnesses"],
        receipt=receipt,
    )

    stale = [
        row for row in projected["source_observations"] if row.get("currentness") == "STALE"
    ]
    unknown = [
        row
        for row in projected["unresolved_prior_sources"]
        if row.get("currentness") == "UNKNOWN"
    ]

    return {
        "version": VERSION,
        "admission_kind": SOURCE_OWNER_BOUND_REPRODUCTION,
        "source_owner_bound_exact_reproduction": True,
        "source_projection_receipt_identity": projected["receipt_identity"],
        "o8_receipt_identity": exact["o8_receipt_identity"],
        "previous_binding_identity": exact["previous_binding_identity"],
        "observed_binding_identity": exact["observed_binding_identity"],
        "minimum_reentry_scope": exact["minimum_reentry_scope"],
        "minimum_reentry_source_keys": exact["minimum_reentry_source_keys"],
        "canonical_o8_receipt_equal": receipt == expected,
        "stale_dependency_count": len(stale),
        "unknown_dependency_count": len(unknown),
        "stale_expected_dependency_identity_preserved": all(
            row.get("dependency_identity_source") == "EXPECTED_PR488_SOURCE_BODY_WITNESS"
            for row in stale
        ),
        "stale_observed_bytes_bound_to_source_generation": any(
            row.get("observed_bytes_bound_to_source_generation") is True for row in stale
        ),
        "unknown_identity_guessed": any(row.get("identity_guessed") is True for row in unknown),
        "graph_witness_producer_authenticated": False,
        "source_observation_producer_authenticated": False,
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
