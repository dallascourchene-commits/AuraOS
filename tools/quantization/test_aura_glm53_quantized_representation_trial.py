from __future__ import annotations

import unittest

from tools.quantization.aura_glm53_quantized_representation_trial import (
    FULL_MODEL_STATIC,
    ROUTED_EXPERT_BANK_STATIC,
    IndependentVerification,
    QuantizedTrialRequest,
    RepresentationIdentity,
    TrialSample,
    compare_quantized_representation,
)

H = "a" * 64
T = "b" * 64
A = "c" * 64
P = "d" * 64
B = "e" * 64
C = "f" * 64
O1 = "1" * 64
O2 = "2" * 64
D = "9" * 64
D2 = "8" * 64


def reps():
    baseline = RepresentationIdentity("glm53-r1", H, "fp8-r1", B, 8.0, 753_000_000_000, FULL_MODEL_STATIC, D, False)
    candidate = RepresentationIdentity("glm53-r1", H, "vq-r1", C, 2.5, 240_000_000_000, FULL_MODEL_STATIC, D, True)
    return baseline, candidate


def req():
    baseline, candidate = reps()
    return QuantizedTrialRequest(T, A, P, "MEDIUM", "SINGLE", "BACKGROUND", baseline, candidate)


def sample(r, *, candidate, passed=6, wall=100.0, ram=100, vram=100, incorrect=0, hallucinated=0, currentness=0):
    rep = r.candidate if candidate else r.baseline
    return TrialSample(
        request_digest=r.request_digest,
        representation_digest=rep.representation_digest,
        route_id="LOCAL_GLM53_QUANT" if candidate else "LOCAL_GLM53_FP8",
        task_count=6,
        tasks_passed=passed,
        tasks_failed=6-passed,
        incorrect_edits=incorrect,
        hallucinated_apis=hallucinated,
        source_currentness_violations=currentness,
        repair_loops=1,
        wall_seconds=wall,
        ttft_seconds=1.0,
        generation_tokens_per_second=10.0,
        bytes_read=1_000,
        peak_ram_bytes=ram,
        peak_vram_bytes=vram,
        output_set_digest=O2 if candidate else O1,
    )


def verify(r, candidate_sample, passed=6, *, producer="agent-a", verifier="agent-b", accepted=True):
    return IndependentVerification(r.request_digest, candidate_sample.sample_digest, producer, verifier, 6, passed, accepted)


