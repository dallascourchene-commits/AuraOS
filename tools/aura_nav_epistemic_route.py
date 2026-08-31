#!/usr/bin/env python3
"""NAV-07A: non-promoting epistemic classifier for located external routes.

Consumes projections of independently owned facts:
- NAV-03A locality resolution;
- EKI-2 version-preserving persistent history;
- EKI-R1 read-time source currentness.

The classifier does not perform those owner operations itself. It classifies the
minimum next debt before hydration/use while keeping "found" separate from
"current", "historical", "hydrated", and all authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import Iterable

SCHEMA = "AURA-NAV-07A-EPISTEMIC-ROUTE-v1"
NAV03A_HEAD = "e253c57dfa95f7655fbb4f9c560102413c183d4e"
PR739_HEAD = "b13ba81aa671693828e4fd97bd5b222db5d49d94"
PR737_HEAD = "55ae020ae1c06501935a45f3ade45eeff532d905"


class EpistemicError(ValueError):
    pass


class LocalityStatus(str, Enum):
    DISTINGUISHED = "DISTINGUISHED"
    LOCALITY_COLLISION = "LOCALITY_COLLISION"
    ANCESTOR_DESCENDANT_COLLISION = "ANCESTOR_DESCENDANT_COLLISION"
    NOT_EVALUATED = "NOT_EVALUATED"


class VersionStatus(str, Enum):
    SELECTED_VERSION_CANDIDATE = "SELECTED_VERSION_CANDIDATE"
    HISTORICAL_ONLY = "HISTORICAL_ONLY"
    AMBIGUOUS_HEAD = "AMBIGUOUS_HEAD"
    NOT_RESOLVED = "NOT_RESOLVED"


class CurrentnessStatus(str, Enum):
    RESOLVED_CURRENT = "RESOLVED_CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    NOT_REQUIRED = "NOT_REQUIRED"


class EpistemicState(str, Enum):
    KNOWN_CURRENT = "KNOWN_CURRENT"
    STALE = "STALE"
    HISTORICAL = "HISTORICAL"
    UNRESOLVED = "UNRESOLVED"
    COLLISION = "COLLISION"
    EXTERNAL_UNHYDRATED = "EXTERNAL_UNHYDRATED"
    OWNER_MISSING = "OWNER_MISSING"
    MAP_GAP = "MAP_GAP"
    UNKNOWN = "UNKNOWN"


class NextTransition(str, Enum):
    NONE = "NONE"
    DISCOVER_OWNER = "DISCOVER_OWNER"
    REPAIR_MAP = "REPAIR_MAP"
    QUOTIENT_COLLISION = "QUOTIENT_COLLISION"
    HISTORY_ONLY = "HISTORY_ONLY"
    RESOLVE_VERSION = "RESOLVE_VERSION"
    REOPEN_CURRENTNESS = "REOPEN_CURRENTNESS"
    RESOLVE_CURRENTNESS = "RESOLVE_CURRENTNESS"
    HYDRATE_MINIMUM = "HYDRATE_MINIMUM"


@dataclass(frozen=True)
class ExternalRouteEvidence:
    owner_ref: str | None
    map_present: bool
    locality: LocalityStatus
    version: VersionStatus
    currentness: CurrentnessStatus
    available_hydration_level: int
    required_hydration_level: int

    def validate(self) -> None:
        if self.owner_ref is not None and (
            not isinstance(self.owner_ref, str) or not self.owner_ref.strip()
        ):
            raise EpistemicError("OWNER_REF_MUST_BE_NONBLANK_OR_NONE")
        if type(self.map_present) is not bool:
            raise EpistemicError("MAP_PRESENT_MUST_BE_BOOL")
        if not isinstance(self.locality, LocalityStatus):
            raise EpistemicError("LOCALITY_STATUS_MUST_BE_TYPED")
        if not isinstance(self.version, VersionStatus):
            raise EpistemicError("VERSION_STATUS_MUST_BE_TYPED")
        if not isinstance(self.currentness, CurrentnessStatus):
            raise EpistemicError("CURRENTNESS_STATUS_MUST_BE_TYPED")
        for value, name in (
            (self.available_hydration_level, "AVAILABLE_HYDRATION_LEVEL"),
            (self.required_hydration_level, "REQUIRED_HYDRATION_LEVEL"),
        ):
            if type(value) is not int or not 0 <= value <= 4:
                raise EpistemicError(f"{name}_MUST_BE_L0_TO_L4")


@dataclass(frozen=True)
class EpistemicRouteReceipt:
    state: EpistemicState
    next_transition: NextTransition
    available_hydration_level: int
    required_hydration_level: int
    semantic_identity_proven_by_classifier: bool = False
    source_currentness_minted_from_persistence: bool = False
    persisted_current_label_used_as_witness: bool = False
    semantic_truth: bool = False
    authority: bool = False
    effect_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    schema: str = SCHEMA

    def validate(self) -> None:
        if not isinstance(self.state, EpistemicState):
            raise EpistemicError("EPISTEMIC_STATE_MUST_BE_TYPED")
        if not isinstance(self.next_transition, NextTransition):
            raise EpistemicError("NEXT_TRANSITION_MUST_BE_TYPED")
        for value in (self.available_hydration_level, self.required_hydration_level):
            if type(value) is not int or not 0 <= value <= 4:
                raise EpistemicError("HYDRATION_LEVEL_MUST_BE_L0_TO_L4")
        for field in (
            "semantic_identity_proven_by_classifier",
            "source_currentness_minted_from_persistence",
            "persisted_current_label_used_as_witness",
            "semantic_truth",
            "authority",
            "effect_authority",
            "native_private_transformer_kv_accessed",
        ):
            if getattr(self, field) is not False:
                raise EpistemicError(f"{field.upper()}_MUST_REMAIN_FALSE")
        if self.schema != SCHEMA:
            raise EpistemicError("EPISTEMIC_SCHEMA_MISMATCH")


def _receipt(
    evidence: ExternalRouteEvidence,
    state: EpistemicState,
    transition: NextTransition,
) -> EpistemicRouteReceipt:
    receipt = EpistemicRouteReceipt(
        state=state,
        next_transition=transition,
        available_hydration_level=evidence.available_hydration_level,
        required_hydration_level=evidence.required_hydration_level,
    )
    receipt.validate()
    return receipt


def classify_decision_tree(evidence: ExternalRouteEvidence) -> EpistemicRouteReceipt:
    """Formulation A: explicit decision tree ordered by blocking debt."""
    evidence.validate()

    if evidence.owner_ref is None:
        return _receipt(evidence, EpistemicState.OWNER_MISSING, NextTransition.DISCOVER_OWNER)
    if not evidence.map_present:
        return _receipt(evidence, EpistemicState.MAP_GAP, NextTransition.REPAIR_MAP)
    if evidence.locality in {
        LocalityStatus.LOCALITY_COLLISION,
        LocalityStatus.ANCESTOR_DESCENDANT_COLLISION,
    } or evidence.version is VersionStatus.AMBIGUOUS_HEAD:
        return _receipt(evidence, EpistemicState.COLLISION, NextTransition.QUOTIENT_COLLISION)
    if evidence.version is VersionStatus.HISTORICAL_ONLY:
        return _receipt(evidence, EpistemicState.HISTORICAL, NextTransition.HISTORY_ONLY)
    if (
        evidence.locality is LocalityStatus.NOT_EVALUATED
        or evidence.version is VersionStatus.NOT_RESOLVED
    ):
        return _receipt(evidence, EpistemicState.UNRESOLVED, NextTransition.RESOLVE_VERSION)
    if evidence.currentness is CurrentnessStatus.STALE:
        return _receipt(evidence, EpistemicState.STALE, NextTransition.REOPEN_CURRENTNESS)
    if evidence.currentness is CurrentnessStatus.UNKNOWN:
        return _receipt(evidence, EpistemicState.UNKNOWN, NextTransition.RESOLVE_CURRENTNESS)
    if evidence.currentness in {
        CurrentnessStatus.MISSING_REQUIRED,
        CurrentnessStatus.NOT_REQUIRED,
    }:
        return _receipt(evidence, EpistemicState.UNRESOLVED, NextTransition.RESOLVE_CURRENTNESS)
    if evidence.currentness is not CurrentnessStatus.RESOLVED_CURRENT:
        raise EpistemicError("UNHANDLED_CURRENTNESS_STATUS")
    if evidence.available_hydration_level < evidence.required_hydration_level:
        return _receipt(
            evidence,
            EpistemicState.EXTERNAL_UNHYDRATED,
            NextTransition.HYDRATE_MINIMUM,
        )
    return _receipt(evidence, EpistemicState.KNOWN_CURRENT, NextTransition.NONE)


def _rules(evidence: ExternalRouteEvidence):
    """Formulation B: ordered rule table, intentionally independent in shape."""
    return (
        (evidence.owner_ref is None, EpistemicState.OWNER_MISSING, NextTransition.DISCOVER_OWNER),
        (not evidence.map_present, EpistemicState.MAP_GAP, NextTransition.REPAIR_MAP),
        (
            evidence.locality
            in {
                LocalityStatus.LOCALITY_COLLISION,
                LocalityStatus.ANCESTOR_DESCENDANT_COLLISION,
            }
            or evidence.version is VersionStatus.AMBIGUOUS_HEAD,
            EpistemicState.COLLISION,
            NextTransition.QUOTIENT_COLLISION,
        ),
        (
            evidence.version is VersionStatus.HISTORICAL_ONLY,
            EpistemicState.HISTORICAL,
            NextTransition.HISTORY_ONLY,
        ),
        (
            evidence.locality is LocalityStatus.NOT_EVALUATED
            or evidence.version is VersionStatus.NOT_RESOLVED,
            EpistemicState.UNRESOLVED,
            NextTransition.RESOLVE_VERSION,
        ),
        (
            evidence.currentness is CurrentnessStatus.STALE,
            EpistemicState.STALE,
            NextTransition.REOPEN_CURRENTNESS,
        ),
        (
            evidence.currentness is CurrentnessStatus.UNKNOWN,
            EpistemicState.UNKNOWN,
            NextTransition.RESOLVE_CURRENTNESS,
        ),
        (
            evidence.currentness
            in {CurrentnessStatus.MISSING_REQUIRED, CurrentnessStatus.NOT_REQUIRED},
            EpistemicState.UNRESOLVED,
            NextTransition.RESOLVE_CURRENTNESS,
        ),
        (
            evidence.currentness is CurrentnessStatus.RESOLVED_CURRENT
            and evidence.available_hydration_level < evidence.required_hydration_level,
            EpistemicState.EXTERNAL_UNHYDRATED,
            NextTransition.HYDRATE_MINIMUM,
        ),
        (
            evidence.currentness is CurrentnessStatus.RESOLVED_CURRENT,
            EpistemicState.KNOWN_CURRENT,
            NextTransition.NONE,
        ),
    )


def classify_rule_table(evidence: ExternalRouteEvidence) -> EpistemicRouteReceipt:
    evidence.validate()
    for predicate, state, transition in _rules(evidence):
        if predicate:
            return _receipt(evidence, state, transition)
    raise EpistemicError("NO_EPISTEMIC_RULE_MATCHED")


def prove_classifier_different_j(
    evidence: ExternalRouteEvidence,
) -> EpistemicRouteReceipt:
    left = classify_decision_tree(evidence)
    right = classify_rule_table(evidence)
    if (left.state, left.next_transition) != (right.state, right.next_transition):
        raise EpistemicError("DIFFERENT_J_EPISTEMIC_CLASSIFIERS_DISAGREE")
    return left


def exhaustive_projection_space() -> Iterable[ExternalRouteEvidence]:
    """Finite full cross-product used by hosted proof."""
    for owner, map_present, locality, version, currentness, available, required in product(
        (None, "owner"),
        (False, True),
        tuple(LocalityStatus),
        tuple(VersionStatus),
        tuple(CurrentnessStatus),
        range(5),
        range(5),
    ):
        yield ExternalRouteEvidence(
            owner_ref=owner,
            map_present=map_present,
            locality=locality,
            version=version,
            currentness=currentness,
            available_hydration_level=available,
            required_hydration_level=required,
        )
