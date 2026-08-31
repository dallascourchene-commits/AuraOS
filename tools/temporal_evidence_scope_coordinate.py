"""Bind point evidence to a historical interval without currentness/authentication laundering.

PR610 V2 can prove its software estimator/gate was traversed, but intentionally
does not authenticate physical sensor capture or effect-time currentness. This
coordinate therefore emits UNKNOWN/HOLD until the point evidence itself is
admitted by an appropriate producer/host owner. Time arithmetic cannot upgrade
an unauthenticated timestamp into an observed event.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import calendar
import hashlib
import json
from typing import Any, Mapping

from tools.k27_eye_pose_observation_contract import verify_eye_pose_receipt
from tools.thinkpad_longitudinal_envelope_series import ThinkPadLongitudinalEnvelopeSeries

SCHEMA = "AuraTemporalEvidenceScopeCoordinateV2"
PR610_REPAIR_HEAD = "3503065b862fd23a5df4ecd350a33c49496349a8"
PR614_EXACT_HEAD = "c2c112f627e93b8fd0b11c971be41badd1902cb6"
RELATIONS = {"BEFORE", "DURING", "AFTER", "UNKNOWN"}


class TemporalEvidenceScopeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_time(value: str) -> datetime:
    try:
        out = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise TemporalEvidenceScopeError("SERIES_TIME_INVALID") from exc
    if out.tzinfo is None or out.utcoffset() is None:
        raise TemporalEvidenceScopeError("SERIES_TIME_NOT_OFFSET_AWARE")
    return out.astimezone(timezone.utc)


def _datetime_ns(value: datetime) -> int:
    utc = value.astimezone(timezone.utc)
    return calendar.timegm(utc.utctimetuple()) * 1_000_000_000 + utc.microsecond * 1_000


@dataclass(frozen=True)
class TemporalEvidenceScopeCoordinate:
    eye_pose_receipt_sha256: str
    longitudinal_series_evidence_ref: str
    longitudinal_series_digest: str
    point_capture_time_ns: int
    series_start_time_ns: int
    series_end_time_ns: int
    point_vs_series_relation: str
    temporal_overlap: bool
    eye_k27_coordinate: int
    point_observation_software_gate_admissible: bool
    point_observation_temporal_admissible: bool
    hold_reason: str | None
    point_observation_current_now_proven: bool = False
    historical_series_current_now_proven: bool = False
    shared_current_world_proven: bool = False
    same_host_proven: bool = False
    temporal_overlap_proves_causality: bool = False
    operating_envelope_caused_eye_pose: bool = False
    eye_pose_caused_operating_envelope: bool = False
    calibrated_metric_eye_truth_proven: bool = False
    physical_steering_authority: bool = False
    performance_causality_proven: bool = False
    producer_authenticated: bool = False
    semantic_k27_authority_proven: bool = False
    effect_authority_proven: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def coordinate_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def evidence_ref(self) -> str:
        return "temporal-evidence-scope-sha256:" + self.coordinate_digest


def _validate_series(longitudinal_series: ThinkPadLongitudinalEnvelopeSeries) -> tuple[int, int]:
    if type(longitudinal_series) is not ThinkPadLongitudinalEnvelopeSeries:
        raise TemporalEvidenceScopeError("EXACT_LONGITUDINAL_SERIES_TYPE_REQUIRED")
    if longitudinal_series.historical_series_only is not True:
        raise TemporalEvidenceScopeError("HISTORICAL_SERIES_SCOPE_REQUIRED")
    for name in (
        "same_host_proven", "benchmark_execution_proven", "thermal_throttling_proven",
        "temperature_caused_performance_change", "memory_pressure_caused_performance_change",
        "battery_state_caused_performance_change", "performance_winner_proven",
        "current_now_proven", "producer_authenticated", "g2_admitted", "effect_authority_proven",
    ):
        if getattr(longitudinal_series, name) is not False:
            raise TemporalEvidenceScopeError("LONGITUDINAL_SERIES_CEILING_WIDENED", name)
    summaries = longitudinal_series.phase_summaries
    if len(summaries) != 3:
        raise TemporalEvidenceScopeError("THREE_PHASE_SERIES_REQUIRED")
    start_ns = _datetime_ns(_parse_time(summaries[0]["observed_at_utc"]))
    end_ns = _datetime_ns(_parse_time(summaries[-1]["observed_at_utc"]))
    if start_ns >= end_ns:
        raise TemporalEvidenceScopeError("SERIES_INTERVAL_INVALID")
    return start_ns, end_ns


def bind_temporal_evidence_scope(*, eye_pose_receipt: Mapping[str, object], longitudinal_series: ThinkPadLongitudinalEnvelopeSeries) -> TemporalEvidenceScopeCoordinate:
    eye = dict(eye_pose_receipt)
    if not verify_eye_pose_receipt(eye):
        raise TemporalEvidenceScopeError("EYE_POSE_RECEIPT_INVALID")
    ceiling = eye.get("claim_ceiling")
    if not isinstance(ceiling, dict) or any(value is not False for value in ceiling.values()):
        raise TemporalEvidenceScopeError("EYE_POSE_CLAIM_CEILING_WIDENED")
    gate = eye.get("gate")
    if not isinstance(gate, dict):
        raise TemporalEvidenceScopeError("EYE_POSE_GATE_MISSING")
    software_gate = gate.get("software_gate_admissible") is True
    if gate.get("physical_effect_authority") is not False:
        raise TemporalEvidenceScopeError("EYE_POSE_PARENT_CEILING_WIDENED")

    start_ns, end_ns = _validate_series(longitudinal_series)
    producer_inputs = eye.get("producer_inputs")
    if not isinstance(producer_inputs, dict) or not isinstance(producer_inputs.get("frame"), dict):
        raise TemporalEvidenceScopeError("EYE_FRAME_MISSING")
    capture_ns = producer_inputs["frame"].get("capture_time_ns")
    if isinstance(capture_ns, bool) or not isinstance(capture_ns, int) or capture_ns < 0:
        raise TemporalEvidenceScopeError("EYE_CAPTURE_TIME_INVALID")
    k27 = eye.get("k27_coordinate")
    if isinstance(k27, bool) or not isinstance(k27, int) or not 0 <= k27 <= 26:
        raise TemporalEvidenceScopeError("EYE_K27_METADATA_INVALID")

    temporal_admissible = eye.get("temporal_point_evidence_admissible") is True
    if not software_gate:
        relation, overlap, hold = "UNKNOWN", False, "POINT_SOFTWARE_GATE_NOT_ADMISSIBLE"
    elif not temporal_admissible:
        relation, overlap, hold = "UNKNOWN", False, "POINT_EVIDENCE_NOT_AUTHENTICATED"
    elif capture_ns < start_ns:
        relation, overlap, hold = "BEFORE", False, None
    elif capture_ns > end_ns:
        relation, overlap, hold = "AFTER", False, None
    else:
        relation, overlap, hold = "DURING", True, None

    return TemporalEvidenceScopeCoordinate(
        eye_pose_receipt_sha256=str(eye["receipt_sha256"]),
        longitudinal_series_evidence_ref=longitudinal_series.evidence_ref,
        longitudinal_series_digest=longitudinal_series.series_digest,
        point_capture_time_ns=capture_ns, series_start_time_ns=start_ns, series_end_time_ns=end_ns,
        point_vs_series_relation=relation, temporal_overlap=overlap, eye_k27_coordinate=k27,
        point_observation_software_gate_admissible=software_gate,
        point_observation_temporal_admissible=temporal_admissible, hold_reason=hold,
    )


def verify_temporal_evidence_scope_coordinate(value: Mapping[str, Any]) -> bool:
    try:
        payload = dict(value); supplied = payload.pop("coordinate_digest")
    except (KeyError, TypeError, ValueError):
        return False
    relation = payload.get("point_vs_series_relation")
    if payload.get("schema") != SCHEMA or relation not in RELATIONS:
        return False
    if relation == "UNKNOWN":
        if payload.get("temporal_overlap") is not False or not payload.get("hold_reason"):
            return False
    else:
        if payload.get("point_observation_temporal_admissible") is not True or payload.get("hold_reason") is not None:
            return False
        if payload.get("temporal_overlap") is not (relation == "DURING"):
            return False
    for key in (
        "point_observation_current_now_proven", "historical_series_current_now_proven",
        "shared_current_world_proven", "same_host_proven", "temporal_overlap_proves_causality",
        "operating_envelope_caused_eye_pose", "eye_pose_caused_operating_envelope",
        "calibrated_metric_eye_truth_proven", "physical_steering_authority",
        "performance_causality_proven", "producer_authenticated", "semantic_k27_authority_proven",
        "effect_authority_proven", "native_private_transformer_kv_accessed", "gate10_promoted",
    ):
        if payload.get(key) is not False:
            return False
    return supplied == _digest(payload)


def portable_temporal_evidence_scope_receipt(*, eye_pose_receipt: Mapping[str, object], longitudinal_series: ThinkPadLongitudinalEnvelopeSeries) -> dict[str, Any]:
    coordinate = bind_temporal_evidence_scope(eye_pose_receipt=eye_pose_receipt, longitudinal_series=longitudinal_series)
    payload = coordinate.to_dict()
    return {**payload, "coordinate_digest": coordinate.coordinate_digest}
