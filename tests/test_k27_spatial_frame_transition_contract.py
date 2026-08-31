from pathlib import Path
import hashlib
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


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_eye_receipt(*, frame_capture=1_000_000_000, gate_admissible=True):
    calibration = eye.CameraCalibration(
        sensor_instance_id="cam-A", runtime_generation="boot-1",
        calibration_generation="cal-1", fx_px=1000.0, fy_px=1000.0,
        cx_px=640.0, cy_px=360.0, image_width_px=1280, image_height_px=720,
    )
    frame = eye.IrisFrameObservation(
        sensor_instance_id="cam-A", runtime_generation="boot-1",
        frame_id="eye-1", capture_time_ns=frame_capture,
        landmark_model_generation="landmarks-v1", tracking_confidence=0.99,
        left_iris_x_px=600.0, left_iris_y_px=360.0,
        right_iris_x_px=680.0, right_iris_y_px=360.0,
    )
    estimate = eye.estimate_eye_pose_from_assumed_ipd(
        frame=frame, calibration=calibration, assumed_ipd_m=0.064
    )
    now_ns = 1_050_000_000 if gate_admissible else 1_500_000_000
    gate = eye.gate_eye_pose_for_steering(
        frame=frame, calibration=calibration, now_ns=now_ns,
        max_age_ns=100_000_000, expected_sensor_instance_id="cam-A",
        expected_runtime_generation="boot-1", expected_calibration_generation="cal-1",
        expected_landmark_model_generation="landmarks-v1", minimum_tracking_confidence=0.9,
    )
    return eye.build_eye_pose_receipt(
        frame=frame, calibration=calibration, estimate=estimate, gate=gate,
        k27_coordinate=13, parent_artifact_ids=("gemini", "deepseek")
    )


def make_phase_receipt(*, reuse_admissible=True):
    payload = b"mask-v1"
    artifact = phase.PhaseMaskArtifactIdentity(
        scene_source_sha256=sha(b"scene"), optical_model_generation="asm-v1",
        phase_encoding_generation="phase-v1", wavelength_nm=532,
        width_px=512, height_px=512, dtype="float16",
        payload_sha256=sha(payload), payload_bytes=len(payload),
    )
    plan = phase.PlannedMaterialization(
        storage_object_id="mask-store", storage_generation="store-1",
        storage_plan_digest=sha(b"plan"), planned_backend="MMAP_DEMAND",
        byte_offset=4096, aligned_extent_bytes=4096,
    )
    handle = phase.make_handle(k27_coordinate=13, artifact=artifact, plan=plan)
    observed_digest = sha(payload if reuse_admissible else b"wrong")
    observation = phase.RetrievalObservation(
        storage_object_id="mask-store", storage_generation="store-1",
        observed_byte_offset=4096, observed_payload_sha256=observed_digest,
        observed_payload_bytes=len(payload),
    )
    gate = phase.validate_retrieval(
        handle=handle, artifact=artifact, plan=plan, observation=observation
    )
    return phase.build_phase_mask_receipt(
        handle=handle, artifact=artifact, plan=plan, gate=gate,
        parent_artifact_ids=("gemini", "pr599")
    )


def intent(eye_receipt, phase_receipt, **overrides):
    values = dict(
        presentation_frame_id="display-frame-77",
        presentation_time_ns=1_080_000_000,
        display_pipeline_generation="display-sim-v1",
        expected_eye_receipt_sha256=eye_receipt["receipt_sha256"],
        expected_phase_receipt_sha256=phase_receipt["receipt_sha256"],
        max_eye_age_at_presentation_ns=100_000_000,
    )
    values.update(overrides)
    return framejoin.SpatialFrameIntent(**values)


