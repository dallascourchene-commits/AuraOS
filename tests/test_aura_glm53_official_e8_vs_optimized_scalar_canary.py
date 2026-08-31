import math
import struct
import unittest

import numpy as np

from tools.quantization import aura_glm53_official_e8_vs_optimized_scalar_canary as q6


class OfficialE8VsOptimizedScalarCanaryTests(unittest.TestCase):
    def test_derivation_and_rate_constants_are_exact(self):
        self.assertEqual(q6.Q14_HEAD, "ee70934e0c45572588829e742e512a897b23863f")
        self.assertEqual(q6.Q14_RUN, 33399560819)
        self.assertEqual(q6.AGELF_DRIVE_ID, "1qgf9Q0vt2ns5KlyS7Cb21zWsvzI1rre4-f4MgK_OLNQ")
        self.assertEqual(q6.SCALAR_PAYLOAD_BYTES, 18)
        self.assertEqual(q6.SCALAR_BITS_PER_WEIGHT, 2.25)
        self.assertEqual(q6.SCALAR_LEVELS, (-3.0, -1.0, 1.0, 3.0))

    def test_two_bit_labels_pack_and_unpack_exactly(self):
        labels = tuple(i % 4 for i in range(64))
        packed = q6._pack_labels(labels)
        self.assertEqual(len(packed), 16)
        self.assertEqual(q6._unpack_labels(packed), labels)
        with self.assertRaises(q6.ScalarCanaryError):
            q6._pack_labels(labels[:-1])
        with self.assertRaises(q6.ScalarCanaryError):
            q6._unpack_labels(packed[:-1])

    def test_scalar_payload_is_exact_18_bytes_and_roundtrips_finite(self):
        values = tuple((i - 31.5) / 17.0 for i in range(64))
        payload = q6.encode_optimized_scalar(values)
        self.assertEqual(len(payload), 18)
        reconstructed = q6.decode_optimized_scalar(payload)
        self.assertEqual(len(reconstructed), 64)
        self.assertTrue(all(math.isfinite(x) for x in reconstructed))

    def test_zero_tile_is_deterministic_and_rate_preserving(self):
        values = (0.0,) * 64
        a = q6.encode_optimized_scalar(values)
        b = q6.encode_optimized_scalar(values)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 18)
        self.assertEqual(q6.decode_optimized_scalar(a), values)

    def test_candidate_search_beats_or_matches_simple_max_scale_baseline(self):
        values = np.asarray([(-1.0 if i % 2 else 1.0) * (0.01 + (i % 13) * 0.07) for i in range(64)], dtype=np.float64)
        payload = q6.encode_optimized_scalar(values)
        optimized = q6._mse(values, q6.decode_optimized_scalar(payload))
        simple_scale = float(np.float16(np.max(np.abs(values)) / 3.0))
        labels, simple_recon, _ = q6._quantize_for_scale(values, simple_scale)
        self.assertEqual(len(q6._pack_labels(labels)) + 2, 18)
        simple = q6._mse(values, simple_recon)
        self.assertLessEqual(optimized, simple + 1e-18)

    def test_invalid_scalar_inputs_fail_closed(self):
        with self.assertRaises(q6.ScalarCanaryError):
            q6.encode_optimized_scalar([1.0] * 63)
        bad = [1.0] * 64
        bad[0] = float("nan")
        with self.assertRaises(q6.ScalarCanaryError):
            q6.encode_optimized_scalar(bad)
        with self.assertRaises(q6.ScalarCanaryError):
            q6.decode_optimized_scalar(bytes(17))
        with self.assertRaises(q6.ScalarCanaryError):
            q6.decode_optimized_scalar(struct.pack("<e", float("inf")) + bytes(16))

    def test_scientific_outcome_is_neutral(self):
        self.assertEqual(q6._classify(1.0, 2.0), "E8_WIN")
        self.assertEqual(q6._classify(2.0, 1.0), "SCALAR_WIN")
        self.assertEqual(q6._classify(1.0, 1.0), "TIE")

    def test_live_receipt_preserves_representative_nonpromotion_ceiling(self):
        receipt = q6.current_official_e8_vs_scalar_canary()
        self.assertEqual(len(receipt.roles), 2)
        self.assertTrue(receipt.same_official_source_tiles_compared)
        self.assertTrue(receipt.optimized_scalar_control_used)
        self.assertTrue(receipt.official_source_equal_rate_distortion_evidence)
        self.assertTrue(receipt.representative_canary_scope_only)
        self.assertAlmostEqual(receipt.exact_codec_rate_bpw, 2.25)
        self.assertTrue(all(role.equal_codec_rate for role in receipt.roles))
        self.assertTrue(all(math.isclose(role.q14_e8_codec_bits_per_weight, 2.25, abs_tol=1e-12) for role in receipt.roles))
        self.assertTrue(all(math.isclose(role.scalar_codec_bits_per_weight, 2.25, abs_tol=1e-12) for role in receipt.roles))
        self.assertIn(receipt.aggregate_outcome, {"E8_WIN", "SCALAR_WIN", "TIE"})
        self.assertFalse(receipt.geometry_privileged)
        self.assertFalse(receipt.full_role_quantized)
        self.assertFalse(receipt.whole_model_quantized)
        self.assertFalse(receipt.glm_quality_proven)
        self.assertFalse(receipt.runtime_performance_proven)
        self.assertFalse(receipt.semantic_k27_authority)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)
        self.assertFalse(receipt.gate10_promoted)


if __name__ == "__main__":
    unittest.main()
