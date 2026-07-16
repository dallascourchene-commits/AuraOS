"""Standard record for engineering quality of generated refactor code.

Planning, orchestration, and executable code quality are separate dimensions.
Every measured result is retained even when mandatory acceptance gates fail. A
patch may therefore be classified ``WORKED_BUT_NOT_ACCEPTABLE`` while preserving
its passing tests, complexity, token usage, and all failed-gate evidence.

The evidence vocabulary maps to ISO/IEC 25010:2023, ISO/IEC 5055:2021, NIST SSDF
1.1, OWASP SAMM, and SWE-bench-style isolated patch evaluation. This mapping is
not a claim of formal certification or standards conformance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Any, Iterable

RECORD_VERSION = "AURA_REFACTOR_OUTPUT_RECORD_V1"
QUALITY_STANDARD_VERSION = "AURA_REFACTOR_CODE_QUALITY_STANDARD_V1"

PASS = "PASS"
FAIL = "FAIL"
UNAVAILABLE = "UNAVAILABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"
NOT_MEASURED = "NOT_MEASURED"

DEFAULT_REQUIRED_GATES = (
    "patch_apply",
    "compile",
    "visible_tests",
    "hidden_tests",
    "regression_tests",
    "api_compatibility",
    "scope",
    "security",
)

STANDARD_MAPPING = {
    "functional_suitability": {
        "reference": "ISO/IEC 25010:2023",
        "evidence": ["visible_tests", "hidden_tests"],
    },
    "reliability": {
        "reference": "ISO/IEC 25010:2023 and ISO/IEC 5055:2021",
        "evidence": ["compile", "regression_tests"],
    },
    "compatibility": {
        "reference": "ISO/IEC 25010:2023",
        "evidence": ["api_compatibility"],
    },
    "security": {
        "reference": "ISO/IEC 25010:2023, ISO/IEC 5055:2021, NIST SSDF 1.1, OWASP SAMM",
        "evidence": ["security"],
    },
    "maintainability": {
        "reference": "ISO/IEC 25010:2023 and ISO/IEC 5055:2021",
        "evidence": ["maintainability", "scope", "static_analysis"],
    },
    "performance_efficiency": {
        "reference": "ISO/IEC 25010:2023 and ISO/IEC 5055:2021",
        "evidence": ["performance"],
    },
    "portability": {
        "reference": "ISO/IEC 25010:2023",
        "evidence": ["portability"],
    },
    "isolated_issue_resolution": {
        "reference": "SWE-bench-style methodology",
        "evidence": ["patch_apply", "hidden_tests", "regression_tests"],
    },
}

GATE_WEIGHTS = {
    "patch_apply": 5.0,
    "compile": 10.0,
    "visible_tests": 10.0,
    "hidden_tests": 25.0,
    "regression_tests": 15.0,
    "api_compatibility": 10.0,
    "scope": 5.0,
    "security": 10.0,
    "maintainability": 5.0,
    "static_analysis": 2.5,
    "performance": 1.5,
    "portability": 1.0,
}


@dataclass
class RefactorOutputRecord:
    record_version: str = RECORD_VERSION
    quality_standard_version: str = QUALITY_STANDARD_VERSION
    benchmark_id: str = ""
    run_id: str = ""
    case_id: str = ""
    arm_id: str = ""
    method: str = ""
    output_kind: str = "UNIFIED_DIFF"
    repository_commit_sha: str = ""
    objective: str = ""
    model: str = ""
    provider: str = ""
    prompt_digest: str = ""
    response_digest: str = ""
    patch_digest: str = ""
    token_usage: dict[str, Any] = field(default_factory=dict)
    workload: dict[str, Any] = field(default_factory=dict)
    patch_stats: dict[str, Any] = field(default_factory=dict)
    gates: dict[str, Any] = field(default_factory=dict)
    engineering_metrics: dict[str, Any] = field(default_factory=dict)
    component_scores: dict[str, float | None] = field(default_factory=dict)
    observed_quality_score: float | None = None
    benchmark_quality_score: float | None = None
    measurement_completeness_pct: float = 0.0
    working_status: str = "UNDETERMINED"
    mandatory_gate_passed: bool = False
    failed_required_gates: list[str] = field(default_factory=list)
    disposition: str = "UNASSESSED"
    standards_mapping: dict[str, Any] = field(default_factory=lambda: dict(STANDARD_MAPPING))
    limitations: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def gate(
    status: str,
    *,
    passed: int | None = None,
    total: int | None = None,
    reason: str = "",
    evidence: Any = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"status": status}
    if passed is not None:
        row["passed"] = int(passed)
    if total is not None:
        row["total"] = int(total)
        row["pass_rate"] = round(int(passed or 0) / max(1, int(total)), 4)
    if reason:
        row["reason"] = reason
    if evidence is not None:
        row["evidence"] = evidence
    return row


def _gate_score(value: dict[str, Any]) -> float | None:
    status = value.get("status")
    if status in {None, NOT_MEASURED, UNAVAILABLE, NOT_APPLICABLE}:
        return None
    if "pass_rate" in value:
        return max(0.0, min(1.0, float(value["pass_rate"])))
    return 1.0 if status == PASS else 0.0


def finalize_record(
    record: RefactorOutputRecord,
    *,
    required_gates: Iterable[str] = DEFAULT_REQUIRED_GATES,
) -> RefactorOutputRecord:
    """Calculate scores and disposition without discarding failed-gate metrics."""
    scores = {
        name: _gate_score(record.gates.get(name, {"status": NOT_MEASURED}))
        for name in GATE_WEIGHTS
    }
    record.component_scores = scores
    total_weight = sum(GATE_WEIGHTS.values())
    measured_weight = sum(
        GATE_WEIGHTS[name] for name, score in scores.items() if score is not None
    )
    observed_points = sum(
        GATE_WEIGHTS[name] * float(score)
        for name, score in scores.items()
        if score is not None
    )
    benchmark_points = sum(
        GATE_WEIGHTS[name] * float(score or 0.0)
        for name, score in scores.items()
    )
    record.observed_quality_score = (
        round(100.0 * observed_points / measured_weight, 2)
        if measured_weight
        else None
    )
    record.benchmark_quality_score = round(100.0 * benchmark_points / total_weight, 2)
    record.measurement_completeness_pct = round(100.0 * measured_weight / total_weight, 2)

    required = tuple(required_gates)
    record.failed_required_gates = [
        name for name in required
        if record.gates.get(name, {}).get("status") != PASS
    ]
    record.mandatory_gate_passed = not record.failed_required_gates

    apply_ok = record.gates.get("patch_apply", {}).get("status") == PASS
    compile_ok = record.gates.get("compile", {}).get("status") == PASS
    functional = [
        record.gates.get("visible_tests", {}),
        record.gates.get("hidden_tests", {}),
    ]
    measured_functional = [
        item for item in functional
        if item.get("status") not in {None, NOT_MEASURED, UNAVAILABLE, NOT_APPLICABLE}
    ]
    if not apply_ok or not compile_ok:
        record.working_status = "NOT_WORKING"
    elif not measured_functional:
        record.working_status = "UNDETERMINED"
    elif all(item.get("status") == PASS for item in measured_functional):
        record.working_status = "WORKING"
    elif any(int(item.get("passed") or 0) > 0 for item in measured_functional):
        record.working_status = "PARTIALLY_WORKING"
    else:
        record.working_status = "NOT_WORKING"

    if record.mandatory_gate_passed:
        record.disposition = "ACCEPTED"
    elif record.working_status == "WORKING":
        record.disposition = "WORKED_BUT_NOT_ACCEPTABLE"
    elif record.working_status == "PARTIALLY_WORKING":
        record.disposition = "PARTIAL"
    elif record.working_status == "UNDETERMINED":
        record.disposition = "UNDETERMINED"
    else:
        record.disposition = "FAILED"
    return record


def record_non_executable_output(
    *,
    benchmark_id: str,
    run_id: str,
    case_id: str,
    arm_id: str,
    method: str,
    output_kind: str,
    objective: str,
    reason: str,
    token_usage: dict[str, Any] | None = None,
    planning_metrics: dict[str, Any] | None = None,
) -> RefactorOutputRecord:
    """Record that an arm produced a plan or simulation, not assessable code."""
    record = RefactorOutputRecord(
        benchmark_id=benchmark_id,
        run_id=run_id,
        case_id=case_id,
        arm_id=arm_id,
        method=method,
        output_kind=output_kind,
        objective=objective,
        token_usage=dict(token_usage or {}),
        workload={"planning_metrics": dict(planning_metrics or {})},
        working_status="UNDETERMINED",
        disposition="CODE_QUALITY_UNAVAILABLE",
        limitations=[reason],
    )
    record.gates = {
        name: gate(NOT_MEASURED, reason=reason)
        for name in GATE_WEIGHTS
    }
    record.component_scores = {name: None for name in GATE_WEIGHTS}
    return record


def write_record(path: Path, record: RefactorOutputRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record.to_dict(), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def append_record(path: Path, record: RefactorOutputRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.to_dict(), sort_keys=True, default=str) + "\n")
