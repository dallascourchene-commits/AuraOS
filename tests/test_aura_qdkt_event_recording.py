from __future__ import annotations

import asyncio

import pytest

from aura_event_contracts import AppendOnlyEventStore
from aura_qdkt_observations import (
    QDKTObservation,
    capture_legacy_qdkt_observation,
    record_qdkt_observation,
)

LEGACY_RESULT = {"root": "A1B2C3D4E5F60718", "belief": 6900}
SOURCE_SNAPSHOT = (
    {"path": "alpha.py", "digest": "a" * 64},
    {"path": "beta.py", "digest": "b" * 64},
)


def observation() -> QDKTObservation:
    return QDKTObservation.from_legacy_result(
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )


def test_recording_is_append_only_and_idempotent(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    value = observation()
    first = record_qdkt_observation(
        store,
        value,
        trace_id="trace-1",
        actor_id="aura",
        purpose_digest="purpose-1",
        created_at=100.0,
    )
    second = record_qdkt_observation(
        store,
        value,
        trace_id="trace-1",
        actor_id="aura",
        purpose_digest="purpose-1",
        created_at=100.0,
    )
    assert first.appended is True
    assert second.appended is False
    assert first.event == second.event
    assert first.payload_ref.payload_digest == value.digest
    assert first.payload_ref.redacted is False
    assert first.event.node_id == value.observation_id
    assert first.event.measurement_classes == {"legacy_belief": "DERIVED"}


def test_invalid_envelope_fails_before_sidecar_write(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    with pytest.raises(ValueError, match="trace_id"):
        record_qdkt_observation(
            store,
            observation(),
            trace_id="",
            actor_id="aura",
            purpose_digest="purpose-1",
            created_at=100.0,
        )
    assert list(store.sidecars_dir.iterdir()) == []
    assert not store.events_path.exists()


def test_capture_calls_legacy_generator_once_and_preserves_result(tmp_path) -> None:
    class LegacyGenerator:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_epistemic_system_root(self):
            self.calls += 1
            return dict(LEGACY_RESULT)

    generator = LegacyGenerator()
    receipt = asyncio.run(
        capture_legacy_qdkt_observation(
            AppendOnlyEventStore(tmp_path / "events"),
            generator,
            source_snapshot=SOURCE_SNAPSHOT,
            trace_id="trace-1",
            actor_id="aura",
            purpose_digest="purpose-1",
            created_at=100.0,
        )
    )
    assert generator.calls == 1
    assert receipt.observation.legacy_result == LEGACY_RESULT


def test_capture_rejects_invalid_generator_surface(tmp_path) -> None:
    with pytest.raises(ValueError, match="generate_epistemic_system_root"):
        asyncio.run(
            capture_legacy_qdkt_observation(
                AppendOnlyEventStore(tmp_path / "events"),
                object(),
                source_snapshot=SOURCE_SNAPSHOT,
                trace_id="trace-1",
                actor_id="aura",
                purpose_digest="purpose-1",
                created_at=100.0,
            )
        )


def test_nonfinite_timestamp_is_rejected_before_write(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    with pytest.raises(ValueError, match="created_at must be finite"):
        record_qdkt_observation(
            store,
            observation(),
            trace_id="trace-1",
            actor_id="aura",
            purpose_digest="purpose-1",
            created_at=float("nan"),
        )
    assert list(store.sidecars_dir.iterdir()) == []
