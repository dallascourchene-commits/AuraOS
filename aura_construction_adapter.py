"""Proposal-only SCO Construction coordination adapter for AuraOS.

This module composes the existing Construction contracts/state engine with Aura's
Liquid Planning contracts. It can query, hard-filter, rank, and explain digital
coordination candidates. It never authorizes physical work, releases payment,
controls access, certifies safety or engineering, or mutates authoritative
project records.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
from typing import Any, Iterable, Mapping

from aura_construction_contracts import (
    PATCH_AUTHORITY,
    PROPOSAL_ONLY,
    VSA_PATCH_AUTHORITY,
    ConstructionScope,
)
from aura_construction_state import (
    ConstructionProjectState,
    ConstructionReadinessReport,
    query_claim_readiness,
)
from aura_event_contracts import MeasurementClass, stable_digest, stable_id
from aura_liquid_planning_arena import (
    ActionCapsule,
    ArenaLease,
    BaseArenaAdapter,
    BoundaryContract,
)

CONSTRUCTION_ADAPTER_VERSION = "AURA_CONSTRUCTION_COORDINATION_ADAPTER_V1"
CONSTRUCTION_SIGNAL_VERSION = "AURA_CONSTRUCTION_PROBABILISTIC_SIGNAL_V1"
CONSTRUCTION_EVALUATION_VERSION = "AURA_CONSTRUCTION_COORDINATION_EVALUATION_V1"


class ConstructionArenaMode(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    OWNER_READ_ONLY = "OWNER_READ_ONLY"
    SHADOW = "SHADOW"


class ConstructionAdvisoryLane(str, Enum):
    DEPENDENCY_READINESS = "DEPENDENCY_READINESS"
    ALTERNATIVE_WORK = "ALTERNATIVE_WORK"
    PAYMENT_READINESS = "PAYMENT_READINESS"
    HAZARD_LOCATION = "HAZARD_LOCATION"


class ConstructionAuthorityRoute(str, Enum):
    OWNER_REVIEW_REQUIRED = "OWNER_REVIEW_REQUIRED"
    PROFESSIONAL_REVIEW_REQUIRED = "PROFESSIONAL_REVIEW_REQUIRED"
    REGULATORY_OR_LEGAL_REVIEW_REQUIRED = "REGULATORY_OR_LEGAL_REVIEW_REQUIRED"


class ConstructionRouteClass(str, Enum):
    DETERMINISTIC_QUERY = "DETERMINISTIC_QUERY"
    ADVISORY_EXPLANATION = "ADVISORY_EXPLANATION"
    MULTI_LANE_COMPARISON = "MULTI_LANE_COMPARISON"
    OWNER_REVIEW_REQUIRED = "OWNER_REVIEW_REQUIRED"


def _text(value: Any, name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _enum_value(value: Any, enum_type: type[Enum], name: str) -> str:
    raw = value.value if isinstance(value, enum_type) else value
    if type(raw) is not str or raw not in {item.value for item in enum_type}:
        raise ValueError(f"unknown {name}: {raw}")
    return raw


def _finite(value: Any, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _bounded(value: Any, name: str) -> float:
    number = _finite(value, name)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be between zero and one")
    return number


def _optional_bounded(value: Any, name: str) -> float | None:
    return None if value is None else _bounded(value, name)


def _optional_finite(value: Any, name: str) -> float | None:
    return None if value is None else _finite(value, name)


def _strings(values: Iterable[Any], name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be an iterable of strings")
    materialized = tuple(_text(item, f"{name}[]") for item in values)
    if len(materialized) != len(set(materialized)):
        raise ValueError(f"{name} must not contain duplicates")
    result = tuple(sorted(materialized))
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _measurement(value: Any, name: str) -> str:
    raw = value.value if isinstance(value, MeasurementClass) else value
    if type(raw) is not str or raw not in {item.value for item in MeasurementClass}:
        raise ValueError(f"unknown {name}: {raw}")
    return raw


def _normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return (value - low) / (high - low)


@dataclass(frozen=True)
class ConstructionCriterionScore:
    criterion: str
    expected_score: float
    variance: float
    repetitions: int
    measurement_class: str = MeasurementClass.MODEL_ESTIMATED.value

    def __post_init__(self) -> None:
        if self.criterion != _text(self.criterion, "criterion"):
            raise ValueError("criterion must be canonical normalized text")
        if type(self.expected_score) is not float:
            raise ValueError("expected_score must be a canonical float")
        _bounded(self.expected_score, "expected_score")
        if type(self.variance) is not float:
            raise ValueError("variance must be a canonical float")
        _bounded(self.variance, "variance")
        if type(self.repetitions) is not int or self.repetitions < 1:
            raise ValueError("repetitions must be a positive integer")
        if self.measurement_class != _measurement(
            self.measurement_class, "criterion.measurement_class"
        ):
            raise ValueError("measurement_class must be canonical")

    @classmethod
    def create(
        cls,
        *,
        criterion: str,
        expected_score: float,
        variance: float,
        repetitions: int,
        measurement_class: str | MeasurementClass = MeasurementClass.MODEL_ESTIMATED,
    ) -> "ConstructionCriterionScore":
        return cls(
            criterion=_text(criterion, "criterion"),
            expected_score=_bounded(expected_score, "expected_score"),
            variance=_bounded(variance, "variance"),
            repetitions=repetitions,
            measurement_class=_measurement(measurement_class, "measurement_class"),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionCriterionScore":
        data = dict(value)
        return cls(
            criterion=data.get("criterion"),
            expected_score=data.get("expected_score"),
            variance=data.get("variance"),
            repetitions=data.get("repetitions"),
            measurement_class=data.get("measurement_class"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionProbabilisticSignal:
    signal_id: str
    signal_digest: str
    candidate_id: str
    criteria: tuple[ConstructionCriterionScore, ...]
    aggregate_score: float
    uncertainty: float
    score_margin: float
    progress_score: float | None
    progress_slope: float | None
    distance_from_peak: float | None
    version: str = CONSTRUCTION_SIGNAL_VERSION
    measurement_class: str = MeasurementClass.MODEL_ESTIMATED.value
    proposal_only: bool = PROPOSAL_ONLY
    runtime_authority: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_SIGNAL_VERSION:
            raise ValueError("unsupported Construction probabilistic signal version")
        _text(self.candidate_id, "signal.candidate_id")
        if type(self.criteria) is not tuple or not self.criteria:
            raise ValueError("signal criteria must be a non-empty tuple")
        if not all(type(item) is ConstructionCriterionScore for item in self.criteria):
            raise ValueError("signal criteria must contain exact criterion scores")
        names = tuple(item.criterion for item in self.criteria)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise ValueError("signal criteria must use unique canonical sorted order")
        if type(self.aggregate_score) is not float:
            raise ValueError("aggregate_score must be a canonical float")
        _bounded(self.aggregate_score, "aggregate_score")
        if type(self.uncertainty) is not float:
            raise ValueError("uncertainty must be a canonical float")
        _bounded(self.uncertainty, "uncertainty")
        if type(self.score_margin) is not float:
            raise ValueError("score_margin must be a canonical float")
        _bounded(self.score_margin, "score_margin")
        for name, value in (
            ("progress_score", self.progress_score),
            ("distance_from_peak", self.distance_from_peak),
        ):
            if value is not None:
                if type(value) is not float:
                    raise ValueError(f"{name} must be a canonical float")
                _bounded(value, name)
        if self.progress_slope is not None:
            if type(self.progress_slope) is not float:
                raise ValueError("progress_slope must be a canonical float")
            _finite(self.progress_slope, "progress_slope")
        if self.measurement_class != _measurement(
            self.measurement_class, "signal.measurement_class"
        ):
            raise ValueError("signal measurement_class must be canonical")
        if (
            self.proposal_only is not True
            or self.runtime_authority is not False
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
        ):
            raise ValueError("probabilistic signal crossed its authority boundary")
        payload = self._identity_payload()
        if self.signal_digest != stable_digest(payload):
            raise ValueError("probabilistic signal digest does not match its content")
        if self.signal_id != stable_id("construction-probabilistic-signal", payload):
            raise ValueError("probabilistic signal ID does not match its content")

    @classmethod
    def create(
        cls,
        *,
        candidate_id: str,
        criteria: Iterable[ConstructionCriterionScore],
        score_margin: float = 0.0,
        progress_score: float | None = None,
        progress_slope: float | None = None,
        distance_from_peak: float | None = None,
        measurement_class: str | MeasurementClass = MeasurementClass.MODEL_ESTIMATED,
    ) -> "ConstructionProbabilisticSignal":
        items = tuple(sorted(tuple(criteria), key=lambda item: item.criterion))
        if not items:
            raise ValueError("criteria must not be empty")
        if not all(type(item) is ConstructionCriterionScore for item in items):
            raise ValueError("criteria must contain exact ConstructionCriterionScore values")
        aggregate = sum(item.expected_score for item in items) / len(items)
        uncertainty = math.sqrt(sum(item.variance for item in items) / len(items))
        values = {
            "candidate_id": _text(candidate_id, "candidate_id"),
            "criteria": items,
            "aggregate_score": float(aggregate),
            "uncertainty": float(min(1.0, uncertainty)),
            "score_margin": _bounded(score_margin, "score_margin"),
            "progress_score": _optional_bounded(progress_score, "progress_score"),
            "progress_slope": _optional_finite(progress_slope, "progress_slope"),
            "distance_from_peak": _optional_bounded(
                distance_from_peak, "distance_from_peak"
            ),
            "version": CONSTRUCTION_SIGNAL_VERSION,
            "measurement_class": _measurement(
                measurement_class, "measurement_class"
            ),
            "proposal_only": PROPOSAL_ONLY,
            "runtime_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload = cls._payload_from_values(values)
        return cls(
            signal_id=stable_id("construction-probabilistic-signal", payload),
            signal_digest=stable_digest(payload),
            **values,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionProbabilisticSignal":
        data = dict(value)
        return cls(
            signal_id=data.get("signal_id"),
            signal_digest=data.get("signal_digest"),
            candidate_id=data.get("candidate_id"),
            criteria=tuple(
                ConstructionCriterionScore.from_dict(item)
                for item in data.get("criteria", ())
            ),
            aggregate_score=data.get("aggregate_score"),
            uncertainty=data.get("uncertainty"),
            score_margin=data.get("score_margin"),
            progress_score=data.get("progress_score"),
            progress_slope=data.get("progress_slope"),
            distance_from_peak=data.get("distance_from_peak"),
            version=data.get("version"),
            measurement_class=data.get("measurement_class"),
            proposal_only=data.get("proposal_only"),
            runtime_authority=data.get("runtime_authority"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )

    @staticmethod
    def _payload_from_values(values: Mapping[str, Any]) -> dict[str, Any]:
        return {
            **dict(values),
            "criteria": [item.to_dict() for item in values["criteria"]],
        }

    def _identity_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("signal_id")
        data.pop("signal_digest")
        return data

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionCoordinationCandidate:
    candidate_id: str
    candidate_digest: str
    scope: ConstructionScope
    lane: str
    title: str
    summary: str
    required_claim_ids: tuple[str, ...]
    declared_hard_blockers: tuple[str, ...]
    assumptions: tuple[str, ...]
    authority_route: str
    projected_time_delta_hours: float
    projected_cost_delta_cad: float
    projected_idle_delta_hours: float
    safety_risk: float
    deadline_risk: float
    evidence_quality: float
    reversibility: float
    measurement_class: str
    version: str = CONSTRUCTION_ADAPTER_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    physical_work_authorized: bool = False
    payment_released: bool = False
    access_controlled: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_ADAPTER_VERSION:
            raise ValueError("unsupported Construction candidate version")
        if type(self.scope) is not ConstructionScope:
            raise ValueError("candidate scope must be an exact ConstructionScope")
        _enum_value(self.lane, ConstructionAdvisoryLane, "candidate.lane")
        if self.title != _text(self.title, "candidate.title"):
            raise ValueError("candidate title must be canonical normalized text")
        if self.summary != _text(self.summary, "candidate.summary"):
            raise ValueError("candidate summary must be canonical normalized text")
        _strings(self.required_claim_ids, "candidate.required_claim_ids")
        _strings(self.declared_hard_blockers, "candidate.declared_hard_blockers")
        _strings(self.assumptions, "candidate.assumptions")
        _enum_value(
            self.authority_route,
            ConstructionAuthorityRoute,
            "candidate.authority_route",
        )
        for name, value in (
            ("projected_time_delta_hours", self.projected_time_delta_hours),
            ("projected_cost_delta_cad", self.projected_cost_delta_cad),
            ("projected_idle_delta_hours", self.projected_idle_delta_hours),
        ):
            if type(value) is not float:
                raise ValueError(f"{name} must be a canonical float")
            _finite(value, name)
        for name, value in (
            ("safety_risk", self.safety_risk),
            ("deadline_risk", self.deadline_risk),
            ("evidence_quality", self.evidence_quality),
            ("reversibility", self.reversibility),
        ):
            if type(value) is not float:
                raise ValueError(f"{name} must be a canonical float")
            _bounded(value, name)
        if self.measurement_class != _measurement(
            self.measurement_class, "candidate.measurement_class"
        ):
            raise ValueError("candidate measurement_class must be canonical")
        if (
            self.proposal_only is not True
            or self.physical_work_authorized is not False
            or self.payment_released is not False
            or self.access_controlled is not False
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
        ):
            raise ValueError("Construction candidate crossed its authority boundary")
        payload = self._identity_payload()
        if self.candidate_digest != stable_digest(payload):
            raise ValueError("candidate digest does not match its content")
        if self.candidate_id != stable_id("construction-candidate", payload):
            raise ValueError("candidate ID does not match its content")

    @classmethod
    def create(
        cls,
        *,
        scope: ConstructionScope,
        lane: str | ConstructionAdvisoryLane,
        title: str,
        summary: str,
        required_claim_ids: Iterable[str] = (),
        declared_hard_blockers: Iterable[str] = (),
        assumptions: Iterable[str] = (),
        authority_route: str | ConstructionAuthorityRoute,
        projected_time_delta_hours: float,
        projected_cost_delta_cad: float,
        projected_idle_delta_hours: float,
        safety_risk: float,
        deadline_risk: float,
        evidence_quality: float,
        reversibility: float,
        measurement_class: str | MeasurementClass = MeasurementClass.DERIVED,
    ) -> "ConstructionCoordinationCandidate":
        if type(scope) is not ConstructionScope:
            raise ValueError("scope must be an exact ConstructionScope")
        values = {
            "scope": scope,
            "lane": _enum_value(lane, ConstructionAdvisoryLane, "lane"),
            "title": _text(title, "title"),
            "summary": _text(summary, "summary"),
            "required_claim_ids": _strings(required_claim_ids, "required_claim_ids"),
            "declared_hard_blockers": _strings(
                declared_hard_blockers, "declared_hard_blockers"
            ),
            "assumptions": _strings(assumptions, "assumptions"),
            "authority_route": _enum_value(
                authority_route, ConstructionAuthorityRoute, "authority_route"
            ),
            "projected_time_delta_hours": _finite(
                projected_time_delta_hours, "projected_time_delta_hours"
            ),
            "projected_cost_delta_cad": _finite(
                projected_cost_delta_cad, "projected_cost_delta_cad"
            ),
            "projected_idle_delta_hours": _finite(
                projected_idle_delta_hours, "projected_idle_delta_hours"
            ),
            "safety_risk": _bounded(safety_risk, "safety_risk"),
            "deadline_risk": _bounded(deadline_risk, "deadline_risk"),
            "evidence_quality": _bounded(evidence_quality, "evidence_quality"),
            "reversibility": _bounded(reversibility, "reversibility"),
            "measurement_class": _measurement(measurement_class, "measurement_class"),
            "version": CONSTRUCTION_ADAPTER_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload = cls._payload_from_values(values)
        return cls(
            candidate_id=stable_id("construction-candidate", payload),
            candidate_digest=stable_digest(payload),
            **values,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConstructionCoordinationCandidate":
        data = dict(value)
        return cls(
            candidate_id=data.get("candidate_id"),
            candidate_digest=data.get("candidate_digest"),
            scope=ConstructionScope.from_dict(dict(data.get("scope") or {})),
            lane=data.get("lane"),
            title=data.get("title"),
            summary=data.get("summary"),
            required_claim_ids=tuple(data.get("required_claim_ids", ())),
            declared_hard_blockers=tuple(data.get("declared_hard_blockers", ())),
            assumptions=tuple(data.get("assumptions", ())),
            authority_route=data.get("authority_route"),
            projected_time_delta_hours=data.get("projected_time_delta_hours"),
            projected_cost_delta_cad=data.get("projected_cost_delta_cad"),
            projected_idle_delta_hours=data.get("projected_idle_delta_hours"),
            safety_risk=data.get("safety_risk"),
            deadline_risk=data.get("deadline_risk"),
            evidence_quality=data.get("evidence_quality"),
            reversibility=data.get("reversibility"),
            measurement_class=data.get("measurement_class"),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            physical_work_authorized=data.get("physical_work_authorized"),
            payment_released=data.get("payment_released"),
            access_controlled=data.get("access_controlled"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )

    @staticmethod
    def _payload_from_values(values: Mapping[str, Any]) -> dict[str, Any]:
        return {
            **dict(values),
            "scope": values["scope"].to_dict(),
            "required_claim_ids": list(values["required_claim_ids"]),
            "declared_hard_blockers": list(values["declared_hard_blockers"]),
            "assumptions": list(values["assumptions"]),
        }

    def _identity_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("candidate_id")
        data.pop("candidate_digest")
        return data

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionCandidateAssessment:
    candidate_id: str
    admissible: bool
    blockers: tuple[str, ...]
    readiness_reports: tuple[ConstructionReadinessReport, ...]
    balanced_score: float
    rank_vector: tuple[float | str, ...]
    probabilistic_signal_id: str
    probabilistic_score: float | None
    uncertainty: float

    def __post_init__(self) -> None:
        _text(self.candidate_id, "assessment.candidate_id")
        if type(self.admissible) is not bool:
            raise ValueError("assessment admissible flag must be boolean")
        _strings(self.blockers, "assessment.blockers")
        if type(self.readiness_reports) is not tuple or not all(
            type(item) is ConstructionReadinessReport for item in self.readiness_reports
        ):
            raise ValueError("assessment readiness reports must be exact reports")
        if self.admissible == bool(self.blockers):
            raise ValueError("assessment admissibility and blockers disagree")
        if type(self.balanced_score) is not float:
            raise ValueError("balanced_score must be a canonical float")
        _bounded(self.balanced_score, "balanced_score")
        if type(self.rank_vector) is not tuple or not self.rank_vector:
            raise ValueError("rank_vector must be a non-empty tuple")
        if type(self.probabilistic_signal_id) is not str:
            raise ValueError("probabilistic_signal_id must be a string")
        if self.probabilistic_score is not None:
            if type(self.probabilistic_score) is not float:
                raise ValueError("probabilistic_score must be a canonical float")
            _bounded(self.probabilistic_score, "probabilistic_score")
        if type(self.uncertainty) is not float:
            raise ValueError("uncertainty must be a canonical float")
        _bounded(self.uncertainty, "uncertainty")

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "readiness_reports": [item.to_dict() for item in self.readiness_reports],
            "rank_vector": list(self.rank_vector),
        }


@dataclass(frozen=True)
class ConstructionCoordinationEvaluation:
    evaluation_id: str
    evaluation_digest: str
    mode: str
    lane: str
    route_class: str
    state_digest: str
    evaluated_at: float
    assessments: tuple[ConstructionCandidateAssessment, ...]
    recommended_candidate_id: str
    option_candidate_ids: tuple[str, ...]
    next_authority_route: str
    version: str = CONSTRUCTION_EVALUATION_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    human_release_required: bool = True
    physical_work_authorized: bool = False
    payment_released: bool = False
    access_controlled: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_EVALUATION_VERSION:
            raise ValueError("unsupported Construction evaluation version")
        _enum_value(self.mode, ConstructionArenaMode, "evaluation.mode")
        _enum_value(self.lane, ConstructionAdvisoryLane, "evaluation.lane")
        _enum_value(self.route_class, ConstructionRouteClass, "evaluation.route_class")
        _text(self.state_digest, "evaluation.state_digest")
        if type(self.evaluated_at) is not float:
            raise ValueError("evaluated_at must be a canonical float")
        _finite(self.evaluated_at, "evaluated_at")
        if type(self.assessments) is not tuple or not all(
            type(item) is ConstructionCandidateAssessment for item in self.assessments
        ):
            raise ValueError("evaluation assessments must be exact assessment values")
        assessment_ids = tuple(item.candidate_id for item in self.assessments)
        if assessment_ids != tuple(sorted(assessment_ids)):
            raise ValueError("evaluation assessments must use canonical candidate order")
        if len(assessment_ids) != len(set(assessment_ids)):
            raise ValueError("evaluation assessments must not contain duplicate candidates")
        if type(self.recommended_candidate_id) is not str:
            raise ValueError("recommended_candidate_id must be a string")
        admissible = {item.candidate_id for item in self.assessments if item.admissible}
        if self.recommended_candidate_id and self.recommended_candidate_id not in admissible:
            raise ValueError("recommended candidate must be admissible")
        _strings(self.option_candidate_ids, "evaluation.option_candidate_ids")
        if not set(self.option_candidate_ids).issubset(admissible):
            raise ValueError("all displayed options must be admissible")
        if len(self.option_candidate_ids) > 4:
            raise ValueError("evaluation may expose at most four options")
        if self.next_authority_route:
            _enum_value(
                self.next_authority_route,
                ConstructionAuthorityRoute,
                "evaluation.next_authority_route",
            )
        if (
            self.proposal_only is not True
            or self.human_release_required is not True
            or self.physical_work_authorized is not False
            or self.payment_released is not False
            or self.access_controlled is not False
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
        ):
            raise ValueError("Construction evaluation crossed its authority boundary")
        payload = self._identity_payload()
        if self.evaluation_digest != stable_digest(payload):
            raise ValueError("evaluation digest does not match its content")
        if self.evaluation_id != stable_id("construction-evaluation", payload):
            raise ValueError("evaluation ID does not match its content")

    def _identity_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("evaluation_id")
        data.pop("evaluation_digest")
        return data

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "assessments": [item.to_dict() for item in self.assessments],
        }


def _route_class(admissible_count: int, candidate_count: int) -> str:
    if admissible_count == 0:
        return ConstructionRouteClass.OWNER_REVIEW_REQUIRED.value
    if admissible_count > 1:
        return ConstructionRouteClass.MULTI_LANE_COMPARISON.value
    if candidate_count == 1:
        return ConstructionRouteClass.DETERMINISTIC_QUERY.value
    return ConstructionRouteClass.ADVISORY_EXPLANATION.value


def evaluate_construction_candidates(
    state: ConstructionProjectState,
    *,
    candidates: Iterable[ConstructionCoordinationCandidate],
    now: float,
    mode: str | ConstructionArenaMode,
    lane: str | ConstructionAdvisoryLane,
    probabilistic_signals: Iterable[ConstructionProbabilisticSignal] = (),
) -> ConstructionCoordinationEvaluation:
    """Hard-filter and rank state-local proposal-only coordination candidates."""
    if type(state) is not ConstructionProjectState:
        raise ValueError("state must be an exact ConstructionProjectState")
    state.__post_init__()
    evaluated_at = _finite(now, "now")
    mode_value = _enum_value(mode, ConstructionArenaMode, "mode")
    lane_value = _enum_value(lane, ConstructionAdvisoryLane, "lane")

    candidate_items = tuple(candidates)
    if not all(type(item) is ConstructionCoordinationCandidate for item in candidate_items):
        raise ValueError("candidates must contain exact ConstructionCoordinationCandidate values")
    candidate_by_id = {item.candidate_id: item for item in candidate_items}
    if len(candidate_by_id) != len(candidate_items):
        raise ValueError("candidate IDs must be unique")
    if any(item.lane != lane_value for item in candidate_items):
        raise ValueError("all candidates must match the requested advisory lane")

    signal_items = tuple(probabilistic_signals)
    if not all(type(item) is ConstructionProbabilisticSignal for item in signal_items):
        raise ValueError("probabilistic_signals must contain exact signal values")
    signal_by_candidate = {item.candidate_id: item for item in signal_items}
    if len(signal_by_candidate) != len(signal_items):
        raise ValueError("each candidate may have at most one probabilistic signal")
    unknown_signal_candidates = set(signal_by_candidate).difference(candidate_by_id)
    if unknown_signal_candidates:
        raise ValueError(
            "probabilistic signals reference unknown candidates: "
            f"{sorted(unknown_signal_candidates)}"
        )

    dynamic: dict[str, tuple[tuple[str, ...], tuple[ConstructionReadinessReport, ...]]] = {}
    for candidate in candidate_items:
        blockers = list(candidate.declared_hard_blockers)
        if candidate.scope.project_id != state.project_id:
            blockers.append("candidate_project_scope_mismatch")
        reports = tuple(
            query_claim_readiness(state, claim_id=claim_id, now=evaluated_at)
            for claim_id in candidate.required_claim_ids
        )
        for report in reports:
            blockers.extend(
                f"claim:{report.claim_id}:{blocker}" for blocker in report.blockers
            )
        dynamic[candidate.candidate_id] = (
            tuple(sorted(set(blockers))),
            reports,
        )

    admissible_candidates = [
        item for item in candidate_items if not dynamic[item.candidate_id][0]
    ]
    if admissible_candidates:
        times = [item.projected_time_delta_hours for item in admissible_candidates]
        costs = [item.projected_cost_delta_cad for item in admissible_candidates]
        idle = [item.projected_idle_delta_hours for item in admissible_candidates]
        time_bounds = (min(times), max(times))
        cost_bounds = (min(costs), max(costs))
        idle_bounds = (min(idle), max(idle))
    else:
        time_bounds = cost_bounds = idle_bounds = (0.0, 0.0)

    assessments: list[ConstructionCandidateAssessment] = []
    for candidate in candidate_items:
        blockers, reports = dynamic[candidate.candidate_id]
        signal = signal_by_candidate.get(candidate.candidate_id)
        probability = signal.aggregate_score if signal else None
        uncertainty = signal.uncertainty if signal else 1.0
        evidence_gap = float(sum(1 for report in reports if not report.ready))
        normalized_time = _normalize(
            candidate.projected_time_delta_hours, *time_bounds
        )
        normalized_cost = _normalize(candidate.projected_cost_delta_cad, *cost_bounds)
        normalized_idle = _normalize(
            candidate.projected_idle_delta_hours, *idle_bounds
        )
        probability_penalty = 1.0 - (
            probability if probability is not None else candidate.evidence_quality
        )
        penalty = (
            0.30 * candidate.safety_risk
            + 0.20 * candidate.deadline_risk
            + 0.10 * normalized_time
            + 0.10 * normalized_cost
            + 0.10 * normalized_idle
            + 0.08 * probability_penalty
            + 0.07 * uncertainty
            + 0.05 * (1.0 - candidate.reversibility)
        )
        balanced_score = max(0.0, min(1.0, 1.0 - penalty))
        rank_vector: tuple[float | str, ...] = (
            candidate.safety_risk,
            evidence_gap,
            candidate.deadline_risk,
            uncertainty,
            probability_penalty,
            normalized_time,
            normalized_cost,
            normalized_idle,
            -candidate.reversibility,
            candidate.candidate_id,
        )
        assessments.append(
            ConstructionCandidateAssessment(
                candidate_id=candidate.candidate_id,
                admissible=not blockers,
                blockers=blockers,
                readiness_reports=reports,
                balanced_score=float(balanced_score),
                rank_vector=rank_vector,
                probabilistic_signal_id=signal.signal_id if signal else "",
                probabilistic_score=probability,
                uncertainty=float(uncertainty),
            )
        )

    assessment_by_id = {item.candidate_id: item for item in assessments}
    ranked = sorted(
        admissible_candidates,
        key=lambda item: assessment_by_id[item.candidate_id].rank_vector,
    )
    recommended_id = ranked[0].candidate_id if ranked else ""

    options: list[str] = []
    if ranked:
        selectors = (
            min(ranked, key=lambda item: (item.projected_cost_delta_cad, item.candidate_id)),
            min(ranked, key=lambda item: (item.projected_time_delta_hours, item.candidate_id)),
            ranked[0],
            min(ranked, key=lambda item: (item.safety_risk, item.deadline_risk, item.candidate_id)),
        )
        for item in selectors:
            if item.candidate_id not in options:
                options.append(item.candidate_id)
        for item in ranked:
            if item.candidate_id not in options:
                options.append(item.candidate_id)
            if len(options) >= 4:
                break

    next_authority = ""
    if recommended_id:
        next_authority = candidate_by_id[recommended_id].authority_route

    values = {
        "mode": mode_value,
        "lane": lane_value,
        "route_class": _route_class(len(ranked), len(candidate_items)),
        "state_digest": state.state_digest,
        "evaluated_at": float(evaluated_at),
        "assessments": tuple(sorted(assessments, key=lambda item: item.candidate_id)),
        "recommended_candidate_id": recommended_id,
        "option_candidate_ids": tuple(sorted(options)),
        "next_authority_route": next_authority,
        "version": CONSTRUCTION_EVALUATION_VERSION,
        "proposal_only": PROPOSAL_ONLY,
        "human_release_required": True,
        "physical_work_authorized": False,
        "payment_released": False,
        "access_controlled": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    payload = {
        **values,
        "assessments": [item.to_dict() for item in values["assessments"]],
        "option_candidate_ids": list(values["option_candidate_ids"]),
    }
    return ConstructionCoordinationEvaluation(
        evaluation_id=stable_id("construction-evaluation", payload),
        evaluation_digest=stable_digest(payload),
        **values,
    )


class ConstructionArenaAdapter(BaseArenaAdapter):
    """Liquid Planning domain adapter for proposal-only Construction coordination."""

    domain = "construction"
    domain_objects = (
        "project_scopes",
        "claims",
        "evidence",
        "append_only_events",
        "readiness_reports",
        "conflicts",
        "coordination_candidates",
        "probabilistic_signals",
        "human_authority_routes",
    )

    def schema(self) -> dict[str, Any]:
        return {
            **super().schema(),
            "modes": [item.value for item in ConstructionArenaMode],
            "advisory_lanes": [item.value for item in ConstructionAdvisoryLane],
            "proposal_only": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "probabilistic_signals_authoritative": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def action_capsule_from_intent(
        self,
        *,
        objective: str,
        capsule_id: str,
        target: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
    ) -> ActionCapsule:
        target_value = dict(target or {})
        mode = _enum_value(
            target_value.get("mode", ConstructionArenaMode.SYNTHETIC.value),
            ConstructionArenaMode,
            "target.mode",
        )
        lane = _enum_value(
            target_value.get(
                "lane", ConstructionAdvisoryLane.DEPENDENCY_READINESS.value
            ),
            ConstructionAdvisoryLane,
            "target.lane",
        )
        project_id = _text(target_value.get("project_id"), "target.project_id")
        scope = {
            "regions": [
                {
                    "region_type": "construction_project",
                    "id": project_id,
                    "mode": "read_only",
                }
            ],
            "arena_mode": mode,
            "advisory_lane": lane,
        }
        return ActionCapsule.create(
            capsule_id=_text(capsule_id, "capsule_id"),
            domain=self.domain,
            role="construction_coordination_advisor",
            objective=_text(objective, "objective"),
            target={**target_value, "mode": mode, "lane": lane, "project_id": project_id},
            scope=scope,
            allowed_actions=[
                "read exact Construction state and evidence projections",
                "run deterministic readiness and conflict queries",
                "hard-filter invalid or unsafe digital candidates",
                "rank proposal-only coordination alternatives",
                "attach non-authoritative probabilistic signals",
                "prepare evidence-repair and human-escalation packets",
            ],
            forbidden_actions=[
                "authorize physical work",
                "certify safety or engineering",
                "release payment or transfer funds",
                "control physical access",
                "operate equipment",
                "discipline workers",
                "treat sensor or location evidence as dispositive proof",
                "let a probabilistic score override a failed hard constraint",
                "mutate authoritative project records",
            ],
            acceptance_checks=[
                "all required claims queried against exact state digest",
                "hard blockers removed before ranking",
                "all options preserve human release requirements",
                "probabilistic signals remain proposal-only",
                *(constraints or []),
            ],
            expected_output="CONSTRUCTION_COORDINATION_PACKET",
            escalation_triggers=[
                "missing or expired evidence",
                "conflicting active claims or evidence",
                "professional regulatory or legal review required",
                "all candidates blocked",
            ],
            metadata={
                "adapter_version": CONSTRUCTION_ADAPTER_VERSION,
                "proposal_only": True,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            },
        )

    def boundary_contract_for_scope(
        self,
        *,
        capsule: ActionCapsule,
        scope: ConstructionScope,
        mode: str | ConstructionArenaMode,
    ) -> BoundaryContract:
        if type(capsule) is not ActionCapsule:
            raise ValueError("capsule must be an exact ActionCapsule")
        if type(scope) is not ConstructionScope:
            raise ValueError("scope must be an exact ConstructionScope")
        mode_value = _enum_value(mode, ConstructionArenaMode, "mode")
        return BoundaryContract.placeholder(
            domain=self.domain,
            capsule_id=capsule.capsule_id,
            boundary_type="construction_coordination_boundary",
            external_system="owner project records and authorized human workflow",
            source_region={
                "project_id": scope.project_id,
                "zone_id": scope.zone_id,
                "work_package_id": scope.work_package_id,
                "mode": mode_value,
            },
            owned_scope=[scope.scope_key],
            assumptions=[
                "source records remain authoritative",
                "mock fixture values are not real project facts",
                "human professional contractual legal and regulatory authority remains external",
            ],
            required_inputs=[
                "exact Construction state digest",
                "required claim IDs",
                "candidate assumptions and measurement classes",
            ],
            promised_outputs=[
                "proposal-only coordination evaluation",
                "blocked-candidate reasons",
                "next-authority route",
            ],
            constraints=[
                "read-only or synthetic operation",
                "no physical work authorization",
                "no payment release",
                "no access control",
                "no model score may override a hard blocker",
            ],
            escalation_triggers=[
                "evidence gap",
                "authority gap",
                "privacy or consent conflict",
                "all routes blocked",
            ],
            invariant=(
                "Aura represents and evaluates digital claims; authorized people govern "
                "physical contractual professional regulatory and legal decisions"
            ),
            metadata={
                "proposal_only": True,
                "human_release_required": True,
                "adapter_version": CONSTRUCTION_ADAPTER_VERSION,
            },
        )

    def lease_for_capsule(
        self,
        *,
        capsule: ActionCapsule,
        scope: ConstructionScope,
    ) -> ArenaLease:
        if type(capsule) is not ActionCapsule:
            raise ValueError("capsule must be an exact ActionCapsule")
        if type(scope) is not ConstructionScope:
            raise ValueError("scope must be an exact ConstructionScope")
        return ArenaLease.create(
            domain=self.domain,
            capsule_id=capsule.capsule_id,
            holder="construction_coordination_advisor",
            regions=[
                {
                    "region_type": "construction_scope",
                    "id": scope.scope_key,
                    "mode": "read_only",
                }
            ],
            allowed_actions=capsule.allowed_actions,
            forbidden_actions=capsule.forbidden_actions,
            mode="read_only",
            conflict_policy="deny_then_escalate",
            metadata={
                "action_phase_hash": capsule.phase_hash,
                "proposal_only": True,
                "human_release_required": True,
            },
        )

    def build_runtime_packet(
        self,
        *,
        objective: str,
        state: ConstructionProjectState,
        scope: ConstructionScope,
        candidates: Iterable[ConstructionCoordinationCandidate],
        now: float,
        mode: str | ConstructionArenaMode,
        lane: str | ConstructionAdvisoryLane,
        probabilistic_signals: Iterable[ConstructionProbabilisticSignal] = (),
    ) -> dict[str, Any]:
        if type(state) is not ConstructionProjectState:
            raise ValueError("state must be an exact ConstructionProjectState")
        if type(scope) is not ConstructionScope:
            raise ValueError("scope must be an exact ConstructionScope")
        candidate_items = tuple(candidates)
        signal_items = tuple(probabilistic_signals)
        mode_value = _enum_value(mode, ConstructionArenaMode, "mode")
        lane_value = _enum_value(lane, ConstructionAdvisoryLane, "lane")
        capsule_id = stable_id(
            "construction-coordination-capsule",
            {
                "objective": _text(objective, "objective"),
                "state_digest": state.state_digest,
                "scope": scope.to_dict(),
                "candidate_ids": sorted(item.candidate_id for item in candidate_items),
                "mode": mode_value,
                "lane": lane_value,
            },
        )
        capsule = self.action_capsule_from_intent(
            objective=objective,
            capsule_id=capsule_id,
            target={
                "project_id": scope.project_id,
                "zone_id": scope.zone_id,
                "work_package_id": scope.work_package_id,
                "mode": mode_value,
                "lane": lane_value,
                "state_digest": state.state_digest,
            },
        )
        boundary = self.boundary_contract_for_scope(
            capsule=capsule, scope=scope, mode=mode_value
        )
        lease = self.lease_for_capsule(capsule=capsule, scope=scope)
        evaluation = evaluate_construction_candidates(
            state,
            candidates=candidate_items,
            now=now,
            mode=mode_value,
            lane=lane_value,
            probabilistic_signals=signal_items,
        )
        return {
            "ok": True,
            "version": CONSTRUCTION_ADAPTER_VERSION,
            "adapter": self.schema(),
            "action_capsule": capsule.to_dict(),
            "boundary_contract": boundary.to_dict(),
            "arena_lease": lease.to_dict(),
            "evaluation": evaluation.to_dict(),
            "state_digest": state.state_digest,
            "source_records_mutated": False,
            "proposal_only": True,
            "human_release_required": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


__all__ = [
    "CONSTRUCTION_ADAPTER_VERSION",
    "CONSTRUCTION_SIGNAL_VERSION",
    "CONSTRUCTION_EVALUATION_VERSION",
    "ConstructionArenaMode",
    "ConstructionAdvisoryLane",
    "ConstructionAuthorityRoute",
    "ConstructionRouteClass",
    "ConstructionCriterionScore",
    "ConstructionProbabilisticSignal",
    "ConstructionCoordinationCandidate",
    "ConstructionCandidateAssessment",
    "ConstructionCoordinationEvaluation",
    "ConstructionArenaAdapter",
    "evaluate_construction_candidates",
]
