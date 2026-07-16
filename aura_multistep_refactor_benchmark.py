"""Deterministic multi-step refactor execution benchmark.

This benchmark does not claim model-quality superiority.  It tests the part the
first planning benchmark did not: how slice-leased execution, repair, token
accounting, and replayable history scale as a refactor grows from one to several
sequential Act Capsules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from aura_benchmark_registry import BenchmarkRegistry
from aura_external_llm_session_recorded import RecordedAuraExternalLLMSessionManager

BENCHMARK_VERSION = "AURA_MULTISTEP_REFACTOR_BENCHMARK_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def _tokens(text: str) -> int:
    return (len(text.encode("utf-8")) + 3) // 4


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


class SyntheticMultiStepBridge:
    """Deterministic Agent Arena bridge with one forced verifier repair."""

    def __init__(self, task_count: int, *, repair_task_index: int | None = None) -> None:
        self.task_count = int(task_count)
        self.repair_task_index = repair_task_index
        self.current_task_id = ""
        self.attempts: dict[str, int] = {}
        self.calls: list[dict[str, Any]] = []

    def aura_prepare_arena(self, **kwargs: Any) -> dict[str, Any]:
        tasks = []
        for index in range(self.task_count):
            task_id = f"A{index + 1}"
            tasks.append(
                {
                    "task_id": task_id,
                    "objective": f"Apply bounded refactor step {index + 1} of {self.task_count}",
                    "target_file": f"aura_synthetic_step_{index + 1}.py",
                    "target_symbol": f"step_{index + 1}",
                    "related_files": [],
                    "allowed_scope": "single exact file and symbol",
                    "acceptance": "The staged diff passes the focused synthetic verifier.",
                    "expected_output": "UNIFIED_DIFF",
                    "size": "S",
                    "depends_on": [f"A{index}"] if index else [],
                }
            )
        objective = str(kwargs.get("objective") or "")
        phase_hash = f"MULTI-{_digest({'objective': objective, 'task_count': self.task_count})[:16]}"
        return {
            "ok": True,
            "plan_phase_hash": phase_hash,
            "act_capsules": tasks,
            "grounding_evidence": [],
            "shadow_findings": [],
            "routing_decisions": [
                {"task_id": task["task_id"], "route": "BUILDER_PATCH"}
                for task in tasks
            ],
            "ready_for_incubator": True,
        }

    def aura_get_micro_context(self, **kwargs: Any) -> dict[str, Any]:
        task_id = str(kwargs.get("task_id") or "")
        index = max(1, int(task_id.removeprefix("A") or 1))
        path = f"aura_synthetic_step_{index}.py"
        symbol = f"step_{index}"
        return {
            "ok": True,
            "task_id": task_id,
            "target_file": path,
            "target_symbol": symbol,
            "line_ranges": [{"file": path, "symbol": symbol, "line_range": [1, 3]}],
            "tests": [f"tests/test_aura_synthetic_step_{index}.py"],
            "compressed_context": f"Exact synthetic context for {task_id}; prior tasks are dependencies only.",
        }

    def aura_read_slice(self, **kwargs: Any) -> dict[str, Any]:
        path = str(kwargs.get("file") or "")
        is_test = path.startswith("tests/")
        content = (
            "def test_step():\n    assert True\n"
            if is_test
            else "def step(value):\n    return value\n"
        )
        return {
            "ok": True,
            "file": path,
            "symbol": str(kwargs.get("symbol") or ""),
            "line_start": 1,
            "line_end": len(content.splitlines()),
            "total_lines": len(content.splitlines()),
            "content": content,
            "warnings": [],
        }

    def aura_stage_patch(self, **kwargs: Any) -> dict[str, Any]:
        task_id = str(kwargs.get("task_id") or "")
        self.current_task_id = task_id
        self.attempts[task_id] = self.attempts.get(task_id, 0) + 1
        self.calls.append({"tool": "stage", "task_id": task_id, "attempt": self.attempts[task_id]})
        return {
            "ok": True,
            "patch": {
                "patch_id": f"PATCH-{task_id}-{self.attempts[task_id]}",
                "task_id": task_id,
                "affected_files": list(kwargs.get("affected_files") or []),
                "status": "staged",
            },
        }

    def aura_verify_arena(self, **kwargs: Any) -> dict[str, Any]:
        task_id = self.current_task_id
        index = max(0, int(task_id.removeprefix("A") or 1) - 1)
        forced_failure = self.repair_task_index == index and self.attempts.get(task_id, 0) == 1
        self.calls.append({"tool": "verify", "task_id": task_id, "forced_failure": forced_failure})
        return {
            "ok": not forced_failure,
            "stage": "blocked" if forced_failure else "ready",
            "failures": (
                [{"stage": "tests", "message": f"forced repair for {task_id}"}]
                if forced_failure
                else []
            ),
            "checks": [],
            "next_action": "repair_with_builder" if forced_failure else "promote_hotswap",
            "hotswap_ready": not forced_failure,
        }

    def aura_repair_packet(self, **kwargs: Any) -> dict[str, Any]:
        task_id = str(kwargs.get("task_id") or "")
        index = max(1, int(task_id.removeprefix("A") or 1))
        return {
            "ok": True,
            "task_id": task_id,
            "failed_check": "tests",
            "compressed_error": f"forced repair for {task_id}",
            "allowed_files": [f"aura_synthetic_step_{index}.py"],
            "do_not_touch": [],
            "required_response": "unified diff only",
        }

    def aura_hotswap_status(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "status": "ready",
            "hotswap_ready": True,
            "production_mutation": False,
        }


def _diff_for_turn(turn: dict[str, Any]) -> str:
    path = str((turn.get("allowed_files") or ["unknown.py"])[0])
    symbol = str(dict(turn.get("act_capsule") or {}).get("target_symbol") or "step")
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1,2 +1,2 @@\n"
        f"-def {symbol}(value):\n"
        f"+def {symbol}(value):\n"
        "     return value\n"
    )


def run_case(root: Path, output_dir: Path, task_count: int) -> dict[str, Any]:
    case_dir = output_dir / f"tasks-{task_count}"
    case_dir.mkdir(parents=True, exist_ok=True)
    repair_index = task_count // 2 if task_count > 1 else None
    bridge = SyntheticMultiStepBridge(task_count, repair_task_index=repair_index)
    manager = RecordedAuraExternalLLMSessionManager(
        root,
        bridge=bridge,
        chronicle_path=case_dir / "refactor_chronicle.jsonl",
        experience_db_path=case_dir / "arena_experience.db",
    )
    started = time.perf_counter()
    result = manager.open_session(
        objective=f"Execute a {task_count}-step bounded synthetic refactor with dependency order and recorded evidence.",
        provider="fixture",
        model="deterministic-multistep-worker",
        max_context_tokens=1600,
        max_output_tokens=600,
        max_turns=max(4, task_count * 3),
    )
    assert result.get("ok"), result
    session_id = str(result["session"]["session_id"])
    turn = dict(result["turn"])
    while turn:
        diff = _diff_for_turn(turn)
        usage = {
            "input_tokens": int(turn.get("context_token_estimate") or _tokens(json.dumps(turn, sort_keys=True))),
            "output_tokens": _tokens(diff),
            "cost_usd": 0.0,
        }
        result = manager.submit_response(
            session_id=session_id,
            turn_id=str(turn["turn_id"]),
            response=diff,
            provider_usage=usage,
        )
        next_turn = result.get("next_turn")
        turn = dict(next_turn) if isinstance(next_turn, dict) else {}
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    state = manager.get_session(session_id)
    summary = dict(state.get("chronicle") or {})
    token_totals = dict(summary.get("token_totals") or {})
    completed_tasks = int(state.get("session", {}).get("active_task_index") or 0)
    case = {
        "task_count": task_count,
        "dependency_depth": task_count,
        "forced_repair_task_index": repair_index,
        "terminal_status": state.get("session", {}).get("status"),
        "completed_tasks": completed_tasks,
        "turn_count": state.get("session", {}).get("turn_count"),
        "repair_event_count": summary.get("repair_event_count"),
        "input_tokens_estimated": token_totals.get("input_tokens_estimated"),
        "output_tokens_estimated": token_totals.get("output_tokens_estimated"),
        "input_tokens_reported": token_totals.get("input_tokens_reported"),
        "output_tokens_reported": token_totals.get("output_tokens_reported"),
        "reported_cost_usd": token_totals.get("cost_usd_reported"),
        "estimated_tokens_per_completed_task": round(
            (
                float(token_totals.get("input_tokens_estimated") or 0)
                + float(token_totals.get("output_tokens_estimated") or 0)
            )
            / max(1, completed_tasks),
            3,
        ),
        "elapsed_ms": elapsed_ms,
        "chronicle_event_count": summary.get("event_count"),
        "chronicle_path": str(case_dir / "refactor_chronicle.jsonl"),
        "experience_db_path": str(case_dir / "arena_experience.db"),
        "bridge_calls": bridge.calls,
        "production_mutation": False,
    }
    (case_dir / "case.json").write_text(json.dumps(case, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return case


def run_benchmark(root: Path, output_dir: Path, lengths: list[int]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = [run_case(root, output_dir, count) for count in lengths]
    report = {
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "objective": "Measure slice-leased multi-step refactor execution, repair overhead, token accounting, and replay history as plan length grows.",
        "cases": cases,
        "measurement_classes": {
            "task_turn_counts": "MEASURED",
            "input_output_tokens_estimated": "ESTIMATED_CHAR4_PROXY",
            "input_output_tokens_reported": "DETERMINISTIC_FIXTURE_REPORTED",
            "latency": "MEASURED_LOCAL_WORKFLOW",
            "quality": "NOT_MEASURED_BY_THIS_SYNTHETIC_EXECUTION_TEST",
        },
        "finding": (
            "The execution protocol completes sequential Act Capsules, preserves dependency order, "
            "records a forced repair, and accumulates per-turn input/output token evidence. This test "
            "validates long-refactor bookkeeping and control flow; it does not determine whether a "
            "Council improves real patch quality."
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "production_mutation": False,
    }
    report_path = output_dir / "multistep_refactor_benchmark.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    registry = BenchmarkRegistry(root, path=output_dir / "benchmark_registry.jsonl")
    registry.record(
        {
            "benchmark_id": "multistep_refactor_execution",
            "benchmark_version": BENCHMARK_VERSION,
            "generated_at": report["generated_at"],
            "objective_hash": _digest(report["objective"]),
            "measurement_class": report["measurement_classes"],
            "length_profile": {"tested_task_counts": lengths, "max_dependency_depth": max(lengths)},
            "arms": {
                f"tasks_{case['task_count']}": {
                    key: case.get(key)
                    for key in (
                        "turn_count",
                        "repair_event_count",
                        "input_tokens_estimated",
                        "output_tokens_estimated",
                        "input_tokens_reported",
                        "output_tokens_reported",
                        "reported_cost_usd",
                        "terminal_status",
                    )
                }
                for case in cases
            },
            "report_digest": _digest(report),
            "evidence_refs": ["multistep_refactor_benchmark.json", "tasks-*/refactor_chronicle.jsonl"],
            "limitations": [
                "Synthetic bridge and deterministic diffs validate orchestration, not real code quality.",
                "Council-versus-single quality must be measured with provider-backed multi-step refactors.",
            ],
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark-output/multistep"))
    parser.add_argument("--lengths", default="1,4,8")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    lengths = sorted({max(1, int(item)) for item in args.lengths.split(",") if item.strip()})
    report = run_benchmark(root, output, lengths)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
