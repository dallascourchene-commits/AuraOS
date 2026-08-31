#!/usr/bin/env python3
"""Bind admitted historical benchmark evidence to owner-resolved proposal currentness.

D0 / HS1 / NONPROMOTING.

Historical benchmark admission, proposal currentness, and proposal-specific benchmark-use
relevance remain separate owner planes. This module computes only the relation between
them. Proposal invalidation or use-binding invalidation never rewrites historical score
identity; either event only removes current-use eligibility for the proposal-bound evidence
relation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Protocol

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
USE_BINDING_SCHEMA = "AURA-PROPOSAL-BOUND-BENCHMARK-USE-BINDING-v1"
SCORE_BEARING_STATES = frozenset({"PASS", "FAIL"})


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


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
class ProposalBenchmarkUseBinding:
    """Owner-resolved permission to use one historical score for one proposal basis.

    This is evidence-relevance/current-use policy only. It cannot authorize proposal
    execution, provider effects, or promotion.
    """

    schema_version: str
    binding_generation: str
    proposal_id: str
    proposal_basis_digest: str
    benchmark_score_identity: str
    benchmark_receipt_digest: str
    benchmark_policy_generation: str
    binding_current: bool
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if self.schema_version != USE_BINDING_SCHEMA:
            raise ValueError("BENCHMARK_USE_BINDING_SCHEMA_MISMATCH")
        for value, name in (
            (self.binding_generation, "BENCHMARK_USE_BINDING_GENERATION"),
            (self.proposal_id, "BENCHMARK_USE_PROPOSAL_ID"),
            (self.proposal_basis_digest, "BENCHMARK_USE_PROPOSAL_BASIS_DIGEST"),
            (self.benchmark_score_identity, "BENCHMARK_USE_SCORE_IDENTITY"),
            (self.benchmark_receipt_digest, "BENCHMARK_USE_RECEIPT_DIGEST"),
            (self.benchmark_policy_generation, "BENCHMARK_USE_POLICY_GENERATION"),
        ):
            _required(value, name)
        if type(self.binding_current) is not bool:
            raise ValueError("BENCHMARK_USE_BINDING_CURRENT_MUST_BE_BOOL")
        if any(
            value is not False
            for value in (
                self.execution_authorized,
                self.provider_effect_authorized,
                self.gate10_promoted,
            )
        ):
            raise ValueError("BENCHMARK_USE_BINDING_CANNOT_CARRY_EFFECT_AUTHORITY")

    @property
    def binding_digest(self) -> str:
        self.validate()
        return _sha({"domain": USE_BINDING_SCHEMA, "binding": asdict(self)})


class BenchmarkUseBindingResolver(Protocol):
    """Trusted current-use relation owner; implemented alongside proposal owners."""

    def resolve_benchmark_use_binding(
        self, *, proposal_id: str, benchmark_score_identity: str
    ) -> ProposalBenchmarkUseBinding | None: ...


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
    benchmark_use_binding_generation: str | None
    benchmark_use_binding_digest: str | None
    benchmark_use_binding_current: bool
    benchmark_use_binding_matches: bool
    benchmark_use_binding_reason: str
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
        if self.benchmark_use_binding_matches is True:
            if self.benchmark_use_binding_current is not True:
                raise ValueError("MATCHED_BENCHMARK_USE_BINDING_MUST_BE_CURRENT")
            if not self.benchmark_use_binding_generation or not self.benchmark_use_binding_digest:
                raise ValueError("MATCHED_BENCHMARK_USE_BINDING_IDENTITY_REQUIRED")
        if self.current_use_admissible is True:
            if self.proposal_currentness_state != "CURRENT_NONEXECUTABLE":
                raise ValueError("CURRENT_USE_REQUIRES_CURRENT_NONEXECUTABLE_PROPOSAL")
            if self.benchmark_use_binding_matches is not True:
                raise ValueError("CURRENT_USE_REQUIRES_TRUSTED_BENCHMARK_USE_BINDING")
            if self.benchmark_use_binding_current is not True:
                raise ValueError("CURRENT_USE_REQUIRES_CURRENT_BENCHMARK_USE_BINDING")
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
            "benchmark_use_binding_generation": self.benchmark_use_binding_generation,
            "benchmark_use_binding_digest": self.benchmark_use_binding_digest,
            "benchmark_use_binding_current": self.benchmark_use_binding_current,
            "benchmark_use_binding_matches": self.benchmark_use_binding_matches,
            "benchmark_use_binding_reason": self.benchmark_use_binding_reason,
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


def _resolve_use_binding(
    *,
    proposal_owner_resolver: ProposalOwnerResolver | None,
    proposal_capsule: ProposalCapsule,
    benchmark_receipt: BenchmarkTaskReceipt,
    benchmark_policy: BenchmarkAdmissionPolicy,
) -> tuple[ProposalBenchmarkUseBinding | None, bool, str]:
    if proposal_owner_resolver is None:
        return None, False, "BENCHMARK_USE_BINDING_OWNER_UNAVAILABLE"
    resolver = getattr(proposal_owner_resolver, "resolve_benchmark_use_binding", None)
    if resolver is None or not callable(resolver):
        return None, False, "BENCHMARK_USE_BINDING_RESOLVER_UNAVAILABLE"
    try:
        binding = resolver(
            proposal_id=proposal_capsule.proposal_id,
            benchmark_score_identity=benchmark_receipt.score_identity,
        )
    except Exception:
        return None, False, "BENCHMARK_USE_BINDING_RESOLVER_ERROR"
    if binding is None:
        return None, False, "BENCHMARK_USE_BINDING_UNAVAILABLE_OR_UNKNOWN"
    try:
        binding.validate()
    except ValueError:
        return None, False, "BENCHMARK_USE_BINDING_INVALID"
    if not binding.binding_current:
        return binding, False, "BENCHMARK_USE_BINDING_NOT_CURRENT"
    exact = (
        binding.proposal_id == proposal_capsule.proposal_id
        and binding.proposal_basis_digest == proposal_capsule.proposal_basis_digest
        and binding.benchmark_score_identity == benchmark_receipt.score_identity
        and binding.benchmark_receipt_digest == benchmark_receipt.receipt_digest
        and binding.benchmark_policy_generation == benchmark_policy.policy_generation
    )
    if not exact:
        return binding, False, "BENCHMARK_USE_BINDING_OPERAND_MISMATCH"
    return binding, True, "EXACT_OWNER_RESOLVED_BENCHMARK_USE_BINDING"


def evaluate_proposal_bound_benchmark_currentness(
    *,
    benchmark_receipt: BenchmarkTaskReceipt,
    benchmark_policy: BenchmarkAdmissionPolicy,
    proposal_capsule: ProposalCapsule,
    proposal_owner_resolver: ProposalOwnerResolver | None,
    retrieval_k27_coordinate: tuple[int, int, int] | None = None,
) -> ProposalBoundBenchmarkCurrentness:
    """Join three owner decisions without mutating any owner plane.

    The benchmark owner first admits the historical score. The proposal owner then
    re-resolves currentness. A third owner-resolved binding must explicitly authorize
    this exact historical score/receipt/policy generation as relevant current evidence
    for this exact proposal ID/basis. If proposal or use binding becomes invalid, the
    historical score remains admitted and identity-stable, but current use is denied.
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
    binding, binding_matches, binding_reason = _resolve_use_binding(
        proposal_owner_resolver=proposal_owner_resolver,
        proposal_capsule=proposal_capsule,
        benchmark_receipt=benchmark_receipt,
        benchmark_policy=benchmark_policy,
    )
    current_use_admissible = (
        proposal_decision.state == "CURRENT_NONEXECUTABLE" and binding_matches
    )

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
        "benchmark_use_binding_generation": binding.binding_generation if binding else None,
        "benchmark_use_binding_digest": binding.binding_digest if binding else None,
        "benchmark_use_binding_current": binding.binding_current if binding else False,
        "benchmark_use_binding_matches": binding_matches,
        "benchmark_use_binding_reason": binding_reason,
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
