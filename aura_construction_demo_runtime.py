"""Canonical proposal-only runtime composition for the G4 Construction fixture."""
from __future__ import annotations

from typing import Any

from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaAdapter,
    ConstructionArenaMode,
    ConstructionCoordinationCandidate,
    ConstructionCriterionScore,
    ConstructionProbabilisticSignal,
)
from aura_construction_demo_fixture import ConstructionDemoProjectFixture


def _signal(candidate: ConstructionCoordinationCandidate) -> ConstructionProbabilisticSignal:
    """Build a deterministic, non-authoritative signal from declared candidate fields."""
    if type(candidate) is not ConstructionCoordinationCandidate:
        raise ValueError("candidate must be an exact ConstructionCoordinationCandidate")
    criteria = (
        ConstructionCriterionScore.create(
            criterion="evidence quality",
            expected_score=float(candidate.evidence_quality),
            variance=0.01,
            repetitions=4,
        ),
        ConstructionCriterionScore.create(
            criterion="safety fit",
            expected_score=float(1.0 - candidate.safety_risk),
            variance=0.01,
            repetitions=4,
        ),
        ConstructionCriterionScore.create(
            criterion="schedule fit",
            expected_score=float(1.0 - candidate.deadline_risk),
            variance=0.01,
            repetitions=4,
        ),
        ConstructionCriterionScore.create(
            criterion="reversibility",
            expected_score=float(candidate.reversibility),
            variance=0.01,
            repetitions=4,
        ),
    )
    aggregate = sum(item.expected_score for item in criteria) / len(criteria)
    return ConstructionProbabilisticSignal.create(
        candidate_id=candidate.candidate_id,
        criteria=criteria,
        score_margin=0.05,
        progress_score=float(aggregate),
        progress_slope=0.0,
        distance_from_peak=float(1.0 - aggregate),
    )


def build_construction_demo_runtime_packet(
    fixture: ConstructionDemoProjectFixture,
    *,
    now: float = 30.0,
) -> dict[str, Any]:
    """Compose Aura's canonical adapter packet without adding runtime authority."""
    if type(fixture) is not ConstructionDemoProjectFixture:
        raise ValueError("fixture must be an exact ConstructionDemoProjectFixture")
    fixture.__post_init__()
    blocked = next(
        (
            package
            for package in fixture.work_packages
            if package.package_id == fixture.blocked_package_id
        ),
        None,
    )
    if blocked is None:
        raise ValueError("fixture blocked package is unavailable")
    signals = tuple(
        sorted((_signal(candidate) for candidate in fixture.candidates), key=lambda item: item.candidate_id)
    )
    packet = ConstructionArenaAdapter().build_runtime_packet(
        objective=(
            "Protect the synthetic project schedule without crossing asbestos evidence, "
            "professional review, payment, access, or physical-work authority boundaries."
        ),
        state=fixture.state,
        scope=blocked.scope,
        candidates=fixture.candidates,
        now=now,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=signals,
    )
    for key, expected in {
        "ok": True,
        "source_records_mutated": False,
        "proposal_only": True,
        "human_release_required": True,
        "physical_work_authorized": False,
        "payment_released": False,
        "access_controlled": False,
        "vsa_patch_authority": False,
    }.items():
        if packet.get(key) is not expected:
            raise ValueError(f"Construction runtime packet crossed boundary: {key}")
    if packet.get("state_digest") != fixture.state.state_digest:
        raise ValueError("Construction runtime packet is stale for the fixture state")
    evaluation = packet.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError("Construction runtime packet lacks an evaluation")
    if not evaluation.get("recommended_candidate_id"):
        raise ValueError("Construction runtime packet did not produce a review candidate")
    if evaluation.get("recommended_candidate_id") not in {
        candidate.candidate_id for candidate in fixture.candidates
    }:
        raise ValueError("Construction runtime packet recommended an unknown candidate")
    return packet


__all__ = ["build_construction_demo_runtime_packet"]
