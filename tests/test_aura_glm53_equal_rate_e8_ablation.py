import importlib.util
import math
import pathlib
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "tools" / "quantization" / "aura_glm53_equal_rate_e8_ablation.py"
spec = importlib.util.spec_from_file_location("equal_rate_e8", MODULE_PATH)
q = importlib.util.module_from_spec(spec)
# W3 loader repair: dataclasses need the dynamically loaded module registered first.
sys.modules[spec.name] = q
assert spec.loader is not None
spec.loader.exec_module(q)


class EqualRateE8AblationTests(unittest.TestCase):
    def test_e8_root_system_is_exact_and_finite(self):
        self.assertEqual(len(q.E8_ROOTS), 240)
        self.assertEqual(len(set(q.E8_ROOTS)), 240)
        for root in q.E8_ROOTS:
            self.assertTrue(math.isclose(sum(x * x for x in root), 2.0))
        self.assertIn((0.5,) * 8, q.E8_ROOTS)

    def test_matched_payload_rate_is_exactly_1_25_bpw(self):
        block = q.frozen_gaussian_blocks(1)[0]
        e8_payload = q.encode_group(block, q.E8_SCHEME)
        hc_payload = q.encode_group(block, q.HYPERCUBE_SCHEME)
        self.assertEqual(len(e8_payload), 10)
        self.assertEqual(len(hc_payload), 10)
        self.assertEqual(len(e8_payload), len(hc_payload))
        self.assertEqual(q.CODEC_BPW, 1.25)

    def test_packed_roundtrip_is_deterministic(self):
        block = q.frozen_heavy_tail_blocks(1)[0]
        p1 = q.encode_group(block, q.E8_SCHEME)
        p2 = q.encode_group(block, q.E8_SCHEME)
        self.assertEqual(p1, p2)
        self.assertEqual(q.decode_group(p1, q.E8_SCHEME), q.decode_group(p2, q.E8_SCHEME))

    def test_unused_e8_byte_indices_fail_closed(self):
        payload = b"\x00\x00" + bytes([240]) + bytes(7)
        with self.assertRaises(ValueError):
            q.decode_group(payload, q.E8_SCHEME)

    def test_unknown_scheme_fails_closed(self):
        block = q.frozen_gaussian_blocks(1)[0]
        with self.assertRaises(ValueError):
            q.encode_group(block, "RAW_LATTICE_COORDS")

    def test_e8_beats_equal_rate_hypercube_on_frozen_gaussian(self):
        receipt = q.run_ablation()
        lane = next(x for x in receipt.lanes if x.fixture == "FROZEN_GAUSSIAN_V1")
        self.assertTrue(lane.e8_better)
        self.assertLess(lane.e8_over_hypercube, 0.95)

    def test_e8_beats_equal_rate_hypercube_on_frozen_heavy_tail(self):
        receipt = q.run_ablation()
        lane = next(x for x in receipt.lanes if x.fixture == "FROZEN_HEAVY_TAIL_V1")
        self.assertTrue(lane.e8_better)
        self.assertLess(lane.e8_over_hypercube, 0.85)

    def test_consequence_ceiling_stays_closed(self):
        receipt = q.run_ablation()
        self.assertTrue(receipt.synthetic_distortion_evidence_only)
        self.assertFalse(receipt.real_glm_tensor_quantized)
        self.assertFalse(receipt.glm_quality_proven)
        self.assertFalse(receipt.runtime_performance_proven)
        self.assertFalse(receipt.geometry_privileged)
        self.assertFalse(receipt.gate10_promoted)


if __name__ == "__main__":
    unittest.main()
