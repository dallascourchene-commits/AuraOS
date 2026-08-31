#!/usr/bin/env python3
"""NAV-13H: compile the minimum lawful hydration-level route.

D0 / HS1 / NONPROMOTING.

This module consumes projections from existing owners rather than reimplementing
them:
- NAV-13 EffectiveLawField: inherited/narrowed policy and evidence obligations;
- NAV-07A: typed pre-hydration epistemic state;
- EKI-1: source-resolvable CURRENT_REFERENCE + L0..L4 hydration identity;
- WP03 reader: exact snapshot/currentness/principal-bounded candidate read.

It emits only a deterministic hydration *plan*. It does not fetch, materialize,
read network content, execute tools, issue authority, or claim byte/token/AST
minimality. "Minimum" means the least contiguous EKI hydration level that
satisfies the explicit LawField evidence contracts after blocking epistemic debt
has already been resolved.

Core laws:
- MinimumHydrationLevel != MinimumBytes != MinimumASTCone.
- Located != Current != Hydrated != Authorized.
- BlockingEpistemicDebtPrecedesHydration.
- CurrentReference + VerifiedReader != SemanticTruth.
- SemanticHydrationNeed != K27PlacementHint.
- HydrationPlan != Materialization != EffectAuthority.
- ExactSourceOptionalForSatisfiedEvidence != ExactSourceOptionalForNewHydration.
- CoordinateMemory != MODEL_PREFIX_KV.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum, IntEnum
import hashlib
import json
from typing import Mapping, Sequence
from urllib.parse import urlparse

from tools.aura_nav13_lawfield import EffectiveLawField

SCHEMA = "AURA-NAV13-MINIMUM-HYDRATION-v1"
SOURCE_PROJECTION_SCHEMA = "AURA-NAV13-HYDRATION-SOURCE-PROJECTION-v1"
ROUTE_PROJECTION_SCHEMA = "AURA-NAV13-EPISTEMIC-PROJECTION-v1"

HEX = frozenset("0123456789abcdef")


class HydrationLevel(IntEnum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4

    @property
    def label(self) -> str:
        return f"L{int(self)}"


class PlanDisposition(str, Enum):
    READY_NO_HYDRATION = "READY_NO_HYDRATION"
    HYDRATE_MINIMUM = "HYDRATE_MINIMUM"
    HOLD_EPISTEMIC_DEBT = "HOLD_EPISTEMIC_DEBT"
    HOLD_ROUTE_REBASE_REQUIRED = "HOLD_ROUTE_REBASE_REQUIRED"
    HOLD_LAW_FORBIDS_HYDRATION = "HOLD_LAW_FORBIDS_HYDRATION"
    HOLD_REQUIREMENT_UNBOUND = "HOLD_REQUIREMENT_UNBOUND"
    HOLD_SOURCE_NOT_CURRENT = "HOLD_SOURCE_NOT_CURRENT"
    HOLD_SOURCE_READER_UNVERIFIED = "HOLD_SOURCE_READER_UNVERIFIED"
    HOLD_SOURCE_CURRENTNESS_UNRESOLVED = "HOLD_SOURCE_CURRENTNESS_UNRESOLVED"
    HOLD_EXACT_SOURCE_UNRESOLVED = "HOLD_EXACT_SOURCE_UNRESOLVED"


BLOCKING_EPISTEMIC_STATES = frozenset(
    {
        "STALE",
        "HISTORICAL",
        "UNRESOLVED",
        "COLLISION",
        "OWNER_MISSING",
        "MAP_GAP",
        "UNKNOWN",
    }
)

VALID_EPISTEMIC_STATE_TRANSITIONS = {
    "KNOWN_CURRENT": "NONE",
    "EXTERNAL_UNHYDRATED": "HYDRATE_MINIMUM",
    "STALE": "REOPEN_CURRENTNESS",
    "HISTORICAL": "HISTORY_ONLY",
    "UNRESOLVED": "RESOLVE_VERSION",
    "COLLISION": "QUOTIENT_COLLISION",
    "OWNER_MISSING": "DISCOVER_OWNER",
    "MAP_GAP": "REPAIR_MAP",
    "UNKNOWN": "RESOLVE_CURRENTNESS",
}


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


def _exact_uri(value: str | None, code: str) -> str | None:
    if value is None:
        return None
    value = _text(value, code)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https", "git", "doi", "arxiv", "hf", "file"}:
        raise ValueError(code)
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class EpistemicRouteProjection:
    schema: str
    state: str
    next_transition: str
    route_receipt_digest: str

    def validate(self) -> None:
        if self.schema != ROUTE_PROJECTION_SCHEMA:
            raise ValueError("EPISTEMIC_ROUTE_SCHEMA_MISMATCH")
        if self.state not in VALID_EPISTEMIC_STATE_TRANSITIONS:
            raise ValueError("EPISTEMIC_STATE_UNSUPPORTED")
        expected = VALID_EPISTEMIC_STATE_TRANSITIONS[self.state]
        if self.next_transition != expected:
            raise ValueError("EPISTEMIC_STATE_TRANSITION_INCONSISTENT")
        _digest(self.route_receipt_digest, "ROUTE_RECEIPT_DIGEST_REQUIRED")


@dataclass(frozen=True)
class EvidenceRequirement:
    requirement_id: str
    semantic_key: str
    minimum_level: HydrationLevel
    currentness_required: bool = True
    exact_source_required: bool = True

    def validate(self) -> None:
        _text(self.requirement_id, "REQUIREMENT_ID_REQUIRED")
        _text(self.semantic_key, "SEMANTIC_KEY_REQUIRED")
        if not isinstance(self.minimum_level, HydrationLevel):
            raise ValueError("MINIMUM_HYDRATION_LEVEL_INVALID")
        if type(self.currentness_required) is not bool:
            raise ValueError("CURRENTNESS_REQUIRED_MUST_BE_BOOL")
        if type(self.exact_source_required) is not bool:
            raise ValueError("EXACT_SOURCE_REQUIRED_MUST_BE_BOOL")


@dataclass(frozen=True)
class HydrationSourceProjection:
    schema: str
    semantic_key: str
    subject_key: str
    evidence_generation_key: str
    knowledge_node_digest: str
    validation_fingerprint: str
    reader_receipt_digest: str
    knowledge_state: str
    reader_disposition: str
    source_currentness: str
    available_level: HydrationLevel
    exact_source_uri: str | None
    evidence_domain: str
    principal: str
    k27_placement_hint: tuple[int, int, int] | None = None
    candidate_only: bool = True
    instruction_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != SOURCE_PROJECTION_SCHEMA:
            raise ValueError("HYDRATION_SOURCE_SCHEMA_MISMATCH")
        _text(self.semantic_key, "SEMANTIC_KEY_REQUIRED")
        for value, code in (
            (self.subject_key, "SUBJECT_KEY_REQUIRED"),
            (self.evidence_generation_key, "EVIDENCE_GENERATION_KEY_REQUIRED"),
            (self.knowledge_node_digest, "KNOWLEDGE_NODE_DIGEST_REQUIRED"),
            (self.validation_fingerprint, "VALIDATION_FINGERPRINT_REQUIRED"),
            (self.reader_receipt_digest, "READER_RECEIPT_DIGEST_REQUIRED"),
        ):
            _digest(value, code)
        if self.knowledge_state not in {
            "DISCOVERED_UNVERIFIED",
            "SOURCE_RESOLVED",
            "METADATA_VERIFIED",
            "CONTENT_VERIFIED",
            "CURRENT_REFERENCE",
            "STALE_REVERIFY_REQUIRED",
            "INVALIDATED",
        }:
            raise ValueError("KNOWLEDGE_STATE_UNSUPPORTED")
        if self.reader_disposition not in {
            "FOUND_VERIFIED",
            "NOT_FOUND",
            "STORE_STALE",
            "STORE_INTEGRITY_ERROR",
            "ROW_DIGEST_MISMATCH",
            "SOURCE_REVALIDATION_REQUIRED",
            "CURRENTNESS_REOPEN",
            "WRONG_EVIDENCE_DOMAIN",
            "WRONG_RESPONSIBILITY_OWNER",
            "PRINCIPAL_SCOPE_MISMATCH",
            "SUPERSEDED_HISTORY_ONLY",
            "HYDRATION_LIMIT_EXCEEDED",
        }:
            raise ValueError("READER_DISPOSITION_UNSUPPORTED")
        if self.source_currentness not in {
            "RESOLVED_CURRENT",
            "STALE",
            "UNKNOWN",
            "NOT_REQUIRED",
        }:
            raise ValueError("SOURCE_CURRENTNESS_UNSUPPORTED")
        if not isinstance(self.available_level, HydrationLevel):
            raise ValueError("AVAILABLE_HYDRATION_LEVEL_INVALID")
        _exact_uri(self.exact_source_uri, "EXACT_SOURCE_URI_INVALID")
        _text(self.evidence_domain, "EVIDENCE_DOMAIN_REQUIRED")
        _text(self.principal, "PRINCIPAL_REQUIRED")
        if self.k27_placement_hint is not None:
            if (
                len(self.k27_placement_hint) != 3
                or any(type(v) is not int or v < 0 or v >= 27 for v in self.k27_placement_hint)
            ):
                raise ValueError("K27_PLACEMENT_HINT_INVALID")
        if self.candidate_only is not True:
            raise ValueError("HYDRATION_SOURCE_MUST_REMAIN_CANDIDATE_ONLY")
        if any(
            (
                self.instruction_authority,
                self.write_authority,
                self.effect_authority,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("HYDRATION_SOURCE_EXCEEDED_NONPROMOTION_CEILING")


@dataclass(frozen=True)
class HydrationStep:
    semantic_key: str
    requirement_ids: tuple[str, ...]
    subject_key: str
    evidence_generation_key: str
    knowledge_node_digest: str
    validation_fingerprint: str
    reader_receipt_digest: str
    exact_source_uri: str
    from_level: HydrationLevel
    target_level: HydrationLevel
    missing_levels: tuple[str, ...]
    k27_placement_hint: tuple[int, int, int] | None

    @property
    def semantic_identity(self) -> str:
        return _sha(
            "AURA-NAV13-HYDRATION-STEP-SEMANTIC-v1",
            {
                "semantic_key": self.semantic_key,
                "requirement_ids": self.requirement_ids,
                "subject_key": self.subject_key,
                "evidence_generation_key": self.evidence_generation_key,
                "knowledge_node_digest": self.knowledge_node_digest,
                "validation_fingerprint": self.validation_fingerprint,
                "reader_receipt_digest": self.reader_receipt_digest,
                "exact_source_uri": self.exact_source_uri,
                "from_level": self.from_level.label,
                "target_level": self.target_level.label,
                "missing_levels": self.missing_levels,
            },
        )

    @property
    def routing_identity(self) -> str:
        return _sha(
            "AURA-NAV13-HYDRATION-STEP-ROUTING-v1",
            {
                "semantic_identity": self.semantic_identity,
                "k27_placement_hint": self.k27_placement_hint,
            },
        )


@dataclass(frozen=True)
class MinimumHydrationPlan:
    schema: str
    disposition: PlanDisposition
    reason: str
    law_field_digest: str
    epistemic_route_receipt_digest: str
    steps: tuple[HydrationStep, ...]
    unresolved_requirements: tuple[str, ...]
    semantic_plan_digest: str
    routing_receipt_digest: str
    minimum_level_proven: bool
    minimum_bytes_proven: bool = False
    minimum_ast_cone_proven: bool = False
    materialization_started: bool = False
    source_truth_proven: bool = False
    authorization_issued: bool = False
    effect_authorized: bool = False
    effect_executed: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("MINIMUM_HYDRATION_SCHEMA_MISMATCH")
        _digest(self.law_field_digest, "LAW_FIELD_DIGEST_REQUIRED")
        _digest(self.epistemic_route_receipt_digest, "ROUTE_RECEIPT_DIGEST_REQUIRED")
        _digest(self.semantic_plan_digest, "SEMANTIC_PLAN_DIGEST_REQUIRED")
        _digest(self.routing_receipt_digest, "ROUTING_RECEIPT_DIGEST_REQUIRED")
        if tuple(sorted(set(self.unresolved_requirements))) != self.unresolved_requirements:
            raise ValueError("UNRESOLVED_REQUIREMENTS_MUST_BE_CANONICAL")
        if self.disposition is PlanDisposition.HYDRATE_MINIMUM:
            if not self.steps or not self.minimum_level_proven:
                raise ValueError("HYDRATE_MINIMUM_REQUIRES_LEVEL_PROOF")
        elif self.disposition is PlanDisposition.READY_NO_HYDRATION:
            if self.steps or not self.minimum_level_proven:
                raise ValueError("NO_HYDRATION_READY_REQUIRES_EMPTY_PROVEN_PLAN")
        else:
            if self.minimum_level_proven:
                raise ValueError("HOLD_CANNOT_CLAIM_MINIMUM_LEVEL_PROVEN")
        if any(
            (
                self.minimum_bytes_proven,
                self.minimum_ast_cone_proven,
                self.materialization_started,
                self.source_truth_proven,
                self.authorization_issued,
                self.effect_authorized,
                self.effect_executed,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("MINIMUM_HYDRATION_EXCEEDED_NONPROMOTION_CEILING")


def _step_signature(step: HydrationStep) -> tuple[object, ...]:
    return (
        step.semantic_key,
        step.requirement_ids,
        step.subject_key,
        step.evidence_generation_key,
        step.knowledge_node_digest,
        step.validation_fingerprint,
        step.reader_receipt_digest,
        step.exact_source_uri,
        int(step.from_level),
        int(step.target_level),
        step.missing_levels,
    )


def _source_gate(
    requirement: EvidenceRequirement,
    source: HydrationSourceProjection,
) -> tuple[PlanDisposition | None, str | None]:
    source.validate()
    if source.knowledge_state != "CURRENT_REFERENCE":
        return PlanDisposition.HOLD_SOURCE_NOT_CURRENT, "SOURCE_NOT_CURRENT_REFERENCE"
    if source.reader_disposition != "FOUND_VERIFIED":
        return PlanDisposition.HOLD_SOURCE_READER_UNVERIFIED, f"READER_{source.reader_disposition}"
    if requirement.currentness_required and source.source_currentness != "RESOLVED_CURRENT":
        return (
            PlanDisposition.HOLD_SOURCE_CURRENTNESS_UNRESOLVED,
            f"SOURCE_CURRENTNESS_{source.source_currentness}",
        )
    if requirement.exact_source_required and source.exact_source_uri is None:
        return PlanDisposition.HOLD_EXACT_SOURCE_UNRESOLVED, "EXACT_SOURCE_REQUIRED"
    if source.available_level < requirement.minimum_level and source.exact_source_uri is None:
        return (
            PlanDisposition.HOLD_EXACT_SOURCE_UNRESOLVED,
            "HYDRATION_DEFICIT_REQUIRES_EXACT_SOURCE",
        )
    return None, None


def _requirements_by_source(
    requirements: Sequence[EvidenceRequirement],
) -> dict[str, tuple[EvidenceRequirement, ...]]:
    grouped: dict[str, list[EvidenceRequirement]] = {}
    for requirement in requirements:
        grouped.setdefault(requirement.semantic_key, []).append(requirement)
    return {
        key: tuple(sorted(items, key=lambda item: item.requirement_id))
        for key, items in sorted(grouped.items())
    }


def _compile_requirement_first(
    requirements: Sequence[EvidenceRequirement],
    sources: Mapping[str, HydrationSourceProjection],
) -> tuple[HydrationStep, ...]:
    target_by_source: dict[str, HydrationLevel] = {}
    req_ids_by_source: dict[str, list[str]] = {}
    for req in sorted(requirements, key=lambda item: item.requirement_id):
        target_by_source[req.semantic_key] = max(
            target_by_source.get(req.semantic_key, HydrationLevel.L0),
            req.minimum_level,
        )
        req_ids_by_source.setdefault(req.semantic_key, []).append(req.requirement_id)

    steps: list[HydrationStep] = []
    for key in sorted(target_by_source):
        source = sources[key]
        target = target_by_source[key]
        if source.available_level >= target:
            continue
        if source.exact_source_uri is None:
            raise AssertionError("SOURCE_GATE_MUST_RESOLVE_EXACT_URI_BEFORE_STEP_BUILD")
        missing = tuple(
            HydrationLevel(level).label
            for level in range(int(source.available_level) + 1, int(target) + 1)
        )
        steps.append(
            HydrationStep(
                semantic_key=key,
                requirement_ids=tuple(sorted(req_ids_by_source[key])),
                subject_key=source.subject_key,
                evidence_generation_key=source.evidence_generation_key,
                knowledge_node_digest=source.knowledge_node_digest,
                validation_fingerprint=source.validation_fingerprint,
                reader_receipt_digest=source.reader_receipt_digest,
                exact_source_uri=source.exact_source_uri,
                from_level=source.available_level,
                target_level=target,
                missing_levels=missing,
                k27_placement_hint=source.k27_placement_hint,
            )
        )
    return tuple(steps)


def _compile_source_first(
    requirements: Sequence[EvidenceRequirement],
    sources: Mapping[str, HydrationSourceProjection],
) -> tuple[HydrationStep, ...]:
    grouped = _requirements_by_source(requirements)
    steps: list[HydrationStep] = []
    for key, reqs in grouped.items():
        source = sources[key]
        target = HydrationLevel(max(int(req.minimum_level) for req in reqs))
        if source.available_level >= target:
            continue
        if source.exact_source_uri is None:
            raise AssertionError("SOURCE_GATE_MUST_RESOLVE_EXACT_URI_BEFORE_STEP_BUILD")
        missing = tuple(
            HydrationLevel(level).label
            for level in range(int(source.available_level) + 1, int(target) + 1)
        )
        steps.append(
            HydrationStep(
                semantic_key=key,
                requirement_ids=tuple(sorted(req.requirement_id for req in reqs)),
                subject_key=source.subject_key,
                evidence_generation_key=source.evidence_generation_key,
                knowledge_node_digest=source.knowledge_node_digest,
                validation_fingerprint=source.validation_fingerprint,
                reader_receipt_digest=source.reader_receipt_digest,
                exact_source_uri=source.exact_source_uri,
                from_level=source.available_level,
                target_level=target,
                missing_levels=missing,
                k27_placement_hint=source.k27_placement_hint,
            )
        )
    return tuple(steps)


def _plan_digests(
    *,
    disposition: PlanDisposition,
    reason: str,
    law_digest: str,
    route_digest: str,
    steps: Sequence[HydrationStep],
    unresolved: Sequence[str],
) -> tuple[str, str]:
    semantic = _sha(
        "AURA-NAV13-MINIMUM-HYDRATION-SEMANTIC-v1",
        {
            "disposition": disposition.value,
            "reason": reason,
            "law_digest": law_digest,
            "route_digest": route_digest,
            "steps": [step.semantic_identity for step in steps],
            "unresolved": list(unresolved),
        },
    )
    routing = _sha(
        "AURA-NAV13-MINIMUM-HYDRATION-ROUTING-v1",
        {
            "semantic_plan_digest": semantic,
            "steps": [step.routing_identity for step in steps],
        },
    )
    return semantic, routing


def _decision(
    *,
    disposition: PlanDisposition,
    reason: str,
    law: EffectiveLawField,
    route: EpistemicRouteProjection,
    steps: Sequence[HydrationStep] = (),
    unresolved: Sequence[str] = (),
    minimum_level_proven: bool = False,
) -> MinimumHydrationPlan:
    unresolved_tuple = tuple(sorted(set(unresolved)))
    semantic, routing = _plan_digests(
        disposition=disposition,
        reason=reason,
        law_digest=law.digest,
        route_digest=route.route_receipt_digest,
        steps=steps,
        unresolved=unresolved_tuple,
    )
    plan = MinimumHydrationPlan(
        schema=SCHEMA,
        disposition=disposition,
        reason=reason,
        law_field_digest=law.digest,
        epistemic_route_receipt_digest=route.route_receipt_digest,
        steps=tuple(steps),
        unresolved_requirements=unresolved_tuple,
        semantic_plan_digest=semantic,
        routing_receipt_digest=routing,
        minimum_level_proven=minimum_level_proven,
    )
    plan.validate()
    return plan


def compile_minimum_hydration_route(
    *,
    law: EffectiveLawField,
    epistemic_route: EpistemicRouteProjection,
    requirements: Sequence[EvidenceRequirement],
    sources: Sequence[HydrationSourceProjection],
) -> MinimumHydrationPlan:
    """Compile a non-executing minimum *level* hydration route.

    Every LawField required-evidence atom must have exactly one EvidenceRequirement.
    Every requirement must resolve to exactly one source projection. Blocking
    epistemic debt is returned before any hydration step can be emitted.
    """
    law.validate_ceiling()
    epistemic_route.validate()

    requirement_tuple = tuple(requirements)
    for requirement in requirement_tuple:
        requirement.validate()
    requirement_ids = tuple(req.requirement_id for req in requirement_tuple)
    if len(requirement_ids) != len(set(requirement_ids)):
        raise ValueError("DUPLICATE_EVIDENCE_REQUIREMENT")
    if set(requirement_ids) != set(law.required_evidence):
        missing = sorted(set(law.required_evidence) - set(requirement_ids))
        extra = sorted(set(requirement_ids) - set(law.required_evidence))
        return _decision(
            disposition=PlanDisposition.HOLD_REQUIREMENT_UNBOUND,
            reason=f"LAW_REQUIREMENT_BINDING_MISMATCH:missing={missing}:extra={extra}",
            law=law,
            route=epistemic_route,
            unresolved=tuple(missing + extra),
        )

    source_map: dict[str, HydrationSourceProjection] = {}
    for source in sources:
        source.validate()
        if source.semantic_key in source_map:
            raise ValueError("DUPLICATE_HYDRATION_SOURCE_SEMANTIC_KEY")
        source_map[source.semantic_key] = source

    if epistemic_route.state in BLOCKING_EPISTEMIC_STATES:
        return _decision(
            disposition=PlanDisposition.HOLD_EPISTEMIC_DEBT,
            reason=f"BLOCKING_EPISTEMIC_STATE:{epistemic_route.state}",
            law=law,
            route=epistemic_route,
            unresolved=law.required_evidence,
        )

    for requirement in requirement_tuple:
        source = source_map.get(requirement.semantic_key)
        if source is None:
            return _decision(
                disposition=PlanDisposition.HOLD_REQUIREMENT_UNBOUND,
                reason=f"SOURCE_NOT_BOUND:{requirement.requirement_id}",
                law=law,
                route=epistemic_route,
                unresolved=(requirement.requirement_id,),
            )
        disposition, reason = _source_gate(requirement, source)
        if disposition is not None:
            return _decision(
                disposition=disposition,
                reason=f"{reason}:{requirement.requirement_id}",
                law=law,
                route=epistemic_route,
                unresolved=(requirement.requirement_id,),
            )

    left = _compile_requirement_first(requirement_tuple, source_map)
    right = _compile_source_first(requirement_tuple, source_map)
    if tuple(_step_signature(step) for step in left) != tuple(
        _step_signature(step) for step in right
    ):
        raise AssertionError("DIFFERENT_J_MINIMUM_HYDRATION_COMPILERS_DISAGREE")

    if left:
        if epistemic_route.state != "EXTERNAL_UNHYDRATED":
            return _decision(
                disposition=PlanDisposition.HOLD_ROUTE_REBASE_REQUIRED,
                reason="HYDRATION_DEFICIT_REQUIRES_EXTERNAL_UNHYDRATED_ROUTE",
                law=law,
                route=epistemic_route,
                unresolved=tuple(req.requirement_id for req in requirement_tuple),
            )
        if "HYDRATE" not in law.allowed_actions:
            return _decision(
                disposition=PlanDisposition.HOLD_LAW_FORBIDS_HYDRATION,
                reason="EFFECTIVE_LAW_DOES_NOT_ALLOW_HYDRATE",
                law=law,
                route=epistemic_route,
                unresolved=tuple(req.requirement_id for req in requirement_tuple),
            )
        return _decision(
            disposition=PlanDisposition.HYDRATE_MINIMUM,
            reason="MINIMUM_CONTIGUOUS_EKI_LEVEL_ROUTE",
            law=law,
            route=epistemic_route,
            steps=left,
            minimum_level_proven=True,
        )

    if epistemic_route.state != "KNOWN_CURRENT":
        return _decision(
            disposition=PlanDisposition.HOLD_ROUTE_REBASE_REQUIRED,
            reason="NO_HYDRATION_DEFICIT_REQUIRES_KNOWN_CURRENT_REBASE",
            law=law,
            route=epistemic_route,
        )
    return _decision(
        disposition=PlanDisposition.READY_NO_HYDRATION,
        reason="ALL_REQUIRED_EVIDENCE_AT_OR_ABOVE_MINIMUM_LEVEL",
        law=law,
        route=epistemic_route,
        minimum_level_proven=True,
    )


LAWS = (
    "MinimumHydrationLevel!=MinimumBytes!=MinimumASTCone",
    "Located!=Current!=Hydrated!=Authorized",
    "BlockingEpistemicDebtPrecedesHydration",
    "CurrentReference+VerifiedReader!=SemanticTruth",
    "SemanticHydrationNeed!=K27PlacementHint",
    "HydrationPlan!=Materialization!=EffectAuthority",
    "PersistedCurrentLabel!=ReadCurrentnessWitness",
    "NOT_REQUIREDCannotPayRequiredCurrentnessDebt",
    "ContiguousL0ToL4MeansSharedSourceTargetUsesMaximumRequiredLevel",
    "ExactSourceOptionalForSatisfiedEvidence!=ExactSourceOptionalForNewHydration",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)


__all__ = [
    "SCHEMA",
    "SOURCE_PROJECTION_SCHEMA",
    "ROUTE_PROJECTION_SCHEMA",
    "HydrationLevel",
    "PlanDisposition",
    "EpistemicRouteProjection",
    "EvidenceRequirement",
    "HydrationSourceProjection",
    "HydrationStep",
    "MinimumHydrationPlan",
    "compile_minimum_hydration_route",
    "LAWS",
]
