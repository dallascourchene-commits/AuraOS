"""Project verified SCO benchmark episodes into Experience Ledger and Crucible.

Each stored episode is a separate seeded execution of one deterministic synthetic
scenario. The module preserves that distinction: repeated permutations may test
software invariance, but they are not relabelled as distinct project situations,
human approvals, provider usage, or production outcomes. Crucible remains
proposal-only and cannot mutate active grammars or gain operational authority.
"""
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
from aura_event_contracts import stable_digest

CONSTRUCTION_LEARNING_VERSION = "AURA_SCO_CONSTRUCTION_PHASE3_LEARNING_V4"
ARENA_ID = "sco_construction"
ARENA_VERSION = "AURA_SCO_CONSTRUCTION_ARENA_V1"
GRAMMAR_VERSION = "sco-construction-wfst-v1"
NOT_MEASURED = "NOT_MEASURED"
_MIN_EXPERIENCES = 15
_MAX_EXPERIENCES = 500
_MAX_ITERATIONS_PER_EXPERIENCE = 10_000
_OBJECTIVE = (
    "Verify deterministic proposal-only construction alternative ranking for the "
    "single synthetic SCO demonstration scenario."
)
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


def _validated_benchmark(*, iterations: int, seed: int) -> dict[str, Any]:
    benchmark = run_construction_phase3_benchmark(iterations=iterations, seed=seed)
    if not benchmark.get("ok"):
        raise RuntimeError(f"construction benchmark did not pass for seed {seed}")
    report = dict(benchmark["report"])
    if not (
        report.get("unique_evaluation_digests") == 1
        and report.get("unique_recommendations") == 1
        and report.get("unsafe_high_score_candidate_blocked") is True
        and report.get("candidate_order_invariant") is True
    ):
        raise RuntimeError(
            f"construction benchmark verifier conditions failed for seed {seed}"
        )
    return benchmark


def _deterministic_benchmark_observation(
    benchmark: dict[str, Any],
) -> dict[str, Any]:
    """Remove run-local timing before content-addressed experience storage."""
    observation = json.loads(json.dumps(benchmark, sort_keys=True, default=str))
    report = dict(observation.get("report") or {})
    report.pop("elapsed_ms", None)
    observation["report"] = report
    observation["timing_evidence"] = "RECORDED_IN_RUN_REPORT_ONLY"
    return observation


def _registered_transition(*, recommendation: str) -> tuple[str, str]:
    fixture = build_sco_construction_demo_fixture()
    recommended_candidate = next(
        (item for item in fixture.candidates if item.candidate_id == recommendation),
        None,
    )
    if recommended_candidate is None:
        raise RuntimeError("benchmark recommendation is not present in the fixture")
    transition = _TITLE_TRANSITIONS.get(recommended_candidate.title)
    if transition is None:
        raise RuntimeError("recommended candidate has no registered WFST transition")
    return transition


def _validate_bounds(
    *, experience_count: int, iterations_per_experience: int, seed_base: int
) -> None:
    if type(experience_count) is not int or not (
        _MIN_EXPERIENCES <= experience_count <= _MAX_EXPERIENCES
    ):
        raise ValueError(
            f"experience_count must be between {_MIN_EXPERIENCES} and "
            f"{_MAX_EXPERIENCES}"
        )
    if type(iterations_per_experience) is not int or not (
        1 <= iterations_per_experience <= _MAX_ITERATIONS_PER_EXPERIENCE
    ):
        raise ValueError(
            "iterations_per_experience must be a positive bounded integer"
        )
    if type(seed_base) is not int or seed_base < 0:
        raise ValueError("seed_base must be a non-negative integer")


def _validate_crucible_boundary(crucible: dict[str, Any]) -> None:
    if crucible.get("ok") is not True:
        raise RuntimeError("Crucible run did not complete")
    for field in (
        "thresholds_have_runtime_authority",
        "active_grammar_mutated",
        "learned_weight_patch_authority",
        "crystallization_patch_authority",
        "automatic_grammar_promotion",
        "automatic_commit",
        "automatic_push",
        "automatic_merge",
    ):
        if crucible.get(field) is not False:
            raise RuntimeError(f"Crucible crossed proposal-only boundary: {field}")
    for proposal in crucible.get("proposals", []):
        validation = dict(proposal.get("validation") or {})
        if validation.get("all_proposal_thresholds_met") is True:
            raise RuntimeError(
                "single-scenario permutation evidence may not satisfy all "
                "generalization thresholds"
            )


