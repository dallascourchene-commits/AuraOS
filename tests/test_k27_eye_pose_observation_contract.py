import dataclasses
import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import k27_eye_pose_observation_contract as eye

PARENTS=("source-artifact","review-artifact")

def calibration():
    return eye.CameraCalibration(
        sensor_instance_id="cam0", runtime_generation="run7",
        calibration_generation="cal3", coordinate_space=eye.COORDINATE_SPACE,
        fx_px=800.0, fy_px=1200.0, cx_px=640.0, cy_px=360.0,
        image_width_px=1280, image_height_px=720,
        calibration_evidence_ref="calibration-dataset:abc",
    )

def frame():
    return eye.IrisFrameObservation(
        sensor_instance_id="cam0", runtime_generation="run7", frame_id="f10",
        capture_time_ns=1_000_000, landmark_model_generation="landmark4",
        tracking_confidence=0.99,
        left_iris_x_px=600.0, left_iris_y_px=350.0,
        right_iris_x_px=680.0, right_iris_y_px=390.0,
    )

def policy():
    return eye.GatePolicyV1(
        now_ns=1_000_100, max_age_ns=1_000,
        expected_sensor_instance_id="cam0", expected_runtime_generation="run7",
        expected_calibration_generation="cal3",
        expected_landmark_model_generation="landmark4",
        minimum_tracking_confidence=0.9,
    )

class EyeProducerTraversalTests(unittest.TestCase):
    def test_anisotropic_intrinsics_are_used_in_depth(self):
        e=eye.estimate_eye_pose_from_assumed_ipd(frame=frame(), calibration=calibration(), assumed_ipd_m=0.064)
        expected=0.064/((80.0/800.0)**2+(40.0/1200.0)**2)**0.5
        self.assertAlmostEqual(e.z_m,expected)

    def test_raw_coordinate_space_rejected(self):
        c=dataclasses.replace(calibration(), coordinate_space="RAW_DISTORTED_PIXELS_V1")
        with self.assertRaises(ValueError):
            eye.estimate_eye_pose_from_assumed_ipd(frame=frame(),calibration=c,assumed_ipd_m=0.064)

    def test_receipt_builder_accepts_no_estimate_or_gate(self):
        params=inspect.signature(eye.build_eye_pose_receipt).parameters
        self.assertNotIn("estimate",params)
        self.assertNotIn("gate",params)

    def test_receipt_recomputes_producer_and_verifies(self):
        r=eye.build_eye_pose_receipt(frame=frame(),calibration=calibration(),assumed_ipd_m=0.064,
            gate_policy=policy(),k27_coordinate=7,parent_artifact_ids=PARENTS)
        self.assertTrue(r["gate"]["software_gate_admissible"])
        self.assertTrue(eye.verify_eye_pose_receipt(r))
        self.assertFalse(r["temporal_point_evidence_admissible"])

    def test_forged_gate_with_fresh_hash_rejected(self):
        r=dict(eye.build_eye_pose_receipt(frame=frame(),calibration=calibration(),assumed_ipd_m=0.064,
            gate_policy=policy(),k27_coordinate=7,parent_artifact_ids=PARENTS))
        r["gate"]=dict(r["gate"]); r["gate"]["software_gate_admissible"]=False
        payload={k:v for k,v in r.items() if k!="receipt_sha256"}
        r["receipt_sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
        self.assertFalse(eye.verify_eye_pose_receipt(r))

    def test_forged_estimate_with_fresh_hash_rejected(self):
        r=dict(eye.build_eye_pose_receipt(frame=frame(),calibration=calibration(),assumed_ipd_m=0.064,
            gate_policy=policy(),k27_coordinate=7,parent_artifact_ids=PARENTS))
        r["estimate"]=dict(r["estimate"]); r["estimate"]["z_m"]=999.0
        payload={k:v for k,v in r.items() if k!="receipt_sha256"}
        r["receipt_sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
        self.assertFalse(eye.verify_eye_pose_receipt(r))

    def test_stale_frame_fails_software_gate(self):
        p=dataclasses.replace(policy(), now_ns=2_000_000)
        r=eye.build_eye_pose_receipt(frame=frame(),calibration=calibration(),assumed_ipd_m=0.064,
            gate_policy=p,k27_coordinate=7,parent_artifact_ids=PARENTS)
        self.assertFalse(r["gate"]["software_gate_admissible"])
        self.assertIn("FRAME_STALE_OR_FROM_FUTURE",r["gate"]["refusals"])

    def test_claim_ceiling_never_upgrades_capture_or_authority(self):
        r=eye.build_eye_pose_receipt(frame=frame(),calibration=calibration(),assumed_ipd_m=0.064,
            gate_policy=policy(),k27_coordinate=7,parent_artifact_ids=PARENTS)
        self.assertTrue(all(v is False for v in r["claim_ceiling"].values()))
        self.assertFalse(r["gate"]["sensor_observation_authenticated"])
        self.assertFalse(r["gate"]["effect_time_currentness_authorized"])

if __name__=="__main__":
    unittest.main()
