from __future__ import annotations

import difflib
from pathlib import Path

from aura_refactor_output_record import (
    PASS,
    RefactorOutputRecord,
    finalize_record,
    gate,
    record_non_executable_output,
)
from aura_refactor_patch_evaluator import EvaluationSpec, evaluate


def _fixture(root: Path) -> Path:
    fixture = root / "fixture"
    fixture.mkdir()
    (fixture / "calc.py").write_text(
        "def mean(values):\n"
        "    return sum(values) / len(values)\n\n"
        "def public_total(values):\n"
        "    return sum(values)\n",
        encoding="utf-8",
    )
    (fixture / "notes.py").write_text("NOTE = 'unchanged'\n", encoding="utf-8")
    (fixture / "tests_visible.py").write_text(
        "from calc import mean\n\n"
        "def test_regular_mean():\n"
        "    assert mean([2, 4]) == 3\n",
        encoding="utf-8",
    )
    (fixture / "tests_hidden.py").write_text(
        "from calc import mean\n\n"
        "def test_empty_mean():\n"
        "    assert mean([]) == 0.0\n",
        encoding="utf-8",
    )
    (fixture / "tests_regression.py").write_text(
        "from calc import public_total\n\n"
        "def test_public_total_unchanged():\n"
        "    assert public_total([1, 2, 3]) == 6\n",
        encoding="utf-8",
    )
    return fixture


