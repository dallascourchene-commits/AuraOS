"""Length-aware Architect Council for multi-step refactor planning.

V1 proved slice efficiency but exposed two planning defects: normalization dropped
plan-level governance fields, and candidate scoring treated more tasks as an
unqualified benefit.  V2 preserves the complete plan contract, profiles refactor
length/dependencies, and adds sequence, continuity, and rollback critics for long
plans.  It remains planning-only and grants no patch authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from aura_live_architect import (
    ArchitectCouncilDecision,
    ArchitectFusionCouncil,
    ArchitectModelRouter,
    _attach_grounding_to_plan,
)

ARCHITECT_COUNCIL_V2 = "AURA_ARCHITECT_COUNCIL_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item) for item in value if str(item).strip()]


def _task_dependencies(task: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("depends_on", "after", "prerequisites", "dependency_tasks"):
        for item in _string_list(task.get(key)):
            if item not in values:
                values.append(item)
    return values


@dataclass(frozen=True)
class RefactorLengthProfile:
    task_count: int
    distinct_file_count: int
    dependency_edge_count: int
    sequential_depth_estimate: int
    large_task_count: int
    estimated_min_model_turns: int
    estimated_max_model_turns: int
    length_class: str
    council_recommended: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


def profile_refactor_length(plan: dict[str, Any]) -> RefactorLengthProfile:
    tasks = [dict(item) for item in list(plan.get("act_tasks", []) or []) if isinstance(item, dict)]
    task_ids = [str(item.get("task_id") or f"A{index + 1}") for index, item in enumerate(tasks)]
    files: set[str] = set()
    dependency_edges = 0
    large_tasks = 0
    depth_by_task: dict[str, int] = {}
    for index, task in enumerate(tasks):
        for path in [task.get("target_file"), *list(task.get("related_files", []) or [])]:
            if path:
                files.add(str(path))
        size = str(task.get("size") or "S").upper()
        if size in {"L", "XL"}:
            large_tasks += 1
        dependencies = _task_dependencies(task)
        dependency_edges += len(dependencies)
        depth_by_task[task_ids[index]] = 1 + max(
            (depth_by_task.get(dep, 0) for dep in dependencies),
            default=0,
        )
    depth = max(depth_by_task.values(), default=(1 if tasks else 0))
    if len(tasks) <= 2 and len(files) <= 2 and dependency_edges == 0:
        length_class = "SHORT"
    elif len(tasks) <= 5 and len(files) <= 6 and depth <= 3:
        length_class = "MEDIUM"
    elif len(tasks) <= 12 and depth <= 8:
        length_class = "LONG"
    else:
        length_class = "PROGRAM"
    reasons: list[str] = []
    if len(tasks) >= 4:
        reasons.append("multiple_act_capsules")
    if dependency_edges:
        reasons.append("explicit_task_dependencies")
    if depth >= 3:
        reasons.append("sequential_dependency_depth")
    if large_tasks:
        reasons.append("large_or_xl_capsules")
    council_recommended = length_class in {"LONG", "PROGRAM"} or dependency_edges >= 2 or large_tasks >= 2
    return RefactorLengthProfile(
        task_count=len(tasks),
        distinct_file_count=len(files),
        dependency_edge_count=dependency_edges,
        sequential_depth_estimate=depth,
        large_task_count=large_tasks,
        estimated_min_model_turns=len(tasks),
        estimated_max_model_turns=len(tasks) * 3,
        length_class=length_class,
        council_recommended=council_recommended,
        reasons=tuple(reasons),
    )


class LengthAwareArchitectFusionCouncil(ArchitectFusionCouncil):
    """Preserve governance fields and judge plans relative to their length."""

    def _normalize_plan_spec(
        self,
        data: dict[str, Any],
        *,
        intent: str,
        inferred_file: str | None,
        target_symbol: str | None,
        topological_grounding: dict[str, Any] | None = None,
        source: str,
    ) -> dict[str, Any] | None:
        tasks = data.get("act_tasks") if isinstance(data.get("act_tasks"), list) else []
        if not tasks:
            return None
        plan = {
            "architecture_decision": str(data.get("architecture_decision") or "Use the live Architect loop."),
            "target_file": (
                str(data.get("target_file") or inferred_file)
                if data.get("target_file") or inferred_file
                else None
            ),
            "target_symbol": (
                str(data.get("target_symbol") or target_symbol)
                if data.get("target_symbol") or target_symbol
                else None
            ),
            "act_tasks": tasks,
            "acceptance_criteria": _string_list(data.get("acceptance_criteria")),
            "rollback_conditions": _string_list(data.get("rollback_conditions")),
            "risk_map": _string_list(data.get("risk_map")),
            "constraints": _string_list(data.get("constraints")),
            "escalation_rules": _string_list(data.get("escalation_rules")),
            "source": source,
            "ledger_hints": self.router.ledger_hints(),
            "objective": intent,
            "council_version": ARCHITECT_COUNCIL_V2,
        }
        plan["length_profile"] = profile_refactor_length(plan).to_dict()
        return _attach_grounding_to_plan(plan, topological_grounding or {})

    def _candidate(
        self,
        candidate_id: str,
        plan: dict[str, Any],
        *,
        cost_tier: str,
        source: str,
    ) -> dict[str, Any]:
        candidate = super()._candidate(candidate_id, plan, cost_tier=cost_tier, source=source)
        profile = profile_refactor_length(plan)
        contract_fields = (
            "acceptance_criteria",
            "rollback_conditions",
            "risk_map",
            "constraints",
        )
        completeness = sum(bool(plan.get(field)) for field in contract_fields) / len(contract_fields)
        score = float(candidate.get("score", 0.0))
        score += completeness * 0.10
        if profile.length_class in {"LONG", "PROGRAM"} and completeness < 0.75:
            score -= 0.16
        if profile.dependency_edge_count and profile.sequential_depth_estimate <= 1:
            score -= 0.08
        candidate["score"] = round(max(0.0, min(1.0, score)), 4)
        candidate["length_profile"] = profile.to_dict()
        candidate["plan_contract_completeness"] = round(completeness, 4)
        return candidate

    async def _run_shadow_critics(
        self,
        candidates: list[dict[str, Any]],
        budget_route: dict[str, Any],
    ) -> list[dict[str, Any]]:
        reports = await super()._run_shadow_critics(candidates, budget_route)
        for candidate in candidates:
            profile = dict(candidate.get("length_profile") or {})
            if profile.get("length_class") not in {"LONG", "PROGRAM"}:
                continue
            for critic_id in ("sequence", "continuity", "rollback"):
                prompt = (
                    "You are an Aura long-refactor Shadow critic. Return JSON only with "
                    "approved, score, blockers, rationale. Check the named lane against task "
                    "dependencies, bounded checkpoints, rollback, and context continuity. "
                    f"Critic lane: {critic_id}. Length profile: {json.dumps(profile, sort_keys=True)}. "
                    f"Candidate: {json.dumps(candidate['plan'], sort_keys=True)}"
                )
                response = await self.router.call_model(
                    "shadow",
                    prompt,
                    intensity=1,
                    meta={
                        "candidate_id": candidate["candidate_id"],
                        "critic_id": critic_id,
                        "council_phase": "long_refactor_shadow",
                        "length_class": profile.get("length_class"),
                    },
                )
                report = self._parse_critic_report(response, candidate, critic_id)
                candidate.setdefault("critic_reports", []).append(report)
                reports.append(report)
            candidate_reports = list(candidate.get("critic_reports") or [])
            if candidate_reports:
                average = sum(float(item.get("score", 0.0)) for item in candidate_reports) / len(candidate_reports)
                blockers = sum(1 for item in candidate_reports if item.get("blockers"))
                candidate["score"] = round(
                    max(0.0, min(1.0, (float(candidate.get("score", 0.0)) + average) / 2 - blockers * 0.10)),
                    4,
                )
        return reports


class LengthAwareArchitectModelRouter(ArchitectModelRouter):
    """Route planning through the V2 Council while retaining V1 model profiles."""

    async def plan_with_council(
        self,
        intent: str,
        *,
        target_file: str | None = None,
        target_symbol: str | None = None,
    ) -> ArchitectCouncilDecision:
        council = LengthAwareArchitectFusionCouncil(self)
        return await council.select_plan(
            intent,
            target_file=target_file,
            target_symbol=target_symbol,
        )


__all__ = [
    "ARCHITECT_COUNCIL_V2",
    "LengthAwareArchitectFusionCouncil",
    "LengthAwareArchitectModelRouter",
    "RefactorLengthProfile",
    "profile_refactor_length",
]
