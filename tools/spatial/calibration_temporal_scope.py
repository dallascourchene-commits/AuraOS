from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import inspect
import json
from typing import Any, Mapping, Sequence

from tools.spatial.eye_calibration_contract import (
    BinocularCalibrationV2,
    CameraIntrinsicsV2,
    eligibility_receipt,
)
from tools.temporal_evidence_scope_coordinate import (
    PORTABLE_SCOPE as TEMPORAL_PORTABLE_SCOPE,
    SCHEMA as TEMPORAL_SCHEMA,
    verify_temporal_evidence_scope_coordinate,
)

SCHEMA = "AURA_SPATIAL_CALIBRATION_TEMPORAL_SCOPE_V2"
PARENT_CALIBRATION = "PR621:6e635976f009104e02f586cb8658651de5532ec1"
PARENT_TEMPORAL = "PR622:a998e370dd3d757810ebd888f6c982ef9ec9cca0"
EXACT_PARENT_IDS = (PARENT_CALIBRATION, PARENT_TEMPORAL)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


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
        raise ValueError("exact repaired parent artifacts are required")
    return EXACT_PARENT_IDS


@dataclass(frozen=True)
class CalibrationTemporalScopeReceipt:
    calibration_eligibility_receipt_sha256: str
    temporal_coordinate_digest: str
    camera_evidence_sha256: str
    ipd_evidence_sha256: str
    camera_policy_digest: str
    ipd_policy_digest: str
    camera_sensor_id: str
    camera_sensor_generation: str
    camera_calibration_generation: str
    ipd_sensor_id: str
    ipd_sensor_generation: str
    ipd_calibration_generation: str
    declared_calibration_time_ns: int
    declared_use_time_ns: int
    declared_calibration_age_ns: int
    max_declared_calibration_age_ns: int
    reprojection_rms_px: float
    eye_origin_sigma_m: float
    software_scope_candidate: bool
    point_temporal_admissible: bool
    declared_scope_admissible: bool
    hold_reason: str | None
    temporal_parent_schema: str = TEMPORAL_SCHEMA
    temporal_parent_portable_scope: str = TEMPORAL_PORTABLE_SCOPE
    calibration_producer_traversed: bool = True
    ipd_producer_traversed: bool = True
    calibration_time_authenticated: bool = False
    physical_calibration_producer_authenticated: bool = False
    physical_ipd_producer_authenticated: bool = False
    physical_use_admissible: bool = False
    calibration_current_now_proven: bool = False
    calibration_accuracy_at_use_time_proven: bool = False
    sensor_matches_original_calibration_proven: bool = False
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
    intrinsics: CameraIntrinsicsV2,
    binocular: BinocularCalibrationV2,
    temporal_coordinate: Mapping[str, Any],
    declared_calibration_time_ns: int,
    max_declared_calibration_age_ns: int,
    parent_artifact_ids: Sequence[str] = EXACT_PARENT_IDS,
) -> CalibrationTemporalScopeReceipt:
    _parents(parent_artifact_ids)
    if not verify_temporal_evidence_scope_coordinate(temporal_coordinate):
        raise ValueError("exact repaired portable temporal coordinate is invalid")

    eligible = eligibility_receipt(intrinsics, binocular)
    if eligible.get("metric_geometry_eligible") is not True:
        raise ValueError("repaired calibration parents are not metric-geometry eligible")
    if eligible.get("camera_producer_traversed") is not True or eligible.get("ipd_producer_traversed") is not True:
        raise ValueError("producer-traversed calibration evidence is required")
    for name in (
        "physical_calibration_producer_authenticated",
        "physical_gaze_accuracy_proven",
        "physical_3d_accuracy_proven",
        "semantic_k27_authority",
        "native_transformer_kv_accessed",
    ):
        if eligible.get(name) is not False:
            raise ValueError(f"parent calibration ceiling widened: {name}")

    camera_evidence = intrinsics.evidence
    ipd_evidence = binocular.evidence
    if intrinsics.metric_ray_eligible is not True or binocular.metric_eye_origin_eligible is not True:
        raise ValueError("producer traversal recheck failed")

    use_time_ns = _nonnegative_int("point_capture_time_ns", temporal_coordinate.get("point_capture_time_ns"))
    declared_calibration_time_ns = _nonnegative_int("declared_calibration_time_ns", declared_calibration_time_ns)
    max_declared_calibration_age_ns = _positive_int(
        "max_declared_calibration_age_ns", max_declared_calibration_age_ns
    )
    if declared_calibration_time_ns > use_time_ns:
        raise ValueError("declared calibration time cannot occur after declared use time")
    age = use_time_ns - declared_calibration_time_ns
    if age > max_declared_calibration_age_ns:
        raise ValueError("declared calibration time lies outside requested scope")

    point_temporal_admissible = temporal_coordinate.get("point_observation_temporal_admissible") is True
    relation = temporal_coordinate.get("point_vs_series_relation")
    software_scope_candidate = (
        temporal_coordinate.get("schema") == TEMPORAL_SCHEMA
        and temporal_coordinate.get("portable_scope") == TEMPORAL_PORTABLE_SCOPE
        and relation == "UNKNOWN"
        and age <= max_declared_calibration_age_ns
    )
    declared_scope_admissible = software_scope_candidate and point_temporal_admissible
    hold_reason = None if declared_scope_admissible else str(
        temporal_coordinate.get("hold_reason") or "POINT_TEMPORAL_ADMISSION_REQUIRED"
    )

    return CalibrationTemporalScopeReceipt(
        calibration_eligibility_receipt_sha256=str(eligible["receipt_sha256"]),
        temporal_coordinate_digest=str(temporal_coordinate["coordinate_digest"]),
        camera_evidence_sha256=camera_evidence.evidence_sha256,
        ipd_evidence_sha256=ipd_evidence.evidence_sha256,
        camera_policy_digest=camera_evidence.policy.digest,
        ipd_policy_digest=ipd_evidence.policy.digest,
        camera_sensor_id=camera_evidence.dataset.sensor_id,
        camera_sensor_generation=camera_evidence.dataset.sensor_generation,
        camera_calibration_generation=camera_evidence.dataset.calibration_generation,
        ipd_sensor_id=ipd_evidence.dataset.sensor_id,
        ipd_sensor_generation=ipd_evidence.dataset.sensor_generation,
        ipd_calibration_generation=ipd_evidence.dataset.calibration_generation,
        declared_calibration_time_ns=declared_calibration_time_ns,
        declared_use_time_ns=use_time_ns,
        declared_calibration_age_ns=age,
        max_declared_calibration_age_ns=max_declared_calibration_age_ns,
        reprojection_rms_px=float(camera_evidence.reprojection_rms_px),
        eye_origin_sigma_m=float(binocular.eye_origin_sigma_m),
        software_scope_candidate=software_scope_candidate,
        point_temporal_admissible=point_temporal_admissible,
        declared_scope_admissible=declared_scope_admissible,
        hold_reason=hold_reason,
    )


def portable_calibration_temporal_scope_receipt(**kwargs: Any) -> dict[str, Any]:
    receipt = bind_calibration_temporal_scope(**kwargs)
    payload = receipt.to_dict()
    return {
        **payload,
        "receipt_digest": receipt.receipt_digest,
        "parent_artifact_ids": EXACT_PARENT_IDS,
    }


def public_inputs() -> tuple[str, ...]:
    return tuple(inspect.signature(bind_calibration_temporal_scope).parameters)
