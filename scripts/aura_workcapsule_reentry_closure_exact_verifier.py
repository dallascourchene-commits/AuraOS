#!/usr/bin/env python3
"""Exact-input verification for selective WorkCapsule re-entry closure receipts.

O10 proves whether a selective re-entry is CLOSED or HOLD and protects that
receipt with a public self-digest. O9 separately proves that self-digest
consistency is not exact evidence-input reproduction. This D0 membrane applies
that already-earned distinction to the closure consequence itself.

It recompiles O10 from the exact previous binding, exact O8 re-entry receipt,
and exact independently admitted candidate binding, then requires canonical
byte equality with the candidate closure receipt. It mints no semantic, review,
mutation, execution, commit, merge, promotion, provider, public, or human
authority.
"""
from __future__ import annotations

import json
from typing import Any

from scripts.aura_workcapsule_reentry_closure import (
    compile_reentry_closure,
    verify_reentry_closure,
)

VERSION = "AURA_WORKCAPSULE_REENTRY_CLOSURE_EXACT_VERIFIER_V1"
EXACT_CLOSURE_INPUT_MISMATCH = "CLOSURE_RECEIPT_NOT_EXACT_INPUT_REPRODUCTION"
PREVIOUS_BINDING_IDENTITY_MISMATCH = "CLOSURE_PREVIOUS_BINDING_IDENTITY_NOT_EXACT"
REENTRY_RECEIPT_IDENTITY_MISMATCH = "CLOSURE_REENTRY_RECEIPT_IDENTITY_NOT_EXACT"
CANDIDATE_BINDING_IDENTITY_MISMATCH = "CLOSURE_CANDIDATE_BINDING_IDENTITY_NOT_EXACT"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def verify_exact_reentry_closure(
    *,
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    candidate_binding: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> list[str]:
    """Return violations for an O10 receipt against the exact closure inputs."""
    violations = [f"O10_{item}" for item in verify_reentry_closure(closure_receipt)]

    expected = compile_reentry_closure(
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_binding=candidate_binding,
    )

    if closure_receipt.get("previous_binding_identity") != previous_binding.get("binding_identity"):
        violations.append(PREVIOUS_BINDING_IDENTITY_MISMATCH)
    if closure_receipt.get("reentry_receipt_identity") != reentry_receipt.get("receipt_identity"):
        violations.append(REENTRY_RECEIPT_IDENTITY_MISMATCH)
    if closure_receipt.get("candidate_binding_identity") != candidate_binding.get("binding_identity"):
        violations.append(CANDIDATE_BINDING_IDENTITY_MISMATCH)
    if _canonical_bytes(closure_receipt) != _canonical_bytes(expected):
        violations.append(EXACT_CLOSURE_INPUT_MISMATCH)

    return list(dict.fromkeys(violations))


def admit_exact_reentry_closure(
    *,
    previous_binding: dict[str, Any],
    reentry_receipt: dict[str, Any],
    candidate_binding: dict[str, Any],
    closure_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Return a narrow exact-reproduction witness or fail closed."""
    violations = verify_exact_reentry_closure(
        previous_binding=previous_binding,
        reentry_receipt=reentry_receipt,
        candidate_binding=candidate_binding,
        closure_receipt=closure_receipt,
    )
    if violations:
        raise ValueError("re-entry closure exact-input verification failed: " + ",".join(violations))

    return {
        "version": VERSION,
        "exact_closure_input_reproduction": True,
        "closure_status": closure_receipt["closure_status"],
        "minimum_reentry_scope": closure_receipt["minimum_reentry_scope"],
        "previous_binding_identity": closure_receipt["previous_binding_identity"],
        "reentry_receipt_identity": closure_receipt["reentry_receipt_identity"],
        "candidate_binding_identity": closure_receipt["candidate_binding_identity"],
        "o10_closure_receipt_identity": closure_receipt["receipt_identity"],
        "producer_identity_authenticated": False,
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
