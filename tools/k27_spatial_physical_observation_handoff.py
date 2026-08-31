from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from hashlib import sha256
import json
import math
import re
from typing import Mapping, Sequence

from tools.temporal_evidence_scope_coordinate import (
    PORTABLE_SCOPE as TEMPORAL_PORTABLE_SCOPE,
    SCHEMA as TEMPORAL_SCHEMA,
    verify_temporal_evidence_scope_coordinate,
)

SCHEMA = "AURA_K27_SPATIAL_PHYSICAL_OBSERVATION_HANDOFF_V2"
PARENT_TEMPORAL = "PR622:a998e370dd3d757810ebd888f6c982ef9ec9cca0"
PARENT_OWNER_HOST = "PR582:24a5404ee3b987dee12192917e40b35d3a43e81c"
EXACT_PARENT_IDS = (PARENT_TEMPORAL, PARENT_OWNER_HOST)

ALLOWED_METRICS = frozenset({
    "speckle_contrast",
    "forward_leakage_ratio",
    "reconstruction_nrmse",
    "command_to_photon_latency_ms",
})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _sha256(name: str, value: str) -> str:
    value = _text(name, value).lower()
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _metric_names(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("requested_metrics must be a sequence")
    names = tuple(sorted({_text("metric", value) for value in values}))
    if not names:
        raise ValueError("at least one metric is required")
    unknown = set(names) - ALLOWED_METRICS
    if unknown:
        raise ValueError(f"unsupported metrics: {sorted(unknown)}")
    return names


def _parents(values: Sequence[str]) -> tuple[str, str]:
    if isinstance(values, (str, bytes)):
        raise ValueError("parent_artifact_ids must be a sequence")
    parents = tuple(values)
    if len(parents) != 2 or len(set(parents)) != 2 or set(parents) != set(EXACT_PARENT_IDS):
        raise ValueError("parent artifact ids must match the exact repaired O57 parents")
    return EXACT_PARENT_IDS


@dataclass(frozen=True)
class SpatialPhysicalObservationRequest:
    temporal_coordinate: InitVar[Mapping[str, object]]
    phase_mask_artifact_digest: str
    display_device_instance: str
    display_runtime_generation: str
    calibration_evidence_ref: str
    optical_bench_setup_digest: str
    requested_metrics: tuple[str, ...]
    max_wall_ms: int
    max_capture_bytes: int
    effect_admission_ref: str
    parent_artifact_ids: tuple[str, str] = EXACT_PARENT_IDS
    temporal_coordinate_digest: str = field(init=False)
    temporal_schema: str = field(init=False)
    temporal_portable_scope: str = field(init=False)
    temporal_point_admissible: bool = field(init=False)
    temporal_hold_reason: str = field(init=False)

    def __post_init__(self, temporal_coordinate: Mapping[str, object]) -> None:
        try:
            temporal = dict(temporal_coordinate)
        except (TypeError, ValueError) as exc:
            raise ValueError("temporal_coordinate must be a mapping") from exc
        if not verify_temporal_evidence_scope_coordinate(temporal):
            raise ValueError("exact repaired portable temporal coordinate is invalid")
        if temporal.get("schema") != TEMPORAL_SCHEMA:
            raise ValueError("temporal schema is not the repaired V3 schema")
        if temporal.get("portable_scope") != TEMPORAL_PORTABLE_SCOPE:
            raise ValueError("temporal portable scope mismatch")
        if temporal.get("point_observation_temporal_admissible") is not False:
            raise ValueError("V2 physical handoff cannot consume self-promoted temporal admission")
        hold = temporal.get("hold_reason")
        if hold not in {"POINT_EVIDENCE_NOT_AUTHENTICATED", "POINT_SOFTWARE_GATE_NOT_ADMISSIBLE"}:
            raise ValueError("typed temporal hold is required")
        object.__setattr__(self, "temporal_coordinate_digest", _sha256("coordinate_digest", str(temporal["coordinate_digest"])))
        object.__setattr__(self, "temporal_schema", str(temporal["schema"]))
        object.__setattr__(self, "temporal_portable_scope", str(temporal["portable_scope"]))
        object.__setattr__(self, "temporal_point_admissible", False)
        object.__setattr__(self, "temporal_hold_reason", str(hold))
        object.__setattr__(self, "phase_mask_artifact_digest", _sha256("phase_mask_artifact_digest", self.phase_mask_artifact_digest))
        object.__setattr__(self, "display_device_instance", _text("display_device_instance", self.display_device_instance))
        object.__setattr__(self, "display_runtime_generation", _text("display_runtime_generation", self.display_runtime_generation))
        object.__setattr__(self, "calibration_evidence_ref", _text("calibration_evidence_ref", self.calibration_evidence_ref))
        object.__setattr__(self, "optical_bench_setup_digest", _sha256("optical_bench_setup_digest", self.optical_bench_setup_digest))
        object.__setattr__(self, "requested_metrics", _metric_names(self.requested_metrics))
        object.__setattr__(self, "max_wall_ms", _positive_int("max_wall_ms", self.max_wall_ms))
        object.__setattr__(self, "max_capture_bytes", _positive_int("max_capture_bytes", self.max_capture_bytes))
        object.__setattr__(self, "effect_admission_ref", _text("effect_admission_ref", self.effect_admission_ref))
        object.__setattr__(self, "parent_artifact_ids", _parents(self.parent_artifact_ids))

    @property
    def request_digest(self) -> str:
        return _digest({
            "schema": SCHEMA,
            "kind": "request",
            "temporal_coordinate_digest": self.temporal_coordinate_digest,
            "temporal_schema": self.temporal_schema,
            "temporal_portable_scope": self.temporal_portable_scope,
            "temporal_point_admissible": self.temporal_point_admissible,
            "temporal_hold_reason": self.temporal_hold_reason,
            "phase_mask_artifact_digest": self.phase_mask_artifact_digest,
            "display_device_instance": self.display_device_instance,
            "display_runtime_generation": self.display_runtime_generation,
            "calibration_evidence_ref": self.calibration_evidence_ref,
            "optical_bench_setup_digest": self.optical_bench_setup_digest,
            "requested_metrics": self.requested_metrics,
            "max_wall_ms": self.max_wall_ms,
            "max_capture_bytes": self.max_capture_bytes,
            "effect_admission_ref": self.effect_admission_ref,
            "parent_artifact_ids": self.parent_artifact_ids,
        })


@dataclass(frozen=True)
class SpatialPhysicalObservationAttempt:
    request_digest: str
    observer_instance: str
    observer_runtime_generation: str
    started_at_unix_ns: int
    ended_at_unix_ns: int
    observed_display_device_instance: str
    observed_display_runtime_generation: str
    observed_calibration_evidence_ref: str
    observed_phase_mask_artifact_digest: str
    observed_optical_bench_setup_digest: str
    raw_capture_digest: str
    raw_capture_bytes: int
    measurement_artifact_digest: str
    reported_metrics: Mapping[str, float]
    process_exit_code: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_digest", _sha256("request_digest", self.request_digest))
        object.__setattr__(self, "observer_instance", _text("observer_instance", self.observer_instance))
        object.__setattr__(self, "observer_runtime_generation", _text("observer_runtime_generation", self.observer_runtime_generation))
        object.__setattr__(self, "started_at_unix_ns", _nonnegative_int("started_at_unix_ns", self.started_at_unix_ns))
        object.__setattr__(self, "ended_at_unix_ns", _nonnegative_int("ended_at_unix_ns", self.ended_at_unix_ns))
        if self.ended_at_unix_ns < self.started_at_unix_ns:
            raise ValueError("ended_at_unix_ns must not precede started_at_unix_ns")
        object.__setattr__(self, "observed_display_device_instance", _text("observed_display_device_instance", self.observed_display_device_instance))
        object.__setattr__(self, "observed_display_runtime_generation", _text("observed_display_runtime_generation", self.observed_display_runtime_generation))
        object.__setattr__(self, "observed_calibration_evidence_ref", _text("observed_calibration_evidence_ref", self.observed_calibration_evidence_ref))
        object.__setattr__(self, "observed_phase_mask_artifact_digest", _sha256("observed_phase_mask_artifact_digest", self.observed_phase_mask_artifact_digest))
        object.__setattr__(self, "observed_optical_bench_setup_digest", _sha256("observed_optical_bench_setup_digest", self.observed_optical_bench_setup_digest))
        object.__setattr__(self, "raw_capture_digest", _sha256("raw_capture_digest", self.raw_capture_digest))
        object.__setattr__(self, "raw_capture_bytes", _nonnegative_int("raw_capture_bytes", self.raw_capture_bytes))
        object.__setattr__(self, "measurement_artifact_digest", _sha256("measurement_artifact_digest", self.measurement_artifact_digest))
        if isinstance(self.process_exit_code, bool) or not isinstance(self.process_exit_code, int):
            raise ValueError("process_exit_code must be an integer")
        metrics = {}
        for key, value in self.reported_metrics.items():
            key = _text("metric name", key)
            if key not in ALLOWED_METRICS:
                raise ValueError(f"unsupported metric: {key}")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0:
                raise ValueError(f"metric {key} must be finite and non-negative")
            metrics[key] = float(value)
        object.__setattr__(self, "reported_metrics", dict(sorted(metrics.items())))

    @property
    def attempt_digest(self) -> str:
        return _digest({
            "schema": SCHEMA,
            "kind": "attempt",
            "request_digest": self.request_digest,
            "observer_instance": self.observer_instance,
            "observer_runtime_generation": self.observer_runtime_generation,
            "started_at_unix_ns": self.started_at_unix_ns,
            "ended_at_unix_ns": self.ended_at_unix_ns,
            "observed_display_device_instance": self.observed_display_device_instance,
            "observed_display_runtime_generation": self.observed_display_runtime_generation,
            "observed_calibration_evidence_ref": self.observed_calibration_evidence_ref,
            "observed_phase_mask_artifact_digest": self.observed_phase_mask_artifact_digest,
            "observed_optical_bench_setup_digest": self.observed_optical_bench_setup_digest,
            "raw_capture_digest": self.raw_capture_digest,
            "raw_capture_bytes": self.raw_capture_bytes,
            "measurement_artifact_digest": self.measurement_artifact_digest,
            "reported_metrics": self.reported_metrics,
            "process_exit_code": self.process_exit_code,
        })


def join_spatial_physical_observation(
    request: SpatialPhysicalObservationRequest,
    attempt: SpatialPhysicalObservationAttempt,
) -> dict[str, object]:
    if attempt.request_digest != request.request_digest:
        raise ValueError("attempt/request digest mismatch")
    if attempt.observed_display_device_instance != request.display_device_instance:
        raise ValueError("display device instance mismatch")
    if attempt.observed_display_runtime_generation != request.display_runtime_generation:
        raise ValueError("display runtime generation mismatch")
    if attempt.observed_calibration_evidence_ref != request.calibration_evidence_ref:
        raise ValueError("calibration evidence reference mismatch")
    if attempt.observed_phase_mask_artifact_digest != request.phase_mask_artifact_digest:
        raise ValueError("phase-mask artifact mismatch")
    if attempt.observed_optical_bench_setup_digest != request.optical_bench_setup_digest:
        raise ValueError("optical bench setup mismatch")
    if attempt.raw_capture_bytes > request.max_capture_bytes:
        raise ValueError("raw capture exceeded request budget")
    if attempt.ended_at_unix_ns - attempt.started_at_unix_ns > request.max_wall_ms * 1_000_000:
        raise ValueError("attempt exceeded wall-time budget")
    if set(attempt.reported_metrics) != set(request.requested_metrics):
        raise ValueError("reported metric set does not match request")
    if attempt.process_exit_code != 0:
        raise ValueError("attempt did not exit successfully")

    reported_observation_digest = _digest({
        "request_digest": request.request_digest,
        "attempt_digest": attempt.attempt_digest,
        "temporal_coordinate_digest": request.temporal_coordinate_digest,
        "measurement_artifact_digest": attempt.measurement_artifact_digest,
    })
    return {
        "schema": SCHEMA,
        "request_digest": request.request_digest,
        "attempt_digest": attempt.attempt_digest,
        "reported_observation_digest": reported_observation_digest,
        "integrity_joined": True,
        "reported_measurement_present": True,
        "temporal_portable_verified": True,
        "temporal_coordinate_bound": True,
        "temporal_point_admissible": False,
        "temporal_hold_reason": request.temporal_hold_reason,
        "physical_attempt_cannot_upgrade_temporal_parent": True,
        "display_generation_bound": True,
        "calibration_reference_bound": True,
        "phase_mask_identity_bound": True,
        "raw_capture_bound": True,
        "producer_authenticated": False,
        "physical_measurement_attested": False,
        "optical_truth_proven": False,
        "speckle_reduction_proven": False,
        "zero_forward_leakage_proven": False,
        "privacy_proven": False,
        "optical_safety_proven": False,
        "deployment_ready": False,
        "effect_authority_proven": False,
        "gate10_promoted": False,
        "native_transformer_kv_accessed": False,
        "k27_semantic_authority": False,
    }


def build_receipt(
    request: SpatialPhysicalObservationRequest,
    attempt: SpatialPhysicalObservationAttempt,
) -> dict[str, object]:
    joined = join_spatial_physical_observation(request, attempt)
    receipt = {
        "schema": SCHEMA,
        "parent_artifact_ids": request.parent_artifact_ids,
        "request": {
            "request_digest": request.request_digest,
            "temporal_coordinate_digest": request.temporal_coordinate_digest,
            "temporal_schema": request.temporal_schema,
            "temporal_portable_scope": request.temporal_portable_scope,
            "temporal_point_admissible": request.temporal_point_admissible,
            "temporal_hold_reason": request.temporal_hold_reason,
            "requested_metrics": request.requested_metrics,
            "effect_admission_ref": request.effect_admission_ref,
        },
        "attempt": {
            "attempt_digest": attempt.attempt_digest,
            "reported_metrics": attempt.reported_metrics,
        },
        "join": joined,
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt
