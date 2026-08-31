#!/usr/bin/env python3
"""Producer-traversed calibration/uncertainty membrane for Aura Spatial.

The module deliberately distinguishes:
- nominal assumptions from producer-traversed calibration observations;
- measured values from policy admission;
- recomputable software evidence from physical producer authentication;
- calibration uncertainty from currentness/trust/authority.

It is not a gaze estimator and it does not claim that caller-supplied observation
datasets are physically authentic. Its public metric-geometry methods re-run the
canonical producers over embedded lower inputs before use, so arbitrary enum/ref
strings or caller-authored result fields cannot mint eligibility.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass
from enum import Enum

SCHEMA = "AURA_SPATIAL_EYE_CALIBRATION_V2"
CAMERA_PRODUCER = "AURA_CAMERA_CALIBRATION_PRODUCER_V1"
IPD_PRODUCER = "AURA_IPD_CALIBRATION_PRODUCER_V1"


class CalibrationContractError(ValueError):
    pass


class CoordinateSpace(str, Enum):
    UNDISTORTED_PINHOLE_PIXELS_V1 = "UNDISTORTED_PINHOLE_PIXELS_V1"
    RAW_DISTORTED_PIXELS_V1 = "RAW_DISTORTED_PIXELS_V1"


def _number(value: float, name: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationContractError(f"{name}:REAL_NUMBER_REQUIRED")
    out = float(value)
    if not math.isfinite(out):
        raise CalibrationContractError(f"{name}:FINITE_REQUIRED")
    if positive and out <= 0.0:
        raise CalibrationContractError(f"{name}:POSITIVE_REQUIRED")
    if nonnegative and out < 0.0:
        raise CalibrationContractError(f"{name}:NONNEGATIVE_REQUIRED")
    return out


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CalibrationContractError(f"{name}:POSITIVE_INT_REQUIRED")
    return value


def _clean_id(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise CalibrationContractError(f"{name}:STRING_REQUIRED")
    out = " ".join(value.strip().split())
    if not out or len(out) > 256:
        raise CalibrationContractError(f"{name}:BOUNDED_ID_REQUIRED")
    return out


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CalibrationQualityPolicyV1:
    policy_generation: str
    min_camera_samples: int = 6
    max_camera_reprojection_rms_px: float = 1.0
    min_ipd_samples: int = 3
    max_ipd_sample_sigma_m: float = 0.0025
    min_ipd_m: float = 0.03
    max_ipd_m: float = 0.09

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_generation", _clean_id(self.policy_generation, "policy_generation"))
        object.__setattr__(self, "min_camera_samples", _positive_int(self.min_camera_samples, "min_camera_samples"))
        object.__setattr__(self, "min_ipd_samples", _positive_int(self.min_ipd_samples, "min_ipd_samples"))
        object.__setattr__(
            self, "max_camera_reprojection_rms_px",
            _number(self.max_camera_reprojection_rms_px, "max_camera_reprojection_rms_px", positive=True),
        )
        object.__setattr__(
            self, "max_ipd_sample_sigma_m",
            _number(self.max_ipd_sample_sigma_m, "max_ipd_sample_sigma_m", nonnegative=True),
        )
        object.__setattr__(self, "min_ipd_m", _number(self.min_ipd_m, "min_ipd_m", positive=True))
        object.__setattr__(self, "max_ipd_m", _number(self.max_ipd_m, "max_ipd_m", positive=True))
        if self.min_ipd_m >= self.max_ipd_m:
            raise CalibrationContractError("ipd_policy:INVALID_RANGE")

    @property
    def digest(self) -> str:
        return _digest({"schema": "AURA_CALIBRATION_QUALITY_POLICY_V1", **asdict(self)})


@dataclass(frozen=True)
class CameraCalibrationSampleV1:
    x_over_z: float
    y_over_z: float
    u_px: float
    v_px: float

    def __post_init__(self) -> None:
        for name in ("x_over_z", "y_over_z", "u_px", "v_px"):
            object.__setattr__(self, name, _number(getattr(self, name), name))


@dataclass(frozen=True)
class CameraCalibrationDatasetV1:
    sensor_id: str
    sensor_generation: str
    calibration_generation: str
    width_px: int
    height_px: int
    coordinate_space: CoordinateSpace
    samples: tuple[CameraCalibrationSampleV1, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sensor_id", _clean_id(self.sensor_id, "sensor_id"))
        object.__setattr__(self, "sensor_generation", _clean_id(self.sensor_generation, "sensor_generation"))
        object.__setattr__(self, "calibration_generation", _clean_id(self.calibration_generation, "calibration_generation"))
        object.__setattr__(self, "width_px", _positive_int(self.width_px, "width_px"))
        object.__setattr__(self, "height_px", _positive_int(self.height_px, "height_px"))
        if not isinstance(self.coordinate_space, CoordinateSpace):
            raise CalibrationContractError("coordinate_space:TYPED_VALUE_REQUIRED")
        if not isinstance(self.samples, tuple) or not self.samples:
            raise CalibrationContractError("samples:NONEMPTY_TUPLE_REQUIRED")
        if not all(isinstance(s, CameraCalibrationSampleV1) for s in self.samples):
            raise CalibrationContractError("samples:TYPED_SAMPLE_REQUIRED")

    @property
    def digest(self) -> str:
        return _digest({"schema": "AURA_CAMERA_CALIBRATION_DATASET_V1", **asdict(self)})


@dataclass(frozen=True)
class CameraCalibrationEvidenceV1:
    producer_schema: str
    dataset: CameraCalibrationDatasetV1
    policy: CalibrationQualityPolicyV1
    fx_px: float
    fy_px: float
    cx_px: float
    cy_px: float
    reprojection_rms_px: float
    quality_admitted: bool
    evidence_sha256: str


def _fit_axis(coords: list[float], pixels: list[float], axis: str) -> tuple[float, float]:
    mean_c = statistics.fmean(coords)
    mean_p = statistics.fmean(pixels)
    denom = sum((c - mean_c) ** 2 for c in coords)
    if denom <= 1e-15:
        raise CalibrationContractError(f"{axis}:CALIBRATION_GEOMETRY_DEGENERATE")
    slope = sum((c - mean_c) * (p - mean_p) for c, p in zip(coords, pixels)) / denom
    intercept = mean_p - slope * mean_c
    if slope <= 0.0 or not math.isfinite(slope) or not math.isfinite(intercept):
        raise CalibrationContractError(f"{axis}:INVALID_PINHOLE_FIT")
    return slope, intercept


def _camera_evidence_payload(
    dataset: CameraCalibrationDatasetV1,
    policy: CalibrationQualityPolicyV1,
    fx: float, fy: float, cx: float, cy: float, rms: float, admitted: bool,
) -> dict:
    return {
        "schema": "AURA_CAMERA_CALIBRATION_EVIDENCE_V1",
        "producer_schema": CAMERA_PRODUCER,
        "dataset": asdict(dataset),
        "dataset_digest": dataset.digest,
        "policy": asdict(policy),
        "policy_digest": policy.digest,
        "fx_px": fx, "fy_px": fy, "cx_px": cx, "cy_px": cy,
        "reprojection_rms_px": rms,
        "quality_admitted": admitted,
        "physical_calibration_producer_authenticated": False,
        "physical_3d_accuracy_proven": False,
    }


def produce_camera_calibration_evidence(
    dataset: CameraCalibrationDatasetV1,
    policy: CalibrationQualityPolicyV1,
) -> CameraCalibrationEvidenceV1:
    if dataset.coordinate_space is not CoordinateSpace.UNDISTORTED_PINHOLE_PIXELS_V1:
        raise CalibrationContractError("camera_dataset:UNDISTORTED_PINHOLE_SPACE_REQUIRED")
    xs = [s.x_over_z for s in dataset.samples]
    ys = [s.y_over_z for s in dataset.samples]
    us = [s.u_px for s in dataset.samples]
    vs = [s.v_px for s in dataset.samples]
    fx, cx = _fit_axis(xs, us, "x")
    fy, cy = _fit_axis(ys, vs, "y")
    sq = 0.0
    for s in dataset.samples:
        du = fx * s.x_over_z + cx - s.u_px
        dv = fy * s.y_over_z + cy - s.v_px
        sq += du * du + dv * dv
    rms = math.sqrt(sq / (2.0 * len(dataset.samples)))
    admitted = len(dataset.samples) >= policy.min_camera_samples and rms <= policy.max_camera_reprojection_rms_px
    payload = _camera_evidence_payload(dataset, policy, fx, fy, cx, cy, rms, admitted)
    return CameraCalibrationEvidenceV1(
        producer_schema=CAMERA_PRODUCER,
        dataset=dataset,
        policy=policy,
        fx_px=fx, fy_px=fy, cx_px=cx, cy_px=cy,
        reprojection_rms_px=rms,
        quality_admitted=admitted,
        evidence_sha256=_digest(payload),
    )


def verify_camera_calibration_evidence(evidence: CameraCalibrationEvidenceV1) -> bool:
    if not isinstance(evidence, CameraCalibrationEvidenceV1) or evidence.producer_schema != CAMERA_PRODUCER:
        return False
    try:
        expected = produce_camera_calibration_evidence(evidence.dataset, evidence.policy)
    except CalibrationContractError:
        return False
    return expected == evidence


@dataclass(frozen=True)
class CameraIntrinsicsV2:
    evidence: CameraCalibrationEvidenceV1

    @property
    def metric_ray_eligible(self) -> bool:
        return verify_camera_calibration_evidence(self.evidence) and self.evidence.quality_admitted

    def unit_ray_from_undistorted_pixel(self, u_px: float, v_px: float) -> tuple[float, float, float]:
        if not self.metric_ray_eligible:
            raise CalibrationContractError("intrinsics:PRODUCER_TRAVERSED_CALIBRATION_REQUIRED")
        u = _number(u_px, "u_px")
        v = _number(v_px, "v_px")
        e = self.evidence
        x = (u - e.cx_px) / e.fx_px
        y = (v - e.cy_px) / e.fy_px
        norm = math.sqrt(x * x + y * y + 1.0)
        return (x / norm, y / norm, 1.0 / norm)


@dataclass(frozen=True)
class IpdMeasurementDatasetV1:
    sensor_id: str
    sensor_generation: str
    calibration_generation: str
    coordinate_space: str
    ipd_samples_m: tuple[float, ...]
    midpoint_sigma_m: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "sensor_id", _clean_id(self.sensor_id, "sensor_id"))
        object.__setattr__(self, "sensor_generation", _clean_id(self.sensor_generation, "sensor_generation"))
        object.__setattr__(self, "calibration_generation", _clean_id(self.calibration_generation, "calibration_generation"))
        object.__setattr__(self, "coordinate_space", _clean_id(self.coordinate_space, "coordinate_space"))
        if self.coordinate_space != "HEAD_LOCAL_METERS_V1":
            raise CalibrationContractError("ipd_coordinate_space:HEAD_LOCAL_METERS_V1_REQUIRED")
        if not isinstance(self.ipd_samples_m, tuple) or not self.ipd_samples_m:
            raise CalibrationContractError("ipd_samples_m:NONEMPTY_TUPLE_REQUIRED")
        object.__setattr__(self, "ipd_samples_m", tuple(_number(v, "ipd_sample_m", positive=True) for v in self.ipd_samples_m))
        object.__setattr__(self, "midpoint_sigma_m", _number(self.midpoint_sigma_m, "midpoint_sigma_m", nonnegative=True))

    @property
    def digest(self) -> str:
        return _digest({"schema": "AURA_IPD_MEASUREMENT_DATASET_V1", **asdict(self)})


@dataclass(frozen=True)
class IpdCalibrationEvidenceV1:
    producer_schema: str
    dataset: IpdMeasurementDatasetV1
    policy: CalibrationQualityPolicyV1
    ipd_m: float
    ipd_sample_sigma_m: float
    ipd_mean_sigma_m: float
    midpoint_sigma_m: float
    quality_admitted: bool
    evidence_sha256: str


def _ipd_payload(
    dataset: IpdMeasurementDatasetV1,
    policy: CalibrationQualityPolicyV1,
    mean: float, sample_sigma: float, mean_sigma: float, admitted: bool,
) -> dict:
    return {
        "schema": "AURA_IPD_CALIBRATION_EVIDENCE_V1",
        "producer_schema": IPD_PRODUCER,
        "dataset": asdict(dataset),
        "dataset_digest": dataset.digest,
        "policy": asdict(policy),
        "policy_digest": policy.digest,
        "ipd_m": mean,
        "ipd_sample_sigma_m": sample_sigma,
        "ipd_mean_sigma_m": mean_sigma,
        "midpoint_sigma_m": dataset.midpoint_sigma_m,
        "quality_admitted": admitted,
        "physical_measurement_producer_authenticated": False,
        "user_identity_authenticated": False,
    }


def produce_ipd_calibration_evidence(
    dataset: IpdMeasurementDatasetV1,
    policy: CalibrationQualityPolicyV1,
) -> IpdCalibrationEvidenceV1:
    mean = statistics.fmean(dataset.ipd_samples_m)
    sample_sigma = statistics.stdev(dataset.ipd_samples_m) if len(dataset.ipd_samples_m) >= 2 else math.inf
    mean_sigma = sample_sigma / math.sqrt(len(dataset.ipd_samples_m))
    admitted = (
        len(dataset.ipd_samples_m) >= policy.min_ipd_samples
        and policy.min_ipd_m <= mean <= policy.max_ipd_m
        and sample_sigma <= policy.max_ipd_sample_sigma_m
    )
    payload = _ipd_payload(dataset, policy, mean, sample_sigma, mean_sigma, admitted)
    return IpdCalibrationEvidenceV1(
        producer_schema=IPD_PRODUCER,
        dataset=dataset,
        policy=policy,
        ipd_m=mean,
        ipd_sample_sigma_m=sample_sigma,
        ipd_mean_sigma_m=mean_sigma,
        midpoint_sigma_m=dataset.midpoint_sigma_m,
        quality_admitted=admitted,
        evidence_sha256=_digest(payload),
    )


def verify_ipd_calibration_evidence(evidence: IpdCalibrationEvidenceV1) -> bool:
    if not isinstance(evidence, IpdCalibrationEvidenceV1) or evidence.producer_schema != IPD_PRODUCER:
        return False
    try:
        expected = produce_ipd_calibration_evidence(evidence.dataset, evidence.policy)
    except CalibrationContractError:
        return False
    return expected == evidence


@dataclass(frozen=True)
class BinocularCalibrationV2:
    evidence: IpdCalibrationEvidenceV1

    @property
    def metric_eye_origin_eligible(self) -> bool:
        return verify_ipd_calibration_evidence(self.evidence) and self.evidence.quality_admitted

    @property
    def eye_origin_sigma_m(self) -> float:
        if not self.metric_eye_origin_eligible:
            raise CalibrationContractError("ipd:PRODUCER_TRAVERSED_MEASUREMENT_REQUIRED")
        e = self.evidence
        return math.sqrt(e.midpoint_sigma_m ** 2 + (0.5 * e.ipd_mean_sigma_m) ** 2)

    def eye_origins_about_midpoint(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        if not self.metric_eye_origin_eligible:
            raise CalibrationContractError("ipd:PRODUCER_TRAVERSED_MEASUREMENT_REQUIRED")
        half = self.evidence.ipd_m / 2.0
        return ((-half, 0.0, 0.0), (half, 0.0, 0.0))


def nominal_intrinsics_from_horizontal_fov(*, width_px: int, height_px: int, horizontal_fov_deg: float) -> dict:
    width = _positive_int(width_px, "width_px")
    height = _positive_int(height_px, "height_px")
    fov = _number(horizontal_fov_deg, "horizontal_fov_deg", positive=True)
    if fov >= 179.0:
        raise CalibrationContractError("horizontal_fov_deg:OUT_OF_RANGE")
    fx = width / (2.0 * math.tan(math.radians(fov) / 2.0))
    return {
        "schema": "AURA_NOMINAL_FOV_ASSUMPTION_V1",
        "width_px": width, "height_px": height,
        "horizontal_fov_deg": fov, "fx_px": fx,
        "metric_ray_eligible": False,
        "calibration_evidence": None,
    }


def assumed_population_ipd() -> dict:
    return {
        "schema": "AURA_POPULATION_IPD_ASSUMPTION_V1",
        "ipd_m": 0.064,
        "metric_eye_origin_eligible": False,
        "user_measurement_evidence": None,
    }


def eligibility_receipt(intrinsics: CameraIntrinsicsV2 | dict, binocular: BinocularCalibrationV2 | dict) -> dict:
    camera_ok = isinstance(intrinsics, CameraIntrinsicsV2) and intrinsics.metric_ray_eligible
    ipd_ok = isinstance(binocular, BinocularCalibrationV2) and binocular.metric_eye_origin_eligible
    receipt = {
        "schema": SCHEMA,
        "metric_geometry_eligible": camera_ok and ipd_ok,
        "camera_producer_traversed": camera_ok,
        "ipd_producer_traversed": ipd_ok,
        "quality_policy_separate_from_measurement": True,
        "sensor_generation_bound": camera_ok and ipd_ok,
        "calibration_generation_bound": camera_ok and ipd_ok,
        "coordinate_space_bound": camera_ok and ipd_ok,
        "fixed_64mm_ipd_is_user_ground_truth": False,
        "nominal_fov_is_calibrated_intrinsics": False,
        "renderer_pose_part_of_calibration_identity": False,
        "raw_sensor_persistence_authorized": False,
        "physical_calibration_producer_authenticated": False,
        "physical_gaze_accuracy_proven": False,
        "physical_3d_accuracy_proven": False,
        "vergence_accommodation_conflict_eliminated": False,
        "semantic_k27_authority": False,
        "native_transformer_kv_accessed": False,
    }
    if camera_ok:
        receipt["camera_evidence_sha256"] = intrinsics.evidence.evidence_sha256
        receipt["camera_policy_digest"] = intrinsics.evidence.policy.digest
    if ipd_ok:
        receipt["ipd_evidence_sha256"] = binocular.evidence.evidence_sha256
        receipt["ipd_policy_digest"] = binocular.evidence.policy.digest
        receipt["eye_origin_sigma_m"] = binocular.eye_origin_sigma_m
    receipt["receipt_sha256"] = _digest(receipt)
    return receipt


def _demo_camera_dataset() -> CameraCalibrationDatasetV1:
    fx, fy, cx, cy = 1100.0, 1098.0, 959.5, 539.5
    points = ((-0.3, -0.2), (-0.1, 0.25), (0.0, -0.1), (0.15, 0.1), (0.3, -0.25), (0.4, 0.3))
    return CameraCalibrationDatasetV1(
        sensor_id="fixture-camera",
        sensor_generation="fixture-runtime-1",
        calibration_generation="fixture-cal-1",
        width_px=1920, height_px=1080,
        coordinate_space=CoordinateSpace.UNDISTORTED_PINHOLE_PIXELS_V1,
        samples=tuple(CameraCalibrationSampleV1(x, y, fx*x+cx, fy*y+cy) for x, y in points),
    )


def main() -> None:
    policy = CalibrationQualityPolicyV1(policy_generation="fixture-policy-1")
    receipt = eligibility_receipt(
        CameraIntrinsicsV2(produce_camera_calibration_evidence(_demo_camera_dataset(), policy)),
        assumed_population_ipd(),
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
