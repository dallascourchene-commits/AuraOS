#!/usr/bin/env python3
"""Canonical Q22 public membrane with exact Q21 producer-lineage reconstruction.

The inner Q22 relation validates the parent receipt envelope and claim ceiling. This
public membrane additionally reconstructs Q21's typed receipt and independently
recomputes the exact Q21 lineage digest before any PR708 support can be associated.
Noncanonical extra fields are rejected rather than becoming accidental identity.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from tools import aura_materialization_support_lifecycle_lineage as q22
from tools import aura_pre_attempt_lifecycle_lineage as q21

SCHEMA = q22.SCHEMA


def _canonical_q21_receipt(lineage: Mapping[str, Any]) -> q21.PreAttemptLifecycleLineageReceipt:
    if not isinstance(lineage, Mapping):
        raise ValueError("Q22_LINEAGE_MAPPING_REQUIRED")
    body = dict(lineage)
    supplied_receipt_digest = body.pop("receipt_digest", None)
    try:
        typed = q21.PreAttemptLifecycleLineageReceipt(**body)
    except TypeError as exc:
        raise ValueError("Q22_LINEAGE_NONCANONICAL_FIELDS") from exc

    # Dataclass annotations do not enforce runtime types. Reconstructing an exact
    # producer receipt therefore has to enforce producer-side typed fields too;
    # otherwise a self-resealed mapping could carry e.g. "true" instead of True
    # while retaining a valid envelope digest and the same lineage identity.
    if type(typed.lifecycle_reusable_evidence_eligible) is not bool:
        raise ValueError("Q22_LINEAGE_REUSABLE_EVIDENCE_MUST_BE_BOOL")

    if supplied_receipt_digest != typed.receipt_digest:
        raise ValueError("Q22_LINEAGE_RECEIPT_DIGEST_MISMATCH")

    identity_payload = {
        "domain": q21.SCHEMA,
        "o65_parent": {"head": q21.O65_HEAD, "run": q21.O65_RUN},
        "lifecycle_parent": {"head": q21.LIFECYCLE_HEAD, "run": q21.LIFECYCLE_RUN},
        "proposal_id": typed.proposal_id,
        "proposal_basis_digest": typed.proposal_basis_digest,
        "pre_attempt_id": typed.pre_attempt_id,
        "owner_state_epoch": typed.owner_state_epoch,
        "pre_attempt_policy_generation": typed.pre_attempt_policy_generation,
        "pre_attempt_policy_digest": typed.pre_attempt_policy_digest,
        "expected_route_fingerprint": typed.expected_route_fingerprint,
        "expected_observer_identity": typed.expected_observer_identity,
        "concurrency_scope_digest": typed.concurrency_scope_digest,
        "lifecycle_model_objective_id": typed.lifecycle_model_objective_id,
        "lifecycle_model_attempt_id": typed.lifecycle_model_attempt_id,
        "lifecycle_model_output_digest": typed.lifecycle_model_output_digest,
        "lifecycle_source_generation": typed.lifecycle_source_generation,
        "lifecycle_authority_scope": typed.lifecycle_authority_scope,
        "lifecycle_terminal_state": typed.lifecycle_terminal_state,
        "lifecycle_semantic_commit_key": typed.lifecycle_semantic_commit_key,
    }
    expected_lineage_digest = q21._sha(identity_payload)
    if typed.lineage_digest != expected_lineage_digest:
        raise ValueError("Q22_LINEAGE_DIGEST_MISMATCH")
    return typed


def bind_materialization_support_to_exact_lineage(
    *, support: Any, lineage: Mapping[str, Any]
) -> q22.MaterializationSupportedLifecycleLineageReceipt:
    """Bind PR708 support only after exact Q21 producer-semantic reconstruction."""
    typed = _canonical_q21_receipt(lineage)
    canonical_lineage = typed.to_dict()
    return q22.bind_materialization_support_to_lineage(
        support=support,
        lineage=canonical_lineage,
    )


def example_lineage() -> dict[str, Any]:
    base = q22.example_lineage()
    body = dict(base)
    body.pop("receipt_digest", None)
    identity_payload = {
        "domain": q21.SCHEMA,
        "o65_parent": {"head": q21.O65_HEAD, "run": q21.O65_RUN},
        "lifecycle_parent": {"head": q21.LIFECYCLE_HEAD, "run": q21.LIFECYCLE_RUN},
        "proposal_id": body["proposal_id"],
        "proposal_basis_digest": body["proposal_basis_digest"],
        "pre_attempt_id": body["pre_attempt_id"],
        "owner_state_epoch": body["owner_state_epoch"],
        "pre_attempt_policy_generation": body["pre_attempt_policy_generation"],
        "pre_attempt_policy_digest": body["pre_attempt_policy_digest"],
        "expected_route_fingerprint": body["expected_route_fingerprint"],
        "expected_observer_identity": body["expected_observer_identity"],
        "concurrency_scope_digest": body["concurrency_scope_digest"],
        "lifecycle_model_objective_id": body["lifecycle_model_objective_id"],
        "lifecycle_model_attempt_id": body["lifecycle_model_attempt_id"],
        "lifecycle_model_output_digest": body["lifecycle_model_output_digest"],
        "lifecycle_source_generation": body["lifecycle_source_generation"],
        "lifecycle_authority_scope": body["lifecycle_authority_scope"],
        "lifecycle_terminal_state": body["lifecycle_terminal_state"],
        "lifecycle_semantic_commit_key": body["lifecycle_semantic_commit_key"],
    }
    body["lineage_digest"] = q21._sha(identity_payload)
    typed = q21.PreAttemptLifecycleLineageReceipt(**body)
    return typed.to_dict()


def main() -> None:
    receipt = bind_materialization_support_to_exact_lineage(
        support=q22.example_support(), lineage=example_lineage()
    )
    print(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
