from pathlib import Path
import dataclasses
import hashlib
import inspect
import json
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_eye_pose_observation_contract as eye
import k27_phase_mask_artifact_contract as phase
import k27_spatial_frame_transition_contract as framejoin

PARENTS = (
    "1l8FLO6a0ebJX1D4L2VP5PThii4P_vcGGrGMxBHYy_Ew",
    "1hs1S62PPd0sLM2O_w-PvDClIbit8BeVYPs_Y_Zk3YJw",
)
EYE_PARENTS = ("gemini", "deepseek")

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def eye_inputs(*, capture=1_000_000_000, stale=False, confidence=0.99):
    calibration = eye.CameraCalibration(
        sensor_instance_id="cam-A", runtime_generation="boot-1",
        calibration_generation="cal-1", coordinate_space=eye.COORDINATE_SPACE,
        fx_px=1000.0, fy_px=1100.0, cx_px=640.0, cy_px=360.0,
        image_width_px=1280, image_height_px=720,
        calibration_evidence_ref="dataset:cal-1",
    )
    frame = eye.IrisFrameObservation(
        sensor_instance_id="cam-A", runtime_generation="boot-1", frame_id="eye-1",
        capture_time_ns=capture, landmark_model_generation="landmarks-v1",
        tracking_confidence=confidence,
        left_iris_x_px=600.0, left_iris_y_px=355.0,
        right_iris_x_px=680.0, right_iris_y_px=365.0,
    )
    policy = eye.GatePolicyV1(
        now_ns=capture + (500_000_000 if stale else 50_000_000),
        max_age_ns=100_000_000,
        expected_sensor_instance_id="cam-A", expected_runtime_generation="boot-1",
        expected_calibration_generation="cal-1",
        expected_landmark_model_generation="landmarks-v1",
        minimum_tracking_confidence=0.9,
    )
    return frame, calibration, 0.064, policy

def produce_eye(inputs):
    f,c,ipd,p = inputs
    return eye.build_eye_pose_receipt(
        frame=f, calibration=c, assumed_ipd_m=ipd, gate_policy=p,
        k27_coordinate=13, parent_artifact_ids=EYE_PARENTS,
    )

def make_phase_receipt(*, reuse_admissible=True):
    payload=b"mask-v1"
    artifact=phase.PhaseMaskArtifactIdentity(
        scene_source_sha256=sha(b"scene"), optical_model_generation="asm-v1",
        phase_encoding_generation="phase-v1", wavelength_nm=532,
        width_px=512,height_px=512,dtype="float16",
        payload_sha256=sha(payload),payload_bytes=len(payload),
    )
    plan=phase.PlannedMaterialization(
        storage_object_id="mask-store",storage_generation="store-1",
        storage_plan_digest=sha(b"plan"),planned_backend="MMAP_DEMAND",
        byte_offset=4096,aligned_extent_bytes=4096,
    )
    handle=phase.make_handle(k27_coordinate=13,artifact=artifact,plan=plan)
    observed=sha(payload if reuse_admissible else b"wrong")
    observation=phase.RetrievalObservation(
        storage_object_id="mask-store",storage_generation="store-1",
        observed_byte_offset=4096,observed_payload_sha256=observed,
        observed_payload_bytes=len(payload),
    )
    gate=phase.validate_retrieval(handle=handle,artifact=artifact,plan=plan,observation=observation)
    return phase.build_phase_mask_receipt(
        handle=handle,artifact=artifact,plan=plan,gate=gate,
        parent_artifact_ids=("gemini","pr599"),
    )

def intent(inputs, phase_receipt, *, present=1_080_000_000, **overrides):
    e=produce_eye(inputs)
    values=dict(
        presentation_frame_id="display-frame-77",presentation_time_ns=present,
        display_pipeline_generation="display-sim-v1",
        expected_eye_receipt_sha256=e["receipt_sha256"],
        expected_phase_receipt_sha256=phase_receipt["receipt_sha256"],
        max_eye_age_at_presentation_ns=100_000_000,
    )
    values.update(overrides)
    return framejoin.SpatialFrameIntent(**values)

def bind(inputs, p, i):
    f,c,ipd,pol=inputs
    return framejoin.bind_spatial_frame_transition(
        eye_frame=f,eye_calibration=c,assumed_ipd_m=ipd,eye_gate_policy=pol,
        eye_k27_coordinate=13,eye_parent_artifact_ids=EYE_PARENTS,
        phase_receipt=p,intent=i,
    )

