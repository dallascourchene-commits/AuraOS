#!/usr/bin/env python3
"""Assumption-aware eye/camera geometry contract for Aura Spatial.

This module does not implement a gaze estimator. It classifies whether metric
geometry is admissible from supplied calibration evidence and propagates a
bounded uncertainty for left/right eye origins. Population IPD constants and
nominal-FOV intrinsics remain typed assumptions, never user-specific truth.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum

SCHEMA = "AURA_SPATIAL_EYE_CALIBRATION_V1"


class CalibrationContractError(ValueError):
    pass


class IntrinsicsSource(str, Enum):
    CALIBRATED = "CALIBRATED"
    NOMINAL_FOV_ASSUMPTION = "NOMINAL_FOV_ASSUMPTION"


class IpdSource(str, Enum):
    MEASURED_USER = "MEASURED_USER"
    ASSUMED_POPULATION = "ASSUMED_POPULATION"


def _finite_positive(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0.0:
        raise CalibrationContractError(f"{name}:POSITIVE_FINITE_REQUIRED")
    return float(value)


def _finite_nonnegative(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0.0:
        raise CalibrationContractError(f"{name}:NONNEGATIVE_FINITE_REQUIRED")
    return float(value)


def _evidence_ref(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 1024:
        raise CalibrationContractError(f"{name}:EVIDENCE_REF_REQUIRED")
    return " ".join(value.strip().split())


@dataclass(frozen=True)
class CameraIntrinsicsV1:
    width_px: int
    height_px: int
    fx_px: float
    fy_px: float
    cx_px: float
    cy_px: float
    source: IntrinsicsSource
    calibration_ref: str
    reprojection_rms_px: float | None = None
    pixels_are_undistorted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.width_px, int) or self.width_px <= 0:
            raise CalibrationContractError("width_px:POSITIVE_INT_REQUIRED")
        if not isinstance(self.height_px, int) or self.height_px <= 0:
            raise CalibrationContractError("height_px:POSITIVE_INT_REQUIRED")
        object.__setattr__(self, "fx_px", _finite_positive(self.fx_px, "fx_px"))
        object.__setattr__(self, "fy_px", _finite_positive(self.fy_px, "fy_px"))
        for name in ("cx_px", "cy_px"):
            value = float(getattr(self, name))
            if not math.isfinite(value):
                raise CalibrationContractError(f"{name}:FINITE_REQUIRED")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "calibration_ref", _evidence_ref(self.calibration_ref, "calibration_ref"))
        if self.reprojection_rms_px is not None:
            object.__setattr__(
                self,
                "reprojection_rms_px",
                _finite_nonnegative(self.reprojection_rms_px, "reprojection_rms_px"),
            )
        if self.source is IntrinsicsSource.CALIBRATED and self.reprojection_rms_px is None:
            raise CalibrationContractError("reprojection_rms_px:REQUIRED_FOR_CALIBRATED")

    @property
    def metric_ray_eligible(self) -> bool:
        return (
            self.source is IntrinsicsSource.CALIBRATED
            and self.reprojection_rms_px is not None
            and self.pixels_are_undistorted
        )

    def unit_ray_from_undistorted_pixel(self, u_px: float, v_px: float) -> tuple[float, float, float]:
        if not self.metric_ray_eligible:
            raise CalibrationContractError("intrinsics:METRIC_RAY_NOT_ADMITTED")
        if not all(math.isfinite(float(v)) for v in (u_px, v_px)):
            raise CalibrationContractError("pixel:FINITE_REQUIRED")
        x = (float(u_px) - self.cx_px) / self.fx_px
        y = (float(v_px) - self.cy_px) / self.fy_px
        norm = math.sqrt(x * x + y * y + 1.0)
        return (x / norm, y / norm, 1.0 / norm)


@dataclass(frozen=True)
class BinocularCalibrationV1:
    ipd_m: float
    ipd_sigma_m: float
    midpoint_sigma_m: float
    source: IpdSource
    calibration_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ipd_m", _finite_positive(self.ipd_m, "ipd_m"))
        if not 0.03 <= self.ipd_m <= 0.09:
            raise CalibrationContractError("ipd_m:OUT_OF_BOUNDED_HUMAN_RANGE")
        object.__setattr__(self, "ipd_sigma_m", _finite_nonnegative(self.ipd_sigma_m, "ipd_sigma_m"))
        object.__setattr__(self, "midpoint_sigma_m", _finite_nonnegative(self.midpoint_sigma_m, "midpoint_sigma_m"))
        object.__setattr__(self, "calibration_ref", _evidence_ref(self.calibration_ref, "calibration_ref"))

    @property
    def metric_eye_origin_eligible(self) -> bool:
        return self.source is IpdSource.MEASURED_USER

    @property
    def eye_origin_sigma_m(self) -> float:
        # x_eye = x_mid +/- IPD/2, treating the two supplied uncertainties as
        # independent calibration terms for this bounded receipt.
        return math.sqrt(self.midpoint_sigma_m**2 + (0.5 * self.ipd_sigma_m) ** 2)

    def eye_origins_about_midpoint(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        if not self.metric_eye_origin_eligible:
            raise CalibrationContractError("ipd:METRIC_EYE_ORIGIN_NOT_ADMITTED")
        half = self.ipd_m / 2.0
        return ((-half, 0.0, 0.0), (half, 0.0, 0.0))


def nominal_intrinsics_from_horizontal_fov(
    *, width_px: int, height_px: int, horizontal_fov_deg: float
) -> CameraIntrinsicsV1:
    """Create typed nominal intrinsics that can never emit an admitted metric ray."""
    if not isinstance(width_px, int) or width_px <= 0 or not isinstance(height_px, int) or height_px <= 0:
        raise CalibrationContractError("image_size:POSITIVE_INT_REQUIRED")
    fov = _finite_positive(horizontal_fov_deg, "horizontal_fov_deg")
    if fov >= 179.0:
        raise CalibrationContractError("horizontal_fov_deg:OUT_OF_RANGE")
    fx = width_px / (2.0 * math.tan(math.radians(fov) / 2.0))
    return CameraIntrinsicsV1(
        width_px=width_px,
        height_px=height_px,
        fx_px=fx,
        fy_px=fx,
        cx_px=(width_px - 1) / 2.0,
        cy_px=(height_px - 1) / 2.0,
        source=IntrinsicsSource.NOMINAL_FOV_ASSUMPTION,
        calibration_ref=f"nominal:fov:{fov:g}",
        reprojection_rms_px=None,
        pixels_are_undistorted=False,
    )


def assumed_population_ipd(ipd_m: float = 0.064) -> BinocularCalibrationV1:
    """Represent the imported 64 mm constant honestly as an assumption."""
    return BinocularCalibrationV1(
        ipd_m=ipd_m,
        ipd_sigma_m=0.0,
        midpoint_sigma_m=0.0,
        source=IpdSource.ASSUMED_POPULATION,
        calibration_ref="assumption:population-ipd",
    )


@dataclass(frozen=True)
class EyeGeometryEligibilityReceiptV1:
    schema: str
    intrinsics_source: str
    ipd_source: str
    intrinsics_metric_ray_eligible: bool
    ipd_metric_eye_origin_eligible: bool
    metric_geometry_eligible: bool
    eye_origin_sigma_m: float
    renderer_pose_part_of_calibration_identity: bool
    fixed_64mm_ipd_is_user_ground_truth: bool
    nominal_fov_is_calibrated_intrinsics: bool
    raw_sensor_persistence_authorized: bool
    physical_gaze_accuracy_proven: bool
    vergence_accommodation_conflict_eliminated: bool
    semantic_k27_authority: bool
    native_transformer_kv_accessed: bool
    receipt_sha256: str = ""


def eligibility_receipt(
    intrinsics: CameraIntrinsicsV1,
    binocular: BinocularCalibrationV1,
) -> EyeGeometryEligibilityReceiptV1:
    metric = intrinsics.metric_ray_eligible and binocular.metric_eye_origin_eligible
    unsigned = EyeGeometryEligibilityReceiptV1(
        schema=SCHEMA,
        intrinsics_source=intrinsics.source.value,
        ipd_source=binocular.source.value,
        intrinsics_metric_ray_eligible=intrinsics.metric_ray_eligible,
        ipd_metric_eye_origin_eligible=binocular.metric_eye_origin_eligible,
        metric_geometry_eligible=metric,
        eye_origin_sigma_m=binocular.eye_origin_sigma_m,
        renderer_pose_part_of_calibration_identity=False,
        fixed_64mm_ipd_is_user_ground_truth=False,
        nominal_fov_is_calibrated_intrinsics=False,
        raw_sensor_persistence_authorized=False,
        physical_gaze_accuracy_proven=False,
        vergence_accommodation_conflict_eliminated=False,
        semantic_k27_authority=False,
        native_transformer_kv_accessed=False,
    )
    raw = json.dumps(asdict(unsigned), sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    return EyeGeometryEligibilityReceiptV1(**{**asdict(unsigned), "receipt_sha256": digest})


if __name__ == "__main__":
    nominal = nominal_intrinsics_from_horizontal_fov(width_px=1920, height_px=1080, horizontal_fov_deg=90.0)
    assumed = assumed_population_ipd()
    print(json.dumps(asdict(eligibility_receipt(nominal, assumed)), indent=2, sort_keys=True))
