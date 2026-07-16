"""Selective-critic Architect Council for long refactors.

V2 preserved the complete plan contract and added long-horizon critics, but called
all available critic lanes uniformly. V3 routes critic lanes from measurable plan
structure and risk evidence so strategic review is retained without paying every
critic tax on every candidate.

V3 remains planning-only. It grants no patch, commit, merge, or promotion authority.
"""
from __future__ import annotations

import json
from typing import Any

from aura_architect_council_v2 import (
    LengthAwareArchitectFusionCouncil,
    RefactorLengthProfile,
    profile_refactor_length,
)
from aura_live_architect import ArchitectCouncilDecision, ArchitectModelRouter

ARCHITECT_COUNCIL_V3 = "AURA_ARCHITECT_COUNCIL_V3_SELECTIVE_CRITICS"


def select_critic_lanes(candidate: dict[str, Any]) -> list[str]:
    """Select only critic lanes justified by plan length, dependencies, and risk."""
    plan = dict(candidate.get("plan") or {})
    profile = profile_refactor_length(plan)
    lanes = ["scope", "tests"]

    if profile.dependency_edge_count > 0 or profile.sequential_depth_estimate >= 3:
        lanes.append("sequence")
    if profile.task_count >= 8 or profile.sequential_depth_estimate >= 5:
        lanes.append("continuity")
    if (
        profile.task_count >= 4
        or bool(plan.get("rollback_conditions"))
        or bool(plan.get("risk_map"))
    ):
        lanes.append("rollback")
    if (
        profile.large_task_count >= 2
        or profile.estimated_max_model_turns >= 30
        or profile.length_class == "PROGRAM"
    ):
        lanes.append("cost")

    ordered: list[str] = []
    for lane in lanes:
        if lane not in ordered:
            ordered.append(lane)
    return ordered


class SelectiveArchitectFusionCouncil(LengthAwareArchitectFusionCouncil):
    """Run one evidence-routed critic pass per candidate."""

    async def _run_shadow_critics(
        self,
        candidates: list[dict[str, Any]],
        budget_route: dict[str, Any],
    ) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for candidate in candidates:
            profile = profile_refactor_length(dict(candidate.get("plan") or {}))
            lanes = select_critic_lanes(candidate)
            candidate["critic_route"] = {
                "council_version": ARCHITECT_COUNCIL_V3,
                "selected_lanes": lanes,
                "skipped_lanes": [
                    lane
                    for lane in ("scope", "tests", "cost", "sequence", "continuity", "rollback")
                    if lane not in lanes
                ],
                "length_profile": profile.to_dict(),
                "selection_reasons": _selection_reasons(profile, candidate),
            }
            candidate_reports: list[dict[str, Any]] = []
            for critic_id in lanes:
                prompt = _critic_prompt(critic_id, candidate, profile)
                response = await self.router.call_model(
                    "shadow",
                    prompt,
                    intensity=1 if critic_id in {"sequence", "continuity", "rollback"} else 0,
                    meta={
                        "candidate_id": candidate["candidate_id"],
                        "critic_id": critic_id,
                        "council_phase": "selective_plan_shadow",
                        "length_class": profile.length_class,
                        "selected_critic_count": len(lanes),
                    },
                )
                report = self._parse_critic_report(response, candidate, critic_id)
                report["routing"] = "SELECTED_BY_PLAN_PROFILE"
                candidate_reports.append(report)
                reports.append(report)
            candidate["critic_reports"] = candidate_reports
            if candidate_reports:
                average = sum(float(item.get("score", 0.0)) for item in candidate_reports) / len(candidate_reports)
                blockers = sum(1 for item in candidate_reports if item.get("blockers"))
                candidate["score"] = round(
                    max(
                        0.0,
                        min(
                            1.0,
                            (float(candidate.get("score", 0.0)) + average) / 2
                            - blockers * 0.12,
                        ),
                    ),
                    4,
                )
        return reports

    def _normalize_plan_spec(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        plan = super()._normalize_plan_spec(*args, **kwargs)
        if plan is not None:
            plan["council_version"] = ARCHITECT_COUNCIL_V3
        return plan


class SelectiveArchitectModelRouter(ArchitectModelRouter):
    """Route planning through selective Council V3."""

    async def plan_with_council(
        self,
        intent: str,
        *,
        target_file: str | None = None,
        target_symbol: str | None = None,
    ) -> ArchitectCouncilDecision:
        council = SelectiveArchitectFusionCouncil(self)
        return await council.select_plan(
            intent,
            target_file=target_file,
            target_symbol=target_symbol,
        )


def _selection_reasons(
    profile: RefactorLengthProfile,
    candidate: dict[str, Any],
) -> list[str]:
    plan = dict(candidate.get("plan") or {})
    reasons = ["scope_and_tests_are_universal"]
    if profile.dependency_edge_count > 0 or profile.sequential_depth_estimate >= 3:
        reasons.append("dependency_or_sequence_evidence")
    if profile.task_count >= 8 or profile.sequential_depth_estimate >= 5:
        reasons.append("long_horizon_continuity")
    if profile.task_count >= 4 or plan.get("rollback_conditions") or plan.get("risk_map"):
        reasons.append("rollback_or_risk_evidence")
    if profile.large_task_count >= 2 or profile.estimated_max_model_turns >= 30 or profile.length_class == "PROGRAM":
        reasons.append("cost_pressure")
    return reasons


def _critic_prompt(
    critic_id: str,
    candidate: dict[str, Any],
    profile: RefactorLengthProfile,
) -> str:
    if critic_id in {"sequence", "continuity", "rollback"}:
        return (
            "You are an Aura long-refactor Shadow critic. Return JSON only with "
            "approved, score, blockers, rationale. Check only the named lane against "
            "task dependencies, bounded checkpoints, rollback, and context continuity. "
            f"Critic lane: {critic_id}. Length profile: "
            f"{json.dumps(profile.to_dict(), sort_keys=True)}. Candidate: "
            f"{json.dumps(candidate['plan'], sort_keys=True)}"
        )
    return (
        "You are an Aura cheap Shadow critic. Return JSON only with approved, score, "
        "blockers, rationale. Check only the named lane. "
        f"Critic lane: {critic_id}. Candidate: "
        f"{json.dumps(candidate['plan'], sort_keys=True)}"
    )


__all__ = [
    "ARCHITECT_COUNCIL_V3",
    "SelectiveArchitectFusionCouncil",
    "SelectiveArchitectModelRouter",
    "select_critic_lanes",
]