def run_construction_phase3_learning(
    *,
    repo_root: str | Path = ".",
    output_dir: str | Path,
    repository_commit_sha: str = "",
    experience_count: int = _MIN_EXPERIENCES,
    iterations_per_experience: int = 25,
    seed_base: int = 1337,
) -> dict[str, Any]:
    """Store seeded synthetic executions and run proposal-only Crucible analysis."""
    _validate_bounds(
        experience_count=experience_count,
        iterations_per_experience=iterations_per_experience,
        seed_base=seed_base,
    )
    root = Path(repo_root).resolve()
    output = Path(output_dir).resolve()
    if output == root:
        raise ValueError("output_dir may not be the repository root")
    output.mkdir(parents=True, exist_ok=True)

    manifest_path = root / ".aura" / "arena_routes" / "construction.v1.json"
    compiled = load_and_compile_arena_grammar(manifest_path)
    if not compiled.ok or compiled.grammar is None:
        raise RuntimeError("construction grammar did not compile")
    runtime = ArenaWFSTRuntime(repo_root=root)
    runtime.register_grammar(compiled.grammar)

    experience_db = output / "arena_experience.db"
    crucible_db = output / "crucible.db"
    records: list[dict[str, Any]] = []
    episode_reports: list[dict[str, Any]] = []
    base_time = 1000.0
    expected_recommendation = ""
    expected_evaluation_digest = ""

    with ArenaExperienceLedger(root, db_path=experience_db) as ledger:
        initial_count = int(ledger.status().get("record_count") or 0)
        if initial_count not in {0, experience_count}:
            raise RuntimeError(
                "learning output contains an incompatible prior experience set"
            )
        for index in range(experience_count):
            seed = seed_base + index
            benchmark = _validated_benchmark(
                iterations=iterations_per_experience,
                seed=seed,
            )
            deterministic_benchmark = _deterministic_benchmark_observation(benchmark)
            report = dict(benchmark["report"])
            recommendation = str(report.get("recommended_candidate_id") or "")
            evaluation_digest = str(report.get("stable_evaluation_digest") or "")
            if index == 0:
                expected_recommendation = recommendation
                expected_evaluation_digest = evaluation_digest
            elif (
                recommendation != expected_recommendation
                or evaluation_digest != expected_evaluation_digest
            ):
                raise RuntimeError(
                    "seeded benchmark episodes disagree on deterministic outcome"
                )

            transition_id, input_text = _registered_transition(
                recommendation=recommendation
            )
            route = runtime.route(
                arena_id=ARENA_ID,
                current_state="DECIDE",
                input_text=input_text,
                evidence={
                    "benchmark_report": deterministic_benchmark["report"],
                    "verification_packet": {"verification_ok": True},
                    "episode_seed": seed,
                },
            )
            selected = dict(route.get("selected") or {})
            if selected.get("transition_id") != transition_id:
                raise RuntimeError(
                    f"construction WFST did not admit seed {seed} transition"
                )

            episode_identity = {
                "seed": seed,
                "iterations": iterations_per_experience,
                "recommendation": recommendation,
                "evaluation_digest": evaluation_digest,
                "route_transition": transition_id,
                "scenario_id": "SCO_SYNTHETIC_SCENARIO_1",
            }
            episode_digest = stable_digest(episode_identity)
            vector = OutcomeVector(
                terminal_class="VERIFIED",
                task_progress=1.0,
                evidence_quality=1.0,
                verification_quality=1.0,
                safety_quality=1.0,
                human_alignment=None,
                cost_efficiency=None,
                latency_efficiency=None,
                abstention_quality=None,
                recovery_quality=None,
                measurement_classes={
                    "verification": "VERIFIER_BACKED",
                    "benchmark": "EXECUTABLE_SYNTHETIC_FIXTURE",
                    "human_alignment": "UNAVAILABLE",
                    "provider_tokens": "UNAVAILABLE",
                    "provider_cost": "UNAVAILABLE",
                },
                labels=(
                    "SYNTHETIC_PERMUTATION_EXECUTION",
                    "SINGLE_SCENARIO",
                    "PROPOSAL_ONLY",
                    "HUMAN_RELEASE_REQUIRED",
                ),
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
                    "benchmark": deterministic_benchmark,
                    "episode_seed": seed,
                    "episode_digest": episode_digest,
                    "scenario_id": "SCO_SYNTHETIC_SCENARIO_1",
                    "execution_class": "SYNTHETIC_PERMUTATION",
                    "timestamp_class": "SYNTHETIC_DETERMINISTIC",
                    "generalization_claimed": False,
                    "authority_boundary": {
                        "proposal_only": True,
                        "physical_work_authorized": False,
                        "payment_released": False,
                        "automatic_grammar_promotion": False,
                    },
                },
                experience_id=f"EXP-SCO-PHASE3-{seed:08d}",
                task_id=f"SCO-PHASE3-{seed:08d}",
                workflow_id="SCO-E7-E8",
                started_at=base_time + index * 2.0,
                completed_at=base_time + index * 2.0 + 0.01,
                repository_commit_sha=repository_commit_sha,
                objective=_OBJECTIVE,
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
                    "idempotent_replay": bool(stored.get("idempotent_replay")),
                    "episode_digest": episode_digest,
                    "seed": seed,
                    "execution_class": "SYNTHETIC_PERMUTATION",
                    "eligible_for_crucible_observation": True,
                    "eligible_for_generalization_claim": False,
                }
            )
            episode_reports.append(
                {
                    "seed": seed,
                    "iterations": iterations_per_experience,
                    "evaluation_digest": evaluation_digest,
                    "recommendation": recommendation,
                    "episode_digest": episode_digest,
                    "elapsed_ms": report.get("elapsed_ms"),
                    "measurement_class": "EXECUTABLE_SYNTHETIC_FIXTURE",
                }
            )
        ledger_status = ledger.status()

    if len({item["episode_digest"] for item in records}) != experience_count:
        raise RuntimeError("seeded benchmark episodes did not produce unique evidence IDs")
    if int(ledger_status.get("record_count") or 0) != experience_count:
        raise RuntimeError("experience ledger contains an unexpected record count")

    service = ArenaCrucibleService(
        root,
        experience_db_path=experience_db,
        crucible_db_path=crucible_db,
    )
    try:
        crucible = service.run_once(arena_id=ARENA_ID)
    finally:
        service.close()
    _validate_crucible_boundary(crucible)

    result = {
        "ok": True,
        "version": CONSTRUCTION_LEARNING_VERSION,
        "benchmark_series": {
            "episode_count": experience_count,
            "iterations_per_episode": iterations_per_experience,
            "seed_base": seed_base,
            "scenario_count": 1,
            "objective_count": 1,
            "unique_episode_digests": len(
                {item["episode_digest"] for item in episode_reports}
            ),
            "unique_evaluation_digests": len(
                {item["evaluation_digest"] for item in episode_reports}
            ),
            "unique_recommendations": len(
                {item["recommendation"] for item in episode_reports}
            ),
            "reports": episode_reports,
            "provider_tokens": NOT_MEASURED,
            "provider_cost": NOT_MEASURED,
            "real_project_savings": NOT_MEASURED,
        },
        "experience_ledger": {
            "record_count": len(records),
            "records": records,
            "status": ledger_status,
        },
        "crucible": crucible,
        "claim_boundaries": {
            "synthetic_only": True,
            "single_synthetic_scenario": True,
            "independent_permutation_executions": True,
            "distinct_project_scenarios": 1,
            "distinct_objectives": 1,
            "source_episode_cloning": False,
            "generalization_claimed": False,
            "all_proposal_thresholds_expected": False,
            "content_addressed_payload_excludes_wall_clock_timing": True,
            "crucible_dataset_split": "INTERNAL_TEMPORAL_TRAIN_VALIDATION_SHADOW",
            "provider_tokens_and_cost": NOT_MEASURED,
            "real_project_savings": NOT_MEASURED,
            "production_readiness": "NOT_CLAIMED",
            "physical_work_authorized": False,
            "payment_released": False,
            "active_grammar_mutated": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        },
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
    parser.add_argument("--experience-count", type=int, default=_MIN_EXPERIENCES)
    parser.add_argument("--iterations-per-experience", type=int, default=25)
    parser.add_argument("--seed-base", type=int, default=1337)
    args = parser.parse_args()
    result = run_construction_phase3_learning(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        repository_commit_sha=os.environ.get("GITHUB_SHA", ""),
        experience_count=args.experience_count,
        iterations_per_experience=args.iterations_per_experience,
        seed_base=args.seed_base,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARENA_ID",
    "ARENA_VERSION",
    "CONSTRUCTION_LEARNING_VERSION",
    "GRAMMAR_VERSION",
    "NOT_MEASURED",
    "run_construction_phase3_learning",
]