class SpatialFrameTransitionV2Tests(unittest.TestCase):
    def test_public_consumer_has_no_serialized_eye_receipt_parameter(self):
        params=inspect.signature(framejoin.bind_spatial_frame_transition).parameters
        self.assertNotIn("eye_receipt",params)
        self.assertIn("eye_frame",params)
        self.assertIn("eye_gate_policy",params)

    def test_valid_lower_inputs_form_software_candidate_but_not_authenticated_transition(self):
        x=eye_inputs(); p=make_phase_receipt(); g=bind(x,p,intent(x,p))
        self.assertTrue(g.software_same_frame_candidate)
        self.assertFalse(g.admissible_same_transition_evidence)
        self.assertFalse(g.eye_temporal_evidence_authenticated)
        self.assertIn("EYE_TEMPORAL_EVIDENCE_NOT_AUTHENTICATED",g.refusals)

    def test_low_confidence_cannot_be_laundered_by_consumer(self):
        x=eye_inputs(confidence=0.2); p=make_phase_receipt(); g=bind(x,p,intent(x,p))
        self.assertFalse(g.eye_software_gate_admissible)
        self.assertFalse(g.software_same_frame_candidate)
        self.assertIn("EYE_SOFTWARE_GATE_NOT_ADMISSIBLE",g.refusals)

    def test_stale_eye_gate_cannot_be_laundered(self):
        x=eye_inputs(stale=True); p=make_phase_receipt(); g=bind(x,p,intent(x,p))
        self.assertFalse(g.eye_software_gate_admissible)
        self.assertFalse(g.admissible_same_transition_evidence)

    def test_foreign_expected_eye_identity_rejected(self):
        x=eye_inputs(); p=make_phase_receipt(); i=intent(x,p,expected_eye_receipt_sha256=sha(b"foreign"))
        g=bind(x,p,i)
        self.assertIn("EYE_RECEIPT_IDENTITY_MISMATCH",g.refusals)

    def test_phase_reuse_gate_still_required(self):
        x=eye_inputs(); p=make_phase_receipt(reuse_admissible=False); g=bind(x,p,intent(x,p))
        self.assertIn("PHASE_MASK_SEMANTIC_REUSE_NOT_ADMISSIBLE",g.refusals)

    def test_presentation_time_cut_still_required(self):
        x=eye_inputs(capture=500_000_000); p=make_phase_receipt(); g=bind(x,p,intent(x,p))
        self.assertIn("EYE_FRAME_OUTSIDE_PRESENTATION_TIME_CUT",g.refusals)

    def test_receipt_builder_recomputes_gate_and_rejects_freshly_rehashed_forgery(self):
        x=eye_inputs(); p=make_phase_receipt(); i=intent(x,p); f,c,ipd,pol=x
        r=dict(framejoin.build_spatial_frame_receipt(
            eye_frame=f,eye_calibration=c,assumed_ipd_m=ipd,eye_gate_policy=pol,
            eye_k27_coordinate=13,eye_parent_artifact_ids=EYE_PARENTS,
            phase_receipt=p,intent=i,parent_artifact_ids=PARENTS,
        ))
        self.assertTrue(framejoin.verify_spatial_frame_receipt(r))
        self.assertFalse(r["gate"]["admissible_same_transition_evidence"])
        r["gate"]=dict(r["gate"]); r["gate"]["admissible_same_transition_evidence"]=True
        payload={k:v for k,v in r.items() if k!="receipt_sha256"}
        r["receipt_sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
        self.assertFalse(framejoin.verify_spatial_frame_receipt(r))

    def test_claim_ceiling_remains_hard_false(self):
        x=eye_inputs(); p=make_phase_receipt(); i=intent(x,p); f,c,ipd,pol=x
        r=framejoin.build_spatial_frame_receipt(
            eye_frame=f,eye_calibration=c,assumed_ipd_m=ipd,eye_gate_policy=pol,
            eye_k27_coordinate=13,eye_parent_artifact_ids=EYE_PARENTS,
            phase_receipt=p,intent=i,parent_artifact_ids=PARENTS,
        )
        self.assertTrue(all(v is False for v in r["claim_ceiling"].values()))

if __name__=="__main__":
    unittest.main()
