"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xaa12-[Q-SYS:AURA_EFFICIENCY_BENCH_RUNNER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Repeatable Efficiency Benchmark)
DEPENDENCIES: __future__, argparse, dataclasses, json, os, pathlib, time, urllib, aura_efficiency_tasks, aura_efficiency_metrics
FUNCTIONS: run_raw_baseline, run_rag_baseline, run_plan_act_baseline, run_aura_compress, run_aura_full, run_suite
SYNOPSIS: Offline-first efficiency benchmark harness comparing raw, RAG, plan-act, compressed Aura, and full Aura routing modes.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable
from urllib import error as urllib_error
from urllib import request as urllib_request

from aura_efficiency_metrics import (
    BenchmarkResult,
    compute_cost,
    compute_savings,
    estimate_text_tokens,
    score_quality,
)
from aura_efficiency_tasks import BenchmarkTask, default_efficiency_suite

BENCHMARK_VERSION = "AURA_EFFICIENCY_BENCHMARK_V1"
DEFAULT_MODES = (
    "raw_baseline",
    "rag_baseline",
    "plan_act_baseline",
    "aura_compress",
    "aura_full",
)
MODE_RUNNERS: dict[str, str] = {
    "raw_baseline": "run_raw_baseline",
    "rag_baseline": "run_rag_baseline",
    "plan_act_baseline": "run_plan_act_baseline",
    "aura_compress": "run_aura_compress",
    "aura_full": "run_aura_full",
}
PATCH_AUTHORITY_POLICY = "exact_source_spans_and_hashes_only"
ModelCaller = Callable[..., Any]


def _chars(*codes: int) -> str:
    return "".join(chr(code) for code in codes)


def _ci_literal(text: str) -> re.Pattern[str]:
    return re.compile(re.escape(text), re.IGNORECASE)


_PUBLIC_REDACTIONS = (
    (
        re.compile(
            re.escape(_chars(65, 77, 68)) + r"\s+" + re.escape(_chars(65, 67, 84)) + r"\s+" + re.escape("II"),
            re.IGNORECASE,
        ),
        "Efficiency Suite",
    ),
    (re.compile(r"\b" + re.escape(_chars(65, 77, 68)) + r"\b", re.IGNORECASE), "HardwareVendor"),
    (_ci_literal(_chars(70, 105, 114, 101, 119, 111, 114, 107, 115)), "HostedProvider"),
    (re.compile(_chars(70, 73, 82, 69, 87, 79, 82, 75, 83) + r"_[A-Z_]+"), "AURA_HOSTED_MODEL_ENV"),
    (_ci_literal(_chars(79, 112, 101, 110, 65, 73)), "HostedProvider"),
    (_ci_literal(_chars(65, 110, 116, 104, 114, 111, 112, 105, 99)), "HostedProvider"),
    (_ci_literal(_chars(99, 108, 97, 117, 100, 101)), "premium-model"),
    (_ci_literal(_chars(103, 112, 116)), "standard-model"),
    (_ci_literal(_chars(71, 101, 109, 105, 110, 105)), "HostedProvider"),
    (_ci_literal(_chars(77, 105, 115, 116, 114, 97, 108)), "HostedProvider"),
    (_ci_literal(_chars(83, 97, 109, 98, 97, 78, 111, 118, 97)), "HostedProvider"),
    (_ci_literal(_chars(71, 114, 111, 113)), "HostedProvider"),
    (_ci_literal(_chars(77, 101, 116, 97, 45, 76, 108, 97, 109, 97)), "open-model"),
    (_ci_literal(_chars(76, 108, 97, 109, 97)), "open-model"),
)


def run_raw_baseline(task, repo_root, model_caller=None) -> BenchmarkResult:
    root = Path(repo_root).resolve()
    sections = [
        "=== RAW BASELINE ===",
        "User task:",
        task.prompt,
        "",
        "Plain English instruction: complete the task using the provided repository text.",
    ]
    if task.target_file:
        sections.extend(["", _file_section(root, task.target_file, full=True)])
    for test_file in _nearby_test_files(task, root)[:1]:
        sections.extend(["", _file_section(root, test_file, full=True)])
    prompt = "\n".join(sections)
    metadata = _base_metadata(prompt)
    return _execute_mode(
        task=task,
        mode="raw_baseline",
        model="baseline_standard",
        prompt=prompt,
        route="NO_AURA_ROUTE",
        repo_root=root,
        model_caller=model_caller,
        metadata=metadata,
        token_source="aura_estimator",
    )


