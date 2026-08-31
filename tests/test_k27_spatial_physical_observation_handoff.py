import unittest

from tools.k27_spatial_physical_observation_handoff import (
    EXACT_PARENT_IDS,
    PARENT_TEMPORAL,
    SpatialPhysicalObservationAttempt,
    SpatialPhysicalObservationRequest,
    build_receipt,
    join_spatial_physical_observation,
)

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


def request(**kw):
    base = dict(
        temporal_coordinate_digest=D0,
        phase_mask_artifact_digest=D1,
        display_device_instance="slm:bench-a:serial-opaque",
        display_runtime_generation="display-runtime:g7",
        calibration_evidence_ref="calibration-evidence:pending-independent-owner",
        optical_bench_setup_digest=D2,
        requested_metrics=("speckle_contrast", "forward_leakage_ratio"),
        max_wall_ms=50,
        max_capture_bytes=4096,
        effect_admission_ref="effect-admission:required",
        parent_artifact_ids=EXACT_PARENT_IDS,
    )
    base.update(kw)
    return SpatialPhysicalObservationRequest(**base)


def attempt(req, **kw):
    base = dict(
        request_digest=req.request_digest,
        observer_instance="observer:camera-a",
        observer_runtime_generation="observer-runtime:g3",
        started_at_unix_ns=1_000_000_000,
        ended_at_unix_ns=1_010_000_000,
        observed_display_device_instance=req.display_device_instance,
        observed_display_runtime_generation=req.display_runtime_generation,
        observed_calibration_evidence_ref=req.calibration_evidence_ref,
        observed_phase_mask_artifact_digest=req.phase_mask_artifact_digest,
        observed_optical_bench_setup_digest=req.optical_bench_setup_digest,
        raw_capture_digest=D3,
        raw_capture_bytes=1024,
        measurement_artifact_digest=D4,
        reported_metrics={"speckle_contrast": 0.42, "forward_leakage_ratio": 0.01},
        process_exit_code=0,
    )
    base.update(kw)
    return SpatialPhysicalObservationAttempt(**base)


class TestSpatialPhysicalObservationHandoff(unittest.TestCase):
    def test_happy_path_is_integrity_only(self):
        req = request()
        joined = join_spatial_physical_observation(req, attempt(req))
        self.assertTrue(joined["integrity_joined"])
        self.assertTrue(joined["reported_measurement_present"])
        for key in (
            "producer_authenticated",
            "physical_measurement_attested",
            "optical_truth_proven",
            "privacy_proven",
            "optical_safety_proven",
            "deployment_ready",
            "effect_authority_proven",
            "gate10_promoted",
            "native_transformer_kv_accessed",
            "k27_semantic_authority",
        ):
            self.assertFalse(joined[key])

    def test_exact_two_parents_required(self):
        with self.assertRaises(ValueError):
            request(parent_artifact_ids=(PARENT_TEMPORAL,))
        with self.assertRaises(ValueError):
            request(parent_artifact_ids=(PARENT_TEMPORAL, PARENT_TEMPORAL))
        with self.assertRaises(ValueError):
            request(parent_artifact_ids=(PARENT_TEMPORAL, "PR999:foreign"))

    def test_unsupported_metric_rejected(self):
        with self.assertRaises(ValueError):
            request(requested_metrics=("speckle_contrast", "optical_safety"))

    def test_request_digest_mismatch_rejected(self):
        req = request()
        with self.assertRaises(ValueError):
            join_spatial_physical_observation(req, attempt(req, request_digest="f" * 64))

    def test_display_generation_aba_rejected(self):
        req = request()
        with self.assertRaises(ValueError):
            join_spatial_physical_observation(req, attempt(req, observed_display_runtime_generation="display-runtime:g8"))

    def test_calibration_or_phase_substitution_rejected(self):
        req = request()
        with self.assertRaises(ValueError):
            join_spatial_physical_observation(req, attempt(req, observed_calibration_evidence_ref="calibration:foreign"))
        with self.assertRaises(ValueError):
            join_spatial_physical_observation(req, attempt(req, observed_phase_mask_artifact_digest="e" * 64))

    def test_budget_escape_rejected(self):
        req = request()
        with self.assertRaises(ValueError):
            join_spatial_physical_observation(req, attempt(req, raw_capture_bytes=4097))
        with self.assertRaises(ValueError):
            join_spatial_physical_observation(req, attempt(req, ended_at_unix_ns=1_100_000_001))

    def test_metric_set_must_match_exactly(self):
        req = request()
        with self.assertRaises(ValueError):
            join_spatial_physical_observation(req, attempt(req, reported_metrics={"speckle_contrast": 0.4}))

    def test_failed_attempt_cannot_be_relabelled_successful(self):
        req = request()
        with self.assertRaises(ValueError):
            join_spatial_physical_observation(req, attempt(req, process_exit_code=2))

    def test_receipt_deterministic_and_tamper_sensitive(self):
        req = request()
        a = build_receipt(req, attempt(req))
        b = build_receipt(req, attempt(req))
        self.assertEqual(a["receipt_digest"], b["receipt_digest"])
        c = build_receipt(req, attempt(req, reported_metrics={"speckle_contrast": 0.43, "forward_leakage_ratio": 0.01}))
        self.assertNotEqual(a["receipt_digest"], c["receipt_digest"])

    def test_temporal_coordinate_is_bound_not_currentness_authority(self):
        req = request()
        joined = join_spatial_physical_observation(req, attempt(req))
        self.assertTrue(joined["temporal_coordinate_bound"])
        self.assertFalse(joined["physical_measurement_attested"])


if __name__ == "__main__":
    unittest.main()
