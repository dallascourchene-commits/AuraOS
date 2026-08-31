from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
import unittest

from tools.quantization import aura_glm53_live_official_tensor_payload_canary as q10


class LiveOfficialTensorPayloadCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.weight = b"W" * q10._expected_bytes(q10.WEIGHT_DTYPE, q10.WEIGHT_SHAPE)
        cls.scale = b"S" * q10._expected_bytes(q10.SCALE_DTYPE, q10.SCALE_SHAPE)

    def test_exact_parent_metadata_byte_counts(self) -> None:
        q10._validate_parent_metadata()
        self.assertEqual(len(self.weight), 12_582_912)
        self.assertEqual(len(self.scale), 3_072)
        self.assertEqual(len(self.weight) + len(self.scale), 12_585_984)
        self.assertEqual(q10.WEIGHT_OFFSETS[1] - q10.WEIGHT_OFFSETS[0], len(self.weight))
        self.assertEqual(q10.SCALE_OFFSETS[1] - q10.SCALE_OFFSETS[0], len(self.scale))

    def test_receipt_binds_raw_payload_hashes_and_half_open_absolute_ranges(self) -> None:
        r = q10._build_receipt(header_len=4096, weight_raw=self.weight, scale_raw=self.scale)
        self.assertEqual(r.weight_payload_sha256, hashlib.sha256(self.weight).hexdigest())
        self.assertEqual(r.scale_payload_sha256, hashlib.sha256(self.scale).hexdigest())
        self.assertEqual(r.weight_absolute_range[1] - r.weight_absolute_range[0], r.weight_payload_bytes)
        self.assertEqual(r.scale_absolute_range[1] - r.scale_absolute_range[0], r.scale_payload_bytes)
        self.assertEqual(r.weight_absolute_range[0], 8 + 4096 + q10.WEIGHT_OFFSETS[0])
        self.assertEqual(r.scale_absolute_range[0], 8 + 4096 + q10.SCALE_OFFSETS[0])

    def test_new_rank_is_representative_payload_only(self) -> None:
        r = q10._build_receipt(header_len=4096, weight_raw=self.weight, scale_raw=self.scale)
        self.assertTrue(r.live_representative_tensor_payload_pair_observed)
        self.assertTrue(r.representative_scope_only)
        self.assertFalse(r.full_expert_payload_observed)
        self.assertFalse(r.all_layer_expert_payload_uniformity_proven)

    def test_raw_fp8_payload_cannot_impersonate_pr628_float32_source_identity(self) -> None:
        r = q10._build_receipt(header_len=4096, weight_raw=self.weight, scale_raw=self.scale)
        self.assertFalse(r.raw_fp8_payload_is_pr628_canonical_float32_source_identity)
        self.assertFalse(r.official_tensor_to_pr628_source_tensor_relation_proven)
        self.assertFalse(r.candidate_page_materialization_owner_bound)
        self.assertFalse(r.baseline_same_official_source_tensor_set_proven)

    def test_full_nonpromotion_ceiling(self) -> None:
        r = q10._build_receipt(header_len=4096, weight_raw=self.weight, scale_raw=self.scale)
        for field in (
            "real_tensor_quantization_eligible",
            "model_execution_observed",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(getattr(r, field), field)

    def test_wrong_payload_length_fails_closed(self) -> None:
        with self.assertRaises(q10.PayloadCanaryError):
            q10._build_receipt(header_len=4096, weight_raw=self.weight[:-1], scale_raw=self.scale)
        with self.assertRaises(q10.PayloadCanaryError):
            q10._build_receipt(header_len=4096, weight_raw=self.weight, scale_raw=self.scale + b"x")

    def test_header_length_bounds_fail_closed(self) -> None:
        for bad in (0, 1, q10.MAX_HEADER_BYTES + 1):
            with self.assertRaises(q10.PayloadCanaryError):
                q10._build_receipt(header_len=bad, weight_raw=self.weight, scale_raw=self.scale)

    def test_receipt_is_deterministic_and_tamper_sensitive(self) -> None:
        a = q10._build_receipt(header_len=4096, weight_raw=self.weight, scale_raw=self.scale)
        b = q10._build_receipt(header_len=4096, weight_raw=self.weight, scale_raw=self.scale)
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertNotEqual(a.receipt_digest, replace(a, candidate_page_materialization_owner_bound=True).receipt_digest)

    def test_live_public_observation_has_zero_caller_inputs(self) -> None:
        self.assertEqual(len(inspect.signature(q10.current_live_observation).parameters), 0)


if __name__ == "__main__":
    unittest.main()
