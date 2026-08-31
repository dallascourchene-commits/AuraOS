from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from tools.spatial.eye_calibration_contract import (
    BinocularCalibrationV1,
    CameraIntrinsicsV1,
    eligibility_receipt,
)

SCHEMA = "AURA_SPATIAL_CALIBRATION_TEMPORAL_SCOPE_V1"
PARENT_CALIBRATION = "PR621:944c4e52be670d251ebf43b05558f7fab275bed2"
PARENT_TEMPORAL = "PR622:ccc932fc02caf59686e08c3d77ef6154c0cb2b67"
EXACT_PARENT_IDS = (PARENT_CALIBRATION, PARENT_TEMPORAL)
TEMPORAL_SCHEMA = "AuraTemporalEvidenceScopeCoordinateV1"

_TEMPORAL_HARD_FALSE = (
    "point_observation_current_now_proven",
    "historical_series_current_now_proven",
    "shared_current_world_proven",
    "same_host_proven",
    "temporal_overlap_proves_causality",
    "calibrated_metric_eye_truth_proven",
    "physical_steering_authority",
    "producer_authenticated",
    "semantic_k27_authority_proven",
    "effect_authority_proven",
    "native_private_transformer_kv_accessed",
    "gate10_promoted",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _nonnegative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _positive_int(name: str, value: int) -> int:
    value = _nonnegative_int(name, value)
    if value == 0:
        raise ValueError(f"{name} must be positive")
    return value


def _parents(values: Sequence[str]) -> tuple[str, str]:
    if isinstance(values, (str, bytes)):
        raise ValueError("parent_artifact_ids must be a sequence")
    parents = tuple(values)
    if len(parents) != 2 or len(set(parents)) != 2 or set(parents) != set(EXACT_PARENT_IDS):
        raise ValueError("exact O58 parent artifacts are required")
    return EXACT_PARENT_IDS


def verify_parent_temporal_coordinate(value: Mapping[str, Any]) -> bool:
    try:
        payload = dict(value)
        supplied = payload.pop("coordinate_digest")
    except (TypeError, ValueError, KeyError):
        return False
    if payload.get("schema") != TEMPORAL_SCHEMA:
        return False
    if payload.get("point_observation_was_gate_admissible") is not True:
        return False
    if payload.get("point_vs_series_relation") not in {"BEFORE", "DURING", "AFTER"}:
        return False
    if payload.get("temporal_overlap") is not (payload.get("point_vs_series_relation") == "DURING"):
        return False
    if any(payload.get(key) is not False for key in _TEMPORAL_HARD_FALSE):
        return False
    return supplied == _digest(payload)


@dataclass(frozen=True)
class CalibrationTemporalScopeReceipt:
    calibration_eligibility_receipt_sha256: str
    temporal_coordinate_digest: str
    sensor_instance: str
    sensor_runtime_generation: str
    calibration_generation: str
    calibration_observed_at_ns: int
    use_time_ns: int
    calibration_age_ns: int
    max_calibration_age_ns: int
    intrinsics_calibration_ref: str
    binocular_calibration_ref: str
    reprojection_rms_px: float
    eye_origin_sigma_m: float
    declared_scope_admissible: bool = True
    metric_geometry_parent_eligible: bool = True
    calibration_current_now_proven: bool = False
    calibration_accuracy_at_use_time_proven: bool = False
    unchanged_physical_mount_proven: bool = False
    same_physical_world_proven: bool = False
    physical_gaze_accuracy_proven: bool = False
    physical_display_effect_authority: bool = False
    producer_authenticated: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_digest(self) -> str:
        return _digest(self.to_dict())


def bind_calibration_temporal_scope(
    *,
    intrinsics: CameraIntrinsicsV1,
    binocular: BinocularCalibrationV1,
    temporal_coordinate: Mapping[str, Any],
    sensor_instance: str,
    sensor_runtime_generation: str,
    calibration_generation: str,
    calibration_observed_at_ns: int,
    max_calibration_age_ns: int,
    parent_artifact_ids: Sequence[str] = EXACT_PARENT_IDS,
) -> CalibrationTemporalScopeReceipt:
    _parents(parent_artifact_ids)
    if not verify_parent_temporal_coordinate(temporal_coordinate):
        raise ValueError("exact parent temporal coordinate is invalid")

    eligible = eligibility_receipt(intrinsics, binocular)
    if eligible.metric_geometry_eligible is not True:
        raise ValueError("parent calibration is not metric-geometry eligible")
    if eligible.physical_gaze_accuracy_proven is not False:
        raise ValueError("parent calibration ceiling widened")

    use_time_ns = temporal_coordinate.get("point_capture_time_ns")
    use_time_ns = _nonnegative_int("point_capture_time_ns", use_time_ns)
    calibration_observed_at_ns = _nonnegative_int("calibration_observed_at_ns", calibration_observed_at_ns)
    max_calibration_age_ns = _positive_int("max_calibration_age_ns", max_calibration_age_ns)
    if calibration_observed_at_ns > use_time_ns:
        raise ValueError("calibration observation cannot occur after use time")
    age = use_time_ns - calibration_observed_at_ns
    if age > max_calibration_age_ns:
        raise ValueError("calibration lies outside declared temporal scope")
    if intrinsics.reprojection_rms_px is None:
        raise ValueError("calibrated reprojection RMS is required")

    return CalibrationTemporalScopeReceipt(
        calibration_eligibility_receipt_sha256=eligible.receipt_sha256,
        temporal_coordinate_digest=str(temporal_coordinate["coordinate_digest"]),
        sensor_instance=_text("sensor_instance", sensor_instance),
        sensor_runtime_generation=_text("sensor_runtime_generation", sensor_runtime_generation),
        calibration_generation=_text("calibration_generation", calibration_generation),
        calibration_observed_at_ns=calibration_observed_at_ns,
        use_time_ns=use_time_ns,
        calibration_age_ns=age,
        max_calibration_age_ns=max_calibration_age_ns,
        intrinsics_calibration_ref=intrinsics.calibration_ref,
        binocular_calibration_ref=binocular.calibration_ref,
        reprojection_rms_px=float(intrinsics.reprojection_rms_px),
        eye_origin_sigma_m=float(eligible.eye_origin_sigma_m),
    )


def portable_calibration_temporal_scope_receipt(**kwargs: Any) -> dict[str, Any]:
    receipt = bind_calibration_temporal_scope(**kwargs)
    payload = receipt.to_dict()
    return {**payload, "receipt_digest": receipt.receipt_digest, "parent_artifact_ids": EXACT_PARENT_IDS}
