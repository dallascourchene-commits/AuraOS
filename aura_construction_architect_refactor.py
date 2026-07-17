"""Run SCO Construction changes through Aura's native refactor architecture.

The branch diff is treated as four bounded Act Capsules: coordination, synthetic
fixtures, deterministic benchmarking, and governed learning. Selective Council
V3 compares frozen plans; Work Splitter, CODEMAP grounding, Shadow, Liquid
Planning leases, Surgeon staging, Verifier, Judge, rollback, hot-swap, and the
append-only Architect ledger remain the canonical execution owners.

Nothing in this module grants production, VSA, merge, deployment, physical-work,
payment, access, professional, legal, regulatory, or Crucible promotion authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
from typing import Any, Mapping

from aura_architect_control import normalize_control_profile
from aura_architect_loop import ArchitectFusionLoop, judge_refactor_arena
from aura_arena_architect_connector import AuraArenaArchitectConnector
from aura_work_splitter import split_by_file, work_split_to_act_capsules

CONSTRUCTION_ARCHITECT_REFACTOR_VERSION = (
    "AURA_SCO_CONSTRUCTION_ARCHITECT_REFACTOR_V3"
)
NOT_MEASURED = "NOT_MEASURED"
SELECTED_PLAN_ID = "SELECTIVE_COUNCIL_V3_SURGEON"
_COMMIT_SHA = re.compile(r"^[0-9a-f]{7,64}$")

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
            "Hard blockers precede ranking, serialized inputs fail closed, option roles "
            "remain stable, and both adapter test suites pass."
        ),
        "tests": (
            "tests/test_aura_construction_adapter.py",
            "tests/test_aura_construction_adapter_hardening.py",
        ),
        "allowed_scope": "single Construction adapter module",
        "expected_output": "UNIFIED_DIFF",
        "size": "M",
    },
    {
        "task_id": "SCO-E8-FIXTURE",
        "objective": (
            "Harden deterministic fictional SCO fixtures without private project data "
            "or production connectors."
        ),
        "target_file": "aura_construction_fixtures.py",
        "target_symbol": "build_sco_construction_demo_fixture",
        "acceptance": (
            "Replay stays deterministic, the unsafe high-score route remains blocked, "
            "and tests/test_aura_construction_fixtures.py passes."
        ),
        "tests": ("tests/test_aura_construction_fixtures.py",),
        "allowed_scope": "single synthetic fixture module",
        "expected_output": "UNIFIED_DIFF",
        "size": "S",
    },
    {
        "task_id": "SCO-E11-BENCHMARK",
        "objective": (
            "Harden the zero-model benchmark and its truth-class boundaries without "
            "inventing provider usage or real-project savings."
        ),
        "target_file": "aura_construction_benchmark.py",
        "target_symbol": "run_construction_phase3_benchmark",
        "acceptance": (
            "The 250-permutation gate stays deterministic and "
            "tests/test_aura_construction_benchmark.py passes."
        ),
        "tests": ("tests/test_aura_construction_benchmark.py",),
        "allowed_scope": "single executable benchmark module",
        "expected_output": "UNIFIED_DIFF",
        "size": "S",
    },
    {
        "task_id": "SCO-E10-LEARNING",
        "objective": (
            "Project only truthful synthetic permutation executions into the existing "
            "Experience Ledger and proposal-only Crucible owners."
        ),
        "target_file": "aura_construction_learning.py",
        "target_symbol": "run_construction_phase3_learning",
        "acceptance": (
            "Single-scenario evidence cannot satisfy generalization thresholds, Crucible "
            "remains proposal-only, and tests/test_aura_construction_learning.py passes."
        ),
        "tests": ("tests/test_aura_construction_learning.py",),
        "allowed_scope": "single governed learning projection module",
        "expected_output": "UNIFIED_DIFF",
        "size": "M",
    },
)

REQUIRED_CAPABILITIES: tuple[str, ...] = (
    "canonical_owner_reuse",
    "hard_filter_before_ranking",
    "proposal_only_authority",
    "synthetic_fixture_boundary",
    "deterministic_benchmark",
    "experience_crucible_evidence_integrity",
    "bounded_patch_leases",
    "rollback_and_human_review",
)

EXISTING_MODULES: tuple[str, ...] = (
    "aura_construction_contracts.py",
    "aura_construction_state.py",
    "aura_construction_authority.py",
    "aura_liquid_planning_arena.py",
    "aura_arena_wfst_runtime.py",
    "aura_arena_experience.py",
    "aura_arena_experience_ledger.py",
    "aura_arena_crucible.py",
    "aura_architect_loop.py",
    "aura_architect_control.py",
    "aura_arena_architect_connector.py",
    "aura_work_splitter.py",
)


def _canonical_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _task_without_tests(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "tests"}


def _base_plan(
    *,
    architecture_decision: str,
    tasks: list[Mapping[str, Any]],
    coverage_tags: list[str],
    architecture_reuse: bool,
    acceptance: list[str],
    rollback: list[str],
    risks: list[str],
    constraints: list[str],
) -> dict[str, Any]:
    return {
        "architecture_decision": architecture_decision,
        "act_tasks": [dict(item) for item in tasks],
        "acceptance_criteria": list(acceptance),
        "rollback_conditions": list(rollback),
        "risk_map": list(risks),
        "constraints": list(constraints),
        "coverage_tags": list(coverage_tags),
        "architecture_reuse": architecture_reuse,
        "existing_modules": list(EXISTING_MODULES) if architecture_reuse else [],
        "domains": ["construction", "code", "verification", "learning"],
        "dependency_edges": [
            ["SCO-E7-ADAPTER", "SCO-E8-FIXTURE"],
            ["SCO-E8-FIXTURE", "SCO-E11-BENCHMARK"],
            ["SCO-E11-BENCHMARK", "SCO-E10-LEARNING"],
        ],
    }


def build_refactor_plan_candidates() -> list[dict[str, Any]]:
    """Build frozen, zero-model alternatives for Selective Council V3."""
    source_tasks = [_task_without_tests(item) for item in SOURCE_SHARDS]
    selective_tasks = [
        {
            **item,
            "escalate_if": [
                "target symbol is absent from CODEMAP",
                "patch crosses its leased file",
                "paired focused test fails",
                "authority or evidence boundary changes",
            ],
        }
        for item in source_tasks
    ]
    broad_task = {
        "task_id": "BROAD-1",
        "objective": "Rewrite the complete Construction intelligence subsystem.",
        "target_file": "aura_construction_adapter.py",
        "target_symbol": "evaluate_construction_candidates",
        "acceptance": "Construction tests pass.",
        "expected_output": "UNIFIED_DIFF",
        "size": "XL",
    }
    candidates = [
        {
            "candidate_id": "BROAD_IMPLEMENTER",
            "arm_family": "BROAD_IMPLEMENTER",
            "plan": _base_plan(
                architecture_decision="Use one broad cross-concern rewrite.",
                tasks=[broad_task],
                coverage_tags=["deterministic_benchmark"],
                architecture_reuse=False,
                acceptance=["Focused tests pass."],
                rollback=["Revert the broad patch on failure."],
                risks=["Large patch mixes truth, runtime, benchmark, and learning."],
                constraints=["No production mutation."],
            ),
        },
        {
            "candidate_id": "ZERO_MODEL_MINIMAL",
            "arm_family": "ZERO_MODEL_MINIMAL",
            "plan": _base_plan(
                architecture_decision="Patch only the adapter and defer other surfaces.",
                tasks=[{**source_tasks[0], "task_id": "MINIMAL-1"}],
                coverage_tags=[
                    "hard_filter_before_ranking",
                    "proposal_only_authority",
                ],
                architecture_reuse=True,
                acceptance=["Adapter tests pass."],
                rollback=["Revert the adapter patch."],
                risks=["Fixture, benchmark, and learning remain unreviewed."],
                constraints=["No production mutation."],
            ),
        },
        {
            "candidate_id": "SLICED_SURGEON",
            "arm_family": "SLICED_SURGEON",
            "plan": _base_plan(
                architecture_decision="Use four bounded Surgeon shards.",
                tasks=source_tasks,
                coverage_tags=list(REQUIRED_CAPABILITIES[:-1]),
                architecture_reuse=True,
                acceptance=[
                    "All focused suites pass.",
                    "No source shard crosses its file boundary.",
                ],
                rollback=["Discard any failed shard by phase hash."],
                risks=["Cross-shard ordering needs explicit verification."],
                constraints=[
                    "Reuse canonical owners.",
                    "No production, physical-work, payment, or learning authority.",
                ],
            ),
        },
        {
            "candidate_id": SELECTED_PLAN_ID,
            "arm_family": "SELECTIVE_COUNCIL_V3_PLUS_SURGEON",
            "plan": _base_plan(
                architecture_decision=(
                    "Reuse Construction, Liquid Planning, WFST, Experience, Crucible, "
                    "and Architect owners; route ambiguity through Selective Council V3; "
                    "execute four exact Surgeon shards under leases and Verifier/Judge gates."
                ),
                tasks=selective_tasks,
                coverage_tags=list(REQUIRED_CAPABILITIES),
                architecture_reuse=True,
                acceptance=[
                    "All Act Capsules are CODEMAP-grounded.",
                    "Shadow reports no blockers.",
                    "Every staged diff remains inside one file lease.",
                    "All paired tests pass under Verifier.",
                    "Judge returns promote_hotswap with human review still required.",
                    "Benchmark and learning evidence never invent usage or savings.",
                ],
                rollback=[
                    "Any Shadow, lease, test, authority, or replay failure blocks hot-swap.",
                    "Rollback retains exact phase and file digests.",
                ],
                risks=[
                    "Probabilistic scores may not override exact readiness blockers.",
                    "Synthetic fixture or learning values are not real project facts.",
                    "Repeated seeded executions are not independent field outcomes.",
                    "Crucible output remains an unpromoted proposal.",
                ],
                constraints=[
                    "Patch authority is exact source spans and hashes only.",
                    "VSA patch authority remains false.",
                    "No production connectors or private project data.",
                    "No physical, payment, access, professional, legal, or regulatory authority.",
                    "Human review remains mandatory before merge or deployment.",
                ],
            ),
        },
    ]
    for candidate in candidates:
        candidate["provenance"] = {
            "generation": "frozen_local_plan",
            "model_calls": 0,
        }
        candidate["token_usage"] = {
            "provider_reported": None,
            "measurement_class": NOT_MEASURED,
        }
    return candidates


def _normalize_base_sha(value: Any) -> str:
    if type(value) is not str or not _COMMIT_SHA.fullmatch(value.strip().lower()):
        raise ValueError("base_sha must be a hexadecimal commit SHA")
    return value.strip().lower()


def _resolve_output(root: Path, output_dir: str | Path) -> tuple[Path, PurePosixPath]:
    output = Path(output_dir)
    if output.is_absolute():
        raise ValueError("output_dir must be repository-relative")
    raw = PurePosixPath(str(output).replace("\\", "/"))
    if not raw.parts or any(part in {"", ".", ".."} for part in raw.parts):
        raise ValueError("output_dir must be a safe repository-relative path")
    resolved = (root / Path(*raw.parts)).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("output_dir escapes the repository root") from exc
    return resolved, raw


def _verify_git_boundary(repo_root: Path, base_sha: str) -> str:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout.strip()
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{base_sha}^{{commit}}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if exists.returncode != 0:
        raise ValueError("base_sha is not an available commit")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_sha, head],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if ancestry.returncode != 0:
        raise ValueError("base_sha is not an ancestor of HEAD")
    return head


def _git_diff_for_file(repo_root: Path, base_sha: str, path: str) -> str:
    if path not in {str(item["target_file"]) for item in SOURCE_SHARDS}:
        raise ValueError(f"unleased Architect shard path: {path}")
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
    allowed = {
        test
        for shard in SOURCE_SHARDS
        for test in tuple(shard.get("tests") or ())
    }
    if test_name not in allowed:
        return {
            "ok": False,
            "returncode": 2,
            "test": test_name,
            "elapsed_ms": 0.0,
            "stdout_tail": "",
            "stderr_tail": "test target is outside the Construction Act Capsule allowlist",
        }
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", test_name],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "test": test_name,
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
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
    if not isinstance(payload, dict):
        raise RuntimeError("CODEMAP root must be an object")
    summary = dict(payload.get("summary") or {})
    coverage = dict(payload.get("coverage") or {})
    return {
        "repository_file_count": summary.get("file_count")
        or coverage.get("included_file_count")
        or NOT_MEASURED,
        "repository_text_tokens_est": summary.get("text_tokens_est", NOT_MEASURED),
    }


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_construction_architect_refactor(
    *,
    repo_root: str | Path,
    base_sha: str,
    output_dir: str | Path = "Aura_Staging/sco_construction_phase3_architect",
) -> dict[str, Any]:
    """Verify the exact branch diff through Aura's governed refactor loop."""
    root = Path(repo_root).resolve()
    normalized_base = _normalize_base_sha(base_sha)
    output_path, output_relative = _resolve_output(root, output_dir)
    head_sha = _verify_git_boundary(root, normalized_base)
    output_path.mkdir(parents=True, exist_ok=True)

    control = normalize_control_profile(
        {
            "surface": "native",
            "council_mode": "SELECTIVE_V3",
            "council_call_budget": 8,
            "critic_lanes": ["scope", "tests", "sequence", "rollback", "cost"],
            "surgeon_mode": "STAGE_AND_VERIFY",
            "surgeon_max_turns": 16,
            "surgeon_max_local_repairs": 2,
            "record_outputs": True,
            "output_root": output_relative.as_posix(),
        },
        benchmark=True,
    )
    candidates = build_refactor_plan_candidates()
    objective = (
        "Verify the SCO Construction E7-E11 refactor by reusing Aura's canonical "
        "architecture, preserving authority and evidence boundaries, and recording "
        "executable refactor and learning benchmarks."
    )
    run_id = (
        "SCO-P3-"
        + hashlib.blake2b(
            f"{normalized_base}:{head_sha}".encode("utf-8"), digest_size=8
        ).hexdigest()
    )
    started = time.perf_counter()
    comparison = AuraArenaArchitectConnector(root, bridge=object()).compare_plans(
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
    tests_by_task = {
        str(item["task_id"]): list(item["tests"]) for item in SOURCE_SHARDS
    }
    patch_submissions = []
    for task in selected_plan["act_tasks"]:
        task_id = str(task["task_id"])
        target_file = str(task["target_file"])
        if task_id not in tests_by_task:
            raise RuntimeError(f"selected plan contains unknown task: {task_id}")
        patch_submissions.append(
            {
                "task_id": task_id,
                "owner": "aura_surgeon",
                "diff": _git_diff_for_file(root, normalized_base, target_file),
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
        context_pressure=0.92,
        runner=lambda test_name: _pytest_runner(root, test_name),
        ledger_path=output_path / "architect_ledger.jsonl",
    )
    judge = judge_refactor_arena(execution.verification)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if not all(item.ok for item in execution.stage_results):
        raise RuntimeError("Aura Surgeon rejected a Construction source shard")
    if not execution.verification.hotswap_ready:
        raise RuntimeError(
            "Aura Verifier blocked the Construction refactor: "
            f"{execution.verification.failures}"
        )
    if judge["decision"] != "promote_hotswap":
        raise RuntimeError(f"Aura Judge blocked the verified refactor: {judge}")

    codemap = _codemap_metrics(root)
    repo_files = codemap["repository_file_count"]
    repo_tokens = codemap["repository_text_tokens_est"]
    source_count = len(SOURCE_SHARDS)
    selected_tokens = comparison["selected_assessment"]["token_proxy"]
    file_scope_reduction = (
        round(1.0 - source_count / float(repo_files), 6)
        if isinstance(repo_files, int) and repo_files > 0
        else NOT_MEASURED
    )
    context_proxy_reduction = (
        round(1.0 - selected_tokens / float(repo_tokens), 6)
        if isinstance(repo_tokens, int) and repo_tokens > 0
        else NOT_MEASURED
    )
    report = {
        "ok": True,
        "version": CONSTRUCTION_ARCHITECT_REFACTOR_VERSION,
        "run_id": run_id,
        "base_sha": normalized_base,
        "head_sha": head_sha,
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
            "selected_plan_token_proxy": selected_tokens,
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
            "source_file_scope_count": source_count,
            "structural_file_scope_reduction": file_scope_reduction,
            "repository_text_tokens_est": repo_tokens,
            "planning_context_proxy_reduction": context_proxy_reduction,
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
            "active_grammar_mutated": False,
            "provider_tokens": NOT_MEASURED,
            "provider_cost": NOT_MEASURED,
            "real_project_savings": NOT_MEASURED,
            "production_readiness": "NOT_CLAIMED",
        },
    }
    report["report_digest"] = _canonical_digest(report)
    _atomic_json(output_path / "architect_refactor_report.json", report)
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
