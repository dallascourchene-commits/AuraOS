from __future__ import annotations

import unittest

from tools import aura_glm53_execution_qualified_official_canary_evidence as q15


def exact_observation():
    return {
        "receipt_digest": q15.Q5_RECEIPT_DIGEST,
        "official_repository": q15.OFFICIAL_REPOSITORY,
        "official_revision": q15.OFFICIAL_REVISION,
        "q13_head": q15.Q13_HEAD,
        "q13_run": q15.Q13_RUN,
        "q13_source_blob": q15.Q13_SOURCE_BLOB,
        "q13_source_tensor_set_digest": q15.Q13_SOURCE_SET_DIGEST,
        "q4_codec_blob": q15.Q4_CODEC_BLOB,
        "selected_layer": q15.SELECTED_LAYER,
        "selected_expert": q15.SELECTED_EXPERT,
        "selected_shard": q15.SELECTED_SHARD,
        "total_official_weights_observed": q15.TOTAL_WEIGHTS,
        "codec_bpw_e8": q15.RATE_BPW,
        "codec_bpw_control": q15.RATE_BPW,
        "equal_rate": True,
        "official_source_equal_rate_distortion_evidence": True,
        "representative_canary_scope_only": True,
        "geometry_privileged": False,
        "full_tensor_quantized": False,
        "whole_model_quantized": False,
        "glm_quality_proven": False,
        "runtime_performance_proven": False,
        "semantic_k27_authority": False,
        "gate10_promoted": False,
        "aggregate_outcome": q15.AGGREGATE_OUTCOME,
        "aggregate_e8_over_control": q15.AGGREGATE_E8_OVER_CONTROL,
    }


class ExecutionQualifiedOfficialCanaryEvidenceTests(unittest.TestCase):
    def classify(self, observation=None, run=None, jobs=None):
        exact_run, exact_jobs = q15.exact_execution_fixture()
        return q15.classify_official_canary_portable_evidence(
            q5_observation=observation if observation is not None else exact_observation(),
            run=run if run is not None else exact_run,
            jobs=jobs if jobs is not None else exact_jobs,
        )

    def test_exact_q5_result_is_execution_qualified_historical_reuse_only(self):
        r = self.classify()
        self.assertTrue(r.exact_q5_receipt_identity)
        self.assertTrue(r.exact_q5_source_identity)
        self.assertTrue(r.exact_q5_scope_ceiling)
        self.assertTrue(r.exact_q5_outcome_bound)
        self.assertTrue(r.execution_qualified_portable_evidence)
        self.assertTrue(r.historical_exact_execution_reuse)
        self.assertFalse(r.semantic_sibling_credit)
        self.assertFalse(r.fresh_semantic_sibling_execution_qualified)
        self.assertTrue(r.representative_canary_scope_only)

    def test_wrong_receipt_identity_fails_closed(self):
        x = exact_observation()
        x["receipt_digest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Q5_RECEIPT_IDENTITY_MISMATCH"):
            self.classify(observation=x)

    def test_wrong_source_set_fails_closed_even_with_q5_digest_claim(self):
        x = exact_observation()
        x["q13_source_tensor_set_digest"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "Q5_SOURCE_IDENTITY_MISMATCH"):
            self.classify(observation=x)

    def test_scope_laundering_fails_closed(self):
        x = exact_observation()
        x["representative_canary_scope_only"] = False
        with self.assertRaisesRegex(ValueError, "Q5_SCOPE_CEILING_MISMATCH"):
            self.classify(observation=x)

    def test_outcome_substitution_fails_closed(self):
        x = exact_observation()
        x["aggregate_outcome"] = "CONTROL_WIN"
        with self.assertRaisesRegex(ValueError, "Q5_OUTCOME_MISMATCH"):
            self.classify(observation=x)

    def test_wrong_run_head_workflow_or_job_cannot_execution_qualify(self):
        run, _jobs = q15.exact_execution_fixture()
        bad = dict(run)
        bad["head_sha"] = "f" * 40
        self.assertFalse(self.classify(run=bad).execution_qualified_portable_evidence)
        bad = dict(run)
        bad["name"] = "Different Workflow"
        self.assertFalse(self.classify(run=bad).execution_qualified_portable_evidence)
        self.assertFalse(self.classify(jobs=[
            {"id": q15.Q5_JOB + 1, "status": "completed", "conclusion": "success"}
        ]).execution_qualified_portable_evidence)

    def test_successful_execution_does_not_generalize_or_grant_authority(self):
        r = self.classify()
        for key in (
            "generalized_e8_superiority_proven",
            "full_tensor_quantized",
            "whole_model_quantized",
            "glm_quality_proven",
            "runtime_performance_proven",
            "c2_execution_authority_granted",
            "producer_authenticated",
            "effect_authority_granted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            self.assertFalse(getattr(r, key), key)

    def test_q5_is_pre_objective_cut_and_transfer_does_not_reset_clock(self):
        self.assertLess(q15.Q5_SEMANTIC_GENERATED_AT, q15.OBJECTIVE_CUT)
        self.assertGreater(q15.TRANSFER_OBSERVED_AT, q15.OBJECTIVE_CUT)
        r = self.classify()
        self.assertTrue(r.historical_exact_execution_reuse)
        self.assertFalse(r.semantic_sibling_credit)

    def test_receipt_is_deterministic(self):
        self.assertEqual(self.classify().receipt_digest, self.classify().receipt_digest)


if __name__ == "__main__":
    unittest.main()
