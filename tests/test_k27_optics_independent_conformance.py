from pathlib import Path
import dataclasses
import hashlib
import inspect
import json
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_optics_independent_conformance as conf


class IndependentOpticsConformanceTests(unittest.TestCase):
    def test_default_grid_has_both_domains_and_expected_size(self):
        findings = conf.run_independent_conformance()
        self.assertEqual(len(findings), 12)
        self.assertEqual({f.domain for f in findings}, {"ASM", "STEERING"})

    def test_default_grid_independently_agrees(self):
        findings = conf.run_independent_conformance()
        self.assertTrue(all(f.within_tolerance for f in findings))
        self.assertTrue(all(f.class_agreement for f in findings))

    def test_cutoff_side_classification_is_fail_closed(self):
        wavelength = 532e-9
        cutoff = 1.0 / wavelength
        below = conf.independent_asm_transfer(conf.ASMConformanceCase(0.99*cutoff, 0, 0.03, wavelength))
        above = conf.independent_asm_transfer(conf.ASMConformanceCase(1.01*cutoff, 0, 0.03, wavelength))
        self.assertTrue(below[1])
        self.assertFalse(above[1])
        self.assertEqual(above[0], 0j)

    def test_phase_conformance_uses_circular_error(self):
        self.assertAlmostEqual(conf.circular_phase_error(3.1415926535, -3.1415926535), 0.0, places=8)

    def test_tightened_noncanonical_tolerance_can_falsify(self):
        findings = conf.run_independent_conformance(
            complex_tolerance=1e-30, phase_tolerance_radians=1e-30
        )
        self.assertTrue(any(not f.within_tolerance for f in findings))

    def test_canonical_receipt_builder_has_zero_caller_inputs(self):
        self.assertEqual(list(inspect.signature(conf.build_conformance_receipt).parameters), [])
        receipt = conf.build_conformance_receipt()
        self.assertEqual(tuple(receipt["parent_artifact_ids"]), conf.CANONICAL_PARENT_ARTIFACT_IDS)
        self.assertEqual(receipt["imported_source_sha256"], conf.IMPORTED_SOURCE_SHA256)
        self.assertFalse(receipt["caller_findings_accepted"])
        self.assertFalse(receipt["caller_source_sha_accepted"])
        self.assertFalse(receipt["caller_parent_ids_accepted"])

    def test_hash_valid_fabricated_all_green_findings_cannot_mint_pass(self):
        receipt = dict(conf.build_conformance_receipt())
        receipt["findings"] = [{
            "domain": "ASM",
            "case_index": 999,
            "class_agreement": True,
            "numeric_error": 0.0,
            "within_tolerance": True,
        }]
        payload = {k:v for k,v in receipt.items() if k != "receipt_sha256"}
        receipt["receipt_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        self.assertFalse(conf.verify_conformance_receipt(receipt))

    def test_source_sha_cannot_be_overridden_even_with_fresh_hash(self):
        receipt = dict(conf.build_conformance_receipt())
        receipt["imported_source_sha256"] = "0"*64
        payload = {k:v for k,v in receipt.items() if k != "receipt_sha256"}
        receipt["receipt_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        self.assertFalse(conf.verify_conformance_receipt(receipt))

    def test_receipt_is_recomputable_and_nonauthorizing(self):
        receipt = conf.build_conformance_receipt()
        self.assertTrue(receipt["software_independent_conformance_pass"])
        self.assertTrue(conf.verify_conformance_receipt(receipt))
        self.assertTrue(all(v is False for v in receipt["claim_ceiling"].values()))

    def test_invalid_steering_geometry_rejects(self):
        case = dataclasses.replace(conf.default_steering_grid()[0], eye_z_m=0.0)
        with self.assertRaises(ValueError):
            conf.independent_phase_steering(case)


if __name__ == "__main__":
    unittest.main()