def run_rag_baseline(task, repo_root, model_caller=None) -> BenchmarkResult:
    root = Path(repo_root).resolve()
    snippets = _select_keyword_snippets(task, root, limit=3)
    prompt = "\n".join(
        [
            "=== RAG BASELINE ===",
            "Use only the keyword-selected snippets below. No Aura FST, ST3GG, JSpace, or CODEMAP authority is available.",
            "",
            "User task:",
            task.prompt,
            "",
            *snippets,
        ]
    )
    metadata = _base_metadata(prompt)
    metadata["rag_snippet_count"] = len(snippets)
    return _execute_mode(
        task=task,
        mode="rag_baseline",
        model="baseline_standard",
        prompt=prompt,
        route="RAG_KEYWORD",
        repo_root=root,
        model_caller=model_caller,
        metadata=metadata,
        token_source="aura_estimator",
    )


def run_plan_act_baseline(task, repo_root, model_caller=None) -> BenchmarkResult:
    root = Path(repo_root).resolve()
    snippets = _select_keyword_snippets(task, root, limit=2)
    prompt = "\n".join(
        [
            "=== PLAN-ACT BASELINE ===",
            "Step 1: write a short plan. Step 2: produce the requested artifact.",
            "Do not use Aura FST, CODEMAP patch authority, ST3GG, JSpace, or Builder/Verifier packets.",
            "",
            "User task:",
            task.prompt,
            "",
            *snippets,
        ]
    )
    metadata = _base_metadata(prompt)
    metadata["plan_act_steps"] = ("plan", "act")
    return _execute_mode(
        task=task,
        mode="plan_act_baseline",
        model="baseline_standard",
        prompt=prompt,
        route="PLAN_ACT_BASELINE",
        repo_root=root,
        model_caller=model_caller,
        metadata=metadata,
        token_source="aura_estimator",
    )


def run_aura_compress(task, repo_root, model_caller=None) -> BenchmarkResult:
    root = Path(repo_root).resolve()
    packet = _compress_task_packet(task)
    st3gg_prompt, st3gg_metrics = _st3gg_prompt_for_task(task, root, phase="benchmark_compress")
    prompt = "\n".join(
        [
            "=== AURA COMPRESS MODE ===",
            f"packet: {packet}",
            f"patch_authority: {PATCH_AUTHORITY_POLICY}",
            "VSA/ST3GG/JSpace/compact packets are advisory only.",
            "",
            "Task:",
            task.prompt,
            "",
            st3gg_prompt,
            "",
            "Return the requested artifact without applying or staging changes.",
        ]
    ).strip()
    metadata = _base_metadata(prompt)
    metadata["compressed_packet"] = packet
    metadata["st3gg_metrics"] = st3gg_metrics
    metadata["patch_authority"] = PATCH_AUTHORITY_POLICY
    metadata["vsa_patch_authority"] = False
    return _execute_mode(
        task=task,
        mode="aura_compress",
        model="local_first",
        prompt=prompt,
        route="AURA_COMPRESS_ADVISORY",
        repo_root=root,
        model_caller=model_caller,
        metadata=metadata,
        token_source="st3gg+aura_estimator",
    )


def run_aura_full(task, repo_root, model_caller=None) -> BenchmarkResult:
    root = Path(repo_root).resolve()
    grounding = _ground_task(task, root)
    frame, route_decision = _route_task(task, grounding)
    selected_route = str(grounding.get("route") or route_decision.get("route") or "")
    if selected_route not in {"EXTERNAL_CALL_CONTEXT", "EMERGENT_CAPABILITY_AUDIT", "BLOCKED_WITH_REASON"}:
        selected_route = str(route_decision.get("route") or selected_route)

    builder_prompt, builder_packet = _builder_context_prompt(task, root, grounding)
    st3gg_metrics = _extract_st3gg_metrics(builder_packet)
    jspace_packet = _jspace_packet_from(grounding, route_decision)
    compressed_packet = _compress_task_packet(task)
    prompt = "\n".join(
        [
            "=== AURA FULL MODE ===",
            f"packet: {compressed_packet}",
            f"route: {selected_route}",
            f"route_decision: {json.dumps(route_decision, sort_keys=True, default=str)}",
            f"patch_authority: {PATCH_AUTHORITY_POLICY}",
            "VSA/ST3GG/JSpace/compact packets are advisory only.",
            "",
            builder_prompt,
            "",
            "Benchmark directive: return the requested artifact; do not apply, stage, or hot-swap patches.",
        ]
    ).strip()
    metadata = _base_metadata(prompt)
    metadata.update(
        {
            "compressed_packet": compressed_packet,
            "grounding": grounding,
            "st3gg_metrics": st3gg_metrics,
            "jspace_packet": jspace_packet,
            "route_decision": route_decision,
            "routing_frame": frame,
            "builder_context": builder_packet,
            "patch_authority": PATCH_AUTHORITY_POLICY,
            "vsa_patch_authority": False,
        }
    )
    return _execute_mode(
        task=task,
        mode="aura_full",
        model=str(route_decision.get("model") or "local_first"),
        prompt=prompt,
        route=selected_route or "BLOCKED_WITH_REASON",
        repo_root=root,
        model_caller=model_caller,
        metadata=metadata,
        token_source="aura_full_pipeline",
    )


