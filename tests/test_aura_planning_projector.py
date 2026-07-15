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
    finish = ActionSpec(
        action_id="finish",
        name="finish",
        domain="planning-projector-test",
        preconditions=(),
        effects=(EffectSpec("finished", True),),
        verifier_ids=("verifier",),
        evidence_refs=("evidence:finish",),
    )
    return PlanningBoard(
        board_id="board-projector",
        arena_id="test-arena",
        purpose_digest="purpose:projector",
        goal=GoalSpec(
            "goal-projector",
            "Reconstruct an exact proposal-only planning history",
            (PredicateSpec("finished", True),),
        ),
        actions=(finish,),
    )


def _chain(tmp_path: Path, *, timestamps=(1.0, 2.0, 3.0)):
    store = AppendOnlyEventStore(tmp_path / "events")
    board = _board()
    state = {}
    regression = regress_board_goal(board, state)
    frontier = replay_regression_frontier(board, state, regression)
    board_receipt = record_planning_board_event(
        store,
        board,
        trace_id="trace-projector",
        actor_id="aura",
        evidence_refs=("source:board",),
        created_at=timestamps[0],
    )
    regression_receipt = record_regression_event(
        store,
        board,
        state,
        regression,
        trace_id="trace-projector",
        actor_id="aura",
        parent_event_ids=(board_receipt.event.event_id,),
        evidence_refs=("source:regression",),
        created_at=timestamps[1],
    )
    frontier_receipt = record_frontier_event(
        store,
        board,
        state,
        regression,
        frontier,
        trace_id="trace-projector",
        actor_id="aura",
        parent_event_ids=(regression_receipt.event.event_id,),
        evidence_refs=("source:frontier",),
        created_at=timestamps[2],
    )
    return store, board, state, regression, frontier, (
        board_receipt,
        regression_receipt,
        frontier_receipt,
    )


def _event_rows(store: AppendOnlyEventStore) -> list[dict]:
    return [
        json.loads(line)
        for line in store.events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_event_rows(store: AppendOnlyEventStore, rows: list[dict]) -> None:
    store.events_path.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
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


def _replace_payload(
    store: AppendOnlyEventStore,
    rows: list[dict],
    index: int,
    kind: PlanningEventKind,
    payload: dict,
) -> None:
    digest = stable_digest(payload)
    ref_id = stable_id(
        "payload",
        {"kind": _SIDECAR_KIND[kind], "digest": digest},
    )
    (store.sidecars_dir / f"{ref_id}.json").write_text(
        canonical_json(payload),
        encoding="utf-8",
    )
    rows[index] = _rebuild_event(
        rows[index],
        payload_ref=ref_id,
        payload_digest=digest,
    )


def _codes(report) -> set[ProjectionFindingCode]:
    return {finding.code for finding in report.findings}


def _snapshot_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_valid_chain_projects_deterministically_without_store_mutation(tmp_path) -> None:
    store, board, _state, _regression, _frontier, receipts = _chain(tmp_path)
    before = _snapshot_files(store.root)

    first = project_planning_history(store)
    second = project_planning_history(store)

    assert first.integrity_complete is True
    assert first.findings == ()
    assert first.planning_event_count == 3
    assert first.ignored_nonplanning_events == 0
    assert len(first.chains) == 1
    chain = first.chains[0]
    assert chain.trace_id == "trace-projector"
    assert chain.board_id == board.board_id
    assert chain.board_event.event_id == receipts[0].event.event_id
    assert chain.regression_event.event_id == receipts[1].event.event_id
    assert chain.frontier_event.event_id == receipts[2].event.event_id
    assert first.to_dict() == second.to_dict()
    assert first.digest == second.digest
    assert _snapshot_files(store.root) == before


def test_unrelated_events_are_counted_and_ignored(tmp_path) -> None:
    store, *_rest = _chain(tmp_path)
    with store.events_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json({"event_id": "other", "event_type": "tool.result"}) + "\n")

    report = project_planning_history(store)

    assert report.integrity_complete is True
    assert len(report.chains) == 1
    assert report.planning_event_count == 3
    assert report.ignored_nonplanning_events == 1


