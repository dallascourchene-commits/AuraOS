"""Producer-traversed eye-pose/common-cut evidence for K27 spatial experiments.

The public receipt path accepts lower observations and policy inputs only. It
recomputes the geometric estimate and temporal/common-cut gate internally.
Hash integrity is therefore not confused with producer traversal.

The contract still does NOT authenticate the physical sensor capture, currentness
owner, calibration provenance, or effect authority. Those remain separate gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence

SCHEMA = "AURA_K27_EYE_POSE_OBSERVATION_COMMON_CUT_V2"
POSE_CLASS = "CALIBRATED_ASSUMED_IPD_GEOMETRIC_ESTIMATE"
K27_SCHEME = "K27-B3MOD27-XYZ-v1"
COORDINATE_SPACE = "UNDISTORTED_PINHOLE_PIXELS_V1"


def _real(name: str, value: object, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number, not bool")
    out = float(value)
    if not math.isfinite(out) or (positive and out <= 0.0):
        raise ValueError(f"{name} must be finite" + (" and positive" if positive else ""))
    return out


def _nonempty(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")
    return value.strip()


@dataclass(frozen=True)
class CameraCalibration:
    sensor_instance_id: str
    runtime_generation: str
    calibration_generation: str
    coordinate_space: str
    fx_px: float
    fy_px: float
    cx_px: float
    cy_px: float
    image_width_px: int
    image_height_px: int
    calibration_evidence_ref: str

    def validate(self) -> None:
        for name in ("sensor_instance_id", "runtime_generation", "calibration_generation", "calibration_evidence_ref"):
            _nonempty(name, getattr(self, name))
        if self.coordinate_space != COORDINATE_SPACE:
            raise ValueError("coordinate_space must be UNDISTORTED_PINHOLE_PIXELS_V1")
        _real("fx_px", self.fx_px, positive=True)
        _real("fy_px", self.fy_px, positive=True)
        _real("cx_px", self.cx_px)
        _real("cy_px", self.cy_px)
        for name in ("image_width_px", "image_height_px"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class IrisFrameObservation:
    sensor_instance_id: str
    runtime_generation: str
    frame_id: str
    capture_time_ns: int
    landmark_model_generation: str
    tracking_confidence: float
    left_iris_x_px: float
    left_iris_y_px: float
    right_iris_x_px: float
    right_iris_y_px: float

    def validate(self) -> None:
        for name in ("sensor_instance_id", "runtime_generation", "frame_id", "landmark_model_generation"):
            _nonempty(name, getattr(self, name))
        if isinstance(self.capture_time_ns, bool) or not isinstance(self.capture_time_ns, int) or self.capture_time_ns < 0:
            raise ValueError("capture_time_ns must be a non-negative integer")
        confidence = _real("tracking_confidence", self.tracking_confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("tracking_confidence must be within [0,1]")
        for name in ("left_iris_x_px", "left_iris_y_px", "right_iris_x_px", "right_iris_y_px"):
            _real(name, getattr(self, name))


@dataclass(frozen=True)
class EyePoseEstimate:
    x_m: float
    y_m: float
    z_m: float
    assumed_ipd_m: float
    pose_class: str = POSE_CLASS
    calibrated_metric_truth_proven: bool = False
    physical_steering_authority: bool = False


@dataclass(frozen=True)
class SteeringGate:
    software_gate_admissible: bool
    refusals: tuple[str, ...]
    common_cut_matched: bool
    freshness_matched: bool
    calibration_generation_matched: bool
    landmark_model_generation_matched: bool
    sensor_observation_authenticated: bool = False
    calibration_producer_authenticated: bool = False
    effect_time_currentness_authorized: bool = False
    physical_effect_authority: bool = False

    @property
    def admissible(self) -> bool:
        """Compatibility projection: software gate only, never physical authority."""
        return self.software_gate_admissible


@dataclass(frozen=True)
class GatePolicyV1:
    now_ns: int
    max_age_ns: int
    expected_sensor_instance_id: str
    expected_runtime_generation: str
    expected_calibration_generation: str
    expected_landmark_model_generation: str
    minimum_tracking_confidence: float

    def validate(self) -> None:
        for name in (
            "expected_sensor_instance_id", "expected_runtime_generation",
            "expected_calibration_generation", "expected_landmark_model_generation",
        ):
            _nonempty(name, getattr(self, name))
        for name in ("now_ns", "max_age_ns"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        confidence = _real("minimum_tracking_confidence", self.minimum_tracking_confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("minimum_tracking_confidence must be within [0,1]")


def estimate_eye_pose_from_assumed_ipd(
    *, frame: IrisFrameObservation, calibration: CameraCalibration, assumed_ipd_m: float,
) -> EyePoseEstimate:
    frame.validate()
    calibration.validate()
    ipd = _real("assumed_ipd_m", assumed_ipd_m, positive=True)
    if frame.sensor_instance_id != calibration.sensor_instance_id or frame.runtime_generation != calibration.runtime_generation:
        raise ValueError("frame and calibration are not from the same sensor runtime cut")
    dx = frame.right_iris_x_px - frame.left_iris_x_px
    dy = frame.right_iris_y_px - frame.left_iris_y_px
    normalized_ipd = math.hypot(dx / calibration.fx_px, dy / calibration.fy_px)
    if normalized_ipd <= 0.0:
        raise ValueError("observed normalized pixel IPD must be positive")
    z_m = ipd / normalized_ipd
    mid_x = 0.5 * (frame.left_iris_x_px + frame.right_iris_x_px)
    mid_y = 0.5 * (frame.left_iris_y_px + frame.right_iris_y_px)
    x_m = (mid_x - calibration.cx_px) * z_m / calibration.fx_px
    y_m = (mid_y - calibration.cy_px) * z_m / calibration.fy_px
    return EyePoseEstimate(x_m=x_m, y_m=y_m, z_m=z_m, assumed_ipd_m=ipd)


def gate_eye_pose_for_steering(
    *, frame: IrisFrameObservation, calibration: CameraCalibration, policy: GatePolicyV1,
) -> SteeringGate:
    frame.validate()
    calibration.validate()
    policy.validate()
    refusals: list[str] = []
    same_cut = (
        frame.sensor_instance_id == calibration.sensor_instance_id == policy.expected_sensor_instance_id
        and frame.runtime_generation == calibration.runtime_generation == policy.expected_runtime_generation
    )
    if not same_cut:
        refusals.append("SENSOR_RUNTIME_COMMON_CUT_MISMATCH")
    calibration_current = calibration.calibration_generation == policy.expected_calibration_generation
    if not calibration_current:
        refusals.append("CALIBRATION_GENERATION_MISMATCH")
    model_current = frame.landmark_model_generation == policy.expected_landmark_model_generation
    if not model_current:
        refusals.append("LANDMARK_MODEL_GENERATION_MISMATCH")
    age_ns = policy.now_ns - frame.capture_time_ns
    freshness = 0 <= age_ns <= policy.max_age_ns
    if not freshness:
        refusals.append("FRAME_STALE_OR_FROM_FUTURE")
    if frame.tracking_confidence < policy.minimum_tracking_confidence:
        refusals.append("TRACKING_CONFIDENCE_BELOW_GATE")
    return SteeringGate(
        software_gate_admissible=not refusals,
        refusals=tuple(refusals),
        common_cut_matched=same_cut,
        freshness_matched=freshness,
        calibration_generation_matched=calibration_current,
        landmark_model_generation_matched=model_current,
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_eye_pose_receipt(
    *,
    frame: IrisFrameObservation,
    calibration: CameraCalibration,
    assumed_ipd_m: float,
    gate_policy: GatePolicyV1,
    k27_coordinate: int,
    parent_artifact_ids: Sequence[str],
) -> Mapping[str, object]:
    """Force estimator + gate traversal from lower inputs; no result objects accepted."""
    if isinstance(k27_coordinate, bool) or not isinstance(k27_coordinate, int) or not 0 <= k27_coordinate <= 26:
        raise ValueError("k27_coordinate must be an integer in [0,26]")
    parents = tuple(parent_artifact_ids)
    if len(parents) != 2 or len(set(parents)) != 2 or any(not p for p in parents):
        raise ValueError("exactly two distinct non-empty parent artifact IDs are required")
    estimate = estimate_eye_pose_from_assumed_ipd(frame=frame, calibration=calibration, assumed_ipd_m=assumed_ipd_m)
    gate = gate_eye_pose_for_steering(frame=frame, calibration=calibration, policy=gate_policy)
    payload = {
        "schema": SCHEMA,
        "producer_schema": "AURA_K27_EYE_POSE_RECEIPT_PRODUCER_V2",
        "k27_scheme": K27_SCHEME,
        "k27_coordinate": k27_coordinate,
        "parent_artifact_ids": parents,
        "producer_inputs": {
            "frame": asdict(frame),
            "calibration": asdict(calibration),
            "assumed_ipd_m": assumed_ipd_m,
            "gate_policy": asdict(gate_policy),
        },
        "estimate": asdict(estimate),
        "gate": asdict(gate),
        "temporal_point_evidence_admissible": False,
        "reason_temporal_point_not_admissible": "PHYSICAL_SENSOR_CAPTURE_AND_EFFECT_TIME_CURRENTNESS_NOT_AUTHENTICATED",
        "claim_ceiling": {
            "camera_pose_is_metric_ground_truth": False,
            "sensor_capture_authenticated": False,
            "calibration_producer_authenticated": False,
            "effect_time_currentness_authorized": False,
            "k27_coordinate_is_authority": False,
            "physical_display_effect_authorized": False,
            "optical_safety_proven": False,
            "deployment_ready": False,
            "gate10_promoted": False,
            "native_transformer_kv_accessed": False,
        },
    }
    return {**payload, "receipt_sha256": hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()}


def _from_receipt_inputs(receipt: Mapping[str, object]) -> Mapping[str, object]:
    p = receipt["producer_inputs"]
    return build_eye_pose_receipt(
        frame=IrisFrameObservation(**p["frame"]),
        calibration=CameraCalibration(**p["calibration"]),
        assumed_ipd_m=p["assumed_ipd_m"],
        gate_policy=GatePolicyV1(**p["gate_policy"]),
        k27_coordinate=receipt["k27_coordinate"],
        parent_artifact_ids=receipt["parent_artifact_ids"],
    )


def verify_eye_pose_receipt(receipt: Mapping[str, object]) -> bool:
    """Re-run producer; a fresh hash over caller-selected estimate/gate is insufficient."""
    if not isinstance(receipt, Mapping) or receipt.get("schema") != SCHEMA:
        return False
    try:
        expected = _from_receipt_inputs(receipt)
    except (KeyError, TypeError, ValueError):
        return False
    return dict(receipt) == dict(expected)
