"""Shared Architect/Council connector for Aura's Coding and Human Agent Arenas.

The connector exposes the same bounded architecture through Python, MCP, HTTP,
and container surfaces. It compares multiple plans with Council V3's selective
critic routing, prepares the selected plan through the Agent Arena bridge, and
routes native model work through the Model Cognome instead of a hard-coded API.

This module is proposal-only. It never commits, merges, promotes, or mutates
production state directly.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

from aura_architect_council_v2 import profile_refactor_length
from aura_architect_council_v3 import select_critic_lanes
from aura_cognitive_labor_router import route_initial_refactor
from aura_native_model_gateway import AuraNativeModelGateway

ARENA_ARCHITECT_CONNECTOR_VERSION = "AURA_ARENA_ARCHITECT_CONNECTOR_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_REQUIRED_PLAN_FIELDS = (
    "architecture_decision",
    "act_tasks",
    "acceptance_criteria",
    "rollback_conditions",
    "risk_map",
    "constraints",
)


def _digest(value: Any, *, size: int = 16) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=size).hexdigest()


def _token_proxy(value: Any) -> int:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return (len(text.encode("utf-8")) + 3) // 4


@dataclass(frozen=True)
class PlanAssessment:
    candidate_id: str
    score: float
    selected_critic_lanes: tuple[str, ...]
    length_profile: dict[str, Any]
    coverage_fraction: float
    exact_task_fraction: float
    governance_fraction: float
    testability_fraction: float
    architecture_reuse: bool
    reasons: tuple[str, ...]
    plan_digest: str
    token_proxy: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["selected_critic_lanes"] = list(self.selected_critic_lanes)
        data["reasons"] = list(self.reasons)
        return data


class AuraArenaArchitectConnector:
    """One shared application service for Coding, Human, MCP, and container clients."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        bridge: Any | None = None,
        bridge_factory: Callable[..., Any] | None = None,
        model_gateway: AuraNativeModelGateway | None = None,
        record_path: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._bridge = bridge
        self._bridge_factory = bridge_factory
        self.model_gateway = model_gateway or AuraNativeModelGateway(self.repo_root)
        self.record_path = Path(record_path) if record_path else (
            self.repo_root / "Aura_Memory" / "benchmarks" / "architect_plan_selections.jsonl"
        )

    @property
    def bridge(self) -> Any:
        if self._bridge is None:
            factory = self._bridge_factory
            if factory is None:
                from aura_agent_arena_bridge import AuraAgentArenaBridge
                factory = AuraAgentArenaBridge
            self._bridge = factory(repo_root=self.repo_root)
        return self._bridge

    @staticmethod
    def _task_exactness(tasks: Sequence[Mapping[str, Any]]) -> float:
        if not tasks:
            return 0.0
        exact = 0
        for task in tasks:
            if (
                str(task.get("task_id") or "").strip()
                and str(task.get("target_file") or "").strip()
                and str(task.get("target_symbol") or "").strip()
                and str(task.get("acceptance") or "").strip()
                and str(task.get("expected_output") or "").upper() == "UNIFIED_DIFF"
            ):
                exact += 1
        return exact / len(tasks)

    @staticmethod
    def _testability(tasks: Sequence[Mapping[str, Any]], plan: Mapping[str, Any]) -> float:
        checks = len(list(plan.get("acceptance_criteria") or []))
        checks += sum(1 for task in tasks if task.get("tests") or task.get("acceptance"))
        denominator = max(1, len(tasks) + 1)
        return min(1.0, checks / denominator)

    def assess_plan(
        self,
        candidate: Mapping[str, Any],
        *,
        required_capabilities: Sequence[str] = (),
    ) -> PlanAssessment:
        candidate_id = str(candidate.get("candidate_id") or candidate.get("plan_id") or "candidate")
        plan = dict(candidate.get("plan") or candidate)
        tasks = [dict(item) for item in list(plan.get("act_tasks") or [])]
        profile = profile_refactor_length(plan)
        lanes = tuple(select_critic_lanes({"candidate_id": candidate_id, "plan": plan}))
        required = {str(item) for item in required_capabilities if str(item)}
        covered = {str(item) for item in list(plan.get("coverage_tags") or []) if str(item)}
        coverage = 1.0 if not required else len(required & covered) / len(required)
        exactness = self._task_exactness(tasks)
        governance = sum(bool(plan.get(field)) for field in _REQUIRED_PLAN_FIELDS) / len(_REQUIRED_PLAN_FIELDS)
        testability = self._testability(tasks, plan)
        reuse = bool(plan.get("architecture_reuse") or plan.get("existing_modules"))
        reasons: list[str] = []
        if coverage == 1.0:
            reasons.append("covers_all_required_capabilities")
        if exactness == 1.0:
            reasons.append("all_act_capsules_are_exact")
        if governance == 1.0:
            reasons.append("complete_governance_contract")
        if reuse:
            reasons.append("reuses_existing_aura_architecture")
        if "tests" in lanes:
            reasons.append("selective_council_test_review")
        if "sequence" in lanes or "continuity" in lanes:
            reasons.append("long_horizon_dependencies_reviewed")
        score = (
            coverage * 0.34
            + exactness * 0.20
            + governance * 0.16
            + testability * 0.14
            + (0.10 if reuse else 0.0)
            + min(0.06, len(lanes) * 0.01)
        )
        if not tasks:
            score = 0.0
            reasons.append("no_act_capsules")
        return PlanAssessment(
            candidate_id=candidate_id,
            score=round(min(1.0, score), 4),
            selected_critic_lanes=lanes,
            length_profile=profile.to_dict(),
            coverage_fraction=round(coverage, 4),
            exact_task_fraction=round(exactness, 4),
            governance_fraction=round(governance, 4),
            testability_fraction=round(testability, 4),
            architecture_reuse=reuse,
            reasons=tuple(reasons),
            plan_digest=_digest(plan),
            token_proxy=_token_proxy(plan),
        )

    def compare_plans(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        record: bool = True,
    ) -> dict[str, Any]:
        objective_text = str(objective or "").strip()
        if not objective_text:
            raise ValueError("objective is required")
        if not candidates:
            raise ValueError("at least one candidate plan is required")
        assessments = [
            self.assess_plan(candidate, required_capabilities=required_capabilities)
            for candidate in candidates
        ]
        assessments.sort(key=lambda item: (-item.score, item.token_proxy, item.candidate_id))
        selected = assessments[0]
        selected_candidate = next(
            dict(item.get("plan") or item)
            for item in candidates
            if str(item.get("candidate_id") or item.get("plan_id") or "candidate") == selected.candidate_id
        )
        profile = selected.length_profile
        initial_route = route_initial_refactor(
            objective=objective_text,
            task_count=int(profile.get("task_count") or 0),
            distinct_file_count=int(profile.get("distinct_file_count") or 0),
            dependency_edge_count=int(profile.get("dependency_edge_count") or 0),
            sequential_depth=int(profile.get("sequential_depth_estimate") or 0),
            cross_domain_count=len(set(selected_candidate.get("domains") or [])),
            large_task_count=int(profile.get("large_task_count") or 0),
        )
        result = {
            "ok": True,
            "version": ARENA_ARCHITECT_CONNECTOR_VERSION,
            "objective": objective_text,
            "required_capabilities": list(required_capabilities),
            "selected_candidate_id": selected.candidate_id,
            "selected_plan": selected_candidate,
            "selected_assessment": selected.to_dict(),
            "assessments": [item.to_dict() for item in assessments],
            "cognitive_labor_route": initial_route.to_dict(),
            "selection_digest": _digest(
                {
                    "objective": objective_text,
                    "selected": selected.to_dict(),
                    "candidates": [item.to_dict() for item in assessments],
                }
            ),
            "proposal_only": True,
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        if record:
            self._record("architect_plan_selected", result)
        return result

    def prepare_refactor(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        target_file: str | None = None,
        target_symbol: str | None = None,
    ) -> dict[str, Any]:
        comparison = self.compare_plans(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
        )
        selected = dict(comparison["selected_plan"])
        prepared = self.bridge.aura_prepare_arena(
            objective=objective,
            target_file=target_file or selected.get("target_file"),
            target_symbol=target_symbol or selected.get("target_symbol"),
            acceptance_criteria=list(selected.get("acceptance_criteria") or []),
            risk_map=list(selected.get("risk_map") or []),
            constraints=list(selected.get("constraints") or []),
        )
        result = {
            "ok": bool(prepared.get("ok", True)),
            "comparison": comparison,
            "arena_preparation": prepared,
            "proposal_only": True,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        self._record("architect_arena_prepared", result)
        return result

    def route_native_model(self, **kwargs: Any) -> dict[str, Any]:
        return self.model_gateway.plan_best(**kwargs)

    def execute_native_model(self, **kwargs: Any) -> dict[str, Any]:
        return self.model_gateway.execute_best(**kwargs)

    def _record(self, event_type: str, payload: Mapping[str, Any]) -> None:
        try:
            self.record_path.parent.mkdir(parents=True, exist_ok=True)
            row = {
                "event_type": event_type,
                "recorded_at": time.time(),
                "payload_digest": _digest(payload),
                "payload": dict(payload),
            }
            with self.record_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        except OSError:
            return


__all__ = [
    "ARENA_ARCHITECT_CONNECTOR_VERSION",
    "AuraArenaArchitectConnector",
    "PlanAssessment",
]
