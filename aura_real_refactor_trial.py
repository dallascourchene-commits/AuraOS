"""Benchmark Four: use Aura's real hardening refactor as the benchmark task."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any
import xml.etree.ElementTree as ET

from aura_arena_architect_connector import AuraArenaArchitectConnector

TRIAL_VERSION = "AURA_REAL_REFACTOR_TRIAL_V1"


def _junit(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"status": "NOT_MEASURED", "tests": None, "failures": None, "errors": None, "skipped": None}
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.attrib.get(key, 0) or 0)
    return {
        "status": "PASS" if totals["failures"] == 0 and totals["errors"] == 0 else "FAIL",
        **totals,
        "passed": totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"],
    }


def _changed_files(repo_root: Path, base_sha: str, head_sha: str) -> list[str]:
    if not base_sha or not head_sha:
        return []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_sha, head_sha],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def run_trial(
    *,
    repo_root: Path,
    plans_path: Path,
    output_dir: Path,
    junit_path: Path | None = None,
    gate_evidence_path: Path | None = None,
    base_sha: str = "",
    head_sha: str = "",
) -> dict[str, Any]:
    payload = json.loads(plans_path.read_text(encoding="utf-8"))
    connector = AuraArenaArchitectConnector(repo_root, bridge=object())
    comparison = connector.compare_plans(
        objective=str(payload["objective"]),
        candidates=list(payload["candidates"]),
        required_capabilities=list(payload["required_capabilities"]),
        record=False,
    )
    junit = _junit(junit_path)
    gates = {}
    if gate_evidence_path and gate_evidence_path.is_file():
        gates = json.loads(gate_evidence_path.read_text(encoding="utf-8"))
    expected = str(payload["expected_selected_candidate_id"])
    selected_ok = comparison["selected_candidate_id"] == expected
    required_gate_values = [str(value) for value in gates.values()]
    gates_ok = bool(gates) and all(value == "PASS" for value in required_gate_values)
    tests_ok = junit.get("status") == "PASS"
    result = {
        "trial_version": TRIAL_VERSION,
        "objective": payload["objective"],
        "prior_evidence": payload.get("prior_evidence", {}),
        "plan_comparison": comparison,
        "selected_plan_expected": expected,
        "selected_plan_match": selected_ok,
        "execution_evidence": {
            "junit": junit,
            "gates": gates,
            "changed_files": _changed_files(repo_root, base_sha, head_sha),
            "base_sha": base_sha,
            "head_sha": head_sha,
        },
        "disposition": (
            "READY_FOR_CODERABBIT_OR_MANUAL_REVIEW"
            if selected_ok and tests_ok and gates_ok
            else "NOT_READY"
        ),
        "claims": {
            "measured": [
                "multiple plans were compared by one deterministic Council V3 connector contract",
                "the selected plan was executed on the real AuraOS branch",
                "focused executable tests and declared engineering gates were recorded",
            ],
            "not_yet_proven": [
                "independent provider generation superiority",
                "general benchmark superiority across repositories",
                "container image publication until the publish workflow completes",
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
    lines = [
        "# Aura Real Refactor Trial V1",
        "",
        f"- Selected plan: **{comparison['selected_candidate_id']}**",
        f"- Expected plan selected: **{selected_ok}**",
        f"- Focused tests: **{junit.get('passed')}/{junit.get('tests')} passed**",
        f"- Engineering gates: **{'PASS' if gates_ok else 'FAIL/UNAVAILABLE'}**",
        f"- Disposition: **{result['disposition']}**",
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
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--gate-evidence", type=Path)
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--head-sha", default="")
    args = parser.parse_args()
    result = run_trial(
        repo_root=args.repo_root.resolve(),
        plans_path=args.plans.resolve(),
        output_dir=args.output_dir.resolve(),
        junit_path=args.junit.resolve() if args.junit else None,
        gate_evidence_path=args.gate_evidence.resolve() if args.gate_evidence else None,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
    )
    print(json.dumps({"selected": result["plan_comparison"]["selected_candidate_id"], "disposition": result["disposition"]}, indent=2))
    return 0 if result["disposition"] != "NOT_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
