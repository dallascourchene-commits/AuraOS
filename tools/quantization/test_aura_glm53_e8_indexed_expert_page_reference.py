import importlib.util
import sys
from pathlib import Path
import unittest
import numpy as np

MODULE_PATH = Path(__file__).resolve().parent / "aura_glm53_e8_indexed_expert_page_reference.py"
spec = importlib.util.spec_from_file_location("e8ref", MODULE_PATH)
e8 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = e8
spec.loader.exec_module(e8)


class E8ReferenceTests(unittest.TestCase):
    def test_half_integer_coset_survives_roundtrip_safe_encoding(self):
        x = np.full((1, 8), 0.49, dtype=np.float64)
        q = e8.quantize_e8_unbounded(x)
        self.assertTrue(np.all(q == 0.5))
        encoded = e8.encode_e8_doubled_coordinates(q)
        self.assertTrue(np.all(encoded == 1))
        decoded = e8.decode_e8_doubled_coordinates(encoded)
        np.testing.assert_array_equal(decoded, q)
        self.assertTrue(np.any(q != q.astype(np.int8).astype(np.float64)))

    def test_finite_codebook_is_uint16_addressable(self):
        grid, _ = e8.get_codebook()
        self.assertEqual(grid.shape, (58112, 8))
        self.assertLess(len(grid), 2**16)

    def test_compress_decompress_and_rate_accounting(self):
        rng = np.random.default_rng(7)
        w = rng.normal(0, 0.02, size=(8, 64)).astype(np.float32)
        c = e8.compress_weights(w, block_size=64)
        r = e8.decompress_weights(c)
        self.assertEqual(r.shape, w.shape)
        self.assertEqual(c.indices.dtype, np.uint16)
        self.assertEqual(c.scales.dtype, np.float16)
        self.assertAlmostEqual(e8.payload_bits_per_weight(w.size, 64), 2.25, places=8)

    def test_reference_fixture_beats_simple_four_level_scalar(self):
        receipt = e8.benchmark_receipt(seed=42, shape=(32, 64), block_size=64)
        self.assertTrue(e8.verify_benchmark_receipt(receipt))
        self.assertTrue(receipt["e8_beats_scalar_on_fixture"])
        self.assertLess(receipt["mse_e8"], receipt["mse_scalar_4level"])
        self.assertFalse(receipt["claim_ceiling"]["glm53_quality_preserved"])
        self.assertFalse(receipt["claim_ceiling"]["production_quantizer_ready"])

    def test_expert_page_binary_roundtrip_binds_provenance_and_k27_metadata(self):
        rng = np.random.default_rng(9)
        w = rng.normal(0, 0.02, size=(16, 64)).astype(np.float32)
        page = e8.pack_expert_page(
            w,
            model_revision="zai-org/GLM-5.3@test-rev",
            representation_revision="aura-e8-ref-v1",
            layer_id=3,
            expert_id=17,
            tensor_role="gate_up_proj",
            block_size=64,
        )
        restored = e8.unpack_expert_page(page)
        self.assertEqual(restored.shape, w.shape)
        self.assertEqual(page.k27_coordinate, e8.k27_coordinate_from_digest(page.identity.digest()))
        receipt = e8.expert_page_receipt(page)
        self.assertFalse(receipt["claim_ceiling"]["k27_coordinate_is_expert_identity"])
        self.assertFalse(receipt["claim_ceiling"]["model_router_semantics_changed"])
        self.assertEqual(receipt["payload_sha256"], page.payload_sha256)
        self.assertGreater(page.serialized_bits_per_weight, page.codec_bits_per_weight)

    def test_expert_page_tamper_and_identity_substitution_fail(self):
        rng = np.random.default_rng(10)
        w = rng.normal(0, 0.02, size=(8, 64)).astype(np.float32)
        page = e8.pack_expert_page(
            w,
            model_revision="mrev",
            representation_revision="rrev",
            layer_id=4,
            expert_id=2,
            tensor_role="down_proj",
        )
        bad_payload = bytearray(page.payload)
        bad_payload[-1] ^= 1
        tampered = e8.PackedExpertPage(
            identity=page.identity,
            payload=bytes(bad_payload),
            payload_sha256=page.payload_sha256,
            k27_coordinate=page.k27_coordinate,
            codec_bits_per_weight=page.codec_bits_per_weight,
            serialized_bits_per_weight=page.serialized_bits_per_weight,
        )
        with self.assertRaises(ValueError):
            e8.unpack_expert_page(tampered)

        wrong_identity = e8.ExpertPageIdentity(
            model_revision=page.identity.model_revision,
            representation_revision="other-representation",
            layer_id=page.identity.layer_id,
            expert_id=page.identity.expert_id,
            tensor_role=page.identity.tensor_role,
            source_tensor_sha256=page.identity.source_tensor_sha256,
            source_shape=page.identity.source_shape,
        )
        substituted = e8.PackedExpertPage(
            identity=wrong_identity,
            payload=page.payload,
            payload_sha256=page.payload_sha256,
            k27_coordinate=e8.k27_coordinate_from_digest(wrong_identity.digest()),
            codec_bits_per_weight=page.codec_bits_per_weight,
            serialized_bits_per_weight=page.serialized_bits_per_weight,
        )
        with self.assertRaises(ValueError):
            e8.unpack_expert_page(substituted)

    def test_bad_receipt_tamper_fails(self):
        receipt = e8.benchmark_receipt(seed=1, shape=(8, 64), block_size=64)
        self.assertTrue(e8.verify_benchmark_receipt(receipt))
        receipt["mse_e8"] = 0.0
        self.assertFalse(e8.verify_benchmark_receipt(receipt))


if __name__ == "__main__":
    unittest.main()
