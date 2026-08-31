from __future__ import annotations

from dataclasses import replace
import unittest

from tools.arena_portable_semantic_evidence_transfer import (
    native_expectation,
    q6_descriptor,
    r3_descriptor,
)
from tools.aura_execution_qualified_portable_semantic_evidence import (
    ADMIT,
    HOLD_FAILURE,
    HOLD_HEAD,
    HOLD_INSUFFICIENT,
    HOLD_JOB,
    HOLD_PROVIDER,
    HOLD_RUN,
    HOLD_WAIT,
    HOLD_WORKFLOW,
    classify_execution_qualified_transfer,
)


def exact_run(evidence, **overrides):
    run = {
        "id": evidence.producer_run,
        "name": evidence.workflow_name,
        "head_sha": evidence.producer_head,
        "status": "completed",
        "conclusion": "success",
    }
    run.update(overrides)
    return run


def exact_job(evidence, **overrides):
    job = {
        "id": evidence.producer_job,
        "status": "completed",
        "conclusion": "success",
    }
    job.update(overrides)
    return job


class ExecutionQualifiedPortableEvidenceTests(unittest.TestCase):
    def classify(self, *, run=None, jobs=None, evidence=None, consumer=None):
        evidence = evidence or q6_descriptor()
        consumer = consumer or native_expectation(evidence)
        return classify_execution_qualified_transfer(
            run=run or exact_run(evidence),
            jobs=exact_job(evidence) if jobs is None else jobs,
            evidence=evidence,
            consumer=consumer,
        )

    def test_exact_success_and_exact_portable_identity_admits(self):
        receipt = self.classify()
        self.assertTrue(receipt.execution_qualified_portable_evidence_admitted)
        self.assertEqual(receipt.disposition, ADMIT)
        self.assertTrue(receipt.exact_producer_job_success)
        self.assertTrue(receipt.portable_transfer_evaluated)
        self.assertTrue(receipt.portable_transfer_admitted)

    def test_provider_gate_stops_before_portable_transfer(self):
        evidence = q6_descriptor()
        receipt = self.classify(
            run=exact_run(evidence, conclusion="action_required"), jobs=[]
        )
        self.assertEqual(receipt.disposition, HOLD_PROVIDER)
        self.assertFalse(receipt.portable_transfer_evaluated)

    def test_queued_stops_before_portable_transfer(self):
        evidence = q6_descriptor()
        receipt = self.classify(
            run=exact_run(evidence, status="queued", conclusion=None), jobs=[]
        )
        self.assertEqual(receipt.disposition, HOLD_WAIT)
        self.assertFalse(receipt.portable_transfer_evaluated)

    def test_in_progress_stops_before_portable_transfer(self):
        evidence = q6_descriptor()
        receipt = self.classify(
            run=exact_run(evidence, status="in_progress", conclusion=None),
            jobs=[exact_job(evidence, status="in_progress", conclusion=None)],
        )
        self.assertEqual(receipt.disposition, HOLD_WAIT)
        self.assertFalse(receipt.portable_transfer_evaluated)

    def test_terminal_zero_job_is_insufficient(self):
        evidence = q6_descriptor()
        receipt = self.classify(
            run=exact_run(evidence, conclusion="cancelled"), jobs=[]
        )
        self.assertEqual(receipt.disposition, HOLD_INSUFFICIENT)
        self.assertFalse(receipt.portable_transfer_evaluated)

    def test_executed_failure_is_not_portable(self):
        evidence = q6_descriptor()
        receipt = self.classify(
            run=exact_run(evidence, conclusion="failure"),
            jobs=[exact_job(evidence, conclusion="failure")],
        )
        self.assertEqual(receipt.disposition, HOLD_FAILURE)
        self.assertFalse(receipt.portable_transfer_evaluated)

    def test_wrong_run_rejected(self):
        evidence = q6_descriptor()
        receipt = self.classify(run=exact_run(evidence, id=evidence.producer_run + 1))
        self.assertEqual(receipt.disposition, HOLD_RUN)

    def test_wrong_head_rejected(self):
        evidence = q6_descriptor()
        receipt = self.classify(run=exact_run(evidence, head_sha="0" * 40))
        self.assertEqual(receipt.disposition, HOLD_HEAD)

    def test_wrong_workflow_rejected(self):
        evidence = q6_descriptor()
        receipt = self.classify(run=exact_run(evidence, name="Impostor Workflow"))
        self.assertEqual(receipt.disposition, HOLD_WORKFLOW)

    def test_some_successful_job_cannot_impersonate_exact_producer_job(self):
        evidence = q6_descriptor()
        receipt = self.classify(
            jobs=[exact_job(evidence, id=evidence.producer_job + 1)]
        )
        self.assertEqual(receipt.disposition, HOLD_JOB)
        self.assertFalse(receipt.exact_producer_job_success)

    def test_duplicate_exact_job_identity_fails_closed(self):
        evidence = q6_descriptor()
        job = exact_job(evidence)
        receipt = self.classify(jobs=[job, dict(job)])
        self.assertEqual(receipt.disposition, HOLD_JOB)

    def test_exact_execution_does_not_rescue_cross_domain_consumer(self):
        evidence = q6_descriptor()
        receipt = self.classify(
            evidence=evidence,
            consumer=native_expectation(r3_descriptor()),
        )
        self.assertFalse(receipt.execution_qualified_portable_evidence_admitted)
        self.assertTrue(receipt.portable_transfer_evaluated)
        self.assertIn("HOLD_", receipt.disposition)
        self.assertIn("SUBJECT_IDENTITY_MISMATCH", receipt.disposition)

    def test_exact_execution_does_not_rescue_consequence_digest_substitution(self):
        evidence = q6_descriptor()
        consumer = replace(native_expectation(evidence), consequence_digest="0" * 64)
        receipt = self.classify(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.execution_qualified_portable_evidence_admitted)
        self.assertIn("CONSEQUENCE_IDENTITY_MISMATCH", receipt.disposition)

    def test_exact_execution_does_not_rescue_consumer_substitution(self):
        evidence = q6_descriptor()
        consumer = replace(native_expectation(evidence), consumer_class="other.consumer.v1")
        receipt = self.classify(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.execution_qualified_portable_evidence_admitted)
        self.assertIn("CONSUMER_IDENTITY_MISMATCH", receipt.disposition)

    def test_nonpromotion_ceiling_is_fixed(self):
        receipt = self.classify()
        for key in (
            "producer_authenticated",
            "semantic_truth_proven",
            "broader_claims_inherited",
            "effect_authority_granted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(getattr(receipt, key), key)

    def test_receipt_is_deterministic(self):
        first = self.classify()
        second = self.classify()
        self.assertEqual(first.receipt_digest, second.receipt_digest)


if __name__ == "__main__":
    unittest.main()
