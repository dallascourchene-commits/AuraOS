from __future__ import annotations
from dataclasses import replace
import hashlib
import json
import unittest

from tools.k27_eye_pose_observation_contract import (
    COORDINATE_SPACE, CameraCalibration, GatePolicyV1, IrisFrameObservation,
    build_eye_pose_receipt,
)
from tools.test_thinkpad_longitudinal_envelope_series import ThinkPadLongitudinalEnvelopeSeriesTests
from tools.temporal_evidence_scope_coordinate import (
    TemporalEvidenceScopeError, bind_temporal_evidence_scope,
    portable_temporal_evidence_scope_receipt, verify_temporal_evidence_scope_coordinate,
)

PARENTS=("eye-source-artifact","common-cut-artifact")

def calibration():
    return CameraCalibration(
        sensor_instance_id="camera-instance-A", runtime_generation="boot-17",
        calibration_generation="cal-4", coordinate_space=COORDINATE_SPACE,
        fx_px=1000.0, fy_px=1100.0, cx_px=640.0, cy_px=360.0,
        image_width_px=1280, image_height_px=720,
        calibration_evidence_ref="dataset:cal4",
    )

def eye_receipt(capture_ns:int, *, stale=False):
    c=calibration()
    f=IrisFrameObservation(
        sensor_instance_id="camera-instance-A", runtime_generation="boot-17",
        frame_id=f"frame-{capture_ns}", capture_time_ns=capture_ns,
        landmark_model_generation="face-landmarker-v7", tracking_confidence=0.98,
        left_iris_x_px=600.0,left_iris_y_px=355.0,
        right_iris_x_px=680.0,right_iris_y_px=365.0,
    )
    policy=GatePolicyV1(
        now_ns=capture_ns+(300_000_000 if stale else 100_000_000),
        max_age_ns=200_000_000,
        expected_sensor_instance_id="camera-instance-A",
        expected_runtime_generation="boot-17",
        expected_calibration_generation="cal-4",
        expected_landmark_model_generation="face-landmarker-v7",
        minimum_tracking_confidence=0.9,
    )
    return build_eye_pose_receipt(
        frame=f, calibration=c, assumed_ipd_m=0.064, gate_policy=policy,
        k27_coordinate=13, parent_artifact_ids=PARENTS,
    )

def series():
    return ThinkPadLongitudinalEnvelopeSeriesTests().build()

class TemporalEvidenceScopeCoordinateTests(unittest.TestCase):
    def test_repaired_point_holds_unknown_until_temporal_authentication(self):
        out=bind_temporal_evidence_scope(
            eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000), longitudinal_series=series())
        self.assertEqual("UNKNOWN",out.point_vs_series_relation)
        self.assertFalse(out.temporal_overlap)
        self.assertTrue(out.point_observation_software_gate_admissible)
        self.assertFalse(out.point_observation_temporal_admissible)
        self.assertEqual("POINT_EVIDENCE_NOT_AUTHENTICATED",out.hold_reason)

    def test_stale_point_is_unknown_before_time_relation(self):
        out=bind_temporal_evidence_scope(
            eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000,stale=True), longitudinal_series=series())
        self.assertEqual("UNKNOWN",out.point_vs_series_relation)
        self.assertFalse(out.point_observation_software_gate_admissible)
        self.assertEqual("POINT_SOFTWARE_GATE_NOT_ADMISSIBLE",out.hold_reason)

    def test_caller_cannot_flip_temporal_admission_with_fresh_hash(self):
        r=dict(eye_receipt(1_788_156_600_000_000_000)); r["temporal_point_evidence_admissible"]=True
        payload={k:v for k,v in r.items() if k!="receipt_sha256"}
        r["receipt_sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
        with self.assertRaisesRegex(TemporalEvidenceScopeError,"EYE_POSE_RECEIPT_INVALID"):
            bind_temporal_evidence_scope(eye_pose_receipt=r,longitudinal_series=series())

    def test_forged_gate_result_is_rejected_before_temporal_use(self):
        r=dict(eye_receipt(1_788_156_600_000_000_000)); r["gate"]=dict(r["gate"])
        r["gate"]["software_gate_admissible"]=False
        payload={k:v for k,v in r.items() if k!="receipt_sha256"}
        r["receipt_sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
        with self.assertRaisesRegex(TemporalEvidenceScopeError,"EYE_POSE_RECEIPT_INVALID"):
            bind_temporal_evidence_scope(eye_pose_receipt=r,longitudinal_series=series())

    def test_longitudinal_current_now_widening_still_fails(self):
        with self.assertRaisesRegex(TemporalEvidenceScopeError,"LONGITUDINAL_SERIES_CEILING_WIDENED"):
            bind_temporal_evidence_scope(
                eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000),
                longitudinal_series=replace(series(),current_now_proven=True))

    def test_portable_unknown_coordinate_is_tamper_evident(self):
        r=portable_temporal_evidence_scope_receipt(
            eye_pose_receipt=eye_receipt(1_788_156_600_000_000_000), longitudinal_series=series())
        self.assertTrue(verify_temporal_evidence_scope_coordinate(r))
        t=dict(r); t["point_vs_series_relation"]="DURING"
        self.assertFalse(verify_temporal_evidence_scope_coordinate(t))

    def test_coordinate_identity_is_deterministic(self):
        e=eye_receipt(1_788_156_600_000_000_000); s=series()
        a=bind_temporal_evidence_scope(eye_pose_receipt=e,longitudinal_series=s)
        b=bind_temporal_evidence_scope(eye_pose_receipt=e,longitudinal_series=s)
        self.assertEqual(a.coordinate_digest,b.coordinate_digest)

if __name__=="__main__":
    unittest.main()
