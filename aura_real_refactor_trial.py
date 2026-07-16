"""Benchmark Four: use Aura's real hardening refactor as the benchmark task."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any
import xml.etree.ElementTree as ET

from aura_arena_architect_connector import AuraArenaArchitectConnector
from aura_refactor_output_record import (
    NOT_MEASURED,
    PASS,
    RefactorOutputRecord,
    finalize_record,
    gate,
    write_record,
)

TRIAL_VERSION = "AURA_REAL_REFACTOR_TRIAL_V2"
_DEFAULT_ALLOWED = {
    ".aura/CODEMAP.json",
    ".aura/CODEMAP.md",
    ".github/workflows/architect-real-refactor-hardening.yml",
    ".github/workflows/architect-real-refactor-trial.yml",
    ".github/workflows/publish-arena-connector.yml",
    "Dockerfile.arena-connector",
    "aura_agent_arena_mcp_architect.py",
    "aura_arena_architect_connector.py",
    "aura_arena_connector_server.py",
    "aura_cognitive_labor_router.py",
    "aura_native_model_gateway.py",
    "aura_real_refactor_trial.py",
    "aura_refactor_state_identity.py",
    "aura_refactor_state_ledger.py",
    "aura_refactor_state_ledger_core.py",
    "aura_refactor_state_ledger_metrics.py",
    "benchmarks/real_refactor_trial/plans.json",
    "docker-compose.arena-connector.yml",
    "docs/AURA_REAL_REFACTOR_TRIAL_V1.md",
    "tests/conftest.py",
    "tests/test_aura_arena_connector_hardening.py",
    "tests/test_aura_benchmark_four.py",
    "tests/test_aura_benchmark_four_hardening.py",
    "tests/test_aura_state_identity_cycles.py",
}


def _junit(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {
            "status": NOT_MEASURED,
            "tests": None,
            "passed": None,
            "failures": None,
            "errors": None,
            "skipped": None,
        }
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.attrib.get(key, 0) or 0)
    passed = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    return {
        "status": PASS if totals["failures"] == 0 and totals["errors"] == 0 else "FAIL",
        **totals,
        "passed": passed,
    }


def _git_diff(repo_root: Path, base_sha: str, head_sha: str) -> tuple[list[str], str]:
    if not base_sha or not head_sha:
        return [], ""
    try:
        names = subprocess.run(
            ["git", "diff", "--name-only", base_sha, head_sha],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout
        patch = subprocess.run(
            ["git", "diff", "--binary", base_sha, head_sha],
            cwd=repo_root,
            capture_output=True,
            check=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return [], ""
    files = [line.strip() for line in names.splitlines() if line.strip()]
    return files, hashlib.blake2b(patch, digest_size=16).hexdigest() if patch else ""


def _test_gate(result: dict[str, Any], label: str) -> dict[str, Any]:
    if result["status"] == NOT_MEASURED:
        return gate(NOT_MEASURED, reason=f"{label} JUnit was not supplied")
    return gate(
        str(result["status"]),
        passed=int(result["passed"] or 0),
        total=int(result["tests"] or 0),
        evidence={
            "failures": result["failures"],
            "errors": result["errors"],
            "skipped": result["skipped"],
        },
    )


def run_trial(
    *,
    repo_root: Path,
    plans_path: Path,
    output_dir: Path,
    visible_junit_path: Path | None = None,
    hidden_junit_path: Path | None = None,
    regression_junit_path: Path | None = None,
    gate_evidence_path: Path | None = None,
    base_sha: str = "",
    head_sha: str = "",
) -> dict[str, Any]:
    payload = json.loads(plans_path.read_text(encoding="utf-8"))
    trial_base = str(payload.get("trial_base_sha") or base_sha)
    connector = AuraArenaArchitectConnector(repo_root, bridge=object())
    comparison = connector.compare_plans(
        objective=str(payload["objective"]),
        candidates=list(payload["candidates"]),
        required_capabilities=list(payload["required_capabilities"]),
        record=False,
    )
    visible = _junit(visible_junit_path)
    hidden = _junit(hidden_junit_path)
    regression = _junit(regression_junit_path)
    gates = (
        json.loads(gate_evidence_path.read_text(encoding="utf-8"))
        if gate_evidence_path and gate_evidence_path.is_file()
        else {}
    )
    changed_files, patch_digest = _git_diff(repo_root, trial_base, head_sha)
    allowed = set(payload.get("allowed_support_files") or _DEFAULT_ALLOWED)
    out_of_scope = sorted(set(changed_files) - allowed)
    expected = str(payload["expected_selected_candidate_id"])
    selected_ok = comparison["selected_candidate_id"] == expected

    record = RefactorOutputRecord(
        benchmark_id=str(payload.get("benchmark_id") or TRIAL_VERSION),
        run_id=head_sha[:16] or "LOCAL",
        case_id="real-aura-hardening-refactor",
        arm_id=comparison["selected_candidate_id"],
        method="SELECTIVE_COUNCIL_V3_PLAN_PLUS_BOUNDED_SURGEON",
        output_kind="REAL_BRANCH_REFACTOR",
        repository_commit_sha=head_sha,
        objective=str(payload["objective"]),
        model="Aura Architect/Council V3 assisted implementation",
        provider="mixed_assisted_real_branch",
        prompt_digest=hashlib.blake2b(str(payload["objective"]).encode(), digest_size=16).hexdigest(),
        response_digest=str(comparison["selection_digest"]),
        patch_digest=patch_digest,
        workload={
            "trial_base_sha": trial_base,
            "selected_plan_expected": expected,
            "selected_plan_match": selected_ok,
            "plan_comparison": comparison,
            "prior_evidence": payload.get("prior_evidence", {}),
            "review_source": "uploaded independent adversarial feedback plus manual CodeRabbit-style review",
        },
        patch_stats={
            "file_count": len(changed_files),
            "files_touched": changed_files,
            "out_of_scope_files": out_of_scope,
        },
        limitations=[
            "The plan comparison is deterministic Council V3 profile scoring, not independent live provider generation.",
            "The refactor was produced in an assisted session rather than a blinded competition between providers.",
            "Collection-order history is a deterministic fallback; exact temporal provenance requires canonical event_history.",
            "Performance and published-container availability are not established until separately measured and released.",
        ],
        evidence_refs=[
            "benchmark-four-visible.xml",
            "benchmark-four-hidden.xml",
            "benchmark-four-regression.xml",
            "benchmark-four-gates.json",
        ],
    )
    record.gates = {
        "patch_apply": gate(PASS if patch_digest and changed_files else "FAIL", evidence={"base_sha": trial_base, "head_sha": head_sha, "patch_digest": patch_digest}),
        "compile": gate(str(gates.get("compile") or NOT_MEASURED)),
        "visible_tests": _test_gate(visible, "visible/property"),
        "hidden_tests": _test_gate(hidden, "review-derived adversarial"),
        "regression_tests": _test_gate(regression, "regression"),
        "api_compatibility": gate(str(gates.get("api_compatibility") or NOT_MEASURED)),
        "scope": gate(PASS if not out_of_scope else "FAIL", evidence={"allowed_file_count": len(allowed), "out_of_scope_files": out_of_scope}),
        "security": gate(str(gates.get("security") or NOT_MEASURED)),
        "maintainability": gate(NOT_MEASURED, reason="No calibrated maintainability delta was run for the real branch trial."),
        "static_analysis": gate(str(gates.get("static_analysis") or NOT_MEASURED)),
        "performance": gate(NOT_MEASURED, reason="No calibrated latency or resource threshold was run."),
        "portability": gate(str(gates.get("container_build") or NOT_MEASURED), evidence={"pull_only_compose": True, "loopback_default": True}),
    }
    record.engineering_metrics = {
        "history_reconstructability": gates.get("history_reconstructability", NOT_MEASURED),
        "record_redaction": gates.get("record_redaction", NOT_MEASURED),
        "proposal_only_authority": gates.get("proposal_only_authority", NOT_MEASURED),
        "property_tests": gates.get("property_tests", NOT_MEASURED),
    }
    finalized = finalize_record(record)

    result = {
        "trial_version": TRIAL_VERSION,
        "objective": payload["objective"],
        "prior_evidence": payload.get("prior_evidence", {}),
        "plan_comparison": comparison,
        "selected_plan_expected": expected,
        "selected_plan_match": selected_ok,
        "execution_evidence": {
            "visible_junit": visible,
            "hidden_junit": hidden,
            "regression_junit": regression,
            "gates": gates,
            "changed_files": changed_files,
            "base_sha": trial_base,
            "head_sha": head_sha,
            "patch_digest": patch_digest,
        },
        "code_quality_record": finalized.to_dict(),
        "disposition": finalized.disposition,
        "claims": {
            "measured": [
                "three candidate plans were compared by one deterministic Council V3 connector contract",
                "the selected plan was implemented on the real AuraOS branch",
                "visible/property, review-derived adversarial, regression, compile, static, security, scope, and container evidence were recorded",
            ],
            "not_yet_proven": [
                "independent provider generation superiority",
                "general benchmark superiority across repositories",
                "published image availability until the publish workflow completes",
            ],
        },
        "production_mutation": False,
        "human_review_required": True,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "real_refactor_trial.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    write_record(output_dir / "real_refactor_output_record.json", finalized)
    lines = [
        "# Aura Real Refactor Trial V2",
        "",
        f"- Selected plan: **{comparison['selected_candidate_id']}**",
        f"- Expected plan selected: **{selected_ok}**",
        f"- Visible/property tests: **{visible.get('passed')}/{visible.get('tests')} passed**",
        f"- Adversarial/hidden tests: **{hidden.get('passed')}/{hidden.get('tests')} passed**",
        f"- Regression tests: **{regression.get('passed')}/{regression.get('tests')} passed**",
        f"- Standard disposition: **{finalized.disposition}**",
        f"- Observed quality: **{finalized.observed_quality_score}**",
        f"- Benchmark quality: **{finalized.benchmark_quality_score}**",
        f"- Measurement completeness: **{finalized.measurement_completeness_pct}%**",
        "",
        "| Candidate | Score | Token proxy | Critic lanes | Coverage |",
        "|---|---:|---:|---|---:|",
    ]
    for item in comparison["assessments"]:
        lines.append(
            f"| {item['candidate_id']} | {item['score']} | {item['token_proxy']} | "
            f"{', '.join(item['selected_critic_lanes'])} | {item['coverage_fraction']} |"
        )
    (output_dir / "real_refactor_trial.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--plans", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--visible-junit", type=Path)
    parser.add_argument("--hidden-junit", type=Path)
    parser.add_argument("--regression-junit", type=Path)
    parser.add_argument("--gate-evidence", type=Path)
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--head-sha", default="")
    args = parser.parse_args()
    result = run_trial(
        repo_root=args.repo_root.resolve(),
        plans_path=args.plans.resolve(),
        output_dir=args.output_dir.resolve(),
        visible_junit_path=args.visible_junit.resolve() if args.visible_junit else None,
        hidden_junit_path=args.hidden_junit.resolve() if args.hidden_junit else None,
        regression_junit_path=args.regression_junit.resolve() if args.regression_junit else None,
        gate_evidence_path=args.gate_evidence.resolve() if args.gate_evidence else None,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
    )
    print(json.dumps({"selected": result["plan_comparison"]["selected_candidate_id"], "disposition": result["disposition"]}, indent=2))
    return 0 if result["disposition"] == "ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
