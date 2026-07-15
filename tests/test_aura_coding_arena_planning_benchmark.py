from dataclasses import replace
import json

import pytest

from aura_coding_arena_planning_benchmark import (
    default_benchmark_cases,
    main,
    run_coding_arena_planning_benchmark,
)
from aura_coding_arena_planning_types import (
    CODING_ARENA_BENCHMARK_VERSION,
    CodingArenaCompatibilityStatus,
)
from aura_event_contracts import canonical_json


def test_default_benchmark_passes_exact_parity_gate():
    report = run_coding_arena_planning_benchmark(repeats=3)

    assert report.version == CODING_ARENA_BENCHMARK_VERSION
    assert report.measurement_class == "EMPIRICAL_FIXTURE_WITH_HEURISTIC_TOKEN_PROXY"
    assert report.total_cases == 5
    assert report.passed_cases == 5
    assert report.total_tasks == 6
    assert report.mapped_actions == 6
    assert report.action_coverage == 1.0
    assert report.deterministic_case_rate == 1.0
    assert report.order_preservation_rate == 1.0
    assert report.verifier_declaration_rate == 1.0
    assert report.mutation_drift_count == 0
    assert report.authority_drift_count == 0
    assert report.identifier_collision_count == 0
    assert report.baseline_bytes > 0
    assert report.candidate_bytes > 0
    assert report.overhead_ratio > 0
    assert report.gate_passed is True


def test_benchmark_output_is_canonical_and_deterministic():
    first = run_coding_arena_planning_benchmark(repeats=3)
    second = run_coding_arena_planning_benchmark(repeats=3)

    assert first.digest == second.digest
    assert first.to_json() == second.to_json()
    assert first.to_json() == canonical_json(json.loads(first.to_json()))


def test_cli_writes_canonical_report(tmp_path):
    output = tmp_path / "p7-benchmark.json"

    status = main(["--output", str(output), "--repeats", "3"])

    text = output.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert status == 0
    assert text == canonical_json(payload) + "\n"
    assert payload["gate_passed"] is True


@pytest.mark.parametrize("repeats", [True, 1, 21, 3.0])
def test_benchmark_rejects_invalid_repeat_counts(repeats):
    with pytest.raises(ValueError):
        run_coding_arena_planning_benchmark(repeats=repeats)


def test_benchmark_fails_when_expected_status_is_misdeclared():
    case = default_benchmark_cases()[0]
    mismatched_expectation = replace(
        case,
        expected_status=CodingArenaCompatibilityStatus.BLOCKED_LEGACY,
    )

    report = run_coding_arena_planning_benchmark(
        cases=(mismatched_expectation,),
        repeats=2,
    )

    assert report.passed_cases == 0
    assert report.gate_passed is False


def test_benchmark_states_scope_and_does_not_claim_general_efficiency():
    report = run_coding_arena_planning_benchmark(repeats=2)
    limitations = " ".join(report.limitations).lower()

    assert "fixture" in limitations
    assert "token" in limitations
    assert "no latency" in limitations
    assert "no" in limitations and "efficiency improvement" in limitations
    assert "never stages patches" in limitations
