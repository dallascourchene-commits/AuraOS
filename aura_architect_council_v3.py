"""Selective-critic Architect Council for long refactors.

V2 preserved the complete plan contract and added long-horizon critics, but called
all available critic lanes uniformly. V3 routes critic lanes from measurable plan
structure and risk evidence so strategic review is retained without paying every
critic tax on every candidate.

V3 remains planning-only. It grants no patch, commit, merge, or promotion authority.
"""

from __future__ import annotations

import inspect
import json
import os
from typing import Any

from aura_architect_council_v2 import (
    LengthAwareArchitectFusionCouncil,
    RefactorLengthProfile,
    profile_refactor_length,
)
from aura_live_architect import ArchitectCouncilDecision, ArchitectModelRouter

ARCHITECT_COUNCIL_V3 = "AURA_ARCHITECT_COUNCIL_V3_SELECTIVE_CRITICS"


def _verification_depth(value: Any) -> int:
    try:
        depth = int(value if value is not None else 1)
    except (TypeError, ValueError):
        return 1
    return max(1, depth)


def select_critic_lanes(candidate: dict[str, Any]) -> list[str]:
    """Select only critic lanes justified by plan length, dependencies, and risk."""
    plan = dict(candidate.get("plan") or {})
    profile = profile_refactor_length(plan)
    lanes = ["scope", "tests"]
    if plan.get("bilateral_contract") or plan.get("confirmation_digest"):
        lanes.extend(["continuity", "rollback"])
    unified = candidate.get("unified_memory_continuity") or plan.get("unified_memory_continuity") or {}
    if not isinstance(unified, dict):
        unified = {}
    disagreement_refs = list(unified.get("disagreement_refs") or [])
    verification_depth = _verification_depth(unified.get("required_verification_depth"))
    continuity_requirements = list(unified.get("continuity_requirements") or [])
    if disagreement_refs or verification_depth > 1:
        lanes.append("continuity")
    if unified.get("p0_required") is True or continuity_requirements:
        lanes.append("rollback")

    if profile.dependency_edge_count > 0 or profile.sequential_depth_estimate >= 3:
        lanes.append("sequence")
    if profile.task_count >= 8 or profile.sequential_depth_estimate >= 5:
        lanes.append("continuity")
    if profile.task_count >= 4 or bool(plan.get("rollback_conditions")) or bool(plan.get("risk_map")):
        lanes.append("rollback")
    if profile.large_task_count >= 2 or profile.estimated_max_model_turns >= 30 or profile.length_class == "PROGRAM":
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
                            (float(candidate.get("score", 0.0)) + average) / 2 - blockers * 0.12,
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
    """Route Council V3 through the canonical DeepSeek-first egress."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        defaults = {
            "planner": ("AURA_ARCHITECT_PLANNER_PROVIDER", "DEEPSEEK"),
            "planner_alt": ("AURA_ARCHITECT_ALT_PLANNER_PROVIDER", "MISTRAL"),
            "worker": ("AURA_ARCHITECT_WORKER_PROVIDER", "MISTRAL"),
            "shadow": ("AURA_ARCHITECT_SHADOW_PROVIDER", "MISTRAL"),
            "judge": ("AURA_ARCHITECT_JUDGE_PROVIDER", "DEEPSEEK"),
        }
        for role, (env_name, fallback) in defaults.items():
            if role in self.profiles:
                self.profiles[role].provider = os.getenv(env_name, fallback)

    async def call_model(
        self,
        role: str,
        prompt: str,
        *,
        intensity: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> str | None:
        profile = self.profile_for(role, intensity=intensity)
        callback = self.model_caller
        is_legacy_node_callback = bool(
            callback is not None
            and getattr(callback, "__module__", "") == "aura_node"
            and getattr(callback, "__name__", "") == "call_architect_model"
        )
        if callback is None or is_legacy_node_callback:
            from aura_llm_egress import generate_architect_model

            return generate_architect_model(
                profile.provider,
                prompt,
                {"role": role, "profile": profile.to_dict(), **(meta or {})},
            )
        result = callback(
            profile.provider,
            prompt,
            {"role": role, "profile": profile.to_dict(), **(meta or {})},
        )
        if inspect.isawaitable(result):
            result = await result
        return str(result) if result is not None else None

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
    if plan.get("bilateral_contract") or plan.get("confirmation_digest"):
        reasons.append("bilateral_intent_requires_continuity_and_rollback_review")
    unified = candidate.get("unified_memory_continuity") or plan.get("unified_memory_continuity") or {}
    if isinstance(unified, dict):
        if (
            list(unified.get("disagreement_refs") or [])
            or _verification_depth(unified.get("required_verification_depth")) > 1
        ):
            reasons.append("cross_model_disagreement_requires_deeper_verification")
        if unified.get("p0_required") is True or list(unified.get("continuity_requirements") or []):
            reasons.append("prediction_and_continuity_require_rollback_review")
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
    "route_compass_failure_classes",
]


def route_compass_failure_classes(failure_classes: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Route failures without allowing Council to override bilateral denials."""
    normalized = list(dict.fromkeys(str(item).strip().upper() for item in failure_classes if str(item).strip()))
    local = {
        "LOCAL_ASSERTION",
        "LOCAL_TEST",
        "LOCAL_NEGATIVE_TEST",
        "EXACT_SPAN_PATCH",
        "SOURCE_ASSERTION",
    }
    human = {
        "SEMANTIC_AMBIGUITY",
        "CONFIRMATION_STALE",
        "AUTHORITY_DENIAL",
        "GUARDRAIL_CONFLICT",
    }
    structural = {
        "INTERFACE",
        "DEPENDENCY",
        "INVARIANT",
        "SCOPE",
        "AUTHORITY",
        "PROHIBITION",
        "SEQUENCE",
        "INTENT_FIDELITY",
        "NEGATIVE_REQUIREMENT",
        "PLAN_ASSUMPTION_INVALIDATED",
    }
    if any(item in human for item in normalized):
        return {
            "route": "HUMAN_RECONFIRMATION_REQUIRED",
            "critic_lanes": [],
            "reason": "deterministic_bilateral_denial",
            "failure_classes": normalized,
            "deterministic_denial": True,
            "council_override_allowed": False,
            "proposal_only": True,
        }
    if normalized and set(normalized).issubset(local):
        return {
            "route": "SURGEON",
            "critic_lanes": ["tests", "scope"],
            "reason": "local_assertion_failure",
            "failure_classes": normalized,
            "deterministic_denial": False,
            "council_override_allowed": False,
            "proposal_only": True,
        }
    lanes = ["scope", "tests"]
    if any(item in structural for item in normalized):
        lanes.extend(["sequence", "rollback"])
    if "INVARIANT" in normalized or "SCOPE" in normalized:
        lanes.append("continuity")
    return {
        "route": "COUNCIL_V3",
        "critic_lanes": list(dict.fromkeys(lanes)),
        "reason": "structural_or_cross_boundary_failure" if normalized else "preflight_review",
        "failure_classes": normalized,
        "deterministic_denial": False,
        "council_override_allowed": True,
        "proposal_only": True,
    }
