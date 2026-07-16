"""Benchmark Aura's Council–Surgeon division of cognitive labor.

The Council runs once to produce a long execution graph. Single sliced planners
(the Surgeons) execute each bounded Act Capsule. A local step-4 assertion failure
must remain local; an architectural step-4 failure must escalate to a Council
replan and then resume sliced execution.

Measured outputs include state preservation, context-drift avoidance, Council-token
amortization, local-repair versus replan routing, and estimated/reported input and
output tokens. Synthetic execution validates control flow, not real patch quality.
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
from aura_multistep_refactor_benchmark import SyntheticMultiStepBridge, _diff_for_turn

BENCHMARK_VERSION = "AURA_HYBRID_COUNCIL_SURGEON_BENCHMARK_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def _tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return (len(text.encode("utf-8")) + 3) // 4


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


class HybridFailureBridge(SyntheticMultiStepBridge):
    """Synthetic bridge with either local or graph-invalidating step failure."""

    def __init__(self, task_count: int, *, failure_mode: str, failure_task_index: int | None) -> None:
        super().__init__(task_count, repair_task_index=None)
        self.failure_mode = str(failure_mode)
        self.failure_task_index = failure_task_index
        self.failure_emitted = False

    def aura_verify_arena(self, **kwargs: Any) -> dict[str, Any]:
        task_id = self.current_task_id
        index = max(0, int(task_id.removeprefix("A") or 1) - 1)
        should_fail = (
            not self.failure_emitted
            and self.failure_task_index is not None
            and index == self.failure_task_index
            and self.attempts.get(task_id, 0) == 1
        )
        if not should_fail:
            self.calls.append({"tool": "verify", "task_id": task_id, "failure_mode": "none"})
            return {
                "ok": True,
                "stage": "ready",
                "failures": [],
                "checks": [],
                "next_action": "promote_hotswap",
                "hotswap_ready": True,
            }
        self.failure_emitted = True
        if self.failure_mode == "graph":
            message = (
                f"interface contract and dependency graph invalidated at {task_id}; "
                "downstream tasks require execution-graph revision"
            )
            scope = {
                "affected_task_count": max(2, self.task_count - index),
                "affected_file_count": 3,
                "downstream_tasks_invalidated": max(1, self.task_count - index - 1),
                "invariant_breach": True,
                "interface_contract_breach": True,
                "dependency_graph_breach": True,
            }
        else:
            message = f"focused unit test assertion failed locally for {task_id}"
            scope = {
                "affected_task_count": 1,
                "affected_file_count": 1,
                "downstream_tasks_invalidated": 0,
                "invariant_breach": False,
                "interface_contract_breach": False,
                "dependency_graph_breach": False,
            }
        self.calls.append({"tool": "verify", "task_id": task_id, "failure_mode": self.failure_mode})
        return {
            "ok": False,
            "stage": "blocked",
            "failures": [{"stage": "tests", "message": message}],
            "failure_scope": scope,
            "checks": [],
            "next_action": "repair_with_builder" if self.failure_mode != "graph" else "replan_with_council",
            "hotswap_ready": False,
        }

    def aura_repair_packet(self, **kwargs: Any) -> dict[str, Any]:
        task_id = str(kwargs.get("task_id") or "")
        index = max(1, int(task_id.removeprefix("A") or 1))
        return {
            "ok": True,
            "task_id": task_id,
            "failed_check": "tests",
            "compressed_error": (
                f"focused assertion failure for {task_id}"
                if self.failure_mode != "graph"
                else f"dependency graph and interface contract failure for {task_id}"
            ),
            "allowed_files": [f"aura_synthetic_step_{index}.py"],
            "do_not_touch": [],
            "required_response": "unified diff only",
        }


def _planning_tokens(planning_report: dict[str, Any]) -> dict[str, int]:
    arm = dict(dict(planning_report.get("arms") or {}).get("aura_architect_council") or {})
    return {
        "input": int(arm.get("input_tokens") or 0),
        "output": int(arm.get("output_tokens") or 0),
        "total": int(arm.get("total_tokens") or 0),
        "calls": int(arm.get("model_calls") or 0),
    }


def _remaining_tasks(manager: RecordedAuraExternalLLMSessionManager, session_id: str) -> list[dict[str, Any]]:
    session = manager._sessions[session_id]  # benchmark-only inspection
    remaining = []
    for task in session.act_capsules[session.active_task_index :]:
        revised = dict(task)
        revised["council_replan_revision"] = 1
        revised["acceptance"] = str(revised.get("acceptance") or "") + " Revalidate interface and downstream dependency invariants."
        remaining.append(revised)
    return remaining


def _metric_at_task(metrics: list[dict[str, Any]], task_id: str) -> dict[str, Any]:
    for item in metrics:
        if item.get("task_id") == task_id and item.get("turn_index"):
            return dict(item)
    return {}


def run_case(
    root: Path,
    output_dir: Path,
    *,
    task_count: int,
    failure_mode: str,
    planning_tokens: dict[str, int],
) -> dict[str, Any]:
    label = f"tasks-{task_count}-{failure_mode}"
    case_dir = output_dir / label
    case_dir.mkdir(parents=True, exist_ok=True)
    failure_index = 3 if task_count >= 4 and failure_mode != "none" else None
    bridge = HybridFailureBridge(
        task_count,
        failure_mode=failure_mode,
        failure_task_index=failure_index,
    )
    manager = RecordedAuraExternalLLMSessionManager(
        root,
        bridge=bridge,
        chronicle_path=case_dir / "refactor_chronicle.jsonl",
        experience_db_path=case_dir / "arena_experience.db",
        max_local_repairs=2,
    )
    opened = manager.open_session(
        objective=(
            f"Execute a {task_count}-step cross-module refactor from one Council plan; "
            "preserve dependencies and safety invariants with sliced implementers."
        ),
        provider="fixture",
        model="deterministic-surgeon",
        max_context_tokens=1800,
        max_output_tokens=600,
        max_turns=max(4, task_count * 3),
    )
    assert opened.get("ok"), opened
    initial_route = dict(opened.get("cognitive_labor_route") or {})
    session_id = str(opened["session"]["session_id"])
    turn = dict(opened["turn"])
    routing_trace: list[dict[str, Any]] = []
    started = time.perf_counter()
    while turn:
        diff = _diff_for_turn(turn)
        usage = {
            "input_tokens": int(turn.get("context_token_estimate") or _tokens(turn)),
            "output_tokens": _tokens(diff),
            "cost_usd": 0.0,
        }
        result = manager.submit_response(
            session_id=session_id,
            turn_id=str(turn["turn_id"]),
            response=diff,
            provider_usage=usage,
        )
        decision = result.get("cognitive_labor_decision")
        if isinstance(decision, dict):
            routing_trace.append(decision)
        if result.get("council_replan_required"):
            remaining = _remaining_tasks(manager, session_id)
            state = manager.get_session(session_id)
            replan_prompt = json.dumps(
                {
                    "role": "Council",
                    "instruction": "Revise only the remaining execution graph after an interface/dependency failure.",
                    "state_metrics": state.get("state_metrics", [])[-1:] or [],
                    "remaining_act_capsules": remaining,
                    "failure_packet": result.get("failure_packet"),
                },
                sort_keys=True,
            )
            replan_response = json.dumps(
                {
                    "architecture_decision": "Preserve completed work; revalidate the failed interface and downstream dependencies.",
                    "remaining_act_capsules": remaining,
                    "constraints": ["No production mutation", "Human review required"],
                },
                sort_keys=True,
            )
            replan = manager.apply_council_replan(
                session_id=session_id,
                remaining_act_capsules=remaining,
                rationale="Graph-level failure invalidated downstream dependencies.",
                prompt=replan_prompt,
                response=replan_response,
                provider_usage={
                    "input_tokens": _tokens(replan_prompt),
                    "output_tokens": _tokens(replan_response),
                    "cost_usd": 0.0,
                },
            )
            assert replan.get("ok"), replan
            turn = dict(replan.get("turn") or {})
            continue
        next_turn = result.get("next_turn")
        turn = dict(next_turn) if isinstance(next_turn, dict) else {}

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    state = manager.get_session(session_id)
    session = dict(state.get("session") or {})
    metrics = list(state.get("state_metrics") or [])
    history = manager.chronicle.history(
        correlation_id=f"REF-{session_id}",
        session_id=session_id,
        limit=10000,
    )
    surgeon_events = [
        row for row in history
        if row.get("event_type") in {"refactor_worker_completed", "refactor_repair_completed"}
    ]
    replan_events = [row for row in history if row.get("event_type") == "refactor_council_replan_applied"]
    surgeon_input = sum(int(row.get("input_tokens_estimated") or 0) for row in surgeon_events)
    surgeon_output = sum(int(row.get("output_tokens_estimated") or 0) for row in surgeon_events)
    replan_input = sum(int(row.get("input_tokens_estimated") or 0) for row in replan_events)
    replan_output = sum(int(row.get("output_tokens_estimated") or 0) for row in replan_events)
    council_once = int(planning_tokens.get("total") or 0)
    council_replan = replan_input + replan_output
    surgeon_total = surgeon_input + surgeon_output
    hybrid_total = council_once + council_replan + surgeon_total
    repeated_council_tax = council_once * task_count
    avoided_council_tax = max(0, repeated_council_tax - council_once - council_replan)
    min_preservation = min(
        (float(item.get("state_preservation_score", 0.0)) for item in metrics),
        default=0.0,
    )
    max_drift = max((float(item.get("context_drift_score", 1.0)) for item in metrics), default=1.0)
    step3 = _metric_at_task(metrics, "A3")
    step7 = _metric_at_task(metrics, "A7")
    case = {
        "case_id": label,
        "task_count": task_count,
        "failure_mode": failure_mode,
        "failure_step": failure_index + 1 if failure_index is not None else None,
        "terminal_status": session.get("status"),
        "completed_tasks": session.get("active_task_index"),
        "turn_count": session.get("turn_count"),
        "initial_cognitive_route": initial_route,
        "failure_routing_trace": routing_trace,
        "local_repair_completed_count": sum(1 for row in history if row.get("event_type") == "refactor_repair_completed"),
        "council_replan_count": state.get("council_replan_count"),
        "state_preservation": {
            "minimum_score": round(min_preservation, 4),
            "maximum_context_drift": round(max_drift, 4),
            "step_3": step3,
            "step_7": step7,
            "all_steps": metrics,
        },
        "token_amortization": {
            "initial_council_calls": planning_tokens.get("calls"),
            "initial_council_input_tokens_estimated": planning_tokens.get("input"),
            "initial_council_output_tokens_estimated": planning_tokens.get("output"),
            "initial_council_total_tokens_estimated": council_once,
            "council_replan_tokens_estimated": council_replan,
            "surgeon_input_tokens_estimated": surgeon_input,
            "surgeon_output_tokens_estimated": surgeon_output,
            "surgeon_total_tokens_estimated": surgeon_total,
            "hybrid_total_tokens_estimated": hybrid_total,
            "initial_council_tokens_amortized_per_step": round(council_once / max(1, task_count), 3),
            "hybrid_tokens_per_completed_step": round(hybrid_total / max(1, int(session.get("active_task_index") or 0)), 3),
            "hypothetical_council_every_step_tax": repeated_council_tax,
            "avoided_council_tax_estimated": avoided_council_tax,
            "council_tax_reduction_pct": round(
                avoided_council_tax / max(1, repeated_council_tax) * 100.0,
                2,
            ),
        },
        "elapsed_ms": elapsed_ms,
        "chronicle_event_count": len(history),
        "chronicle_path": str(case_dir / "refactor_chronicle.jsonl"),
        "experience_db_path": str(case_dir / "arena_experience.db"),
        "production_mutation": False,
    }
    (case_dir / "case.json").write_text(json.dumps(case, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return case


def run_benchmark(
    root: Path,
    output_dir: Path,
    planning_report_path: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    planning_report = json.loads(planning_report_path.read_text(encoding="utf-8"))
    planning_tokens = _planning_tokens(planning_report)
    scenarios = [
        (1, "none"),
        (4, "local"),
        (8, "local"),
        (10, "local"),
        (10, "graph"),
    ]
    cases = [
        run_case(
            root,
            output_dir,
            task_count=task_count,
            failure_mode=failure_mode,
            planning_tokens=planning_tokens,
        )
        for task_count, failure_mode in scenarios
    ]
    report = {
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": (
            "One Council plans long cross-system work; sliced Surgeons execute bounded steps; "
            "local failures remain local; graph and invariant failures escalate for Council replan."
        ),
        "division_of_cognitive_labor": {
            "surgeon": {
                "optimal_scope": "localized implementation, single-module refactoring, pure code synthesis",
                "context_profile": "hyper-narrow, high-density, exact interface surfaces plus compact state ledger",
                "primary_output": "compile-ready bounded patch capsules",
                "failure_mode": "tunnel vision or architectural-rule violation",
            },
            "council": {
                "optimal_scope": "architectural design, cross-domain dependency mapping, trade-off analysis, graph repair",
                "context_profile": "systemic indexes, dependency trees, plan history, invariants, and failure graph",
                "primary_output": "execution sequence, interface specifications, invariants, and rollback conditions",
                "failure_mode": "consensus drift, boilerplate, token tax, and latency",
            },
        },
        "planning_tokens": planning_tokens,
        "cases": cases,
        "measurement_classes": {
            "state_preservation": "DERIVED_DETERMINISTIC_FACT_MATCH",
            "context_tokens": "ESTIMATED_CHAR4_PROXY",
            "provider_tokens": "DETERMINISTIC_FIXTURE_REPORTED",
            "token_amortization": "DERIVED_FROM_RECORDED_COUNCIL_AND_SURGEON_TOKENS",
            "rollback_route": "MEASURED_ROUTER_DECISION_TRACE",
            "patch_quality": "NOT_MEASURED_BY_SYNTHETIC_EXECUTION",
        },
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "production_mutation": False,
    }
    path = output_dir / "hybrid_refactor_benchmark.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    BenchmarkRegistry(root, path=output_dir / "benchmark_registry.jsonl").record(
        {
            "benchmark_id": "hybrid_council_surgeon_refactor",
            "benchmark_version": BENCHMARK_VERSION,
            "generated_at": report["generated_at"],
            "objective_hash": _digest(report["hypothesis"]),
            "measurement_class": report["measurement_classes"],
            "length_profile": {"scenarios": scenarios, "max_task_count": 10},
            "arms": {case["case_id"]: case["token_amortization"] for case in cases},
            "comparison": {
                "minimum_state_preservation": min(case["state_preservation"]["minimum_score"] for case in cases),
                "local_failure_route": next(case["failure_routing_trace"] for case in cases if case["case_id"] == "tasks-10-local"),
                "graph_failure_route": next(case["failure_routing_trace"] for case in cases if case["case_id"] == "tasks-10-graph"),
            },
            "report_digest": _digest(report),
            "evidence_refs": ["hybrid_refactor_benchmark.json", "tasks-*/refactor_chronicle.jsonl"],
            "limitations": [
                "Synthetic bridge validates state, routing, token accounting, and continuation—not real patch quality.",
                "Hypothetical Council-every-step tax is an extrapolation, clearly labeled as derived.",
            ],
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark-output/hybrid"))
    parser.add_argument("--planning-report", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    planning_report = args.planning_report if args.planning_report.is_absolute() else root / args.planning_report
    report = run_benchmark(root, output, planning_report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
