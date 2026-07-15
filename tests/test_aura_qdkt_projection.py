from __future__ import annotations

import json

from aura_event_contracts import (
    ActorType,
    AppendOnlyEventStore,
    AuraEventEnvelope,
    DIKWPStage,
    canonical_json,
)
from aura_qdkt_observations import (
    QDKT_EVENT_TYPE,
    QDKT_POLICY_SCOPE,
    QDKTObservation,
    record_qdkt_observation,
)
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
        trace_id=kwargs.pop("trace_id", "trace-1"),
        actor_id=kwargs.pop("actor_id", "aura"),
        purpose_digest=kwargs.pop("purpose_digest", "purpose-1"),
        created_at=kwargs.pop("created_at", 100.0),
        **kwargs,
    )


def codes(report) -> set[QDKTProjectionFindingCode]:
    return {finding.code for finding in report.findings}


def generic_event(
    *,
    event_type: str = "test.parent",
    created_at: float = 90.0,
    payload_ref: str = "payload-parent",
) -> AuraEventEnvelope:
    return AuraEventEnvelope.create(
        trace_id="trace-parent",
        event_type=event_type,
        actor_id="verifier",
        actor_type=ActorType.VERIFIER,
        purpose_digest="purpose-parent",
        dikwp_stage=DIKWPStage.DATA,
        payload_ref=payload_ref,
        payload_digest="digest-parent",
        proposal_only=True,
        created_at=created_at,
    )


def test_valid_projection_is_complete_and_read_only(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    before_events = store.events_path.read_bytes()
    before_sidecar = (store.root / receipt.payload_ref.path).read_bytes()

    report = project_qdkt_events(store)

    assert report.integrity_complete is True
    assert report.qdkt_event_count == 1
    assert report.ignored_non_qdkt_events == 0
    assert report.events[0].observation_id == receipt.observation.observation_id
    assert store.events_path.read_bytes() == before_events
    assert (store.root / receipt.payload_ref.path).read_bytes() == before_sidecar


def test_non_qdkt_event_is_ignored(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    store.append(generic_event())
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


def test_conflicting_duplicate_event_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    conflict = receipt.event.to_dict()
    conflict["actor_id"] = "substituted"
    with store.events_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(conflict) + "\n")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.CONFLICTING_DUPLICATE_EVENT in codes(report)


def test_noncanonical_event_row_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    noncanonical = json.dumps(receipt.event.to_dict(), sort_keys=False, indent=2)
    store.events_path.write_text(noncanonical + "\n", encoding="utf-8")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.NONCANONICAL_EVENT_RECORD in codes(report)


def test_tampered_sidecar_digest_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    path = store.root / receipt.payload_ref.path
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["legacy_belief"] += 1
    path.write_text(canonical_json(payload), encoding="utf-8")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.PAYLOAD_DIGEST_MISMATCH in codes(report)


def test_nonfinite_sidecar_is_reported_without_throwing(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    path = store.root / receipt.payload_ref.path
    payload = receipt.observation.to_dict()
    payload["legacy_belief"] = float("nan")
    path.write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.MALFORMED_SIDECAR in codes(report)


def test_missing_sidecar_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    (store.root / receipt.payload_ref.path).unlink()

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.MISSING_SIDECAR in codes(report)


def test_unsafe_payload_reference_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    value = observation()
    event = AuraEventEnvelope.create(
        trace_id="trace-1",
        event_type=QDKT_EVENT_TYPE,
        actor_id="aura",
        actor_type=ActorType.AURA,
        node_id=value.observation_id,
        purpose_digest="purpose-1",
        dikwp_stage=DIKWPStage.KNOWLEDGE,
        payload_ref="outside-reference",
        payload_digest=value.digest,
        policy_scope=QDKT_POLICY_SCOPE,
        proposal_only=True,
        measurement_classes={"legacy_belief": "DERIVED"},
        created_at=100.0,
    )
    store.append(event)

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.UNSAFE_PAYLOAD_REF in codes(report)


def test_nonproposal_authority_escalation_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    raw = receipt.event.to_dict()
    escalated = AuraEventEnvelope.create(
        trace_id=raw["trace_id"],
        parent_event_ids=raw["parent_event_ids"],
        event_type=raw["event_type"],
        actor_id=raw["actor_id"],
        actor_type=raw["actor_type"],
        arena_id=raw["arena_id"],
        board_id=raw["board_id"],
        node_id=raw["node_id"],
        objective_id=raw["objective_id"],
        purpose_digest=raw["purpose_digest"],
        dikwp_stage=raw["dikwp_stage"],
        payload_ref=raw["payload_ref"],
        payload_digest=raw["payload_digest"],
        evidence_refs=raw["evidence_refs"],
        policy_scope=raw["policy_scope"],
        proposal_only=False,
        measurement_classes=raw["measurement_classes"],
        created_at=raw["created_at"],
    )
    store.events_path.write_text(
        canonical_json(escalated.to_dict()) + "\n", encoding="utf-8"
    )

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.NON_PROPOSAL_EVENT in codes(report)


def test_missing_parent_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store, parent_event_ids=("missing-parent",))

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.MISSING_PARENT in codes(report)


def test_parent_appended_after_child_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    parent = generic_event(created_at=90.0)
    record(store, parent_event_ids=(parent.event_id,), created_at=100.0)
    store.append(parent)

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.OUT_OF_ORDER in codes(report)


def test_nonfinite_and_duplicate_key_event_rows_fail_closed(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    store.events_path.parent.mkdir(parents=True, exist_ok=True)
    store.events_path.write_text(
        '{"event_type":"qdkt.observation.recorded",'
        '"event_type":"qdkt.observation.recorded","created_at":NaN}\n',
        encoding="utf-8",
    )

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.INVALID_EVENT_RECORD in codes(report)
    assert report.qdkt_event_count == 0


def test_planning_reference_is_not_conflated_with_board_id(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    value = observation(planning_board_ref="payload-ref-for-board")
    record(store, observation=value, board_id="board-domain-id")

    report = project_qdkt_events(store)

    assert report.integrity_complete is True
