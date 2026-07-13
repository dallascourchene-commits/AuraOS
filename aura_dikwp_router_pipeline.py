"""Canonical DIKWP provenance envelopes for Model Cognome routing.

Records are append-only audit evidence. They do not mutate active routing policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Iterable

from aura_model_cognome import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest, stable_id

DIKWP_VERSION = "AURA_DIKWP_ROUTER_PIPELINE_V1"


class DIKWPStage(str, Enum):
    DATA = "DATA"
    INFORMATION = "INFORMATION"
    KNOWLEDGE = "KNOWLEDGE"
    WISDOM = "WISDOM"
    PURPOSE = "PURPOSE"


@dataclass(frozen=True)
class DIKWPEnvelope:
    envelope_id: str
    correlation_id: str
    stage: str
    payload_digest: str
    source_record_ids: tuple[str, ...] = ()
    measurement_classes: dict[str, str] = field(default_factory=dict)
    confidence: float | None = None
    policy_scope: str = ""
    purpose_digest: str = ""
    created_at: float = field(default_factory=time.time)
    proposal_only: bool = True

    @classmethod
    def create(
        cls,
        *,
        correlation_id: str,
        stage: str | DIKWPStage,
        payload: Any,
        source_record_ids: tuple[str, ...] = (),
        measurement_classes: dict[str, str] | None = None,
        confidence: float | None = None,
        policy_scope: str = "",
        purpose_digest: str = "",
        created_at: float | None = None,
        proposal_only: bool = True,
    ) -> "DIKWPEnvelope":
        stage_value = stage.value if isinstance(stage, DIKWPStage) else str(stage)
        if stage_value not in {item.value for item in DIKWPStage}:
            raise ValueError(f"Unknown DIKWP stage: {stage_value}")
        if stage_value in {DIKWPStage.INFORMATION.value, DIKWPStage.KNOWLEDGE.value, DIKWPStage.WISDOM.value} and not source_record_ids:
            raise ValueError(f"{stage_value} requires provenance source_record_ids")
        if stage_value == DIKWPStage.WISDOM.value and not purpose_digest:
            raise ValueError("WISDOM requires a pinned purpose_digest")
        payload_digest = stable_digest(payload)
        timestamp = time.time() if created_at is None else float(created_at)
        basis = {
            "correlation_id": correlation_id,
            "stage": stage_value,
            "payload_digest": payload_digest,
            "source_record_ids": source_record_ids,
            "purpose_digest": purpose_digest,
            "created_at": timestamp,
        }
        return cls(
            envelope_id=stable_id("dikwp", basis),
            correlation_id=correlation_id,
            stage=stage_value,
            payload_digest=payload_digest,
            source_record_ids=source_record_ids,
            measurement_classes=dict(measurement_classes or {}),
            confidence=confidence,
            policy_scope=policy_scope,
            purpose_digest=purpose_digest,
            created_at=timestamp,
            proposal_only=proposal_only,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "correlation_id": self.correlation_id,
            "stage": self.stage,
            "payload_digest": self.payload_digest,
            "source_record_ids": list(self.source_record_ids),
            "measurement_classes": dict(self.measurement_classes),
            "confidence": self.confidence,
            "policy_scope": self.policy_scope,
            "purpose_digest": self.purpose_digest,
            "created_at": self.created_at,
            "proposal_only": self.proposal_only,
            "version": DIKWP_VERSION,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def purpose_digest(payload: Any) -> str:
    return stable_digest(payload)


def validate_dikwp_chain(envelopes: Iterable[DIKWPEnvelope], *, consequential: bool = True) -> dict[str, Any]:
    items = list(envelopes)
    by_id = {item.envelope_id: item for item in items}
    by_stage: dict[str, list[DIKWPEnvelope]] = {stage.value: [] for stage in DIKWPStage}
    errors: list[str] = []
    for item in items:
        by_stage.setdefault(item.stage, []).append(item)

    required = {stage.value for stage in DIKWPStage} if consequential else {
        DIKWPStage.DATA.value,
        DIKWPStage.INFORMATION.value,
    }
    missing = sorted(stage for stage in required if not by_stage.get(stage))
    if missing:
        errors.append("missing stages: " + ", ".join(missing))

    allowed_parent_stages = {
        DIKWPStage.INFORMATION.value: {DIKWPStage.DATA.value},
        DIKWPStage.KNOWLEDGE.value: {DIKWPStage.INFORMATION.value},
        DIKWPStage.WISDOM.value: {DIKWPStage.KNOWLEDGE.value, DIKWPStage.PURPOSE.value},
    }
    for item in items:
        allowed = allowed_parent_stages.get(item.stage)
        if not allowed:
            continue
        parent_stages = {by_id[parent].stage for parent in item.source_record_ids if parent in by_id}
        if not parent_stages.intersection(allowed):
            errors.append(f"{item.envelope_id} lacks a valid {item.stage} parent")
        unknown = sorted(parent for parent in item.source_record_ids if parent not in by_id)
        if unknown:
            errors.append(f"{item.envelope_id} references unknown sources: {', '.join(unknown)}")

    purpose_payloads = {item.payload_digest for item in by_stage.get(DIKWPStage.PURPOSE.value, [])}
    for wisdom in by_stage.get(DIKWPStage.WISDOM.value, []):
        if wisdom.purpose_digest not in purpose_payloads:
            errors.append(f"{wisdom.envelope_id} purpose_digest does not match a PURPOSE envelope")
        if not wisdom.proposal_only:
            errors.append(f"{wisdom.envelope_id} must remain proposal_only")

    return {
        "ok": not errors,
        "errors": errors,
        "stages_present": sorted(stage for stage, values in by_stage.items() if values),
        "consequential": consequential,
        "version": DIKWP_VERSION,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
