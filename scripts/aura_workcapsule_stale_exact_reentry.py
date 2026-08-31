#!/usr/bin/env python3
"""Fail-closed composition of rejected source currentness and exact WorkCapsule re-entry.

PR509 preserves expected source dependency identity across STALE observations while refusing to
bind the mismatching observed bytes to that generation. PR510 proves that an O8 re-entry receipt
is the exact deterministic result of its explicit evidence inputs. This membrane composes those
owners without promoting exact reproduction into source CURRENTness.
"""
from __future__ import annotations

from typing import Any

from scripts.aura_workcapsule_reentry_exact_verifier import (
    admit_exact_reentry_receipt,
    verify_exact_reentry_receipt,
)
from scripts.aura_workcapsule_reentry_invalidation import FULL_GRAPH, NONE, SELECTED_SOURCES
from scripts.aura_workcapsule_source_reentry_observation import verify_source_reentry_observations

VERSION = "AURA_WORKCAPSULE_STALE_EXACT_REENTRY_V1"
REJECTED_CURRENTNESS_REQUIRED = "REJECTED_CURRENTNESS_REQUIRED"
REJECTED_CURRENTNESS_REENTRY_NOT_REQUIRED = "REJECTED_CURRENTNESS_REENTRY_NOT_REQUIRED"
STALE_SOURCE_NOT_SELECTED_FOR_REENTRY = "STALE_SOURCE_NOT_SELECTED_FOR_REENTRY"
SOURCE_OBSERVATION_INVALID_PREFIX = "SOURCE_OBSERVATION_"
EXACT_REENTRY_INVALID_PREFIX = "EXACT_REENTRY_"


def _source_key(row: dict[str, Any]) -> tuple[int, str]:
    return int(row["file_id"]), str(row["relative_path"])


def _rejected_source_keys(source_observation_receipt: dict[str, Any]) -> set[tuple[int, str]]:
    keys: set[tuple[int, str]] = set()
    for observation in source_observation_receipt.get("source_observations", []):
        if observation.get("currentness") == "STALE":
            expected = observation.get("expected_source_identity")
            if isinstance(expected, dict):
                keys.add((int(expected["file_id"]), str(observation["relative_path"])))
    for unresolved in source_observation_receipt.get("unresolved_prior_sources", []):
        if unresolved.get("currentness") in {"STALE", "UNKNOWN"}:
            keys.add((int(unresolved["prior_file_id"]), str(unresolved["relative_path"])))
    return keys


def verify_stale_safe_exact_reentry(
    *,
    source_observation_receipt: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
) -> list[str]:
    """Verify exact O8 reproduction without laundering rejected source currentness."""
    violations = [
        SOURCE_OBSERVATION_INVALID_PREFIX + item
        for item in verify_source_reentry_observations(source_observation_receipt)
    ]

    observed_sources = source_observation_receipt.get("o7_source_witnesses")
    if not isinstance(observed_sources, list):
        observed_sources = []
        violations.append(SOURCE_OBSERVATION_INVALID_PREFIX + "MALFORMED_O7_SOURCE_WITNESSES")

    violations.extend(
        EXACT_REENTRY_INVALID_PREFIX + item
        for item in verify_exact_reentry_receipt(
            previous_binding=previous_binding,
            observed_graph_witness=observed_graph_witness,
            observed_source_witnesses=observed_sources,
            receipt=reentry_receipt,
        )
    )

    rejected_keys = _rejected_source_keys(source_observation_receipt)
    if not rejected_keys:
        violations.append(REJECTED_CURRENTNESS_REQUIRED)

    scope = reentry_receipt.get("minimum_reentry_scope")
    if rejected_keys and scope == NONE:
        violations.append(REJECTED_CURRENTNESS_REENTRY_NOT_REQUIRED)

    if rejected_keys and scope == SELECTED_SOURCES:
        selected_keys = {
            _source_key(row) for row in reentry_receipt.get("minimum_reentry_source_keys", [])
        }
        if not rejected_keys.issubset(selected_keys):
            violations.append(STALE_SOURCE_NOT_SELECTED_FOR_REENTRY)
    elif rejected_keys and scope not in {SELECTED_SOURCES, FULL_GRAPH}:
        violations.append(REJECTED_CURRENTNESS_REENTRY_NOT_REQUIRED)

    return list(dict.fromkeys(violations))


def admit_stale_safe_exact_reentry(
    *,
    source_observation_receipt: dict[str, Any],
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    reentry_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Admit only an exact, rejected-currentness-driven re-entry decision."""
    violations = verify_stale_safe_exact_reentry(
        source_observation_receipt=source_observation_receipt,
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        reentry_receipt=reentry_receipt,
    )
    if violations:
        raise ValueError("stale-safe exact re-entry verification failed: " + ",".join(violations))

    exact = admit_exact_reentry_receipt(
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        observed_source_witnesses=source_observation_receipt["o7_source_witnesses"],
        receipt=reentry_receipt,
    )
    rejected_keys = sorted(_rejected_source_keys(source_observation_receipt))
    stale_count = sum(
        1
        for row in source_observation_receipt.get("source_observations", [])
        if row.get("currentness") == "STALE"
    )
    unresolved_count = sum(
        1
        for row in source_observation_receipt.get("unresolved_prior_sources", [])
        if row.get("currentness") in {"STALE", "UNKNOWN"}
    )

    return {
        "version": VERSION,
        "exact_input_reproduction": exact["exact_input_reproduction"],
        "previous_binding_identity": exact["previous_binding_identity"],
        "observed_binding_identity": exact["observed_binding_identity"],
        "o8_receipt_identity": exact["o8_receipt_identity"],
        "minimum_reentry_scope": exact["minimum_reentry_scope"],
        "minimum_reentry_source_keys": exact["minimum_reentry_source_keys"],
        "rejected_dependency_keys": [
            {"file_id": file_id, "relative_path": path} for file_id, path in rejected_keys
        ],
        "stale_source_count": stale_count,
        "unresolved_source_count": unresolved_count,
        "reentry_required": exact["minimum_reentry_scope"] != NONE,
        "stale_observed_bytes_bound_to_source_generation": False,
        "current_source_evidence_admitted": False,
        "source_currentness_minted_by_exact_reproduction": False,
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
