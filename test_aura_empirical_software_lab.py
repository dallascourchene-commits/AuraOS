import json
from pathlib import Path

import aura_empirical_software_lab
from aura_empirical_software_lab import (
    EmpiricalCandidate,
    analyze_empirical_candidate,
    define_empirical_task,
    generate_candidate,
    record_empirical_result,
    recommend_promotion,
    score_candidate,
    select_next_candidate_ucb,
)


def _write_empirical_repo(root: Path) -> None:
    for name in [
        "aura_patch_quality_gate.py",
        "aura_patch_repair.py",
        "aura_live_architect.py",
        "aura_harness_evolver.py",
        "aura_repo_localizer.py",
        "aura_repair_kg.py",
        "aura_builder_context.py",
        "aura_context_crusher.py",
        "aura_st3gg_recall.py",
        "aura_hotswap_refactor.py",
        "aura_architect_loop.py",
        "arxiv_forager.py",
        "aura_research_manifest.py",
        "aura_research_ingest_bridge.py",
        "aura_paper_memory.py",
    ]:
        (root / name).write_text(f"def marker_{name.replace('.', '_')}():\n    return 1\n", encoding="utf-8")
    aura_dir = root / ".aura"
    aura_dir.mkdir()
    (aura_dir / "CODEMAP.json").write_text(
        json.dumps(
            {
                "coverage": {"included_file_count": 15},
                "files": [
                    {"path": "aura_patch_quality_gate.py", "role": "patch gate", "lines": 10, "topology": {}},
                    {"path": "aura_repo_localizer.py", "role": "localizer", "lines": 10, "topology": {}},
                ],
                "symbol_index": {
                    "preflight_patch": [{"file": "aura_patch_quality_gate.py", "kind": "function", "line": 1}],
                },
            }
        ),
        encoding="utf-8",
    )


def test_empirical_task_definitions_are_codemap_grounded(tmp_path: Path):
    _write_empirical_repo(tmp_path)

    task = define_empirical_task("patch_repair", tmp_path)

    assert task.metric_name == "patch_repair_score"
    assert "aura_patch_quality_gate.py" in task.target_modules
    assert task.evidence["manifest"]["manifest_hash"]
    assert task.evidence["codemap"]["codemap_available"] is True
    assert "No production writes." in task.constraints


def test_score_patch_repair_candidate_rewards_green_metrics(tmp_path: Path):
    _write_empirical_repo(tmp_path)
    task = define_empirical_task("patch_repair", tmp_path)

    good = score_candidate(
        task,
        {
            "patch_staged_count": 1,
            "workspace_ok": True,
            "repair_success_count": 0,
            "test_pass_count": 1,
            "verifier_failure_count": 0,
        },
    )
    bad = score_candidate(
        task,
        {
            "patch_staged_count": 0,
            "workspace_ok": False,
            "preflight_rejection_count": 2,
            "test_fail_count": 1,
            "verifier_failure_count": 1,
        },
    )

    assert good.score > bad.score
    assert good.passed is True
    assert bad.passed is False


def test_ucb_prefers_high_score_with_exploration():
    stable = EmpiricalCandidate(
        candidate_id="stable",
        parent_id=None,
        task_type="patch_repair",
        target_module="a.py",
        proposal="stable",
        expected_metric="score",
        evidence={},
        score=0.9,
        visits=10,
        fitness_history=[0.9, 0.9],
    )
    fresh = EmpiricalCandidate(
        candidate_id="fresh",
        parent_id=None,
        task_type="patch_repair",
        target_module="b.py",
        proposal="fresh",
        expected_metric="score",
        evidence={},
        score=0.75,
        visits=0,
        fitness_history=[0.75],
    )

    selected = select_next_candidate_ucb([stable, fresh], exploration_c=0.1)
    assert selected is stable

    selected_explore = select_next_candidate_ucb([stable, fresh], exploration_c=2.0)
    assert selected_explore is fresh


def test_no_promotion_when_verifier_failed(tmp_path: Path, monkeypatch):
    _write_empirical_repo(tmp_path)
    monkeypatch.setattr(aura_empirical_software_lab, "record_harness_prediction", lambda *args, **kwargs: None)
    task = define_empirical_task("patch_repair", tmp_path)
    candidate = generate_candidate(task)
    result = analyze_empirical_candidate(
        task=task,
        candidate=candidate,
        transaction_or_metrics={
            "patch_staged_count": 1,
            "workspace_ok": False,
            "test_fail_count": 1,
            "verifier_failure_count": 1,
        },
    )
    record_empirical_result(result, tmp_path)

    recommendation = recommend_promotion(candidate.candidate_id, tmp_path)

    assert recommendation["recommended"] is False
    assert recommendation["no_autopromote"] is True


def test_records_candidate_tree_jsonl(tmp_path: Path, monkeypatch):
    _write_empirical_repo(tmp_path)
    monkeypatch.setattr(aura_empirical_software_lab, "record_harness_prediction", lambda *args, **kwargs: None)
    task = define_empirical_task("patch_repair", tmp_path)
    candidate = generate_candidate(task)
    result = analyze_empirical_candidate(
        task=task,
        candidate=candidate,
        transaction_or_metrics={
            "patch_staged_count": 1,
            "workspace_ok": True,
            "test_pass_count": 1,
            "verifier_failure_count": 0,
        },
    )
    record_empirical_result(result, tmp_path)

    ledger = tmp_path / "Aura_Staging" / "empirical_candidate_tree.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]

    assert rows[0]["event_class"] == "empirical_run_result"
    assert rows[0]["candidate_id"] == candidate.candidate_id
