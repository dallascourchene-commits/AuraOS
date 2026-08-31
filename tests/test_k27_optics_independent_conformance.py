from pathlib import Path
import dataclasses
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_optics_independent_conformance as conf


PARENTS = (
    "1l8FLO6a0ebJX1D4L2VP5PThii4P_vcGGrGMxBHYy_Ew",
    "10OUpjrsvxaVfJprxqCIuGcX9cB0V58noo4mbzYW4peg",
)
SOURCE_SHA = "56d8593284d37ce03a2762dedc2390878ee6d271a0f1f100a5e245ad01080d6d"


class IndependentOpticsConformanceTests(unittest.TestCase):
    def test_default_grid_has_both_domains_and_expected_size(self):
        findings = conf.run_independent_conformance()
        self.assertEqual(len(findings), 12)
        self.assertEqual({f.domain for f in findings}, {"ASM", "STEERING"})

    def test_default_grid_independently_agrees(self):
        findings = conf.run_independent_conformance()
        self.assertTrue(all(f.within_tolerance for f in findings))
        self.assertTrue(all(f.class_agreement for f in findings))

    def test_asm_grid_contains_propagating_and_evanescent_cases(self):
        results = [conf.independent_asm_transfer(case)[1] for case in conf.default_asm_grid()]
        self.assertIn(True, results)
        self.assertIn(False, results)

    def test_cutoff_side_classification_is_fail_closed(self):
        wavelength = 532e-9
        cutoff = 1.0 / wavelength
        below = conf.independent_asm_transfer(conf.ASMConformanceCase(0.99 * cutoff, 0.0, 0.03, wavelength))
        above = conf.independent_asm_transfer(conf.ASMConformanceCase(1.01 * cutoff, 0.0, 0.03, wavelength))
        self.assertTrue(below[1])
        self.assertFalse(above[1])
        self.assertEqual(above[0], 0j)

    def test_phase_conformance_uses_circular_error(self):
        self.assertAlmostEqual(conf.circular_phase_error(3.1415926535, -3.1415926535), 0.0, places=8)

    def test_steering_formula_invalid_eye_distance_rejects(self):
        case = dataclasses.replace(conf.default_steering_grid()[0], eye_z_m=0.0)
        with self.assertRaises(ValueError):
            conf.independent_phase_steering(case)

    def test_tightened_tolerance_can_falsify_if_below_float_noise(self):
        findings = conf.run_independent_conformance(complex_tolerance=1e-30, phase_tolerance_radians=1e-30)
        self.assertTrue(any(not f.within_tolerance for f in findings))

    def test_receipt_requires_exactly_two_distinct_parents(self):
        findings = conf.run_independent_conformance()
        with self.assertRaises(ValueError):
            conf.build_conformance_receipt(
                parent_artifact_ids=(PARENTS[0], PARENTS[0]),
                imported_source_sha256=SOURCE_SHA,
                findings=findings,
            )

    def test_receipt_is_tamper_evident_and_nonauthorizing(self):
        findings = conf.run_independent_conformance()
        receipt = conf.build_conformance_receipt(
            parent_artifact_ids=PARENTS,
            imported_source_sha256=SOURCE_SHA,
            findings=findings,
        )
        self.assertTrue(receipt["software_independent_conformance_pass"])
        self.assertTrue(conf.verify_conformance_receipt(receipt))
        self.assertTrue(all(v is False for v in receipt["claim_ceiling"].values()))
        tampered = dict(receipt)
        tampered["software_independent_conformance_pass"] = False
        self.assertFalse(conf.verify_conformance_receipt(tampered))


if __name__ == "__main__":
    unittest.main()
