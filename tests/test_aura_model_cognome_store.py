from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time

import pytest

from aura_model_cognome import (
    MECHANISTIC_OPEN_WEIGHT,
    ModelCapabilityEdge,
    ModelEndpointIdentity,
    ModelObservation,
    RouteDecision,
    TaskContext,
)
from aura_model_cognome_store import ModelCognomeStore, sanitize_for_storage


def test_store_uses_wal_foreign_keys_and_expected_tables(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        status = store.schema_status()
        assert status["journal_mode"] == "wal"
        assert status["foreign_keys"] is True
        assert status["store_schema_version"] == 2
        assert "model_endpoints" in status["tables"]
        assert "dikwp_envelopes" in status["tables"]
        assert "storage_sync_outbox" in status["tables"]


def test_v1_database_migrates_posterior_primary_key(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at REAL NOT NULL);
        INSERT INTO schema_migrations VALUES (1, 0);
        CREATE TABLE model_endpoints(
          profile_id TEXT PRIMARY KEY, provider TEXT, requested_model TEXT, returned_model TEXT,
          base_url_digest TEXT, access_class TEXT, endpoint_fingerprint TEXT,
          fingerprint_version TEXT, provider_revision TEXT, tokenizer_family TEXT,
          price_snapshot_digest TEXT, first_seen_at REAL, last_seen_at REAL, status TEXT,
          record_json TEXT, updated_at REAL
        );
        CREATE TABLE capability_posteriors(
          profile_id TEXT, task_bucket TEXT, context_bucket TEXT, verifier_id TEXT,
          sample_count INTEGER, verified_success_alpha REAL, verified_success_beta REAL,
          evidence_digest TEXT, status TEXT, last_validated_at REAL, record_json TEXT,
          PRIMARY KEY(profile_id, task_bucket, context_bucket, verifier_id)
        );
    """)
    conn.commit(); conn.close()
    with ModelCognomeStore(db_path=path) as store:
        info = store._conn.execute("PRAGMA table_info(capability_posteriors)").fetchall()
        pk = [row[1] for row in sorted(info, key=lambda row: row[5]) if row[5] > 0]
        assert pk[-1] == "validation_split"


def test_candidate_gate_is_task_and_graph_conditioned(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
        store.upsert_endpoint(endpoint)
        edge = ModelCapabilityEdge.create(
            profile_id=endpoint.profile_id,
            aura_capability_id="aura.agent_arena.bridge",
            task_bucket="localization",
            support_level="VALIDATED",
            status="VALIDATED",
            evidence_count=3,
            evidence_digest="evidence",
            capability_graph_digest="graph-1",
            last_validated_at=time.time(),
        )
        store.upsert_model_capability_edge(edge)
        matching = TaskContext.create(
            objective="localize code", purpose_digest="purpose",
            task_family="localization",
            required_capability_ids=("aura.agent_arena.bridge",),
            capability_graph_digest="graph-1",
        )
        wrong_task = TaskContext.create(
            objective="review code", purpose_digest="purpose",
            task_family="review",
            required_capability_ids=("aura.agent_arena.bridge",),
            capability_graph_digest="graph-1",
        )
        stale_graph = TaskContext.create(
            objective="localize other", purpose_digest="purpose",
            task_family="localization",
            required_capability_ids=("aura.agent_arena.bridge",),
            capability_graph_digest="graph-2",
        )
        assert [item["profile_id"] for item in store.query_candidates(matching)] == [endpoint.profile_id]
        assert store.query_candidates(wrong_task) == []
        assert store.query_candidates(stale_graph) == []


def test_validated_edge_requires_real_evidence_and_graph_digest(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
        store.upsert_endpoint(endpoint)
        edge = ModelCapabilityEdge.create(
            profile_id=endpoint.profile_id,
            aura_capability_id="aura.agent_arena.bridge",
            task_bucket="localization",
            support_level="VALIDATED",
            status="VALIDATED",
        )
        with pytest.raises(ValueError, match="evidence"):
            store.upsert_model_capability_edge(edge)


def test_black_box_mechanistic_observation_is_rejected_at_storage_boundary(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="api", requested_model="closed")
        store.upsert_endpoint(endpoint)
        observation = ModelObservation.create(
            profile_id=endpoint.profile_id,
            evidence_class=MECHANISTIC_OPEN_WEIGHT,
        )
        with pytest.raises(ValueError, match="OPEN_WEIGHT"):
            store.record_observation(observation)


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


def test_route_purpose_and_observation_links_are_enforced(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
        store.upsert_endpoint(endpoint)
        context = TaskContext.create(objective="route", purpose_digest="purpose")
        store.record_task_context(context)
        bad = RouteDecision.create(
            task_context_id=context.task_context_id,
            purpose_digest="other",
            policy_mode="DIRECT",
            policy_version="shadow-v1",
        )
        with pytest.raises(ValueError, match="purpose_digest"):
            store.record_route_decision(bad)


def test_posterior_updates_require_verifier_linkage_and_preserve_splits(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
        store.upsert_endpoint(endpoint)
        context = TaskContext.create(
            objective="verify", purpose_digest="purpose",
            task_family="coding", verifier_id="pytest", context_tokens=100,
        )
        store.record_task_context(context)
        observation = ModelObservation.create(
            profile_id=endpoint.profile_id,
            task_context_id=context.task_context_id,
            verifier_pass=True,
            created_at=10,
        )
        store.record_observation(observation)
        train = store.update_posterior(observation.observation_id, validation_split="TRAIN")
        shadow = store.update_posterior(observation.observation_id, validation_split="SHADOW")
        assert train["validation_split"] == "TRAIN"
        assert shadow["validation_split"] == "SHADOW"
        count = store._conn.execute("SELECT COUNT(*) FROM capability_posteriors").fetchone()[0]
        assert count == 2


def test_drift_quarantines_endpoint_and_candidate_query_excludes_it(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="api", requested_model="alias")
        store.upsert_endpoint(endpoint)
        store.record_drift_event({
            "profile_id": endpoint.profile_id,
            "reference_fingerprint": endpoint.endpoint_fingerprint,
            "current_fingerprint": "changed",
            "drift_score": 1.0,
            "status": "QUARANTINED",
            "created_at": 10,
        })
        assert store.get_endpoint(endpoint.profile_id)["status"] == "QUARANTINED"
        context = TaskContext.create(objective="task", purpose_digest="p")
        assert store.query_candidates(context) == []


def test_legacy_probe_import_is_idempotent_and_behavioral(tmp_path: Path) -> None:
    ledger = tmp_path / "aura_model_probe_ledger.jsonl"
    ledger.write_text(
        json.dumps({
            "provider": "fireworks", "model": "glm", "role": "WORKER",
            "historical_quality": 0.8, "updated_at": "2026-07-01T00:00:00Z",
            "api_key": "sk-should-not-survive",
        }) + "\nnot-json\n",
        encoding="utf-8",
    )
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        first = store.import_legacy_model_probe_ledger(ledger)
        second = store.import_legacy_model_probe_ledger(ledger)
        assert first["imported"] == 1 and first["skipped"] == 1
        assert second["already_imported"] is True
        row = store._conn.execute("SELECT record_json FROM model_observations").fetchone()[0]
        assert "BEHAVIORAL_SURROGATE" in row
        assert "should-not-survive" not in row


def test_export_import_bundle_round_trip(tmp_path: Path) -> None:
    source_db = tmp_path / "source.db"
    bundle = tmp_path / "bundle.json"
    with ModelCognomeStore(db_path=source_db) as source:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="qwen")
        source.upsert_endpoint(endpoint)
        context = TaskContext.create(objective="route", purpose_digest="purpose")
        source.record_task_context(context)
        source.export_bundle(bundle)
    with ModelCognomeStore(db_path=tmp_path / "target.db") as target:
        result = target.import_bundle(bundle)
        assert result["ok"] is True
        assert target.get_endpoint(endpoint.profile_id) is not None


def test_outbox_is_idempotent_and_can_be_marked_synced(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        first = store.enqueue_sync_event("endpoint", "p", {"x": 1})
        second = store.enqueue_sync_event("endpoint", "p", {"x": 1})
        assert first == second
        store.mark_outbox_synced(first, synced_at=10)
        row = store._conn.execute(
            "SELECT status, synced_at FROM storage_sync_outbox WHERE outbox_id=?", (first,)
        ).fetchone()
        assert tuple(row) == ("SYNCED", 10.0)


def test_paired_live_experiment_requires_approval(tmp_path: Path) -> None:
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        with pytest.raises(ValueError, match="approval"):
            store.record_experiment_comparison({"measurement_mode": "PAIRED_LIVE"})
        comparison_id = store.record_experiment_comparison({
            "measurement_mode": "PAIRED_LIVE", "approved_live": True,
        })
        assert comparison_id.startswith("comparison_")


def test_sanitize_for_storage_handles_nested_and_multiple_secret_formats() -> None:
    clean = sanitize_for_storage({
        "nested": {"password": "x"},
        "openai": "sk-1234567890",
        "github": "ghp_abcdefghijklmnopqrstuvwxyz123456",
        "scratchpad": {"internal_scratchpad": "secret thought"},
    })
    encoded = json.dumps(clean)
    assert "secret thought" not in encoded
    assert "ghp_" not in encoded
    assert encoded.count("[REDACTED]") >= 4
