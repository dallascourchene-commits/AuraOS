"""Bounded backward-regression planning over proposal-only Planning Boards.

P2.2 introduces deterministic backward search without execution, authority,
provider calls, or live planner migration. Planning proposes candidate action
sequences; existing governance and verification contracts remain authoritative.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import json
from typing import Any

from aura_event_contracts import canonical_json, stable_digest
from aura_planning_board import (
    ActionSpec,
    PlanningBoard,
    PredicateOperator,
    PredicateSpec,
)

REGRESSION_VERSION = "AURA_PLANNING_REGRESSION_V1"


class RegressionFindingCode(str, Enum):
    NO_PRODUCER = "NO_PRODUCER"
    DEPTH_LIMIT = "DEPTH_LIMIT"
    CYCLE_BLOCKED = "CYCLE_BLOCKED"
    CANDIDATE_LIMIT = "CANDIDATE_LIMIT"


class CanonicalRecord:
    def to_dict(self) -> dict[str, Any]:
        return json.loads(canonical_json(self))


@dataclass(frozen=True)
class RegressionFinding(CanonicalRecord):
    code: RegressionFindingCode | str
    fact: str
    message: str
    path_action_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        try:
            code = self.code if isinstance(self.code, RegressionFindingCode) else RegressionFindingCode(str(self.code))
        except ValueError as exc:
            raise ValueError(f"unknown regression finding code: {self.code}") from exc
        fact = str(self.fact or "").strip()
        message = str(self.message or "").strip()
        if not fact:
            raise ValueError("regression finding fact must not be empty")
        if not message:
            raise ValueError("regression finding message must not be empty")
        if isinstance(self.path_action_ids, (str, bytes, bytearray)):
            raise ValueError("path_action_ids must be a sequence")
        path = tuple(str(item or "").strip() for item in self.path_action_ids)
        if any(not item for item in path):
            raise ValueError("path_action_ids must not contain empty values")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "fact", fact)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "path_action_ids", path)


@dataclass(frozen=True)
class RegressionCandidate(CanonicalRecord):
    """One possible action sequence. It never grants authority or executes."""

    action_ids: tuple[str, ...]
    unresolved_predicates: tuple[PredicateSpec, ...] = ()
    proposal_only: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.action_ids, (str, bytes, bytearray)):
            raise ValueError("candidate action_ids must be a sequence")
        action_ids = tuple(str(item or "").strip() for item in self.action_ids)
        if any(not item for item in action_ids):
            raise ValueError("candidate action_ids must not contain empty values")
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("candidate action_ids must not contain duplicates")
        if isinstance(self.unresolved_predicates, (str, bytes, bytearray)):
            raise ValueError("candidate unresolved_predicates must be a sequence")
        predicates = tuple(self.unresolved_predicates)
        if not all(isinstance(item, PredicateSpec) for item in predicates):
            raise ValueError("candidate unresolved_predicates contains an invalid value")
        if type(self.proposal_only) is not bool:
            raise ValueError("candidate proposal_only must be a boolean")
        if self.proposal_only is not True:
            raise ValueError("regression candidates must remain proposal_only")
        object.__setattr__(self, "action_ids", action_ids)
        object.__setattr__(self, "unresolved_predicates", predicates)

    @property
    def complete(self) -> bool:
        return not self.unresolved_predicates


@dataclass(frozen=True)
class RegressionReport(CanonicalRecord):
    board_id: str
    board_digest: str
    state_digest: str
    candidates: tuple[RegressionCandidate, ...]
    findings: tuple[RegressionFinding, ...]
    explored_nodes: int
    version: str = REGRESSION_VERSION

    def __post_init__(self) -> None:
        for field_name in ("board_id", "board_digest", "state_digest"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"report {field_name} must not be empty")
            object.__setattr__(self, field_name, value)
        if isinstance(self.candidates, (str, bytes, bytearray)):
            raise ValueError("report candidates must be a sequence")
        candidates = tuple(self.candidates)
        if not all(isinstance(item, RegressionCandidate) for item in candidates):
            raise ValueError("report candidates contains an invalid value")
        if isinstance(self.findings, (str, bytes, bytearray)):
            raise ValueError("report findings must be a sequence")
        findings = tuple(self.findings)
        if not all(isinstance(item, RegressionFinding) for item in findings):
            raise ValueError("report findings contains an invalid value")
        if type(self.explored_nodes) is not int or self.explored_nodes < 0:
            raise ValueError("report explored_nodes must be a non-negative integer")
        if self.version != REGRESSION_VERSION:
            raise ValueError(f"unsupported regression version: {self.version}")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "findings", findings)

    @property
    def complete_candidates(self) -> tuple[RegressionCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.complete)


def predicate_satisfied(predicate: PredicateSpec, state: Mapping[str, Any]) -> bool:
    """Evaluate public symbolic state only; no model reasoning is inspected."""

    if not isinstance(predicate, PredicateSpec):
        raise ValueError("predicate must be a PredicateSpec")
    if not isinstance(state, Mapping):
        raise ValueError("state must be a mapping")
    exists = predicate.fact in state
    if predicate.operator is PredicateOperator.EXISTS:
        return exists is bool(predicate.expected)
    if not exists:
        return False
    actual = state[predicate.fact]
    if predicate.operator is PredicateOperator.EQ:
        return actual == predicate.expected
    if predicate.operator is PredicateOperator.IN:
        try:
            return actual in predicate.expected
        except TypeError:
            return False
    raise ValueError(f"unsupported predicate operator: {predicate.operator}")


def _effect_value_satisfies(value: Any, predicate: PredicateSpec) -> bool:
    if predicate.operator is PredicateOperator.EXISTS:
        return predicate.expected is True
    if predicate.operator is PredicateOperator.EQ:
        return value == predicate.expected
    if predicate.operator is PredicateOperator.IN:
        try:
            return value in predicate.expected
        except TypeError:
            return False
    raise ValueError(f"unsupported predicate operator: {predicate.operator}")


def _effect_satisfies(action: ActionSpec, predicate: PredicateSpec) -> bool:
    matching = tuple(effect for effect in action.effects if effect.fact == predicate.fact)
    if not matching:
        return False
    values = {canonical_json(effect.value) for effect in matching}
    if len(values) != 1:
        return False
    return _effect_value_satisfies(matching[0].value, predicate)


def _action_conflicts(
    action: ActionSpec,
    predicates: Sequence[PredicateSpec],
) -> bool:
    """Return True when an action ambiguously overwrites a protected requirement."""

    by_fact: dict[str, list[Any]] = {}
    for effect in action.effects:
        by_fact.setdefault(effect.fact, []).append(effect.value)
    for predicate in predicates:
        values = by_fact.get(predicate.fact)
        if values is None:
            continue
        canonical_values = {canonical_json(value) for value in values}
        if len(canonical_values) != 1:
            return True
        if not _effect_value_satisfies(values[0], predicate):
            return True
    return False


def _predicate_key(predicate: PredicateSpec) -> str:
    return canonical_json(predicate)


def _dedupe_predicates(predicates: Sequence[PredicateSpec]) -> tuple[PredicateSpec, ...]:
    by_key: dict[str, PredicateSpec] = {}
    for predicate in predicates:
        by_key.setdefault(_predicate_key(predicate), predicate)
    return tuple(by_key[key] for key in sorted(by_key))


def _open_predicates(
    predicates: Sequence[PredicateSpec],
    initial_state: Mapping[str, Any],
) -> tuple[PredicateSpec, ...]:
    return _dedupe_predicates(
        tuple(predicate for predicate in predicates if not predicate_satisfied(predicate, initial_state))
    )


def regress_board_goal(
    board: PlanningBoard,
    initial_state: Mapping[str, Any],
    *,
    max_depth: int = 8,
    max_candidates: int = 32,
    max_explored_nodes: int = 2048,
) -> RegressionReport:
    """Backward-regress the board goal into bounded proposal-only candidates.

    Search is deterministic and finite. Actions are never executed, constraints
    are not waived, and a complete symbolic candidate is not an authority grant.
    """

    if not isinstance(board, PlanningBoard):
        raise ValueError("board must be a PlanningBoard")
    if not isinstance(initial_state, Mapping):
        raise ValueError("initial_state must be a mapping")
    for name, value in (
        ("max_depth", max_depth),
        ("max_candidates", max_candidates),
        ("max_explored_nodes", max_explored_nodes),
    ):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    canonical_json(initial_state)

    actions = tuple(sorted(board.actions, key=lambda action: action.action_id))
    initial_open = _open_predicates(board.goal.desired_state, initial_state)
    if not initial_open:
        return RegressionReport(
            board_id=board.board_id,
            board_digest=board.digest,
            state_digest=stable_digest(initial_state),
            candidates=(RegressionCandidate(()),),
            findings=(),
            explored_nodes=1,
        )

    initial_protected = _dedupe_predicates(board.goal.desired_state)
    queue: list[
        tuple[tuple[PredicateSpec, ...], tuple[PredicateSpec, ...], tuple[str, ...]]
    ] = [(initial_open, initial_protected, ())]
    visited: set[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = set()
    candidates: list[RegressionCandidate] = []
    findings: list[RegressionFinding] = []
    explored_nodes = 0
    candidate_limit_reported = False

    while queue and explored_nodes < max_explored_nodes:
        open_predicates, protected_predicates, selected_reversed = queue.pop(0)
        state_key = (
            tuple(_predicate_key(item) for item in open_predicates),
            tuple(_predicate_key(item) for item in protected_predicates),
            selected_reversed,
        )
        if state_key in visited:
            continue
        visited.add(state_key)
        explored_nodes += 1

        if not open_predicates:
            candidates.append(RegressionCandidate(tuple(reversed(selected_reversed))))
            if len(candidates) >= max_candidates:
                candidate_limit_reported = bool(queue)
                break
            continue

        protected_requirements = _dedupe_predicates(
            (*open_predicates, *protected_predicates)
        )
        producer_options = tuple(
            (target, action)
            for target in open_predicates
            for action in actions
            if _effect_satisfies(action, target)
            and not _action_conflicts(action, protected_requirements)
        )
        producible_keys = {
            _predicate_key(target) for target, _action in producer_options
        }
        missing_targets = tuple(
            target
            for target in open_predicates
            if _predicate_key(target) not in producible_keys
        )
        if missing_targets:
            target = missing_targets[0]
            candidates.append(
                RegressionCandidate(
                    tuple(reversed(selected_reversed)),
                    unresolved_predicates=open_predicates,
                )
            )
            findings.append(
                RegressionFinding(
                    RegressionFindingCode.NO_PRODUCER,
                    target.fact,
                    "no board action can establish the open predicate",
                    tuple(reversed(selected_reversed)),
                )
            )
            if len(candidates) >= max_candidates:
                candidate_limit_reported = bool(queue)
                break
            continue

        if len(selected_reversed) >= max_depth:
            target = open_predicates[0]
            candidates.append(
                RegressionCandidate(
                    tuple(reversed(selected_reversed)),
                    unresolved_predicates=open_predicates,
                )
            )
            findings.append(
                RegressionFinding(
                    RegressionFindingCode.DEPTH_LIMIT,
                    target.fact,
                    "maximum regression depth reached before resolving the predicate",
                    tuple(reversed(selected_reversed)),
                )
            )
            if len(candidates) >= max_candidates:
                candidate_limit_reported = bool(queue)
                break
            continue

        expanded = False
        for target, action in producer_options:
            if action.action_id in selected_reversed:
                findings.append(
                    RegressionFinding(
                        RegressionFindingCode.CYCLE_BLOCKED,
                        target.fact,
                        f"action '{action.action_id}' would repeat in the same candidate path",
                        tuple(reversed(selected_reversed)),
                    )
                )
                continue
            remaining = tuple(
                predicate
                for predicate in open_predicates
                if not _effect_satisfies(action, predicate)
            )
            protected_after = _dedupe_predicates(
                tuple(
                    predicate
                    for predicate in protected_predicates
                    if not _effect_satisfies(action, predicate)
                )
            )
            regressed = _open_predicates((*remaining, *action.preconditions), initial_state)
            queue.append(
                (regressed, protected_after, (*selected_reversed, action.action_id))
            )
            expanded = True
        if not expanded:
            candidates.append(
                RegressionCandidate(
                    tuple(reversed(selected_reversed)),
                    unresolved_predicates=open_predicates,
                )
            )
            if len(candidates) >= max_candidates:
                candidate_limit_reported = bool(queue)
                break

    if queue and explored_nodes >= max_explored_nodes:
        target = queue[0][0][0] if queue[0][0] else board.goal.desired_state[0]
        findings.append(
            RegressionFinding(
                RegressionFindingCode.DEPTH_LIMIT,
                target.fact,
                "maximum explored-node budget reached",
                tuple(reversed(queue[0][2])),
            )
        )
    if candidate_limit_reported:
        target = queue[0][0][0] if queue and queue[0][0] else board.goal.desired_state[0]
        findings.append(
            RegressionFinding(
                RegressionFindingCode.CANDIDATE_LIMIT,
                target.fact,
                "maximum candidate count reached",
            )
        )

    unique_candidates: dict[str, RegressionCandidate] = {}
    for candidate in candidates:
        unique_candidates.setdefault(canonical_json(candidate), candidate)
    ordered_candidates = tuple(unique_candidates[key] for key in sorted(unique_candidates))
    ordered_findings = tuple(
        sorted(findings, key=lambda item: (item.code.value, item.fact, item.path_action_ids, item.message))
    )
    return RegressionReport(
        board_id=board.board_id,
        board_digest=board.digest,
        state_digest=stable_digest(initial_state),
        candidates=ordered_candidates,
        findings=ordered_findings,
        explored_nodes=explored_nodes,
    )
