from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from aura_arena_crucible import ArenaCrucibleService
from aura_arena_experience import OutcomeVector, build_arena_experience
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_crucible_cli import build_parser
from aura_crucible_miner import mine_crucible_candidates, three_way_temporal_split
from aura_crucible_store import CrucibleStore
from aura_crucible_types import CRYSTALLIZATION_PROPOSED, CrystallizationProposal, CruciblePolicy
from aura_crucible_validation import validate_crucible_candidate, validate_manifest_pin

RANK = {
    "unresolved_risk": 0.0,
    "declared_evidence_gap": 0.0,
    "empirical_uncertainty": 1.0,
    "semantic_ambiguity": 0.0,
    "context_switch_cost": 0.0,
    "latency_cost": 0.2,
    "token_cost": 0.3,
    "thermal_cost": 0.1,
    "negative_semantic_fit": -0.9,
    "negative_user_fit": -0.8,
    "stable_transition_id": "T.A",
    "measurement_classes": {"latency": "MEASURED", "tokens": "MEASURED", "thermal": "MEASURED"},
}


def _manifest(root: Path):
    path = root / ".aura" / "arena_routes" / "test.v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "AURA_ARENA_GRAMMAR_MANIFEST_V1",
        "arena_id": "test",
        "arena_version": "v1",
        "grammar_version": "g1",
        "start_state": "S",
        "states": ["S", "N"],
        "terminal_states": ["N"],
        "transitions": [
            {"transition_id": "T.A", "from_state": "S", "next_state": "N", "output_symbol": "A", "soft_weight_profile": {"empirical_uncertainty": 1.0}},
            {"transition_id": "T.B", "from_state": "S", "next_state": "N", "output_symbol": "B", "soft_weight_profile": {"empirical_uncertainty": 0.8}},
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    result = load_and_compile_arena_grammar(path)
    assert result.ok and result.grammar is not None
    return path, result


def _route(digest: str, selected: str = "T.A") -> dict:
    a = {"transition_id": "T.A", "next_state": "N", "risk": "low", "required_evidence": [], "produced_evidence": ["x"], "verifier_requirement": "none", "approval_requirement": "none", "semantic_fit": 0.9, "rank": dict(RANK)}
    b_rank = dict(RANK)
    b_rank["empirical_uncertainty"] = 0.8
    b_rank["stable_transition_id"] = "T.B"
    b = {"transition_id": "T.B", "next_state": "N", "risk": "low", "required_evidence": [], "produced_evidence": ["y"], "verifier_requirement": "none", "approval_requirement": "none", "semantic_fit": 0.8, "rank": b_rank}
    return {"grammar_digest": digest, "selected": a if selected == "T.A" else b, "available": [a, b], "recommended": [a, b], "blocked": [], "abstained": False}


def _experience(index: int, digest: str, score: float = 0.85):
    vector = OutcomeVector(terminal_class="COMPLETED", task_progress=score, evidence_quality=score, verification_quality=score, safety_quality=1.0, human_alignment=score, cost_efficiency=0.8, latency_efficiency=0.8)
    return build_arena_experience(
        arena_id="test", arena_version="v1", grammar_version="g1", runtime_version="r", compiler_version="c",
        state_before="S", state_after="N", selected_transition="T.A",
        final_outcome="COMPLETED" if index % 2 else "DENIED",
        payload={"route": _route(digest), "action_result": {"ok": bool(index % 2)}, "evidence_keys": []},
        outcome_vector=vector, experience_id=f"EXP-{index:03}", objective=f"objective-{index % 4}",
        started_at=float(index), completed_at=float(index) + 0.1,
    )


def _grammar(root: Path):
    path, result = _manifest(root)
    return replace(result.grammar, source_path=path.relative_to(root).as_posix()), result.manifest_digest


def test_experience_requires_digest_and_preserves_every_alternative_and_prediction(tmp_path: Path):
    _, result = _manifest(tmp_path)
    exp = _experience(1, result.manifest_digest)
    assert exp.grammar_manifest_digest == result.manifest_digest
    assert [row["transition_id"] for row in exp.admissible_alternatives] == ["T.A", "T.B"]
    assert [row["transition_id"] for row in exp.predictions] == ["T.A", "T.B"]
    assert sum(bool(row["predicted_selected"]) for row in exp.predictions) == 1
    assert exp.outcome_vector.proposal_projection()["runtime_authority"] is False
    with pytest.raises(ValueError, match="grammar_manifest_digest"):
        build_arena_experience(arena_id="x", arena_version="v", grammar_version="g", runtime_version="r", compiler_version="c", state_before="S", state_after="S", selected_transition="", final_outcome="BLOCKED")


def test_outcome_vector_replaces_binary_scoring(tmp_path: Path):
    grammar, digest = _grammar(tmp_path)
    rows = [_experience(i, digest, 0.82).to_dict() for i in range(1, 18)]
    assert {row["final_outcome"] for row in rows} == {"COMPLETED", "DENIED"}
    candidates = mine_crucible_candidates(rows, {("test", "g1"): grammar})
    assert len(candidates) == 1
    assert candidates[0].train_outcome_summary["binary_outcome_used"] is False
    assert candidates[0].train_outcome_summary["score_mean"] > 0.8


def test_v1_ledger_migrates_without_fabricating_v2_observations(tmp_path: Path):
    _, result = _manifest(tmp_path)
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.executescript("""CREATE TABLE arena_experiences (experience_id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL, task_id TEXT, workflow_id TEXT, arena_id TEXT NOT NULL, arena_version TEXT NOT NULL, grammar_version TEXT NOT NULL, runtime_version TEXT NOT NULL, compiler_version TEXT NOT NULL, started_at REAL NOT NULL, completed_at REAL NOT NULL, state_before TEXT NOT NULL, state_after TEXT NOT NULL, selected_transition TEXT, final_outcome TEXT NOT NULL, repository_commit_sha TEXT, working_tree_digest TEXT, objective_hash TEXT, source_hash_digest TEXT, provider TEXT, model TEXT, measurement_class TEXT, cost_run_id TEXT, trace_atom_ids_json TEXT NOT NULL, raw_evidence_refs_json TEXT NOT NULL, redactions_json TEXT NOT NULL, payload_json TEXT NOT NULL, experience_digest TEXT NOT NULL, schema_version TEXT NOT NULL, created_at REAL NOT NULL); CREATE TABLE arena_experience_migrations(version INTEGER PRIMARY KEY, applied_at REAL NOT NULL);""")
    con.execute("INSERT INTO arena_experiences VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("OLD", "C", "", "", "test", "v1", "g1", "r", "c", 0, 1, "S", "N", "T.A", "COMPLETED", "", "", "", "", "", "", "UNAVAILABLE", "", "[]", "[]", "[]", "{}", "d", "V1", 1))
    con.commit()
    con.close()
    with ArenaExperienceLedger(tmp_path, db_path=db) as ledger:
        assert ledger.get("OLD")["legacy_record"] is True
        assert ledger.record(_experience(1, result.manifest_digest))["ok"]
        assert ledger.get("EXP-001")["legacy_record"] is False
        assert ledger.status()["v2_complete_record_count"] == 1


def test_train_validation_shadow_are_disjoint(tmp_path: Path):
    _, digest = _grammar(tmp_path)
    rows = [_experience(i, digest).to_dict() for i in range(1, 21)]
    split = three_way_temporal_split(rows, CruciblePolicy())
    assert split is not None
    ids = [{row["experience_id"] for row in dataset} for dataset in split]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])


