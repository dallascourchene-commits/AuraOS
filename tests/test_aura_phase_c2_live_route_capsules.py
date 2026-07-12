"""Phase C2 integration tests for guarded live route capsules."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3

from aura_arena_experience import build_arena_experience
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_arena_wfst_compiler import compile_arena_grammar
from aura_arena_wfst_runtime import ArenaWFSTRuntime
from aura_coding_workbench_actions import localize_code

REPO = Path(__file__).resolve().parents[1]
CODING_MANIFEST = REPO / ".aura" / "arena_routes" / "coding.v1.json"


def test_compiler_requires_paired_capsule_references():
    manifest = {
        "schema_version": "AURA_ARENA_GRAMMAR_MANIFEST_V1",
        "arena_id": "x", "arena_version": "v1", "grammar_version": "g1",
        "start_state": "A", "states": ["A", "B"],
        "transitions": [{
            "transition_id": "X.GO", "from_state": "A", "next_state": "B",
            "output_symbol": "GO", "morphology_profile_ref": ".aura/morphology_profiles/six_slot.v1.json",
        }],
    }
    result = compile_arena_grammar(manifest)
    assert result.ok is False
    assert any(item.code == "incomplete_route_capsule_reference" for item in result.diagnostics)


def test_live_capsule_materializes_only_after_hard_guard():
    runtime = ArenaWFSTRuntime(repo_root=REPO)
    report = runtime.register_manifest(CODING_MANIFEST)
    assert report["ok"], report
    blocked = runtime.route(
        arena_id="coding_workbench", current_state="TASK_SCOPED",
        input_text="localize_code", evidence={}, context={"objective": "find runtime"},
        policy={"route_capsules_enabled": True},
    )
    assert blocked["selected"] is None
    row = next(item for item in blocked["blocked"] if item["transition_id"] == "CODING.TASK_SCOPED.LOCALIZE_CODE")
    assert row["failed_guards"]
    assert not row.get("route_capsule")

    admitted = runtime.route(
        arena_id="coding_workbench", current_state="TASK_SCOPED",
        input_text="localize_code", evidence={"objective": "find runtime"},
        context={"objective": "find runtime"}, policy={"route_capsules_enabled": True},
    )
    selected = admitted["selected"]
    assert selected["transition_id"] == "CODING.TASK_SCOPED.LOCALIZE_CODE"
    assert selected["route_capsule"]["capsule_id"] == "CODING.LOCALIZE.V1"
    assert selected["route_capsule"]["runtime_authority"] == "bounded_after_hard_guards"
    assert selected["capsule_resonance"] is not None
    assert selected["route_capsule"]["automatic_activation"] is False


def test_feature_flag_disables_materialization_without_blocking_transition():
    runtime = ArenaWFSTRuntime(repo_root=REPO)
    assert runtime.register_manifest(CODING_MANIFEST)["ok"]
    route = runtime.route(
        arena_id="coding_workbench", current_state="TASK_SCOPED",
        input_text="localize_code", evidence={"objective": "find runtime"},
        context={"objective": "find runtime"}, policy={"route_capsules_enabled": False},
    )
    assert route["selected"]["route_capsule"] is None
    assert route["selected"]["route_capsule_status"] == "disabled"


def test_experience_captures_capsule_and_actual_usage():
    runtime = ArenaWFSTRuntime(repo_root=REPO)
    report = runtime.register_manifest(CODING_MANIFEST)
    route = runtime.route(
        arena_id="coding_workbench", current_state="TASK_SCOPED",
        input_text="localize_code", evidence={"objective": "find runtime"},
        context={"objective": "find runtime"}, policy={"route_capsules_enabled": True},
    )
    usage = {
        "actual_context_items": ["aura_arena_wfst_runtime.py"],
        "actual_tool_calls": ["tool:topology_inspector"],
        "actual_model": "",
        "budget_consumed": {"retrieved_files": 1},
    }
    experience = build_arena_experience(
        arena_id="coding_workbench", arena_version="v1", grammar_version="g1",
        grammar_manifest_digest=report["manifest_digest"], runtime_version="r", compiler_version="c",
        state_before="TASK_SCOPED", state_after="CODE_LOCALIZED",
        selected_transition="CODING.TASK_SCOPED.LOCALIZE_CODE", final_outcome="COMPLETED",
        payload={"route": route, "action_result": {"route_capsule_usage": usage}},
    )
    observation = experience.route_capsule_observation
    assert observation["capsule_id"] == "CODING.LOCALIZE.V1"
    assert observation["actual_context_items"] == ["aura_arena_wfst_runtime.py"]
    assert observation["actual_tool_calls"] == ["tool:topology_inspector"]
    assert observation["budget_requested"]["input_tokens"] == 6000
    assert experience.route_capsule_observation_digest


def test_v2_database_migrates_and_persists_capsule_observation(tmp_path):
    db = tmp_path / "legacy.db"
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE arena_experiences (experience_id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL, task_id TEXT, workflow_id TEXT, arena_id TEXT NOT NULL, arena_version TEXT NOT NULL, grammar_version TEXT NOT NULL, grammar_manifest_digest TEXT NOT NULL DEFAULT '', runtime_version TEXT NOT NULL, compiler_version TEXT NOT NULL, started_at REAL NOT NULL, completed_at REAL NOT NULL, state_before TEXT NOT NULL, state_after TEXT NOT NULL, selected_transition TEXT, final_outcome TEXT NOT NULL, outcome_vector_json TEXT NOT NULL DEFAULT '{}', admissible_alternatives_json TEXT NOT NULL DEFAULT '[]', predictions_json TEXT NOT NULL DEFAULT '[]', route_observation_digest TEXT NOT NULL DEFAULT '', repository_commit_sha TEXT, working_tree_digest TEXT, objective_hash TEXT, source_hash_digest TEXT, provider TEXT, model TEXT, measurement_class TEXT, cost_run_id TEXT, trace_atom_ids_json TEXT NOT NULL, raw_evidence_refs_json TEXT NOT NULL, redactions_json TEXT NOT NULL, payload_json TEXT NOT NULL, experience_digest TEXT NOT NULL, schema_version TEXT NOT NULL, created_at REAL NOT NULL)")
    connection.execute("CREATE TABLE arena_experience_migrations(version INTEGER PRIMARY KEY, applied_at REAL NOT NULL)")
    connection.commit(); connection.close()
    with ArenaExperienceLedger(tmp_path, db_path=db) as ledger:
        columns = {row[1] for row in ledger._conn.execute("PRAGMA table_info(arena_experiences)")}
        assert "route_capsule_observation_json" in columns
        assert "route_capsule_observation_digest" in columns
        assert ledger.status()["schema_version"] == 3


def test_localization_aperture_clamps_outputs(monkeypatch, tmp_path):
    aperture = tmp_path / ".aura" / "data_apertures" / "coding_localize.v1.json"
    aperture.parent.mkdir(parents=True)
    aperture.write_text(json.dumps({"maximum_files": 2, "maximum_symbols": 3, "maximum_lines": 40, "allow_unbounded_repository_context": False}), encoding="utf-8")
    import aura_code_region_ranker
    monkeypatch.setattr(aura_code_region_ranker, "rank_code_regions", lambda *a, **k: {
        "files": ["a", "b", "c"], "symbols": ["s1", "s2", "s3", "s4"],
        "line_ranges": ["1:10", "11:20"],
    })
    monkeypatch.setenv("AURA_ROUTE_CAPSULES_ENABLED", "1")
    result = localize_code("objective", repo_root=tmp_path)
    assert result["localized_files"] == ["a", "b"]
    assert result["localized_symbols"] == ["s1", "s2", "s3"]
    assert result["route_capsule_usage"]["data_aperture_enforced"] is True
    assert result["route_capsule_usage"]["budget_consumed"]["retrieved_files"] == 2
