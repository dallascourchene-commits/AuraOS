#!/usr/bin/env python3
from dataclasses import replace
import unittest

from tools.arena_portable_semantic_evidence_transfer import (
    Q6_RUN,
    R3_RUN,
    R3_STALE_PR_PROSE_RUN,
    classify_transfer,
    native_expectation,
    portable_current_receipt,
    q6_descriptor,
    r3_descriptor,
)


class PortableSemanticEvidenceTransferTests(unittest.TestCase):
    def test_q6_native_transfer_is_exact_but_nonpromoting(self):
        evidence = q6_descriptor()
        receipt = classify_transfer(
            evidence=evidence, consumer=native_expectation(evidence)
        )
        self.assertTrue(receipt.portable_semantic_evidence_admitted)
        self.assertEqual(
            receipt.disposition, "ADMIT_EXACT_PORTABLE_SEMANTIC_EVIDENCE"
        )
        self.assertFalse(receipt.producer_authenticated)
        self.assertFalse(receipt.semantic_truth_proven)
        self.assertFalse(receipt.broader_claims_inherited)
        self.assertFalse(receipt.effect_authority_granted)
        self.assertFalse(receipt.semantic_k27_authority_minted)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)
        self.assertFalse(receipt.gate10_promoted)

    def test_r3_native_transfer_uses_provider_observed_run(self):
        evidence = r3_descriptor()
        self.assertEqual(evidence.producer_run, R3_RUN)
        self.assertNotEqual(evidence.producer_run, R3_STALE_PR_PROSE_RUN)
        receipt = classify_transfer(
            evidence=evidence, consumer=native_expectation(evidence)
        )
        self.assertTrue(receipt.portable_semantic_evidence_admitted)

    def test_cross_domain_green_artifacts_do_not_transfer_semantics(self):
        receipt = classify_transfer(
            evidence=q6_descriptor(), consumer=native_expectation(r3_descriptor())
        )
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertIn("SUBJECT_IDENTITY_MISMATCH", receipt.disposition)
        self.assertIn("CONSEQUENCE_SCOPE_MISMATCH", receipt.disposition)
        self.assertIn("CONSUMER_IDENTITY_MISMATCH", receipt.disposition)

    def test_head_drift_reopens_generation_cone(self):
        evidence = q6_descriptor()
        consumer = replace(native_expectation(evidence), producer_head="0" * 40)
        receipt = classify_transfer(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertIn("PRODUCER_GENERATION_MISMATCH", receipt.disposition)

    def test_run_drift_reopens_generation_cone(self):
        evidence = q6_descriptor()
        consumer = replace(native_expectation(evidence), producer_run=Q6_RUN + 1)
        receipt = classify_transfer(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertIn("PRODUCER_GENERATION_MISMATCH", receipt.disposition)

    def test_job_substitution_is_independent_failure(self):
        evidence = r3_descriptor()
        consumer = replace(
            native_expectation(evidence), producer_job=evidence.producer_job + 1
        )
        receipt = classify_transfer(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertIn("PRODUCER_JOB_MISMATCH", receipt.disposition)

    def test_scope_substitution_fails_closed(self):
        evidence = q6_descriptor()
        consumer = replace(
            native_expectation(evidence), consequence_scope="GLM53_TENSOR_QUALITY"
        )
        receipt = classify_transfer(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertIn("CONSEQUENCE_SCOPE_MISMATCH", receipt.disposition)

    def test_consequence_digest_substitution_fails_closed(self):
        evidence = q6_descriptor()
        consumer = replace(
            native_expectation(evidence), consequence_digest="0" * 64
        )
        receipt = classify_transfer(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertIn("CONSEQUENCE_IDENTITY_MISMATCH", receipt.disposition)

    def test_consumer_substitution_fails_closed(self):
        evidence = r3_descriptor()
        consumer = replace(
            native_expectation(evidence),
            consumer_class="hardware.performance.consumer.v1",
        )
        receipt = classify_transfer(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertIn("CONSUMER_IDENTITY_MISMATCH", receipt.disposition)

    def test_stale_pr_prose_run_cannot_impersonate_provider_run(self):
        evidence = r3_descriptor()
        consumer = replace(
            native_expectation(evidence), producer_run=R3_STALE_PR_PROSE_RUN
        )
        receipt = classify_transfer(evidence=evidence, consumer=consumer)
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertIn("PRODUCER_GENERATION_MISMATCH", receipt.disposition)

    def test_current_receipt_contains_native_admits_and_cross_domain_hold(self):
        receipt = portable_current_receipt()
        self.assertTrue(receipt["q6_native"]["portable_semantic_evidence_admitted"])
        self.assertTrue(receipt["r3_native"]["portable_semantic_evidence_admitted"])
        self.assertFalse(
            receipt["q6_to_r3_cross_domain"]["portable_semantic_evidence_admitted"]
        )
        self.assertTrue(receipt["stale_pr_prose_run_rejected"])

    def test_invalid_subject_digest_fails_closed(self):
        evidence = replace(q6_descriptor(), subject_digest="xyz")
        with self.assertRaises(ValueError):
            classify_transfer(
                evidence=evidence, consumer=native_expectation(q6_descriptor())
            )


if __name__ == "__main__":
    unittest.main()
