from dataclasses import replace
import unittest

import numpy as np

from tools.quantization import aura_glm53_e8_indexed_expert_page_reference as e8
from tools.quantization import aura_glm53_e8_concrete_page_trial_binding as bind
from tools.quantization import aura_glm53_quantized_representation_trial as q3

H = "a" * 64
TASKS = "b" * 64
CRITERIA = "c" * 64
HOST = "d" * 64
BASE_REP = "e" * 64
BASE_OUT = "1" * 64
CAND_OUT = "2" * 64


class ConcreteE8PageTrialBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(8060)
        cls.gate = e8.pack_expert_page(
            rng.normal(0.0, 0.02, size=(8, 64)).astype(np.float32),
            model_revision="zai-org/GLM-5.3@exact-test-rev",
            representation_revision="aura-e8-page-r1",
            layer_id=7,
            expert_id=11,
            tensor_role="gate_up_proj",
            block_size=64,
        )
        cls.down = e8.pack_expert_page(
            rng.normal(0.0, 0.02, size=(8, 64)).astype(np.float32),
            model_revision="zai-org/GLM-5.3@exact-test-rev",
            representation_revision="aura-e8-page-r1",
            layer_id=7,
            expert_id=11,
            tensor_role="down_proj",
            block_size=64,
        )
        cls.pages = (cls.gate, cls.down)
        cls.page_set = bind.derive_concrete_e8_page_set(cls.pages)

    def request(self, *, digest=None, nominal=None, static_bytes=None, revision=None):
        ps = self.page_set
        baseline = q3.RepresentationIdentity(
            ps.model_revision, H, "fp8-baseline-r1", BASE_REP, 8.0, 100_000, False
        )
        candidate = q3.RepresentationIdentity(
            ps.model_revision,
            H,
            ps.representation_revision if revision is None else revision,
            ps.representation_digest if digest is None else digest,
            ps.serialized_bits_per_weight if nominal is None else nominal,
            ps.total_serialized_bytes if static_bytes is None else static_bytes,
            True,
        )
        return q3.QuantizedTrialRequest(
            TASKS, CRITERIA, HOST, "MEDIUM", "SINGLE", "BACKGROUND", baseline, candidate
        )

    def sample(self, request, *, candidate, passed=4, wall=80.0):
        rep = request.candidate if candidate else request.baseline
        return q3.TrialSample(
            request_digest=request.request_digest,
            representation_digest=rep.representation_digest,
            route_id="E8_PAGE_SET" if candidate else "FP8_BASELINE",
            task_count=4,
            tasks_passed=passed,
            tasks_failed=4 - passed,
            incorrect_edits=0,
            hallucinated_apis=0,
            source_currentness_violations=0,
            repair_loops=0,
            wall_seconds=wall,
            ttft_seconds=1.0,
            generation_tokens_per_second=10.0,
            bytes_read=rep.static_weight_bytes,
            peak_ram_bytes=rep.static_weight_bytes + 100,
            peak_vram_bytes=0,
            output_set_digest=CAND_OUT if candidate else BASE_OUT,
        )

    def verification(self, request, candidate_sample, *, digest=None):
        return q3.IndependentVerification(
            request.request_digest,
            candidate_sample.sample_digest if digest is None else digest,
            "producer-a",
            "verifier-b",
            4,
            candidate_sample.tasks_passed,
            True,
        )

    def bind_valid(self):
        request = self.request()
        base = self.sample(request, candidate=False, wall=100.0)
        cand = self.sample(request, candidate=True, wall=70.0)
        verification = self.verification(request, cand)
        return bind.bind_concrete_e8_trial(
            pages=self.pages,
            request=request,
            baseline_sample=base,
            candidate_sample=cand,
            independent_verification=verification,
        )

    def test_exact_page_set_binds_q3_candidate_and_independent_sample(self):
        out = self.bind_valid()
        self.assertTrue(out.candidate_identity_bound_to_concrete_page_set)
        self.assertTrue(out.candidate_sample_bound_to_concrete_page_set)
        self.assertTrue(out.independent_verifier_bound_to_candidate_sample)
        self.assertEqual(out.concrete_representation_digest, self.page_set.representation_digest)
        self.assertEqual(out.page_count, 2)
        self.assertEqual(len(out.receipt_sha256), 64)

    def test_page_set_identity_is_order_independent_but_slot_sensitive(self):
        reverse = bind.derive_concrete_e8_page_set(tuple(reversed(self.pages)))
        self.assertEqual(reverse.page_set_digest, self.page_set.page_set_digest)
        self.assertEqual(reverse.representation_digest, self.page_set.representation_digest)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_LOGICAL_PAGE_SLOT"):
            bind.derive_concrete_e8_page_set((self.gate, self.gate))

    def test_valid_generic_q3_candidate_digest_cannot_impersonate_concrete_pages(self):
        request = self.request(digest="f" * 64)
        base = self.sample(request, candidate=False)
        cand = self.sample(request, candidate=True)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_DIGEST_NOT_CONCRETE_PAGE_SET"):
            bind.bind_concrete_e8_trial(
                pages=self.pages,
                request=request,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=self.verification(request, cand),
            )

    def test_codec_only_225_bpw_cannot_hide_serialized_page_overhead(self):
        self.assertNotAlmostEqual(self.page_set.serialized_bits_per_weight, self.page_set.codec_bits_per_weight)
        request = self.request(nominal=self.page_set.codec_bits_per_weight)
        base = self.sample(request, candidate=False)
        cand = self.sample(request, candidate=True)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_BPW_NOT_EXACT_SERIALIZED_PAGE_SET_RATE"):
            bind.bind_concrete_e8_trial(
                pages=self.pages,
                request=request,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=self.verification(request, cand),
            )

    def test_static_bytes_must_equal_exact_serialized_page_set(self):
        request = self.request(static_bytes=self.page_set.total_serialized_bytes + 1)
        base = self.sample(request, candidate=False)
        cand = self.sample(request, candidate=True)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_BYTES_NOT_EXACT_SERIALIZED_PAGE_SET_BYTES"):
            bind.bind_concrete_e8_trial(
                pages=self.pages,
                request=request,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=self.verification(request, cand),
            )

    def test_payload_tamper_fails_before_q3_binding(self):
        payload = bytearray(self.gate.payload)
        payload[-1] ^= 1
        bad = e8.PackedExpertPage(
            identity=self.gate.identity,
            payload=bytes(payload),
            payload_sha256=self.gate.payload_sha256,
            k27_coordinate=self.gate.k27_coordinate,
            codec_bits_per_weight=self.gate.codec_bits_per_weight,
            serialized_bits_per_weight=self.gate.serialized_bits_per_weight,
        )
        with self.assertRaises(ValueError):
            bind.derive_concrete_e8_page_set((bad, self.down))

    def test_mixed_representation_revision_is_rejected(self):
        rng = np.random.default_rng(9)
        foreign = e8.pack_expert_page(
            rng.normal(0.0, 0.02, size=(8, 64)).astype(np.float32),
            model_revision=self.gate.identity.model_revision,
            representation_revision="aura-e8-page-r2",
            layer_id=7,
            expert_id=11,
            tensor_role="down_proj",
            block_size=64,
        )
        with self.assertRaisesRegex(ValueError, "MIXED_REPRESENTATION_REVISIONS"):
            bind.derive_concrete_e8_page_set((self.gate, foreign))

    def test_source_tensor_change_invalidates_old_candidate_identity(self):
        rng = np.random.default_rng(10)
        replacement = e8.pack_expert_page(
            rng.normal(0.0, 0.02, size=(8, 64)).astype(np.float32),
            model_revision=self.gate.identity.model_revision,
            representation_revision=self.gate.identity.representation_revision,
            layer_id=7,
            expert_id=11,
            tensor_role="down_proj",
            block_size=64,
        )
        changed = bind.derive_concrete_e8_page_set((self.gate, replacement))
        self.assertNotEqual(changed.source_tensor_set_digest, self.page_set.source_tensor_set_digest)
        self.assertNotEqual(changed.representation_digest, self.page_set.representation_digest)
        request = self.request()
        base = self.sample(request, candidate=False)
        cand = self.sample(request, candidate=True)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_DIGEST_NOT_CONCRETE_PAGE_SET"):
            bind.bind_concrete_e8_trial(
                pages=(self.gate, replacement),
                request=request,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=self.verification(request, cand),
            )

    def test_q3_independent_verifier_still_must_bind_exact_candidate_sample(self):
        request = self.request()
        base = self.sample(request, candidate=False)
        cand = self.sample(request, candidate=True)
        with self.assertRaisesRegex(ValueError, "VERIFIER_SAMPLE_BINDING_MISMATCH"):
            bind.bind_concrete_e8_trial(
                pages=self.pages,
                request=request,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=self.verification(request, cand, digest="3" * 64),
            )

    def test_success_remains_below_official_source_whole_model_execution_and_authority(self):
        out = self.bind_valid()
        for value in (
            out.official_glm_source_authenticated,
            out.baseline_same_source_tensor_set_proven,
            out.whole_model_coverage_proven,
            out.page_set_executed_in_model,
            out.router_execution_observed,
            out.coding_quality_generalized_beyond_frozen_corpus,
            out.general_performance_winner_proven,
            out.owner_host_identity_authenticated,
            out.physical_io_attributed_exclusively,
            out.semantic_k27_authority_minted,
            out.native_private_transformer_kv_accessed,
            out.gate10_ready_for_owner_promotion,
            out.deployment_authorized,
        ):
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
