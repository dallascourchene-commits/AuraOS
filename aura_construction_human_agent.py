"""Read-only Human Agent and Observatory profile for SCO Construction.

The profile consumes exact Construction state and a verified proposal-only
coordination evaluation. It exposes purpose-limited candidate summaries for
human review without copying raw evidence, mutating project records, granting
physical authority, or adding a second Construction truth store.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from aura_construction_adapter import (
    ConstructionArenaMode,
    ConstructionCoordinationCandidate,
    ConstructionCoordinationEvaluation,
    evaluate_construction_candidates,
)
from aura_construction_contracts import PATCH_AUTHORITY, PROPOSAL_ONLY, VSA_PATCH_AUTHORITY
from aura_construction_fixtures import ConstructionDemoFixture, build_sco_construction_demo_fixture
from aura_construction_state import ConstructionProjectState
from aura_event_contracts import stable_digest, stable_id

CONSTRUCTION_HUMAN_AGENT_VERSION = "AURA_SCO_CONSTRUCTION_HUMAN_AGENT_V1"
CONSTRUCTION_OBSERVATORY_VERSION = "AURA_SCO_CONSTRUCTION_OBSERVATORY_V1"
_ALLOWED_HANDOFF_ARENAS = frozenset(
    {
        "coding_arena",
        "coding_workbench",
        "human_agent_arena",
        "agent_bridge_arena",
        "construction_arena",
    }
)


def _text(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    normalized = " ".join(value.split())
    if not normalized and not allow_empty:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _strings(values: Iterable[Any], name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be an iterable of strings")
    materialized = tuple(sorted({_text(item, f"{name}[]") for item in values}))
    return materialized


@dataclass(frozen=True)
class ConstructionHumanAgentCandidate:
    candidate_id: str
    title: str
    summary: str
    lane: str
    authority_route: str
    admissible: bool
    blockers: tuple[str, ...]
    balanced_score: float
    projected_time_delta_hours: float
    projected_cost_delta_cad: float
    projected_idle_delta_hours: float
    measurement_class: str
    recommended: bool
    option_role: str
    proposal_only: bool = PROPOSAL_ONLY
    human_review_required: bool = True
    physical_work_authorized: bool = False
    payment_released: bool = False
    access_controlled: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "candidate_id",
            "title",
            "summary",
            "lane",
            "authority_route",
            "measurement_class",
        ):
            if getattr(self, field_name) != _text(getattr(self, field_name), field_name):
                raise ValueError(f"{field_name} must be canonical text")
        if self.option_role != _text(self.option_role, "option_role", allow_empty=True):
            raise ValueError("option_role must be canonical text")
        if self.blockers != _strings(self.blockers, "blockers"):
            raise ValueError("blockers must be canonical and unique")
        if type(self.admissible) is not bool or self.admissible == bool(self.blockers):
            raise ValueError("candidate admissibility and blockers disagree")
        if type(self.recommended) is not bool:
            raise ValueError("recommended must be boolean")
        if self.recommended and not self.admissible:
            raise ValueError("blocked candidate cannot be recommended")
        for field_name in (
            "balanced_score",
            "projected_time_delta_hours",
            "projected_cost_delta_cad",
            "projected_idle_delta_hours",
        ):
            if type(getattr(self, field_name)) is not float:
                raise ValueError(f"{field_name} must be a canonical float")
        if not 0.0 <= self.balanced_score <= 1.0:
            raise ValueError("balanced_score must be between zero and one")
        if (
            self.proposal_only is not True
            or self.human_review_required is not True
            or self.physical_work_authorized is not False
            or self.payment_released is not False
            or self.access_controlled is not False
        ):
            raise ValueError("candidate view crossed the Human Agent authority boundary")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["blockers"] = list(self.blockers)
        return value


@dataclass(frozen=True)
class ConstructionHumanAgentProfile:
    profile_id: str
    profile_digest: str
    project_id: str
    ledger_id: str
    state_digest: str
    event_chain_digest: str
    evaluation_id: str
    evaluation_digest: str
    mode: str
    lane: str
    route_class: str
    evaluated_at: float
    recommended_candidate_id: str
    option_candidate_ids: tuple[str, ...]
    next_authority_route: str
    candidates: tuple[ConstructionHumanAgentCandidate, ...]
    checkpoint_id: str
    version: str = CONSTRUCTION_HUMAN_AGENT_VERSION
    synthetic: bool = False
    read_only: bool = True
    proposal_only: bool = PROPOSAL_ONLY
    raw_records_included: bool = False
    human_review_required: bool = True
    physical_work_authorized: bool = False
    payment_released: bool = False
    access_controlled: bool = False
    professional_certification_authorized: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_HUMAN_AGENT_VERSION:
            raise ValueError("unsupported Construction Human Agent profile version")
        for field_name in (
            "project_id",
            "ledger_id",
            "state_digest",
            "event_chain_digest",
            "evaluation_id",
            "evaluation_digest",
            "mode",
            "lane",
            "route_class",
        ):
            if getattr(self, field_name) != _text(getattr(self, field_name), field_name):
                raise ValueError(f"{field_name} must be canonical text")
        for field_name in (
            "recommended_candidate_id",
            "next_authority_route",
            "checkpoint_id",
        ):
            if getattr(self, field_name) != _text(
                getattr(self, field_name), field_name, allow_empty=True
            ):
                raise ValueError(f"{field_name} must be canonical text")
        if type(self.evaluated_at) is not float:
            raise ValueError("evaluated_at must be a canonical float")
        if type(self.candidates) is not tuple or not all(
            type(item) is ConstructionHumanAgentCandidate for item in self.candidates
        ):
            raise ValueError("candidates must contain exact Human Agent candidate views")
        candidate_ids = tuple(item.candidate_id for item in self.candidates)
        if candidate_ids != tuple(sorted(candidate_ids)) or len(candidate_ids) != len(
            set(candidate_ids)
        ):
            raise ValueError("candidate views must use unique canonical order")
        if type(self.option_candidate_ids) is not tuple:
            raise ValueError("option_candidate_ids must be a tuple")
        if len(self.option_candidate_ids) != len(set(self.option_candidate_ids)):
            raise ValueError("option_candidate_ids must be unique")
        if not set(self.option_candidate_ids).issubset(candidate_ids):
            raise ValueError("option_candidate_ids reference unknown candidates")
        if self.recommended_candidate_id and self.recommended_candidate_id not in candidate_ids:
            raise ValueError("recommended candidate is missing from the profile")
        if bool(self.recommended_candidate_id) != bool(self.next_authority_route):
            raise ValueError("recommendation and authority route must be paired")
        recommended = [item for item in self.candidates if item.recommended]
        if len(recommended) != (1 if self.recommended_candidate_id else 0):
            raise ValueError("profile recommendation markers disagree")
        if recommended and recommended[0].candidate_id != self.recommended_candidate_id:
            raise ValueError("profile recommendation identity disagrees")
        if (
            self.read_only is not True
            or self.proposal_only is not True
            or self.raw_records_included is not False
            or self.human_review_required is not True
            or self.physical_work_authorized is not False
            or self.payment_released is not False
            or self.access_controlled is not False
            or self.professional_certification_authorized is not False
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
        ):
            raise ValueError("Human Agent profile crossed its authority boundary")
        payload = self._identity_payload()
        if self.profile_digest != stable_digest(payload):
            raise ValueError("profile digest does not match its content")
        if self.profile_id != stable_id("construction-human-agent-profile", payload):
            raise ValueError("profile ID does not match its content")

    def _identity_payload(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("profile_id")
        value.pop("profile_digest")
        return value

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["option_candidate_ids"] = list(self.option_candidate_ids)
        value["candidates"] = [item.to_dict() for item in self.candidates]
        value["allowed_human_actions"] = [
            "inspect proposal evidence references",
            "request missing or fresher evidence",
            "prepare a review-gated checkpoint",
            "prepare a payload-free cross-arena handoff",
            "record an external human decision in the authoritative owner workflow",
        ]
        value["forbidden_actions"] = [
            "authorize physical work",
            "release payment or transfer funds",
            "control physical access or equipment",
            "certify safety engineering legal or regulatory status",
            "mutate authoritative Construction records",
            "let model or sensor scores override hard blockers",
        ]
        return value

    def observatory_projection(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": CONSTRUCTION_OBSERVATORY_VERSION,
            "profile_id": self.profile_id,
            "profile_digest": self.profile_digest,
            "project_id": self.project_id,
            "state_digest": self.state_digest,
            "event_chain_digest": self.event_chain_digest,
            "evaluation_id": self.evaluation_id,
            "evaluation_digest": self.evaluation_digest,
            "mode": self.mode,
            "lane": self.lane,
            "route_class": self.route_class,
            "evaluated_at": self.evaluated_at,
            "recommended_candidate_id": self.recommended_candidate_id,
            "next_authority_route": self.next_authority_route,
            "candidate_statuses": [
                {
                    "candidate_id": item.candidate_id,
                    "admissible": item.admissible,
                    "recommended": item.recommended,
                    "blocker_count": len(item.blockers),
                }
                for item in self.candidates
            ],
            "option_candidate_ids": list(self.option_candidate_ids),
            "checkpoint_id": self.checkpoint_id,
            "payload_included": False,
            "raw_records_included": False,
            "candidate_narratives_included": False,
            "execution_methods": [],
            "read_only": True,
            "proposal_only": True,
            "human_review_required": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "professional_certification_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def handoff_packet(self, target_arena_id: str) -> dict[str, Any]:
        target = _text(target_arena_id, "target_arena_id")
        if target not in _ALLOWED_HANDOFF_ARENAS:
            raise ValueError(f"unsupported target arena: {target}")
        return {
            "ok": True,
            "version": CONSTRUCTION_HUMAN_AGENT_VERSION,
            "source_arena_id": "construction_arena",
            "target_arena_id": target,
            "profile_id": self.profile_id,
            "profile_digest": self.profile_digest,
            "project_id": self.project_id,
            "state_digest": self.state_digest,
            "evaluation_digest": self.evaluation_digest,
            "checkpoint_id": self.checkpoint_id,
            "payload_included": False,
            "raw_records_included": False,
            "target_arena_mutated": False,
            "digital_baton_only": True,
            "human_review_required": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def build_construction_human_agent_profile(
    state: ConstructionProjectState,
    evaluation: ConstructionCoordinationEvaluation,
    *,
    candidates: Iterable[ConstructionCoordinationCandidate],
    checkpoint_id: str = "",
    synthetic: bool = False,
) -> ConstructionHumanAgentProfile:
    """Build a purpose-limited review profile from exact verified owners."""
    if type(state) is not ConstructionProjectState:
        raise ValueError("state must be an exact ConstructionProjectState")
    if type(evaluation) is not ConstructionCoordinationEvaluation:
        raise ValueError("evaluation must be an exact ConstructionCoordinationEvaluation")
    state.__post_init__()
    evaluation.__post_init__()
    if evaluation.state_digest != state.state_digest:
        raise ValueError("evaluation does not bind the supplied Construction state")
    candidate_items = tuple(candidates)
    if not candidate_items or not all(
        type(item) is ConstructionCoordinationCandidate for item in candidate_items
    ):
        raise ValueError("candidates must contain exact Construction candidates")
    candidate_by_id = {item.candidate_id: item for item in candidate_items}
    if len(candidate_by_id) != len(candidate_items):
        raise ValueError("candidate IDs must be unique")
    assessments = {item.candidate_id: item for item in evaluation.assessments}
    if set(assessments) != set(candidate_by_id):
        raise ValueError("evaluation and candidate identities do not match")
    role_by_id = {
        candidate_id: f"OPTION_{index + 1}"
        for index, candidate_id in enumerate(evaluation.option_candidate_ids)
    }
    views: list[ConstructionHumanAgentCandidate] = []
    for candidate_id in sorted(candidate_by_id):
        candidate = candidate_by_id[candidate_id]
        assessment = assessments[candidate_id]
        views.append(
            ConstructionHumanAgentCandidate(
                candidate_id=candidate_id,
                title=candidate.title,
                summary=candidate.summary,
                lane=candidate.lane,
                authority_route=candidate.authority_route,
                admissible=assessment.admissible,
                blockers=assessment.blockers,
                balanced_score=float(assessment.balanced_score),
                projected_time_delta_hours=float(candidate.projected_time_delta_hours),
                projected_cost_delta_cad=float(candidate.projected_cost_delta_cad),
                projected_idle_delta_hours=float(candidate.projected_idle_delta_hours),
                measurement_class=candidate.measurement_class,
                recommended=candidate_id == evaluation.recommended_candidate_id,
                option_role=role_by_id.get(candidate_id, ""),
            )
        )
    values = {
        "project_id": state.project_id,
        "ledger_id": state.ledger_id,
        "state_digest": state.state_digest,
        "event_chain_digest": state.final_chain_digest,
        "evaluation_id": evaluation.evaluation_id,
        "evaluation_digest": evaluation.evaluation_digest,
        "mode": evaluation.mode,
        "lane": evaluation.lane,
        "route_class": evaluation.route_class,
        "evaluated_at": float(evaluation.evaluated_at),
        "recommended_candidate_id": evaluation.recommended_candidate_id,
        "option_candidate_ids": tuple(evaluation.option_candidate_ids),
        "next_authority_route": evaluation.next_authority_route,
        "candidates": tuple(views),
        "checkpoint_id": _text(checkpoint_id, "checkpoint_id", allow_empty=True),
        "version": CONSTRUCTION_HUMAN_AGENT_VERSION,
        "synthetic": bool(synthetic),
        "read_only": True,
        "proposal_only": PROPOSAL_ONLY,
        "raw_records_included": False,
        "human_review_required": True,
        "physical_work_authorized": False,
        "payment_released": False,
        "access_controlled": False,
        "professional_certification_authorized": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    identity = {
        **values,
        "candidates": [item.to_dict() for item in values["candidates"]],
        "option_candidate_ids": list(values["option_candidate_ids"]),
    }
    return ConstructionHumanAgentProfile(
        profile_id=stable_id("construction-human-agent-profile", identity),
        profile_digest=stable_digest(identity),
        **values,
    )


class ConstructionHumanAgentProfileService:
    """Local read-only service for the Human Agent Construction surface."""

    def __init__(self, *, demo: bool = False) -> None:
        self.demo = bool(demo)
        self.fixture: ConstructionDemoFixture | None = None
        self.state: ConstructionProjectState | None = None
        self.evaluation: ConstructionCoordinationEvaluation | None = None
        self.profile: ConstructionHumanAgentProfile | None = None
        if self.demo:
            self.load_demo()

    def load_demo(self) -> ConstructionHumanAgentProfile:
        fixture = build_sco_construction_demo_fixture()
        evaluation = evaluate_construction_candidates(
            fixture.state,
            candidates=fixture.candidates,
            now=20.0,
            mode=ConstructionArenaMode.SYNTHETIC,
            lane=fixture.candidates[0].lane,
            probabilistic_signals=fixture.probabilistic_signals,
        )
        profile = build_construction_human_agent_profile(
            fixture.state,
            evaluation,
            candidates=fixture.candidates,
            synthetic=True,
        )
        self.fixture = fixture
        self.state = fixture.state
        self.evaluation = evaluation
        self.profile = profile
        return profile

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": CONSTRUCTION_HUMAN_AGENT_VERSION,
            "available": self.profile is not None,
            "demo": self.demo,
            "project_id": self.profile.project_id if self.profile else "",
            "profile_id": self.profile.profile_id if self.profile else "",
            "read_only": True,
            "proposal_only": True,
            "human_review_required": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def get_profile(self) -> dict[str, Any]:
        if self.profile is None:
            raise KeyError("Construction Human Agent profile is unavailable")
        return {"ok": True, "profile": self.profile.to_dict()}

    def get_observatory_projection(self) -> dict[str, Any]:
        if self.profile is None:
            raise KeyError("Construction Human Agent profile is unavailable")
        return self.profile.observatory_projection()

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        if self.profile is None:
            raise KeyError("Construction Human Agent profile is unavailable")
        identifier = _text(candidate_id, "candidate_id")
        candidate = next(
            (item for item in self.profile.candidates if item.candidate_id == identifier),
            None,
        )
        if candidate is None:
            raise KeyError(f"Construction candidate not found: {identifier}")
        return {
            "ok": True,
            "candidate": candidate.to_dict(),
            "state_digest": self.profile.state_digest,
            "evaluation_digest": self.profile.evaluation_digest,
            "raw_records_included": False,
            "human_review_required": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def prepare_handoff(self, target_arena_id: str) -> dict[str, Any]:
        if self.profile is None:
            raise KeyError("Construction Human Agent profile is unavailable")
        return self.profile.handoff_packet(target_arena_id)


__all__ = [
    "CONSTRUCTION_HUMAN_AGENT_VERSION",
    "CONSTRUCTION_OBSERVATORY_VERSION",
    "ConstructionHumanAgentCandidate",
    "ConstructionHumanAgentProfile",
    "ConstructionHumanAgentProfileService",
    "build_construction_human_agent_profile",
]
