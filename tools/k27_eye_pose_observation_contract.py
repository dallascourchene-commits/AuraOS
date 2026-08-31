"""Temporal/common-cut eye-pose evidence contract for K27 spatial-display experiments.

This contract imports the useful geometry from a camera/landmark proposal while
preserving calibration, sensor-runtime identity, model generation, freshness,
and metric-truth boundaries as explicit evidence planes.

It authorizes no physical display effect.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence


SCHEMA = "AURA_K27_EYE_POSE_OBSERVATION_COMMON_CUT_V1"
POSE_CLASS = "CALIBRATED_ASSUMED_IPD_GEOMETRIC_ESTIMATE"
K27_SCHEME = "K27-B3MOD27-XYZ-v1"


def _finite_positive(name: str, value: float) -> float:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _finite(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


@dataclass(frozen=True)
class CameraCalibration:
    sensor_instance_id: str
    runtime_generation: str
    calibration_generation: str
    fx_px: float
    fy_px: float
    cx_px: float
    cy_px: float
    image_width_px: int
    image_height_px: int

    def validate(self) -> None:
        for name in ("sensor_instance_id", "runtime_generation", "calibration_generation"):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        _finite_positive("fx_px", self.fx_px)
        _finite_positive("fy_px", self.fy_px)
        _finite("cx_px", self.cx_px)
        _finite("cy_px", self.cy_px)
        if isinstance(self.image_width_px, bool) or self.image_width_px <= 0:
            raise ValueError("image_width_px must be a positive integer")
        if isinstance(self.image_height_px, bool) or self.image_height_px <= 0:
            raise ValueError("image_height_px must be a positive integer")


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
        for name in (
            "sensor_instance_id",
            "runtime_generation",
            "frame_id",
            "landmark_model_generation",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        if isinstance(self.capture_time_ns, bool) or not isinstance(self.capture_time_ns, int):
            raise TypeError("capture_time_ns must be an integer")
        if self.capture_time_ns < 0:
            raise ValueError("capture_time_ns must be non-negative")
        if not math.isfinite(self.tracking_confidence) or not 0.0 <= self.tracking_confidence <= 1.0:
            raise ValueError("tracking_confidence must be within [0,1]")
        for name in (
            "left_iris_x_px",
            "left_iris_y_px",
            "right_iris_x_px",
            "right_iris_y_px",
        ):
            _finite(name, getattr(self, name))


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
    admissible: bool
    refusals: tuple[str, ...]
    common_cut_proven: bool
    freshness_proven: bool
    calibration_current: bool
    landmark_model_current: bool
    physical_effect_authority: bool = False


def estimate_eye_pose_from_assumed_ipd(
    *,
    frame: IrisFrameObservation,
    calibration: CameraCalibration,
    assumed_ipd_m: float,
) -> EyePoseEstimate:
    """Estimate camera-relative pose using calibrated intrinsics + assumed IPD.

    This is intentionally typed as an estimate: assumed IPD is not per-user
    metrology and the result is never promoted to physical steering authority.
    """
    frame.validate()
    calibration.validate()
    _finite_positive("assumed_ipd_m", assumed_ipd_m)
    if (
        frame.sensor_instance_id != calibration.sensor_instance_id
        or frame.runtime_generation != calibration.runtime_generation
    ):
        raise ValueError("frame and calibration are not from the same sensor runtime cut")

    dx = frame.right_iris_x_px - frame.left_iris_x_px
    dy = frame.right_iris_y_px - frame.left_iris_y_px
    pixel_ipd = math.hypot(dx, dy)
    if pixel_ipd <= 0.0:
        raise ValueError("observed pixel IPD must be positive")

    mid_x = 0.5 * (frame.left_iris_x_px + frame.right_iris_x_px)
    mid_y = 0.5 * (frame.left_iris_y_px + frame.right_iris_y_px)
    z_m = calibration.fx_px * assumed_ipd_m / pixel_ipd
    x_m = (mid_x - calibration.cx_px) * z_m / calibration.fx_px
    y_m = (mid_y - calibration.cy_px) * z_m / calibration.fy_px
    return EyePoseEstimate(x_m=x_m, y_m=y_m, z_m=z_m, assumed_ipd_m=assumed_ipd_m)


def gate_eye_pose_for_steering(
    *,
    frame: IrisFrameObservation,
    calibration: CameraCalibration,
    now_ns: int,
    max_age_ns: int,
    expected_sensor_instance_id: str,
    expected_runtime_generation: str,
    expected_calibration_generation: str,
    expected_landmark_model_generation: str,
    minimum_tracking_confidence: float,
) -> SteeringGate:
    """Check the effect-time observation membrane without authorizing an effect."""
    frame.validate()
    calibration.validate()
    if isinstance(now_ns, bool) or not isinstance(now_ns, int):
        raise TypeError("now_ns must be an integer")
    if isinstance(max_age_ns, bool) or not isinstance(max_age_ns, int) or max_age_ns < 0:
        raise ValueError("max_age_ns must be a non-negative integer")
    if not math.isfinite(minimum_tracking_confidence) or not 0.0 <= minimum_tracking_confidence <= 1.0:
        raise ValueError("minimum_tracking_confidence must be within [0,1]")

    refusals: list[str] = []
    same_cut = (
        frame.sensor_instance_id == calibration.sensor_instance_id == expected_sensor_instance_id
        and frame.runtime_generation == calibration.runtime_generation == expected_runtime_generation
    )
    if not same_cut:
        refusals.append("SENSOR_RUNTIME_COMMON_CUT_MISMATCH")

    calibration_current = calibration.calibration_generation == expected_calibration_generation
    if not calibration_current:
        refusals.append("CALIBRATION_GENERATION_MISMATCH")

    model_current = frame.landmark_model_generation == expected_landmark_model_generation
    if not model_current:
        refusals.append("LANDMARK_MODEL_GENERATION_MISMATCH")

    age_ns = now_ns - frame.capture_time_ns
    freshness = 0 <= age_ns <= max_age_ns
    if not freshness:
        refusals.append("FRAME_STALE_OR_FROM_FUTURE")

    if frame.tracking_confidence < minimum_tracking_confidence:
        refusals.append("TRACKING_CONFIDENCE_BELOW_GATE")

    return SteeringGate(
        admissible=not refusals,
        refusals=tuple(refusals),
        common_cut_proven=same_cut,
        freshness_proven=freshness,
        calibration_current=calibration_current,
        landmark_model_current=model_current,
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_eye_pose_receipt(
    *,
    frame: IrisFrameObservation,
    calibration: CameraCalibration,
    estimate: EyePoseEstimate,
    gate: SteeringGate,
    k27_coordinate: int,
    parent_artifact_ids: Sequence[str],
) -> Mapping[str, object]:
    """Create a portable evidence receipt. K27 remains metadata, never authority."""
    if isinstance(k27_coordinate, bool) or not isinstance(k27_coordinate, int) or not 0 <= k27_coordinate <= 26:
        raise ValueError("k27_coordinate must be an integer in [0,26]")
    parents = tuple(parent_artifact_ids)
    if len(parents) != 2 or len(set(parents)) != 2 or any(not p for p in parents):
        raise ValueError("exactly two distinct non-empty parent artifact IDs are required")

    payload = {
        "schema": SCHEMA,
        "k27_scheme": K27_SCHEME,
        "k27_coordinate": k27_coordinate,
        "parent_artifact_ids": parents,
        "frame": asdict(frame),
        "calibration": asdict(calibration),
        "estimate": asdict(estimate),
        "gate": asdict(gate),
        "claim_ceiling": {
            "camera_pose_is_metric_ground_truth": False,
            "k27_coordinate_is_authority": False,
            "physical_display_effect_authorized": False,
            "optical_safety_proven": False,
            "deployment_ready": False,
            "gate10_promoted": False,
        },
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {**payload, "receipt_sha256": digest}


def verify_eye_pose_receipt(receipt: Mapping[str, object]) -> bool:
    expected = {
        "schema",
        "k27_scheme",
        "k27_coordinate",
        "parent_artifact_ids",
        "frame",
        "calibration",
        "estimate",
        "gate",
        "claim_ceiling",
        "receipt_sha256",
    }
    if set(receipt) != expected:
        return False
    if receipt.get("schema") != SCHEMA or receipt.get("k27_scheme") != K27_SCHEME:
        return False
    ceiling = receipt.get("claim_ceiling")
    if not isinstance(ceiling, dict) or not ceiling or any(v is not False for v in ceiling.values()):
        return False
    payload = {key: receipt[key] for key in expected if key != "receipt_sha256"}
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return receipt.get("receipt_sha256") == digest
