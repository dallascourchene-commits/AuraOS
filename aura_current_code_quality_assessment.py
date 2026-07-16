"""Create standardized code-output records for the existing Aura benchmarks.

The current planning arms produce plans, and the hybrid arms use deterministic
synthetic diffs to validate orchestration. Neither is evidence of generated-code
engineering quality. This assessment records that limitation explicitly while
retaining planning, state, routing, and token results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from aura_code_quality_registry import CodeQualityRegistry
from aura_refactor_output_record import record_non_executable_output, write_record

ASSESSMENT_VERSION = "AURA_CURRENT_CODE_OUTPUT_ASSESSMENT_V1"


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=12).hexdigest()


def assess(
    planning_report_path: Path,
    hybrid_report_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    planning = json.loads(planning_report_path.read_text(encoding="utf-8"))
    hybrid = json.loads(hybrid_report_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run_id = f"CODE-QUALITY-{_digest({'planning': planning.get('repository_commit_sha'), 'generated_at': generated_at})}"
    registry = CodeQualityRegistry(output_dir, path=output_dir / "refactor_output_records.jsonl")
    records = []

    planning_methods = {
        "raw_broad_context": "BROAD_CONTEXT_SINGLE_PLANNER",
        "aura_slice_single": "AURA_SLICE_SINGLE_PLANNER",
        "aura_architect_council": "LENGTH_AWARE_ARCHITECT_COUNCIL",
    }
    for arm_id, method in planning_methods.items():
        arm = dict(dict(planning.get("arms") or {}).get(arm_id) or {})
        record = record_non_executable_output(
            benchmark_id=ASSESSMENT_VERSION,
            run_id=run_id,
            case_id=f"planning:{arm_id}",
            arm_id=arm_id,
            method=method,
            output_kind="PLAN_ONLY",
            objective=str(planning.get("objective") or ""),
            reason=(
                "This arm produced a refactor plan, not an executable patch. Planning quality, "
                "grounding, and token efficiency were measured; code-output quality is unavailable."
            ),
            token_usage={
                "model_calls": arm.get("model_calls"),
                "input_tokens_estimated": arm.get("input_tokens"),
                "output_tokens_estimated": arm.get("output_tokens"),
                "total_tokens_estimated": arm.get("total_tokens"),
                "input_tokens_reported": arm.get("input_tokens_reported"),
                "output_tokens_reported": arm.get("output_tokens_reported"),
                "reported_cost_usd": arm.get("reported_cost_usd"),
            },
            planning_metrics={
                "grounded_plan_quality": dict(arm.get("quality") or {}).get("quality_score"),
                "length_profile": arm.get("length_profile"),
            },
        )
        record.repository_commit_sha = str(planning.get("repository_commit_sha") or "")
        record.evidence_refs = [planning_report_path.name, "prompt_manifest.json"]
        write_record(output_dir / f"{arm_id}.code-quality.json", record)
        registry.record(record)
        records.append(record.to_dict())

    for case in list(hybrid.get("cases") or []):
        case_id = str(case.get("case_id") or "hybrid")
        amortization = dict(case.get("token_amortization") or {})
        record = record_non_executable_output(
            benchmark_id=ASSESSMENT_VERSION,
            run_id=run_id,
            case_id=f"hybrid:{case_id}",
            arm_id=case_id,
            method="COUNCIL_PLAN_SYNTHETIC_SURGEON_EXECUTION",
            output_kind="SYNTHETIC_CONTROL_FLOW",
            objective=(
                "Validate state preservation, token amortization, local repair, and Council "
                "replan routing across a multi-step refactor simulation."
            ),
            reason=(
                "The bridge used deterministic synthetic files and generated fixture diffs. "
                "It validates orchestration and accounting, not independent model-generated "
                "patch correctness, maintainability, security, or production regression risk."
            ),
            token_usage={
                "initial_council_input_tokens_estimated": amortization.get("initial_council_input_tokens_estimated"),
                "initial_council_output_tokens_estimated": amortization.get("initial_council_output_tokens_estimated"),
                "surgeon_input_tokens_estimated": amortization.get("surgeon_input_tokens_estimated"),
                "surgeon_output_tokens_estimated": amortization.get("surgeon_output_tokens_estimated"),
                "council_replan_tokens_estimated": amortization.get("council_replan_tokens_estimated"),
                "hybrid_total_tokens_estimated": amortization.get("hybrid_total_tokens_estimated"),
            },
            planning_metrics={
                "terminal_status": case.get("terminal_status"),
                "completed_tasks": case.get("completed_tasks"),
                "state_preservation": case.get("state_preservation"),
                "local_repair_completed_count": case.get("local_repair_completed_count"),
                "council_replan_count": case.get("council_replan_count"),
            },
        )
        record.repository_commit_sha = str(planning.get("repository_commit_sha") or "")
        record.evidence_refs = [hybrid_report_path.name]
        write_record(output_dir / f"{case_id}.code-quality.json", record)
        registry.record(record)
        records.append(record.to_dict())

    summary = {
        "assessment_version": ASSESSMENT_VERSION,
        "run_id": run_id,
        "generated_at": generated_at,
        "repository_commit_sha": planning.get("repository_commit_sha"),
        "record_count": len(records),
        "records": records,
        "assessment": {
            "planning_code_quality": "UNAVAILABLE",
            "hybrid_code_quality": "UNAVAILABLE",
            "reason": (
                "No benchmark arm generated and independently evaluated a real repository patch "
                "against visible, held-out, regression, compatibility, scope, security, and "
                "maintainability gates."
            ),
            "what_is_supported": [
                "planning grounding and contract quality",
                "context and token accounting",
                "synthetic state preservation",
                "synthetic local-repair versus Council-replan routing",
            ],
            "what_is_not_supported": [
                "generated patch correctness",
                "maintainability superiority",
                "security superiority",
                "real repository regression avoidance",
                "production engineering quality superiority",
            ],
        },
        "next_benchmark_requirement": (
            "Each method must produce a unified diff for the same isolated real task and receive "
            "an AURA_REFACTOR_OUTPUT_RECORD_V1 result."
        ),
        "registry": "refactor_output_records.jsonl",
    }
    (output_dir / "current_code_output_assessment.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Current Code-Output Quality Assessment",
        "",
        "| Arm | Output | Code-quality disposition | Why |",
        "|---|---|---|---|",
    ]
    for row in records:
        lines.append(
            f"| `{row['arm_id']}` | `{row['output_kind']}` | `{row['disposition']}` | {row['limitations'][0]} |"
        )
    lines.extend(
        [
            "",
            "The existing planning and synthetic execution results remain valid for their stated dimensions, but they do not measure generated-code engineering quality.",
            "",
        ]
    )
    (output_dir / "current_code_output_assessment.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--planning-report", type=Path, required=True)
    parser.add_argument("--hybrid-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = assess(args.planning_report, args.hybrid_report, args.output_dir)
    print(json.dumps(summary["assessment"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
