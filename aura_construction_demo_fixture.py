"""Asset-pack-bound synthetic fixture contracts for the Construction Arena demo.

This module composes the existing Construction truth owners.  It does not own
project, schedule, financial, regulatory, professional-release, renderer, or
physical-location truth.  Every value is fictional, proposal-only, and intended
only for deterministic software verification and presentation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from aura_construction_adapter import ConstructionCoordinationCandidate
from aura_construction_contracts import ConstructionClaim, ConstructionScope
from aura_construction_demo_contracts import ConstructionDemoAssetPack
from aura_construction_state import ConstructionProjectState
from aura_event_contracts import stable_digest

CONSTRUCTION_DEMO_FIXTURE_VERSION = "AURA_CONSTRUCTION_DEMO_FIXTURE_V1"
SYNTHETIC_RULE_TRUTH_CLASS = "SYNTHETIC_DEMO_RULE"
CONSTRUCTION_DEMO_WORK_STATES = frozenset(
    {
        "ACTIVE",
        "AWAITING_INSPECTION",
        "AWAITING_PROFESSIONAL_RELEASE",
        "BLOCKED",
        "COMPLETED",
        "DELAYED",
        "NOT_STARTED",
        "READY_FOR_REVIEW",
        "REWORK_REQUIRED",
    }
)
CONSTRUCTION_DEMO_REQUIRED_TRADES = frozenset(
    {
        "asbestos-abatement",
        "crane-logistics",
        "demolition",
        "electrical",
        "fire-protection",
        "general-contractor",
        "inspection",
        "mechanical",
        "plumbing",
        "roofing",
        "structural",
        "temporary-labour",
    }
)


def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value or value != " ".join(value.split()):
        raise ValueError(f"{name} must be normalized non-empty text")
    return value


def _identifier(value: Any, name: str) -> str:
    text = _text(value, name)
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-._:" for character in text):
        raise ValueError(f"{name} must be a lowercase canonical identifier")
    return text


def _tuple_text(value: Any, name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    normalized = tuple(_text(item, f"{name}[]") for item in value)
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must not be empty")
    if normalized != tuple(sorted(set(normalized))):
        raise ValueError(f"{name} must be sorted and unique")
    return normalized


def _finite(value: Any, name: str, *, minimum: float | None = None) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or (minimum is not None and number < minimum):
        raise ValueError(f"{name} must be finite and at least {minimum}")
    return number


@dataclass(frozen=True)
class ConstructionDemoTrade:
    trade_id: str
    subcontractor_id: str
    label: str
    synthetic: bool = True
    person_level_data_included: bool = False

    def __post_init__(self) -> None:
        _identifier(self.trade_id, "trade_id")
        _identifier(self.subcontractor_id, "subcontractor_id")
        _text(self.label, "label")
        if self.synthetic is not True or self.person_level_data_included is not False:
            raise ValueError("trade crossed the synthetic privacy boundary")


@dataclass(frozen=True)
class ConstructionDemoWorkPackage:
    package_id: str
    scope: ConstructionScope
    trade_id: str
    title: str
    status: str
    dependency_package_ids: tuple[str, ...]
    required_evidence_label: str
    inspection_required: bool
    professional_release_required: bool
    crane_window_required: bool
    alternative_package_ids: tuple[str, ...]
    base_geometry_mutated: bool = False
    physical_work_authorized: bool = False

    def __post_init__(self) -> None:
        _identifier(self.package_id, "package_id")
        if type(self.scope) is not ConstructionScope:
            raise ValueError("scope must be an exact ConstructionScope")
        _identifier(self.trade_id, "trade_id")
        _text(self.title, "title")
        if self.status not in CONSTRUCTION_DEMO_WORK_STATES:
            raise ValueError("status is not a supported demo work state")
        _tuple_text(self.dependency_package_ids, "dependency_package_ids")
        _text(self.required_evidence_label, "required_evidence_label")
        _tuple_text(self.alternative_package_ids, "alternative_package_ids")
        for name in (
            "inspection_required",
            "professional_release_required",
            "crane_window_required",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if self.base_geometry_mutated is not False or self.physical_work_authorized is not False:
            raise ValueError("work package crossed its projection-only authority boundary")


@dataclass(frozen=True)
class ConstructionDemoTimelineEntry:
    timeline_id: str
    package_id: str
    start_hour: float
    end_hour: float
    status: str

    def __post_init__(self) -> None:
        _identifier(self.timeline_id, "timeline_id")
        _identifier(self.package_id, "package_id")
        start = _finite(self.start_hour, "start_hour", minimum=0.0)
        end = _finite(self.end_hour, "end_hour", minimum=0.0)
        if end <= start:
            raise ValueError("timeline end_hour must follow start_hour")
        if self.status not in CONSTRUCTION_DEMO_WORK_STATES:
            raise ValueError("timeline status is unsupported")


@dataclass(frozen=True)
class ConstructionDemoBudgetLine:
    budget_line_id: str
    package_id: str
    baseline_cad: float
    projected_cad: float
    currency: str = "CAD"
    synthetic_projection: bool = True
    payment_released: bool = False

    def __post_init__(self) -> None:
        _identifier(self.budget_line_id, "budget_line_id")
        _identifier(self.package_id, "package_id")
        _finite(self.baseline_cad, "baseline_cad", minimum=0.0)
        _finite(self.projected_cad, "projected_cad", minimum=0.0)
        if self.currency != "CAD":
            raise ValueError("demo budget currency must be CAD")
        if self.synthetic_projection is not True or self.payment_released is not False:
            raise ValueError("budget line crossed its synthetic financial boundary")


@dataclass(frozen=True)
class ConstructionDemoRule:
    rule_id: str
    label: str
    package_ids: tuple[str, ...]
    truth_class: str = SYNTHETIC_RULE_TRUTH_CLASS
    legal_authority: bool = False
    regulatory_authority: bool = False
    jurisdiction_claimed: str = "none"

    def __post_init__(self) -> None:
        _identifier(self.rule_id, "rule_id")
        _text(self.label, "label")
        _tuple_text(self.package_ids, "package_ids", allow_empty=False)
        if self.truth_class != SYNTHETIC_RULE_TRUTH_CLASS:
            raise ValueError("rule must be labelled SYNTHETIC_DEMO_RULE")
        if self.legal_authority is not False or self.regulatory_authority is not False:
            raise ValueError("synthetic rule cannot claim legal or regulatory authority")
        if self.jurisdiction_claimed != "none":
            raise ValueError("synthetic rule cannot claim a jurisdiction")


@dataclass(frozen=True)
class ConstructionDemoProjectFixture:
    asset_pack: ConstructionDemoAssetPack
    state: ConstructionProjectState
    trades: tuple[ConstructionDemoTrade, ...]
    work_packages: tuple[ConstructionDemoWorkPackage, ...]
    timeline: tuple[ConstructionDemoTimelineEntry, ...]
    budget_lines: tuple[ConstructionDemoBudgetLine, ...]
    rules: tuple[ConstructionDemoRule, ...]
    claims: tuple[ConstructionClaim, ...]
    candidates: tuple[ConstructionCoordinationCandidate, ...]
    blocked_package_id: str
    recommended_candidate_id: str
    fixture_digest: str = ""
    version: str = CONSTRUCTION_DEMO_FIXTURE_VERSION
    synthetic: bool = True
    proposal_only: bool = True
    project_state_owner: bool = False
    schedule_truth_owner: bool = False
    financial_truth_owner: bool = False
    regulatory_truth_owner: bool = False
    renderer_authority: bool = False
    production_mutation: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if type(self.asset_pack) is not ConstructionDemoAssetPack:
            raise ValueError("asset_pack must be an exact ConstructionDemoAssetPack")
        if type(self.state) is not ConstructionProjectState:
            raise ValueError("state must be an exact ConstructionProjectState")
        if self.state.project_id != self.asset_pack.building_id:
            raise ValueError("fixture state project must match asset-pack building_id")
        typed_sequences = (
            (self.trades, ConstructionDemoTrade, "trades"),
            (self.work_packages, ConstructionDemoWorkPackage, "work_packages"),
            (self.timeline, ConstructionDemoTimelineEntry, "timeline"),
            (self.budget_lines, ConstructionDemoBudgetLine, "budget_lines"),
            (self.rules, ConstructionDemoRule, "rules"),
            (self.claims, ConstructionClaim, "claims"),
            (self.candidates, ConstructionCoordinationCandidate, "candidates"),
        )
        for values, expected_type, name in typed_sequences:
            if type(values) is not tuple or not values or not all(type(item) is expected_type for item in values):
                raise ValueError(f"{name} must be a non-empty tuple of exact {expected_type.__name__} values")
        trade_ids = {item.trade_id for item in self.trades}
        if not CONSTRUCTION_DEMO_REQUIRED_TRADES.issubset(trade_ids):
            raise ValueError("fixture does not include every required fictional trade")
        package_ids = {item.package_id for item in self.work_packages}
        storey_ids = {item.storey_id for item in self.asset_pack.storeys}
        if self.blocked_package_id not in package_ids:
            raise ValueError("blocked_package_id is unknown")
        if self.recommended_candidate_id not in {item.candidate_id for item in self.candidates}:
            raise ValueError("recommended_candidate_id is unknown")
        for package in self.work_packages:
            if package.trade_id not in trade_ids:
                raise ValueError("work package references an unknown trade")
            if package.scope.project_id != self.asset_pack.building_id or package.scope.zone_id not in storey_ids:
                raise ValueError("work package is not bound to a discovered asset-pack storey")
            if not set(package.dependency_package_ids).issubset(package_ids):
                raise ValueError("work package has an unknown dependency")
            if not set(package.alternative_package_ids).issubset(package_ids):
                raise ValueError("work package has an unknown alternative")
        if any(item.package_id not in package_ids for item in self.timeline):
            raise ValueError("timeline references an unknown work package")
        if any(item.package_id not in package_ids for item in self.budget_lines):
            raise ValueError("budget references an unknown work package")
        if any(not set(item.package_ids).issubset(package_ids) for item in self.rules):
            raise ValueError("synthetic rule references an unknown work package")
        for name, expected in {
            "synthetic": True,
            "proposal_only": True,
            "project_state_owner": False,
            "schedule_truth_owner": False,
            "financial_truth_owner": False,
            "regulatory_truth_owner": False,
            "renderer_authority": False,
            "production_mutation": False,
            "human_review_required": True,
        }.items():
            if getattr(self, name) is not expected:
                raise ValueError(f"fixture authority boundary changed: {name}")
        if self.version != CONSTRUCTION_DEMO_FIXTURE_VERSION:
            raise ValueError("unsupported Construction demo fixture version")
        expected_digest = stable_digest(self._identity_body())
        if self.fixture_digest and self.fixture_digest != expected_digest:
            raise ValueError("fixture_digest does not match fixture content")
        object.__setattr__(self, "fixture_digest", expected_digest)

    def _identity_body(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "asset_pack_digest": self.asset_pack.asset_pack_digest,
            "state_digest": self.state.state_digest,
            "trades": [asdict(item) for item in self.trades],
            "work_packages": [asdict(item) for item in self.work_packages],
            "timeline": [asdict(item) for item in self.timeline],
            "budget_lines": [asdict(item) for item in self.budget_lines],
            "rules": [asdict(item) for item in self.rules],
            "claim_ids": [item.claim_id for item in self.claims],
            "candidate_ids": [item.candidate_id for item in self.candidates],
            "blocked_package_id": self.blocked_package_id,
            "recommended_candidate_id": self.recommended_candidate_id,
            "synthetic": self.synthetic,
            "proposal_only": self.proposal_only,
            "project_state_owner": self.project_state_owner,
            "schedule_truth_owner": self.schedule_truth_owner,
            "financial_truth_owner": self.financial_truth_owner,
            "regulatory_truth_owner": self.regulatory_truth_owner,
            "renderer_authority": self.renderer_authority,
            "production_mutation": self.production_mutation,
            "human_review_required": self.human_review_required,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_body(), "fixture_digest": self.fixture_digest}


__all__ = [
    "CONSTRUCTION_DEMO_FIXTURE_VERSION",
    "CONSTRUCTION_DEMO_REQUIRED_TRADES",
    "CONSTRUCTION_DEMO_WORK_STATES",
    "SYNTHETIC_RULE_TRUTH_CLASS",
    "ConstructionDemoBudgetLine",
    "ConstructionDemoProjectFixture",
    "ConstructionDemoRule",
    "ConstructionDemoTimelineEntry",
    "ConstructionDemoTrade",
    "ConstructionDemoWorkPackage",
]
