"""Native Aura Architect/Surgeon verification for the SCO Construction refactor.

This module makes the Construction refactor itself pass through Aura's existing
refactor architecture: controlled Selective Council V3 plan comparison, Work
Splitter Act shards, CODEMAP grounding, Shadow preflight, Liquid Planning file
leases, Surgeon patch staging, Verifier tests, Judge, hot-swap, rollback, and an
append-only ledger. It verifies a branch diff; it never mutates production or
promotes a branch without human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Mapping

from aura_architect_control import normalize_control_profile
from aura_architect_loop import ArchitectFusionLoop, judge_refactor_arena
from aura_arena_architect_connector import AuraArenaArchitectConnector
from aura_work_splitter import split_by_file, work_split_to_act_capsules

CONSTRUCTION_ARCHITECT_REFACTOR_VERSION = "AURA_SCO_CONSTRUCTION_ARCHITECT_REFACTOR_V1"
NOT_MEASURED = "NOT_MEASURED"
SELECTED_PLAN_ID = "SELECTIVE_COUNCIL_V3_SURGEON"

SOURCE_SHARDS: tuple[dict[str, Any], ...] = (
    {
        "task_id": "SCO-E7-ADAPTER",
        "objective": (
            "Harden the proposal-only Construction coordination adapter while "
            "preserving canonical state, authority, and Liquid Planning owners."
        ),
        "target_file": "aura_construction_adapter.py",
        "target_symbol": "evaluate_construction_candidates",
        "acceptance": (
            "Hard blockers precede ranking; authority remains human-governed; "
            "tests/test_aura_construction_adapter.py passes."
        ),
        "tests": ["tests/test_aura_construction_adapter.py"],
        "allowed_scope": "single Construction adapter module",
        "expected_output": "UNIFIED_DIFF",
        "size": "M",
    },
    {
        "task_id": "SCO-E8-FIXTURE",
        "objective": (
            "Harden deterministic fictional SCO demo fixtures without introducing "
            "private project data or production connectors."
        ),
        "target_file": "aura_construction_fixtures.py",
        "target_symbol": "build_sco_construction_demo_fixture",
        "acceptance": (
            "Fixture replay remains deterministic and the unsafe high-score route "
            "remains blocked; tests/test_aura_construction_fixtures.py passes."
        ),
        "tests": ["tests/test_aura_construction_fixtures.py"],
        "allowed_scope": "single synthetic fixture module",
        "expected_output": "UNIFIED_DIFF",
        "size": "S",
    },
    {
        "task_id": "SCO-E11-BENCHMARK",
        "objective": (
            "Harden the zero-model Construction benchmark and its evidence boundaries "
            "without inventing provider usage or real-project savings."
        ),
        "target_file": "aura_construction_benchmark.py",
        "target_symbol": "run_construction_phase3_benchmark",
        "acceptance": (
            "The 250-permutation gate remains deterministic and benchmark claims stay "
            "truth-classed; tests/test_aura_construction_benchmark.py passes."
        ),
        "tests": ["tests/test_aura_construction_benchmark.py"],
        "allowed_scope": "single executable benchmark module",
        "expected_output": "UNIFIED_DIFF",
        "size": "S",
    },
)

REQUIRED_CAPABILITIES: tuple[str, ...] = (
    "canonical_owner_reuse",
    "hard_filter_before_ranking",
    "proposal_only_authority",
    "synthetic_fixture_boundary",
    "deterministic_benchmark",
    "bounded_patch_leases",
    "rollback_and_human_review",
)

EXISTING_MODULES: tuple[str, ...] = (
    "aura_construction_contracts.py",
    "aura_construction_state.py",
    "aura_construction_authority.py",
    "aura_liquid_planning_arena.py",
    "aura_arena_wfst_runtime.py",
    "aura_architect_loop.py",
    "aura_architect_control.py",
    "aura_arena_architect_connector.py",
    "aura_work_splitter.py",
)


def _canonical_digest(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


def _base_plan(
    *,
    architecture_decision: str,
    act_tasks: list[Mapping[str, Any]],
    coverage_tags: list[str],
    architecture_reuse: bool,
    acceptance_criteria: list[str],
    rollback_conditions: list[str],
    risk_map: list[str],
    constraints: list[str],
) -> dict[str, Any]:
    return {
        "architecture_decision": architecture_decision,
        "act_tasks": [dict(item) for item in act_tasks],
        "acceptance_criteria": list(acceptance_criteria),
        "rollback_conditions": list(rollback_conditions),
        "risk_map": list(risk_map),
        "constraints": list(constraints),
        "coverage_tags": list(coverage_tags),
        "architecture_reuse": architecture_reuse,
        "existing_modules": list(EXISTING_MODULES) if architecture_reuse else [],
        "domains": ["construction", "code", "verification"],
        "dependency_edges": [
            ["SCO-E7-ADAPTER", "SCO-E8-FIXTURE"],
            ["SCO-E8-FIXTURE", "SCO-E11-BENCHMARK"],
        ],
    }


def build_refactor_plan_candidates() -> list[dict[str, Any]]:
    """Return frozen plans for Aura's controlled Council comparison."""
    broad_task = {
        "task_id": "BROAD-1",
        "objective": "Rewrite the Construction advisory subsystem in one pass.",
        "target_file": "aura_construction_adapter.py",
        "target_symbol": "evaluate_construction_candidates",
        "acceptance": "Construction tests pass.",
        "expected_output": "UNIFIED_DIFF",
        "size": "XL",
    }
    minimal_tasks = [
        {
            **SOURCE_SHARDS[0],
            "task_id": "MINIMAL-1",
            "acceptance": "The adapter imports and one focused test passes.",
        }
    ]
    surgeon_tasks = [
        {key: value for key, value in item.items() if key != "tests"}
        for item in SOURCE_SHARDS
    ]
    selective_tasks = [
        {
            **{key: value for key, value in item.items() if key != "tests"},
            "escalate_if": [
                "target symbol is absent from CODEMAP",
                "patch crosses the leased file",
                "paired focused test fails",
                "authority boundary changes",
            ],
        }
        for item in SOURCE_SHARDS
    ]
    return [
        {
            "candidate_id": "BROAD_IMPLEMENTER",
            "arm_family": "BROAD_IMPLEMENTER",
            "provenance": {"generation": "frozen_local_plan", "model_calls": 0},
            "token_usage": {"provider_reported": None, "measurement_class": NOT_MEASURED},
            "plan": _base_plan(
                architecture_decision="Use one broad rewrite task.",
                act_tasks=[broad_task],
                coverage_tags=["deterministic_benchmark"],
                architecture_reuse=False,
                acceptance_criteria=["Focused tests pass."],
                rollback_conditions=["Revert the broad patch if tests fail."],
                risk_map=["Large cross-concern patch."],
                constraints=["Do not mutate production."],
            ),
        },
        {
            "candidate_id": "ZERO_MODEL_MINIMAL",
            "arm_family": "ZERO_MODEL_MINIMAL",
            "provenance": {"generation": "frozen_local_plan", "model_calls": 0},
            "token_usage": {"provider_reported": None, "measurement_class": NOT_MEASURED},
            "plan": _base_plan(
                architecture_decision="Use the smallest local patch and defer the rest.",
                act_tasks=minimal_tasks,
                coverage_tags=[
                    "hard_filter_before_ranking",
                    "proposal_only_authority",
                ],
                architecture_reuse=True,
                acceptance_criteria=["Adapter test passes."],
                rollback_conditions=["Revert the adapter file on failure."],
                risk_map=["Fixture and benchmark remain unreviewed."],
                constraints=["No production mutation."],
            ),
        },
        {
            "candidate_id": "SLICED_SURGEON",
            "arm_family": "SLICED_SURGEON",
            "provenance": {"generation": "frozen_local_plan", "model_calls": 0},
            "token_usage": {"provider_reported": None, "measurement_class": NOT_MEASURED},
            "plan": _base_plan(
                architecture_decision="Use three bounded Surgeon shards.",
                act_tasks=surgeon_tasks,
                coverage_tags=list(REQUIRED_CAPABILITIES[:-1]),
                architecture_reuse=True,
                acceptance_criteria=[
                    "All three focused suites pass.",
                    "No source shard crosses its file boundary.",
                ],
                rollback_conditions=["Discard any failed shard by phase hash."],
                risk_map=["Cross-shard sequencing requires explicit verification."],
                constraints=[
                    "Reuse canonical owners.",
                    "No production mutation.",
                    "No physical or payment authority.",
                ],
            ),
        },
        {
            "candidate_id": SELECTED_PLAN_ID,
            "arm_family": "SELECTIVE_COUNCIL_V3_PLUS_SURGEON",
            "provenance": {
                "generation": "frozen_local_plan",
                "model_calls": 0,
                "council_mode": "SELECTIVE_V3",
            },
            "token_usage": {"provider_reported": None, "measurement_class": NOT_MEASURED},
            "plan": _base_plan(
                architecture_decision=(
                    "Reuse Construction truth and authority owners, route ambiguity through "
                    "Selective Council V3, and execute three exact Surgeon shards inside "
                    "Liquid Planning leases with Verifier/Judge promotion gates."
                ),
                act_tasks=selective_tasks,
                coverage_tags=list(REQUIRED_CAPABILITIES),
                architecture_reuse=True,
                acceptance_criteria=[
                    "All Act Capsules are CODEMAP-grounded.",
                    "Shadow reports no blockers.",
                    "Every staged diff stays inside one file lease.",
                    "All paired focused tests pass under Verifier.",
                    "Judge returns promote_hotswap while human review remains required.",
                    "Benchmark evidence never invents provider usage or real savings.",
                ],
                rollback_conditions=[
                    "Any Shadow blocker prevents Builder staging.",
                    "Any lease, test, authority, or deterministic replay failure blocks hot-swap.",
                    "Rollback capsule must retain exact file digests.",
                ],
                risk_map=[
                    "Construction authority may not expand beyond proposal-only advice.",
                    "Probabilistic scores may not override exact readiness blockers.",
                    "Synthetic fixture values may not be represented as real project facts.",
                    "Benchmark timings are environment-specific and not provider cost evidence.",
                ],
                constraints=[
                    "PATCH_AUTHORITY remains exact source spans and hashes only.",
                    "VSA patch authority remains false.",
                    "Reuse existing state, authority, Liquid Planning, WFST, and Architect owners.",
                    "No physical work, payment, access, safety, engineering, legal, or regulatory authority.",
                    "No production connectors or private project data in this phase.",
                    "Human review remains mandatory before merge or deployment.",
                ],
            ),
        },
    ]


