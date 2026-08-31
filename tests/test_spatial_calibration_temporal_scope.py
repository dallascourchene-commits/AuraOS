import hashlib
import json
import unittest

from tools.spatial.eye_calibration_contract import (
    BinocularCalibrationV2,
    CalibrationQualityPolicyV1,
    CameraCalibrationDatasetV1,
    CameraCalibrationSampleV1,
    CameraIntrinsicsV2,
    CoordinateSpace,
    IpdMeasurementDatasetV1,
    produce_camera_calibration_evidence,
    produce_ipd_calibration_evidence,
)
from tools.spatial.calibration_temporal_scope import (
    EXACT_PARENT_IDS,
    bind_calibration_temporal_scope,
    portable_calibration_temporal_scope_receipt,
    public_inputs,
)
from tests.test_temporal_evidence_scope_coordinate import eye_receipt, series
from tools.temporal_evidence_scope_coordinate import (
    portable_temporal_evidence_scope_receipt,
    verify_temporal_evidence_scope_coordinate,
)


def calibrated_pair():
    policy = CalibrationQualityPolicyV1(
        policy_generation="scope-policy-v1",
        min_camera_samples=6,
        max_camera_reprojection_rms_px=1.0,
        min_ipd_samples=3,
        max_ipd_sample_sigma_m=0.0025,
    )
    fx, fy, cx, cy = 1100.0, 1098.0, 959.5, 539.5
    points = ((-0.3, -0.2), (-0.1, 0.25), (0.0, -0.1), (0.15, 0.1), (0.3, -0.25), (0.4, 0.3))
    camera_ds = CameraCalibrationDatasetV1(
        sensor_id="camera:bench-a",
        sensor_generation="camera-runtime:g5",
        calibration_generation="camera-cal:g9",
        width_px=1920,
        height_px=1080,
        coordinate_space=CoordinateSpace.UNDISTORTED_PINHOLE_PIXELS_V1,
        samples=tuple(CameraCalibrationSampleV1(x, y, fx*x+cx, fy*y+cy) for x, y in points),
    )
    ipd_ds = IpdMeasurementDatasetV1(
        sensor_id="ipd-tool:a",
        sensor_generation="ipd-runtime:g4",
        calibration_generation="ipd-cal:g4",
        coordinate_space="HEAD_LOCAL_METERS_V1",
        ipd_samples_m=(0.0628, 0.0630, 0.0632),
        midpoint_sigma_m=0.0003,
    )
    return (
        CameraIntrinsicsV2(produce_camera_calibration_evidence(camera_ds, policy)),
        BinocularCalibrationV2(produce_ipd_calibration_evidence(ipd_ds, policy)),
    )


def temporal():
    return portable_temporal_evidence_scope_receipt(
        eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000),
        longitudinal_series=series(),
    )


