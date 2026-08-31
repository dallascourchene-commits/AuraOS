from __future__ import annotations

from dataclasses import replace

import pytest

from tools.benchmarks.aura_benchmark_score_admission import (
    BenchmarkAdmissionPolicy,
    BenchmarkTaskReceipt,
    admit_score,
)


def policy(**changes):
    base = BenchmarkAdmissionPolicy(
        policy_generation="benchmark-policy-gen-1",
        authority_scope="BENCHMARK_EVIDENCE_ONLY",
        expected_execution_route_fingerprint="route:harbor:host-observed",
        trusted_execution_observer_identity="BENCHMARK_HOST_OBSERVER",
        trusted_source_verifier_identity="UPSTREAM_SOURCE_VERIFIER",
        execution_authority_verified=True,
        source_verifier_authority_verified=True,
    )
    return replace(base, **changes)


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
        execution_route_fingerprint="route:harbor:host-observed",
        execution_observer_identity="BENCHMARK_HOST_OBSERVER",
        source_verifier_identity="UPSTREAM_SOURCE_VERIFIER",
    )
    return replace(base, **changes)


def test_duplicate_attempt_does_not_inflate_score():
    first = fixture()
    retry = fixture(run_id="run-2", attempt_id="attempt-2")
    summary = admit_score([first, retry], policy=policy())
    assert summary["unique_task_count"] == 1
    assert summary["passed"] == 1
    assert summary["duplicate_process_count"] == 1


def test_changed_agent_generation_is_distinct_parent_state():
    summary = admit_score(
        [fixture(), fixture(agent_generation="c" * 40, run_id="run-2")],
        policy=policy(),
    )
    assert summary["unique_task_count"] == 2


def test_changed_dataset_generation_is_distinct_parent_state():
    summary = admit_score(
        [fixture(), fixture(suite_generation="new-generation", run_id="run-2")],
        policy=policy(),
    )
    assert summary["unique_task_count"] == 2


def test_contradictory_duplicate_result_fails_closed():
    with pytest.raises(ValueError, match="CONTRADICTORY_RESULT_FOR_SCORE_IDENTITY"):
        admit_score(
            [fixture(), fixture(result_state="FAIL", run_id="run-2")],
            policy=policy(),
        )


def test_scoring_result_requires_source_verification_for_pass_and_fail():
    for result_state in ("PASS", "FAIL"):
        with pytest.raises(ValueError, match="RESULT_WITHOUT_VERIFIED_SOURCE"):
            fixture(result_state=result_state, source_verified=False).validate()


def test_scoring_result_requires_observed_execution():
    with pytest.raises(ValueError, match="RESULT_WITHOUT_OBSERVED_EXECUTION"):
        fixture(execution_observed=False).validate()


def test_receipt_booleans_cannot_self_mint_execution_authority():
    with pytest.raises(ValueError, match="EXECUTION_AUTHORITY_NOT_VERIFIED"):
        admit_score([fixture()], policy=policy(execution_authority_verified=False))


def test_receipt_route_must_match_trusted_policy():
    with pytest.raises(ValueError, match="EXECUTION_ROUTE_FINGERPRINT_MISMATCH"):
        admit_score([fixture(execution_route_fingerprint="route:caller:minted")], policy=policy())


def test_receipt_observer_must_match_trusted_policy():
    with pytest.raises(ValueError, match="EXECUTION_OBSERVER_IDENTITY_MISMATCH"):
        admit_score([fixture(execution_observer_identity="CALLER_SELF_REPORT")], policy=policy())


def test_source_verifier_must_be_authorized_and_match_trusted_policy():
    with pytest.raises(ValueError, match="SOURCE_VERIFIER_AUTHORITY_NOT_VERIFIED"):
        admit_score([fixture()], policy=policy(source_verifier_authority_verified=False))
    with pytest.raises(ValueError, match="SOURCE_VERIFIER_IDENTITY_MISMATCH"):
        admit_score([fixture(source_verifier_identity="CALLER_SOURCE_LABEL")], policy=policy())


def test_authority_scope_must_match_policy():
    with pytest.raises(ValueError, match="BENCHMARK_AUTHORITY_SCOPE_MISMATCH"):
        admit_score([fixture(authority_scope="LEADERBOARD_AUTHORITY")], policy=policy())


def test_unknown_measurement_cannot_launder_zero_or_estimates():
    with pytest.raises(ValueError, match="UNKNOWN_MEASUREMENT_CANNOT_CARRY_VALUES"):
        fixture(measurement_class="UNKNOWN", wall_time_ms=0.0).validate()


def test_unknown_measurement_with_no_values_is_valid():
    receipt = fixture(
        result_state="UNKNOWN",
        measurement_class="UNKNOWN",
        wall_time_ms=None,
        peak_rss_mb=None,
        input_tokens=None,
        output_tokens=None,
        cost_usd=None,
        source_verified=False,
        execution_observed=False,
        execution_route_fingerprint=None,
        execution_observer_identity=None,
        source_verifier_identity=None,
    )
    receipt.validate()
    summary = admit_score([receipt], policy=policy())
    assert summary["unknown"] == 1


def test_estimated_measurement_remains_explicitly_estimated():
    receipt = fixture(measurement_class="ESTIMATED", cost_usd=0.125)
    assert receipt.to_dict()["measurement_class"] == "ESTIMATED"


def test_score_identity_excludes_retry_identity_but_binds_model():
    first = fixture()
    retry = fixture(run_id="run-9", attempt_id="attempt-9")
    changed_model = fixture(model_id="provider/other-model")
    assert first.score_identity == retry.score_identity
    assert first.score_identity != changed_model.score_identity


def test_policy_generation_changes_evidence_generation_not_score_identity():
    receipt = fixture()
    first = admit_score([receipt], policy=policy(policy_generation="gen-1"))
    second = admit_score([receipt], policy=policy(policy_generation="gen-2"))
    assert receipt.score_identity == receipt.score_identity
    assert first["policy_generation"] != second["policy_generation"]


def test_receipt_is_deterministic():
    assert fixture().to_dict() == fixture().to_dict()
