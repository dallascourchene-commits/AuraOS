import unittest

from tools.spatial.eye_calibration_contract import (
    BinocularCalibrationV1,
    CameraIntrinsicsV1,
    IntrinsicsSource,
    IpdSource,
    assumed_population_ipd,
    nominal_intrinsics_from_horizontal_fov,
)
from tools.spatial.calibration_temporal_scope import (
    EXACT_PARENT_IDS,
    _digest,
    bind_calibration_temporal_scope,
    portable_calibration_temporal_scope_receipt,
    verify_parent_temporal_coordinate,
)


def calibrated_intrinsics():
    return CameraIntrinsicsV1(
        width_px=1920,
        height_px=1080,
        fx_px=1000.0,
        fy_px=1001.0,
        cx_px=959.5,
        cy_px=539.5,
        source=IntrinsicsSource.CALIBRATED,
        calibration_ref="camera-cal:fixture:g7",
        reprojection_rms_px=0.31,
        pixels_are_undistorted=True,
    )


def measured_ipd():
    return BinocularCalibrationV1(
        ipd_m=0.063,
        ipd_sigma_m=0.0004,
        midpoint_sigma_m=0.0003,
        source=IpdSource.MEASURED_USER,
        calibration_ref="ipd-cal:fixture:g4",
    )


def temporal_coordinate(**updates):
    payload = {
        "eye_pose_receipt_sha256": "1" * 64,
        "longitudinal_series_evidence_ref": "longitudinal:fixture",
        "longitudinal_series_digest": "2" * 64,
        "point_capture_time_ns": 200,
        "series_start_time_ns": 100,
        "series_end_time_ns": 300,
        "point_vs_series_relation": "DURING",
        "temporal_overlap": True,
        "eye_k27_coordinate": 5,
        "point_observation_was_gate_admissible": True,
        "point_observation_current_now_proven": False,
        "historical_series_current_now_proven": False,
        "shared_current_world_proven": False,
        "same_host_proven": False,
        "temporal_overlap_proves_causality": False,
        "operating_envelope_caused_eye_pose": False,
        "eye_pose_caused_operating_envelope": False,
        "calibrated_metric_eye_truth_proven": False,
        "physical_steering_authority": False,
        "performance_causality_proven": False,
        "producer_authenticated": False,
        "semantic_k27_authority_proven": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
        "schema": "AuraTemporalEvidenceScopeCoordinateV1",
    }
    payload.update(updates)
    return {**payload, "coordinate_digest": _digest(payload)}


def bind(**updates):
    kwargs = dict(
        intrinsics=calibrated_intrinsics(),
        binocular=measured_ipd(),
        temporal_coordinate=temporal_coordinate(),
        sensor_instance="camera:bench-a",
        sensor_runtime_generation="sensor-runtime:g5",
        calibration_generation="calibration:g9",
        calibration_observed_at_ns=150,
        max_calibration_age_ns=100,
        parent_artifact_ids=EXACT_PARENT_IDS,
    )
    kwargs.update(updates)
    return bind_calibration_temporal_scope(**kwargs)


class TestCalibrationTemporalScope(unittest.TestCase):
    def test_happy_path_is_declared_scope_not_current_truth(self):
        receipt = bind()
        self.assertTrue(receipt.declared_scope_admissible)
        self.assertTrue(receipt.metric_geometry_parent_eligible)
        self.assertEqual(receipt.calibration_age_ns, 50)
        for name in (
            "calibration_current_now_proven",
            "calibration_accuracy_at_use_time_proven",
            "sensor_matches_original_calibration_proven",
            "unchanged_physical_mount_proven",
            "same_physical_world_proven",
            "physical_gaze_accuracy_proven",
            "physical_display_effect_authority",
            "producer_authenticated",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            self.assertFalse(getattr(receipt, name))

    def test_population_ipd_cannot_enter_metric_scope(self):
        with self.assertRaises(ValueError):
            bind(binocular=assumed_population_ipd())

    def test_nominal_fov_cannot_enter_metric_scope(self):
        nominal = nominal_intrinsics_from_horizontal_fov(width_px=1920, height_px=1080, horizontal_fov_deg=90.0)
        with self.assertRaises(ValueError):
            bind(intrinsics=nominal)

    def test_future_calibration_rejected(self):
        with self.assertRaises(ValueError):
            bind(calibration_observed_at_ns=201)

    def test_expired_declared_scope_rejected(self):
        with self.assertRaises(ValueError):
            bind(calibration_observed_at_ns=99, max_calibration_age_ns=100)

    def test_incomplete_parent_temporal_schema_rejected(self):
        value = temporal_coordinate()
        value.pop("same_host_proven")
        unsigned = dict(value)
        unsigned.pop("coordinate_digest")
        value["coordinate_digest"] = _digest(unsigned)
        self.assertFalse(verify_parent_temporal_coordinate(value))
        with self.assertRaises(ValueError):
            bind(temporal_coordinate=value)

    def test_parent_temporal_tamper_rejected(self):
        value = temporal_coordinate()
        value["point_capture_time_ns"] = 201
        self.assertFalse(verify_parent_temporal_coordinate(value))
        with self.assertRaises(ValueError):
            bind(temporal_coordinate=value)

    def test_exact_two_parent_identity_required(self):
        with self.assertRaises(ValueError):
            bind(parent_artifact_ids=(EXACT_PARENT_IDS[0], EXACT_PARENT_IDS[0]))
        with self.assertRaises(ValueError):
            bind(parent_artifact_ids=(EXACT_PARENT_IDS[0], "PR999:foreign"))

    def test_sensor_generation_change_rebinds_receipt_without_proving_match(self):
        a = portable_calibration_temporal_scope_receipt(
            intrinsics=calibrated_intrinsics(), binocular=measured_ipd(), temporal_coordinate=temporal_coordinate(),
            sensor_instance="camera:bench-a", sensor_runtime_generation="sensor-runtime:g5",
            calibration_generation="calibration:g9", calibration_observed_at_ns=150,
            max_calibration_age_ns=100, parent_artifact_ids=EXACT_PARENT_IDS,
        )
        b = portable_calibration_temporal_scope_receipt(
            intrinsics=calibrated_intrinsics(), binocular=measured_ipd(), temporal_coordinate=temporal_coordinate(),
            sensor_instance="camera:bench-a", sensor_runtime_generation="sensor-runtime:g6",
            calibration_generation="calibration:g9", calibration_observed_at_ns=150,
            max_calibration_age_ns=100, parent_artifact_ids=EXACT_PARENT_IDS,
        )
        self.assertNotEqual(a["receipt_digest"], b["receipt_digest"])
        self.assertFalse(a["sensor_matches_original_calibration_proven"])
        self.assertFalse(b["sensor_matches_original_calibration_proven"])


if __name__ == "__main__":
    unittest.main()
