"""Executable zero-model benchmark for the SCO Construction coordination adapter."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import random
import time
from typing import Any

from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaMode,
    evaluate_construction_candidates,
)
from aura_construction_fixtures import build_sco_construction_demo_fixture
from aura_event_contracts import stable_digest

CONSTRUCTION_BENCHMARK_VERSION = "AURA_SCO_CONSTRUCTION_PHASE3_BENCHMARK_V2"
_MAX_ITERATIONS = 10_000


@dataclass(frozen=True)
class ConstructionBenchmarkReport:
    iterations: int
    stable_evaluation_digest: str
    unique_evaluation_digests: int
    unique_recommendations: int
    recommended_candidate_id: str
    blocked_candidate_count: int
    admissible_candidate_count: int
    displayed_option_count: int
    unsafe_high_score_candidate_blocked: bool
    candidate_order_invariant: bool
    elapsed_ms: float
    version: str = CONSTRUCTION_BENCHMARK_VERSION
    measurement_class: str = "EXECUTABLE_SYNTHETIC_FIXTURE"
    provider_tokens: str = "NOT_MEASURED"
    provider_cost: str = "NOT_MEASURED"
    real_project_savings: str = "NOT_MEASURED"
    production_readiness: str = "NOT_CLAIMED"

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_BENCHMARK_VERSION:
            raise ValueError("unsupported Construction benchmark version")
        if type(self.iterations) is not int or not 1 <= self.iterations <= _MAX_ITERATIONS:
            raise ValueError("iterations must be a positive bounded integer")
        if type(self.stable_evaluation_digest) is not str or not self.stable_evaluation_digest:
            raise ValueError("stable_evaluation_digest is required")
        if type(self.recommended_candidate_id) is not str or not self.recommended_candidate_id:
            raise ValueError("recommended_candidate_id is required")
        for name, value in (
            ("unique_evaluation_digests", self.unique_evaluation_digests),
            ("unique_recommendations", self.unique_recommendations),
            ("blocked_candidate_count", self.blocked_candidate_count),
            ("admissible_candidate_count", self.admissible_candidate_count),
            ("displayed_option_count", self.displayed_option_count),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.displayed_option_count > 4:
            raise ValueError("displayed_option_count may not exceed four")
        if type(self.elapsed_ms) is not float or not math.isfinite(self.elapsed_ms) or self.elapsed_ms < 0.0:
            raise ValueError("elapsed_ms must be a non-negative canonical float")
        if self.unique_evaluation_digests != 1:
            raise ValueError("deterministic benchmark produced multiple evaluation digests")
        if self.unique_recommendations != 1:
            raise ValueError("deterministic benchmark produced multiple recommendations")
        if self.unsafe_high_score_candidate_blocked is not True:
            raise ValueError("unsafe high-score candidate escaped the hard filter")
        if self.candidate_order_invariant is not True:
            raise ValueError("candidate input order changed the evaluation")
        if self.measurement_class != "EXECUTABLE_SYNTHETIC_FIXTURE":
            raise ValueError("benchmark measurement_class was relabelled")
        if any(
            value != "NOT_MEASURED"
            for value in (
                self.provider_tokens,
                self.provider_cost,
                self.real_project_savings,
            )
        ):
            raise ValueError("benchmark may not invent provider or real-project measurements")
        if self.production_readiness != "NOT_CLAIMED":
            raise ValueError("benchmark may not claim production readiness")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_construction_phase3_benchmark(
    *,
    iterations: int = 250,
    seed: int = 1337,
) -> dict[str, Any]:
    """Run deterministic permutation/replay checks over the synthetic fixture."""
    if type(iterations) is not int or not 1 <= iterations <= _MAX_ITERATIONS:
        raise ValueError("iterations must be a positive bounded integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")

    fixture = build_sco_construction_demo_fixture()
    signals = fixture.probabilistic_signals
    randomizer = random.Random(seed)
    digests: set[str] = set()
    recommendations: set[str] = set()
    canonical_assessment_projection = ""
    unsafe_candidate_id = max(
        fixture.candidates,
        key=lambda item: next(
            signal.aggregate_score
            for signal in signals
            if signal.candidate_id == item.candidate_id
        ),
    ).candidate_id
    unsafe_blocked = True
    started = time.perf_counter()

    for _ in range(iterations):
        candidates = list(fixture.candidates)
        shuffled_signals = list(signals)
        randomizer.shuffle(candidates)
        randomizer.shuffle(shuffled_signals)
        evaluation = evaluate_construction_candidates(
            fixture.state,
            candidates=candidates,
            now=30.0,
            mode=ConstructionArenaMode.SYNTHETIC,
            lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
            probabilistic_signals=shuffled_signals,
        )
        digests.add(evaluation.evaluation_digest)
        recommendations.add(evaluation.recommended_candidate_id)
        unsafe_assessment = next(
            item
            for item in evaluation.assessments
            if item.candidate_id == unsafe_candidate_id
        )
        unsafe_blocked = unsafe_blocked and not unsafe_assessment.admissible
        projection = stable_digest(
            [
                {
                    "candidate_id": item.candidate_id,
                    "admissible": item.admissible,
                    "blockers": list(item.blockers),
                    "balanced_score": item.balanced_score,
                    "rank_vector": list(item.rank_vector),
                }
                for item in evaluation.assessments
            ]
        )
        if not canonical_assessment_projection:
            canonical_assessment_projection = projection
        elif projection != canonical_assessment_projection:
            raise AssertionError("candidate permutation changed assessment projection")

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    final = evaluate_construction_candidates(
        fixture.state,
        candidates=fixture.candidates,
        now=30.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=signals,
    )
    report = ConstructionBenchmarkReport(
        iterations=iterations,
        stable_evaluation_digest=next(iter(digests)),
        unique_evaluation_digests=len(digests),
        unique_recommendations=len(recommendations),
        recommended_candidate_id=next(iter(recommendations)),
        blocked_candidate_count=sum(
            1 for item in final.assessments if not item.admissible
        ),
        admissible_candidate_count=sum(
            1 for item in final.assessments if item.admissible
        ),
        displayed_option_count=len(final.option_candidate_ids),
        unsafe_high_score_candidate_blocked=unsafe_blocked,
        candidate_order_invariant=len(digests) == 1 and len(recommendations) == 1,
        elapsed_ms=float(elapsed_ms),
    )
    return {
        "ok": True,
        "version": CONSTRUCTION_BENCHMARK_VERSION,
        "report": report.to_dict(),
        "benchmark_arms": {
            "ZERO_MODEL": {
                "status": "MEASURED",
                "measurement_class": "EXECUTABLE_SYNTHETIC_FIXTURE",
                "iterations": iterations,
                "stable": True,
            },
            "BROAD_IMPLEMENTER": {"status": "NOT_MEASURED"},
            "SLICED_SURGEON": {"status": "NOT_MEASURED"},
            "SELECTIVE_COUNCIL_V3_PLUS_SURGEON": {"status": "NOT_MEASURED"},
        },
        "claim_boundaries": {
            "synthetic_fixture_only": True,
            "provider_tokens_and_cost": "NOT_MEASURED",
            "real_project_savings": "NOT_MEASURED",
            "production_readiness": "NOT_CLAIMED",
            "physical_work_authorized": False,
            "payment_released": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the SCO Construction Phase 3 zero-model benchmark."
    )
    parser.add_argument("--iterations", type=int, default=250)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_construction_phase3_benchmark(
        iterations=args.iterations,
        seed=args.seed,
    )
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        report = result["report"]
        print(
            "SCO Construction Phase 3 benchmark: "
            f"{report['iterations']} iterations, "
            f"{report['unique_evaluation_digests']} digest, "
            f"{report['blocked_candidate_count']} blocked, "
            f"{report['admissible_candidate_count']} admissible"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