def rehash(value):
    payload = {k: v for k, v in value.items() if k != "coordinate_digest"}
    value["coordinate_digest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return value


class TestCalibrationTemporalScopeV2(unittest.TestCase):
    def test_current_portable_temporal_parent_preserves_hold(self):
        intrinsics, binocular = calibrated_pair()
        t = temporal()
        out = bind_calibration_temporal_scope(
            intrinsics=intrinsics,
            binocular=binocular,
            temporal_coordinate=t,
            declared_calibration_time_ns=t["point_capture_time_ns"] - 50,
            max_declared_calibration_age_ns=100,
        )
        self.assertTrue(out.software_scope_candidate)
        self.assertFalse(out.point_temporal_admissible)
        self.assertFalse(out.declared_scope_admissible)
        self.assertEqual("POINT_EVIDENCE_NOT_AUTHENTICATED", out.hold_reason)
        self.assertTrue(out.calibration_producer_traversed)
        self.assertTrue(out.ipd_producer_traversed)
        self.assertFalse(out.physical_use_admissible)
        self.assertFalse(out.physical_calibration_producer_authenticated)

    def test_sensor_and_generation_identity_are_derived_from_parent_evidence(self):
        intrinsics, binocular = calibrated_pair()
        t = temporal()
        out = bind_calibration_temporal_scope(
            intrinsics=intrinsics,
            binocular=binocular,
            temporal_coordinate=t,
            declared_calibration_time_ns=t["point_capture_time_ns"] - 10,
            max_declared_calibration_age_ns=100,
        )
        self.assertEqual("camera:bench-a", out.camera_sensor_id)
        self.assertEqual("camera-runtime:g5", out.camera_sensor_generation)
        self.assertEqual("camera-cal:g9", out.camera_calibration_generation)
        self.assertEqual("ipd-tool:a", out.ipd_sensor_id)
        self.assertEqual("ipd-runtime:g4", out.ipd_sensor_generation)
        self.assertEqual("ipd-cal:g4", out.ipd_calibration_generation)

    def test_freshly_rehashed_positive_temporal_parent_is_rejected(self):
        intrinsics, binocular = calibrated_pair()
        t = temporal()
        t["point_observation_temporal_admissible"] = True
        t["point_vs_series_relation"] = "DURING"
        t["temporal_overlap"] = True
        t["hold_reason"] = None
        rehash(t)
        self.assertFalse(verify_temporal_evidence_scope_coordinate(t))
        with self.assertRaises(ValueError):
            bind_calibration_temporal_scope(
                intrinsics=intrinsics,
                binocular=binocular,
                temporal_coordinate=t,
                declared_calibration_time_ns=100,
                max_declared_calibration_age_ns=100,
            )

    def test_forged_camera_result_fields_fail_parent_producer_replay(self):
        from dataclasses import replace
        intrinsics, binocular = calibrated_pair()
        forged = CameraIntrinsicsV2(replace(intrinsics.evidence, fx_px=intrinsics.evidence.fx_px + 10.0))
        t = temporal()
        with self.assertRaises(ValueError):
            bind_calibration_temporal_scope(
                intrinsics=forged,
                binocular=binocular,
                temporal_coordinate=t,
                declared_calibration_time_ns=t["point_capture_time_ns"] - 50,
                max_declared_calibration_age_ns=100,
            )

    def test_declared_calibration_time_is_not_authenticated(self):
        intrinsics, binocular = calibrated_pair()
        t = temporal()
        out = bind_calibration_temporal_scope(
            intrinsics=intrinsics,
            binocular=binocular,
            temporal_coordinate=t,
            declared_calibration_time_ns=t["point_capture_time_ns"] - 50,
            max_declared_calibration_age_ns=100,
        )
        self.assertFalse(out.calibration_time_authenticated)
        self.assertFalse(out.calibration_current_now_proven)
        self.assertFalse(out.calibration_accuracy_at_use_time_proven)

    def test_future_and_expired_declared_scope_fail_closed(self):
        intrinsics, binocular = calibrated_pair()
        t = temporal()
        use = t["point_capture_time_ns"]
        with self.assertRaises(ValueError):
            bind_calibration_temporal_scope(
                intrinsics=intrinsics, binocular=binocular, temporal_coordinate=t,
                declared_calibration_time_ns=use + 1, max_declared_calibration_age_ns=100,
            )
        with self.assertRaises(ValueError):
            bind_calibration_temporal_scope(
                intrinsics=intrinsics, binocular=binocular, temporal_coordinate=t,
                declared_calibration_time_ns=use - 101, max_declared_calibration_age_ns=100,
            )

    def test_public_boundary_has_no_caller_sensor_or_generation_override(self):
        self.assertEqual(
            (
                "intrinsics",
                "binocular",
                "temporal_coordinate",
                "declared_calibration_time_ns",
                "max_declared_calibration_age_ns",
                "parent_artifact_ids",
            ),
            public_inputs(),
        )

    def test_portable_receipt_is_deterministic_and_exact_parent_bound(self):
        intrinsics, binocular = calibrated_pair()
        t = temporal()
        kwargs = dict(
            intrinsics=intrinsics,
            binocular=binocular,
            temporal_coordinate=t,
            declared_calibration_time_ns=t["point_capture_time_ns"] - 50,
            max_declared_calibration_age_ns=100,
            parent_artifact_ids=EXACT_PARENT_IDS,
        )
        a = portable_calibration_temporal_scope_receipt(**kwargs)
        b = portable_calibration_temporal_scope_receipt(**kwargs)
        self.assertEqual(a["receipt_digest"], b["receipt_digest"])
        self.assertEqual(EXACT_PARENT_IDS, tuple(a["parent_artifact_ids"]))

if __name__ == "__main__":
    unittest.main()
