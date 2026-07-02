import json
from pathlib import Path

import aura_harness_evolver
from aura_harness_evolver import analyze_transaction_outcome, record_harness_prediction, verify_harness_predictions


def test_prediction_is_written_to_jsonl_without_qdkt(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(aura_harness_evolver, "get_qdkt", None)

    record_harness_prediction(
        "change-1",
        "localizer",
        "Improve top five accuracy.",
        "localizer_score",
        0.8,
        repo_root=tmp_path,
    )

    ledger = tmp_path / "Aura_Staging" / "harness_predictions.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["change_id"] == "change-1"
    assert rows[0]["status"] == "pending"


def test_analyze_transaction_outcome_extracts_metrics():
    metrics = analyze_transaction_outcome(
        {
            "stage_results": [{"ok": True}, {"ok": False}],
            "workspace": {"ok": True, "test_results": {"test_demo.py": {"status": "passed"}}},
            "verification": {"hotswap_ready": True, "failures": []},
            "patch_quality": {
                "attempts": [{"status": "preflight_failed", "preflight": {"rejections": ["bad hunk"]}}],
                "repair_succeeded": 1,
            },
        }
    )

    assert metrics["patch_staged_count"] == 1
    assert metrics["preflight_rejection_count"] == 2
    assert metrics["repair_success_count"] == 1
    assert metrics["workspace_ok"] is True
    assert metrics["hotswap_ready"] is True
    assert metrics["test_pass_count"] == 1


def test_verify_harness_predictions_returns_inconclusive_without_observed_data(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(aura_harness_evolver, "get_qdkt", None)
    record_harness_prediction(
        "change-1",
        "localizer",
        "Improve top five accuracy.",
        "localizer_score",
        0.8,
        repo_root=tmp_path,
    )

    result = verify_harness_predictions(tmp_path)

    assert result["checked_count"] == 1
    assert result["inconclusive_count"] == 1
    assert result["failed_count"] == 0
