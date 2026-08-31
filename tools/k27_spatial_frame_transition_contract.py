"""Producer-traversed binding for one K27 spatial presentation-frame candidate.

The consumer no longer accepts a serialized eye receipt. It receives the lower
eye observation/calibration/policy inputs and invokes the repaired PR610 producer
internally. A software same-frame candidate may be derived, but evidence cannot
be promoted to an authenticated same-transition fact while PR610 intentionally
keeps physical sensor/temporal admission false.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Sequence

import k27_eye_pose_observation_contract as eye
import k27_phase_mask_artifact_contract as phase

SCHEMA = "AURA_K27_SPATIAL_FRAME_TRANSITION_V2"


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError("expected receipt digest must be 64 hex characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("expected receipt digest must be hexadecimal") from exc
    return value.lower()


@dataclass(frozen=True)
class SpatialFrameIntent:
    presentation_frame_id: str
    presentation_time_ns: int
    display_pipeline_generation: str
    expected_eye_receipt_sha256: str
    expected_phase_receipt_sha256: str
    max_eye_age_at_presentation_ns: int

    def validate(self) -> None:
        if not isinstance(self.presentation_frame_id, str) or not self.presentation_frame_id.strip():
            raise ValueError("presentation_frame_id must be non-empty")
        if not isinstance(self.display_pipeline_generation, str) or not self.display_pipeline_generation.strip():
            raise ValueError("display_pipeline_generation must be non-empty")
        for name in ("presentation_time_ns", "max_eye_age_at_presentation_ns"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        _sha256(self.expected_eye_receipt_sha256)
        _sha256(self.expected_phase_receipt_sha256)


@dataclass(frozen=True)
class SpatialFrameGate:
    admissible_same_transition_evidence: bool
    software_same_frame_candidate: bool
    refusals: tuple[str, ...]
    eye_receipt_exact: bool
    phase_receipt_exact: bool
    eye_software_gate_admissible: bool
    eye_temporal_evidence_authenticated: bool
    phase_semantic_reuse_admissible: bool
    eye_temporally_bound_to_presentation: bool
    physical_display_effect_authority: bool = False


def _produce_eye_receipt(
    *,
    eye_frame: eye.IrisFrameObservation,
    eye_calibration: eye.CameraCalibration,
    assumed_ipd_m: float,
    eye_gate_policy: eye.GatePolicyV1,
    eye_k27_coordinate: int,
    eye_parent_artifact_ids: Sequence[str],
) -> Mapping[str, object]:
    return eye.build_eye_pose_receipt(
        frame=eye_frame,
        calibration=eye_calibration,
        assumed_ipd_m=assumed_ipd_m,
        gate_policy=eye_gate_policy,
        k27_coordinate=eye_k27_coordinate,
        parent_artifact_ids=eye_parent_artifact_ids,
    )


def bind_spatial_frame_transition(
    *,
    eye_frame: eye.IrisFrameObservation,
    eye_calibration: eye.CameraCalibration,
    assumed_ipd_m: float,
    eye_gate_policy: eye.GatePolicyV1,
    eye_k27_coordinate: int,
    eye_parent_artifact_ids: Sequence[str],
    phase_receipt: Mapping[str, object],
    intent: SpatialFrameIntent,
) -> SpatialFrameGate:
    """Traverse the eye producer and bind its result to one phase/presentation cut."""
    intent.validate()
    refusals: list[str] = []

    eye_receipt = _produce_eye_receipt(
        eye_frame=eye_frame,
        eye_calibration=eye_calibration,
        assumed_ipd_m=assumed_ipd_m,
        eye_gate_policy=eye_gate_policy,
        eye_k27_coordinate=eye_k27_coordinate,
        eye_parent_artifact_ids=eye_parent_artifact_ids,
    )
    eye_valid = eye.verify_eye_pose_receipt(eye_receipt)
    if not eye_valid:
        refusals.append("EYE_PRODUCER_RECEIPT_INVALID")
    phase_valid = phase.verify_phase_mask_receipt(phase_receipt)
    if not phase_valid:
        refusals.append("PHASE_RECEIPT_INVALID")

    eye_exact = bool(
        eye_valid
        and eye_receipt.get("receipt_sha256") == intent.expected_eye_receipt_sha256
    )
    if not eye_exact:
        refusals.append("EYE_RECEIPT_IDENTITY_MISMATCH")
    phase_exact = bool(
        phase_valid
        and phase_receipt.get("receipt_sha256") == intent.expected_phase_receipt_sha256
    )
    if not phase_exact:
        refusals.append("PHASE_RECEIPT_IDENTITY_MISMATCH")

    gate_payload = eye_receipt.get("gate", {}) if eye_valid else {}
    eye_software_gate = bool(
        isinstance(gate_payload, dict)
        and gate_payload.get("software_gate_admissible") is True
    )
    if not eye_software_gate:
        refusals.append("EYE_SOFTWARE_GATE_NOT_ADMISSIBLE")

    eye_temporal_authenticated = bool(
        eye_valid and eye_receipt.get("temporal_point_evidence_admissible") is True
    )
    if not eye_temporal_authenticated:
        refusals.append("EYE_TEMPORAL_EVIDENCE_NOT_AUTHENTICATED")

    phase_gate = bool(
        phase_valid
        and isinstance(phase_receipt.get("retrieval_gate"), dict)
        and phase_receipt["retrieval_gate"].get("admissible_for_semantic_reuse") is True
    )
    if not phase_gate:
        refusals.append("PHASE_MASK_SEMANTIC_REUSE_NOT_ADMISSIBLE")

    temporal = False
    if eye_valid:
        producer_inputs = eye_receipt.get("producer_inputs")
        if isinstance(producer_inputs, dict) and isinstance(producer_inputs.get("frame"), dict):
            capture_time_ns = producer_inputs["frame"].get("capture_time_ns")
            if isinstance(capture_time_ns, int) and not isinstance(capture_time_ns, bool):
                age = intent.presentation_time_ns - capture_time_ns
                temporal = 0 <= age <= intent.max_eye_age_at_presentation_ns
    if not temporal:
        refusals.append("EYE_FRAME_OUTSIDE_PRESENTATION_TIME_CUT")

    software_candidate = bool(
        eye_valid and phase_valid and eye_exact and phase_exact
        and eye_software_gate and phase_gate and temporal
    )
    admissible = software_candidate and eye_temporal_authenticated

    return SpatialFrameGate(
        admissible_same_transition_evidence=admissible,
        software_same_frame_candidate=software_candidate,
        refusals=tuple(refusals),
        eye_receipt_exact=eye_exact,
        phase_receipt_exact=phase_exact,
        eye_software_gate_admissible=eye_software_gate,
        eye_temporal_evidence_authenticated=eye_temporal_authenticated,
        phase_semantic_reuse_admissible=phase_gate,
        eye_temporally_bound_to_presentation=temporal,
    )


def build_spatial_frame_receipt(
    *,
    eye_frame: eye.IrisFrameObservation,
    eye_calibration: eye.CameraCalibration,
    assumed_ipd_m: float,
    eye_gate_policy: eye.GatePolicyV1,
    eye_k27_coordinate: int,
    eye_parent_artifact_ids: Sequence[str],
    phase_receipt: Mapping[str, object],
    intent: SpatialFrameIntent,
    parent_artifact_ids: Sequence[str],
) -> Mapping[str, object]:
    parents = tuple(parent_artifact_ids)
    if len(parents) != 2 or len(set(parents)) != 2 or any(not p for p in parents):
        raise ValueError("exactly two distinct non-empty parent artifact IDs are required")
    intent.validate()
    derived_eye = _produce_eye_receipt(
        eye_frame=eye_frame,
        eye_calibration=eye_calibration,
        assumed_ipd_m=assumed_ipd_m,
        eye_gate_policy=eye_gate_policy,
        eye_k27_coordinate=eye_k27_coordinate,
        eye_parent_artifact_ids=eye_parent_artifact_ids,
    )
    gate = bind_spatial_frame_transition(
        eye_frame=eye_frame,
        eye_calibration=eye_calibration,
        assumed_ipd_m=assumed_ipd_m,
        eye_gate_policy=eye_gate_policy,
        eye_k27_coordinate=eye_k27_coordinate,
        eye_parent_artifact_ids=eye_parent_artifact_ids,
        phase_receipt=phase_receipt,
        intent=intent,
    )
    payload = {
        "schema": SCHEMA,
        "producer_schema": "AURA_K27_SPATIAL_FRAME_PRODUCER_V2",
        "parent_artifact_ids": parents,
        "producer_inputs": {
            "eye_frame": asdict(eye_frame),
            "eye_calibration": asdict(eye_calibration),
            "assumed_ipd_m": assumed_ipd_m,
            "eye_gate_policy": asdict(eye_gate_policy),
            "eye_k27_coordinate": eye_k27_coordinate,
            "eye_parent_artifact_ids": tuple(eye_parent_artifact_ids),
            "phase_receipt": dict(phase_receipt),
            "intent": asdict(intent),
        },
        "eye_receipt_sha256": derived_eye.get("receipt_sha256"),
        "phase_receipt_sha256": phase_receipt.get("receipt_sha256"),
        "gate": asdict(gate),
        "claim_ceiling": {
            "software_same_frame_candidate_is_authenticated_transition": False,
            "same_transition_evidence_is_physical_effect": False,
            "eye_pose_is_metric_ground_truth": False,
            "eye_sensor_capture_authenticated": False,
            "phase_mask_is_optically_correct": False,
            "display_pipeline_generation_is_observed_hardware": False,
            "display_actuation_observed": False,
            "optical_safety_proven": False,
            "deployment_ready": False,
            "semantic_k27_authority": False,
            "native_transformer_kv_accessed": False,
            "gate10_promoted": False,
        },
    }
    return {
        **payload,
        "receipt_sha256": hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest(),
    }


def verify_spatial_frame_receipt(receipt: Mapping[str, object]) -> bool:
    if not isinstance(receipt, Mapping) or receipt.get("schema") != SCHEMA:
        return False
    try:
        p = receipt["producer_inputs"]
        expected = build_spatial_frame_receipt(
            eye_frame=eye.IrisFrameObservation(**p["eye_frame"]),
            eye_calibration=eye.CameraCalibration(**p["eye_calibration"]),
            assumed_ipd_m=p["assumed_ipd_m"],
            eye_gate_policy=eye.GatePolicyV1(**p["eye_gate_policy"]),
            eye_k27_coordinate=p["eye_k27_coordinate"],
            eye_parent_artifact_ids=tuple(p["eye_parent_artifact_ids"]),
            phase_receipt=p["phase_receipt"],
            intent=SpatialFrameIntent(**p["intent"]),
            parent_artifact_ids=tuple(receipt["parent_artifact_ids"]),
        )
    except (KeyError, TypeError, ValueError):
        return False
    return dict(receipt) == dict(expected)