def test_stale_or_unknown_manifest_digest_is_not_mined(tmp_path: Path):
    grammar, digest = _grammar(tmp_path)
    rows = [_experience(i, "stale-digest").to_dict() for i in range(1, 15)]
    assert mine_crucible_candidates(rows, {("test", "g1"): grammar}) == []
    assert digest != "stale-digest"


def test_all_thresholds_remain_proposal_only_and_do_not_block_candidates(tmp_path: Path):
    grammar, digest = _grammar(tmp_path)
    rows = [_experience(i, digest, 0.55).to_dict() for i in range(1, 16)]
    policy = CruciblePolicy(proposal_min_train_records=999, proposal_min_validation_records=999, proposal_min_shadow_records=999, proposal_min_outcome_coverage=0.99, proposal_min_train_score=0.99, proposal_min_validation_score=0.99, proposal_min_uncertainty_delta=0.99)
    candidate = mine_crucible_candidates(rows, {("test", "g1"): grammar}, policy=policy)[0]
    assert candidate.threshold_scope == "PROPOSAL_ONLY"
    assert candidate.threshold_assessment["all_proposal_thresholds_met"] is False
    assert candidate.threshold_assessment["candidate_generation_blocked"] is False


def test_manifest_pin_is_repo_relative_and_compiler_canonical(tmp_path: Path):
    path, result = _manifest(tmp_path)
    rel = path.relative_to(tmp_path).as_posix()
    assert validate_manifest_pin(repo_root=tmp_path, manifest_path=rel, manifest_digest=result.manifest_digest, arena_id="test", grammar_version="g1")["passed"]
    assert not validate_manifest_pin(repo_root=tmp_path, manifest_path=str(path.resolve()), manifest_digest=result.manifest_digest, arena_id="test", grammar_version="g1")["passed"]
    assert not validate_manifest_pin(repo_root=tmp_path, manifest_path="../escape.json", manifest_digest=result.manifest_digest, arena_id="test", grammar_version="g1")["passed"]
    raw_digest = hashlib.blake2b(path.read_bytes(), digest_size=20).hexdigest()
    assert raw_digest != result.manifest_digest
    assert not validate_manifest_pin(repo_root=tmp_path, manifest_path=rel, manifest_digest=raw_digest, arena_id="test", grammar_version="g1")["passed"]


