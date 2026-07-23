"""Asset-pack-bound synthetic Construction Arena fixture contracts.

This module extends Aura's existing canonical Construction owners.  It does not
create a second project ledger, schedule authority, financial authority,
regulatory authority, professional release path, or renderer authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
import re
from typing import Any

from aura_construction_adapter import (
    ConstructionCoordinationCandidate,
    ConstructionProbabilisticSignal,
)
from aura_construction_contracts import ConstructionScope
from aura_construction_demo_contracts import ConstructionDemoAssetPack
from aura_construction_state import ConstructionProjectState
from aura_event_contracts import stable_digest

CONSTRUCTION_DEMO_FIXTURE_VERSION = "AURA_CONSTRUCTION_DEMO_FIXTURE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_HEX_DIGEST = re.compile(r"^(?:[0-9a-f]{32}|[0-9a-f]{64})$")


class ConstructionDemoWorkStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    DELAYED = "DELAYED"
    COMPLETED = "COMPLETED"
    REWORK_REQUIRED = "REWORK_REQUIRED"
    AWAITING_INSPECTION = "AWAITING_INSPECTION"
    AWAITING_PROFESSIONAL_RELEASE = "AWAITING_PROFESSIONAL_RELEASE"


class ConstructionDemoRecordTruth(str, Enum):
    SYNTHETIC_DEMO_SCHEDULE = "SYNTHETIC_DEMO_SCHEDULE"
    SYNTHETIC_DEMO_BUDGET = "SYNTHETIC_DEMO_BUDGET"
    SYNTHETIC_DEMO_RULE = "SYNTHETIC_DEMO_RULE"
    SYNTHETIC_DEMO_ACTIVITY = "SYNTHETIC_DEMO_ACTIVITY"
    SYNTHETIC_DEMO_HAZARD = "SYNTHETIC_DEMO_HAZARD"
    SYNTHETIC_DEMO_INSPECTION = "SYNTHETIC_DEMO_INSPECTION"
    SYNTHETIC_DEMO_PROPOSAL = "SYNTHETIC_DEMO_PROPOSAL"


MINIMUM_TRADE_NAMES = frozenset(
    {
        "asbestos abatement",
        "crane and logistics",
        "demolition",
        "electrical",
        "fire protection",
        "general contractor",
        "inspection",
        "mechanical",
        "plumbing",
        "roofing",
        "structural",
        "temporary labour",
    }
)


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical identifier")
    return value


def _text(value: Any, name: str, *, maximum: int = 512) -> str:
    if type(value) is not str or not value or value != " ".join(value.split()):
        raise ValueError(f"{name} must be normalized non-empty text")
    if len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{name} exceeds {maximum} bytes")
    return value


def _ids(value: Any, name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    result = tuple(_identifier(item, f"{name}[]") for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    if result != tuple(sorted(set(result))):
        raise ValueError(f"{name} must be sorted and unique")
    return result


def _finite(value: Any, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _nonnegative(value: Any, name: str) -> float:
    result = _finite(value, name)
    if result < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _digest(value: Any, name: str) -> str:
    if type(value) is not str or _HEX_DIGEST.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase 32- or 64-character digest")
    return value


def _strict_boundary(value: Any, name: str, expected: bool) -> None:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"{name} must be {str(expected).lower()}")


@dataclass(frozen=True)
class ConstructionDemoTrade:
    trade_id: str
    name: str
    subcontractor_id: str
    truth_class: str = ConstructionDemoRecordTruth.SYNTHETIC_DEMO_ACTIVITY.value
    person_level_data_included: bool = False

    def __post_init__(self) -> None:
        _identifier(self.trade_id, "trade_id")
        _text(self.name, "trade.name", maximum=128)
        _identifier(self.subcontractor_id, "subcontractor_id")
        if self.truth_class != ConstructionDemoRecordTruth.SYNTHETIC_DEMO_ACTIVITY.value:
            raise ValueError("trade truth_class must remain synthetic")
        _strict_boundary(self.person_level_data_included, "person_level_data_included", False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionDemoWorkPackage:
    work_package_id: str
    storey_id: str
    zone_id: str
    title: str
    trade_id: str
    status: str
    scope: ConstructionScope
    planned_start_day: float
    planned_finish_day: float
    dependency_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    inspection_ids: tuple[str, ...] = ()
    hazard_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    crane_window_id: str | None = None
    professional_release_required: bool = False
    truth_class: str = ConstructionDemoRecordTruth.SYNTHETIC_DEMO_SCHEDULE.value
    projection_only: bool = True

    def __post_init__(self) -> None:
        _identifier(self.work_package_id, "work_package_id")
        _identifier(self.storey_id, "storey_id")
        _identifier(self.zone_id, "zone_id")
        _text(self.title, "work_package.title")
        _identifier(self.trade_id, "trade_id")
        if self.status not in {item.value for item in ConstructionDemoWorkStatus}:
            raise ValueError("unsupported work-package status")
        if type(self.scope) is not ConstructionScope:
            raise ValueError("work-package scope must be an exact ConstructionScope")
        if self.scope.zone_id != self.zone_id or self.scope.work_package_id != self.work_package_id:
            raise ValueError("work-package scope does not match its identifiers")
        start = _finite(self.planned_start_day, "planned_start_day")
        finish = _finite(self.planned_finish_day, "planned_finish_day")
        if finish < start:
            raise ValueError("planned_finish_day must not predate planned_start_day")
        for field_name in (
            "dependency_ids",
            "evidence_refs",
            "inspection_ids",
            "hazard_ids",
            "rule_ids",
        ):
            _ids(getattr(self, field_name), field_name)
        if self.work_package_id in self.dependency_ids:
            raise ValueError("work package cannot depend on itself")
        if self.crane_window_id is not None:
            _identifier(self.crane_window_id, "crane_window_id")
        if type(self.professional_release_required) is not bool:
            raise ValueError("professional_release_required must be boolean")
        if self.truth_class != ConstructionDemoRecordTruth.SYNTHETIC_DEMO_SCHEDULE.value:
            raise ValueError("work-package truth_class must remain synthetic")
        _strict_boundary(self.projection_only, "projection_only", True)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "scope": self.scope.to_dict()}


@dataclass(frozen=True)
class ConstructionDemoBudgetLine:
    budget_line_id: str
    work_package_id: str
    description: str
    committed_cad: float
    forecast_cad: float
    actual_cad: float
    truth_class: str = ConstructionDemoRecordTruth.SYNTHETIC_DEMO_BUDGET.value
    financial_authority: bool = False

    def __post_init__(self) -> None:
        _identifier(self.budget_line_id, "budget_line_id")
        _identifier(self.work_package_id, "work_package_id")
        _text(self.description, "budget_line.description")
        _nonnegative(self.committed_cad, "committed_cad")
        _nonnegative(self.forecast_cad, "forecast_cad")
        _nonnegative(self.actual_cad, "actual_cad")
        if self.truth_class != ConstructionDemoRecordTruth.SYNTHETIC_DEMO_BUDGET.value:
            raise ValueError("budget truth_class must remain synthetic")
        _strict_boundary(self.financial_authority, "financial_authority", False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionDemoRule:
    rule_id: str
    title: str
    applies_to_work_package_ids: tuple[str, ...]
    requirement: str
    truth_class: str = ConstructionDemoRecordTruth.SYNTHETIC_DEMO_RULE.value
    legal_authority: bool = False
    regulatory_authority: bool = False
    jurisdiction_claimed: str = "none"

    def __post_init__(self) -> None:
        _identifier(self.rule_id, "rule_id")
        _text(self.title, "rule.title")
        _ids(self.applies_to_work_package_ids, "applies_to_work_package_ids", allow_empty=False)
        _text(self.requirement, "rule.requirement")
        if self.truth_class != ConstructionDemoRecordTruth.SYNTHETIC_DEMO_RULE.value:
            raise ValueError("rule truth_class must remain synthetic")
        _strict_boundary(self.legal_authority, "legal_authority", False)
        _strict_boundary(self.regulatory_authority, "regulatory_authority", False)
        if self.jurisdiction_claimed != "none":
            raise ValueError("synthetic demo rules cannot claim a jurisdiction")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionDemoInspection:
    inspection_id: str
    work_package_id: str
    title: str
    status: str
    scheduled_day: float
    truth_class: str = ConstructionDemoRecordTruth.SYNTHETIC_DEMO_INSPECTION.value
    professional_release_authority: bool = False

    def __post_init__(self) -> None:
        _identifier(self.inspection_id, "inspection_id")
        _identifier(self.work_package_id, "work_package_id")
        _text(self.title, "inspection.title")
        if self.status not in {"NOT_SCHEDULED", "SCHEDULED", "PASSED", "FAILED", "AWAITING_REVIEW"}:
            raise ValueError("unsupported synthetic inspection status")
        _finite(self.scheduled_day, "scheduled_day")
        if self.truth_class != ConstructionDemoRecordTruth.SYNTHETIC_DEMO_INSPECTION.value:
            raise ValueError("inspection truth_class must remain synthetic")
        _strict_boundary(
            self.professional_release_authority,
            "professional_release_authority",
            False,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionDemoHazard:
    hazard_id: str
    work_package_id: str
    title: str
    severity: str
    active: bool
    evidence_refs: tuple[str, ...] = ()
    truth_class: str = ConstructionDemoRecordTruth.SYNTHETIC_DEMO_HAZARD.value
    physical_work_authority: bool = False

    def __post_init__(self) -> None:
        _identifier(self.hazard_id, "hazard_id")
        _identifier(self.work_package_id, "work_package_id")
        _text(self.title, "hazard.title")
        if self.severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("unsupported synthetic hazard severity")
        if type(self.active) is not bool:
            raise ValueError("hazard.active must be boolean")
        _ids(self.evidence_refs, "hazard.evidence_refs")
        if self.truth_class != ConstructionDemoRecordTruth.SYNTHETIC_DEMO_HAZARD.value:
            raise ValueError("hazard truth_class must remain synthetic")
        _strict_boundary(self.physical_work_authority, "physical_work_authority", False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionDemoActivity:
    activity_id: str
    work_package_id: str
    trade_id: str
    day: float
    status: str
    note: str
    truth_class: str = ConstructionDemoRecordTruth.SYNTHETIC_DEMO_ACTIVITY.value
    person_level_data_included: bool = False

    def __post_init__(self) -> None:
        _identifier(self.activity_id, "activity_id")
        _identifier(self.work_package_id, "work_package_id")
        _identifier(self.trade_id, "trade_id")
        _finite(self.day, "activity.day")
        if self.status not in {item.value for item in ConstructionDemoWorkStatus}:
            raise ValueError("unsupported synthetic activity status")
        _text(self.note, "activity.note")
        if self.truth_class != ConstructionDemoRecordTruth.SYNTHETIC_DEMO_ACTIVITY.value:
            raise ValueError("activity truth_class must remain synthetic")
        _strict_boundary(self.person_level_data_included, "person_level_data_included", False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionDemoAlternative:
    alternative_id: str
    title: str
    source_work_package_id: str
    target_work_package_ids: tuple[str, ...]
    projected_time_delta_hours: float
    projected_cost_delta_cad: float
    projected_idle_delta_hours: float
    admissible: bool
    blocker_codes: tuple[str, ...] = ()
    recommended_for_human_review: bool = False
    truth_class: str = ConstructionDemoRecordTruth.SYNTHETIC_DEMO_PROPOSAL.value
    automatic_execution: bool = False

    def __post_init__(self) -> None:
        _identifier(self.alternative_id, "alternative_id")
        _text(self.title, "alternative.title")
        _identifier(self.source_work_package_id, "source_work_package_id")
        _ids(self.target_work_package_ids, "target_work_package_ids", allow_empty=False)
        _finite(self.projected_time_delta_hours, "projected_time_delta_hours")
        _finite(self.projected_cost_delta_cad, "projected_cost_delta_cad")
        _finite(self.projected_idle_delta_hours, "projected_idle_delta_hours")
        if type(self.admissible) is not bool:
            raise ValueError("alternative.admissible must be boolean")
        _ids(self.blocker_codes, "blocker_codes")
        if self.admissible and self.blocker_codes:
            raise ValueError("admissible alternative cannot retain blocker codes")
        if type(self.recommended_for_human_review) is not bool:
            raise ValueError("recommended_for_human_review must be boolean")
        if self.recommended_for_human_review and not self.admissible:
            raise ValueError("blocked alternative cannot be recommended")
        if self.truth_class != ConstructionDemoRecordTruth.SYNTHETIC_DEMO_PROPOSAL.value:
            raise ValueError("alternative truth_class must remain synthetic")
        _strict_boundary(self.automatic_execution, "automatic_execution", False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionDemoProjectFixture:
    asset_pack: ConstructionDemoAssetPack
    state: ConstructionProjectState
    focus_scope: ConstructionScope
    trades: tuple[ConstructionDemoTrade, ...]
    work_packages: tuple[ConstructionDemoWorkPackage, ...]
    budget_lines: tuple[ConstructionDemoBudgetLine, ...]
    rules: tuple[ConstructionDemoRule, ...]
    inspections: tuple[ConstructionDemoInspection, ...]
    hazards: tuple[ConstructionDemoHazard, ...]
    work_history: tuple[ConstructionDemoActivity, ...]
    alternatives: tuple[ConstructionDemoAlternative, ...]
    candidates: tuple[ConstructionCoordinationCandidate, ...]
    probabilistic_signals: tuple[ConstructionProbabilisticSignal, ...]
    blocked_clearance_claim_id: str
    fixture_digest: str = ""
    version: str = CONSTRUCTION_DEMO_FIXTURE_VERSION
    synthetic: bool = True
    private_data_used: bool = False
    production_connectors_used: bool = False
    project_state_owner: bool = False
    schedule_authority: bool = False
    financial_authority: bool = False
    regulatory_authority: bool = False
    physical_work_authority: bool = False
    automatic_execution: bool = False
    human_review_required: bool = True
    patch_authority: str = PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if type(self.asset_pack) is not ConstructionDemoAssetPack:
            raise ValueError("asset_pack must be an exact ConstructionDemoAssetPack")
        if type(self.state) is not ConstructionProjectState:
            raise ValueError("state must be an exact ConstructionProjectState")
        if type(self.focus_scope) is not ConstructionScope:
            raise ValueError("focus_scope must be an exact ConstructionScope")
        if self.focus_scope.project_id != self.state.project_id:
            raise ValueError("focus_scope and state project IDs differ")
        if self.version != CONSTRUCTION_DEMO_FIXTURE_VERSION:
            raise ValueError("unsupported Construction demo fixture version")
        self._validate_collections()
        self._validate_references()
        for name, expected in {
            "synthetic": True,
            "private_data_used": False,
            "production_connectors_used": False,
            "project_state_owner": False,
            "schedule_authority": False,
            "financial_authority": False,
            "regulatory_authority": False,
            "physical_work_authority": False,
            "automatic_execution": False,
            "human_review_required": True,
        }.items():
            _strict_boundary(getattr(self, name), name, expected)
        if self.patch_authority != PATCH_AUTHORITY:
            raise ValueError("fixture patch-authority boundary was modified")
        _identifier(self.blocked_clearance_claim_id, "blocked_clearance_claim_id")
        digest = stable_digest(self._body())
        if self.fixture_digest and self.fixture_digest != digest:
            raise ValueError("fixture_digest does not match fixture body")
        object.__setattr__(self, "fixture_digest", digest)

    def _validate_collections(self) -> None:
        typed = (
            ("trades", ConstructionDemoTrade, "trade_id"),
            ("work_packages", ConstructionDemoWorkPackage, "work_package_id"),
            ("budget_lines", ConstructionDemoBudgetLine, "budget_line_id"),
            ("rules", ConstructionDemoRule, "rule_id"),
            ("inspections", ConstructionDemoInspection, "inspection_id"),
            ("hazards", ConstructionDemoHazard, "hazard_id"),
            ("work_history", ConstructionDemoActivity, "activity_id"),
            ("alternatives", ConstructionDemoAlternative, "alternative_id"),
        )
        for field_name, expected_type, identity_field in typed:
            values = getattr(self, field_name)
            if type(values) is not tuple or not values or not all(type(item) is expected_type for item in values):
                raise ValueError(f"{field_name} must be a non-empty tuple of exact {expected_type.__name__} values")
            identities = tuple(getattr(item, identity_field) for item in values)
            if identities != tuple(sorted(set(identities))):
                raise ValueError(f"{field_name} must use canonical unique identity order")
        if (
            type(self.candidates) is not tuple
            or not self.candidates
            or not all(type(item) is ConstructionCoordinationCandidate for item in self.candidates)
        ):
            raise ValueError("candidates must contain exact ConstructionCoordinationCandidate values")
        if (
            type(self.probabilistic_signals) is not tuple
            or not self.probabilistic_signals
            or not all(type(item) is ConstructionProbabilisticSignal for item in self.probabilistic_signals)
        ):
            raise ValueError("probabilistic_signals must contain exact ConstructionProbabilisticSignal values")
        if {item.name for item in self.trades} != MINIMUM_TRADE_NAMES:
            raise ValueError("fixture must contain the complete minimum fictional trade set")
        statuses = {item.status for item in self.work_packages}
        if statuses != {item.value for item in ConstructionDemoWorkStatus}:
            raise ValueError("fixture must demonstrate every required work status")

    def _validate_references(self) -> None:
        storey_ids = {item.storey_id for item in self.asset_pack.storeys}
        trade_ids = {item.trade_id for item in self.trades}
        package_ids = {item.work_package_id for item in self.work_packages}
        budget_package_ids = {item.work_package_id for item in self.budget_lines}
        rule_ids = {item.rule_id for item in self.rules}
        inspection_ids = {item.inspection_id for item in self.inspections}
        hazard_ids = {item.hazard_id for item in self.hazards}
        for package in self.work_packages:
            if package.storey_id not in storey_ids:
                raise ValueError("work package references an unknown asset-pack storey")
            if package.trade_id not in trade_ids:
                raise ValueError("work package references an unknown trade")
            if not set(package.dependency_ids).issubset(package_ids):
                raise ValueError("work package references an unknown dependency")
            if not set(package.rule_ids).issubset(rule_ids):
                raise ValueError("work package references an unknown rule")
            if not set(package.inspection_ids).issubset(inspection_ids):
                raise ValueError("work package references an unknown inspection")
            if not set(package.hazard_ids).issubset(hazard_ids):
                raise ValueError("work package references an unknown hazard")
        if budget_package_ids != package_ids:
            raise ValueError("every work package must have exactly one budget line")
        if len(self.budget_lines) != len(package_ids):
            raise ValueError("work packages cannot have duplicate budget lines")
        if any(item.work_package_id not in package_ids for item in self.work_history):
            raise ValueError("work history references an unknown work package")
        if any(item.trade_id not in trade_ids for item in self.work_history):
            raise ValueError("work history references an unknown trade")
        for item in self.rules:
            if not set(item.applies_to_work_package_ids).issubset(package_ids):
                raise ValueError("synthetic rule references an unknown work package")
        for item in (*self.inspections, *self.hazards):
            if item.work_package_id not in package_ids:
                raise ValueError("fixture record references an unknown work package")
        for item in self.alternatives:
            if item.source_work_package_id not in package_ids or not set(item.target_work_package_ids).issubset(
                package_ids
            ):
                raise ValueError("alternative references an unknown work package")

    def _body(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "asset_pack_digest": self.asset_pack.asset_pack_digest,
            "state_digest": self.state.state_digest,
            "final_chain_digest": self.state.final_chain_digest,
            "focus_scope": self.focus_scope.to_dict(),
            "trades": [item.to_dict() for item in self.trades],
            "work_packages": [item.to_dict() for item in self.work_packages],
            "budget_lines": [item.to_dict() for item in self.budget_lines],
            "rules": [item.to_dict() for item in self.rules],
            "inspections": [item.to_dict() for item in self.inspections],
            "hazards": [item.to_dict() for item in self.hazards],
            "work_history": [item.to_dict() for item in self.work_history],
            "alternatives": [item.to_dict() for item in self.alternatives],
            "candidate_ids": [item.candidate_id for item in self.candidates],
            "probabilistic_signal_ids": [item.signal_id for item in self.probabilistic_signals],
            "blocked_clearance_claim_id": self.blocked_clearance_claim_id,
            "synthetic": self.synthetic,
            "private_data_used": self.private_data_used,
            "production_connectors_used": self.production_connectors_used,
            "project_state_owner": self.project_state_owner,
            "schedule_authority": self.schedule_authority,
            "financial_authority": self.financial_authority,
            "regulatory_authority": self.regulatory_authority,
            "physical_work_authority": self.physical_work_authority,
            "automatic_execution": self.automatic_execution,
            "human_review_required": self.human_review_required,
            "patch_authority": self.patch_authority,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._body(),
            "fixture_digest": self.fixture_digest,
            "asset_pack": self.asset_pack.to_dict(),
            "state": self.state.to_dict(),
            "candidates": [item.to_dict() for item in self.candidates],
            "probabilistic_signals": [item.to_dict() for item in self.probabilistic_signals],
        }


__all__ = [
    "CONSTRUCTION_DEMO_FIXTURE_VERSION",
    "MINIMUM_TRADE_NAMES",
    "ConstructionDemoActivity",
    "ConstructionDemoAlternative",
    "ConstructionDemoBudgetLine",
    "ConstructionDemoHazard",
    "ConstructionDemoInspection",
    "ConstructionDemoProjectFixture",
    "ConstructionDemoRecordTruth",
    "ConstructionDemoRule",
    "ConstructionDemoTrade",
    "ConstructionDemoWorkPackage",
    "ConstructionDemoWorkStatus",
]
