from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from aura_efficiency_benchmark import (
    PATCH_AUTHORITY_POLICY,
    deterministic_mock_model_caller,
    log_results_to_savings_db,
    main,
    result_to_dict,
    run_aura_compress,
    run_aura_full,
    run_raw_baseline,
    run_suite,
    summarize_results,
)
from aura_efficiency_tasks import BenchmarkTask, default_efficiency_suite

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_default_suite_loads() -> None:
    tasks = default_efficiency_suite()

    assert len(tasks) >= 7
    assert {task.category for task in tasks} >= {
        "route_classification",
        "code_localization",
        "external_call_context",
        "capability_audit",
        "test_gap_detection",
        "small_safe_patch_tasks",
        "summarization_compression",
    }
    assert all(isinstance(task, BenchmarkTask) for task in tasks)


def test_raw_baseline_has_at_least_aura_compress_prompt_tokens_for_code_task() -> None:
    task = next(task for task in default_efficiency_suite() if task.task_id == "eff_st3gg_summarization")

    raw = run_raw_baseline(task, REPO_ROOT, model_caller=deterministic_mock_model_caller)
    compressed = run_aura_compress(task, REPO_ROOT, model_caller=deterministic_mock_model_caller)

    assert raw.input_tokens >= compressed.input_tokens


def test_aura_full_mode_includes_grounding_metadata() -> None:
    task = next(task for task in default_efficiency_suite() if task.task_id == "eff_small_safe_patch")

    result = run_aura_full(task, REPO_ROOT, model_caller=deterministic_mock_model_caller)

    assert isinstance(result.metadata["grounding"], dict)
    assert result.metadata["grounding"].get("route")
    assert result.metadata["route_decision"]


def test_st3gg_metrics_are_included_when_target_source_is_available() -> None:
    task = next(task for task in default_efficiency_suite() if task.task_id == "eff_st3gg_summarization")

    result = run_aura_compress(task, REPO_ROOT, model_caller=deterministic_mock_model_caller)

    metrics = result.metadata["st3gg_metrics"]
    assert isinstance(metrics, dict)
    assert metrics["raw_token_estimate"] > 0
    assert metrics["encoded_token_estimate"] > 0


def test_results_serialize_to_json() -> None:
    task = default_efficiency_suite()[0]
    result = run_raw_baseline(task, REPO_ROOT, model_caller=deterministic_mock_model_caller)

    serialized = json.dumps(result_to_dict(result), sort_keys=True, default=str)

    assert json.loads(serialized)["task_id"] == task.task_id


def test_summary_computes_token_savings_and_quality_averages() -> None:
    task = next(task for task in default_efficiency_suite() if task.task_id == "eff_st3gg_summarization")
    results = run_suite([task], ["raw_baseline", "aura_compress"], REPO_ROOT, model_caller=deterministic_mock_model_caller)

    summary = summarize_results(results)

    assert summary["modes"]["raw_baseline"]["tasks"] == 1
    assert summary["modes"]["aura_compress"]["tasks"] == 1
    assert summary["modes"]["aura_compress"]["tokens_saved_pct"] >= 0
    assert 0 <= summary["modes"]["aura_compress"]["avg_quality"] <= 1


def test_aura_savings_db_logging_accepts_benchmark_metadata(tmp_path: Path) -> None:
    task = default_efficiency_suite()[0]
    results = run_suite([task], ["raw_baseline", "aura_compress"], REPO_ROOT, model_caller=deterministic_mock_model_caller)
    db_path = tmp_path / "aura_savings.db"

    row_ids = log_results_to_savings_db(results, REPO_ROOT, db_path=db_path)

    assert len(row_ids) == 2
    assert db_path.exists()


def test_no_benchmark_mode_treats_vsa_st3gg_jspace_as_patch_authority() -> None:
    task = next(task for task in default_efficiency_suite() if task.task_id == "eff_unsafe_advisory_patch_block")
    results = run_suite(
        [task],
        ["raw_baseline", "rag_baseline", "plan_act_baseline", "aura_compress", "aura_full"],
        REPO_ROOT,
        model_caller=deterministic_mock_model_caller,
    )

    for result in results:
        assert result.metadata["patch_authority"] == PATCH_AUTHORITY_POLICY
        assert result.metadata["vsa_patch_authority"] is False
    aura_full = next(result for result in results if result.mode == "aura_full")
    assert aura_full.unsafe_blocked is True
    assert aura_full.route == "BLOCKED_WITH_REASON"


def test_mock_model_caller_works() -> None:
    def caller(model: str, prompt: str, metadata: dict):
        return {"text": json.dumps({"ok": True}), "model": "mock-special", "input_tokens": 7, "output_tokens": 3}

    task = default_efficiency_suite()[0]
    result = run_raw_baseline(task, REPO_ROOT, model_caller=caller)

    assert result.model == "mock-special"
    assert result.input_tokens == 7
    assert result.output_format_valid is True


def test_cli_dry_run_works(tmp_path: Path) -> None:
    out = tmp_path / "aura_efficiency_latest.json"

    code = main(
        [
            "--suite",
            "efficiency",
            "--modes",
            "raw_baseline,aura_compress",
            "--out",
            str(out),
            "--repo-root",
            str(REPO_ROOT),
            "--dry-run",
            "--limit-tasks",
            "1",
            "--no-savings-db",
        ]
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["summary"]["result_count"] == 2
    assert json.dumps([asdict(task) for task in default_efficiency_suite()[:1]], default=str)