def test_duplicate_and_conflicting_event_ids_fail_closed(tmp_path) -> None:
    store, *_rest = _chain(tmp_path)
    rows = _event_rows(store)
    rows.append(dict(rows[0]))
    _write_event_rows(store, rows)

    duplicate = project_planning_history(store)
    assert ProjectionFindingCode.DUPLICATE_EVENT_ID in _codes(duplicate)
    assert duplicate.integrity_complete is False

    rows[-1] = dict(rows[0])
    rows[-1]["actor_id"] = "tampered-actor"
    _write_event_rows(store, rows)
    conflicting = project_planning_history(store)
    assert ProjectionFindingCode.CONFLICTING_DUPLICATE_EVENT in _codes(conflicting)
    assert conflicting.integrity_complete is False


def test_event_id_and_envelope_are_independently_reverified(tmp_path) -> None:
    store, *_rest = _chain(tmp_path)
    rows = _event_rows(store)
    rows[0]["event_id"] = "event_tampered"
    _write_event_rows(store, rows)

    report = project_planning_history(store)

    assert ProjectionFindingCode.EVENT_ID_MISMATCH in _codes(report)
    assert report.integrity_complete is False


def test_invalid_contract_and_nonproposal_event_fail_closed(tmp_path) -> None:
    store, *_rest = _chain(tmp_path)
    rows = _event_rows(store)
    rows[0]["actor_type"] = "BAD"
    _write_event_rows(store, rows)
    invalid = project_planning_history(store)
    assert ProjectionFindingCode.INVALID_EVENT_RECORD in _codes(invalid)

    store, *_rest = _chain(tmp_path / "nonproposal")
    rows = _event_rows(store)
    rows[0] = _rebuild_event(rows[0], proposal_only=False)
    _write_event_rows(store, rows)
    nonproposal = project_planning_history(store)
    assert ProjectionFindingCode.NON_PROPOSAL_EVENT in _codes(nonproposal)
    assert nonproposal.integrity_complete is False


def test_wrong_stage_or_measurement_contract_is_rejected(tmp_path) -> None:
    store, *_rest = _chain(tmp_path)
    rows = _event_rows(store)
    rows[1] = _rebuild_event(rows[1], dikwp_stage="DATA")
    rows[2] = _rebuild_event(
        rows[2],
        parent_event_ids=(rows[1]["event_id"],),
    )
    _write_event_rows(store, rows)

    report = project_planning_history(store)

    assert ProjectionFindingCode.WRONG_EVENT_CONTRACT in _codes(report)
    assert report.integrity_complete is False


def test_unsafe_missing_malformed_and_noncanonical_sidecars_fail_closed(tmp_path) -> None:
    store, *_rest = _chain(tmp_path / "unsafe")
    rows = _event_rows(store)
    rows[0] = _rebuild_event(rows[0], payload_ref="../escape")
    _write_event_rows(store, rows)
    assert ProjectionFindingCode.UNSAFE_PAYLOAD_REF in _codes(project_planning_history(store))

    store, *_rest, receipts = _chain(tmp_path / "missing")
    (store.root / receipts[0].payload_ref.path).unlink()
    assert ProjectionFindingCode.MISSING_SIDECAR in _codes(project_planning_history(store))

    store, *_rest, receipts = _chain(tmp_path / "malformed")
    (store.root / receipts[0].payload_ref.path).write_text("{", encoding="utf-8")
    assert ProjectionFindingCode.MALFORMED_SIDECAR in _codes(project_planning_history(store))

    store, *_rest, receipts = _chain(tmp_path / "noncanonical")
    path = store.root / receipts[0].payload_ref.path
    payload = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    assert ProjectionFindingCode.NONCANONICAL_SIDECAR in _codes(project_planning_history(store))


def test_sidecar_digest_and_canonical_ref_are_reverified(tmp_path) -> None:
    store, *_rest, receipts = _chain(tmp_path / "digest")
    path = store.root / receipts[0].payload_ref.path
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["board_id"] = "tampered"
    path.write_text(canonical_json(payload), encoding="utf-8")
    assert ProjectionFindingCode.PAYLOAD_DIGEST_MISMATCH in _codes(project_planning_history(store))

    store, *_rest = _chain(tmp_path / "ref")
    rows = _event_rows(store)
    rows[0] = _rebuild_event(rows[0], payload_ref="payload_not_canonical")
    _write_event_rows(store, rows)
    codes = _codes(project_planning_history(store))
    assert ProjectionFindingCode.MISSING_SIDECAR in codes or ProjectionFindingCode.PAYLOAD_REF_MISMATCH in codes


