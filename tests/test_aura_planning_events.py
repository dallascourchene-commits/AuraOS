import json

import pytest

from aura_event_contracts import AppendOnlyEventStore, stable_digest
from aura_planning_board import (
    ActionSpec,
    EffectSpec,
    GoalSpec,
    PlanningBoard,
    PredicateSpec,
)
from aura_planning_events import (
    PlanningEventKind,
    record_frontier_event,
    record_planning_board_event,
    record_regression_event,
)
from aura_planning_frontier import (
    FrontierConvergenceReport,
    replay_regression_frontier,
)
from aura_planning_regression import RegressionReport, regress_board_goal


def _board(*, expected=True, evidence_refs=()) -> PlanningBoard:
    finish = ActionSpec(
        action_id="finish",
        name="finish",
        domain="planning-event-test",
        preconditions=(),
        effects=(EffectSpec("finished", expected),),
        verifier_ids=("verifier",),
        evidence_refs=tuple(evidence_refs),
    )
    return PlanningBoard(
        board_id="board-events",
        arena_id="test-arena",
        purpose_digest="purpose:events",
        goal=GoalSpec(
            "goal-events",
            "Record a proposal-only planning history",
            (PredicateSpec("finished", expected),),
        ),
        actions=(finish,),
    )


def _planning_stack(board: PlanningBoard, state=None):
    state = {} if state is None else state
    regression = regress_board_goal(board, state)
    frontier = replay_regression_frontier(board, state, regression)
    return state, regression, frontier


def _sidecar_payload(store: AppendOnlyEventStore, path: str):
    return json.loads((store.root / path).read_text(encoding="utf-8"))


