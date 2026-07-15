from __future__ import annotations

import json

from aura_event_contracts import (
    ActorType,
    AppendOnlyEventStore,
    AuraEventEnvelope,
    DIKWPStage,
)
from aura_qdkt_observations import QDKTObservation, record_qdkt_observation
from aura_qdkt_projection import project_qdkt_events
from aura_qdkt_projection_types import QDKTProjectionFindingCode

LEGACY_RESULT = {"root": "A1B2C3D4E5F60718", "belief": 6900}
SOURCE_SNAPSHOT = (
    {"path": "alpha.py", "digest": "a" * 64},
    {"path": "beta.py", "digest": "b" * 64},
)


def observation(**kwargs) -> QDKTObservation:
    return QDKTObservation.from_legacy_result(
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
        **kwargs,
    )


def record(store: AppendOnlyEventStore, **kwargs):
    return record_qdkt_observation(
        store,
        kwargs.pop("observation", observation()),
        trace_id="trace-1",
        actor_id="aura",
        purpose_digest="purpose-1",
        created_at=kwargs.pop("created_at", 100.0),
        **kwargs,
    )


def codes(report) -> set[QDKTProjectionFindingCode]:
    return {finding.code for finding in report.findings}


def parent_event(created_at: float = 90.0) -> AuraEventEnvelope:
    return AuraEventEnvelope.create(
        trace_id="trace-parent",
        event_type="test.parent",
        actor_id="verifier",
        actor_type=ActorType.VERIFIER,
        purpose_digest="purpose-parent",
        dikwp_stage=DIKWPStage.DATA,
        payload_ref="payload-parent",
        payload_digest="digest-parent",
        proposal_only=True,
        created_at=created_at,
    )


def test_valid_projection_is_complete_and_read_only(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    before_events = store.events_path.read_bytes()
    sidecar = store.root / receipt.payload_ref.path
    before_sidecar = sidecar.read_bytes()

    report = project_qdkt_events(store)

    assert report.integrity_complete is True
    assert report.qdkt_event_count == 1
    assert report.ignored_non_qdkt_events == 0
    assert report.events[0].observation_id == receipt.observation.observation_id
    assert store.events_path.read_bytes() == before_events
    assert sidecar.read_bytes() == before_sidecar


def test_non_qdkt_event_is_ignored(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    store.append(parent_event())
    record(store)

    report = project_qdkt_events(store)

    assert report.integrity_complete is True
    assert report.qdkt_event_count == 1
    assert report.ignored_non_qdkt_events == 1


def test_exact_duplicate_event_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)
    line = store.events_path.read_text(encoding="utf-8")
    with store.events_path.open("a", encoding="utf-8") as handle:
        handle.write(line)

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.DUPLICATE_EVENT_ID in codes(report)
    assert report.integrity_complete is False


def test_single_line_noncanonical_json_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    line = json.dumps(receipt.event.to_dict(), separators=(", ", ": "))
    store.events_path.write_text(line + "\n", encoding="utf-8")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.NONCANONICAL_EVENT_RECORD in codes(report)


def test_missing_terminal_newline_is_reported_but_row_is_read(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)
    text = store.events_path.read_text(encoding="utf-8")
    store.events_path.write_text(text.removesuffix("\n"), encoding="utf-8")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.NONCANONICAL_EVENT_RECORD in codes(report)
    assert report.qdkt_event_count == 1
    assert report.integrity_complete is False


def test_injected_blank_row_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)
    with store.events_path.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.NONCANONICAL_EVENT_RECORD in codes(report)
    assert report.integrity_complete is False


def test_missing_parent_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store, parent_event_ids=("missing-parent",))

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.MISSING_PARENT in codes(report)


def test_parent_appended_after_child_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    parent = parent_event()
    record(store, parent_event_ids=(parent.event_id,), created_at=100.0)
    store.append(parent)

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.OUT_OF_ORDER in codes(report)


def test_planning_reference_is_not_conflated_with_board_id(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    value = observation(planning_board_ref="payload-ref-for-board")
    record(store, observation=value, board_id="board-domain-id")

    assert project_qdkt_events(store).integrity_complete is True
