"""Phase C2 tests for opt-in live capsule routing and experience provenance."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from aura_arena_experience import ARENA_EXPERIENCE_VERSION, build_arena_experience
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_arena_wfst_types import ArenaTransition
from aura_route_capsule_compiler import compile_route_capsule
from aura_route_capsule_live_runtime import CapsuleAwareArenaWFSTRuntime
from aura_route_capsule_materializer import materialize_route_capsule

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPSULE_REF = ".aura/route_capsules/coding_localize.v1.json"
TRANSITION_ID = "CODING.TASK_SCOPED.LOCALIZE_CODE"
LEASE = "tool:topology_inspector"


def _runtime(*, enabled: bool) -> CapsuleAwareArenaWFSTRuntime:
    runtime = CapsuleAwareArenaWFSTRuntime(
        repo_root=REPO_ROOT,
        route_capsules_enabled=enabled,
    )
    coding = runtime.register_manifest(REPO_ROOT / ".aura/arena_routes/coding.v1.json")
    meta = runtime.register_manifest(REPO_ROOT / ".aura/arena_routes/meta.v1.json")
    assert coding["ok"], coding
    assert meta["ok"], meta
    attached = runtime.attach_capsule(
        arena_id="coding_workbench",
        transition_id=TRANSITION_ID,
        route_capsule_ref=CAPSULE_REF,
        morphology_profile_ref=".aura/morphology_profiles/six_slot.v1.json",
        feature_flag="c2_coding_localization_enabled",
    )
    assert attached["ok"], attached
    return runtime


def _route(runtime: CapsuleAwareArenaWFSTRuntime, *, lease: bool, enabled: bool):
    return runtime.route(
        arena_id="coding_workbench",
        current_state="TASK_SCOPED",
        input_text="localize code",
        evidence={"objective": "Find the route capsule runtime"},
        context={
            "objective": "Find the route capsule runtime",
            "lease_capabilities": [LEASE] if lease else [],
            "requested_model": "no_model",
        },
        policy={
            "route_capsules_enabled": enabled,
            "c2_coding_localization_enabled": enabled,
            "grounding_class": "exact_source_hashes",
        },
    )


def test_transition_contract_carries_optional_capsule_references():
    transition = ArenaTransition.from_dict(
        {
            "transition_id": "T",
            "from_state": "A",
            "next_state": "B",
            "output_symbol": "OUT",
            "morphology_profile_ref": ".aura/morphology_profiles/six_slot.v1.json",
            "route_capsule_ref": CAPSULE_REF,
            "capsule_feature_flag": "c2_enabled",
        },
        arena_id="test",
        grammar_version="v1",
    )
    packet = transition.to_dict()
    assert packet["route_capsule_ref"] == CAPSULE_REF
    assert packet["capsule_feature_flag"] == "c2_enabled"


def test_declarative_capsule_reference_compiles_during_manifest_registration(tmp_path):
    payload = json.loads((REPO_ROOT / ".aura/arena_routes/coding.v1.json").read_text())
    target = next(row for row in payload["transitions"] if row["transition_id"] == TRANSITION_ID)
    target.update({
        "route_capsule_ref": CAPSULE_REF,
        "morphology_profile_ref": ".aura/morphology_profiles/six_slot.v1.json",
        "capsule_feature_flag": "c2_coding_localization_enabled",
    })
    manifest = tmp_path / "coding.c2.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    runtime = CapsuleAwareArenaWFSTRuntime(repo_root=REPO_ROOT, route_capsules_enabled=True)
    report = runtime.register_manifest(manifest)
    assert report["ok"], report
    assert report["capsule_attachments"][0]["capsule_id"] == "CODING.LOCALIZE.V1"


def test_materializer_requires_feature_flag_and_explicit_lease():
    result = compile_route_capsule(CAPSULE_REF, repo_root=REPO_ROOT)
    assert result.ok, [item.to_dict() for item in result.diagnostics]
    disabled = materialize_route_capsule(result.compiled, repo_root=REPO_ROOT, policy={})
    assert disabled["reason"] == "route_capsule_feature_disabled"
    unleased = materialize_route_capsule(
        result.compiled,
        repo_root=REPO_ROOT,
        policy={"route_capsules_enabled": True},
        context={},
    )
    assert unleased["reason"] == "capsule_lease_missing_capability"


def test_materializer_enforces_pinned_budget_and_bounded_context():
    result = compile_route_capsule(CAPSULE_REF, repo_root=REPO_ROOT)
    context = {
        "lease_capabilities": [LEASE],
        "requested_model": "no_model",
        "capsule_context_items": [
            {"path": f"file_{index}.py", "symbol": f"s{index}", "line_count": 100}
            for index in range(10)
        ],
        "capsule_budget_consumed": {"tool_calls": 1, "model_calls": 0},
    }
    materialized = materialize_route_capsule(
        result.compiled,
        repo_root=REPO_ROOT,
        policy={"route_capsules_enabled": True},
        context=context,
    )
    assert materialized["ok"]
    packet = materialized["materialized"]
    assert len(packet["actual_context_items"]) <= packet["data_aperture"]["maximum_files"]
    assert packet["automatic_activation"] is False

    context["capsule_budget_consumed"] = {"tool_calls": 999}
    denied = materialize_route_capsule(
        result.compiled,
        repo_root=REPO_ROOT,
        policy={"route_capsules_enabled": True},
        context=context,
    )
    assert denied["reason"] == "capsule_budget_exceeded"


def test_base_hard_guard_blocks_before_capsule_materialization():
    runtime = _runtime(enabled=True)
    route = runtime.route(
        arena_id="coding_workbench",
        current_state="TASK_SCOPED",
        input_text="localize code",
        evidence={},
        context={"lease_capabilities": [LEASE]},
        policy={
            "route_capsules_enabled": True,
            "c2_coding_localization_enabled": True,
        },
    )
    assert route["selected"] is None
    blocked = next(item for item in route["blocked"] if item["transition_id"] == TRANSITION_ID)
    assert blocked.get("capsule_blocked") is not True
    assert blocked["failed_guards"][0]["guard_id"] == "GUARD.EVIDENCE_ALL"


def test_feature_disabled_preserves_legacy_selection():
    route = _route(_runtime(enabled=False), lease=False, enabled=False)
    assert route["selected"]["transition_id"] == TRANSITION_ID
    assert route["selected"]["route_capsule"]["status"] == "feature_disabled"
    assert route["automatic_capsule_activation"] is False


def test_enabled_exact_transition_fails_closed_without_capsule_lease():
    route = _route(_runtime(enabled=True), lease=False, enabled=True)
    assert route["selected"] is None
    assert route["abstained"] is True
    assert route["abstention_reason"] == "exact_transition_blocked_by_capsule"
    blocked = next(item for item in route["blocked"] if item["transition_id"] == TRANSITION_ID)
    assert blocked["capsule_blocked"] is True


def test_enabled_route_materializes_only_after_base_admission():
    route = _route(_runtime(enabled=True), lease=True, enabled=True)
    selected = route["selected"]
    assert selected["transition_id"] == TRANSITION_ID
    assert selected["route_capsule"]["status"] == "materialized"
    assert selected["route_capsule"]["routing_authority"] == "advisory_after_hard_guards"
    assert selected["materialized_aperture"]["runtime_execution_performed"] is False
    assert route["intent_packet"]["packet_digest"] == selected["intent_packet_digest"]


def test_experience_and_ledger_capture_capsule_provenance(tmp_path):
    route = _route(_runtime(enabled=True), lease=True, enabled=True)
    usage = {
        "context_items": [{"path": "aura_route_capsule_live_runtime.py", "source_hash": "abc"}],
        "tool_calls": ["aura_code_region_ranker.rank_code_regions"],
        "model": "no_model",
        "budget_consumed": {"tool_calls": 1, "model_calls": 0},
    }
    experience = build_arena_experience(
        arena_id="coding_workbench",
        arena_version="v1",
        grammar_version="g1",
        runtime_version="c2",
        compiler_version="compiler",
        state_before="TASK_SCOPED",
        state_after="CODE_LOCALIZED",
        selected_transition=TRANSITION_ID,
        final_outcome="COMPLETED",
        payload={"route": route, "capsule_usage": usage},
    )
    assert experience.version == ARENA_EXPERIENCE_VERSION
    assert experience.intent_packet_digest
    assert experience.vsa_profile_digest
    assert experience.route_capsule_digest
    assert experience.aperture_digest
    assert experience.actual_tool_calls == ("aura_code_region_ranker.rank_code_regions",)
    assert experience.budget_consumed["tool_calls"] == 1

    with ArenaExperienceLedger(tmp_path, db_path=tmp_path / "arena.db") as ledger:
        recorded = ledger.record(experience)
        assert recorded["ok"]
        row = ledger.get(experience.experience_id)
        assert row["route_capsule_digest"] == experience.route_capsule_digest
        assert row["actual_tool_calls"] == ["aura_code_region_ranker.rank_code_regions"]
        status = ledger.status()
        assert status["schema_version"] == 4
        assert status["v2_complete_record_count"] == 1
        assert status["v3_complete_record_count"] == 1
        assert status["capsule_record_count"] == 1


def test_v2_database_migrates_without_inventing_capsule_provenance(tmp_path):
    db_path = tmp_path / "legacy-v2.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE arena_experiences (
         experience_id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL, task_id TEXT, workflow_id TEXT,
         arena_id TEXT NOT NULL, arena_version TEXT NOT NULL, grammar_version TEXT NOT NULL,
         grammar_manifest_digest TEXT NOT NULL DEFAULT '', runtime_version TEXT NOT NULL, compiler_version TEXT NOT NULL,
         started_at REAL NOT NULL, completed_at REAL NOT NULL, state_before TEXT NOT NULL, state_after TEXT NOT NULL,
         selected_transition TEXT, final_outcome TEXT NOT NULL, outcome_vector_json TEXT NOT NULL DEFAULT '{}',
         admissible_alternatives_json TEXT NOT NULL DEFAULT '[]', predictions_json TEXT NOT NULL DEFAULT '[]',
         route_observation_digest TEXT NOT NULL DEFAULT '', repository_commit_sha TEXT, working_tree_digest TEXT,
         objective_hash TEXT, source_hash_digest TEXT, provider TEXT, model TEXT, measurement_class TEXT, cost_run_id TEXT,
         trace_atom_ids_json TEXT NOT NULL, raw_evidence_refs_json TEXT NOT NULL, redactions_json TEXT NOT NULL,
         payload_json TEXT NOT NULL, experience_digest TEXT NOT NULL, schema_version TEXT NOT NULL, created_at REAL NOT NULL);
        CREATE TABLE arena_experience_migrations(version INTEGER PRIMARY KEY, applied_at REAL NOT NULL);
        INSERT INTO arena_experiences (
         experience_id, correlation_id, task_id, workflow_id, arena_id, arena_version, grammar_version,
         grammar_manifest_digest, runtime_version, compiler_version, started_at, completed_at,
         state_before, state_after, selected_transition, final_outcome, outcome_vector_json,
         admissible_alternatives_json, predictions_json, route_observation_digest,
         trace_atom_ids_json, raw_evidence_refs_json, redactions_json, payload_json,
         experience_digest, schema_version, created_at
        ) VALUES (
         'legacy-v2-experience-001', 'corr-001', 'task-001', 'workflow-001', 'coding_workbench',
         'v1', 'g1', 'manifest-digest', 'runtime-v1', 'compiler-v1', 1000.0, 1001.0,
         'TASK_SCOPED', 'CODE_LOCALIZED', 'CODING.TASK_SCOPED.LOCALIZE_CODE', 'COMPLETED',
         '{}', '[]', '[]', 'route-digest', '[]', '[]', '[]', '{"test": "legacy"}',
         'exp-digest', 'AURA_ARENA_EXPERIENCE_V2', 1000.0
        );
        """
    )
    connection.commit()
    connection.close()

    with ArenaExperienceLedger(tmp_path, db_path=db_path) as ledger:
        columns = {
            row[1] for row in ledger._conn.execute("PRAGMA table_info(arena_experiences)")
        }
        assert "route_capsule_digest" in columns
        assert "budget_consumed_json" in columns
        assert ledger.status()["capsule_record_count"] == 0

        legacy_row = ledger._conn.execute(
            "SELECT route_capsule_digest, aperture_digest FROM arena_experiences WHERE experience_id = ?",
            ("legacy-v2-experience-001",)
        ).fetchone()
        assert legacy_row is not None
        assert legacy_row[0] in ("", None)
        assert legacy_row[1] in ("", None)
