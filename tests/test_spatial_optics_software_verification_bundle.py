from dataclasses import asdict, replace
import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_optics_independent_conformance as conf
from spatial import optical_invariant_witness as inv
import spatial_optics_software_verification_bundle as bundle


def invariant_receipt():
    return inv.measure_invariants(
        inv.deterministic_fixture(),
        dx_m=8e-6, dy_m=8e-6, wavelength_m=532e-9, distance_m=0.03,
    )


def resign_invariant(receipt):
    unsigned = replace(receipt, receipt_sha256="")
    digest = hashlib.sha256(
        json.dumps(asdict(unsigned), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return replace(unsigned, receipt_sha256=digest)


def conformance_receipt():
    return conf.build_conformance_receipt()


def rehash(value):
    payload = {k: v for k, v in value.items() if k != "receipt_sha256"}
    value["receipt_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return value


class SpatialOpticsSoftwareVerificationBundleV2Tests(unittest.TestCase):
    def test_two_current_software_lanes_bundle_without_physical_promotion(self):
        result = bundle.build_software_verification_bundle(
            invariant_receipt(), conformance_receipt()
        )
        self.assertEqual(result.verification_lanes, bundle.LANES)
        self.assertTrue(result.field_invariant_measurement_pass)
        self.assertTrue(result.independent_formulation_conformance_pass)
        self.assertTrue(result.conformance_producer_traversed)
        self.assertFalse(result.historical_conformance_green_is_current_proof)
        self.assertEqual(bundle.CONFORMANCE_SEMANTIC_GENERATION, result.conformance_semantic_generation)
        self.assertEqual(bundle.CONFORMANCE_OWNER_BLOB, result.conformance_owner_blob)
        self.assertFalse(result.same_test_object_proven)
        self.assertFalse(result.physical_optics_validation_proven)
        self.assertFalse(result.effect_authority_proven)

    def test_rehashed_fake_all_green_conformance_receipt_is_rejected(self):
        fake = dict(conformance_receipt())
        fake["findings"] = [{
            "domain": "ASM", "case_index": 999, "class_agreement": True,
            "numeric_error": 0.0, "within_tolerance": True,
        }]
        rehash(fake)
        self.assertFalse(conf.verify_conformance_receipt(fake))
        with self.assertRaisesRegex(bundle.VerificationBundleError, "INVALID_OR_STALE_CONFORMANCE_RECEIPT"):
            bundle.build_software_verification_bundle(invariant_receipt(), fake)

    def test_caller_override_widening_is_rejected_even_if_rehashed(self):
        fake = dict(conformance_receipt())
        fake["caller_findings_accepted"] = True
        rehash(fake)
        with self.assertRaisesRegex(bundle.VerificationBundleError, "INVALID_OR_STALE_CONFORMANCE_RECEIPT"):
            bundle.build_software_verification_bundle(invariant_receipt(), fake)

    def test_field_lane_must_still_be_closed(self):
        weakened = resign_invariant(replace(invariant_receipt(), power_conservation_measured=False))
        with self.assertRaisesRegex(bundle.VerificationBundleError, "FIELD_INVARIANT_LANE_NOT_CLOSED"):
            bundle.build_software_verification_bundle(weakened, conformance_receipt())

    def test_claim_ceiling_remains_closed(self):
        result = bundle.build_software_verification_bundle(invariant_receipt(), conformance_receipt())
        for value in (
            result.same_test_object_proven,
            result.shared_implementation_generation_proven,
            result.shared_fixture_identity_proven,
            result.shared_sampling_grid_identity_proven,
            result.shared_source_identity_proven,
            result.physical_optics_validation_proven,
            result.hardware_performance_proven,
            result.optical_safety_proven,
            result.deployment_ready,
            result.semantic_k27_authority_proven,
            result.effect_authority_proven,
            result.gate10_promoted,
            result.native_transformer_kv_accessed,
        ):
            self.assertFalse(value)

    def test_reopen_contract_survives_rebind(self):
        result = bundle.build_software_verification_bundle(invariant_receipt(), conformance_receipt())
        self.assertEqual(result.reopen_requirements, bundle.REOPEN_REQUIREMENTS)

    def test_bundle_identity_binds_repaired_conformance_generation(self):
        a = bundle.build_software_verification_bundle(invariant_receipt(), conformance_receipt())
        b = bundle.build_software_verification_bundle(invariant_receipt(), conformance_receipt())
        self.assertEqual(a.bundle_digest, b.bundle_digest)
        self.assertIn("PR620:5a5878eace5974ff6a3f1dbf676fed8295bb457a", a.conformance_semantic_generation)
        self.assertTrue(a.evidence_ref.endswith(a.bundle_digest))

    def test_public_builder_exposes_only_two_evidence_inputs(self):
        params = tuple(inspect.signature(bundle.build_software_verification_bundle).parameters)
        self.assertEqual(params, ("invariant_receipt", "conformance_receipt"))


if __name__ == "__main__":
    unittest.main()
