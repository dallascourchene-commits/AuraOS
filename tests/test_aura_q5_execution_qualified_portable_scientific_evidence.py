from __future__ import annotations

from dataclasses import replace

from tools.quantization import aura_q5_execution_qualified_portable_scientific_evidence as q9


def test_exact_q5_is_execution_qualified_and_reusable_without_freshness_reset():
    r = q9.exact_q5_execution_fixture()
    assert r.execution_qualified_portable_semantic_evidence is True
    assert r.portable_evidence_reuse_allowed is True
    assert r.semantic_sibling_credit is False
    assert r.historical_exact_execution_reuse is True
    assert r.fresh_semantic_sibling_execution_qualified is False
    assert r.execution_qualification_resets_semantic_clock is False
    assert r.execution_qualification_grants_semantic_truth is False


def test_wrong_head_fails_execution_qualification():
    evidence = q9.q5_descriptor()
    r = q9.classify_q5(
        run={"id": q9.Q5_RUN, "name": q9.Q5_WORKFLOW, "head_sha": "f" * 40, "status": "completed", "conclusion": "success"},
        jobs=[{"id": q9.Q5_JOB, "status": "completed", "conclusion": "success"}],
    )
    assert r.execution_qualified_portable_semantic_evidence is False
    assert r.reason == "PRODUCER_RUN_OR_HEAD_MISMATCH"


def test_prejob_gate_cannot_qualify_scientific_evidence():
    r = q9.classify_q5(
        run={"id": q9.Q5_RUN, "name": q9.Q5_WORKFLOW, "head_sha": q9.Q5_HEAD, "status": "action_required", "conclusion": "action_required"},
        jobs=[],
    )
    assert r.execution_qualified_portable_semantic_evidence is False
    assert r.provider_gate_counts_as_execution_qualified_evidence is False


def test_failed_q5_job_cannot_qualify_scientific_support():
    r = q9.classify_q5(
        run={"id": q9.Q5_RUN, "name": q9.Q5_WORKFLOW, "head_sha": q9.Q5_HEAD, "status": "completed", "conclusion": "failure"},
        jobs=[{"id": q9.Q5_JOB, "status": "completed", "conclusion": "failure"}],
    )
    assert r.execution_qualified_portable_semantic_evidence is False
    assert r.executed_failure_counts_as_semantic_support is False


def test_exact_descriptor_preserves_scientific_scope_identity():
    e = q9.q5_descriptor()
    assert e.producer_head == q9.Q5_HEAD
    assert e.producer_run == q9.Q5_RUN
    assert e.producer_job == q9.Q5_JOB
    assert e.consequence_scope == q9.Q5_SCOPE
    assert e.native_consumer_class == q9.Q5_CONSUMER


def test_transfer_after_cut_does_not_reset_semantic_clock():
    r = q9.exact_q5_execution_fixture()
    assert r.semantic_sibling_credit is False
    assert r.execution_qualification_resets_semantic_clock is False


def test_claim_ceiling_remains_nonpromoting():
    r = q9.exact_q5_execution_fixture()
    assert r.execution_qualification_grants_semantic_truth is False
    assert r.producer_authenticated is False
    assert r.broader_claims_inherited is False
    assert r.effect_authority_granted is False
    assert r.semantic_k27_authority_minted is False
    assert r.native_private_transformer_kv_accessed is False
    assert r.gate10_promoted is False
    assert r.merge_or_deployment_authorized is False
