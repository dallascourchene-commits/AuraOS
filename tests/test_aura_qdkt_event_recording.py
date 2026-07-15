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


def test_recording_is_append_only_idempotent_and_time_bound(tmp_path) -> None:
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
    assert first.payload_ref.created_at == first.event.created_at == 100.0
    assert first.event.node_id == value.observation_id
    assert first.event.measurement_classes == {"legacy_belief": "DERIVED"}


def test_default_timestamp_is_resolved_once_for_sidecar_and_event(tmp_path) -> None:
    receipt = record_qdkt_observation(
        AppendOnlyEventStore(tmp_path / "events"),
        observation(),
        trace_id="trace-1",
        actor_id="aura",
        purpose_digest="purpose-1",
    )
    assert receipt.payload_ref.created_at == receipt.event.created_at


def test_invalid_envelope_and_policy_fail_before_sidecar_write(tmp_path) -> None:
    for suffix, kwargs, pattern in (
        ("trace", {"trace_id": ""}, "trace_id"),
        ("policy", {"policy_scope": "qdkt.execute"}, "policy_scope"),
        ("actor", {"actor_type": "ADMIN"}, "actor_type"),
    ):
        store = AppendOnlyEventStore(tmp_path / suffix)
        arguments = {
            "trace_id": "trace-1",
            "actor_id": "aura",
            "purpose_digest": "purpose-1",
            "created_at": 100.0,
            **kwargs,
        }
        with pytest.raises(ValueError, match=pattern):
            record_qdkt_observation(store, observation(), **arguments)
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


def test_capture_preflight_rejects_before_generator_invocation(tmp_path) -> None:
    class LegacyGenerator:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_epistemic_system_root(self):
            self.calls += 1
            return dict(LEGACY_RESULT)

    for suffix, kwargs, pattern in (
        ("trace", {"trace_id": ""}, "trace_id"),
        ("snapshot", {"source_snapshot": "not-a-snapshot"}, "source_snapshot"),
        ("actor", {"actor_type": "ADMIN"}, "actor_type"),
    ):
        generator = LegacyGenerator()
        arguments = {
            "source_snapshot": SOURCE_SNAPSHOT,
            "trace_id": "trace-1",
            "actor_id": "aura",
            "purpose_digest": "purpose-1",
            "created_at": 100.0,
            **kwargs,
        }
        with pytest.raises(ValueError, match=pattern):
            asyncio.run(
                capture_legacy_qdkt_observation(
                    AppendOnlyEventStore(tmp_path / f"capture-{suffix}"),
                    generator,
                    **arguments,
                )
            )
        assert generator.calls == 0


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


def test_invalid_timestamps_are_rejected_before_write(tmp_path) -> None:
    for index, invalid in enumerate((True, float("nan"), float("inf"), "100")):
        store = AppendOnlyEventStore(tmp_path / f"events-{index}")
        with pytest.raises(ValueError, match="created_at must be a finite number"):
            record_qdkt_observation(
                store,
                observation(),
                trace_id="trace-1",
                actor_id="aura",
                purpose_digest="purpose-1",
                created_at=invalid,
            )
        assert list(store.sidecars_dir.iterdir()) == []