class QuantizedRepresentationTrialTests(unittest.TestCase):
    def test_smaller_faster_candidate_requires_quality_and_independent_reproduction(self):
        r = req(); base = sample(r, candidate=False, wall=120, ram=200, vram=200); cand = sample(r, candidate=True, wall=90, ram=100, vram=100)
        out = compare_quantized_representation(request=r, baseline_sample=base, candidate_sample=cand, independent_verification=verify(r, cand))
        self.assertTrue(out.candidate_quality_retained_on_frozen_corpus)
        self.assertTrue(out.candidate_smaller_static_weights)
        self.assertTrue(out.candidate_faster_wall_time)
        self.assertEqual(out.candidate_tradeoff_class, "FROZEN_CORPUS_CANDIDATE_DOMINATES_MEASURED_AXES")
        self.assertEqual(out.static_weight_byte_domain, FULL_MODEL_STATIC)
        self.assertEqual(out.static_weight_byte_domain_digest, D)
        self.assertFalse(out.general_performance_winner_proven)
        self.assertFalse(out.gate10_ready_for_owner_promotion)

    def test_resource_gain_with_quality_regression_is_not_winner(self):
        r = req(); base = sample(r, candidate=False, passed=6, wall=120); cand = sample(r, candidate=True, passed=5, wall=80)
        out = compare_quantized_representation(request=r, baseline_sample=base, candidate_sample=cand, independent_verification=verify(r, cand, passed=5))
        self.assertFalse(out.candidate_quality_retained_on_frozen_corpus)
        self.assertEqual(out.candidate_tradeoff_class, "RESOURCE_GAIN_WITH_QUALITY_REGRESSION")
        self.assertFalse(out.general_performance_winner_proven)

    def test_same_model_and_topology_are_required(self):
        baseline, candidate = reps()
        bad = RepresentationIdentity(
            "glm53-other", H, candidate.representation_revision, candidate.representation_digest,
            candidate.nominal_bits_per_weight, candidate.static_weight_bytes,
            candidate.static_weight_byte_domain, candidate.static_weight_byte_domain_digest, True
        )
        with self.assertRaisesRegex(ValueError, "MODEL_REVISION_MISMATCH"):
            QuantizedTrialRequest(T, A, P, "MEDIUM", "SINGLE", "BACKGROUND", baseline, bad).validate()

    def test_whole_model_vs_routed_expert_byte_cross_cast_is_rejected(self):
        baseline, candidate = reps()
        expert_only = RepresentationIdentity(
            candidate.model_revision, candidate.topology_digest, candidate.representation_revision,
            candidate.representation_digest, candidate.nominal_bits_per_weight, 120_000_000_000,
            ROUTED_EXPERT_BANK_STATIC, D2, True
        )
        with self.assertRaisesRegex(ValueError, "STATIC_WEIGHT_BYTE_DOMAIN_MISMATCH"):
            QuantizedTrialRequest(T, A, P, "MEDIUM", "SINGLE", "BACKGROUND", baseline, expert_only).validate()

    def test_same_domain_label_with_different_component_manifest_is_rejected(self):
        baseline, candidate = reps()
        mismatched_manifest = RepresentationIdentity(
            candidate.model_revision, candidate.topology_digest, candidate.representation_revision,
            candidate.representation_digest, candidate.nominal_bits_per_weight, candidate.static_weight_bytes,
            FULL_MODEL_STATIC, D2, True
        )
        with self.assertRaisesRegex(ValueError, "STATIC_WEIGHT_BYTE_DOMAIN_MANIFEST_MISMATCH"):
            QuantizedTrialRequest(T, A, P, "MEDIUM", "SINGLE", "BACKGROUND", baseline, mismatched_manifest).validate()

    def test_invalid_byte_domain_is_rejected(self):
        baseline, candidate = reps()
        bad = RepresentationIdentity(
            candidate.model_revision, candidate.topology_digest, candidate.representation_revision,
            candidate.representation_digest, candidate.nominal_bits_per_weight, candidate.static_weight_bytes,
            "UNSCOPED_BYTES", D, True
        )
        with self.assertRaisesRegex(ValueError, "INVALID_STATIC_WEIGHT_BYTE_DOMAIN"):
            QuantizedTrialRequest(T, A, P, "MEDIUM", "SINGLE", "BACKGROUND", baseline, bad).validate()

    def test_candidate_output_may_differ_but_quality_must_be_measured(self):
        r = req(); base = sample(r, candidate=False); cand = sample(r, candidate=True)
        self.assertNotEqual(base.output_set_digest, cand.output_set_digest)
        out = compare_quantized_representation(request=r, baseline_sample=base, candidate_sample=cand, independent_verification=verify(r, cand))
        self.assertTrue(out.candidate_quality_retained_on_frozen_corpus)
        self.assertFalse(out.exact_causal_timing_comparison_claimed)

    def test_same_producer_and_verifier_is_rejected(self):
        r = req(); cand = sample(r, candidate=True)
        with self.assertRaisesRegex(ValueError, "SELF_REVIEW_IS_NOT_INDEPENDENT"):
            compare_quantized_representation(request=r, baseline_sample=sample(r, candidate=False), candidate_sample=cand, independent_verification=verify(r, cand, producer="same", verifier="same"))

    def test_independent_verifier_must_bind_exact_candidate_sample(self):
        r = req(); cand = sample(r, candidate=True)
        v = IndependentVerification(r.request_digest, "3"*64, "a", "b", 6, 6, True)
        with self.assertRaisesRegex(ValueError, "VERIFIER_SAMPLE_BINDING_MISMATCH"):
            compare_quantized_representation(request=r, baseline_sample=sample(r, candidate=False), candidate_sample=cand, independent_verification=v)

    def test_quality_retention_includes_error_and_currentness_axes(self):
        r = req(); base = sample(r, candidate=False, incorrect=0, currentness=0); cand = sample(r, candidate=True, incorrect=1, currentness=0)
        out = compare_quantized_representation(request=r, baseline_sample=base, candidate_sample=cand, independent_verification=verify(r, cand))
        self.assertFalse(out.candidate_quality_retained_on_frozen_corpus)

    def test_successful_frozen_corpus_receipt_remains_nonauthorizing(self):
        r = req(); base = sample(r, candidate=False); cand = sample(r, candidate=True)
        out = compare_quantized_representation(request=r, baseline_sample=base, candidate_sample=cand, independent_verification=verify(r, cand))
        self.assertFalse(out.coding_quality_generalized_beyond_frozen_corpus)
        self.assertFalse(out.owner_host_identity_authenticated)
        self.assertFalse(out.physical_io_attributed_exclusively)
        self.assertFalse(out.native_private_transformer_kv_accessed)
        self.assertFalse(out.semantic_k27_authority_minted)
        self.assertFalse(out.deployment_authorized)
        self.assertEqual(len(out.comparison_digest), 64)


if __name__ == "__main__":
    unittest.main()