def test_validation_and_shadow_use_separate_data_and_preserve_observations(tmp_path: Path):
    grammar, digest = _grammar(tmp_path)
    rows = [_experience(i, digest).to_dict() for i in range(1, 21)]
    policy = CruciblePolicy(proposal_min_train_records=2, proposal_min_validation_records=1, proposal_min_shadow_records=1)
    candidate = mine_crucible_candidates(rows, {("test", "g1"): grammar}, policy=policy)[0]
    report = validate_crucible_candidate(candidate, rows, repo_root=tmp_path, policy=policy)
    assert report["passed"]
    assert set(report["dataset_ids"]["validation"]).isdisjoint(report["dataset_ids"]["shadow"])
    assert report["shadow"]["dataset"] == "SHADOW"
    assert report["shadow"]["all_admissible_alternatives_preserved"]
    assert all(len(row["admissible_alternatives"]) == 2 and len(row["recorded_predictions"]) == 2 for row in report["shadow"]["replay_records"])


def test_missing_shadow_prediction_fails_structural_validation(tmp_path: Path):
    grammar, digest = _grammar(tmp_path)
    rows = [_experience(i, digest).to_dict() for i in range(1, 21)]
    candidate = mine_crucible_candidates(rows, {("test", "g1"): grammar})[0]
    shadow_id = candidate.shadow_experience_ids[0]
    next_rows = [dict(row) for row in rows]
    next(row for row in next_rows if row["experience_id"] == shadow_id)["predictions"] = []
    report = validate_crucible_candidate(candidate, next_rows, repo_root=tmp_path)
    assert not report["passed"]
    assert not report["structural_checks"]["shadow_observations_preserve_all_alternatives_and_predictions"]


def test_service_stores_structural_proposal_even_with_threshold_warnings(tmp_path: Path):
    _, result = _manifest(tmp_path)
    with ArenaExperienceLedger(tmp_path) as ledger:
        for i in range(1, 18):
            assert ledger.record(_experience(i, result.manifest_digest, 0.55))["ok"]
    policy = CruciblePolicy(proposal_min_train_records=999, proposal_min_validation_records=999, proposal_min_shadow_records=999, proposal_min_outcome_coverage=0.99, proposal_min_train_score=0.99, proposal_min_validation_score=0.99)
    service = ArenaCrucibleService(tmp_path)
    report = service.run_once(policy=policy)
    service.close()
    assert report["proposal_count"] == 1
    proposal = report["proposals"][0]
    assert proposal["status"] == CRYSTALLIZATION_PROPOSED
    assert proposal["validation"]["passed"]
    assert proposal["validation"]["all_proposal_thresholds_met"] is False
    assert proposal["validation"]["proposal_recommendation"] == "REVIEW_WITH_THRESHOLD_WARNINGS"


def test_pause_resume_persists_across_process_like_store_instances(tmp_path: Path):
    first = CrucibleStore(tmp_path)
    assert first.pause("review")["paused"]
    first.close()
    second = CrucibleStore(tmp_path)
    assert second.status()["paused"]
    assert not second.resume()["paused"]
    second.close()
    third = CrucibleStore(tmp_path)
    assert not third.status()["paused"]
    third.close()


def _proposal(tmp_path: Path) -> CrystallizationProposal:
    path, result = _manifest(tmp_path)
    validation = {"passed": True, "proposal_recommendation": "READY_FOR_HUMAN_REVIEW", "all_proposal_thresholds_met": True}
    return CrystallizationProposal("P1", "R1", "C1", "test", "g1", path.relative_to(tmp_path).as_posix(), result.manifest_digest, "S", "T.A", "soft_weight_profile.empirical_uncertainty", 1.0, 0.2, validation, {"proposal_min_train_records": 1}, {"all_proposal_thresholds_met": True}, ("A",), ("B",), ("C",), "source", 1.0)


def test_store_rejects_forged_authority_and_nonrelative_manifest(tmp_path: Path):
    proposal = _proposal(tmp_path).to_dict()
    proposal["automatic_grammar_promotion"] = True
    store = CrucibleStore(tmp_path)
    assert not store.record_proposal(proposal)["ok"]
    proposal = _proposal(tmp_path).to_dict()
    proposal["manifest_path"] = str((tmp_path / "x.json").resolve())
    assert not store.record_proposal(proposal)["ok"]
    store.close()


def test_cli_has_no_apply_promote_commit_push_or_merge_commands():
    parser = build_parser()
    choices = set(next(action for action in parser._actions if getattr(action, "choices", None)).choices)
    assert choices == {"status", "pause", "resume", "run-once", "service", "proposals", "proposal"}
    assert not choices & {"apply", "promote", "commit", "push", "merge"}
