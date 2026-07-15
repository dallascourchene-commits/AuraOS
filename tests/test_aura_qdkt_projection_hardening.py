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
SOURCE_SNAPSHOT = ({"path": "alpha.py", "digest": "a" * 64},)


def observation() -> QDKTObservation:
    return QDKTObservation.from_legacy_result(
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )


def record(store: AppendOnlyEventStore):
    return record_qdkt_observation(
        store,
        observation(),
        trace_id="trace-1",
        actor_id="aura",
        purpose_digest="purpose-1",
        created_at=100.0,
    )


def codes(report) -> set[QDKTProjectionFindingCode]:
    return {finding.code for finding in report.findings}


def test_conflicting_duplicate_event_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    conflict = receipt.event.to_dict()
    conflict["actor_id"] = "substituted"
    with store.events_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(conflict) + "\n")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.CONFLICTING_DUPLICATE_EVENT in codes(report)


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


def test_invalid_payload_reference_is_reported(tmp_path) -> None:
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


def test_nonproposal_event_is_reported(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    raw = receipt.event.to_dict()
    changed = AuraEventEnvelope.create(
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
        canonical_json(changed.to_dict()) + "\n", encoding="utf-8"
    )

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.NON_PROPOSAL_EVENT in codes(report)


def test_empty_parent_or_evidence_ref_is_reported_without_throwing(tmp_path) -> None:
    for suffix, parent_refs, evidence_refs in (
        ("parent", ("",), ()),
        ("evidence", (), ("",)),
    ):
        store = AppendOnlyEventStore(tmp_path / suffix)
        receipt = record(store)
        raw = receipt.event.to_dict()
        changed = AuraEventEnvelope.create(
            trace_id=raw["trace_id"],
            parent_event_ids=parent_refs,
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
            evidence_refs=evidence_refs,
            policy_scope=raw["policy_scope"],
            proposal_only=True,
            measurement_classes=raw["measurement_classes"],
            created_at=raw["created_at"],
        )
        store.events_path.write_text(
            canonical_json(changed.to_dict()) + "\n", encoding="utf-8"
        )

        report = project_qdkt_events(store)

        assert QDKTProjectionFindingCode.INVALID_EVENT_RECORD in codes(report)
        assert report.integrity_complete is False


def test_nonfinite_and_duplicate_key_rows_fail_closed(tmp_path) -> None:
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


def test_boolean_timestamp_row_is_rejected(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    raw = receipt.event.to_dict()
    raw["created_at"] = True
    store.events_path.write_text(canonical_json(raw) + "\n", encoding="utf-8")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.ENVELOPE_MISMATCH in codes(report)


def test_integer_timestamp_bytes_do_not_impersonate_float_envelope(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    raw = receipt.event.to_dict()
    raw["created_at"] = 100
    store.events_path.write_text(canonical_json(raw) + "\n", encoding="utf-8")

    report = project_qdkt_events(store)

    assert QDKTProjectionFindingCode.ENVELOPE_MISMATCH in codes(report)
    assert report.integrity_complete is False