def test_sidecar_metadata_must_match_event_envelope(tmp_path) -> None:
    store, *_rest, receipts = _chain(tmp_path)
    rows = _event_rows(store)
    payload = json.loads((store.root / receipts[0].payload_ref.path).read_text(encoding="utf-8"))
    payload["board_id"] = "other-board"
    _replace_payload(store, rows, 0, PlanningEventKind.BOARD_CREATED, payload)
    _write_event_rows(store, rows)

    report = project_planning_history(store)

    assert ProjectionFindingCode.PAYLOAD_METADATA_MISMATCH in _codes(report)
    assert report.integrity_complete is False


def test_orphans_wrong_parent_types_and_branching_are_detected(tmp_path) -> None:
    store, *_rest = _chain(tmp_path / "orphan")
    rows = _event_rows(store)
    rows[1] = _rebuild_event(rows[1], parent_event_ids=("event_missing",))
    _write_event_rows(store, rows)
    assert ProjectionFindingCode.MISSING_PARENT in _codes(project_planning_history(store))

    store, *_rest = _chain(tmp_path / "wrong-parent")
    rows = _event_rows(store)
    rows[2] = _rebuild_event(rows[2], parent_event_ids=(rows[0]["event_id"],))
    _write_event_rows(store, rows)
    assert ProjectionFindingCode.WRONG_PARENT_TYPE in _codes(project_planning_history(store))

    store, board, state, regression, _frontier, receipts = _chain(tmp_path / "branch")
    record_regression_event(
        store,
        board,
        state,
        regression,
        trace_id="trace-projector",
        actor_id="aura",
        parent_event_ids=(receipts[0].event.event_id,),
        created_at=2.5,
    )
    assert ProjectionFindingCode.BRANCHING_CHAIN in _codes(project_planning_history(store))


def test_cross_context_and_timestamp_order_mismatches_are_detected(tmp_path) -> None:
    store, *_rest = _chain(tmp_path / "context")
    rows = _event_rows(store)
    rows[1] = _rebuild_event(rows[1], trace_id="trace-other")
    rows[2] = _rebuild_event(rows[2], parent_event_ids=(rows[1]["event_id"],))
    _write_event_rows(store, rows)
    assert ProjectionFindingCode.CHAIN_CONTEXT_MISMATCH in _codes(project_planning_history(store))

    store, *_rest = _chain(tmp_path / "order", timestamps=(3.0, 2.0, 1.0))
    assert ProjectionFindingCode.OUT_OF_ORDER in _codes(project_planning_history(store))


def test_board_regression_frontier_digest_bindings_fail_closed(tmp_path) -> None:
    store, *_rest, receipts = _chain(tmp_path / "board-binding")
    rows = _event_rows(store)
    regression_payload = json.loads(
        (store.root / receipts[1].payload_ref.path).read_text(encoding="utf-8")
    )
    regression_payload["board_digest"] = "wrong-board-digest"
    _replace_payload(
        store,
        rows,
        1,
        PlanningEventKind.REGRESSION_COMPLETED,
        regression_payload,
    )
    rows[2] = _rebuild_event(rows[2], parent_event_ids=(rows[1]["event_id"],))
    _write_event_rows(store, rows)
    assert ProjectionFindingCode.REGRESSION_BOARD_DIGEST_MISMATCH in _codes(
        project_planning_history(store)
    )

    store, *_rest, receipts = _chain(tmp_path / "regression-binding")
    rows = _event_rows(store)
    frontier_payload = json.loads(
        (store.root / receipts[2].payload_ref.path).read_text(encoding="utf-8")
    )
    frontier_payload["regression_report_digest"] = "wrong-regression-digest"
    _replace_payload(
        store,
        rows,
        2,
        PlanningEventKind.FRONTIER_COMPLETED,
        frontier_payload,
    )
    _write_event_rows(store, rows)
    assert ProjectionFindingCode.FRONTIER_REGRESSION_DIGEST_MISMATCH in _codes(
        project_planning_history(store)
    )

    store, *_rest, receipts = _chain(tmp_path / "state-binding")
    rows = _event_rows(store)
    frontier_payload = json.loads(
        (store.root / receipts[2].payload_ref.path).read_text(encoding="utf-8")
    )
    frontier_payload["state_digest"] = "wrong-state-digest"
    _replace_payload(
        store,
        rows,
        2,
        PlanningEventKind.FRONTIER_COMPLETED,
        frontier_payload,
    )
    _write_event_rows(store, rows)
    assert ProjectionFindingCode.STATE_DIGEST_MISMATCH in _codes(
        project_planning_history(store)
    )
