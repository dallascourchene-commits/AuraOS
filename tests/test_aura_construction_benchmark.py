from __future__ import annotations

from dataclasses import replace
import json

import pytest

from aura_construction_benchmark import (
    ConstructionBenchmarkReport,
    main,
    run_construction_phase3_benchmark,
)


def test_zero_model_benchmark_is_stable():
    result = run_construction_phase3_benchmark(iterations=25, seed=1)
    report = result["report"]
    assert result["ok"] is True
    assert report["unique_evaluation_digests"] == 1
    assert report["unique_recommendations"] == 1
    assert report["candidate_order_invariant"] is True


def test_benchmark_hard_filters_unsafe_high_score_route():
    report = run_construction_phase3_benchmark(iterations=10)["report"]
    assert report["unsafe_high_score_candidate_blocked"] is True
    assert report["blocked_candidate_count"] == 1
    assert report["admissible_candidate_count"] == 3


def test_only_zero_model_arm_is_measured():
    arms = run_construction_phase3_benchmark(iterations=5)["benchmark_arms"]
    assert arms["ZERO_MODEL"]["status"] == "MEASURED"
    assert arms["BROAD_IMPLEMENTER"]["status"] == "NOT_MEASURED"
    assert arms["SLICED_SURGEON"]["status"] == "NOT_MEASURED"
    assert arms["SELECTIVE_COUNCIL_V3_PLUS_SURGEON"]["status"] == "NOT_MEASURED"


def test_benchmark_does_not_invent_provider_cost_or_real_savings():
    result = run_construction_phase3_benchmark(iterations=5)
    report = result["report"]
    boundaries = result["claim_boundaries"]
    assert report["provider_tokens"] == "NOT_MEASURED"
    assert report["provider_cost"] == "NOT_MEASURED"
    assert report["real_project_savings"] == "NOT_MEASURED"
    assert report["production_readiness"] == "NOT_CLAIMED"
    assert boundaries["real_project_savings"] == "NOT_MEASURED"
    assert boundaries["production_readiness"] == "NOT_CLAIMED"


def test_benchmark_rejects_invalid_iterations_and_seed():
    for iterations in (0, 10_001):
        with pytest.raises(ValueError, match="positive bounded integer"):
            run_construction_phase3_benchmark(iterations=iterations)
    with pytest.raises(ValueError, match="seed must be an integer"):
        run_construction_phase3_benchmark(iterations=1, seed=1.5)


def test_benchmark_supports_full_250_permutation_gate():
    report = run_construction_phase3_benchmark(iterations=250, seed=1337)["report"]
    assert report["iterations"] == 250
    assert report["unique_evaluation_digests"] == 1
    assert report["displayed_option_count"] == 3


def test_benchmark_cli_human_output(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["aura_construction_benchmark.py", "--iterations", "2", "--seed", "5"],
    )
    assert main() == 0
    output = capsys.readouterr().out
    assert "2 iterations" in output
    assert "1 digest" in output
    assert "1 blocked" in output
    assert "3 admissible" in output


def test_benchmark_cli_json_output(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "aura_construction_benchmark.py",
            "--iterations",
            "2",
            "--seed",
            "5",
            "--json",
        ],
    )
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["report"]["iterations"] == 2
    assert payload["claim_boundaries"]["production_readiness"] == "NOT_CLAIMED"


def test_benchmark_report_rejects_tampered_evidence_claims():
    payload = run_construction_phase3_benchmark(iterations=2)["report"]
    report = ConstructionBenchmarkReport(**payload)
    with pytest.raises(ValueError, match="multiple evaluation digests"):
        replace(report, unique_evaluation_digests=2)
    with pytest.raises(ValueError, match="unsafe high-score candidate"):
        replace(report, unsafe_high_score_candidate_blocked=False)
    with pytest.raises(ValueError, match="may not invent"):
        replace(report, provider_cost="1.00")
    with pytest.raises(ValueError, match="production readiness"):
        replace(report, production_readiness="READY")
    with pytest.raises(ValueError, match="measurement_class"):
        replace(report, measurement_class="MODEL_ESTIMATED")
