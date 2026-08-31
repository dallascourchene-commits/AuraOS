from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_eye_pose_observation_contract as eye


PARENTS = (
    "1l8FLO6a0ebJX1D4L2VP5PThii4P_vcGGrGMxBHYy_Ew",
    "1yesnrKTiuTS4laKhOQ_Qlp45PF1XN29ih0kK_0sNFxA",
)


def calibration(**overrides):
    values = dict(
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
    values.update(overrides)
    return eye.CameraCalibration(**values)


def frame(**overrides):
    values = dict(
        sensor_instance_id="camera-instance-A",
        runtime_generation="boot-17",
        frame_id="frame-100",
        capture_time_ns=1_000_000_000,
        landmark_model_generation="face-landmarker-v7",
        tracking_confidence=0.98,
        left_iris_x_px=600.0,
        left_iris_y_px=360.0,
        right_iris_x_px=680.0,
        right_iris_y_px=360.0,
    )
    values.update(overrides)
    return eye.IrisFrameObservation(**values)


class EyePoseObservationContractTests(unittest.TestCase):
    def test_assumed_ipd_geometry_is_estimate_not_metric_truth(self):
        estimate = eye.estimate_eye_pose_from_assumed_ipd(
            frame=frame(), calibration=calibration(), assumed_ipd_m=0.064
        )
        self.assertAlmostEqual(estimate.z_m, 0.8)
        self.assertAlmostEqual(estimate.x_m, 0.0)
        self.assertAlmostEqual(estimate.y_m, 0.0)
        self.assertEqual(estimate.pose_class, eye.POSE_CLASS)
        self.assertFalse(estimate.calibrated_metric_truth_proven)
        self.assertFalse(estimate.physical_steering_authority)

    def test_stale_frame_fails_closed(self):
        gate = eye.gate_eye_pose_for_steering(
            frame=frame(), calibration=calibration(), now_ns=1_200_000_001,
            max_age_ns=200_000_000, expected_sensor_instance_id="camera-instance-A",
            expected_runtime_generation="boot-17", expected_calibration_generation="cal-4",
            expected_landmark_model_generation="face-landmarker-v7",
            minimum_tracking_confidence=0.9,
        )
        self.assertFalse(gate.admissible)
        self.assertIn("FRAME_STALE_OR_FROM_FUTURE", gate.refusals)

    def test_sensor_aba_runtime_change_fails_common_cut(self):
        gate = eye.gate_eye_pose_for_steering(
            frame=frame(runtime_generation="boot-18"), calibration=calibration(),
            now_ns=1_100_000_000, max_age_ns=200_000_000,
            expected_sensor_instance_id="camera-instance-A",
            expected_runtime_generation="boot-17", expected_calibration_generation="cal-4",
            expected_landmark_model_generation="face-landmarker-v7",
            minimum_tracking_confidence=0.9,
        )
        self.assertFalse(gate.admissible)
        self.assertIn("SENSOR_RUNTIME_COMMON_CUT_MISMATCH", gate.refusals)

    def test_calibration_generation_movement_reopens_gate(self):
        gate = eye.gate_eye_pose_for_steering(
            frame=frame(), calibration=calibration(calibration_generation="cal-3"),
            now_ns=1_100_000_000, max_age_ns=200_000_000,
            expected_sensor_instance_id="camera-instance-A",
            expected_runtime_generation="boot-17", expected_calibration_generation="cal-4",
            expected_landmark_model_generation="face-landmarker-v7",
            minimum_tracking_confidence=0.9,
        )
        self.assertFalse(gate.admissible)
        self.assertIn("CALIBRATION_GENERATION_MISMATCH", gate.refusals)

    def test_landmark_model_generation_movement_reopens_gate(self):
        gate = eye.gate_eye_pose_for_steering(
            frame=frame(landmark_model_generation="face-landmarker-v8"), calibration=calibration(),
            now_ns=1_100_000_000, max_age_ns=200_000_000,
            expected_sensor_instance_id="camera-instance-A",
            expected_runtime_generation="boot-17", expected_calibration_generation="cal-4",
            expected_landmark_model_generation="face-landmarker-v7",
            minimum_tracking_confidence=0.9,
        )
        self.assertFalse(gate.admissible)
        self.assertIn("LANDMARK_MODEL_GENERATION_MISMATCH", gate.refusals)

    def test_low_tracking_confidence_fails_closed(self):
        gate = eye.gate_eye_pose_for_steering(
            frame=frame(tracking_confidence=0.4), calibration=calibration(),
            now_ns=1_100_000_000, max_age_ns=200_000_000,
            expected_sensor_instance_id="camera-instance-A",
            expected_runtime_generation="boot-17", expected_calibration_generation="cal-4",
            expected_landmark_model_generation="face-landmarker-v7",
            minimum_tracking_confidence=0.9,
        )
        self.assertFalse(gate.admissible)
        self.assertIn("TRACKING_CONFIDENCE_BELOW_GATE", gate.refusals)

    def test_current_common_cut_can_be_evidence_admissible_but_not_effect_authorized(self):
        gate = eye.gate_eye_pose_for_steering(
            frame=frame(), calibration=calibration(), now_ns=1_100_000_000,
            max_age_ns=200_000_000, expected_sensor_instance_id="camera-instance-A",
            expected_runtime_generation="boot-17", expected_calibration_generation="cal-4",
            expected_landmark_model_generation="face-landmarker-v7",
            minimum_tracking_confidence=0.9,
        )
        self.assertTrue(gate.admissible)
        self.assertTrue(gate.common_cut_proven)
        self.assertTrue(gate.freshness_proven)
        self.assertFalse(gate.physical_effect_authority)

    def test_receipt_is_two_parent_source_bound_and_tamper_evident(self):
        f = frame()
        c = calibration()
        estimate = eye.estimate_eye_pose_from_assumed_ipd(frame=f, calibration=c, assumed_ipd_m=0.064)
        gate = eye.gate_eye_pose_for_steering(
            frame=f, calibration=c, now_ns=1_100_000_000, max_age_ns=200_000_000,
            expected_sensor_instance_id="camera-instance-A",
            expected_runtime_generation="boot-17", expected_calibration_generation="cal-4",
            expected_landmark_model_generation="face-landmarker-v7",
            minimum_tracking_confidence=0.9,
        )
        receipt = eye.build_eye_pose_receipt(
            frame=f, calibration=c, estimate=estimate, gate=gate, k27_coordinate=13,
            parent_artifact_ids=PARENTS,
        )
        self.assertTrue(eye.verify_eye_pose_receipt(receipt))
        self.assertFalse(receipt["claim_ceiling"]["k27_coordinate_is_authority"])
        tampered = dict(receipt)
        tampered["k27_coordinate"] = 14
        self.assertFalse(eye.verify_eye_pose_receipt(tampered))

    def test_receipt_requires_exactly_two_distinct_parents(self):
        f = frame()
        c = calibration()
        estimate = eye.estimate_eye_pose_from_assumed_ipd(frame=f, calibration=c, assumed_ipd_m=0.064)
        gate = eye.gate_eye_pose_for_steering(
            frame=f, calibration=c, now_ns=1_100_000_000, max_age_ns=200_000_000,
            expected_sensor_instance_id="camera-instance-A",
            expected_runtime_generation="boot-17", expected_calibration_generation="cal-4",
            expected_landmark_model_generation="face-landmarker-v7",
            minimum_tracking_confidence=0.9,
        )
        with self.assertRaises(ValueError):
            eye.build_eye_pose_receipt(
                frame=f, calibration=c, estimate=estimate, gate=gate, k27_coordinate=13,
                parent_artifact_ids=(PARENTS[0], PARENTS[0]),
            )


if __name__ == "__main__":
    unittest.main()
