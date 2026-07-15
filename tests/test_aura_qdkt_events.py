from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from aura_event_contracts import AppendOnlyEventStore
from aura_qdkt_events import (
    QDKTObservation,
    QDKTTruthClass,
    capture_legacy_qdkt_observation,
    record_qdkt_observation,
)

LEGACY_RESULT = {"root": "A1B2C3D4E5F60718", "belief": 6900}
SOURCE_SNAPSHOT = (
    {"path": "alpha.py", "digest": "a" * 64},
    {"path": "beta.py", "digest": "b" * 64},
)


def _observation(**kwargs) -> QDKTObservation:
    return QDKTObservation.from_legacy_result(
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
        **kwargs,
    )


def test_observation_preserves_exact_legacy_result_and_advisory_truth() -> None:
    observation = _observation(
        planning_board_ref="board-1",
        planning_history_ref="history-1",
        continuity_ref="continuity-1",
    )
    assert observation.legacy_result == LEGACY_RESULT
    assert observation.truth_class is QDKTTruthClass.LEGACY_NONDETERMINISTIC_ADVISORY
    assert observation.source_count == 2
    assert observation.proposal_only is True
    assert observation.reproducible is False
    assert observation.qdkt_patch_authority is False


def test_observation_identity_is_deterministic_for_same_exact_snapshot() -> None:
    left = _observation()
    right = _observation()
    assert left == right
    assert left.observation_id == right.observation_id
    assert left.digest == right.digest


def test_observation_rejects_boolean_belief() -> None:
    with pytest.raises(ValueError, match="belief must be an integer"):
        QDKTObservation.from_legacy_result(
            {"root": LEGACY_RESULT["root"], "belief": True},
            source_snapshot=SOURCE_SNAPSHOT,
        )


def test_observation_rejects_malformed_or_extra_legacy_fields() -> None:
    with pytest.raises(ValueError, match="root is malformed"):
        QDKTObservation.from_legacy_result(
            {"root": "abcdef", "belief": 1},
            source_snapshot=SOURCE_SNAPSHOT,
        )
    with pytest.raises(ValueError, match="exactly root and belief"):
        QDKTObservation.from_legacy_result(
            {"root": LEGACY_RESULT["root"], "belief": 1, "extra": 2},
            source_snapshot=SOURCE_SNAPSHOT,
        )


def test_observation_rejects_prohibited_snapshot_field() -> None:
    prohibited_key = "scratch" + "Pad"
    with pytest.raises(ValueError, match="private reasoning field"):
        QDKTObservation.from_legacy_result(
            LEGACY_RESULT,
            source_snapshot={prohibited_key: "hidden"},
        )


def test_observation_from_dict_requires_json_array_inputs() -> None:
    payload = _observation().to_dict()
    payload["nondeterministic_inputs"] = "thermal_reading"

    with pytest.raises(ValueError, match="JSON array"):
        QDKTObservation.from_dict(payload)


def test_observation_rejects_forged_identity_and_authority() -> None:
    observation = _observation()
    with pytest.raises(ValueError, match="observation_id"):
        replace(observation, observation_id="qdkt-observation_forged")
    with pytest.raises(ValueError, match="authority boundary"):
        replace(observation, qdkt_patch_authority=True)
    with pytest.raises(ValueError, match="non-reproducible"):
        replace(observation, reproducible=True)


def test_record_qdkt_observation_is_append_only_and_idempotent(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    observation = _observation()
    first = record_qdkt_observation(
        store,
        observation,
        trace_id="trace-1",
        actor_id="aura",
        purpose_digest="purpose-1",
        created_at=100.0,
    )
    second = record_qdkt_observation(
        store,
        observation,
        trace_id="trace-1",
        actor_id="aura",
        purpose_digest="purpose-1",
        created_at=100.0,
    )
    assert first.appended is True
    assert second.appended is False
    assert first.event == second.event
    assert first.payload_ref.payload_digest == observation.digest
    assert first.event.node_id == observation.observation_id
    assert first.event.measurement_classes == {"legacy_belief": "DERIVED"}


def test_invalid_envelope_fails_before_sidecar_write(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    with pytest.raises(ValueError, match="trace_id"):
        record_qdkt_observation(
            store,
            _observation(),
            trace_id="",
            actor_id="aura",
            purpose_digest="purpose-1",
            created_at=100.0,
        )
    assert list(store.sidecars_dir.iterdir()) == []
    assert not store.events_path.exists()


def test_capture_invokes_legacy_generator_once_and_preserves_result(tmp_path) -> None:
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