def _git_diff_for_file(repo_root: Path, base_sha: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "diff", "--binary", base_sha, "HEAD", "--", path],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git diff failed for {path}")
    if not completed.stdout.strip():
        raise RuntimeError(f"no branch diff found for Architect shard: {path}")
    return completed.stdout


def _pytest_runner(repo_root: Path, test_name: str) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", test_name],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "test": test_name,
        "elapsed_ms": round(elapsed_ms, 3),
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def _codemap_metrics(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".aura" / "CODEMAP.json"
    if not path.is_file():
        return {
            "repository_file_count": NOT_MEASURED,
            "repository_text_tokens_est": NOT_MEASURED,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = dict(payload.get("summary") or {})
    coverage = dict(payload.get("coverage") or {})
    return {
        "repository_file_count": summary.get("file_count")
        or coverage.get("included_file_count")
        or NOT_MEASURED,
        "repository_text_tokens_est": summary.get("text_tokens_est", NOT_MEASURED),
    }


def run_construction_architect_refactor(
    *,
    repo_root: str | Path,
    base_sha: str,
    output_dir: str | Path = "Aura_Staging/sco_construction_phase3_architect",
) -> dict[str, Any]:
    """Run Aura's native governed refactor loop over the current source diff."""
    root = Path(repo_root).resolve()
    if not base_sha.strip():
        raise ValueError("base_sha is required")
    output = Path(output_dir)
    if output.is_absolute():
        raise ValueError("output_dir must be repository-relative")
    output_path = root / output
    output_path.mkdir(parents=True, exist_ok=True)

    control = normalize_control_profile(
        {
            "surface": "native",
            "council_mode": "SELECTIVE_V3",
            "council_call_budget": 6,
            "critic_lanes": ["scope", "tests", "sequence", "rollback", "cost"],
            "surgeon_mode": "STAGE_AND_VERIFY",
            "surgeon_max_turns": 12,
            "surgeon_max_local_repairs": 2,
            "record_outputs": True,
            "output_root": output.as_posix(),
        },
        benchmark=True,
    )
    candidates = build_refactor_plan_candidates()
    objective = (
        "Refactor and verify the SCO Construction E7-E8 advisory runtime by reusing "
        "Aura's canonical architecture, preserving authority boundaries, and recording "
        "executable evidence for the Construction demo and the refactor process."
    )
    run_id = f"SCO-P3-{hashlib.blake2b(base_sha.encode('utf-8'), digest_size=8).hexdigest()}"
    connector = AuraArenaArchitectConnector(root, bridge=object())

    started = time.perf_counter()
    comparison = connector.compare_plans(
        objective=objective,
        candidates=candidates,
        required_capabilities=REQUIRED_CAPABILITIES,
        control=control,
        surface="native",
        run_id=run_id,
        record=False,
        benchmark=True,
    )
    if comparison["selected_candidate_id"] != SELECTED_PLAN_ID:
        raise RuntimeError(
            "Aura Council selected an unexpected plan: "
            f"{comparison['selected_candidate_id']}"
        )
    selected_plan = dict(comparison["selected_plan"])

    split_packet = split_by_file(
        [str(item["target_file"]) for item in SOURCE_SHARDS],
        repo_root=root,
    )
    split_capsules = work_split_to_act_capsules(split_packet, repo_root=root)

    patch_submissions = []
    tests_by_task = {
        str(item["task_id"]): list(item["tests"]) for item in SOURCE_SHARDS
    }
    for task in selected_plan["act_tasks"]:
        task_id = str(task["task_id"])
        target_file = str(task["target_file"])
        patch_submissions.append(
            {
                "task_id": task_id,
                "owner": "aura_surgeon",
                "diff": _git_diff_for_file(root, base_sha, target_file),
                "affected_files": [target_file],
                "affected_symbols": [str(task["target_symbol"])],
                "tests": tests_by_task[task_id],
            }
        )

    execution = ArchitectFusionLoop(repo_root=root).execute(
        objective,
        architecture_decision=str(selected_plan["architecture_decision"]),
        act_tasks=list(selected_plan["act_tasks"]),
        patch_submissions=patch_submissions,
        target_file=str(selected_plan["act_tasks"][0]["target_file"]),
        target_symbol=str(selected_plan["act_tasks"][0]["target_symbol"]),
        acceptance_criteria=list(selected_plan["acceptance_criteria"]),
        rollback_conditions=list(selected_plan["rollback_conditions"]),
        risk_map=list(selected_plan["risk_map"]),
        constraints=list(selected_plan["constraints"]),
        context_pressure=0.91,
        runner=lambda test_name: _pytest_runner(root, test_name),
        ledger_path=output_path / "architect_ledger.jsonl",
    )
    judge = judge_refactor_arena(execution.verification)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if not all(item.ok for item in execution.stage_results):
        raise RuntimeError("Aura Surgeon rejected one or more Construction source shards")
    if not execution.verification.hotswap_ready:
        raise RuntimeError(
            "Aura Verifier blocked the Construction refactor: "
            f"{execution.verification.failures}"
        )
    if judge["decision"] != "promote_hotswap":
        raise RuntimeError(f"Aura Judge did not promote the verified refactor: {judge}")

    codemap = _codemap_metrics(root)
    repo_files = codemap["repository_file_count"]
    source_file_count = len(SOURCE_SHARDS)
    structural_scope_reduction = (
        round(1.0 - source_file_count / float(repo_files), 6)
        if isinstance(repo_files, int) and repo_files > 0
        else NOT_MEASURED
    )
    selected_token_proxy = comparison["selected_assessment"]["token_proxy"]
    repo_token_proxy = codemap["repository_text_tokens_est"]
    planning_context_reduction = (
        round(1.0 - selected_token_proxy / float(repo_token_proxy), 6)
        if isinstance(repo_token_proxy, int) and repo_token_proxy > 0
        else NOT_MEASURED
    )

    report = {
        "ok": True,
        "version": CONSTRUCTION_ARCHITECT_REFACTOR_VERSION,
        "run_id": run_id,
        "base_sha": base_sha,
        "head_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip(),
        "objective": objective,
        "control_profile": control.to_dict(),
        "work_splitter": {
            "split_packet": split_packet,
            "act_capsules": split_capsules,
        },
        "council_comparison": comparison,
        "architect_execution": execution.to_dict(),
        "judge": judge,
        "benchmarks": {
            "elapsed_ms": round(elapsed_ms, 3),
            "plan_candidate_count": len(candidates),
            "selected_plan_id": comparison["selected_candidate_id"],
            "selected_plan_token_proxy": selected_token_proxy,
            "actual_model_calls": comparison["actual_model_calls"],
            "selected_critic_lanes": comparison["selected_assessment"][
                "selected_critic_lanes"
            ],
            "architect_intensity": execution.prepared.intensity,
            "source_act_capsules": len(execution.prepared.plan.act_capsules),
            "codemap_grounded_files": sum(
                1
                for item in execution.prepared.grounding
                if item.file_exists and item.codemap_file_hit
            ),
            "shadow_finding_count": len(execution.prepared.shadow_report.findings),
            "staged_patch_count": len(execution.prepared.arena.shared_patch_queue),
            "lease_count": len(execution.prepared.arena.agent_leases),
            "boundary_contract_count": len(
                execution.prepared.arena.boundary_contracts
            ),
            "verification_check_count": len(execution.verification.checks),
            "verification_failure_count": len(execution.verification.failures),
            "hotswap_ready": execution.verification.hotswap_ready,
            "judge_decision": judge["decision"],
            "canonical_owner_modules_reused": len(EXISTING_MODULES),
            "parallel_truth_stores_added": 0,
            "production_connectors_added": 0,
            "repository_file_count": repo_files,
            "source_file_scope_count": source_file_count,
            "structural_file_scope_reduction": structural_scope_reduction,
            "repository_text_tokens_est": repo_token_proxy,
            "planning_context_proxy_reduction": planning_context_reduction,
            "measurement_classes": {
                "elapsed_ms": "EXECUTABLE_CI_WALL_CLOCK",
                "test_results": "EXECUTABLE_PYTEST",
                "file_scope_reduction": "STRUCTURAL_CONTEXT_PROXY",
                "planning_context_reduction": "STRUCTURAL_PLAN_TOKEN_PROXY",
                "provider_tokens": NOT_MEASURED,
                "provider_cost": NOT_MEASURED,
                "real_project_savings": NOT_MEASURED,
                "production_readiness": "NOT_CLAIMED",
            },
        },
        "claim_boundaries": {
            "proposal_only": True,
            "human_review_required": True,
            "production_mutation": False,
            "physical_work_authorized": False,
            "payment_released": False,
            "provider_tokens": NOT_MEASURED,
            "provider_cost": NOT_MEASURED,
            "real_project_savings": NOT_MEASURED,
            "production_readiness": "NOT_CLAIMED",
        },
    }
    report["report_digest"] = _canonical_digest(report)
    (output_path / "architect_refactor_report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Aura's native Architect/Surgeon loop over SCO Phase 3."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--base-sha", required=True)
    parser.add_argument(
        "--output-dir",
        default="Aura_Staging/sco_construction_phase3_architect",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_construction_architect_refactor(
        repo_root=args.repo_root,
        base_sha=args.base_sha,
        output_dir=args.output_dir,
    )
    if args.json:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        benchmark = report["benchmarks"]
        print(
            "Aura Construction Architect refactor: "
            f"{benchmark['selected_plan_id']}, "
            f"{benchmark['source_act_capsules']} Act Capsules, "
            f"{benchmark['verification_failure_count']} verification failures, "
            f"Judge={benchmark['judge_decision']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONSTRUCTION_ARCHITECT_REFACTOR_VERSION",
    "EXISTING_MODULES",
    "NOT_MEASURED",
    "REQUIRED_CAPABILITIES",
    "SELECTED_PLAN_ID",
    "SOURCE_SHARDS",
    "build_refactor_plan_candidates",
    "run_construction_architect_refactor",
]
