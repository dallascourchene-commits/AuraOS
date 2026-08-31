#!/usr/bin/env python3
"""Exact-input verification for WorkCapsule selective re-entry receipts.

O8 proves a deterministic dependency-class re-entry decision and gives the
receipt a self-digest.  A self-digest detects accidental drift only while a
trusted copy of that digest is already pinned; by itself it does not prove that
an arbitrary receipt is the exact result of the pinned previous WorkCapsule
binding plus the fresh graph/source witnesses.

This D0 membrane closes only that reproduction seam.  It recompiles O8 from the
exact inputs and requires canonical byte equality with the candidate receipt.
It grants no semantic, review, mutation, execution, commit, merge, promotion,
provider, public, or human authority.
"""
from __future__ import annotations

import json
from typing import Any

from scripts.aura_workcapsule_reentry_invalidation import (
    compile_reentry_invalidation,
    verify_reentry_invalidation,
)

VERSION = "AURA_WORKCAPSULE_REENTRY_EXACT_VERIFIER_V1"
EXACT_INPUT_MISMATCH = "REENTRY_RECEIPT_NOT_EXACT_INPUT_REPRODUCTION"
PREVIOUS_IDENTITY_MISMATCH = "PREVIOUS_BINDING_IDENTITY_NOT_EXACT"
OBSERVED_IDENTITY_MISMATCH = "OBSERVED_BINDING_IDENTITY_NOT_EXACT"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def verify_exact_reentry_receipt(
    *,
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    observed_source_witnesses: list[dict[str, Any]],
    receipt: dict[str, Any],
) -> list[str]:
    """Return violations for an O8 receipt against the exact evidence inputs.

    This verifier deliberately does not trust the candidate receipt to describe
    the evidence that produced it.  It runs the canonical O8 constructor on the
    supplied previous binding and fresh witnesses, then compares the complete
    canonical payload (including O8 receipt identity) byte-for-byte.
    """
    violations = [f"O8_{item}" for item in verify_reentry_invalidation(receipt)]

    expected = compile_reentry_invalidation(
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        observed_source_witnesses=observed_source_witnesses,
    )

    if receipt.get("previous_binding_identity") != previous_binding.get("binding_identity"):
        violations.append(PREVIOUS_IDENTITY_MISMATCH)
    if receipt.get("observed_binding_identity") != expected.get("observed_binding_identity"):
        violations.append(OBSERVED_IDENTITY_MISMATCH)
    if _canonical_bytes(receipt) != _canonical_bytes(expected):
        violations.append(EXACT_INPUT_MISMATCH)

    # Deterministic order with no duplicate diagnostic labels.
    return list(dict.fromkeys(violations))


def admit_exact_reentry_receipt(
    *,
    previous_binding: dict[str, Any],
    observed_graph_witness: dict[str, Any],
    observed_source_witnesses: list[dict[str, Any]],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Return a narrow exact-reproduction admission or fail closed."""
    violations = verify_exact_reentry_receipt(
        previous_binding=previous_binding,
        observed_graph_witness=observed_graph_witness,
        observed_source_witnesses=observed_source_witnesses,
        receipt=receipt,
    )
    if violations:
        raise ValueError("re-entry receipt exact-input verification failed: " + ",".join(violations))

    return {
        "version": VERSION,
        "exact_input_reproduction": True,
        "previous_binding_identity": receipt["previous_binding_identity"],
        "observed_binding_identity": receipt["observed_binding_identity"],
        "o8_receipt_identity": receipt["receipt_identity"],
        "minimum_reentry_scope": receipt["minimum_reentry_scope"],
        "minimum_reentry_source_keys": receipt["minimum_reentry_source_keys"],
        "authority": {
            "semantic_truth_minted": False,
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
