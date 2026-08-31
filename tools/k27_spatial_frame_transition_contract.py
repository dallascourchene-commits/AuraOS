"""Canonical temporal binding for one K27 spatial-display presentation frame.

This membrane joins an already-valid eye-pose observation receipt to an
already-valid phase-mask artifact receipt for one intended presentation frame.
It follows the WorkCapsule temporal-identity rule: two green artifacts are not
"the same transition" until exact identities and timing are bound together.

No physical display effect is authorized.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Sequence

import k27_eye_pose_observation_contract as eye
import k27_phase_mask_artifact_contract as phase


SCHEMA = "AURA_K27_SPATIAL_FRAME_TRANSITION_V1"


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
        if not self.presentation_frame_id:
            raise ValueError("presentation_frame_id must be non-empty")
        if not self.display_pipeline_generation:
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
    refusals: tuple[str, ...]
    eye_receipt_exact: bool
    phase_receipt_exact: bool
    eye_gate_admissible: bool
    phase_semantic_reuse_admissible: bool
    eye_temporally_bound_to_presentation: bool
    physical_display_effect_authority: bool = False


def bind_spatial_frame_transition(
    *,
    eye_receipt: Mapping[str, object],
    phase_receipt: Mapping[str, object],
    intent: SpatialFrameIntent,
) -> SpatialFrameGate:
    """Bind exact eye + mask receipts to one presentation-frame intent."""
    intent.validate()
    refusals: list[str] = []

    eye_valid = eye.verify_eye_pose_receipt(eye_receipt)
    if not eye_valid:
        refusals.append("EYE_RECEIPT_INVALID")
    phase_valid = phase.verify_phase_mask_receipt(phase_receipt)
    if not phase_valid:
        refusals.append("PHASE_RECEIPT_INVALID")

    eye_exact = eye_valid and eye_receipt.get("receipt_sha256") == intent.expected_eye_receipt_sha256
    if not eye_exact:
        refusals.append("EYE_RECEIPT_IDENTITY_MISMATCH")
    phase_exact = phase_valid and phase_receipt.get("receipt_sha256") == intent.expected_phase_receipt_sha256
    if not phase_exact:
        refusals.append("PHASE_RECEIPT_IDENTITY_MISMATCH")

    eye_gate = bool(eye_valid and eye_receipt.get("gate", {}).get("admissible") is True)
    if not eye_gate:
        refusals.append("EYE_EVIDENCE_GATE_NOT_ADMISSIBLE")
    phase_gate = bool(
        phase_valid
        and phase_receipt.get("retrieval_gate", {}).get("admissible_for_semantic_reuse") is True
    )
    if not phase_gate:
        refusals.append("PHASE_MASK_SEMANTIC_REUSE_NOT_ADMISSIBLE")

    temporal = False
    if eye_valid:
        capture_time_ns = eye_receipt.get("frame", {}).get("capture_time_ns")
        if isinstance(capture_time_ns, int) and not isinstance(capture_time_ns, bool):
            age = intent.presentation_time_ns - capture_time_ns
            temporal = 0 <= age <= intent.max_eye_age_at_presentation_ns
    if not temporal:
        refusals.append("EYE_FRAME_OUTSIDE_PRESENTATION_TIME_CUT")

    return SpatialFrameGate(
        admissible_same_transition_evidence=not refusals,
        refusals=tuple(refusals),
        eye_receipt_exact=eye_exact,
        phase_receipt_exact=phase_exact,
        eye_gate_admissible=eye_gate,
        phase_semantic_reuse_admissible=phase_gate,
        eye_temporally_bound_to_presentation=temporal,
    )


def build_spatial_frame_receipt(
    *,
    eye_receipt: Mapping[str, object],
    phase_receipt: Mapping[str, object],
    intent: SpatialFrameIntent,
    gate: SpatialFrameGate,
    parent_artifact_ids: Sequence[str],
) -> Mapping[str, object]:
    parents = tuple(parent_artifact_ids)
    if len(parents) != 2 or len(set(parents)) != 2 or any(not p for p in parents):
        raise ValueError("exactly two distinct non-empty parent artifact IDs are required")
    intent.validate()

    payload = {
        "schema": SCHEMA,
        "parent_artifact_ids": parents,
        "intent": asdict(intent),
        "eye_receipt_sha256": eye_receipt.get("receipt_sha256"),
        "phase_receipt_sha256": phase_receipt.get("receipt_sha256"),
        "gate": asdict(gate),
        "claim_ceiling": {
            "same_transition_evidence_is_physical_effect": False,
            "eye_pose_is_metric_ground_truth": False,
            "phase_mask_is_optically_correct": False,
            "display_pipeline_generation_is_observed_hardware": False,
            "display_actuation_observed": False,
            "optical_safety_proven": False,
            "deployment_ready": False,
            "native_transformer_kv_accessed": False,
            "gate10_promoted": False,
        },
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return {**payload, "receipt_sha256": digest}


def verify_spatial_frame_receipt(receipt: Mapping[str, object]) -> bool:
    expected = {
        "schema",
        "parent_artifact_ids",
        "intent",
        "eye_receipt_sha256",
        "phase_receipt_sha256",
        "gate",
        "claim_ceiling",
        "receipt_sha256",
    }
    if set(receipt) != expected or receipt.get("schema") != SCHEMA:
        return False
    ceiling = receipt.get("claim_ceiling")
    if not isinstance(ceiling, dict) or not ceiling or any(value is not False for value in ceiling.values()):
        return False
    payload = {key: receipt[key] for key in expected if key != "receipt_sha256"}
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return receipt.get("receipt_sha256") == digest