def _diff(path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def _spec(
    tmp_path: Path,
    *,
    patch_text: str,
    allowed_files: tuple[str, ...],
    case_id: str,
) -> EvaluationSpec:
    fixture = _fixture(tmp_path)
    patch_file = tmp_path / f"{case_id}.patch"
    patch_file.write_text(patch_text, encoding="utf-8")
    return EvaluationSpec(
        benchmark_id="quality-calibration",
        run_id="RUN-1",
        case_id=case_id,
        arm_id="fixture-arm",
        method="calibration",
        objective="Handle empty means without changing the public API.",
        fixture_root=fixture,
        patch_file=patch_file,
        allowed_files=allowed_files,
        visible_test_paths=("tests_visible.py",),
        hidden_test_paths=("tests_hidden.py",),
        regression_test_paths=("tests_regression.py",),
        protected_api_files=("calc.py",),
        required_gates=(
            "patch_apply",
            "compile",
            "visible_tests",
            "hidden_tests",
            "regression_tests",
            "api_compatibility",
            "scope",
        ),
        token_usage={
            "input_tokens_estimated": 120,
            "output_tokens_estimated": 40,
            "input_tokens_reported": None,
            "output_tokens_reported": None,
        },
    )


def test_accepted_patch_records_executable_engineering_quality(tmp_path: Path) -> None:
    before = (
        "def mean(values):\n"
        "    return sum(values) / len(values)\n\n"
        "def public_total(values):\n"
        "    return sum(values)\n"
    )
    after = (
        "def mean(values):\n"
        "    if not values:\n"
        "        return 0.0\n"
        "    return sum(values) / len(values)\n\n"
        "def public_total(values):\n"
        "    return sum(values)\n"
    )
    record = evaluate(
        _spec(
            tmp_path,
            patch_text=_diff("calc.py", before, after),
            allowed_files=("calc.py",),
            case_id="accepted",
        )
    )
    assert record.working_status == "WORKING"
    assert record.disposition == "ACCEPTED"
    assert record.mandatory_gate_passed is True
    assert record.gates["visible_tests"]["status"] == PASS
    assert record.gates["hidden_tests"]["status"] == PASS
    assert record.gates["regression_tests"]["status"] == PASS
    assert record.gates["api_compatibility"]["status"] == PASS
    assert record.observed_quality_score is not None
    assert record.patch_stats["files_touched"] == ["calc.py"]


def test_working_patch_keeps_all_quality_evidence_when_scope_gate_fails(tmp_path: Path) -> None:
    calc_before = (
        "def mean(values):\n"
        "    return sum(values) / len(values)\n\n"
        "def public_total(values):\n"
        "    return sum(values)\n"
    )
    calc_after = (
        "def mean(values):\n"
        "    if not values:\n"
        "        return 0.0\n"
        "    return sum(values) / len(values)\n\n"
        "def public_total(values):\n"
        "    return sum(values)\n"
    )
    patch = _diff("calc.py", calc_before, calc_after)
    patch += _diff("notes.py", "NOTE = 'unchanged'\n", "NOTE = 'unnecessary edit'\n")
    record = evaluate(
        _spec(
            tmp_path,
            patch_text=patch,
            allowed_files=("calc.py",),
            case_id="working-scope-fail",
        )
    )
    assert record.working_status == "WORKING"
    assert record.disposition == "WORKED_BUT_NOT_ACCEPTABLE"
    assert record.mandatory_gate_passed is False
    assert record.failed_required_gates == ["scope"]
    assert record.gates["visible_tests"]["status"] == PASS
    assert record.gates["hidden_tests"]["status"] == PASS
    assert record.gates["regression_tests"]["status"] == PASS
    assert record.gates["scope"]["status"] == "FAIL"
    assert record.gates["scope"]["evidence"]["out_of_scope_files"] == ["notes.py"]
    assert record.observed_quality_score is not None


def test_partial_patch_records_passing_hidden_behavior_and_failed_visible_behavior(tmp_path: Path) -> None:
    before = (
        "def mean(values):\n"
        "    return sum(values) / len(values)\n\n"
        "def public_total(values):\n"
        "    return sum(values)\n"
    )
    after = (
        "def mean(values):\n"
        "    return 0.0\n\n"
        "def public_total(values):\n"
        "    return sum(values)\n"
    )
    record = evaluate(
        _spec(
            tmp_path,
            patch_text=_diff("calc.py", before, after),
            allowed_files=("calc.py",),
            case_id="partial",
        )
    )
    assert record.working_status == "PARTIALLY_WORKING"
    assert record.disposition == "PARTIAL"
    assert record.gates["visible_tests"]["status"] == "FAIL"
    assert record.gates["hidden_tests"]["status"] == PASS
    assert record.gates["regression_tests"]["status"] == PASS
    assert "visible_tests" in record.failed_required_gates


def test_planning_and_synthetic_results_are_not_relabelled_as_code_quality() -> None:
    record = record_non_executable_output(
        benchmark_id="architect-v2",
        run_id="RUN-PLAN",
        case_id="council",
        arm_id="aura_architect_council",
        method="COUNCIL_PLAN",
        output_kind="PLAN_ONLY",
        objective="Produce a refactor plan.",
        reason="No executable patch was produced by this arm.",
        token_usage={"input_tokens_estimated": 1000, "output_tokens_estimated": 100},
        planning_metrics={"grounded_plan_quality": 0.9625},
    )
    assert record.disposition == "CODE_QUALITY_UNAVAILABLE"
    assert record.working_status == "UNDETERMINED"
    assert record.observed_quality_score is None
    assert record.workload["planning_metrics"]["grounded_plan_quality"] == 0.9625


def test_finalize_record_can_report_working_but_security_gate_failed() -> None:
    record = RefactorOutputRecord(benchmark_id="direct", case_id="security")
    record.gates = {
        "patch_apply": gate(PASS),
        "compile": gate(PASS),
        "visible_tests": gate(PASS, passed=10, total=10),
        "hidden_tests": gate(PASS, passed=5, total=5),
        "regression_tests": gate(PASS, passed=20, total=20),
        "api_compatibility": gate(PASS),
        "scope": gate(PASS),
        "security": gate("FAIL", reason="Static security analysis found a new issue."),
        "maintainability": gate(PASS),
        "static_analysis": gate(PASS),
        "performance": gate(NOT_MEASURED),
        "portability": gate(NOT_MEASURED),
    }
    finalized = finalize_record(record)
    assert finalized.working_status == "WORKING"
    assert finalized.disposition == "WORKED_BUT_NOT_ACCEPTABLE"
    assert finalized.failed_required_gates == ["security"]
    assert finalized.component_scores["security"] == 0.0
