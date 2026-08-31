import importlib.util
import sys
from pathlib import Path
import unittest
import numpy as np

PATH = Path(__file__).resolve().parent / "aura_rope_polar_kv_reference.py"
spec = importlib.util.spec_from_file_location("kvref", PATH)
kv = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = kv
spec.loader.exec_module(kv)


class PolarKVReferenceTests(unittest.TestCase):
    def test_exact_polar_roundtrip(self):
        rng = np.random.default_rng(1)
        x = rng.normal(size=(5, 64))
        r, a = kv.to_polar_blocks(x)
        np.testing.assert_allclose(kv.from_polar_blocks(r, a), x, atol=1e-12)

    def test_rope_theta_add_matches_independent_cartesian_rotation(self):
        rng = np.random.default_rng(2)
        x = rng.normal(size=(7, 64))
        angles = rng.uniform(-np.pi, np.pi, size=32)
        np.testing.assert_allclose(
            kv.rope_rotate_blocks(x, angles),
            kv.rope_rotate_cartesian(x, angles),
            atol=1e-12,
        )

    def test_phase_only_loses_attention_relevant_magnitude(self):
        keys = np.array([[1.0, 0.0], [4.0, 0.0]], dtype=np.float32)
        query = np.array([1.0, 0.0], dtype=np.float32)
        exact = kv.attention_logits(query, keys)
        phase = kv.attention_logits(query, kv.phase_only_quantize(keys, 4).reconstructed)
        self.assertNotAlmostEqual(float(exact[0]), float(exact[1]))
        self.assertAlmostEqual(float(phase[0]), float(phase[1]), places=6)

    def test_matched_rate_fixture_reports_no_generalized_claim(self):
        r = kv.benchmark_receipt(seed=42, tokens=512, head_dim=64)
        self.assertTrue(kv.verify_benchmark_receipt(r))
        self.assertAlmostEqual(r["polar_bits_per_dimension_including_fp16_key_scale"], 4.25)
        self.assertAlmostEqual(r["cartesian_bits_per_dimension_including_fp16_key_scale"], 4.25)
        self.assertTrue(r["polar_beats_phase_only_on_fixture"])
        self.assertTrue(r["polar_beats_matched_cartesian_on_fixture"])
        self.assertFalse(r["claim_ceiling"]["polar_quantization_generally_superior"])
        self.assertFalse(r["claim_ceiling"]["fixture_is_glm53_distribution"])

    def test_format_identity_binds_rope_and_cache_generation(self):
        rope_sha = "12" * 32
        i = kv.KVFormatIdentity(
            model_revision="glm53-test",
            representation_revision="polar-ref-v1",
            cache_generation="prefill-17",
            layer_id=3,
            kv_head_id=2,
            head_dim=64,
            rope_config_sha256=rope_sha,
        )
        d = i.digest()
        moved = kv.KVFormatIdentity(
            model_revision=i.model_revision,
            representation_revision=i.representation_revision,
            cache_generation="prefill-18",
            layer_id=i.layer_id,
            kv_head_id=i.kv_head_id,
            head_dim=i.head_dim,
            rope_config_sha256=rope_sha,
        )
        self.assertNotEqual(d, moved.digest())

    def test_format_receipt_k27_is_metadata_only(self):
        i = kv.KVFormatIdentity(
            model_revision="glm53-test",
            representation_revision="polar-ref-v1",
            cache_generation="prefill-17",
            layer_id=3,
            kv_head_id=2,
            head_dim=64,
            rope_config_sha256="ab" * 32,
        )
        b = kv.benchmark_receipt(seed=4, tokens=64, head_dim=64)
        r = kv.format_receipt(i, b)
        self.assertEqual(r["k27_coordinate"], list(kv.k27_from_digest(i.digest())))
        self.assertFalse(r["claim_ceiling"]["k27_coordinate_is_kv_identity"])
        self.assertFalse(r["claim_ceiling"]["runtime_cache_reuse_authorized"])

    def test_tampered_benchmark_receipt_fails(self):
        r = kv.benchmark_receipt(seed=3, tokens=64, head_dim=64)
        self.assertTrue(kv.verify_benchmark_receipt(r))
        r["phase_only_attention_mae"] = 0.0
        self.assertFalse(kv.verify_benchmark_receipt(r))


if __name__ == "__main__":
    unittest.main()
