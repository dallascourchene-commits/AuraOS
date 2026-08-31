#!/usr/bin/env python3
"""NAV-13D: bind hydration observations to exact minimum-hydration obligations.

D0 / HS1 / NONPROMOTING.

Exactly two semantic parents define this relation:
- NAV-13 LawField: exact inherited policy/evidence obligations.
- NAV-13 minimum lawful hydration: exact source-bound, currentness-gated level plan.

This module does not fetch or materialize content. It accepts an upstream observation
projection and proves only that the projection commutes with an exact planned
HydrationStep. Observation binding is not evidence admission, source truth,
authorization, execution, or effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Mapping, Sequence

from tools.aura_nav13_lawfield import EffectiveLawField
from tools.aura_nav13_minimum_hydration import (
    HydrationLevel,
    HydrationStep,
    MinimumHydrationPlan,
    PlanDisposition,
)

SCHEMA = "AURA-NAV13-HYDRATION-COMPLETION-v1"
OBSERVATION_SCHEMA = "AURA-NAV13-HYDRATION-OBSERVATION-PROJECTION-v1"
HEX = frozenset("0123456789abcdef")


class CompletionDisposition(str, Enum):
    BOUND_COMPLETE = "BOUND_COMPLETE"
    HOLD_PLAN_NOT_HYDRATABLE = "HOLD_PLAN_NOT_HYDRATABLE"
    HOLD_OBSERVATION_SET_MISMATCH = "HOLD_OBSERVATION_SET_MISMATCH"
    HOLD_STEP_IDENTITY_MISMATCH = "HOLD_STEP_IDENTITY_MISMATCH"
    HOLD_SOURCE_GENERATION_MISMATCH = "HOLD_SOURCE_GENERATION_MISMATCH"
    HOLD_CURRENTNESS_UNRESOLVED = "HOLD_CURRENTNESS_UNRESOLVED"
    HOLD_LEVEL_INSUFFICIENT = "HOLD_LEVEL_INSUFFICIENT"
    HOLD_MATERIAL_BINDING_INVALID = "HOLD_MATERIAL_BINDING_INVALID"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(domain: str, value: object) -> str:
    return hashlib.sha256(_canonical({"domain": domain, "value": value})).hexdigest()


def _text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _digest(value: str, code: str) -> str:
    value = _text(value, code)
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class HydrationObservationProjection:
    """Upstream materialization/currentness projection; trust is not minted here."""

    schema: str
    semantic_plan_digest: str
    step_semantic_identity: str
    semantic_key: str
    requirement_ids: tuple[str, ...]
    subject_key: str
    evidence_generation_key: str
    knowledge_node_digest: str
    validation_fingerprint: str
    exact_source_uri: str
    achieved_level: HydrationLevel
    material_digest: str
    materialization_receipt_digest: str
    currentness_witness_digest: str
    currentness_generation: str
    source_currentness: str
    observer_ref: str
    observer_generation: str
    observation_state: str = "VERIFIED_BOUNDED_PROJECTION"
    source_truth_proven: bool = False
    evidence_admitted: bool = False
    instruction_authority: bool = False
    authorization_issued: bool = False
    write_authority: bool = False
    effect_authorized: bool = False
    effect_executed: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != OBSERVATION_SCHEMA:
            raise ValueError("HYDRATION_OBSERVATION_SCHEMA_MISMATCH")
        for value, code in (
            (self.semantic_plan_digest, "SEMANTIC_PLAN_DIGEST_REQUIRED"),
            (self.step_semantic_identity, "STEP_SEMANTIC_IDENTITY_REQUIRED"),
            (self.subject_key, "SUBJECT_KEY_REQUIRED"),
            (self.evidence_generation_key, "EVIDENCE_GENERATION_KEY_REQUIRED"),
            (self.knowledge_node_digest, "KNOWLEDGE_NODE_DIGEST_REQUIRED"),
            (self.validation_fingerprint, "VALIDATION_FINGERPRINT_REQUIRED"),
            (self.material_digest, "MATERIAL_DIGEST_REQUIRED"),
            (self.materialization_receipt_digest, "MATERIALIZATION_RECEIPT_DIGEST_REQUIRED"),
            (self.currentness_witness_digest, "CURRENTNESS_WITNESS_DIGEST_REQUIRED"),
        ):
            _digest(value, code)
        _text(self.semantic_key, "SEMANTIC_KEY_REQUIRED")
        _text(self.exact_source_uri, "EXACT_SOURCE_URI_REQUIRED")
        _text(self.currentness_generation, "CURRENTNESS_GENERATION_REQUIRED")
        _text(self.observer_ref, "OBSERVER_REF_REQUIRED")
        _text(self.observer_generation, "OBSERVER_GENERATION_REQUIRED")
        if not isinstance(self.achieved_level, HydrationLevel):
            raise ValueError("ACHIEVED_HYDRATION_LEVEL_INVALID")
        if tuple(sorted(set(self.requirement_ids))) != self.requirement_ids:
            raise ValueError("OBSERVATION_REQUIREMENT_IDS_MUST_BE_CANONICAL")
        if self.source_currentness not in {"RESOLVED_CURRENT", "STALE", "UNKNOWN"}:
            raise ValueError("OBSERVATION_CURRENTNESS_UNSUPPORTED")
        if self.observation_state != "VERIFIED_BOUNDED_PROJECTION":
            raise ValueError("OBSERVATION_NOT_VERIFIED_BOUNDED_PROJECTION")
        if any(
            (
                self.source_truth_proven,
                self.evidence_admitted,
                self.instruction_authority,
                self.authorization_issued,
                self.write_authority,
                self.effect_authorized,
                self.effect_executed,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("HYDRATION_OBSERVATION_EXCEEDED_NONPROMOTION_CEILING")

    @property
    def projection_digest(self) -> str:
        self.validate()
        return _sha(OBSERVATION_SCHEMA, asdict(self))


@dataclass(frozen=True)
class HydrationCompletionReceipt:
    schema: str
    disposition: CompletionDisposition
    reason: str
    law_field_digest: str
    semantic_plan_digest: str
    completed_step_identities: tuple[str, ...]
    observation_projection_digests: tuple[str, ...]
    requirement_ids: tuple[str, ...]
    completion_digest: str
    hydration_obligation_satisfied: bool
    observer_authenticated_by_this_contract: bool = False
    source_truth_proven: bool = False
    evidence_admitted: bool = False
    authorization_issued: bool = False
    materialization_executed_by_this_contract: bool = False
    effect_authorized: bool = False
    effect_executed: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("HYDRATION_COMPLETION_SCHEMA_MISMATCH")
        _digest(self.law_field_digest, "LAW_FIELD_DIGEST_REQUIRED")
        _digest(self.semantic_plan_digest, "SEMANTIC_PLAN_DIGEST_REQUIRED")
        _digest(self.completion_digest, "COMPLETION_DIGEST_REQUIRED")
        for value in self.completed_step_identities:
            _digest(value, "COMPLETED_STEP_IDENTITY_INVALID")
        for value in self.observation_projection_digests:
            _digest(value, "OBSERVATION_PROJECTION_DIGEST_INVALID")
        if tuple(sorted(set(self.completed_step_identities))) != self.completed_step_identities:
            raise ValueError("COMPLETED_STEP_IDENTITIES_MUST_BE_CANONICAL")
        if tuple(sorted(set(self.observation_projection_digests))) != self.observation_projection_digests:
            raise ValueError("OBSERVATION_PROJECTION_DIGESTS_MUST_BE_CANONICAL")
        if tuple(sorted(set(self.requirement_ids))) != self.requirement_ids:
            raise ValueError("COMPLETION_REQUIREMENT_IDS_MUST_BE_CANONICAL")
        if self.hydration_obligation_satisfied != (self.disposition is CompletionDisposition.BOUND_COMPLETE):
            raise ValueError("COMPLETION_SATISFACTION_DISPOSITION_INCONSISTENT")
        if any(
            (
                self.observer_authenticated_by_this_contract,
                self.source_truth_proven,
                self.evidence_admitted,
                self.authorization_issued,
                self.materialization_executed_by_this_contract,
                self.effect_authorized,
                self.effect_executed,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("HYDRATION_COMPLETION_EXCEEDED_NONPROMOTION_CEILING")


def _receipt(
    *,
    disposition: CompletionDisposition,
    reason: str,
    law: EffectiveLawField,
    plan: MinimumHydrationPlan,
    observations: Sequence[HydrationObservationProjection],
) -> HydrationCompletionReceipt:
    law.validate_ceiling()
    plan.validate()
    obs_digests = tuple(sorted(o.projection_digest for o in observations))
    step_ids = tuple(sorted(step.semantic_identity for step in plan.steps)) if disposition is CompletionDisposition.BOUND_COMPLETE else ()
    req_ids = tuple(sorted({rid for step in plan.steps for rid in step.requirement_ids}))
    body = {
        "law_field_digest": law.digest,
        "semantic_plan_digest": plan.semantic_plan_digest,
        "completed_step_identities": step_ids,
        "observation_projection_digests": obs_digests,
        "requirement_ids": req_ids,
        "disposition": disposition.value,
        "reason": reason,
    }
    receipt = HydrationCompletionReceipt(
        schema=SCHEMA,
        disposition=disposition,
        reason=reason,
        law_field_digest=law.digest,
        semantic_plan_digest=plan.semantic_plan_digest,
        completed_step_identities=step_ids,
        observation_projection_digests=obs_digests,
        requirement_ids=req_ids,
        completion_digest=_sha(SCHEMA, body),
        hydration_obligation_satisfied=disposition is CompletionDisposition.BOUND_COMPLETE,
    )
    receipt.validate()
    return receipt


def _observation_by_step(
    observations: Sequence[HydrationObservationProjection],
) -> Mapping[str, HydrationObservationProjection]:
    out: dict[str, HydrationObservationProjection] = {}
    for observation in observations:
        observation.validate()
        if observation.step_semantic_identity in out:
            raise ValueError("DUPLICATE_HYDRATION_OBSERVATION_FOR_STEP")
        out[observation.step_semantic_identity] = observation
    return out


def bind_hydration_completion(
    *,
    law: EffectiveLawField,
    plan: MinimumHydrationPlan,
    observations: Sequence[HydrationObservationProjection],
) -> HydrationCompletionReceipt:
    """Bind upstream observations to exact planned steps without promoting authority."""

    law.validate_ceiling()
    plan.validate()
    if plan.law_field_digest != law.digest:
        return _receipt(
            disposition=CompletionDisposition.HOLD_STEP_IDENTITY_MISMATCH,
            reason="PLAN_LAW_FIELD_DIGEST_MISMATCH",
            law=law,
            plan=plan,
            observations=observations,
        )
    if plan.disposition is not PlanDisposition.HYDRATE_MINIMUM:
        return _receipt(
            disposition=CompletionDisposition.HOLD_PLAN_NOT_HYDRATABLE,
            reason=f"PLAN_DISPOSITION_{plan.disposition.value}",
            law=law,
            plan=plan,
            observations=observations,
        )

    by_step = _observation_by_step(observations)
    expected_ids = {step.semantic_identity for step in plan.steps}
    if set(by_step) != expected_ids:
        return _receipt(
            disposition=CompletionDisposition.HOLD_OBSERVATION_SET_MISMATCH,
            reason="OBSERVATION_SET_MUST_EQUAL_PLANNED_STEP_SET",
            law=law,
            plan=plan,
            observations=observations,
        )

    for step in plan.steps:
        observation = by_step[step.semantic_identity]
        if observation.semantic_plan_digest != plan.semantic_plan_digest:
            return _receipt(
                disposition=CompletionDisposition.HOLD_STEP_IDENTITY_MISMATCH,
                reason="OBSERVATION_PLAN_DIGEST_MISMATCH",
                law=law,
                plan=plan,
                observations=observations,
            )
        structural_pairs = (
            (observation.semantic_key, step.semantic_key),
            (observation.requirement_ids, step.requirement_ids),
            (observation.subject_key, step.subject_key),
            (observation.knowledge_node_digest, step.knowledge_node_digest),
            (observation.validation_fingerprint, step.validation_fingerprint),
            (observation.exact_source_uri, step.exact_source_uri),
        )
        if any(left != right for left, right in structural_pairs):
            return _receipt(
                disposition=CompletionDisposition.HOLD_STEP_IDENTITY_MISMATCH,
                reason="OBSERVATION_STEP_STRUCTURE_MISMATCH",
                law=law,
                plan=plan,
                observations=observations,
            )
        if observation.evidence_generation_key != step.evidence_generation_key:
            return _receipt(
                disposition=CompletionDisposition.HOLD_SOURCE_GENERATION_MISMATCH,
                reason="OBSERVATION_EVIDENCE_GENERATION_MISMATCH",
                law=law,
                plan=plan,
                observations=observations,
            )
        if observation.source_currentness != "RESOLVED_CURRENT":
            return _receipt(
                disposition=CompletionDisposition.HOLD_CURRENTNESS_UNRESOLVED,
                reason=f"OBSERVATION_CURRENTNESS_{observation.source_currentness}",
                law=law,
                plan=plan,
                observations=observations,
            )
        if observation.achieved_level < step.target_level:
            return _receipt(
                disposition=CompletionDisposition.HOLD_LEVEL_INSUFFICIENT,
                reason="OBSERVED_LEVEL_BELOW_PLANNED_TARGET",
                law=law,
                plan=plan,
                observations=observations,
            )
        # The material and currentness witnesses must be identity-bearing but remain
        # upstream projections; this contract does not authenticate their issuers.
        try:
            _digest(observation.material_digest, "MATERIAL_DIGEST_REQUIRED")
            _digest(observation.materialization_receipt_digest, "MATERIALIZATION_RECEIPT_DIGEST_REQUIRED")
            _digest(observation.currentness_witness_digest, "CURRENTNESS_WITNESS_DIGEST_REQUIRED")
        except ValueError:
            return _receipt(
                disposition=CompletionDisposition.HOLD_MATERIAL_BINDING_INVALID,
                reason="MATERIAL_OR_CURRENTNESS_WITNESS_INVALID",
                law=law,
                plan=plan,
                observations=observations,
            )

    return _receipt(
        disposition=CompletionDisposition.BOUND_COMPLETE,
        reason="ALL_PLANNED_HYDRATION_STEPS_BOUND_TO_CURRENT_EXACT_OBSERVATIONS",
        law=law,
        plan=plan,
        observations=observations,
    )


LAWS = (
    "HydrationPlan!=HydrationObservation!=EvidenceAdmission",
    "HydrationObservedAndBound!=SemanticTruth",
    "ObservationPlanDigestMustEqualMinimumHydrationPlanDigest",
    "ObservationEvidenceGenerationMustEqualPlannedEvidenceGeneration",
    "CurrentnessWitnessRemainsIdentityBearingAtCompletion",
    "AchievedHydrationLevelMustMeetOrExceedPlannedTarget",
    "ObservationSetMustEqualPlannedStepSet",
    "MaterialDigestBound!=ObserverAuthenticatedByThisContract",
    "HydrationCompletion!=Authorization!=EffectAuthority",
    "K27Placement!=HydrationCompletionIdentity!=SemanticAuthority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
