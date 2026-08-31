import inspect
import math
import unittest

from tools.quantization import aura_glm53_official_equal_rate_e8_canary as q5

# Hosted reproof trigger after CODEMAP-bot-only head drift; experiment, codecs,
# fixed source coordinates, outcome neutrality, and claim ceiling are unchanged.


class OfficialEqualRateE8CanaryTests(unittest.TestCase):
    def test_exact_two_nonself_derivation_anchors_are_pinned(self):
        self.assertEqual(q5.Q13_HEAD, "eb09b5ffd14577d1676f57bb908e5ddd81125605")
        self.assertEqual(q5.Q13_RUN, 33397035043)
        self.assertEqual(q5.Q13_SOURCE_SET_DIGEST, "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6")
        self.assertEqual(q5.AGELF_DRIVE_ID, "1qgf9Q0vt2ns5KlyS7Cb21zWsvzI1rre4-f4MgK_OLNQ")

    def test_canary_coordinates_are_fixed_and_each_stays_inside_one_fp8_cell(self):
        self.assertEqual(q5.WINDOW_STARTS, (0, 128, 256, 384))
        for role in q5.ROLE_SPECS:
            for start in q5.WINDOW_STARTS:
                _, _, scale_col = q5._validate_start(role, start)
                self.assertEqual(scale_col, start // 128)
                self.assertLessEqual((start % 128) + q5.WINDOW_WEIGHTS, 128)

    def test_unregistered_coordinate_fails_closed(self):
        with self.assertRaises(q5.OfficialCanaryError):
            q5._validate_start("gate_up_proj", 64)
        with self.assertRaises(q5.OfficialCanaryError):
            q5._validate_start("up_proj", 0)

    def test_decode_tile_requires_exact_64_codes_and_positive_finite_scale(self):
        with self.assertRaises(q5.OfficialCanaryError):
            q5._decode_tile(bytes(63), b"\x00\x00\x80?")
        with self.assertRaises(q5.OfficialCanaryError):
            q5._decode_tile(bytes(64), b"\x00\x00\x00\x00")

    def test_equal_rate_evaluator_never_requires_geometry_to_win(self):
        values = tuple(1.0 if i % 2 else -1.0 for i in range(64))
        e8, control, e8_mse, control_mse, outcome = q5._evaluate(values)
        self.assertEqual(len(e8), len(control))
        self.assertEqual(len(e8), 10)
        self.assertEqual(q5.q4.CODEC_BPW, 1.25)
        self.assertIn(outcome, {"E8_WIN", "CONTROL_WIN", "TIE"})
        self.assertTrue(math.isfinite(e8_mse) and math.isfinite(control_mse))

    def test_outcome_classifier_preserves_win_tie_loss(self):
        self.assertEqual(q5._classify(1.0, 2.0), "E8_WIN")
        self.assertEqual(q5._classify(2.0, 1.0), "CONTROL_WIN")
        self.assertEqual(q5._classify(1.0, 1.0), "TIE")

    def test_live_public_boundary_has_no_source_or_result_override(self):
        params = inspect.signature(q5.current_official_equal_rate_canary).parameters
        self.assertEqual(tuple(params), ())
        for name in ("geometry_privileged", "glm_quality_proven", "runtime_performance_proven", "gate10_promoted"):
            self.assertIn(name, q5.OfficialEqualRateCanaryReceipt.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()
