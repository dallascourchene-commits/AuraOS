from dataclasses import asdict, replace
import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest

# Hosted W3 retrigger marker: no semantic behavior change; forces exact-head reproof.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_optics_independent_conformance as conf
from spatial import optical_invariant_witness as inv
import spatial_optics_software_verification_bundle as bundle

PARENTS = ("artifact-a", "artifact-b")
SOURCE_SHA = bundle.EXPECTED_IMPORTED_SOURCE_SHA256


def invariant_receipt():
    return inv.measure_invariants(
        inv.deterministic_fixture(),
        dx_m=8e-6,
        dy_m=8e-6,
        wavelength_m=532e-9,
        distance_m=0.03,
    )


def resign_invariant(receipt):
    unsigned = replace(receipt, receipt_sha256="")
    digest = hashlib.sha256(
        json.dumps(asdict(unsigned), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return replace(unsigned, receipt_sha256=digest)


def conformance_receipt(*, source_sha=SOURCE_SHA, tolerance=None):
    if tolerance is None:
        findings = conf.run_independent_conformance()
    else:
        findings = conf.run_independent_conformance(
            complex_tolerance=tolerance,
            phase_tolerance_radians=tolerance,
        )
    return conf.build_conformance_receipt(
        parent_artifact_ids=PARENTS,
        imported_source_sha256=source_sha,
        findings=findings,
    )


class SpatialOpticsSoftwareVerificationBundleTests(unittest.TestCase):
    def test_two_green_lanes_bundle_without_same_test_object_promotion(self):
        result = bundle.build_software_verification_bundle(
            invariant_receipt(), conformance_receipt()
        )
        self.assertEqual(result.verification_lanes, bundle.LANES)
        self.assertTrue(result.field_invariant_measurement_pass)
        self.assertTrue(result.independent_formulation_conformance_pass)
        self.assertTrue(result.verification_modes_distinct)
        self.assertFalse(result.same_test_object_proven)
        self.assertFalse(result.shared_implementation_generation_proven)
        self.assertFalse(result.shared_fixture_identity_proven)
        self.assertFalse(result.shared_sampling_grid_identity_proven)
        self.assertFalse(result.shared_source_identity_proven)

    def test_bundle_never_promotes_software_verification_to_physical_validation(self):
        result = bundle.build_software_verification_bundle(
            invariant_receipt(), conformance_receipt()
        )
        for value in (
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

    def test_missing_shared_identity_is_an_explicit_reopen_contract(self):
        result = bundle.build_software_verification_bundle(
            invariant_receipt(), conformance_receipt()
        )
        self.assertEqual(result.reopen_requirements, bundle.REOPEN_REQUIREMENTS)
        self.assertEqual(
            set(result.reopen_requirements),
            {
                "SHARED_IMPLEMENTATION_GENERATION",
                "EXACT_SHARED_FIXTURE_DIGEST",
                "EXACT_SHARED_SAMPLING_OR_GRID_DIGEST",
                "EXACT_SHARED_SOURCE_BINDING",
            },
        )

    def test_field_lane_must_be_closed_not_merely_well_formed(self):
        weakened = resign_invariant(
            replace(invariant_receipt(), power_conservation_measured=False)
        )
        with self.assertRaisesRegex(
            bundle.VerificationBundleError, "FIELD_INVARIANT_LANE_NOT_CLOSED"
        ):
            bundle.build_software_verification_bundle(weakened, conformance_receipt())

    def test_independent_lane_must_be_closed_not_merely_well_formed(self):
        failed = conformance_receipt(tolerance=1e-30)
        self.assertTrue(conf.verify_conformance_receipt(failed))
        self.assertFalse(failed["software_independent_conformance_pass"])
        with self.assertRaisesRegex(
            bundle.VerificationBundleError, "INDEPENDENT_CONFORMANCE_LANE_NOT_CLOSED"
        ):
            bundle.build_software_verification_bundle(invariant_receipt(), failed)

    def test_foreign_source_bound_conformance_receipt_fails_closed(self):
        foreign = conformance_receipt(source_sha="f" * 64)
        self.assertTrue(conf.verify_conformance_receipt(foreign))
        with self.assertRaisesRegex(
            bundle.VerificationBundleError, "CONFORMANCE_SOURCE_BINDING_MISMATCH"
        ):
            bundle.build_software_verification_bundle(invariant_receipt(), foreign)

    def test_tampered_invariant_receipt_fails_closed(self):
        original = invariant_receipt()
        tampered = replace(original, distance_m=original.distance_m + 0.001)
        with self.assertRaisesRegex(
            bundle.VerificationBundleError, "INVALID_FIELD_INVARIANT_RECEIPT"
        ):
            bundle.build_software_verification_bundle(tampered, conformance_receipt())

    def test_bundle_identity_is_deterministic_and_binds_both_receipts(self):
        a_inv = invariant_receipt()
        a_conf = conformance_receipt()
        first = bundle.build_software_verification_bundle(a_inv, a_conf)
        second = bundle.build_software_verification_bundle(a_inv, a_conf)
        self.assertEqual(first.bundle_digest, second.bundle_digest)
        self.assertEqual(first.invariant_receipt_sha256, a_inv.receipt_sha256)
        self.assertEqual(first.conformance_receipt_sha256, a_conf["receipt_sha256"])
        self.assertTrue(first.evidence_ref.endswith(first.bundle_digest))

    def test_public_builder_exposes_only_the_two_evidence_inputs(self):
        params = tuple(inspect.signature(bundle.build_software_verification_bundle).parameters)
        self.assertEqual(params, ("invariant_receipt", "conformance_receipt"))


if __name__ == "__main__":
    unittest.main()
