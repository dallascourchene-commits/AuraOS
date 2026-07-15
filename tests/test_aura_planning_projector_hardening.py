import json
from pathlib import Path

from aura_event_contracts import (
    AppendOnlyEventStore,
    AuraEventEnvelope,
    canonical_json,
    stable_digest,
    stable_id,
)
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
from aura_planning_frontier import replay_regression_frontier
from aura_planning_projector import (
    ProjectionFindingCode,
    project_planning_history,
)
from aura_planning_regression import regress_board_goal


_SIDECAR_KIND = {
    PlanningEventKind.BOARD_CREATED: "planning-board-v1",
    PlanningEventKind.REGRESSION_COMPLETED: "planning-regression-v1",
    PlanningEventKind.FRONTIER_COMPLETED: "planning-frontier-v1",
}


def _board() -> PlanningBoard:
    return PlanningBoard(
        board_id="board-projector-hardening",
        arena_id="test-arena",
        purpose_digest="purpose:projector-hardening",
        goal=GoalSpec(
            "goal-projector-hardening",
            "Preserve fail-closed planning history projection",
            (PredicateSpec("finished", True),),
        ),
        actions=(
            ActionSpec(
                action_id="finish",
                name="finish",
                domain="planning-projector-hardening-test",
                preconditions=(),
                effects=(EffectSpec("finished", True),),
                verifier_ids=("verifier",),
                evidence_refs=("evidence:finish",),
            ),
        ),
    )


def _chain(tmp_path: Path):
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()
    state = {}
    regression = regress_board_goal(board, state)
    frontier = replay_regression_frontier(board, state, regression)
    board_receipt = record_planning_board_event(
        store,
        board,
        trace_id="trace-projector-hardening",
        actor_id="aura",
        created_at=1.0,
    )
    regression_receipt = record_regression_event(
        store,
        board,
        state,
        regression,
        trace_id="trace-projector-hardening",
        actor_id="aura",
        parent_event_ids=(board_receipt.event.event_id,),
        created_at=2.0,
    )
    frontier_receipt = record_frontier_event(
        store,
        board,
        state,
        regression,
        frontier,
        trace_id="trace-projector-hardening",
        actor_id="aura",
        parent_event_ids=(regression_receipt.event.event_id,),
        created_at=3.0,
    )
    return store, (board_receipt, regression_receipt, frontier_receipt)


def _event_rows(store: AppendOnlyEventStore) -> list[dict]:
    return [
        json.loads(line)
        for line in store.events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_rows(store: AppendOnlyEventStore, rows: list[dict]) -> None:
    store.events_path.write_text(
        "".join(
            json.dumps(
                row,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=True,
            )
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _rebuild_event(raw: dict, **changes) -> dict:
    value = dict(raw)
    value.update(changes)
    return AuraEventEnvelope.create(
        trace_id=value.get("trace_id"),
        parent_event_ids=value.get("parent_event_ids", ()),
        event_type=value.get("event_type"),
        actor_id=value.get("actor_id"),
        actor_type=value.get("actor_type"),
        arena_id=value.get("arena_id", ""),
        board_id=value.get("board_id", ""),
        node_id=value.get("node_id", ""),
        objective_id=value.get("objective_id", ""),
        purpose_digest=value.get("purpose_digest"),
        dikwp_stage=value.get("dikwp_stage"),
        payload_ref=value.get("payload_ref"),
        payload_digest=value.get("payload_digest"),
        evidence_refs=value.get("evidence_refs", ()),
        policy_scope=value.get("policy_scope", ""),
        proposal_only=value.get("proposal_only"),
        measurement_classes=value.get("measurement_classes"),
        confidence=value.get("confidence"),
        uncertainty=value.get("uncertainty"),
        created_at=value.get("created_at"),
    ).to_dict()


def _codes(report) -> set[ProjectionFindingCode]:
    return {finding.code for finding in report.findings}


def test_malformed_event_log_returns_blocking_finding(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    store.events_path.write_text("{\n", encoding="utf-8")

    report = project_planning_history(store)

    assert report.integrity_complete is False
    assert report.chains == ()
    assert ProjectionFindingCode.EVENT_LOG_READ_FAILED in _codes(report)


def test_non_string_event_type_is_rejected_without_crashing(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    store.events_path.write_text(
        canonical_json({"event_id": "event_bad", "event_type": []}) + "\n",
        encoding="utf-8",
    )

    report = project_planning_history(store)

    assert report.integrity_complete is False
    assert ProjectionFindingCode.INVALID_EVENT_RECORD in _codes(report)


def test_nonfinite_duplicate_record_fails_closed_before_digesting(tmp_path) -> None:
    store, _receipts = _chain(tmp_path)
    rows = _event_rows(store)
    tampered = dict(rows[0])
    tampered["unexpected_nonfinite"] = float("nan")
    rows.append(tampered)
    _write_rows(store, rows)

    report = project_planning_history(store)

    assert report.integrity_complete is False
    assert ProjectionFindingCode.INVALID_EVENT_RECORD in _codes(report)


def test_frontier_board_binding_has_distinct_diagnostic(tmp_path) -> None:
    store, receipts = _chain(tmp_path)
    rows = _event_rows(store)
    frontier_path = store.root / receipts[2].payload_ref.path
    payload = json.loads(frontier_path.read_text(encoding="utf-8"))
    payload["board_digest"] = "wrong-frontier-board-digest"
    digest = stable_digest(payload)
    ref_id = stable_id(
        "payload",
        {
            "kind": _SIDECAR_KIND[PlanningEventKind.FRONTIER_COMPLETED],
            "digest": digest,
        },
    )
    (store.sidecars_dir / f"{ref_id}.json").write_text(
        canonical_json(payload),
        encoding="utf-8",
    )
    rows[2] = _rebuild_event(
        rows[2],
        payload_ref=ref_id,
        payload_digest=digest,
    )
    _write_rows(store, rows)

    report = project_planning_history(store)

    assert report.integrity_complete is False
    assert ProjectionFindingCode.FRONTIER_BOARD_DIGEST_MISMATCH in _codes(report)
    assert ProjectionFindingCode.REGRESSION_BOARD_DIGEST_MISMATCH not in _codes(report)
