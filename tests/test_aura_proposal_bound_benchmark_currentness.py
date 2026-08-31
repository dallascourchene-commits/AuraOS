from __future__ import annotations

from dataclasses import replace

import pytest

from tools.aura_bounded_proposal_capsule import (
    BASIS_SCHEMA,
    ELIGIBILITY_DISPOSITION,
    EligibilityReceiptRef,
    ProposalBasis,
    RequestOwnerState,
    ScientificEvidenceState,
    SourceAdmissionState,
    create_bounded_proposal_capsule,
)
from tools.aura_proposal_bound_benchmark_currentness import (
    evaluate_proposal_bound_benchmark_currentness,
)
from tools.benchmarks.aura_benchmark_score_admission import (
    BenchmarkAdmissionPolicy,
    BenchmarkTaskReceipt,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64
F = "f" * 64
G = "1" * 64
H = "2" * 64
I = "3" * 64


def eligibility(**changes):
    base = EligibilityReceiptRef(
        owner_ref="owner:generic-product-gate:v1",
        transition_id="transition:source:1",
        domain_id="generic.bounded.c2",
        gate_scope_digest=I,
        source_currentness_root="source-current:4",
        disposition=ELIGIBILITY_DISPOSITION,
        receipt_digest=A,
        receipt_generation="transition-gen-1",
        policy_generation_ref="eligibility-policy-gen-2",
        proposal_eligible=True,
        execution_authorized=False,
        provider_effect_authorized=False,
    )
    return replace(base, **changes)


def basis(**changes):
    base = ProposalBasis(
        schema_version=BASIS_SCHEMA,
        domain_id="generic.bounded.c2",
        action_kind="BOUNDED_C2_PROPOSAL",
        action_parameters_digest=B,
        scientific_scope_digest=C,
        scientific_evidence_generation="science-gen-8",
        scientific_evidence_receipt_digest=D,
        source_scope_digest=E,
        source_admission_generation="source-gen-4",
        source_admission_receipt_digest=F,
        request_id="request:c2:1",
        request_digest=G,
        resource_envelope_digest=H,
        eligibility=eligibility(),
        currentness_roots=("science-current:8", "source-current:4", "router-current:2"),
        invalidators=("science-generation-change", "source-generation-change", "request-envelope-change"),
        authority_scope="D0_NONPROMOTING",
    )
    return replace(base, **changes)


class OwnerResolver:
    def __init__(self, b: ProposalBasis, *, roots=None, invalidators=None):
        self.b = b
        self.roots = roots or {root: True for root in b.currentness_roots}
        self.invalidators = invalidators or {name: False for name in b.invalidators}

    def resolve_eligibility(self, *, owner_ref: str, transition_id: str):
        e = self.b.eligibility
        if e.owner_ref != owner_ref or e.transition_id != transition_id:
            return None
        return e

    def resolve_scientific_evidence(self, *, scope_digest: str):
        if scope_digest != self.b.scientific_scope_digest:
            return None
        return ScientificEvidenceState(
            scope_digest=self.b.scientific_scope_digest,
            generation=self.b.scientific_evidence_generation,
            receipt_digest=self.b.scientific_evidence_receipt_digest,
        )

    def resolve_source_admission(self, *, scope_digest: str):
        if scope_digest != self.b.source_scope_digest:
            return None
        return SourceAdmissionState(
            scope_digest=self.b.source_scope_digest,
            generation=self.b.source_admission_generation,
            receipt_digest=self.b.source_admission_receipt_digest,
        )

    def resolve_request(self, *, request_id: str):
        if request_id != self.b.request_id:
            return None
        return RequestOwnerState(
            request_id=self.b.request_id,
            request_digest=self.b.request_digest,
            action_parameters_digest=self.b.action_parameters_digest,
            resource_envelope_digest=self.b.resource_envelope_digest,
        )

    def currentness_root_is_current(self, *, root: str):
        return self.roots.get(root)

    def invalidator_is_triggered(self, *, invalidator: str):
        return self.invalidators.get(invalidator)


def capsule_and_resolver(*, b=None, roots=None, invalidators=None):
    b = b or basis()
    creator_resolver = OwnerResolver(b)
    capsule = create_bounded_proposal_capsule(
        basis=b,
        producer_identity="proposal-worker-a",
        owner_resolver=creator_resolver,
    ).capsule
    return capsule, OwnerResolver(b, roots=roots, invalidators=invalidators)


def benchmark_policy(**changes):
    base = BenchmarkAdmissionPolicy(
        policy_generation="benchmark-policy-gen-1",
        authority_scope="BENCHMARK_EVIDENCE_ONLY",
        expected_execution_route_fingerprint="route:harbor:host-observed",
        trusted_execution_observer_identity="BENCHMARK_HOST_OBSERVER",
        trusted_source_verifier_identity="UPSTREAM_SOURCE_VERIFIER",
        execution_authority_verified=True,
        source_verifier_authority_verified=True,
    )
    return replace(base, **changes)


def benchmark_receipt(**changes):
    base = BenchmarkTaskReceipt(
        campaign_id="arena-benchmark-20260831",
        suite_id="terminal-bench@2.0",
        suite_generation="upstream-pinned-generation",
        harness_id="harbor",
        harness_generation="pinned-harbor-generation",
        task_id="task-001",
        task_input_digest="4" * 64,
        agent_id="aura-adapter",
        agent_generation="5" * 40,
        model_id="provider/model",
        run_id="run-1",
        attempt_id="attempt-1",
        result_state="PASS",
        measurement_class="OBSERVED",
        wall_time_ms=100.0,
        source_verified=True,
        execution_observed=True,
        execution_route_fingerprint="route:harbor:host-observed",
        execution_observer_identity="BENCHMARK_HOST_OBSERVER",
        source_verifier_identity="UPSTREAM_SOURCE_VERIFIER",
    )
    return replace(base, **changes)


def evaluate(*, receipt=None, policy=None, capsule=None, resolver=None, coordinate=None):
    if capsule is None:
        capsule, default_resolver = capsule_and_resolver()
        resolver = default_resolver if resolver is None else resolver
    return evaluate_proposal_bound_benchmark_currentness(
        benchmark_receipt=receipt or benchmark_receipt(),
        benchmark_policy=policy or benchmark_policy(),
        proposal_capsule=capsule,
        proposal_owner_resolver=resolver,
        retrieval_k27_coordinate=coordinate,
    )


def test_current_proposal_plus_admitted_score_is_current_use_admissible():
    relation = evaluate()
    assert relation.historical_score_admitted is True
    assert relation.proposal_currentness_state == "CURRENT_NONEXECUTABLE"
    assert relation.current_use_admissible is True
    assert relation.score_credit_delta == 0


def test_proposal_invalidation_preserves_historical_score_identity_but_revokes_current_use():
    b = basis()
    roots = {root: True for root in b.currentness_roots}
    roots["source-current:4"] = False
    capsule, resolver = capsule_and_resolver(b=b, roots=roots)
    receipt = benchmark_receipt()
    relation = evaluate(receipt=receipt, capsule=capsule, resolver=resolver)
    assert relation.benchmark_score_identity == receipt.score_identity
    assert relation.historical_score_admitted is True
    assert relation.proposal_currentness_state == "INVALIDATED"
    assert relation.current_use_admissible is False


def test_missing_proposal_owner_resolver_fails_current_use_closed_without_rewriting_score():
    capsule, _ = capsule_and_resolver()
    receipt = benchmark_receipt()
    relation = evaluate(receipt=receipt, capsule=capsule, resolver=None)
    assert relation.historical_score_admitted is True
    assert relation.benchmark_score_identity == receipt.score_identity
    assert relation.current_use_admissible is False
    assert relation.proposal_currentness_reason == "OWNER_RESOLVER_UNAVAILABLE"


def test_triggered_proposal_invalidator_revokes_current_use_only():
    b = basis()
    invalidators = {name: False for name in b.invalidators}
    invalidators["request-envelope-change"] = True
    capsule, resolver = capsule_and_resolver(b=b, invalidators=invalidators)
    relation = evaluate(capsule=capsule, resolver=resolver)
    assert relation.historical_score_admitted is True
    assert relation.current_use_admissible is False


def test_untrusted_benchmark_authority_never_reaches_relation():
    with pytest.raises(ValueError, match="EXECUTION_AUTHORITY_NOT_VERIFIED"):
        evaluate(policy=benchmark_policy(execution_authority_verified=False))


def test_benchmark_source_verifier_substitution_never_reaches_relation():
    with pytest.raises(ValueError, match="SOURCE_VERIFIER_IDENTITY_MISMATCH"):
        evaluate(receipt=benchmark_receipt(source_verifier_identity="CALLER_MINTED"))


def test_policy_generation_recomputes_relation_without_rewriting_score_identity():
    receipt = benchmark_receipt()
    first = evaluate(receipt=receipt, policy=benchmark_policy(policy_generation="policy-gen-a"))
    second = evaluate(receipt=receipt, policy=benchmark_policy(policy_generation="policy-gen-b"))
    assert first.benchmark_score_identity == second.benchmark_score_identity == receipt.score_identity
    assert first.relation_digest != second.relation_digest


def test_tampered_proposal_id_is_rejected_by_owner_capsule_integrity():
    capsule, resolver = capsule_and_resolver()
    with pytest.raises(ValueError, match="PROPOSAL_CAPSULE_ID_INTEGRITY_MISMATCH"):
        evaluate(capsule=replace(capsule, proposal_id="9" * 64), resolver=resolver)


def test_tampered_proposal_basis_is_rejected_by_owner_capsule_integrity():
    capsule, resolver = capsule_and_resolver()
    tampered = replace(capsule, basis=basis(source_admission_generation="tampered"))
    with pytest.raises(ValueError, match="PROPOSAL_CAPSULE_BASIS_INTEGRITY_MISMATCH"):
        evaluate(capsule=tampered, resolver=resolver)


def test_k27_coordinate_is_retrieval_metadata_not_semantic_currentness():
    first = evaluate(coordinate=(1, 2, 3))
    second = evaluate(coordinate=(26, 25, 24))
    assert first.relation_digest == second.relation_digest
    assert first.current_use_admissible == second.current_use_admissible
    assert first.retrieval_k27_coordinate != second.retrieval_k27_coordinate


def test_invalid_k27_coordinate_fails_closed():
    with pytest.raises(ValueError, match="K27_RETRIEVAL_COORDINATE"):
        evaluate(coordinate=(27, 0, 0))


def test_relation_cannot_smuggle_effect_or_score_authority():
    relation = evaluate()
    for changed in (
        replace(relation, score_credit_delta=1),
        replace(relation, execution_authorized=True),
        replace(relation, provider_effect_authorized=True),
        replace(relation, semantic_k27_authority=True),
        replace(relation, native_private_transformer_kv_accessed=True),
        replace(relation, gate10_promoted=True),
    ):
        with pytest.raises(ValueError):
            changed.validate()


def test_non_score_bearing_historical_result_is_rejected():
    with pytest.raises(ValueError, match="BENCHMARK_RESULT_NOT_SCORE_BEARING"):
        evaluate(
            receipt=benchmark_receipt(
                result_state="UNKNOWN",
                measurement_class="UNKNOWN",
                wall_time_ms=None,
                source_verified=False,
                execution_observed=False,
                execution_route_fingerprint=None,
                execution_observer_identity=None,
                source_verifier_identity=None,
            )
        )


def test_relation_is_deterministic_for_same_owner_resolved_state():
    first = evaluate()
    second = evaluate()
    assert first.relation_digest == second.relation_digest
    assert first.to_dict() == second.to_dict()