def test_board_projection_persists_exact_sidecar_and_compact_event(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()

    receipt = record_planning_board_event(
        store,
        board,
        trace_id="trace-1",
        actor_id="aura",
        evidence_refs=("source:1",),
        created_at=100.0,
    )

    payload = _sidecar_payload(store, receipt.payload_ref.path)
    assert receipt.kind is PlanningEventKind.BOARD_CREATED
    assert receipt.appended is True
    assert receipt.payload_ref.payload_digest == stable_digest(payload)
    assert receipt.event.payload_ref == receipt.payload_ref.ref_id
    assert receipt.event.payload_digest == receipt.payload_ref.payload_digest
    assert receipt.event.event_type == "planning.board.created"
    assert receipt.event.board_id == board.board_id
    assert receipt.event.arena_id == board.arena_id
    assert receipt.event.objective_id == board.goal.goal_id
    assert receipt.event.evidence_refs == ("source:1",)
    assert receipt.event.proposal_only is True
    assert list(store.iter_events()) == [receipt.event.to_dict()]


def test_identical_projection_is_idempotent_with_explicit_timestamp(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()
    kwargs = {
        "trace_id": "trace-idempotent",
        "actor_id": "aura",
        "created_at": 123.5,
    }

    first = record_planning_board_event(store, board, **kwargs)
    second = record_planning_board_event(store, board, **kwargs)

    assert first.event.event_id == second.event.event_id
    assert first.payload_ref.ref_id == second.payload_ref.ref_id
    assert first.appended is True
    assert second.appended is False
    assert len(list(store.iter_events())) == 1


def test_board_regression_frontier_parent_chain_is_exact(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()
    state, regression, frontier = _planning_stack(board)

    board_event = record_planning_board_event(
        store,
        board,
        trace_id="trace-chain",
        actor_id="aura",
        created_at=1.0,
    )
    regression_event = record_regression_event(
        store,
        board,
        state,
        regression,
        trace_id="trace-chain",
        actor_id="aura",
        parent_event_ids=(board_event.event.event_id,),
        created_at=2.0,
    )
    frontier_event = record_frontier_event(
        store,
        board,
        state,
        regression,
        frontier,
        trace_id="trace-chain",
        actor_id="aura",
        parent_event_ids=(regression_event.event.event_id,),
        created_at=3.0,
    )

    assert regression_event.event.parent_event_ids == (board_event.event.event_id,)
    assert frontier_event.event.parent_event_ids == (regression_event.event.event_id,)
    assert regression_event.event.measurement_classes == {"explored_nodes": "DERIVED"}
    assert frontier_event.event.measurement_classes == {
        "candidate_convergence": "DERIVED"
    }
    assert [event["event_id"] for event in store.iter_events()] == [
        board_event.event.event_id,
        regression_event.event.event_id,
        frontier_event.event.event_id,
    ]


def test_regression_binding_mismatches_fail_closed(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()
    state, regression, _frontier = _planning_stack(board)

    wrong_board = RegressionReport(
        board_id="other-board",
        board_digest=regression.board_digest,
        state_digest=regression.state_digest,
        candidates=regression.candidates,
        findings=regression.findings,
        explored_nodes=regression.explored_nodes,
    )
    with pytest.raises(ValueError, match="board_id"):
        record_regression_event(
            store,
            board,
            state,
            wrong_board,
            trace_id="trace",
            actor_id="aura",
        )

    wrong_digest = RegressionReport(
        board_id=regression.board_id,
        board_digest="wrong-digest",
        state_digest=regression.state_digest,
        candidates=regression.candidates,
        findings=regression.findings,
        explored_nodes=regression.explored_nodes,
    )
    with pytest.raises(ValueError, match="board_digest"):
        record_regression_event(
            store,
            board,
            state,
            wrong_digest,
            trace_id="trace",
            actor_id="aura",
        )

    with pytest.raises(ValueError, match="state_digest"):
        record_regression_event(
            store,
            board,
            {"tampered": True},
            regression,
            trace_id="trace",
            actor_id="aura",
        )


def test_frontier_must_match_exact_regression_report(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()
    state, regression, frontier = _planning_stack(board)
    tampered = FrontierConvergenceReport(
        board_id=frontier.board_id,
        board_digest=frontier.board_digest,
        state_digest=frontier.state_digest,
        regression_report_digest="wrong-regression",
        assessments=frontier.assessments,
        ignored_incomplete_candidates=frontier.ignored_incomplete_candidates,
    )

    with pytest.raises(ValueError, match="supplied regression"):
        record_frontier_event(
            store,
            board,
            state,
            regression,
            tampered,
            trace_id="trace",
            actor_id="aura",
        )


def test_duplicate_parent_and_evidence_refs_fail_before_append(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()

    with pytest.raises(ValueError, match="parent_event_ids"):
        record_planning_board_event(
            store,
            board,
            trace_id="trace",
            actor_id="aura",
            parent_event_ids=("parent", "parent"),
        )
    with pytest.raises(ValueError, match="evidence_refs"):
        record_planning_board_event(
            store,
            board,
            trace_id="trace",
            actor_id="aura",
            evidence_refs=("evidence", "evidence"),
        )
    assert list(store.iter_events()) == []


def test_existing_store_redacts_secrets_and_rejects_private_reasoning(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    secret_board = _board(expected={"api_key": "sk-abcdefghijklmnopqrstuvwxyz"})

    receipt = record_planning_board_event(
        store,
        secret_board,
        trace_id="trace-secret",
        actor_id="aura",
        created_at=10.0,
    )
    payload = _sidecar_payload(store, receipt.payload_ref.path)
    assert receipt.payload_ref.redacted is True
    assert payload["goal"]["desired_state"][0]["expected"]["api_key"] == "[REDACTED]"
    assert receipt.event.payload_digest == stable_digest(payload)

    private_board = _board(expected={"chain_of_thought": "must never persist"})
    with pytest.raises(ValueError, match="private reasoning"):
        record_planning_board_event(
            store,
            private_board,
            trace_id="trace-private",
            actor_id="aura",
        )


def test_non_finite_timestamp_and_string_ref_sequences_fail_closed(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()

    with pytest.raises(ValueError, match="finite"):
        record_planning_board_event(
            store,
            board,
            trace_id="trace",
            actor_id="aura",
            created_at=float("nan"),
        )
    with pytest.raises(ValueError, match="sequence"):
        record_planning_board_event(
            store,
            board,
            trace_id="trace",
            actor_id="aura",
            parent_event_ids="parent",  # type: ignore[arg-type]
        )
