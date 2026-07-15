import json

from aura_event_contracts import AppendOnlyEventStore
from aura_planning_board import GoalSpec, PlanningBoard, PredicateSpec
from aura_planning_events import record_planning_board_event
from aura_planning_projector import (
    ProjectionFindingCode,
    project_planning_history,
)


def test_noncanonical_planning_event_bytes_fail_closed(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    board = PlanningBoard(
        board_id="board-jsonl",
        arena_id="test-arena",
        purpose_digest="purpose:jsonl",
        goal=GoalSpec(
            "goal-jsonl",
            "Validate canonical event bytes",
            (PredicateSpec("finished", True),),
        ),
        actions=(),
    )
    record_planning_board_event(
        store,
        board,
        trace_id="trace-jsonl",
        actor_id="aura",
        created_at=1.0,
    )
    row = json.loads(store.events_path.read_text(encoding="utf-8"))
    store.events_path.write_text(
        json.dumps(row, indent=2) + "\n",
        encoding="utf-8",
    )

    report = project_planning_history(store)
    codes = {finding.code for finding in report.findings}

    assert report.integrity_complete is False
    assert report.chains == ()
    assert ProjectionFindingCode.NONCANONICAL_EVENT_RECORD in codes
