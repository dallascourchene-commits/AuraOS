#!/usr/bin/env python3
"""Integrity/adequacy checks for Aura provider and physical-swarm receipts.

Transport success is not objective success. These checks are intentionally conservative
and are designed to prevent refusal text, provider identity contradictions, or a single
self-triangulating response from being promoted as a valid physical swarm result.

The installed host remains the authority for provider endpoint authentication, request
IDs, durable idempotency, and effect receipts.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REFUSAL_MARKERS = (
    "i cannot execute",
    "i can't execute",
    "i cannot access",
    "i can't access",
    "i don't have access",
    "i do not have access",
    "i cannot perform",
    "i can't perform",
)
DEEPSEEK_IDENTITY_CONTRADICTIONS = (
    "i'm claude",
    "i am claude",
    "created by anthropic",
    "anthropic, not deepseek",
)
ROLE_SIMULATION_MARKERS = (
    "a+ construct",
    "b- challenge",
    "c0 verify",
    "three distinct identity roles",
)


class SwarmIntegrityError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def classify_model_output(
    record: Mapping[str, Any],
    *,
    expected_provider: str | None = None,
    physical_swarm_expected: bool = False,
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise SwarmIntegrityError("TERMINAL_RECORD_NOT_OBJECT")
    text = str(record.get("result") or record.get("response") or "")
    low = " ".join(text.casefold().split())
    provider = str(record.get("provider") or "").casefold()

    reasons: list[str] = []
    classification = "RESULT_UNVERIFIED"

    if not text.strip():
        reasons.append("EMPTY_MODEL_OUTPUT")
        classification = "RESULT_INVALID"

    if any(marker in low for marker in REFUSAL_MARKERS):
        reasons.append("MODEL_REFUSAL")
        classification = "MODEL_REFUSAL"

    expected = (expected_provider or provider).casefold()
    if expected == "deepseek" and any(
        marker in low for marker in DEEPSEEK_IDENTITY_CONTRADICTIONS
    ):
        reasons.append("PROVIDER_IDENTITY_MISMATCH")
        classification = "PROVIDER_IDENTITY_MISMATCH"

    role_hits = sum(marker in low for marker in ROLE_SIMULATION_MARKERS)
    if physical_swarm_expected and role_hits >= 3:
        reasons.append("ROLE_FANOUT_VIOLATION")
        if classification == "RESULT_UNVERIFIED":
            classification = "ROLE_FANOUT_VIOLATION"

    if not reasons:
        classification = "RESULT_NEEDS_OBJECTIVE_VERIFICATION"

    return {
        "classification": classification,
        "reasons": reasons,
        "provider_observed": provider or "UNKNOWN",
        "text_present": bool(text.strip()),
    }


def validate_physical_swarm_receipts(
    *,
    parent_command_id: str,
    target_size: int,
    child_receipts: Sequence[Mapping[str, Any]],
    expected_provider: str = "deepseek",
) -> dict[str, Any]:
    if isinstance(target_size, bool) or not isinstance(target_size, int) or target_size < 1:
        raise SwarmIntegrityError("INVALID_TARGET_SIZE")
    if len(child_receipts) != target_size:
        raise SwarmIntegrityError("PHYSICAL_CHILD_COUNT_MISMATCH")

    worker_ids: set[str] = set()
    role_ids: set[str] = set()
    attempt_ids: set[str] = set()
    provider_request_ids: set[str] = set()
    classifications: list[dict[str, Any]] = []

    for receipt in child_receipts:
        if not isinstance(receipt, Mapping):
            raise SwarmIntegrityError("INVALID_CHILD_RECEIPT")
        if receipt.get("parent_command_id") != parent_command_id:
            raise SwarmIntegrityError("PARENT_BINDING_MISMATCH")

        worker_id = str(receipt.get("worker_id") or "")
        role_id = str(receipt.get("role_id") or "")
        attempt_id = str(receipt.get("attempt_id") or "")
        request_id = str(receipt.get("provider_request_id") or "")

        if not worker_id or worker_id in worker_ids:
            raise SwarmIntegrityError("WORKER_ID_MISSING_OR_DUPLICATE")
        if not role_id or role_id in role_ids:
            raise SwarmIntegrityError("ROLE_ID_MISSING_OR_DUPLICATE")
        if not attempt_id or attempt_id in attempt_ids or attempt_id == "UNKNOWN":
            raise SwarmIntegrityError("ATTEMPT_ID_MISSING_UNKNOWN_OR_DUPLICATE")
        if not request_id or request_id in provider_request_ids:
            raise SwarmIntegrityError("PROVIDER_REQUEST_ID_MISSING_OR_DUPLICATE")

        worker_ids.add(worker_id)
        role_ids.add(role_id)
        attempt_ids.add(attempt_id)
        provider_request_ids.add(request_id)

        check = classify_model_output(
            receipt,
            expected_provider=expected_provider,
            physical_swarm_expected=False,
        )
        classifications.append(check)
        if check["classification"] in {
            "RESULT_INVALID",
            "MODEL_REFUSAL",
            "PROVIDER_IDENTITY_MISMATCH",
        }:
            raise SwarmIntegrityError(check["classification"])

    return {
        "schema": "AuraPhysicalSwarmIntegrityReceiptV1",
        "parent_command_id": parent_command_id,
        "target_size": target_size,
        "physical_child_count": len(child_receipts),
        "unique_worker_count": len(worker_ids),
        "unique_role_count": len(role_ids),
        "unique_attempt_count": len(attempt_ids),
        "unique_provider_request_count": len(provider_request_ids),
        "all_children_need_objective_verification": all(
            c["classification"] == "RESULT_NEEDS_OBJECTIVE_VERIFICATION"
            for c in classifications
        ),
        "physical_fanout_proven": True,
        "reduction_allowed": True,
    }
