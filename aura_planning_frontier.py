"""Forward symbolic replay for Planning Board regression candidates.

P2.3 establishes a narrow bidirectional convergence boundary: P2.2 proposes
candidate paths by backward regression, and this module replays those paths
forward over public symbolic state. It never executes actions, invokes tools,
grants authority, or waives continuity and verification requirements.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import json
from typing import Any

from aura_event_contracts import canonical_json, stable_digest
from aura_planning_board import ActionSpec, PlanningBoard, PredicateSpec
from aura_planning_regression import (
    RegressionCandidate,
    RegressionReport,
    predicate_satisfied,
)

FRONTIER_VERSION = "AURA_PLANNING_FRONTIER_V1"


class ReplayFindingCode(str, Enum):
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    PRECONDITION_UNSATISFIED = "PRECONDITION_UNSATISFIED"
    AMBIGUOUS_EFFECT = "AMBIGUOUS_EFFECT"
    GOAL_UNSATISFIED = "GOAL_UNSATISFIED"


class CanonicalRecord:
    def to_dict(self) -> dict[str, Any]:
        return json.loads(canonical_json(self))


@dataclass(frozen=True)
class ReplayFinding(CanonicalRecord):
    code: ReplayFindingCode | str
    message: str
    action_id: str | None = None
    predicates: tuple[PredicateSpec, ...] = ()

    def __post_init__(self) -> None:
        try:
            code = self.code if isinstance(self.code, ReplayFindingCode) else ReplayFindingCode(str(self.code))
        except ValueError as exc:
            raise ValueError(f"unknown replay finding code: {self.code}") from exc
        message = str(self.message or "").strip()
        if not message:
            raise ValueError("replay finding message must not be empty")
        action_id = None if self.action_id is None else str(self.action_id or "").strip()
        if self.action_id is not None and not action_id:
            raise ValueError("replay finding action_id must not be empty")
        if isinstance(self.predicates, (str, bytes, bytearray)):
            raise ValueError("replay finding predicates must be a sequence")
        predicates = tuple(self.predicates)
        if not all(isinstance(item, PredicateSpec) for item in predicates):
            raise ValueError("replay finding predicates contains an invalid value")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "action_id", action_id)
        object.__setattr__(self, "predicates", predicates)


@dataclass(frozen=True)
class CandidateConvergence(CanonicalRecord):
    """Forward assessment of one backward candidate; never an execution grant."""

    action_ids: tuple[str, ...]
    applied_action_ids: tuple[str, ...]
    converged: bool
    final_state_digest: str
    findings: tuple[ReplayFinding, ...] = ()
    proposal_only: bool = True

    def __post_init__(self) -> None:
        for field_name in ("action_ids", "applied_action_ids"):
            values = getattr(self, field_name)
            if isinstance(values, (str, bytes, bytearray)):
                raise ValueError(f"candidate convergence {field_name} must be a sequence")
            normalized = tuple(str(item or "").strip() for item in values)
            if any(not item for item in normalized):
                raise ValueError(f"candidate convergence {field_name} contains an empty value")
            if len(normalized) != len(set(normalized)):
                raise ValueError(f"candidate convergence {field_name} must not contain duplicates")
            object.__setattr__(self, field_name, normalized)
        if self.applied_action_ids != self.action_ids[: len(self.applied_action_ids)]:
            raise ValueError("applied_action_ids must be an exact prefix of action_ids")
        if type(self.converged) is not bool:
            raise ValueError("candidate convergence converged must be a boolean")
        digest = str(self.final_state_digest or "").strip()
        if not digest:
            raise ValueError("candidate convergence final_state_digest must not be empty")
        object.__setattr__(self, "final_state_digest", digest)
        if isinstance(self.findings, (str, bytes, bytearray)):
            raise ValueError("candidate convergence findings must be a sequence")
        findings = tuple(self.findings)
        if not all(isinstance(item, ReplayFinding) for item in findings):
            raise ValueError("candidate convergence findings contains an invalid value")
        if self.converged and findings:
            raise ValueError("converged candidates must not contain findings")
        if not self.converged and not findings:
            raise ValueError("non-converged candidates require at least one finding")
        if type(self.proposal_only) is not bool:
            raise ValueError("candidate convergence proposal_only must be a boolean")
        if self.proposal_only is not True:
            raise ValueError("candidate convergence must remain proposal_only")
        object.__setattr__(self, "findings", findings)


@dataclass(frozen=True)
class FrontierConvergenceReport(CanonicalRecord):
    board_id: str
    board_digest: str
    state_digest: str
    regression_report_digest: str
    assessments: tuple[CandidateConvergence, ...]
    ignored_incomplete_candidates: int
    version: str = FRONTIER_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "board_id",
            "board_digest",
            "state_digest",
            "regression_report_digest",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"frontier report {field_name} must not be empty")
            object.__setattr__(self, field_name, value)
        if isinstance(self.assessments, (str, bytes, bytearray)):
            raise ValueError("frontier report assessments must be a sequence")
        assessments = tuple(self.assessments)
        if not all(isinstance(item, CandidateConvergence) for item in assessments):
            raise ValueError("frontier report assessments contains an invalid value")
        action_paths = [item.action_ids for item in assessments]
        if len(action_paths) != len(set(action_paths)):
            raise ValueError("frontier report assessments must have unique action paths")
        if type(self.ignored_incomplete_candidates) is not int or self.ignored_incomplete_candidates < 0:
            raise ValueError("ignored_incomplete_candidates must be a non-negative integer")
        if self.version != FRONTIER_VERSION:
            raise ValueError(f"unsupported frontier version: {self.version}")
        object.__setattr__(self, "assessments", assessments)

    @property
    def converged_candidates(self) -> tuple[CandidateConvergence, ...]:
        return tuple(item for item in self.assessments if item.converged)

    @property
    def convergence_complete(self) -> bool:
        """All complete backward candidates replayed; this is not authority."""

        return bool(self.assessments) and len(self.converged_candidates) == len(self.assessments)

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        value = super().to_dict()
        value["convergence_complete"] = self.convergence_complete
        value["converged_action_paths"] = [
            list(item.action_ids) for item in self.converged_candidates
        ]
        return value


def _open_predicates(
    predicates: Sequence[PredicateSpec],
    state: Mapping[str, Any],
) -> tuple[PredicateSpec, ...]:
    return tuple(
        sorted(
            (item for item in predicates if not predicate_satisfied(item, state)),
            key=canonical_json,
        )
    )


def _deterministic_effects(action: ActionSpec) -> dict[str, Any] | None:
    effects: dict[str, list[Any]] = {}
    for effect in action.effects:
        effects.setdefault(effect.fact, []).append(effect.value)
    normalized: dict[str, Any] = {}
    for fact in sorted(effects):
        values = effects[fact]
        canonical_values = {canonical_json(value) for value in values}
        if len(canonical_values) != 1:
            return None
        normalized[fact] = values[0]
    return normalized


def _validate_bindings(
    board: PlanningBoard,
    initial_state: Mapping[str, Any],
    regression_report: RegressionReport,
) -> str:
    if not isinstance(board, PlanningBoard):
        raise ValueError("board must be a PlanningBoard")
    if not isinstance(initial_state, Mapping):
        raise ValueError("initial_state must be a mapping")
    if not isinstance(regression_report, RegressionReport):
        raise ValueError("regression_report must be a RegressionReport")
    canonical_json(initial_state)
    state_digest = stable_digest(initial_state)
    if regression_report.board_id != board.board_id:
        raise ValueError("regression report board_id does not match the Planning Board")
    if regression_report.board_digest != board.digest:
        raise ValueError("regression report board_digest does not match the Planning Board")
    if regression_report.state_digest != state_digest:
        raise ValueError("regression report state_digest does not match initial_state")
    return state_digest


def _replay_candidate(
    board: PlanningBoard,
    initial_state: Mapping[str, Any],
    candidate: RegressionCandidate,
) -> CandidateConvergence:
    action_by_id = {action.action_id: action for action in board.actions}
    state = dict(initial_state)
    applied: list[str] = []

    for action_id in candidate.action_ids:
        action = action_by_id.get(action_id)
        if action is None:
            return CandidateConvergence(
                candidate.action_ids,
                tuple(applied),
                False,
                stable_digest(state),
                findings=(
                    ReplayFinding(
                        ReplayFindingCode.UNKNOWN_ACTION,
                        f"candidate references unknown action '{action_id}'",
                        action_id=action_id,
                    ),
                ),
            )
        unresolved = _open_predicates(action.preconditions, state)
        if unresolved:
            return CandidateConvergence(
                candidate.action_ids,
                tuple(applied),
                False,
                stable_digest(state),
                findings=(
                    ReplayFinding(
                        ReplayFindingCode.PRECONDITION_UNSATISFIED,
                        "action preconditions are not satisfied by the evolving symbolic state",
                        action_id=action_id,
                        predicates=unresolved,
                    ),
                ),
            )
        effects = _deterministic_effects(action)
        if effects is None:
            return CandidateConvergence(
                candidate.action_ids,
                tuple(applied),
                False,
                stable_digest(state),
                findings=(
                    ReplayFinding(
                        ReplayFindingCode.AMBIGUOUS_EFFECT,
                        "action declares conflicting values for the same effect fact",
                        action_id=action_id,
                    ),
                ),
            )
        state.update(effects)
        applied.append(action_id)

    unresolved_goal = _open_predicates(board.goal.desired_state, state)
    if unresolved_goal:
        return CandidateConvergence(
            candidate.action_ids,
            tuple(applied),
            False,
            stable_digest(state),
            findings=(
                ReplayFinding(
                    ReplayFindingCode.GOAL_UNSATISFIED,
                    "candidate replay completed without satisfying the board goal",
                    predicates=unresolved_goal,
                ),
            ),
        )
    return CandidateConvergence(
        candidate.action_ids,
        tuple(applied),
        True,
        stable_digest(state),
    )


def replay_regression_frontier(
    board: PlanningBoard,
    initial_state: Mapping[str, Any],
    regression_report: RegressionReport,
) -> FrontierConvergenceReport:
    """Forward-replay complete backward candidates over exact symbolic state."""

    state_digest = _validate_bindings(board, initial_state, regression_report)
    complete_candidates = tuple(
        sorted(regression_report.complete_candidates, key=lambda item: item.action_ids)
    )
    action_paths = [candidate.action_ids for candidate in complete_candidates]
    if len(action_paths) != len(set(action_paths)):
        raise ValueError("regression report contains duplicate complete candidate paths")
    assessments = tuple(
        _replay_candidate(board, initial_state, candidate)
        for candidate in complete_candidates
    )
    return FrontierConvergenceReport(
        board_id=board.board_id,
        board_digest=board.digest,
        state_digest=state_digest,
        regression_report_digest=stable_digest(regression_report.to_dict()),
        assessments=assessments,
        ignored_incomplete_candidates=(
            len(regression_report.candidates) - len(complete_candidates)
        ),
    )
