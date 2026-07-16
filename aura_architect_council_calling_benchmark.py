"""Ablate Architect Council critic-calling policy on one frozen planning fixture."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Type

import aura_architect_consolidation_benchmark as base
from aura_architect_council_v2 import LengthAwareArchitectModelRouter
from aura_architect_council_v3 import SelectiveArchitectModelRouter
from aura_external_llm_session import InstrumentedExternalModelCaller
from aura_live_architect import ArchitectModelRouter

BENCHMARK_VERSION = "AURA_ARCHITECT_COUNCIL_CALLING_ABLATION_V1"


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _role_totals(calls: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = {}
    for call in calls:
        role = str(call.get("role") or "unknown")
        row = totals.setdefault(role, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        row["calls"] += 1
        row["input_tokens"] += int(call.get("input_token_estimate") or 0)
        row["output_tokens"] += int(call.get("output_token_estimate") or 0)
    return totals


async def _run_arm(
    root: Path,
    fixture: dict[str, Any],
    output_dir: Path,
    *,
    arm_id: str,
    router_type: Type[ArchitectModelRouter],
) -> dict[str, Any]:
    callback = base.FixtureModelCallback(fixture)
    caller = InstrumentedExternalModelCaller(callback, hard_prompt_token_limit=64_000)
    router = router_type(
        repo_root=root,
        model_caller=caller,
        ledger_path=output_dir / f"{arm_id}.ledger.jsonl",
    )
    decision = await router.plan_with_council(base.OBJECTIVE)
    plan = dict(decision.selected_plan)
    quality = base.score_plan(root, plan, label=arm_id)
    usage = caller.summary()
    calls = list(usage.get("calls", []) or [])
    critic_routes = {
        str(candidate.get("candidate_id")): dict(candidate.get("critic_route") or {})
        for candidate in decision.candidates
    }
    return {
        "arm_id": arm_id,
        "selected_plan": plan,
        "selected_plan_digest": _digest(plan),
        "quality": quality,
        "call_count": int(usage.get("call_count") or 0),
        "input_tokens": int(usage.get("input_token_estimate") or 0),
        "output_tokens": int(usage.get("output_token_estimate") or 0),
        "total_tokens": int(usage.get("input_token_estimate") or 0) + int(usage.get("output_token_estimate") or 0),
        "role_totals": _role_totals(calls),
        "critic_report_count": len(decision.critic_reports),
        "critic_lanes": sorted(
            {
                str(report.get("critic_id"))
                for report in decision.critic_reports
                if report.get("critic_id")
            }
        ),
        "critic_routes": critic_routes,
        "judge_decision": decision.judge_decision,
        "requests": [
            {
                "role": request.get("role"),
                "meta": request.get("meta"),
                "prompt_digest": _digest(request.get("prompt", "")),
            }
            for request in callback.requests
        ],
    }


def _pct_reduction(before: int, after: int) -> float | None:
    if before <= 0:
        return None
    return round((before - after) / before * 100.0, 2)


async def run(root: Path, fixture: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    v2 = await _run_arm(
        root,
        fixture,
        output_dir,
        arm_id="COUNCIL_V2_ALL_LENGTH_CRITICS",
        router_type=LengthAwareArchitectModelRouter,
    )
    v3 = await _run_arm(
        root,
        fixture,
        output_dir,
        arm_id="COUNCIL_V3_SELECTIVE_CRITICS",
        router_type=SelectiveArchitectModelRouter,
    )
    report = {
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "objective": base.OBJECTIVE,
        "fixture_model": fixture.get("model"),
        "arms": {"v2": v2, "v3": v3},
        "comparison": {
            "call_reduction_pct": _pct_reduction(v2["call_count"], v3["call_count"]),
            "input_token_reduction_pct": _pct_reduction(v2["input_tokens"], v3["input_tokens"]),
            "total_token_reduction_pct": _pct_reduction(v2["total_tokens"], v3["total_tokens"]),
            "quality_delta": round(v3["quality"]["quality_score"] - v2["quality"]["quality_score"], 4),
            "selected_plan_same": v2["selected_plan_digest"] == v3["selected_plan_digest"],
            "v2_critic_reports": v2["critic_report_count"],
            "v3_critic_reports": v3["critic_report_count"],
        },
        "interpretation": (
            "This ablation isolates Council critic-calling policy on one frozen response fixture. "
            "It measures whether selective routing preserves the selected plan and deterministic "
            "planning score while reducing calls and token proxy. It does not independently measure "
            "generated-code quality; that is evaluated by the separate executable patch benchmark."
        ),
        "limitations": [
            "The response fixture is fixed and single-session assisted, not a blinded provider trial.",
            "Equal selected plans show no loss on this fixture, not general equivalence.",
            "Token values are deterministic estimates unless provider usage is supplied.",
        ],
    }
    return report


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    v2 = report["arms"]["v2"]
    v3 = report["arms"]["v3"]
    comparison = report["comparison"]
    text = f"""# Architect Council Calling Ablation

| Policy | Calls | Critic reports | Input token proxy | Output token proxy | Total token proxy | Planning quality |
|---|---:|---:|---:|---:|---:|---:|
| Council V2, uniform length critics | {v2['call_count']} | {v2['critic_report_count']} | {v2['input_tokens']:,} | {v2['output_tokens']:,} | {v2['total_tokens']:,} | {v2['quality']['quality_score']:.4f} |
| Council V3, selective critics | {v3['call_count']} | {v3['critic_report_count']} | {v3['input_tokens']:,} | {v3['output_tokens']:,} | {v3['total_tokens']:,} | {v3['quality']['quality_score']:.4f} |

- Call reduction: **{comparison['call_reduction_pct']}%**
- Input-token reduction: **{comparison['input_token_reduction_pct']}%**
- Total-token reduction: **{comparison['total_token_reduction_pct']}%**
- Planning-quality delta: **{comparison['quality_delta']:+.4f}**
- Selected plan unchanged: **{comparison['selected_plan_same']}**

{report['interpretation']}
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    fixture = json.loads(args.responses.read_text(encoding="utf-8"))
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = asyncio.run(run(root, fixture, output_dir))
    (output_dir / "council_calling_ablation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, output_dir / "council_calling_ablation.md")
    print(json.dumps(report["comparison"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
