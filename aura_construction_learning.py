"""Project verified SCO Phase 3 benchmark episodes into ArenaExperience V3 and Crucible."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from aura_arena_crucible import ArenaCrucibleService
from aura_arena_experience import OutcomeVector, build_arena_experience
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_arena_wfst_runtime import ArenaWFSTRuntime
from aura_construction_benchmark import run_construction_phase3_benchmark
from aura_construction_fixtures import build_sco_construction_demo_fixture

CONSTRUCTION_LEARNING_VERSION = "AURA_SCO_CONSTRUCTION_PHASE3_LEARNING_V1"
ARENA_ID = "sco_construction"
ARENA_VERSION = "AURA_SCO_CONSTRUCTION_ARENA_V1"
GRAMMAR_VERSION = "sco-construction-wfst-v1"
_TITLE_TRANSITIONS = {
    "Advance the Floor 4 electrical isolation package": (
        "CONSTRUCTION.ADVANCE_ELECTRICAL",
        "advance electrical package",
    ),
    "Shift the drilling crew to Floor 5 preparation": (
        "CONSTRUCTION.SHIFT_FLOOR5",
        "shift to floor 5 preparation",
    ),
    "Use the crane window and temporary labour on Floor 5 logistics": (
        "CONSTRUCTION.USE_CRANE_LOGISTICS",
        "use crane logistics window",
    ),
}


def run_construction_phase3_learning(
    *,
    repo_root: str | Path = ".",
    output_dir: str | Path,
    repository_commit_sha: str = "",
    experience_count: int = 15,
) -> dict[str, Any]:
    """Store verified synthetic/shadow episodes and run proposal-only Crucible."""
    root = Path(repo_root).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if type(experience_count) is not int or experience_count < 15:
        raise ValueError("experience_count must be at least 15 for the default split")

    benchmark = run_construction_phase3_benchmark(iterations=250, seed=1337)
    if not benchmark.get("ok"):
        raise RuntimeError("construction benchmark did not pass")
    report = dict(benchmark["report"])
    if not (
        report.get("unique_evaluation_digests") == 1
        and report.get("unique_recommendations") == 1
        and report.get("unsafe_high_score_candidate_blocked") is True
        and report.get("candidate_order_invariant") is True
    ):
        raise RuntimeError("construction benchmark verifier conditions failed")

    fixture = build_sco_construction_demo_fixture()
    recommendation = str(report.get("recommended_candidate_id") or "")
    recommended_candidate = next(
        (item for item in fixture.candidates if item.candidate_id == recommendation),
        None,
    )
    if recommended_candidate is None:
        raise RuntimeError("benchmark recommendation is not present in the fixture")
    transition = _TITLE_TRANSITIONS.get(recommended_candidate.title)
    if transition is None:
        raise RuntimeError("recommended candidate has no registered WFST transition")
    transition_id, input_text = transition

    manifest_path = root / ".aura" / "arena_routes" / "construction.v1.json"
    compiled = load_and_compile_arena_grammar(manifest_path)
    if not compiled.ok or compiled.grammar is None:
        raise RuntimeError("construction grammar did not compile")
    runtime = ArenaWFSTRuntime(repo_root=root)
    runtime.register_grammar(compiled.grammar)
    route = runtime.route(
        arena_id=ARENA_ID,
        current_state="DECIDE",
        input_text=input_text,
        evidence={
            "benchmark_report": report,
            "verification_packet": {"verification_ok": True},
        },
    )
    selected = dict(route.get("selected") or {})
    if selected.get("transition_id") != transition_id:
        raise RuntimeError("construction WFST did not admit the benchmark transition")

    experience_db = output / "arena_experience.db"
    crucible_db = output / "crucible.db"
    records: list[dict[str, Any]] = []
    base_time = 1000.0
    with ArenaExperienceLedger(root, db_path=experience_db) as ledger:
        for index in range(experience_count):
            execution_class = (
                "SYNTHETIC" if index < experience_count - 3 else "SHADOW"
            )
            vector = OutcomeVector(
                terminal_class="VERIFIED",
                task_progress=1.0,
                evidence_quality=1.0,
                verification_quality=1.0,
                safety_quality=1.0,
                human_alignment=1.0,
                cost_efficiency=None,
                latency_efficiency=None,
                abstention_quality=None,
                recovery_quality=None,
                measurement_classes={
                    "verification": "VERIFIER_BACKED",
                    "benchmark": "EXECUTABLE_SYNTHETIC_FIXTURE",
                    "provider_tokens": "UNAVAILABLE",
                    "provider_cost": "UNAVAILABLE",
                },
                labels=(execution_class, "PROPOSAL_ONLY", "HUMAN_RELEASE_REQUIRED"),
            )
            experience = build_arena_experience(
                arena_id=ARENA_ID,
                arena_version=ARENA_VERSION,
                grammar_version=GRAMMAR_VERSION,
                grammar_manifest_digest=compiled.manifest_digest,
                runtime_version="AURA_ARENA_WFST_RUNTIME_V2",
                compiler_version=CONSTRUCTION_LEARNING_VERSION,
                state_before="DECIDE",
                state_after="DECIDE",
                selected_transition=transition_id,
                final_outcome="VERIFIED",
                outcome_vector=vector,
                payload={
                    "route": route,
                    "benchmark": benchmark,
                    "execution_class": execution_class,
                    "authority_boundary": {
                        "proposal_only": True,
                        "physical_work_authorized": False,
                        "payment_released": False,
                        "automatic_grammar_promotion": False,
                    },
                },
                experience_id=f"EXP-SCO-PHASE3-{index:03d}",
                task_id=f"SCO-PHASE3-{index:03d}",
                workflow_id="SCO-E7-E8",
                started_at=base_time + index * 2.0,
                completed_at=base_time + index * 2.0 + 0.01,
                repository_commit_sha=repository_commit_sha,
                objective=(
                    f"SCO synthetic coordination benchmark objective {index % 3}"
                ),
                provider="LOCAL_ZERO_MODEL",
                model="NONE",
                measurement_class="VERIFIER_BACKED",
                actual_model="NONE",
                actual_tool_calls=(
                    "run_construction_phase3_benchmark",
                    "ArenaWFSTRuntime.route",
                ),
                budget_requested={"model_calls": 0},
                budget_consumed={"model_calls": 0},
            )
            stored = ledger.record(experience)
            if not stored.get("ok"):
                raise RuntimeError(f"experience storage failed: {stored}")
            records.append(
                {
                    "experience_id": experience.experience_id,
                    "experience_digest": stored["experience_digest"],
                    "execution_class": execution_class,
                    "eligible_for_crucible": True,
                }
            )
        ledger_status = ledger.status()

    service = ArenaCrucibleService(
        root,
        experience_db_path=experience_db,
        crucible_db_path=crucible_db,
    )
    try:
        crucible = service.run_once(arena_id=ARENA_ID)
    finally:
        service.close()

    result = {
        "ok": bool(crucible.get("ok")),
        "version": CONSTRUCTION_LEARNING_VERSION,
        "benchmark": benchmark,
        "experience_ledger": {
            "record_count": len(records),
            "records": records,
            "status": ledger_status,
        },
        "crucible": crucible,
        "claim_boundaries": {
            "synthetic_and_shadow_only": True,
            "provider_tokens_and_cost": "NOT_MEASURED",
            "real_project_savings": "NOT_MEASURED",
            "production_readiness": "NOT_CLAIMED",
            "physical_work_authorized": False,
            "payment_released": False,
            "active_grammar_mutated": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        },
        "coderabbit_triggered": False,
    }
    (output / "sco_phase3_learning_evidence.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--experience-count", type=int, default=15)
    args = parser.parse_args()
    result = run_construction_phase3_learning(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        repository_commit_sha=os.environ.get("GITHUB_SHA", ""),
        experience_count=args.experience_count,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
