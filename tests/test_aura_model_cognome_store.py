from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_dikwp_router_pipeline import DIKWPEnvelope, DIKWPStage
from aura_model_cognome import (
    ModelCapabilityEdge,
    ModelEndpointIdentity,
    ModelObservation,
    RouteDecision,
    TaskContext,
    stable_digest,
)
from aura_model_cognome_store import ModelCognomeStore, sanitize_for_storage


def test_store_uses_wal_foreign_keys_and_expected_tables(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        status = store.schema_status()
        assert status["journal_mode"] == "wal"
        assert status["foreign_keys"] is True
        assert "model_endpoints" in status["tables"]
        assert "dikwp_envelopes" in status["tables"]
        assert "storage_sync_outbox" in status["tables"]


def test_idempotent_records_and_candidate_capability_gate(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
        store.upsert_endpoint(endpoint)
        context = TaskContext.create(
            objective="localize code",
            purpose_digest=stable_digest({"authority": "human"}),
            required_capability_ids=("aura.agent_arena.bridge",),
            capability_graph_digest="graph",
        )
        assert store.record_task_context(context) == context.task_context_id
        assert store.record_task_context(context) == context.task_context_id
        edge = ModelCapabilityEdge.create(
            profile_id=endpoint.profile_id,
            aura_capability_id="aura.agent_arena.bridge",
            task_bucket="localization",
            support_level="VALIDATED",
            status="VALIDATED",
            evidence_count=3,
            evidence_digest="evidence",
        )
        store.upsert_model_capability_edge(edge)
        candidates = store.query_candidates(context)
        assert [item["profile_id"] for item in candidates] == [endpoint.profile_id]


def test_observation_preserves_none_and_redacts_sensitive_evidence(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="api", requested_model="closed")
        store.upsert_endpoint(endpoint)
        observation = ModelObservation(
            observation_id="obs-1",
            profile_id=endpoint.profile_id,
            input_tokens=None,
            output_tokens=None,
            cost_usd=None,
            extra_evidence={
                "api_key": "sk-abcdefghijklmnop",
                "raw_prompt": "private prompt",
                "note": "Bearer abcdefghijklmnop",
            },
        )
        store.record_observation(observation)
        stored = store.get_observation("obs-1")
        assert stored is not None
        assert stored["input_tokens"] is None
        assert stored["cost_usd"] is None
        encoded = json.dumps(stored)
        assert "abcdefghijklmnop" not in encoded
        assert "private prompt" not in encoded
        assert encoded.count("[REDACTED]") >= 3


def test_route_and_dikwp_records_are_linked(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
        store.upsert_endpoint(endpoint)
        purpose = stable_digest({"authority": "human"})
        context = TaskContext.create(objective="route", purpose_digest=purpose)
        store.record_task_context(context)
        decision = RouteDecision.create(
            task_context_id=context.task_context_id,
            purpose_digest=purpose,
            policy_mode="DIRECT",
            policy_version="shadow-v1",
            selected_profile_ids=(endpoint.profile_id,),
        )
        store.record_route_decision(decision)
        data = DIKWPEnvelope.create(
            correlation_id=decision.route_decision_id,
            stage=DIKWPStage.DATA,
            payload={"route_decision_id": decision.route_decision_id},
        )
        assert store.record_dikwp_envelope(data) == data.envelope_id


def test_legacy_probe_import_is_idempotent_and_behavioral(tmp_path: Path) -> None:
    ledger = tmp_path / "aura_model_probe_ledger.jsonl"
    ledger.write_text(
        json.dumps({
            "provider": "fireworks",
            "model": "glm",
            "role": "WORKER",
            "historical_quality": 0.8,
            "updated_at": "2026-07-01T00:00:00Z",
            "api_key": "sk-should-not-survive",
        }) + "\n" + "not-json\n",
        encoding="utf-8",
    )
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        first = store.import_legacy_model_probe_ledger(ledger)
        second = store.import_legacy_model_probe_ledger(ledger)
        assert first["imported"] == 1
        assert first["skipped"] == 1
        assert second["already_imported"] is True
        rows = store._conn.execute("SELECT record_json FROM model_observations").fetchall()
        assert len(rows) == 1
        assert "BEHAVIORAL_SURROGATE" in rows[0][0]
        assert "should-not-survive" not in rows[0][0]


def test_idempotency_conflict_is_rejected(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
        store.upsert_endpoint(endpoint)
        first = TaskContext(
            task_context_id="same",
            objective_hash="one",
            purpose_digest="p",
        )
        second = TaskContext(
            task_context_id="same",
            objective_hash="two",
            purpose_digest="p",
        )
        store.record_task_context(first)
        with pytest.raises(ValueError):
            store.record_task_context(second)


def test_sanitize_for_storage_handles_nested_values() -> None:
    clean = sanitize_for_storage({"nested": {"password": "x"}, "text": "sk-1234567890"})
    assert clean["nested"]["password"] == "[REDACTED]"
    assert clean["text"] == "[REDACTED]"
