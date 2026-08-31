import math
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_optics_candidate_falsifier as optics


SOURCE_SHA = "56d8593284d37ce03a2762dedc2390878ee6d271a0f1f100a5e245ad01080d6d"


class K27OpticsCandidateFalsifierTests(unittest.TestCase):
    def test_k27_is_exact_27_cell_bijection(self):
        cells = {
            optics.k27_cell(x, y, z)
            for x in range(3)
            for y in range(3)
            for z in range(3)
        }
        self.assertEqual(cells, set(range(27)))

    def test_k27_rejects_bool_and_nonternary(self):
        with self.assertRaises(TypeError):
            optics.k27_cell(True, 0, 0)
        with self.assertRaises(ValueError):
            optics.k27_cell(3, 0, 0)

    def test_imported_shift_packing_is_not_k27_cell(self):
        packed = optics.imported_packed_coordinate(1, 1, 1)
        self.assertGreater(packed, 26)
        self.assertNotEqual(packed, optics.k27_cell(0, 0, 0))

    def test_phase_steering_is_explicitly_approximate_and_nonauthorizing(self):
        sample = optics.phase_steering_sample(
            base_phase_radians=0.1,
            sample_x_m=1e-4,
            sample_y_m=-2e-4,
            eye_x_m=0.02,
            eye_y_m=0.005,
            eye_z_m=0.35,
            wavelength_m=532e-9,
        )
        self.assertGreaterEqual(sample.phase_radians, -math.pi)
        self.assertLess(sample.phase_radians, math.pi)
        self.assertFalse(sample.exact_scene_unbinding_proven)
        self.assertFalse(sample.varifocal_correctness_proven)
        self.assertFalse(sample.hardware_latency_proven)

    def test_asm_propagating_mode_has_unit_transfer_but_no_system_claim(self):
        sample = optics.angular_spectrum_transfer(
            fx_cycles_per_m=1000.0,
            fy_cycles_per_m=2000.0,
            z_m=0.03,
            wavelength_m=532e-9,
        )
        self.assertTrue(sample.propagating)
        self.assertAlmostEqual(sample.transfer_magnitude, 1.0, places=12)
        self.assertFalse(sample.energy_conservation_proven)
        self.assertFalse(sample.speckle_free_proven)

    def test_asm_evanescent_mode_is_bandlimited(self):
        sample = optics.angular_spectrum_transfer(
            fx_cycles_per_m=2.0 / 532e-9,
            fy_cycles_per_m=0.0,
            z_m=0.03,
            wavelength_m=532e-9,
        )
        self.assertFalse(sample.propagating)
        self.assertEqual(sample.transfer, 0j)
        self.assertEqual(sample.transfer_magnitude, 0.0)

    def test_candidate_findings_reject_unearned_claims(self):
        findings = {f.key: f for f in optics.imported_candidate_findings()}
        for key in (
            "ENERGY_CONSERVATION_PREVENTS_COHERENT_SPECKLE",
            "ZERO_FORWARD_LIGHT_LEAKAGE_OR_100_PERCENT_PRIVATE_OVERLAY_PROVEN",
            "DISPLAY_DEPLOYMENT_READY",
            "MONOCULAR_ASSUMED_IPD_DEPTH_IS_METRIC_EYE_POSE",
        ):
            self.assertIn(key, findings)
            self.assertFalse(findings[key].admitted)

    def test_receipt_is_deterministic_source_bound_and_closed(self):
        refs_a = ("paper-b", "paper-a", "paper-a")
        refs_b = ("paper-a", "paper-b")
        receipt_a = optics.build_import_receipt(
            imported_source_sha256=SOURCE_SHA,
            external_evidence_refs=refs_a,
        )
        receipt_b = optics.build_import_receipt(
            imported_source_sha256=SOURCE_SHA,
            external_evidence_refs=refs_b,
        )
        self.assertEqual(receipt_a, receipt_b)
        self.assertTrue(optics.verify_import_receipt(receipt_a))

        widened = dict(receipt_a)
        widened["deployment_override"] = True
        self.assertFalse(optics.verify_import_receipt(widened))

    def test_receipt_ceiling_remains_all_false(self):
        receipt = optics.build_import_receipt(imported_source_sha256=SOURCE_SHA)
        self.assertTrue(receipt["claim_ceiling"])
        self.assertTrue(all(value is False for value in receipt["claim_ceiling"].values()))

        tampered = dict(receipt)
        ceiling = dict(tampered["claim_ceiling"])
        ceiling["deployment_ready"] = True
        tampered["claim_ceiling"] = ceiling
        self.assertFalse(optics.verify_import_receipt(tampered))


if __name__ == "__main__":
    unittest.main()
