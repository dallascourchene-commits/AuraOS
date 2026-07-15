"""Append-only event projection for proposal-only planning artifacts.

P3.1 stores exact canonical Planning Board, regression, and frontier payloads in
immutable sidecars, then emits compact digest-bound Aura event envelopes. This
module records planning history only: it never executes, authorizes, verifies,
or captures private reasoning.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from aura_event_contracts import (
    ActorType,
    AppendOnlyEventStore,
    AuraEventEnvelope,
    DIKWPStage,
    ExactPayloadRef,
    MeasurementClass,
    canonical_json,
    stable_digest,
)
from aura_planning_board import PlanningBoard
from aura_planning_frontier import FrontierConvergenceReport
from aura_planning_regression import RegressionReport

PLANNING_EVENT_PROJECTION_VERSION = "AURA_PLANNING_EVENT_PROJECTION_V1"
DEFAULT_POLICY_SCOPE = "planning.proposal"


class PlanningEventKind(str, Enum):
    BOARD_CREATED = "planning.board.created"
    REGRESSION_COMPLETED = "planning.regression.completed"
    FRONTIER_COMPLETED = "planning.frontier.completed"


_SIDECAR_KIND = {
    PlanningEventKind.BOARD_CREATED: "planning-board-v1",
    PlanningEventKind.REGRESSION_COMPLETED: "planning-regression-v1",
    PlanningEventKind.FRONTIER_COMPLETED: "planning-frontier-v1",
}

_STAGE = {
    PlanningEventKind.BOARD_CREATED: DIKWPStage.PURPOSE,
    PlanningEventKind.REGRESSION_COMPLETED: DIKWPStage.KNOWLEDGE,
    PlanningEventKind.FRONTIER_COMPLETED: DIKWPStage.WISDOM,
}

_MEASUREMENTS = {
    PlanningEventKind.BOARD_CREATED: {},
    PlanningEventKind.REGRESSION_COMPLETED: {
        "explored_nodes": MeasurementClass.DERIVED,
    },
    PlanningEventKind.FRONTIER_COMPLETED: {
        "candidate_convergence": MeasurementClass.DERIVED,
    },
}


def _required(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _refs(values: Iterable[Any], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be a sequence")
    normalized = tuple(_required(item, field_name) for item in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


def _timestamp(value: float | None) -> float | None:
    if value is None:
        return None
    timestamp = float(value)
    if not math.isfinite(timestamp):
        raise ValueError("created_at must be finite")
    return timestamp


def _validate_board(board: PlanningBoard) -> None:
    if not isinstance(board, PlanningBoard):
        raise ValueError("board must be a PlanningBoard")


def _validate_regression_bindings(
    board: PlanningBoard,
    initial_state: Mapping[str, Any],
    report: RegressionReport,
) -> str:
    _validate_board(board)
    if not isinstance(initial_state, Mapping):
        raise ValueError("initial_state must be a mapping")
    if not isinstance(report, RegressionReport):
        raise ValueError("regression_report must be a RegressionReport")
    canonical_json(initial_state)
    state_digest = stable_digest(initial_state)
    if report.board_id != board.board_id:
        raise ValueError("regression report board_id does not match the Planning Board")
    if report.board_digest != board.digest:
        raise ValueError("regression report board_digest does not match the Planning Board")
    if report.state_digest != state_digest:
        raise ValueError("regression report state_digest does not match initial_state")
    return state_digest


def _validate_frontier_bindings(
    board: PlanningBoard,
    initial_state: Mapping[str, Any],
    regression_report: RegressionReport,
    frontier_report: FrontierConvergenceReport,
) -> None:
    state_digest = _validate_regression_bindings(
        board,
        initial_state,
        regression_report,
    )
    if not isinstance(frontier_report, FrontierConvergenceReport):
        raise ValueError("frontier_report must be a FrontierConvergenceReport")
    if frontier_report.board_id != board.board_id:
        raise ValueError("frontier report board_id does not match the Planning Board")
    if frontier_report.board_digest != board.digest:
        raise ValueError("frontier report board_digest does not match the Planning Board")
    if frontier_report.state_digest != state_digest:
        raise ValueError("frontier report state_digest does not match initial_state")
    expected_regression_digest = stable_digest(regression_report.to_dict())
    if frontier_report.regression_report_digest != expected_regression_digest:
        raise ValueError("frontier report is not bound to the supplied regression report")


@dataclass(frozen=True)
class PlanningEventReceipt:
    """Result of storing one planning payload and appending its event envelope."""

    kind: PlanningEventKind | str
    payload_ref: ExactPayloadRef
    event: AuraEventEnvelope
    appended: bool
    version: str = PLANNING_EVENT_PROJECTION_VERSION

    def __post_init__(self) -> None:
        try:
            kind = self.kind if isinstance(self.kind, PlanningEventKind) else PlanningEventKind(str(self.kind))
        except ValueError as exc:
            raise ValueError(f"unknown planning event kind: {self.kind}") from exc
        if not isinstance(self.payload_ref, ExactPayloadRef):
            raise ValueError("payload_ref must be an ExactPayloadRef")
        if not isinstance(self.event, AuraEventEnvelope):
            raise ValueError("event must be an AuraEventEnvelope")
        if type(self.appended) is not bool:
            raise ValueError("appended must be a boolean")
        if self.event.event_type != kind.value:
            raise ValueError("event type does not match planning event kind")
        if self.event.payload_ref != self.payload_ref.ref_id:
            raise ValueError("event payload_ref does not match the immutable sidecar")
        if self.event.payload_digest != self.payload_ref.payload_digest:
            raise ValueError("event payload_digest does not match the immutable sidecar")
        if self.event.proposal_only is not True:
            raise ValueError("planning events must remain proposal_only")
        if self.version != PLANNING_EVENT_PROJECTION_VERSION:
            raise ValueError(f"unsupported planning event projection version: {self.version}")
        object.__setattr__(self, "kind", kind)


def _create_envelope(
    *,
    kind: PlanningEventKind,
    board: PlanningBoard,
    trace_id: str,
    actor_id: str,
    actor_type: ActorType | str,
    parent_event_ids: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    policy_scope: str,
    payload_ref: str,
    payload_digest: str,
    created_at: float | None,
) -> AuraEventEnvelope:
    """Create one validated envelope without performing any store mutation."""

    return AuraEventEnvelope.create(
        trace_id=trace_id,
        parent_event_ids=parent_event_ids,
        event_type=kind.value,
        actor_id=actor_id,
        actor_type=actor_type,
        arena_id=board.arena_id,
        board_id=board.board_id,
        node_id=kind.value,
        objective_id=board.goal.goal_id,
        purpose_digest=board.purpose_digest,
        dikwp_stage=_STAGE[kind],
        payload_ref=payload_ref,
        payload_digest=payload_digest,
        evidence_refs=evidence_refs,
        policy_scope=policy_scope,
        proposal_only=True,
        measurement_classes=_MEASUREMENTS[kind],
        created_at=created_at,
    )


def _record(
    store: AppendOnlyEventStore,
    *,
    kind: PlanningEventKind,
    artifact_payload: Mapping[str, Any],
    board: PlanningBoard,
    trace_id: str,
    actor_id: str,
    actor_type: ActorType | str,
    parent_event_ids: Sequence[str],
    evidence_refs: Sequence[str],
    policy_scope: str,
    created_at: float | None,
) -> PlanningEventReceipt:
    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")
    parents = _refs(parent_event_ids, "parent_event_ids")
    evidence = _refs(evidence_refs, "evidence_refs")
    timestamp = _timestamp(created_at)
    trace = _required(trace_id, "trace_id")
    actor = _required(actor_id, "actor_id")
    scope = _required(policy_scope, "policy_scope")

    # Validate every dynamic and fixed envelope field before writing the
    # immutable sidecar. The placeholder values are non-authoritative and are
    # never appended; they only prove that final event creation cannot fail for
    # caller-controlled envelope data after persistence has begun.
    _create_envelope(
        kind=kind,
        board=board,
        trace_id=trace,
        actor_id=actor,
        actor_type=actor_type,
        parent_event_ids=parents,
        evidence_refs=evidence,
        policy_scope=scope,
        payload_ref="preflight:planning-payload",
        payload_digest="preflight-planning-payload-digest",
        created_at=timestamp,
    )

    payload_ref = store.store_payload(
        artifact_payload,
        kind=_SIDECAR_KIND[kind],
        created_at=timestamp,
    )
    event = _create_envelope(
        kind=kind,
        board=board,
        trace_id=trace,
        actor_id=actor,
        actor_type=actor_type,
        parent_event_ids=parents,
        evidence_refs=evidence,
        policy_scope=scope,
        payload_ref=payload_ref.ref_id,
        payload_digest=payload_ref.payload_digest,
        created_at=timestamp,
    )
    return PlanningEventReceipt(
        kind=kind,
        payload_ref=payload_ref,
        event=event,
        appended=store.append(event),
    )


def record_planning_board_event(
    store: AppendOnlyEventStore,
    board: PlanningBoard,
    *,
    trace_id: str,
    actor_id: str,
    actor_type: ActorType | str = ActorType.AURA,
    parent_event_ids: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    policy_scope: str = DEFAULT_POLICY_SCOPE,
    created_at: float | None = None,
) -> PlanningEventReceipt:
    """Persist one exact Planning Board payload and append its proposal event."""

    _validate_board(board)
    return _record(
        store,
        kind=PlanningEventKind.BOARD_CREATED,
        artifact_payload=board.to_dict(),
        board=board,
        trace_id=trace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        parent_event_ids=parent_event_ids,
        evidence_refs=evidence_refs,
        policy_scope=policy_scope,
        created_at=created_at,
    )


def record_regression_event(
    store: AppendOnlyEventStore,
    board: PlanningBoard,
    initial_state: Mapping[str, Any],
    regression_report: RegressionReport,
    *,
    trace_id: str,
    actor_id: str,
    actor_type: ActorType | str = ActorType.AURA,
    parent_event_ids: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    policy_scope: str = DEFAULT_POLICY_SCOPE,
    created_at: float | None = None,
) -> PlanningEventReceipt:
    """Persist an exact, board-bound backward-regression report event."""

    _validate_regression_bindings(board, initial_state, regression_report)
    return _record(
        store,
        kind=PlanningEventKind.REGRESSION_COMPLETED,
        artifact_payload=regression_report.to_dict(),
        board=board,
        trace_id=trace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        parent_event_ids=parent_event_ids,
        evidence_refs=evidence_refs,
        policy_scope=policy_scope,
        created_at=created_at,
    )


def record_frontier_event(
    store: AppendOnlyEventStore,
    board: PlanningBoard,
    initial_state: Mapping[str, Any],
    regression_report: RegressionReport,
    frontier_report: FrontierConvergenceReport,
    *,
    trace_id: str,
    actor_id: str,
    actor_type: ActorType | str = ActorType.AURA,
    parent_event_ids: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    policy_scope: str = DEFAULT_POLICY_SCOPE,
    created_at: float | None = None,
) -> PlanningEventReceipt:
    """Persist an exact frontier report bound to its board and regression."""

    _validate_frontier_bindings(
        board,
        initial_state,
        regression_report,
        frontier_report,
    )
    return _record(
        store,
        kind=PlanningEventKind.FRONTIER_COMPLETED,
        artifact_payload=frontier_report.to_dict(),
        board=board,
        trace_id=trace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        parent_event_ids=parent_event_ids,
        evidence_refs=evidence_refs,
        policy_scope=policy_scope,
        created_at=created_at,
    )