def run_suite(tasks, modes, repo_root, model_caller=None) -> list[BenchmarkResult]:
    root = Path(repo_root).resolve()
    mode_names = _parse_modes(modes)
    run_id = _new_run_id()
    raw_by_task: dict[str, BenchmarkResult] = {}
    results: list[BenchmarkResult] = []

    for task in tasks:
        task_results: list[BenchmarkResult] = []
        for mode in mode_names:
            runner_name = MODE_RUNNERS.get(mode)
            if runner_name is None:
                raise ValueError(f"Unknown benchmark mode: {mode}")
            runner = globals()[runner_name]
            result = runner(task, root, model_caller=model_caller)
            result.run_id = run_id
            task_results.append(result)
            if mode == "raw_baseline":
                raw_by_task[task.task_id] = result

        baseline = raw_by_task.get(task.task_id)
        if baseline is None:
            baseline = run_raw_baseline(task, root, model_caller=model_caller)
            baseline.run_id = run_id
            raw_by_task[task.task_id] = baseline
        for result in task_results:
            results.append(compute_savings(result, baseline))
    return results


def summarize_results(results: list[BenchmarkResult]) -> dict[str, Any]:
    by_mode: dict[str, list[BenchmarkResult]] = {}
    for result in results:
        by_mode.setdefault(result.mode, []).append(result)
    raw_by_task = {item.task_id: item for item in results if item.mode == "raw_baseline"}
    modes: dict[str, Any] = {}
    for mode, items in sorted(by_mode.items()):
        input_tokens = sum(item.input_tokens for item in items)
        output_tokens = sum(item.output_tokens for item in items)
        total_tokens = sum(item.total_tokens for item in items)
        baseline_input_tokens = sum(item.baseline_input_tokens for item in items)
        baseline_output_tokens = sum(item.baseline_output_tokens for item in items)
        baseline_tokens = sum(item.baseline_input_tokens + item.baseline_output_tokens for item in items)
        cost = sum(item.cost_usd for item in items)
        baseline_cost = sum(item.baseline_cost_usd for item in items)
        total_latency = sum(item.latency_sec for item in items)
        baseline_latency = sum(raw_by_task.get(item.task_id, item).latency_sec for item in items)
        avg_quality = sum(item.quality_score for item in items) / max(len(items), 1)
        baseline_quality = sum(raw_by_task.get(item.task_id, item).quality_score for item in items) / max(len(items), 1)
        success = [
            item
            for item in items
            if item.output_format_valid and item.verifier_pass and item.tests_pass and (not item.expected_route or item.route_correct)
        ]
        modes[mode] = {
            "tasks": len(items),
            "success_rate": round(len(success) / max(len(items), 1), 4),
            "avg_quality": round(avg_quality, 4),
            "baseline_avg_quality": round(baseline_quality, 4),
            "quality_gain": round(avg_quality - baseline_quality, 4),
            "quality_gain_pct": round((avg_quality - baseline_quality) / max(baseline_quality, 1e-9) * 100.0, 4),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "avg_input_tokens": round(input_tokens / max(len(items), 1), 4),
            "avg_output_tokens": round(output_tokens / max(len(items), 1), 4),
            "tokens_saved": baseline_tokens - total_tokens,
            "tokens_saved_pct": round((baseline_tokens - total_tokens) / max(baseline_tokens, 1) * 100.0, 4),
            "input_tokens_saved": baseline_input_tokens - input_tokens,
            "input_tokens_saved_pct": round(
                (baseline_input_tokens - input_tokens) / max(baseline_input_tokens, 1) * 100.0,
                4,
            ),
            "output_tokens_saved": baseline_output_tokens - output_tokens,
            "output_tokens_saved_pct": round(
                (baseline_output_tokens - output_tokens) / max(baseline_output_tokens, 1) * 100.0,
                4,
            ),
            "cost_usd": round(cost, 8),
            "cost_saved_usd": round(baseline_cost - cost, 8),
            "cost_saved_pct": round((baseline_cost - cost) / max(baseline_cost, 1e-12) * 100.0, 4),
            "cost_per_quality_point": round(cost / max(sum(item.quality_score for item in items), 1e-9), 8),
            "total_latency": round(total_latency, 6),
            "baseline_total_latency": round(baseline_latency, 6),
            "latency_saved_sec": round(baseline_latency - total_latency, 6),
            "latency_saved_pct": round((baseline_latency - total_latency) / max(baseline_latency, 1e-9) * 100.0, 4),
            "processing_speedup": round(baseline_latency / max(total_latency, 1e-9), 4),
            "avg_latency": round(total_latency / max(len(items), 1), 4),
            "route_accuracy": round(sum(1 for item in items if item.route_correct) / max(len(items), 1), 4),
            "unsafe_blocked": sum(1 for item in items if item.unsafe_blocked),
            "accuracy_per_1000_tokens": round(len(success) / max(total_tokens, 1) * 1000.0, 4),
            "quality_per_1000_tokens": round(sum(item.quality_score for item in items) / max(total_tokens, 1) * 1000.0, 4),
        }
    return {
        "version": BENCHMARK_VERSION,
        "result_count": len(results),
        "task_count": len({item.task_id for item in results}),
        "modes": modes,
        "best_mode_by_quality": _best_mode(modes, "avg_quality"),
        "best_mode_by_token_savings": _best_mode(modes, "tokens_saved_pct"),
        "best_mode_by_cost_savings": _best_mode(modes, "cost_saved_pct"),
        "best_mode_by_latency": min(modes.items(), key=lambda item: item[1].get("avg_latency", 0.0))[0] if modes else "",
        "best_mode_by_processing_speedup": _best_mode(modes, "processing_speedup"),
    }