class SpatialFrameTransitionTests(unittest.TestCase):
    def test_exact_eye_and_mask_bind_to_same_transition_evidence(self):
        e = make_eye_receipt()
        p = make_phase_receipt()
        gate = framejoin.bind_spatial_frame_transition(eye_receipt=e, phase_receipt=p, intent=intent(e, p))
        self.assertTrue(gate.admissible_same_transition_evidence)
        self.assertFalse(gate.physical_display_effect_authority)

    def test_foreign_eye_receipt_identity_rejected(self):
        e = make_eye_receipt()
        p = make_phase_receipt()
        gate = framejoin.bind_spatial_frame_transition(
            eye_receipt=e, phase_receipt=p,
            intent=intent(e, p, expected_eye_receipt_sha256=sha(b"foreign-eye")),
        )
        self.assertIn("EYE_RECEIPT_IDENTITY_MISMATCH", gate.refusals)

    def test_foreign_phase_receipt_identity_rejected(self):
        e = make_eye_receipt()
        p = make_phase_receipt()
        gate = framejoin.bind_spatial_frame_transition(
            eye_receipt=e, phase_receipt=p,
            intent=intent(e, p, expected_phase_receipt_sha256=sha(b"foreign-phase")),
        )
        self.assertIn("PHASE_RECEIPT_IDENTITY_MISMATCH", gate.refusals)

    def test_eye_frame_stale_at_presentation_cut_rejected(self):
        e = make_eye_receipt(frame_capture=500_000_000)
        p = make_phase_receipt()
        gate = framejoin.bind_spatial_frame_transition(eye_receipt=e, phase_receipt=p, intent=intent(e, p))
        self.assertIn("EYE_FRAME_OUTSIDE_PRESENTATION_TIME_CUT", gate.refusals)

    def test_eye_frame_from_future_at_presentation_cut_rejected(self):
        e = make_eye_receipt(frame_capture=1_090_000_000)
        p = make_phase_receipt()
        gate = framejoin.bind_spatial_frame_transition(eye_receipt=e, phase_receipt=p, intent=intent(e, p))
        self.assertIn("EYE_FRAME_OUTSIDE_PRESENTATION_TIME_CUT", gate.refusals)

    def test_eye_evidence_gate_must_be_admissible(self):
        e = make_eye_receipt(gate_admissible=False)
        p = make_phase_receipt()
        gate = framejoin.bind_spatial_frame_transition(eye_receipt=e, phase_receipt=p, intent=intent(e, p))
        self.assertIn("EYE_EVIDENCE_GATE_NOT_ADMISSIBLE", gate.refusals)

    def test_phase_semantic_reuse_gate_must_be_admissible(self):
        e = make_eye_receipt()
        p = make_phase_receipt(reuse_admissible=False)
        gate = framejoin.bind_spatial_frame_transition(eye_receipt=e, phase_receipt=p, intent=intent(e, p))
        self.assertIn("PHASE_MASK_SEMANTIC_REUSE_NOT_ADMISSIBLE", gate.refusals)

    def test_transition_receipt_is_two_parent_and_tamper_evident(self):
        e = make_eye_receipt()
        p = make_phase_receipt()
        i = intent(e, p)
        gate = framejoin.bind_spatial_frame_transition(eye_receipt=e, phase_receipt=p, intent=i)
        receipt = framejoin.build_spatial_frame_receipt(
            eye_receipt=e, phase_receipt=p, intent=i, gate=gate,
            parent_artifact_ids=PARENTS,
        )
        self.assertTrue(framejoin.verify_spatial_frame_receipt(receipt))
        self.assertTrue(all(v is False for v in receipt["claim_ceiling"].values()))
        tampered = dict(receipt)
        tampered["phase_receipt_sha256"] = sha(b"tamper")
        self.assertFalse(framejoin.verify_spatial_frame_receipt(tampered))

    def test_exactly_two_distinct_parent_artifacts_required(self):
        e = make_eye_receipt()
        p = make_phase_receipt()
        i = intent(e, p)
        gate = framejoin.bind_spatial_frame_transition(eye_receipt=e, phase_receipt=p, intent=i)
        with self.assertRaises(ValueError):
            framejoin.build_spatial_frame_receipt(
                eye_receipt=e, phase_receipt=p, intent=i, gate=gate,
                parent_artifact_ids=(PARENTS[0], PARENTS[0]),
            )


if __name__ == "__main__":
    unittest.main()
