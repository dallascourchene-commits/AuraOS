from __future__ import annotations

from dataclasses import replace

import pytest

from tools.benchmarks.aura_benchmark_score_admission import BenchmarkTaskReceipt, admit_score


def fixture(**changes):
    base = BenchmarkTaskReceipt(
        campaign_id="arena-benchmark-20260831",
        suite_id="terminal-bench@2.0",
        suite_generation="upstream-pinned-generation",
        harness_id="harbor",
        harness_generation="pinned-harbor-generation",
        task_id="task-001",
        task_input_digest="a" * 64,
        agent_id="aura-adapter",
        agent_generation="b" * 40,
        model_id="provider/model",
        run_id="run-1",
        attempt_id="attempt-1",
        result_state="PASS",
        measurement_class="OBSERVED",
        wall_time_ms=1234.5,
        peak_rss_mb=128.0,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.25,
        source_verified=True,
        execution_observed=True,
    )
    return replace(base, **changes)


def test_duplicate_attempt_does_not_inflate_score():
    first = fixture()
    retry = fixture(run_id="run-2", attempt_id="attempt-2")
    summary = admit_score([first, retry])
    assert summary["unique_task_count"] == 1
    assert summary["passed"] == 1
    assert summary["duplicate_process_count"] == 1


def test_changed_agent_generation_is_distinct_parent_state():
    summary = admit_score([fixture(), fixture(agent_generation="c" * 40, run_id="run-2")])
    assert summary["unique_task_count"] == 2


def test_changed_dataset_generation_is_distinct_parent_state():
    summary = admit_score([fixture(), fixture(suite_generation="new-generation", run_id="run-2")])
    assert summary["unique_task_count"] == 2


def test_contradictory_duplicate_result_fails_closed():
    with pytest.raises(ValueError, match="CONTRADICTORY_RESULT_FOR_SCORE_IDENTITY"):
        admit_score([fixture(), fixture(result_state="FAIL", run_id="run-2")])


def test_pass_requires_source_verification():
    with pytest.raises(ValueError, match="PASS_WITHOUT_VERIFIED_SOURCE"):
        fixture(source_verified=False).validate()


def test_pass_requires_observed_execution():
    with pytest.raises(ValueError, match="RESULT_WITHOUT_OBSERVED_EXECUTION"):
        fixture(execution_observed=False).validate()


def test_unknown_measurement_cannot_launder_zero_or_estimates():
    with pytest.raises(ValueError, match="UNKNOWN_MEASUREMENT_CANNOT_CARRY_VALUES"):
        fixture(measurement_class="UNKNOWN", wall_time_ms=0.0).validate()


def test_unknown_measurement_with_no_values_is_valid():
    receipt = fixture(
        measurement_class="UNKNOWN",
        wall_time_ms=None,
        peak_rss_mb=None,
        input_tokens=None,
        output_tokens=None,
        cost_usd=None,
    )
    receipt.validate()


def test_estimated_measurement_remains_explicitly_estimated():
    receipt = fixture(measurement_class="ESTIMATED", cost_usd=0.125)
    assert receipt.to_dict()["measurement_class"] == "ESTIMATED"


def test_score_identity_excludes_retry_identity_but_binds_model():
    first = fixture()
    retry = fixture(run_id="run-9", attempt_id="attempt-9")
    changed_model = fixture(model_id="provider/other-model")
    assert first.score_identity == retry.score_identity
    assert first.score_identity != changed_model.score_identity


def test_receipt_is_deterministic():
    assert fixture().to_dict() == fixture().to_dict()
