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
        correlation = str(correlation_id).strip()
        if not correlation:
            raise ValueError("correlation_id must not be empty")
        stage_value = stage.value if isinstance(stage, DIKWPStage) else str(stage)
        if stage_value not in {item.value for item in DIKWPStage}:
            raise ValueError(f"Unknown DIKWP stage: {stage_value}")
        sources = tuple(str(item) for item in source_record_ids)
        if stage_value in {
            DIKWPStage.INFORMATION.value,
            DIKWPStage.KNOWLEDGE.value,
            DIKWPStage.WISDOM.value,
        } and not sources:
            raise ValueError(f"{stage_value} requires provenance source_record_ids")
        if stage_value == DIKWPStage.WISDOM.value and not purpose_digest:
            raise ValueError("WISDOM requires a pinned purpose_digest")
        if confidence is not None and not 0.0 <= float(confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        payload_hash = stable_digest(payload)
        timestamp = time.time() if created_at is None else float(created_at)
        basis = {
            "correlation_id": correlation,
            "stage": stage_value,
            "payload_digest": payload_hash,
            "source_record_ids": sources,
            "purpose_digest": str(purpose_digest),
            "created_at": timestamp,
        }
        return cls(
            envelope_id=stable_id("dikwp", basis),
            correlation_id=correlation,
            stage=stage_value,
            payload_digest=payload_hash,
            source_record_ids=sources,
            measurement_classes=dict(measurement_classes or {}),
            confidence=confidence,
            policy_scope=str(policy_scope),
            purpose_digest=str(purpose_digest),
            created_at=timestamp,
            proposal_only=bool(proposal_only),
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


def _has_cycle(items: list[DIKWPEnvelope], by_id: dict[str, DIKWPEnvelope]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        node = by_id[node_id]
        for parent_id in node.source_record_ids:
            if parent_id in by_id and visit(parent_id):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(item.envelope_id) for item in items if item.envelope_id not in visited)


def validate_dikwp_chain(
    envelopes: Iterable[DIKWPEnvelope],
    *,
    consequential: bool = True,
) -> dict[str, Any]:
    items = list(envelopes)
    errors: list[str] = []
    by_id: dict[str, DIKWPEnvelope] = {}
    for item in items:
        previous = by_id.get(item.envelope_id)
        if previous is not None and previous != item:
            errors.append(f"conflicting duplicate envelope_id: {item.envelope_id}")
        by_id[item.envelope_id] = item

    correlations = {item.correlation_id for item in items}
    if len(correlations) > 1:
        errors.append("all envelopes in a DIKWP chain must share one correlation_id")

    by_stage: dict[str, list[DIKWPEnvelope]] = {stage.value: [] for stage in DIKWPStage}
    for item in items:
        if item.stage not in by_stage:
            errors.append(f"unknown stage on envelope {item.envelope_id}: {item.stage}")
            continue
        by_stage[item.stage].append(item)

    required = (
        {stage.value for stage in DIKWPStage}
        if consequential
        else {DIKWPStage.DATA.value, DIKWPStage.INFORMATION.value}
    )
    missing = sorted(stage for stage in required if not by_stage.get(stage))
    if missing:
        errors.append("missing stages: " + ", ".join(missing))

    required_parent_stages = {
        DIKWPStage.INFORMATION.value: {DIKWPStage.DATA.value},
        DIKWPStage.KNOWLEDGE.value: {DIKWPStage.INFORMATION.value},
        DIKWPStage.WISDOM.value: {DIKWPStage.KNOWLEDGE.value, DIKWPStage.PURPOSE.value},
    }
    for item in items:
        unknown = sorted(parent for parent in item.source_record_ids if parent not in by_id)
        if unknown:
            errors.append(f"{item.envelope_id} references unknown sources: {', '.join(unknown)}")
        parents = [by_id[parent] for parent in item.source_record_ids if parent in by_id]
        for parent in parents:
            if parent.correlation_id != item.correlation_id:
                errors.append(f"{item.envelope_id} references a source from another correlation")
            if parent.created_at > item.created_at:
                errors.append(f"{item.envelope_id} references a source created later")
        required_parents = required_parent_stages.get(item.stage)
        if required_parents:
            actual_parent_stages = {parent.stage for parent in parents}
            missing_parent_stages = sorted(required_parents - actual_parent_stages)
            if missing_parent_stages:
                errors.append(
                    f"{item.envelope_id} lacks required {item.stage} parents: "
                    + ", ".join(missing_parent_stages)
                )

    if _has_cycle(items, by_id):
        errors.append("DIKWP provenance graph contains a cycle")

    for wisdom in by_stage.get(DIKWPStage.WISDOM.value, []):
        cited_purposes = [
            by_id[parent]
            for parent in wisdom.source_record_ids
            if parent in by_id and by_id[parent].stage == DIKWPStage.PURPOSE.value
        ]
        if not cited_purposes:
            errors.append(f"{wisdom.envelope_id} must cite a PURPOSE envelope")
        elif wisdom.purpose_digest not in {item.payload_digest for item in cited_purposes}:
            errors.append(f"{wisdom.envelope_id} purpose_digest does not match its cited PURPOSE envelope")
        if not wisdom.proposal_only:
            errors.append(f"{wisdom.envelope_id} must remain proposal_only")

    return {
        "ok": not errors,
        "errors": errors,
        "stages_present": sorted(stage for stage, values in by_stage.items() if values),
        "correlation_id": next(iter(correlations)) if len(correlations) == 1 else None,
        "consequential": consequential,
        "version": DIKWP_VERSION,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
