#!/usr/bin/env python3
"""Bind admitted historical benchmark evidence to owner-resolved proposal currentness.

D0 / HS1 / NONPROMOTING.

Historical benchmark admission and proposal currentness remain separate owner planes.
This module computes only the relation between them. Proposal invalidation never
rewrites historical score identity; it only removes current-use eligibility for the
proposal-bound evidence relation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.aura_bounded_proposal_capsule import (
    ProposalCapsule,
    ProposalOwnerResolver,
    revalidate_proposal_capsule,
)
from tools.benchmarks.aura_benchmark_score_admission import (
    BenchmarkAdmissionPolicy,
    BenchmarkTaskReceipt,
    admit_score,
)

SCHEMA_ID = "AURA-PROPOSAL-BOUND-BENCHMARK-CURRENTNESS-v1"
SCORE_BEARING_STATES = frozenset({"PASS", "FAIL"})


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_k27(coordinate: tuple[int, int, int] | None) -> None:
    if coordinate is None:
        return
    if (
        not isinstance(coordinate, tuple)
        or len(coordinate) != 3
        or any(type(v) is not int or v < 0 or v > 26 for v in coordinate)
    ):
        raise ValueError("K27_RETRIEVAL_COORDINATE_MUST_BE_THREE_TRITS_MOD27")


@dataclass(frozen=True)
class ProposalBoundBenchmarkCurrentness:
    schema_version: str
    relation_digest: str
    benchmark_score_identity: str
    benchmark_receipt_digest: str
    benchmark_policy_generation: str
    historical_result_state: str
    historical_score_admitted: bool
    proposal_id: str
    proposal_basis_digest: str
    proposal_currentness_state: str
    proposal_currentness_reason: str
    current_use_admissible: bool
    score_credit_delta: int = 0
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    owner_host_execution_observed: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_human_effect: bool = False
    retrieval_k27_coordinate: tuple[int, int, int] | None = None

    def validate(self) -> None:
        if self.schema_version != SCHEMA_ID:
            raise ValueError("PROPOSAL_BOUND_BENCHMARK_SCHEMA_MISMATCH")
        if self.historical_result_state not in SCORE_BEARING_STATES:
            raise ValueError("HISTORICAL_RESULT_NOT_SCORE_BEARING")
        if self.historical_score_admitted is not True:
            raise ValueError("HISTORICAL_SCORE_MUST_BE_OWNER_ADMITTED")
        if self.score_credit_delta != 0:
            raise ValueError("CURRENTNESS_RELATION_CANNOT_ADD_SCORE_CREDIT")
        forbidden = (
            self.execution_authorized,
            self.provider_effect_authorized,
            self.owner_host_execution_observed,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("CURRENTNESS_RELATION_CANNOT_CARRY_EFFECT_AUTHORITY")
        _validate_k27(self.retrieval_k27_coordinate)
        if self.current_use_admissible is True and self.proposal_currentness_state != "CURRENT_NONEXECUTABLE":
            raise ValueError("CURRENT_USE_REQUIRES_CURRENT_NONEXECUTABLE_PROPOSAL")
        expected = _sha(self.semantic_payload)
        if self.relation_digest != expected:
            raise ValueError("CURRENTNESS_RELATION_DIGEST_MISMATCH")

    @property
    def semantic_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "benchmark_score_identity": self.benchmark_score_identity,
            "benchmark_receipt_digest": self.benchmark_receipt_digest,
            "benchmark_policy_generation": self.benchmark_policy_generation,
            "historical_result_state": self.historical_result_state,
            "historical_score_admitted": self.historical_score_admitted,
            "proposal_id": self.proposal_id,
            "proposal_basis_digest": self.proposal_basis_digest,
            "proposal_currentness_state": self.proposal_currentness_state,
            "proposal_currentness_reason": self.proposal_currentness_reason,
            "current_use_admissible": self.current_use_admissible,
            "score_credit_delta": self.score_credit_delta,
            "execution_authorized": self.execution_authorized,
            "provider_effect_authorized": self.provider_effect_authorized,
            "owner_host_execution_observed": self.owner_host_execution_observed,
            "semantic_k27_authority": self.semantic_k27_authority,
            "native_private_transformer_kv_accessed": self.native_private_transformer_kv_accessed,
            "gate10_promoted": self.gate10_promoted,
            "merge_deploy_spend_public_human_effect": self.merge_deploy_spend_public_human_effect,
        }

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


def evaluate_proposal_bound_benchmark_currentness(
    *,
    benchmark_receipt: BenchmarkTaskReceipt,
    benchmark_policy: BenchmarkAdmissionPolicy,
    proposal_capsule: ProposalCapsule,
    proposal_owner_resolver: ProposalOwnerResolver | None,
    retrieval_k27_coordinate: tuple[int, int, int] | None = None,
) -> ProposalBoundBenchmarkCurrentness:
    """Join two owner decisions without mutating either owner plane.

    The benchmark owner first admits the historical score. The proposal owner then
    re-resolves currentness. If the proposal is invalidated, the historical score
    remains admitted and identity-stable, but this proposal-bound current-use
    relation becomes inadmissible.
    """
    _validate_k27(retrieval_k27_coordinate)
    if benchmark_receipt.result_state not in SCORE_BEARING_STATES:
        raise ValueError("BENCHMARK_RESULT_NOT_SCORE_BEARING")

    score_summary = admit_score([benchmark_receipt], policy=benchmark_policy)
    if score_summary["unique_task_count"] != 1:
        raise ValueError("EXPECTED_EXACTLY_ONE_ADMITTED_BENCHMARK_SCORE")
    if benchmark_receipt.receipt_digest not in score_summary["admitted_receipt_digests"]:
        raise ValueError("BENCHMARK_RECEIPT_NOT_ADMITTED")

    proposal_decision = revalidate_proposal_capsule(
        capsule=proposal_capsule,
        owner_resolver=proposal_owner_resolver,
    )
    current_use_admissible = proposal_decision.state == "CURRENT_NONEXECUTABLE"

    payload = {
        "schema_version": SCHEMA_ID,
        "benchmark_score_identity": benchmark_receipt.score_identity,
        "benchmark_receipt_digest": benchmark_receipt.receipt_digest,
        "benchmark_policy_generation": benchmark_policy.policy_generation,
        "historical_result_state": benchmark_receipt.result_state,
        "historical_score_admitted": True,
        "proposal_id": proposal_capsule.proposal_id,
        "proposal_basis_digest": proposal_capsule.proposal_basis_digest,
        "proposal_currentness_state": proposal_decision.state,
        "proposal_currentness_reason": proposal_decision.reason_code,
        "current_use_admissible": current_use_admissible,
        "score_credit_delta": 0,
        "execution_authorized": False,
        "provider_effect_authorized": False,
        "owner_host_execution_observed": False,
        "semantic_k27_authority": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
        "merge_deploy_spend_public_human_effect": False,
    }
    relation = ProposalBoundBenchmarkCurrentness(
        **payload,
        relation_digest=_sha(payload),
        retrieval_k27_coordinate=retrieval_k27_coordinate,
    )
    relation.validate()
    return relation
