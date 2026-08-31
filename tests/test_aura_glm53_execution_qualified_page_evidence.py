from __future__ import annotations

from dataclasses import replace
import unittest

from tools.quantization import aura_glm53_execution_qualified_page_evidence as q15


def exact_inputs():
    d = q15.q14_descriptor()
    run = {
        "id": q15.Q14_RUN,
        "head_sha": q15.Q14_HEAD,
        "name": q15.Q14_WORKFLOW,
        "status": "completed",
        "conclusion": "success",
    }
    jobs = [{
        "id": q15.Q14_JOB,
        "name": q15.Q14_JOB_NAME,
        "status": "completed",
        "conclusion": "success",
    }]
    artifacts = [{
        "name": q15.Q14_ARTIFACT_NAME,
        "digest": q15.Q14_ARTIFACT_DIGEST,
        "expired": False,
    }]
    return d, run, jobs, artifacts


def classify(*, descriptor=None, run=None, jobs=None, artifacts=None):
    d, r, j, a = exact_inputs()
    return q15.classify_execution_qualified_page_evidence(
        descriptor=descriptor or d,
        run=run if run is not None else r,
        jobs=jobs if jobs is not None else j,
        artifacts=artifacts if artifacts is not None else a,
    )


class ExecutionQualifiedPageEvidenceTests(unittest.TestCase):
    def test_exact_q14_generation_is_execution_qualified(self):
        r = classify()
        self.assertTrue(r.q14_semantic_descriptor_exact)
        self.assertTrue(r.provider_run_identity_exact)
        self.assertTrue(r.provider_run_completed_success)
        self.assertTrue(r.exact_producer_job_present_once)
        self.assertTrue(r.exact_producer_job_completed_success)
        self.assertTrue(r.exact_producer_job_name)
        self.assertTrue(r.exact_receipt_artifact_present_once)
        self.assertTrue(r.exact_receipt_artifact_digest)
        self.assertTrue(r.receipt_artifact_unexpired)
        self.assertTrue(r.producer_execution_observed)
        self.assertTrue(r.execution_qualified_official_source_page_evidence)
        self.assertEqual(r.reason, "EXECUTION_QUALIFIED_OFFICIAL_SOURCE_PAGE_EVIDENCE")

    def test_later_branch_tip_cannot_impersonate_exact_green_generation(self):
        _, run, jobs, artifacts = exact_inputs()
        run["head_sha"] = "49cc2947c04c1914e343d816a53d2576917523c8"
        r = classify(run=run, jobs=jobs, artifacts=artifacts)
        self.assertFalse(r.provider_run_identity_exact)
        self.assertFalse(r.execution_qualified_official_source_page_evidence)
        self.assertFalse(r.later_branch_tip_may_replace_exact_generation)

    def test_green_run_label_without_exact_job_is_not_qualified(self):
        _, run, _, artifacts = exact_inputs()
        r = classify(run=run, jobs=[], artifacts=artifacts)
        self.assertFalse(r.exact_producer_job_present_once)
        self.assertFalse(r.producer_execution_observed)
        self.assertFalse(r.execution_qualified_official_source_page_evidence)

    def test_executed_failure_is_not_qualified(self):
        _, run, jobs, artifacts = exact_inputs()
        run["conclusion"] = "failure"
        jobs[0]["conclusion"] = "failure"
        r = classify(run=run, jobs=jobs, artifacts=artifacts)
        self.assertFalse(r.provider_run_completed_success)
        self.assertFalse(r.exact_producer_job_completed_success)
        self.assertFalse(r.execution_qualified_official_source_page_evidence)

    def test_pre_job_provider_gate_is_not_qualified(self):
        _, run, _, artifacts = exact_inputs()
        run["conclusion"] = "action_required"
        r = classify(run=run, jobs=[], artifacts=artifacts)
        self.assertFalse(r.provider_run_completed_success)
        self.assertFalse(r.producer_execution_observed)
        self.assertFalse(r.execution_qualified_official_source_page_evidence)

    def test_page_set_digest_substitution_fails_semantic_descriptor(self):
        d, run, jobs, artifacts = exact_inputs()
        d = replace(d, page_set_digest="f" * 64)
        r = classify(descriptor=d, run=run, jobs=jobs, artifacts=artifacts)
        self.assertFalse(r.q14_semantic_descriptor_exact)
        self.assertFalse(r.execution_qualified_official_source_page_evidence)
        self.assertEqual(r.reason, "Q14_SEMANTIC_DESCRIPTOR_MISMATCH")

    def test_receipt_artifact_digest_substitution_fails(self):
        _, run, jobs, artifacts = exact_inputs()
        artifacts[0]["digest"] = "sha256:" + "0" * 64
        r = classify(run=run, jobs=jobs, artifacts=artifacts)
        self.assertFalse(r.exact_receipt_artifact_digest)
        self.assertFalse(r.execution_qualified_official_source_page_evidence)

    def test_expired_receipt_artifact_fails(self):
        _, run, jobs, artifacts = exact_inputs()
        artifacts[0]["expired"] = True
        r = classify(run=run, jobs=jobs, artifacts=artifacts)
        self.assertFalse(r.receipt_artifact_unexpired)
        self.assertFalse(r.execution_qualified_official_source_page_evidence)

    def test_execution_qualification_preserves_nonpromotion_ceiling(self):
        r = classify()
        for key in (
            "execution_qualification_mints_page_semantics",
            "execution_qualification_mints_semantic_truth",
            "full_role_page_materialization_proven",
            "whole_model_quantization_proven",
            "model_execution_observed",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(getattr(r, key), key)

    def test_receipt_is_deterministic(self):
        self.assertEqual(classify().receipt_digest, classify().receipt_digest)


if __name__ == "__main__":
    unittest.main()
