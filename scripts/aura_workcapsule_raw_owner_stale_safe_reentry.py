#!/usr/bin/env python3
"""Raw-source-owner-bound stale-safe exact WorkCapsule re-entry.

PR517 proves that exact re-entry under rejected source currentness authenticates only
the re-entry decision: exactness must not mint source CURRENTness. PR514 proves that
an exact O8 re-entry receipt can be bound to raw source-currentness owner inputs so
a caller cannot choose the projected source-witness set independently.

This membrane composes those owners. Callers supply raw repository/CODEMAP/anchor/
source-body-witness inputs, not a precompiled source-observation receipt and not an
O8 source-witness list. The membrane recompiles PR509, verifies PR514's raw-owner
binding, then applies PR517's rejected-currentness semantics to that exact projection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.aura_workcapsule_source_bound_exact_reentry import (
    admit_source_bound_exact_reentry,
    verify_source_bound_exact_reentry,
)
from scripts.aura_workcapsule_source_reentry_observation import (
    compile_source_reentry_observations,
    verify_source_reentry_observations,
)
from scripts.aura_workcapsule_stale_exact_reentry import (
    admit_stale_safe_exact_reentry,
    verify_stale_safe_exact_reentry,
)

VERSION = "AURA_WORKCAPSULE_RAW_OWNER_STALE_SAFE_REENTRY_V1"


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
    """Verify one rejected-currentness re-entry against raw source-owner evidence."""
    projected, projection_violations = _projection(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
    )
    violations = [f"RAW_SOURCE_PROJECTION_{item}" for item in projection_violations]
    if projection_violations:
        return list(dict.fromkeys(violations))

    raw_owner_violations = verify_source_bound_exact_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        receipt=reentry_receipt,
    )
    violations.extend(f"RAW_OWNER_{item}" for item in raw_owner_violations)
    if raw_owner_violations:
        return list(dict.fromkeys(violations))

    stale_safe_violations = verify_stale_safe_exact_reentry(
        source_observation_receipt=projected,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )
    violations.extend(f"STALE_SAFE_{item}" for item in stale_safe_violations)
    return list(dict.fromkeys(violations))


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
    """Admit only a raw-owner-bound, rejected-currentness-driven re-entry decision."""
    violations = verify_raw_owner_stale_safe_exact_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )
    if violations:
        raise ValueError("raw-owner stale-safe exact re-entry verification failed: " + ",".join(violations))

    projected, _ = _projection(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
    )
    raw_owner = admit_source_bound_exact_reentry(
        root=root,
        codemap=codemap,
        anchor_manifest=anchor_manifest,
        witness_manifest=witness_manifest,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        receipt=reentry_receipt,
    )
    stale_safe = admit_stale_safe_exact_reentry(
        source_observation_receipt=projected,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )

    return {
        "version": VERSION,
        "raw_source_owner_bound": True,
        "rejected_currentness_exact_reentry_only": True,
        "source_projection_receipt_identity": projected["receipt_identity"],
        "raw_owner_admission": raw_owner,
        "stale_safe_admission": stale_safe,
        "minimum_reentry_scope": stale_safe["minimum_reentry_scope"],
        "minimum_reentry_source_keys": stale_safe["minimum_reentry_source_keys"],
        "rejected_dependency_keys": stale_safe["rejected_dependency_keys"],
        "reentry_required": stale_safe["reentry_required"],
        "caller_source_observation_receipt_accepted": False,
        "caller_source_witnesses_accepted": False,
        "stale_observed_bytes_bound_to_source_generation": False,
        "current_source_evidence_admitted": False,
        "source_currentness_minted_by_exact_reproduction": False,
        "graph_witness_producer_authenticated": False,
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
