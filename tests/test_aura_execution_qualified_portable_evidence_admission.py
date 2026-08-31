from __future__ import annotations

from dataclasses import replace
import unittest

from tools import arena_portable_semantic_evidence_transfer as o61
from tools import aura_execution_qualified_portable_evidence_admission as a7
from tools import aura_fresh_portable_semantic_evidence_admission as fresh


def exact_run(evidence: o61.SemanticEvidenceDescriptor, *, status="completed", conclusion="success"):
    return {
        "id": evidence.producer_run,
        "name": evidence.workflow_name,
        "head_sha": evidence.producer_head,
        "status": status,
        "conclusion": conclusion,
    }


def exact_job(evidence: o61.SemanticEvidenceDescriptor, *, status="completed", conclusion="success"):
    return {"id": evidence.producer_job, "status": status, "conclusion": conclusion}


def classify(evidence=None, consumer=None, run=None, jobs=None, producer_time=None):
    evidence = evidence or o61.q6_descriptor()
    consumer = consumer or o61.native_expectation(evidence)
    run = run if run is not None else exact_run(evidence)
    jobs = jobs if jobs is not None else [exact_job(evidence)]
    return a7.classify_execution_qualified_portable_evidence(
        evidence=evidence,
        consumer=consumer,
        producer_semantic_generated_at=producer_time or fresh.Q6_SEMANTIC_GENERATED_AT,
        transfer_observed_at="2026-08-31T13:40:00Z",
        terminal_at="2026-08-31T13:40:01Z",
        cut=fresh.CURRENT_CUT,
        artifact_id="test:portable:q6",
        run=run,
        jobs=jobs,
    )


class ExecutionQualifiedPortableEvidenceAdmissionTests(unittest.TestCase):
    def test_historical_exact_green_is_reusable_and_execution_qualified_without_freshness(self):
        r = classify()
        self.assertTrue(r.portable_semantic_evidence_admitted)
        self.assertTrue(r.portable_evidence_reuse_allowed)
        self.assertEqual(r.freshness_disposition, "PRE_CUT_SEMANTIC_GENERATION")
        self.assertFalse(r.semantic_sibling_credit)
        self.assertEqual(r.execution_classification, "EXECUTED_JOB_SUCCESS_OBSERVED")
        self.assertTrue(r.run_identity_exact)
        self.assertTrue(r.workflow_identity_exact)
        self.assertTrue(r.exact_producer_job_present_once)
        self.assertTrue(r.exact_producer_job_completed_success)
        self.assertTrue(r.execution_qualified_portable_semantic_evidence)
        self.assertTrue(r.historical_exact_execution_reuse)
        self.assertFalse(r.fresh_semantic_sibling_execution_qualified)
        self.assertFalse(r.execution_qualification_resets_semantic_clock)

    def test_provider_gate_never_execution_qualifies_portable_semantic_evidence(self):
        e = o61.q6_descriptor()
        run = exact_run(e, conclusion="action_required")
        r = classify(evidence=e, run=run, jobs=[])
        self.assertEqual(r.execution_classification, "PRE_JOB_ACTION_REQUIRED")
        self.assertFalse(r.execution_qualified_portable_semantic_evidence)
        self.assertFalse(r.provider_gate_counts_as_execution_qualified_evidence)

    def test_wrong_head_fails_exact_run_identity(self):
        e = o61.q6_descriptor()
        run = exact_run(e)
        run["head_sha"] = "f" * 40
        r = classify(evidence=e, run=run)
        self.assertFalse(r.run_identity_exact)
        self.assertFalse(r.execution_qualified_portable_semantic_evidence)
        self.assertEqual(r.reason, "PRODUCER_RUN_OR_HEAD_MISMATCH")

    def test_wrong_workflow_fails_exact_workflow_identity(self):
        e = o61.q6_descriptor()
        run = exact_run(e)
        run["name"] = "Different Workflow"
        r = classify(evidence=e, run=run)
        self.assertFalse(r.workflow_identity_exact)
        self.assertFalse(r.execution_qualified_portable_semantic_evidence)
        self.assertEqual(r.reason, "PRODUCER_WORKFLOW_MISMATCH")

    def test_missing_exact_job_fails_even_when_run_label_is_success(self):
        e = o61.q6_descriptor()
        jobs = [{"id": e.producer_job + 1, "status": "completed", "conclusion": "success"}]
        r = classify(evidence=e, jobs=jobs)
        self.assertFalse(r.exact_producer_job_present_once)
        self.assertFalse(r.execution_qualified_portable_semantic_evidence)
        self.assertEqual(r.reason, "EXACT_PRODUCER_JOB_NOT_PRESENT_ONCE")

    def test_duplicate_exact_job_id_fails_closed(self):
        e = o61.q6_descriptor()
        jobs = [exact_job(e), exact_job(e)]
        r = classify(evidence=e, jobs=jobs)
        self.assertFalse(r.exact_producer_job_present_once)
        self.assertFalse(r.execution_qualified_portable_semantic_evidence)

    def test_executed_failure_is_execution_evidence_not_semantic_support(self):
        e = o61.q6_descriptor()
        r = classify(
            evidence=e,
            run=exact_run(e, conclusion="failure"),
            jobs=[exact_job(e, conclusion="failure")],
        )
        self.assertEqual(r.execution_classification, "EXECUTED_JOB_FAILURE_OBSERVED")
        self.assertFalse(r.exact_producer_job_completed_success)
        self.assertFalse(r.execution_qualified_portable_semantic_evidence)
        self.assertFalse(r.executed_failure_counts_as_semantic_support)

    def test_cross_domain_portable_transfer_cannot_be_rescued_by_execution_success(self):
        e = o61.q6_descriptor()
        consumer = o61.native_expectation(o61.r3_descriptor())
        r = classify(evidence=e, consumer=consumer)
        self.assertFalse(r.portable_semantic_evidence_admitted)
        self.assertFalse(r.portable_evidence_reuse_allowed)
        self.assertFalse(r.execution_qualified_portable_semantic_evidence)
        self.assertEqual(r.reason, "PORTABLE_TRANSFER_NOT_ADMITTED")

    def test_execution_success_does_not_mint_truth_authority_or_k27_semantics(self):
        r = classify()
        for key in (
            "execution_qualification_grants_semantic_truth",
            "producer_authenticated",
            "broader_claims_inherited",
            "effect_authority_granted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(getattr(r, key), key)

    def test_structurally_post_cut_generation_is_fresh_but_still_nonauthorizing(self):
        r = classify(producer_time="2026-08-31T13:20:00Z")
        self.assertTrue(r.semantic_sibling_credit)
        self.assertTrue(r.execution_qualified_portable_semantic_evidence)
        self.assertTrue(r.fresh_semantic_sibling_execution_qualified)
        self.assertFalse(r.historical_exact_execution_reuse)
        self.assertFalse(r.producer_authenticated)

    def test_receipt_is_deterministic(self):
        self.assertEqual(classify().receipt_digest, classify().receipt_digest)


if __name__ == "__main__":
    unittest.main()
