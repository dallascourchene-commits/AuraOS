"""Second Architect benchmark iteration.

V2 reuses the original RAW and Aura-slice arms, routes the Council through the
length-aware V2 implementation, records every exact prompt, preserves estimated
and provider-reported input/output token fields separately, and appends a compact
run record to Aura's benchmark registry.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import aura_architect_consolidation_benchmark as base
import aura_architect_consolidation_benchmark_refined as refined
from aura_architect_council_v2 import LengthAwareArchitectModelRouter, profile_refactor_length
from aura_benchmark_registry import BenchmarkRegistry, compact_arm_tokens
from aura_external_llm_session import InstrumentedExternalModelCaller

BENCHMARK_V2 = "AURA_ARCHITECT_CONSOLIDATION_BENCHMARK_V2"


def _digest_text(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


def _token_proxy(text: str) -> int:
    return (len(text.encode("utf-8")) + 3) // 4


async def _run_council_v2(root: Path, fixture: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    callback = base.FixtureModelCallback(fixture)
    caller = InstrumentedExternalModelCaller(callback, hard_prompt_token_limit=64_000)
    router = LengthAwareArchitectModelRouter(
        repo_root=root,
        model_caller=caller,
        ledger_path=output_dir / "architect_benchmark_v2_ledger.jsonl",
    )
    decision = await router.plan_with_council(base.OBJECTIVE)
    selected_plan = dict(decision.selected_plan)
    selected_plan["length_profile"] = profile_refactor_length(selected_plan).to_dict()
    selected_score = base.score_plan(root, selected_plan, label="AURA_ARCHITECT_COUNCIL_V2")
    usage = caller.summary()
    calls = list(usage.get("calls", []) or [])
    requests = []
    for index, request in enumerate(callback.requests):
        call = calls[index] if index < len(calls) else {}
        prompt = str(request.get("prompt") or "")
        requests.append(
            {
                "request_index": index + 1,
                "provider": request.get("provider"),
                "role": request.get("role"),
                "meta": request.get("meta"),
                "prompt": prompt,
                "prompt_digest": _digest_text(prompt),
                "input_tokens_estimated": call.get("input_token_estimate", _token_proxy(prompt)),
                "output_tokens_estimated": call.get("output_token_estimate"),
                "input_tokens_reported": call.get("input_tokens"),
                "output_tokens_reported": call.get("output_tokens"),
                "reported_cost_usd": call.get("cost_usd"),
                "response_digest": call.get("response_digest"),
            }
        )
    return {
        "decision": decision.to_dict(),
        "selected_plan": selected_plan,
        "quality": selected_score,
        "model_usage": usage,
        "requests": requests,
        "length_profile": profile_refactor_length(selected_plan).to_dict(),
        "council_version": "AURA_ARCHITECT_COUNCIL_V2",
    }


def _role_totals(calls: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for call in calls:
        role = str(call.get("role") or "unknown")
        row = totals.setdefault(
            role,
            {
                "calls": 0,
                "input_tokens_estimated": 0,
                "output_tokens_estimated": 0,
                "input_tokens_reported": 0,
                "output_tokens_reported": 0,
                "reported_cost_usd": 0.0,
                "reported_input_available": False,
                "reported_output_available": False,
                "reported_cost_available": False,
            },
        )
        row["calls"] += 1
        row["input_tokens_estimated"] += int(call.get("input_token_estimate") or 0)
        row["output_tokens_estimated"] += int(call.get("output_token_estimate") or 0)
        if call.get("input_tokens") is not None:
            row["reported_input_available"] = True
            row["input_tokens_reported"] += int(call.get("input_tokens") or 0)
        if call.get("output_tokens") is not None:
            row["reported_output_available"] = True
            row["output_tokens_reported"] += int(call.get("output_tokens") or 0)
        if call.get("cost_usd") is not None:
            row["reported_cost_available"] = True
            row["reported_cost_usd"] += float(call.get("cost_usd") or 0.0)
    for row in totals.values():
        if not row.pop("reported_input_available"):
            row["input_tokens_reported"] = None
        if not row.pop("reported_output_available"):
            row["output_tokens_reported"] = None
        if not row.pop("reported_cost_available"):
            row["reported_cost_usd"] = None
        elif row["reported_cost_usd"] is not None:
            row["reported_cost_usd"] = round(float(row["reported_cost_usd"]), 8)
    return totals


def _prompt_manifest(output_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    raw = (output_dir / "raw_prompt.txt").read_text(encoding="utf-8")
    sliced = (output_dir / "aura_slice_prompt.txt").read_text(encoding="utf-8")
    requests_path = output_dir / "council_requests.json"
    requests = json.loads(requests_path.read_text(encoding="utf-8")) if requests_path.exists() else []
    entries = [
        {
            "prompt_id": "raw_broad_context",
            "role": "single_planner",
            "exact_text": raw,
            "digest": _digest_text(raw),
            "bytes": len(raw.encode("utf-8")),
            "input_tokens_estimated": _token_proxy(raw),
            "output_tokens_estimated": report["arms"]["raw_broad_context"].get("output_tokens"),
            "input_tokens_reported": None,
            "output_tokens_reported": None,
        },
        {
            "prompt_id": "aura_slice_single",
            "role": "single_planner",
            "exact_text": sliced,
            "digest": _digest_text(sliced),
            "bytes": len(sliced.encode("utf-8")),
            "input_tokens_estimated": _token_proxy(sliced),
            "output_tokens_estimated": report["arms"]["aura_slice_single"].get("output_tokens"),
            "input_tokens_reported": None,
            "output_tokens_reported": None,
        },
    ]
    for item in requests:
        prompt = str(item.get("prompt") or "")
        entries.append(
            {
                "prompt_id": f"council_{int(item.get('request_index') or len(entries) - 1):03d}",
                "role": item.get("role"),
                "provider": item.get("provider"),
                "meta": item.get("meta"),
                "exact_text": prompt,
                "digest": item.get("prompt_digest") or _digest_text(prompt),
                "bytes": len(prompt.encode("utf-8")),
                "input_tokens_estimated": item.get("input_tokens_estimated", item.get("input_token_estimate")),
                "output_tokens_estimated": item.get("output_tokens_estimated"),
                "input_tokens_reported": item.get("input_tokens_reported"),
                "output_tokens_reported": item.get("output_tokens_reported"),
                "reported_cost_usd": item.get("reported_cost_usd"),
                "response_digest": item.get("response_digest"),
            }
        )
    manifest = {
        "version": "AURA_ARCHITECT_PROMPT_MANIFEST_V1",
        "benchmark_version": BENCHMARK_V2,
        "objective_exact": base.OBJECTIVE,
        "plan_instruction_exact": base._plan_instruction(),
        "entry_count": len(entries),
        "entries": entries,
        "measurement_classes": {
            "bytes": "MEASURED_EXACT",
            "input_tokens_estimated": "ESTIMATED_CHAR4_PROXY",
            "output_tokens_estimated": "ESTIMATED_CHAR4_PROXY",
            "input_tokens_reported": "PROVIDER_REPORTED_OR_UNAVAILABLE",
            "output_tokens_reported": "PROVIDER_REPORTED_OR_UNAVAILABLE",
            "reported_cost_usd": "PROVIDER_REPORTED_OR_UNAVAILABLE",
        },
    }
    (output_dir / "prompt_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return manifest


def _enrich(root: Path, output_dir: Path) -> None:
    report_path = output_dir / "architect_consolidation_benchmark.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["benchmark_version"] = BENCHMARK_V2
    council = report["arms"]["aura_architect_council"]
    council["length_profile"] = profile_refactor_length(
        dict(council.get("selected_plan") or {})
    ).to_dict()
    calls = list(dict(council.get("model_usage") or {}).get("calls", []) or [])
    role_totals = _role_totals(calls)
    report["role_token_totals"] = role_totals
    manifest = _prompt_manifest(output_dir, report)
    report["prompt_manifest"] = {
        "path": "prompt_manifest.json",
        "entry_count": manifest["entry_count"],
        "objective_exact": manifest["objective_exact"],
        "plan_instruction_exact": manifest["plan_instruction_exact"],
        "manifest_digest": _digest_text(json.dumps(manifest, sort_keys=True, default=str)),
    }
    for arm in report["arms"].values():
        arm.setdefault("input_tokens_reported", None)
        arm.setdefault("output_tokens_reported", None)
        arm.setdefault("reported_cost_usd", None)
    report.setdefault("limitations", []).append(
        "V2 records exact role prompts and estimated/reported input/output tokens separately; fixture provider usage remains unavailable."
    )
    report.setdefault("limitations", []).append(
        "Length profiling measures plan structure. Multi-step implementation quality requires the separate execution benchmark."
    )
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    base._write_markdown(report, output_dir / "architect_consolidation_benchmark.md")

    run = {
        "benchmark_id": "architect_consolidation",
        "benchmark_version": BENCHMARK_V2,
        "generated_at": report.get("generated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repository_commit_sha": report.get("repository_commit_sha"),
        "objective_hash": _digest_text(base.OBJECTIVE),
        "measurement_class": report.get("measurement_class"),
        "length_profile": council.get("length_profile"),
        "arms": compact_arm_tokens(report),
        "role_token_totals": role_totals,
        "prompt_manifest": report["prompt_manifest"],
        "comparison": report.get("comparison"),
        "report_digest": _digest_text(report_path.read_text(encoding="utf-8")),
        "evidence_refs": [
            "architect_consolidation_benchmark.json",
            "architect_consolidation_benchmark.md",
            "architect_consolidation_skeleton.json",
            "prompt_manifest.json",
            "council_requests.json",
        ],
        "limitations": report.get("limitations"),
    }
    registry = BenchmarkRegistry(root, path=output_dir / "benchmark_registry.jsonl")
    registry_result = registry.record(run)
    (output_dir / "benchmark_registry_result.json").write_text(
        json.dumps(registry_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    base._run_council = _run_council_v2
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", choices=("prepare", "score"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("Aura_Memory/benchmarks/architect_consolidation"))
    parsed, _ = parser.parse_known_args(arguments)
    result = refined.main(arguments)
    if result == 0 and parsed.command == "score":
        root = parsed.repo_root.resolve()
        output_dir = parsed.output_dir if parsed.output_dir.is_absolute() else root / parsed.output_dir
        _enrich(root, output_dir)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