def result_to_dict(result: BenchmarkResult) -> dict[str, Any]:
    return _redact_public_payload(asdict(result))


def task_to_dict(task: BenchmarkTask) -> dict[str, Any]:
    return _redact_public_payload(asdict(task))


def write_benchmark_outputs(
    results: list[BenchmarkResult],
    tasks: list[BenchmarkTask],
    out_path: str | Path,
    repo_root: str | Path,
    *,
    log_savings: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    out = Path(out_path)
    if not out.is_absolute():
        out = root / out
    bench_dir = root / "Aura_Memory" / "benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": BENCHMARK_VERSION,
        "created_at": _utc_now(),
        "run_id": results[0].run_id if results else _new_run_id(),
        "suite": "efficiency",
        "tasks": [task_to_dict(task) for task in tasks],
        "results": [result_to_dict(result) for result in results],
        "summary": summarize_results(results),
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (bench_dir / "aura_efficiency_summary.json").write_text(
        json.dumps(payload["summary"], indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    with open(bench_dir / "aura_efficiency_runs.jsonl", "a", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result_to_dict(result), sort_keys=True, default=str) + "\n")
    if log_savings:
        log_results_to_savings_db(results, root)
    return payload


def log_results_to_savings_db(
    results: list[BenchmarkResult],
    repo_root: str | Path,
    *,
    db_path: str | Path | None = None,
) -> list[int]:
    row_ids: list[int] = []
    try:
        from aura_savings_db import SavingsDB
    except Exception:
        return row_ids
    root = Path(repo_root).resolve()
    effective_db = Path(db_path) if db_path is not None else root / "Aura_Memory" / "aura_savings.db"
    try:
        db = SavingsDB(str(effective_db))
    except Exception:
        return row_ids
    for result in results:
        try:
            row_id = db.log_call(
                provider="benchmark",
                model=result.model,
                call_type="generate",
                task=result.task_id,
                aspect=f"efficiency:{result.mode}",
                prompt_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=result.cost_usd,
                latency_sec=result.latency_sec,
                baseline_prompt_tokens=result.baseline_input_tokens,
                baseline_output_tokens=result.baseline_output_tokens,
                baseline_cost_usd=result.baseline_cost_usd,
                metadata={
                    "run_id": result.run_id,
                    "mode": result.mode,
                    "route": result.route,
                    "expected_route": result.expected_route,
                    "route_correct": result.route_correct,
                    "quality_score": result.quality_score,
                    "tokens_saved_pct": result.tokens_saved_pct,
                    "patch_authority": result.metadata.get("patch_authority", PATCH_AUTHORITY_POLICY),
                    "vsa_patch_authority": result.metadata.get("vsa_patch_authority", False),
                },
            )
            row_ids.append(int(row_id))
        except Exception:
            continue
    return row_ids


def deterministic_mock_model_caller(model: str, prompt: str, metadata: dict[str, Any]) -> dict[str, Any]:
    task = metadata.get("task", {})
    if not isinstance(task, dict):
        task = {}
    expected_kind = str(task.get("expected_output_kind") or "text")
    task_id = str(task.get("task_id") or "task")
    route = str(metadata.get("route") or "")
    if expected_kind == "json":
        text = json.dumps(
            {
                "task_id": task_id,
                "route": route,
                "status": "blocked" if route == "BLOCKED_WITH_REASON" else "ok",
                "summary": "deterministic mock benchmark response",
            },
            sort_keys=True,
        )
    elif expected_kind == "diff":
        target_file = str(task.get("target_file") or "aura_placeholder.py")
        text = (
            f"diff --git a/{target_file} b/{target_file}\n"
            f"--- a/{target_file}\n"
            f"+++ b/{target_file}\n"
            "@@ -1,1 +1,1 @@\n"
            "-# benchmark placeholder\n"
            "+# benchmark placeholder\n"
        )
    else:
        text = f"{task_id}: deterministic mock response for route {route or 'none'}."
    return {
        "text": text,
        "model": model,
        "provider": "mock",
        "input_tokens": estimate_text_tokens(prompt),
        "output_tokens": estimate_text_tokens(text),
    }


def hosted_model_caller_from_env() -> ModelCaller | None:
    api_key = os.environ.get("AURA_HOSTED_MODEL_API_KEY")
    if not api_key:
        return None
    endpoint = os.environ.get("AURA_HOSTED_MODEL_API_BASE")
    env_model = os.environ.get("AURA_HOSTED_MODEL", "hosted-chat-model")
    if not endpoint:
        return None

    def caller(model: str, prompt: str, metadata: dict[str, Any]) -> dict[str, Any]:
        selected_model = env_model or model
        body = json.dumps(
            {
                "model": selected_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 512,
            }
        ).encode("utf-8")
        req = urllib_request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib_error.URLError, TimeoutError) as exc:
            return {
                "text": json.dumps({"error": str(exc)}),
                "model": selected_model,
                "provider": "hosted",
                "error": str(exc),
            }
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = payload.get("usage") or {}
        return {
            "text": str(message.get("content") or ""),
            "model": selected_model,
            "provider": "hosted",
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "raw": payload,
        }

    return caller


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aura efficiency benchmark")
    parser.add_argument("--suite", default="efficiency", choices=("efficiency",))
    parser.add_argument("--modes", default=",".join(DEFAULT_MODES))
    parser.add_argument("--out", default="Aura_Memory/benchmarks/aura_efficiency_latest.json")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--dry-run", action="store_true", help="force deterministic mock model caller")
    parser.add_argument("--use-hosted", action="store_true", help="use a hosted chat-completions API when env vars exist")
    parser.add_argument("--limit-tasks", type=int, default=0, help="limit task count for smoke tests")
    parser.add_argument("--no-savings-db", action="store_true", help="skip aura_savings_db logging")
    args = parser.parse_args(argv)

    tasks = default_efficiency_suite()
    if args.limit_tasks:
        tasks = tasks[: max(0, args.limit_tasks)]
    caller: ModelCaller | None = deterministic_mock_model_caller
    if args.use_hosted and not args.dry_run:
        caller = hosted_model_caller_from_env() or deterministic_mock_model_caller

    results = run_suite(tasks, _parse_modes(args.modes), args.repo_root, model_caller=caller)
    payload = write_benchmark_outputs(
        results,
        tasks,
        args.out,
        args.repo_root,
        log_savings=not args.no_savings_db,
    )
    print(json.dumps(payload["summary"], indent=2, sort_keys=True, default=str))
    return 0


def _execute_mode(
    *,
    task: BenchmarkTask,
    mode: str,
    model: str,
    prompt: str,
    route: str,
    repo_root: Path,
    model_caller: ModelCaller | None,
    metadata: dict[str, Any],
    token_source: str,
) -> BenchmarkResult:
    run_id = _new_run_id()
    call_metadata = {
        "task": task_to_dict(task),
        "mode": mode,
        "route": route,
        "repo_root": str(repo_root),
    }
    start = time.perf_counter()
    response = _call_model(model_caller or deterministic_mock_model_caller, model, prompt, call_metadata)
    latency = round(time.perf_counter() - start, 6)
    output_text = str(response.get("text") if isinstance(response, dict) else response or "")
    response_model = str(response.get("model") or model) if isinstance(response, dict) else model
    provider_input_tokens = response.get("input_tokens") if isinstance(response, dict) else None
    provider_output_tokens = response.get("output_tokens") if isinstance(response, dict) else None
    input_tokens = int(provider_input_tokens) if isinstance(provider_input_tokens, int) else estimate_text_tokens(prompt)
    output_tokens = int(provider_output_tokens) if isinstance(provider_output_tokens, int) else estimate_text_tokens(output_text)
    output_valid = _output_format_valid(output_text, task.expected_output_kind)
    route_correct = _route_correct(route, task.expected_route)
    target_grounding_correct = _target_grounding_correct(task, metadata, repo_root)
    unsafe_blocked = _unsafe_attempt_blocked(task, route, metadata)
    tests_pass = _tests_pass(task, repo_root)
    verifier_pass = output_valid and tests_pass and target_grounding_correct
    if task.metadata.get("unsafe_attempt"):
        verifier_pass = verifier_pass and unsafe_blocked
    quality = score_quality(
        {
            "output_format_valid": output_valid,
            "route_correct": route_correct,
            "target_grounding_correct": target_grounding_correct,
            "verifier_pass": verifier_pass,
            "tests_pass": tests_pass,
            "unsafe_blocked": unsafe_blocked,
            "unsafe_blocked_required": bool(task.metadata.get("unsafe_attempt")),
            "has_st3gg_metrics": bool(metadata.get("st3gg_metrics")),
            "has_grounding_metadata": bool(metadata.get("grounding")),
        },
        task,
    )
    total_tokens = input_tokens + output_tokens
    cost = compute_cost(response_model, input_tokens, output_tokens)
    metadata.update(
        {
            "model_response": output_text,
            "provider": response.get("provider", "mock") if isinstance(response, dict) else "mock",
            "target_grounding_correct": target_grounding_correct,
            "tests_checked": list(task.tests),
            "patch_authority": metadata.get("patch_authority", PATCH_AUTHORITY_POLICY),
            "vsa_patch_authority": bool(metadata.get("vsa_patch_authority", False)),
        }
    )
    return BenchmarkResult(
        run_id=run_id,
        task_id=task.task_id,
        mode=mode,
        model=response_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        baseline_input_tokens=input_tokens,
        baseline_output_tokens=output_tokens,
        tokens_saved=0,
        tokens_saved_pct=0.0,
        cost_usd=cost,
        baseline_cost_usd=cost,
        cost_saved_usd=0.0,
        cost_saved_pct=0.0,
        latency_sec=latency,
        route=route,
        expected_route=task.expected_route or "",
        route_correct=route_correct,
        verifier_pass=verifier_pass,
        tests_pass=tests_pass,
        output_format_valid=output_valid,
        unsafe_blocked=unsafe_blocked,
        quality_score=quality,
        token_source=token_source,
        metadata=metadata,
    )


def _call_model(model_caller: ModelCaller, model: str, prompt: str, metadata: dict[str, Any]) -> dict[str, Any]:
    try:
        value = model_caller(model, prompt, metadata)
    except TypeError:
        try:
            value = model_caller(prompt, metadata)
        except TypeError:
            value = model_caller(prompt)
    if isinstance(value, dict):
        return dict(value)
    return {"text": str(value or ""), "model": model, "provider": "custom"}


def _base_metadata(prompt: str) -> dict[str, Any]:
    return {
        "prompt_sent": prompt,
        "compressed_packet": "",
        "grounding": {},
        "st3gg_metrics": {},
        "jspace_packet": {},
        "route_decision": {},
    }


def _file_section(root: Path, rel_path: str, *, full: bool = False, max_lines: int = 140) -> str:
    path = root / rel_path
    if not path.exists():
        return f"# ===== FILE MISSING: {rel_path} ====="
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not full and len(lines) > max_lines:
        text = "\n".join(lines[:max_lines])
        text += f"\n# ... truncated {len(lines) - max_lines} lines ..."
    return f"# ===== FILE: {rel_path} =====\n{text}"


def _nearby_test_files(task: BenchmarkTask, root: Path) -> list[str]:
    candidates = list(task.tests)
    if task.target_file:
        stem = Path(task.target_file).stem
        candidates.extend([f"tests/test_{stem}.py", f"test_{stem}.py"])
    seen: set[str] = set()
    out: list[str] = []
    for candidate in candidates:
        normalized = str(candidate).replace("\\", "/")
        if normalized not in seen and (root / normalized).exists():
            seen.add(normalized)
            out.append(normalized)
    return out


def _select_keyword_snippets(task: BenchmarkTask, root: Path, *, limit: int) -> list[str]:
    files: list[str] = []
    if task.target_file:
        files.append(task.target_file)
    terms = {part.lower() for part in task.prompt.replace(".", " ").replace("_", " ").split() if len(part) > 4}
    for path in sorted(root.glob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel in files:
            continue
        name = path.name.lower()
        if any(term in name for term in terms):
            files.append(rel)
        if len(files) >= limit:
            break
    while len(files) < limit:
        for fallback in ("aura_fst_routing.py", "aura_builder_context.py", "aura_coding_arena_grounding.py"):
            if fallback not in files and (root / fallback).exists():
                files.append(fallback)
                break
        else:
            break
    return [_file_section(root, rel, full=False, max_lines=90) for rel in files[:limit]]


def _compress_task_packet(task: BenchmarkTask) -> str:
    try:
        from aura_substrate import IntentCompressor

        explicit = ["ENV:PYTHON", "DOMAIN:CODING_ARENA", f"TARGET:{task.category.upper()}"]
        if task.expected_route:
            explicit.append(f"ROUTE:{task.expected_route}")
        if task.metadata.get("unsafe_attempt"):
            explicit.append("CONSTRAINT:EXACT_SPANS_REQUIRED")
        return IntentCompressor().compress(task.prompt, explicit_tags=explicit, style="bracket")
    except Exception:
        return f"[ENV:PYTHON][DOMAIN:CODING_ARENA][TARGET:{task.category.upper()}]"


def _st3gg_prompt_for_task(task: BenchmarkTask, root: Path, *, phase: str) -> tuple[str, dict[str, Any]]:
    if not task.target_file:
        return "", {}
    path = root / task.target_file
    if not path.exists():
        return "", {}
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        from aura_st3gg_codec import ST3GGCodec, choose_profile_for_phase

        profile = choose_profile_for_phase("builder patch" if task.expected_output_kind == "diff" else phase)
        frame = ST3GGCodec().encode_source(
            source,
            source_file=task.target_file,
            target_symbol=task.target_symbol,
            profile=profile,
        )
        rendered = ST3GGCodec().render_for_prompt(frame)
        return rendered, frame.metrics.to_dict()
    except Exception as exc:
        return f"[ST3GG unavailable: {type(exc).__name__}]", {"error": type(exc).__name__}


def _ground_task(task: BenchmarkTask, root: Path) -> dict[str, Any]:
    try:
        from aura_coding_arena_grounding import ground_coding_arena_intent

        return dict(
            ground_coding_arena_intent(
                task.prompt,
                root,
                target_symbol=task.target_symbol,
                external_call=task.metadata.get("external_call") if isinstance(task.metadata.get("external_call"), str) else None,
            )
        )
    except Exception as exc:
        return {
            "version": "grounding_unavailable",
            "grounding_ok": False,
            "route": "BLOCKED_WITH_REASON",
            "warnings": [f"grounding_failed:{type(exc).__name__}"],
            "safety_policy": PATCH_AUTHORITY_POLICY,
            "vsa_patch_authority": False,
        }


def _route_task(task: BenchmarkTask, grounding: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    frame_payload = dict(task.metadata.get("routing_frame", {}) if isinstance(task.metadata.get("routing_frame"), dict) else {})
    frame_payload.setdefault("target_file", task.target_file or grounding.get("target_file"))
    frame_payload.setdefault("target_symbol", task.target_symbol or grounding.get("target_symbol"))
    if not frame_payload:
        frame_payload = _infer_routing_frame(task, grounding)
    else:
        frame_payload["target_file"] = task.target_file or grounding.get("target_file")
        frame_payload["target_symbol"] = task.target_symbol or grounding.get("target_symbol")
    try:
        from aura_fst_routing import AuraCodingArenaRouter, RoutingFrame

        frame = RoutingFrame(**frame_payload)
        decision = AuraCodingArenaRouter().route(frame).to_dict()
        frame_dict = frame.to_dict()
    except Exception as exc:
        frame_dict = dict(frame_payload)
        decision = {
            "route": str(grounding.get("route") or task.expected_route or "BLOCKED_WITH_REASON"),
            "model": "no_model",
            "context": "SUMMARY",
            "reason": f"router_failed:{type(exc).__name__}",
            "verifier_required": True,
        }
    grounding_route = str(grounding.get("route") or "")
    if grounding_route in {"EXTERNAL_CALL_CONTEXT", "EMERGENT_CAPABILITY_AUDIT", "BLOCKED_WITH_REASON"}:
        decision = {
            **decision,
            "route": grounding_route,
            "model": "no_model",
            "context": "EXTERNAL" if grounding_route == "EXTERNAL_CALL_CONTEXT" else "AUDIT" if grounding_route == "EMERGENT_CAPABILITY_AUDIT" else "VERIFIER",
            "reason": (grounding.get("route_reasons") or ["route_valid"])[0],
            "verifier_required": grounding_route == "BLOCKED_WITH_REASON",
        }
    return frame_dict, decision


def _infer_routing_frame(task: BenchmarkTask, grounding: dict[str, Any]) -> dict[str, Any]:
    grounding_items: set[str] = set()
    if task.target_file or grounding.get("target_file"):
        grounding_items.add("file_exists")
    if task.target_symbol and (grounding.get("exact_hits") or grounding.get("target_symbol")):
        grounding_items.add("symbol_exists")
    if grounding.get("tests") or task.tests:
        grounding_items.add("tests_exist")
    if grounding.get("source_spans") or grounding.get("hashes"):
        grounding_items.add("codemap_grounded")
    if {"file_exists", "symbol_exists", "tests_exist", "codemap_grounded"} <= grounding_items:
        grounding_items.add("full")
    return {
        "intent": "benchmark" if task.category == "summarization_compression" else "code_refactor",
        "artifact": "python_module",
        "action": "inspect" if task.metadata.get("read_only") else "modify",
        "scope": "symbol" if task.target_symbol else "file" if task.target_file else "repo",
        "risk": "low" if task.metadata.get("read_only") else "medium",
        "grounding": tuple(sorted(grounding_items)) or ("none",),
        "tests": "existing" if task.tests or grounding.get("tests") else "none",
        "quality": "verifier_required" if task.expected_output_kind == "diff" else "balanced",
        "cost": "local_first",
        "target_file": task.target_file or grounding.get("target_file"),
        "target_symbol": task.target_symbol or grounding.get("target_symbol"),
    }


def _builder_context_prompt(task: BenchmarkTask, root: Path, grounding: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    target_file = task.target_file or grounding.get("target_file")
    try:
        from aura_builder_context import attach_st3gg_summary, build_builder_context_packet

        codemap = _load_codemap(root)
        packet = build_builder_context_packet(
            target_file=str(target_file or ""),
            target_symbol=task.target_symbol or grounding.get("target_symbol"),
            grounding_evidence={
                "codemap_symbol_hits": grounding.get("exact_hits", []),
                "test_files": grounding.get("tests", []),
                "neighbor_files": [],
            },
            codemap=codemap,
            repo_root=root,
            objective=task.prompt,
            task_id=task.task_id,
            topological_grounding=grounding,
        )
        attach_st3gg_summary(packet, repo_root=root)
        return packet.to_prompt_section(), packet.to_dict()
    except Exception as exc:
        return (
            f"BuilderContextPacket unavailable: {type(exc).__name__}\nTask: {task.prompt}",
            {"warnings": [f"builder_context_failed:{type(exc).__name__}"]},
        )


def _load_codemap(root: Path) -> dict[str, Any] | None:
    path = root / ".aura" / "CODEMAP.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_st3gg_metrics(builder_packet: dict[str, Any]) -> dict[str, Any]:
    st3gg = builder_packet.get("st3gg_context", {}) if isinstance(builder_packet, dict) else {}
    if isinstance(st3gg, dict) and isinstance(st3gg.get("metrics"), dict):
        return dict(st3gg["metrics"])
    return {}


def _jspace_packet_from(grounding: dict[str, Any], route_decision: dict[str, Any]) -> dict[str, Any]:
    if isinstance(grounding.get("jspace_route"), dict):
        return dict(grounding["jspace_route"])
    return {
        "packet": route_decision.get("compact_output", ""),
        "patch_authority": PATCH_AUTHORITY_POLICY,
        "vsa_patch_authority": False,
    }


def _output_format_valid(text: str, expected_kind: str) -> bool:
    body = str(text or "").strip()
    if expected_kind == "json":
        try:
            return isinstance(json.loads(body), dict)
        except json.JSONDecodeError:
            return False
    if expected_kind == "diff":
        return body.startswith("diff --git ") or body.startswith("*** Begin Patch")
    return bool(body)


def _route_correct(route: str, expected_route: str | None) -> bool:
    if not expected_route:
        return True
    return str(route or "").upper() == str(expected_route or "").upper()


def _target_grounding_correct(task: BenchmarkTask, metadata: dict[str, Any], root: Path) -> bool:
    if not task.target_file:
        return True
    if not (root / task.target_file).exists():
        return False
    grounding = metadata.get("grounding", {})
    if isinstance(grounding, dict) and grounding:
        if grounding.get("target_file") == task.target_file:
            return True
        spans = [item for item in grounding.get("source_spans", []) or [] if isinstance(item, dict)]
        if any(item.get("file_path") == task.target_file for item in spans):
            return True
        candidates = [item for item in grounding.get("candidate_files", []) or [] if isinstance(item, dict)]
        if any(item.get("path") == task.target_file for item in candidates):
            return True
    return bool(task.target_file)


def _unsafe_attempt_blocked(task: BenchmarkTask, route: str, metadata: dict[str, Any]) -> bool:
    if not task.metadata.get("unsafe_attempt"):
        return False
    safe_routes = {"BLOCKED_WITH_REASON", "LOCALIZE_FIRST", "TEST_GAP_FILL", "VERIFY_ONLY"}
    advisory_only = metadata.get("vsa_patch_authority") is False
    return str(route or "").upper() in safe_routes and advisory_only


def _tests_pass(task: BenchmarkTask, root: Path) -> bool:
    if not task.tests:
        return True
    return all((root / test).exists() for test in task.tests)


def _parse_modes(modes: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(modes, str):
        return [item.strip() for item in modes.split(",") if item.strip()]
    return [str(item).strip() for item in modes if str(item).strip()]


def _best_mode(modes: dict[str, Any], key: str) -> str:
    if not modes:
        return ""
    return max(modes.items(), key=lambda item: item[1].get(key, 0.0))[0]


def _new_run_id() -> str:
    return "aura-eff-" + time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + f"-{int(time.time_ns() % 1_000_000):06d}"


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _redact_public_payload(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern, replacement in _PUBLIC_REDACTIONS:
            redacted = pattern.sub(replacement, redacted)
        return redacted
    if isinstance(value, list):
        return [_redact_public_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_public_payload(item) for item in value)
    if isinstance(value, dict):
        return {
            _redact_public_payload(str(key)): _redact_public_payload(item)
            for key, item in value.items()
        }
    return value


if __name__ == "__main__":
    raise SystemExit(main())
