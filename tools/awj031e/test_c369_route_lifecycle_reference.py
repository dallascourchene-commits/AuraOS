from dataclasses import replace
from itertools import product
import unittest

import c369_route_lifecycle_reference as c


class C369ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.lawful = {f"LT-{a}": c.make_lawful(f"LT-{a}", 7) for a in c.AXES}
        self.axis = tuple(
            c.AxisClosureReceiptV1(f"AX-{a}", a, 7, "SRC-G7", True, True, f"LT-{a}")
            for a in c.AXES
        )
        self.good = c.C369BridgeReceiptV1(
            "BR-369-1", self.axis, ("S-X", "S-Y", "S-Z"), True,
            False, False, 7, 7, (3, 3), (5, 5)
        )

    def test_27_roundtrip_and_shell_counts(self):
        dirs = list(product((-1, 0, 1), repeat=3))
        self.assertTrue(all(c.decode_n(c.encode_n(d)) == d for d in dirs))
        counts = {s: sum(c.route_shell(d) == s for d in dirs) for s in (0, 3, 6, 9)}
        self.assertEqual({0: 1, 3: 6, 6: 12, 9: 8}, counts)
        self.assertTrue(all(c.route_shell(d) == 3 * sum(v != 0 for v in d) for d in dirs))

    def test_exact_dyadic_and_m_nonalias(self):
        self.assertEqual(c.Fraction(1, 8), c.lambda_factor((1, 1, 1), 1))
        self.assertEqual(c.Fraction(1, 512), c.lambda_factor((1, 1, 1), 3))
        u, e = c.refine_then_step((0, 0, 0), (0, 0, 0), (1, -1, 0), 2)
        self.assertEqual((1, -1, 0), u)
        self.assertEqual((2, 2, 0), e)
        self.assertEqual((c.Fraction(1, 4), c.Fraction(-1, 4), c.Fraction(0)), c.exact_position(u, e))

    def test_valid_bridge_and_basic_fail_closed(self):
        self.assertEqual((True, "PASS"), c.validate_c369(self.good, self.lawful))
        cases = [
            (replace(self.good, axis_receipts=self.axis[:2]), "AXIS_RECEIPT_CARDINALITY"),
            (replace(self.good, skipped_seams_reconstructible=False), "UNRECONSTRUCTIBLE_SKIPPED_SEAM"),
            (replace(self.good, gate_bypass=True), "GATE_BYPASS"),
            (replace(self.good, revoked=True), "REVOKED"),
            (replace(self.good, after_generation=8), "C369_CANNOT_INFER_LIFECYCLE_GENERATION"),
            (replace(self.good, bridge_receipt_id=""), "MISSING_BRIDGE_RECEIPT"),
        ]
        for bridge, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(reason, c.validate_c369(bridge, self.lawful)[1])

    def test_axis_and_lawful_receipt_attacks(self):
        duplicate = replace(self.good, axis_receipts=(self.axis[0], self.axis[0], self.axis[2]))
        self.assertEqual("MISSING_OR_DUPLICATE_AXIS", c.validate_c369(duplicate, self.lawful)[1])

        stale = list(self.axis); stale[1] = replace(stale[1], current=False)
        self.assertEqual("STALE_AXIS_RECEIPT", c.validate_c369(replace(self.good, axis_receipts=tuple(stale)), self.lawful)[1])

        mismatched = list(self.axis); mismatched[0] = replace(mismatched[0], matched=False)
        self.assertEqual("MISMATCHED_AXIS_RECEIPT", c.validate_c369(replace(self.good, axis_receipts=tuple(mismatched)), self.lawful)[1])

        source = list(self.axis); source[2] = replace(source[2], source_digest="OTHER")
        self.assertEqual("SOURCE_MISMATCH", c.validate_c369(replace(self.good, axis_receipts=tuple(source)), self.lawful)[1])

        missing = dict(self.lawful); del missing["LT-X"]
        self.assertEqual("MISSING_LAWFUL_TRANSITION", c.validate_c369(self.good, missing)[1])

        unlawful = dict(self.lawful); unlawful["LT-X"] = c.make_lawful("LT-X", 7, source_current=False)
        self.assertEqual("UNLAWFUL_AXIS_TRANSITION", c.validate_c369(self.good, unlawful)[1])

        wrong_gen = dict(self.lawful); wrong_gen["LT-X"] = c.make_lawful("LT-X", 8)
        self.assertEqual("LAWFUL_RECEIPT_GENERATION_MISMATCH", c.validate_c369(self.good, wrong_gen)[1])

    def test_generation_lift_and_incomplete_attacks(self):
        self.assertEqual("GENERATION_MISMATCH", c.validate_c369(replace(self.good, before_generation=6), self.lawful)[1])
        self.assertEqual("BAD_COUPLED_LIFT", c.validate_c369(replace(self.good, after_coordinate=(5, 4)), self.lawful)[1])
        incomplete = list(self.axis); incomplete[0] = replace(incomplete[0], receipt_id="")
        self.assertEqual("INCOMPLETE_AXIS_RECEIPT", c.validate_c369(replace(self.good, axis_receipts=tuple(incomplete)), self.lawful)[1])

    def test_orientation_mechanical_only(self):
        o = c.Orientation369ReceiptV1("D27", "D369", "LT-X", 7, c.encode_n((1, 1, 0)), 6, (3, 6, 9))
        self.assertTrue(c.validate_orientation(o))
        self.assertFalse(c.validate_orientation(replace(o, derivation_receipt_369="")))
        self.assertFalse(c.validate_orientation(replace(o, current_s=9)))
        self.assertFalse(c.validate_orientation(replace(o, permitted_moves=())))

    def test_lifecycle_separate_and_no_self_authorization(self):
        life = c.stage10_rebase(7, 2, 2, True, True)
        self.assertEqual((7, 8, 10, 1), (life.start_generation, life.end_generation, life.start_stage, life.end_stage))
        with self.assertRaises(ValueError): c.stage10_rebase(7, 2, 3, True, True)
        with self.assertRaises(ValueError): c.stage10_rebase(7, 2, 2, False, True)
        with self.assertRaises(ValueError): c.stage10_rebase(7, 2, 2, True, False)

    def test_affected_cone_and_seam_identity(self):
        deps = {"AX-Y": {"BRIDGE-369"}, "BRIDGE-369": {"CREATOR-RUN"}, "UNRELATED": {"OTHER"}}
        self.assertEqual({"AX-Y", "BRIDGE-369", "CREATOR-RUN"}, c.affected_cone({"AX-Y"}, deps))
        self.assertEqual(c.seam_digest(("S-X", "S-Y")), c.seam_digest(("S-X", "S-Y")))
        self.assertNotEqual(c.seam_digest(("S-X", "S-Y")), c.seam_digest(("S-Y", "S-X")))

    def test_invalid_coordinate_inputs_fail_closed(self):
        for bad in ((2, 0, 0), (True, 0, 0)):
            with self.subTest(bad=bad), self.assertRaises(ValueError): c.encode_n(bad)
        for bad in (-1, 27, True, 1.0):
            with self.subTest(bad=bad), self.assertRaises(ValueError): c.decode_n(bad)
        with self.assertRaises(ValueError): c.lambda_factor((1, 0, 0), -1)
        with self.assertRaises(ValueError): c.exact_position((1,), (1, 2))
        with self.assertRaises(ValueError): c.seam_digest(("S-X", ""))

    def test_source_binding_constant(self):
        self.assertEqual("1XUYE51d5j5QbYCCl865eP-gHZyaeiVtm", c.SOURCE_DRIVE_ID)
        self.assertEqual(64, len(c.SOURCE_SHA256))


if __name__ == "__main__":
    unittest.main()
