"""Neutral H-C -> H-G wake binding contract for CS-HARNESS-001.

The wake adapter owns durable intent publication. This module only derives stable,
worker-independent work identity from a CURRENT WorkGraph projection so candidate
worker churn cannot mint a new logical work version or silently duplicate the work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from aura_event_contracts import stable_digest
from aura_creator_studio_workgraph import ProjectionStatus, WorkGraphSnapshot

VERSION = "AURA_CREATOR_STUDIO_WORKGRAPH_WAKE_BINDING_V1"


@dataclass(frozen=True)
class WakeWorkBinding:
    schema: str
    mission_id: str
    project_id: str
    work_id: str
    work_version: str
    assignment_key: str
    projection_revision: str
    currentness_revision: str
    candidate_worker_ids: tuple[str, ...]
    hydration_refs: tuple[str, ...]
    coordination_only: bool = True
    effect_allowed: bool = False
    execution_proven: bool = False

    def __post_init__(self) -> None:
        if self.schema != VERSION:
            raise ValueError("unsupported wake binding schema")
        if not self.mission_id or not self.work_id or not self.work_version or not self.assignment_key:
            raise ValueError("wake binding identity fields must be non-empty")
        if not self.candidate_worker_ids:
            raise ValueError("wake binding requires at least one eligible worker")
        if self.coordination_only is not True or self.effect_allowed is not False or self.execution_proven is not False:
            raise ValueError("wake binding cannot grant effects or prove execution")


def _work_version(snapshot: WorkGraphSnapshot, projection_index: int) -> str:
    projection = snapshot.work[projection_index]
    work = projection.work
    # Deliberately excludes candidate-worker membership and projection generation.
    # Worker availability may change without changing the logical unit of work.
    return stable_digest(
        {
            "work_id": work.work_id,
            "state": work.state,
            "priority": work.priority,
            "parent_objective": work.parent_objective,
            "residual": work.residual,
            "currentness_basis": work.currentness_basis,
            "dependencies": work.dependencies,
            "required_capabilities": work.required_capabilities,
            "free_first_route": work.free_first_route,
            "expected_output": work.expected_output,
            "acceptance": work.acceptance,
            "reopen_conditions": work.reopen_conditions,
            "cost_ceiling_microusd": work.cost_ceiling_microusd,
            "required_effect_ceiling": work.required_effect_ceiling,
            "execution_state": work.execution_state,
            "execution_receipt_refs": work.execution_receipt_refs,
            "hydration_refs": work.hydration_refs,
            "evidence_refs": work.evidence_refs,
        }
    )


def compile_wake_bindings(snapshot: WorkGraphSnapshot, *, mission_id: str) -> tuple[WakeWorkBinding, ...]:
    """Compile stable logical work identities from CURRENT eligible WorkGraph cells."""
    if not isinstance(mission_id, str) or not mission_id.strip():
        raise ValueError("mission_id must be non-empty text")
    if snapshot.projection_status is not ProjectionStatus.CURRENT:
        return ()

    bindings: list[WakeWorkBinding] = []
    for index, projection in enumerate(snapshot.work):
        if not projection.eligible:
            continue
        version = _work_version(snapshot, index)
        assignment_key = stable_digest(
            {
                "mission_id": mission_id.strip(),
                "project_id": snapshot.project_id,
                "work_id": projection.work.work_id,
                "work_version": version,
            }
        )
        bindings.append(
            WakeWorkBinding(
                schema=VERSION,
                mission_id=mission_id.strip(),
                project_id=snapshot.project_id,
                work_id=projection.work.work_id,
                work_version=version,
                assignment_key=assignment_key,
                projection_revision=snapshot.revision,
                currentness_revision=snapshot.canonical_orientation_revision,
                candidate_worker_ids=tuple(sorted(projection.capability_candidates)),
                hydration_refs=projection.work.hydration_refs,
            )
        )
    return tuple(bindings)


def choose_worker(binding: WakeWorkBinding, *, already_assigned: frozenset[str] = frozenset()) -> str | None:
    """Deterministic zero-effect worker proposal; durable assignment still requires H-G/H-C commit."""
    for worker_id in binding.candidate_worker_ids:
        if worker_id not in already_assigned:
            return worker_id
    return None


def validate_wake_intent_binding(intent: Mapping[str, Any], binding: WakeWorkBinding) -> tuple[bool, tuple[str, ...]]:
    """Validate fields present in CreatorStudioWakeIntentV1 against one H-C binding.

    Current H-G WakeIntentV1 does not yet carry assignment_key. The caller should
    persist/compare binding.assignment_key beside the wake event to dedupe logical
    work across worker-candidate churn; worker_id must never be the sole dedupe key.
    """
    reasons: list[str] = []
    if intent.get("mission_id") != binding.mission_id:
        reasons.append("MISSION_ID_MISMATCH")
    if intent.get("work_id") != binding.work_id:
        reasons.append("WORK_ID_MISMATCH")
    if intent.get("work_version") != binding.work_version:
        reasons.append("WORK_VERSION_MISMATCH")
    worker_id = intent.get("worker_id")
    if worker_id not in binding.candidate_worker_ids:
        reasons.append("WORKER_NOT_ELIGIBLE_FOR_BINDING")
    if intent.get("execution_authorized") is True or intent.get("provider_calls_authorized") is True:
        reasons.append("WAKE_INTENT_EFFECT_AUTHORITY_FORBIDDEN")
    if intent.get("background_execution_claimed") is True:
        reasons.append("BACKGROUND_EXECUTION_CLAIM_FORBIDDEN")
    return not reasons, tuple(reasons)
