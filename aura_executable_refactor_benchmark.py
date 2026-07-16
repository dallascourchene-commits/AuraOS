"""Run standardized engineering-quality evaluation for all executable patch arms."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from aura_code_quality_registry import CodeQualityRegistry
from aura_refactor_patch_evaluator_v2 import EvaluationSpec, evaluate
from aura_refactor_output_record import DEFAULT_REQUIRED_GATES, write_record

BENCHMARK_VERSION = "AURA_EXECUTABLE_REFACTOR_CODE_QUALITY_V1"


def _paths(payload: dict[str, Any], name: str) -> tuple[str, ...]:
    return tuple(str(item) for item in payload.get(name, []) or [])


def _load_spec(path: Path) -> EvaluationSpec:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return EvaluationSpec(
        benchmark_id=str(payload["benchmark_id"]),
        run_id=str(payload["run_id"]),
        case_id=str(payload["case_id"]),
        arm_id=str(payload["arm_id"]),
        method=str(payload["method"]),
        objective=str(payload["objective"]),
        fixture_root=Path(payload["fixture_root"]),
        patch_file=Path(payload["patch_file"]),
        allowed_files=_paths(payload, "allowed_files"),
        visible_test_paths=_paths(payload, "visible_test_paths"),
        hidden_test_paths=_paths(payload, "hidden_test_paths"),
        regression_test_paths=_paths(payload, "regression_test_paths"),
        protected_api_files=_paths(payload, "protected_api_files"),
        required_gates=_paths(payload, "required_gates") or DEFAULT_REQUIRED_GATES,
        run_ruff=bool(payload.get("run_ruff", False)),
        run_mypy=bool(payload.get("run_mypy", False)),
        run_bandit=bool(payload.get("run_bandit", False)),
        model=str(payload.get("model", "")),
        provider=str(payload.get("provider", "")),
        repository_commit_sha=str(payload.get("repository_commit_sha", "")),
        prompt_digest=str(payload.get("prompt_digest", "")),
        response_digest=str(payload.get("response_digest", "")),
        token_usage=dict(payload.get("token_usage") or {}),
        workload=dict(payload.get("workload") or {}),
        supplemental_metrics=dict(payload.get("supplemental_metrics") or {}),
        timeout_seconds=int(payload.get("timeout_seconds", 60)),
    )


def _pct_reduction(before: int | None, after: int | None) -> float | None:
    if before is None or after is None or before <= 0:
        return None
    return round((before - after) / before * 100.0, 2)


def run(fixture_dir: Path, output_dir: Path) -> dict[str, Any]:
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    registry = CodeQualityRegistry(output_dir, path=output_dir / "refactor_output_records.jsonl")
    records: dict[str, dict[str, Any]] = {}
    for arm in manifest["arms"]:
        spec_path = Path(arm["spec"])
        record = evaluate(_load_spec(spec_path))
        output_path = output_dir / f"{record.arm_id}.refactor-output.json"
        write_record(output_path, record)
        registry.record(record)
        records[record.arm_id] = record.to_dict()

    v2 = records["council_v2"]
    v3 = records["council_v3"]
    v2_tokens = v2["token_usage"].get("total_tokens_estimated")
    v3_tokens = v3["token_usage"].get("total_tokens_estimated")
    comparison = {
        "v3_vs_v2_total_token_reduction_pct": _pct_reduction(v2_tokens, v3_tokens),
        "v3_vs_v2_observed_quality_delta": _delta(v3.get("observed_quality_score"), v2.get("observed_quality_score")),
        "v3_vs_v2_benchmark_quality_delta": _delta(v3.get("benchmark_quality_score"), v2.get("benchmark_quality_score")),
        "v3_vs_v2_same_patch_digest": v3.get("patch_digest") == v2.get("patch_digest"),
        "v3_vs_v2_same_disposition": v3.get("disposition") == v2.get("disposition"),
        "v3_better_quality_adjusted_efficiency": (
            v3.get("disposition") == v2.get("disposition")
            and float(v3.get("benchmark_quality_score") or 0.0) >= float(v2.get("benchmark_quality_score") or 0.0)
            and (v3_tokens or 0) < (v2_tokens or 0)
        ),
    }
    summary = {
        "benchmark_version": BENCHMARK_VERSION,
        "fixture_version": manifest.get("fixture_version"),
        "objective": manifest.get("objective"),
        "records": records,
        "comparison": comparison,
        "limitations": list(manifest.get("limitations") or []) + [
            "This is an executable controlled fixture, not a full AuraOS production refactor.",
            "Patch fixtures are single-session assisted and not blinded independent model trials.",
            "Council V2 and V3 intentionally share one patch so the V3 comparison isolates calling-policy efficiency."
        ],
        "standards": [
            "ISO/IEC 25010:2023",
            "ISO/IEC 5055:2021",
            "NIST SP 800-218 SSDF 1.1",
            "OWASP SAMM",
            "SWE-bench-style isolated patch and held-out test evaluation"
        ],
    }
    (output_dir / "executable_refactor_benchmark.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    _write_markdown(summary, output_dir / "executable_refactor_benchmark.md")
    return summary


def _delta(after: Any, before: Any) -> float | None:
    if after is None or before is None:
        return None
    return round(float(after) - float(before), 2)


def _test_fraction(gate_value: dict[str, Any]) -> str:
    passed = gate_value.get("passed")
    total = gate_value.get("total")
    status = gate_value.get("status")
    if passed is None or total is None:
        return str(status)
    return f"{passed}/{total} {status}"


def _write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Executable Refactor Code-Quality Benchmark",
        "",
        "| Arm | Working status | Disposition | Visible | Hidden | Regression | API | Scope | Security | Observed score | Benchmark score | Completeness | Total token proxy |",
        "|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|",
    ]
    order = ("broad_context", "slice_surgeon", "council_v2", "council_v3")
    for arm_id in order:
        record = summary["records"][arm_id]
        gates = record["gates"]
        lines.append(
            "| {arm} | `{working}` | `{disposition}` | {visible} | {hidden} | {regression} | {api} | {scope} | {security} | {observed} | {benchmark} | {complete}% | {tokens} |".format(
                arm=arm_id,
                working=record["working_status"],
                disposition=record["disposition"],
                visible=_test_fraction(gates["visible_tests"]),
                hidden=_test_fraction(gates["hidden_tests"]),
                regression=_test_fraction(gates["regression_tests"]),
                api=gates["api_compatibility"]["status"],
                scope=gates["scope"]["status"],
                security=gates["security"]["status"],
                observed=record["observed_quality_score"],
                benchmark=record["benchmark_quality_score"],
                complete=record["measurement_completeness_pct"],
                tokens=record["token_usage"].get("total_tokens_estimated"),
            )
        )
    comparison = summary["comparison"]
    lines.extend(
        [
            "",
            "## Selective Council result",
            "",
            f"- V3 vs V2 total-token reduction: **{comparison['v3_vs_v2_total_token_reduction_pct']}%**",
            f"- Observed code-quality delta: **{comparison['v3_vs_v2_observed_quality_delta']}**",
            f"- Benchmark code-quality delta: **{comparison['v3_vs_v2_benchmark_quality_delta']}**",
            f"- Same executable patch: **{comparison['v3_vs_v2_same_patch_digest']}**",
            f"- Same disposition: **{comparison['v3_vs_v2_same_disposition']}**",
            f"- Better quality-adjusted efficiency on this fixture: **{comparison['v3_better_quality_adjusted_efficiency']}**",
            "",
            "All partial and failed-gate evidence remains in the per-arm JSON records.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.fixture_dir.resolve(), args.output_dir.resolve())
    print(json.dumps(summary["comparison"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
