from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from tools.k27_eye_pose_observation_contract import (
    CameraCalibration,
    IrisFrameObservation,
    build_eye_pose_receipt,
    estimate_eye_pose_from_assumed_ipd,
    gate_eye_pose_for_steering,
)
from tools.test_thinkpad_longitudinal_envelope_series import ThinkPadLongitudinalEnvelopeSeriesTests
from tools.temporal_evidence_scope_coordinate import (
    TemporalEvidenceScopeError,
    bind_temporal_evidence_scope,
    portable_temporal_evidence_scope_receipt,
    verify_temporal_evidence_scope_coordinate,
)

PARENTS = ("eye-source-artifact", "common-cut-artifact")


def calibration() -> CameraCalibration:
    return CameraCalibration(
        sensor_instance_id="camera-instance-A",
        runtime_generation="boot-17",
        calibration_generation="cal-4",
        fx_px=1000.0,
        fy_px=1000.0,
        cx_px=640.0,
        cy_px=360.0,
        image_width_px=1280,
        image_height_px=720,
    )


def eye_receipt(capture_ns: int, *, admissible: bool = True):
    c = calibration()
    f = IrisFrameObservation(
        sensor_instance_id="camera-instance-A",
        runtime_generation="boot-17",
        frame_id=f"frame-{capture_ns}",
        capture_time_ns=capture_ns,
        landmark_model_generation="face-landmarker-v7",
        tracking_confidence=0.98,
        left_iris_x_px=600.0,
        left_iris_y_px=360.0,
        right_iris_x_px=680.0,
        right_iris_y_px=360.0,
    )
    estimate = estimate_eye_pose_from_assumed_ipd(frame=f, calibration=c, assumed_ipd_m=0.064)
    now = capture_ns + (100_000_000 if admissible else 300_000_000)
    gate = gate_eye_pose_for_steering(
        frame=f,
        calibration=c,
        now_ns=now,
        max_age_ns=200_000_000,
        expected_sensor_instance_id="camera-instance-A",
        expected_runtime_generation="boot-17",
        expected_calibration_generation="cal-4",
        expected_landmark_model_generation="face-landmarker-v7",
        minimum_tracking_confidence=0.9,
    )
    return build_eye_pose_receipt(
        frame=f,
        calibration=c,
        estimate=estimate,
        gate=gate,
        k27_coordinate=13,
        parent_artifact_ids=PARENTS,
    )


def series():
    return ThinkPadLongitudinalEnvelopeSeriesTests().build()


class TemporalEvidenceScopeCoordinateTests(unittest.TestCase):
    def test_point_before_historical_series_is_classified_without_currentness_promotion(self):
        out = bind_temporal_evidence_scope(
            eye_pose_receipt=eye_receipt(1_788_155_400_000_000_000),
            longitudinal_series=series(),
        )
        self.assertEqual("BEFORE", out.point_vs_series_relation)
        self.assertFalse(out.temporal_overlap)
        self.assertFalse(out.shared_current_world_proven)
        self.assertFalse(out.effect_authority_proven)

    def test_point_during_historical_series_overlap_is_not_shared_current_world_or_causality(self):
        out = bind_temporal_evidence_scope(
            eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000),
            longitudinal_series=series(),
        )
        self.assertEqual("DURING", out.point_vs_series_relation)
        self.assertTrue(out.temporal_overlap)
        self.assertTrue(out.point_observation_was_gate_admissible)
        self.assertFalse(out.point_observation_current_now_proven)
        self.assertFalse(out.historical_series_current_now_proven)
        self.assertFalse(out.shared_current_world_proven)
        self.assertFalse(out.same_host_proven)
        self.assertFalse(out.temporal_overlap_proves_causality)
        self.assertFalse(out.operating_envelope_caused_eye_pose)
        self.assertFalse(out.eye_pose_caused_operating_envelope)
        self.assertFalse(out.physical_steering_authority)

    def test_point_after_historical_series_is_classified(self):
        out = bind_temporal_evidence_scope(
            eye_pose_receipt=eye_receipt(1_788_157_800_000_000_000),
            longitudinal_series=series(),
        )
        self.assertEqual("AFTER", out.point_vs_series_relation)
        self.assertFalse(out.temporal_overlap)

    def test_inadmissible_eye_common_cut_fails_before_temporal_relation_credit(self):
        with self.assertRaisesRegex(TemporalEvidenceScopeError, "EYE_POSE_GATE_NOT_ADMISSIBLE"):
            bind_temporal_evidence_scope(
                eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000, admissible=False),
                longitudinal_series=series(),
            )

    def test_longitudinal_current_now_widening_fails_before_composition(self):
        widened = replace(series(), current_now_proven=True)
        with self.assertRaisesRegex(TemporalEvidenceScopeError, "LONGITUDINAL_SERIES_CEILING_WIDENED"):
            bind_temporal_evidence_scope(
                eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000),
                longitudinal_series=widened,
            )

    def test_portable_coordinate_is_tamper_evident_and_nonauthorizing(self):
        receipt = portable_temporal_evidence_scope_receipt(
            eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000),
            longitudinal_series=series(),
        )
        self.assertTrue(verify_temporal_evidence_scope_coordinate(receipt))
        tampered = dict(receipt)
        tampered["point_vs_series_relation"] = "AFTER"
        self.assertFalse(verify_temporal_evidence_scope_coordinate(tampered))
        self.assertFalse(receipt["semantic_k27_authority_proven"])
        self.assertFalse(receipt["native_private_transformer_kv_accessed"])
        self.assertFalse(receipt["gate10_promoted"])

    def test_public_builder_has_only_exact_evidence_objects(self):
        self.assertEqual(
            ["eye_pose_receipt", "longitudinal_series"],
            list(inspect.signature(bind_temporal_evidence_scope).parameters),
        )

    def test_coordinate_identity_is_deterministic(self):
        eye = eye_receipt(1_788_156_600_000_000_000)
        hist = series()
        a = bind_temporal_evidence_scope(eye_pose_receipt=eye, longitudinal_series=hist)
        b = bind_temporal_evidence_scope(eye_pose_receipt=eye, longitudinal_series=hist)
        self.assertEqual(a.coordinate_digest, b.coordinate_digest)
        self.assertEqual(a.evidence_ref, b.evidence_ref)


if __name__ == "__main__":
    unittest.main()
