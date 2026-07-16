"""Shared proposal-only Architect connector for Aura's Arena surfaces."""
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

ARENA_ARCHITECT_CONNECTOR_VERSION = "AURA_ARENA_ARCHITECT_CONNECTOR_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
MAX_CANDIDATES = 8
MAX_TASKS = 64
MAX_PLAN_BYTES = 262_144
_REQUIRED = ("architecture_decision", "act_tasks", "acceptance_criteria", "rollback_conditions", "risk_map", "constraints")


def _digest(value: Any, *, size: int = 16) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=size).hexdigest()


def _tokens(value: Any) -> int:
    return (len(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")) + 3) // 4


def _candidate(candidate: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    candidate_id = str(candidate.get("candidate_id") or candidate.get("plan_id") or "candidate")
    plan = dict(candidate.get("plan") or candidate)
    if len(json.dumps(plan, default=str).encode("utf-8")) > MAX_PLAN_BYTES:
        raise ValueError("candidate plan exceeds the bounded plan size")
    if len(list(plan.get("act_tasks") or [])) > MAX_TASKS:
        raise ValueError(f"candidate plan exceeds {MAX_TASKS} Act Capsules")
    return candidate_id, plan


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
        value = asdict(self)
        value["selected_critic_lanes"] = list(self.selected_critic_lanes)
        value["reasons"] = list(self.reasons)
        return value


class AuraArenaArchitectConnector:
    """One bounded service for Coding, Human, MCP, HTTP, and container clients."""

    def __init__(self, repo_root: str | Path = ".", *, bridge: Any | None = None, bridge_factory: Callable[..., Any] | None = None, model_gateway: AuraNativeModelGateway | None = None, record_path: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._bridge = bridge
        self._bridge_factory = bridge_factory
        self.model_gateway = model_gateway or AuraNativeModelGateway(self.repo_root)
        self.record_path = Path(record_path) if record_path else self.repo_root / "Aura_Memory" / "benchmarks" / "architect_plan_selections.jsonl"

    @property
    def bridge(self) -> Any:
        if self._bridge is None:
            factory = self._bridge_factory
            if factory is None:
                from aura_agent_arena_bridge import AuraAgentArenaBridge
                factory = AuraAgentArenaBridge
            self._bridge = factory(repo_root=self.repo_root)
        return self._bridge

    def assess_plan(self, candidate: Mapping[str, Any], *, required_capabilities: Sequence[str] = ()) -> PlanAssessment:
        candidate_id, plan = _candidate(candidate)
        tasks = [dict(item) for item in list(plan.get("act_tasks") or [])]
        profile = profile_refactor_length(plan)
        lanes = tuple(select_critic_lanes({"candidate_id": candidate_id, "plan": plan}))
        required = {str(item) for item in required_capabilities if str(item)}
        covered = {str(item) for item in list(plan.get("coverage_tags") or []) if str(item)}
        coverage = 1.0 if not required else len(required & covered) / len(required)
        exact = sum(bool(str(task.get("task_id") or "").strip() and str(task.get("target_file") or "").strip() and str(task.get("target_symbol") or "").strip() and str(task.get("acceptance") or "").strip() and str(task.get("expected_output") or "").upper() == "UNIFIED_DIFF") for task in tasks) / max(1, len(tasks))
        governance = sum(bool(plan.get(field)) for field in _REQUIRED) / len(_REQUIRED)
        testability = min(1.0, (len(list(plan.get("acceptance_criteria") or [])) + sum(bool(task.get("tests") or task.get("acceptance")) for task in tasks)) / max(1, len(tasks) + 1))
        reuse = bool(plan.get("architecture_reuse") or plan.get("existing_modules"))
        reasons: list[str] = []
        if coverage == 1.0:
            reasons.append("covers_all_required_capabilities")
        if exact == 1.0:
            reasons.append("all_act_capsules_are_exact")
        if governance == 1.0:
            reasons.append("complete_governance_contract")
        if reuse:
            reasons.append("reuses_existing_aura_architecture")
        if "tests" in lanes:
            reasons.append("selective_council_test_review")
        if "sequence" in lanes or "continuity" in lanes:
            reasons.append("long_horizon_dependencies_reviewed")
        score = coverage * .34 + exact * .20 + governance * .16 + testability * .14 + (.10 if reuse else 0) + min(.06, len(lanes) * .01)
        if not tasks:
            score = 0.0
            reasons.append("no_act_capsules")
        return PlanAssessment(candidate_id, round(min(1.0, score), 4), lanes, profile.to_dict(), round(coverage, 4), round(exact, 4), round(governance, 4), round(testability, 4), reuse, tuple(reasons), _digest(plan), _tokens(plan))

    def compare_plans(self, *, objective: str, candidates: Sequence[Mapping[str, Any]], required_capabilities: Sequence[str] = (), record: bool = True) -> dict[str, Any]:
        objective = str(objective or "").strip()
        if not objective:
            raise ValueError("objective is required")
        if not candidates:
            raise ValueError("at least one candidate plan is required")
        if len(candidates) > MAX_CANDIDATES:
            raise ValueError(f"at most {MAX_CANDIDATES} candidate plans are allowed")
        ids = [str(item.get("candidate_id") or item.get("plan_id") or "candidate") for item in candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate ids must be unique")
        assessments = [self.assess_plan(item, required_capabilities=required_capabilities) for item in candidates]
        assessments.sort(key=lambda item: (-item.score, item.token_proxy, item.candidate_id))
        selected = assessments[0]
        selected_plan = next(dict(item.get("plan") or item) for item in candidates if str(item.get("candidate_id") or item.get("plan_id") or "candidate") == selected.candidate_id)
        profile = selected.length_profile
        route = route_initial_refactor(objective=objective, task_count=int(profile.get("task_count") or 0), distinct_file_count=int(profile.get("distinct_file_count") or 0), dependency_edge_count=int(profile.get("dependency_edge_count") or 0), sequential_depth=int(profile.get("sequential_depth_estimate") or 0), cross_domain_count=len(set(selected_plan.get("domains") or [])), large_task_count=int(profile.get("large_task_count") or 0))
        result = {"ok": True, "version": ARENA_ARCHITECT_CONNECTOR_VERSION, "objective": objective, "required_capabilities": list(required_capabilities), "selected_candidate_id": selected.candidate_id, "selected_plan": selected_plan, "selected_assessment": selected.to_dict(), "assessments": [item.to_dict() for item in assessments], "cognitive_labor_route": route.to_dict(), "selection_digest": _digest({"objective": objective, "selected": selected.to_dict(), "candidates": [item.to_dict() for item in assessments]}), "selection_method": "DETERMINISTIC_COUNCIL_V3_PROFILE_RUBRIC", "proposal_only": True, "production_mutation": False, "human_review_required": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        if record:
            self._record("architect_plan_selected", result)
        return result

    def prepare_refactor(self, *, objective: str, candidates: Sequence[Mapping[str, Any]], required_capabilities: Sequence[str] = (), target_file: str | None = None, target_symbol: str | None = None) -> dict[str, Any]:
        comparison = self.compare_plans(objective=objective, candidates=candidates, required_capabilities=required_capabilities)
        selected = dict(comparison["selected_plan"])
        prepared = self.bridge.aura_prepare_arena(objective=objective, target_file=target_file or selected.get("target_file"), target_symbol=target_symbol or selected.get("target_symbol"), acceptance_criteria=list(selected.get("acceptance_criteria") or []), risk_map=list(selected.get("risk_map") or []), constraints=list(selected.get("constraints") or []))
        result = {"ok": bool(prepared.get("ok", True)), "comparison": comparison, "arena_preparation": prepared, "proposal_only": True, "human_review_required": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        self._record("architect_arena_prepared", result)
        return result

    def route_native_model(self, **kwargs: Any) -> dict[str, Any]:
        return self.model_gateway.plan_best(**kwargs)

    def execute_native_model(self, **kwargs: Any) -> dict[str, Any]:
        return self.model_gateway.execute_best(**kwargs)

    def _record(self, event_type: str, payload: Mapping[str, Any]) -> None:
        public = {"version": payload.get("version"), "selected_candidate_id": payload.get("selected_candidate_id") or dict(payload.get("comparison") or {}).get("selected_candidate_id"), "selected_assessment": payload.get("selected_assessment") or dict(payload.get("comparison") or {}).get("selected_assessment"), "selection_digest": payload.get("selection_digest") or dict(payload.get("comparison") or {}).get("selection_digest"), "proposal_only": True, "human_review_required": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        row = {"event_type": event_type, "recorded_at": time.time(), "payload_digest": _digest(public), "payload": public, "redaction": "FULL_PLANS_AUTHORIZATIONS_AND_PRIVATE_EVIDENCE_OMITTED"}
        try:
            self.record_path.parent.mkdir(parents=True, exist_ok=True)
            with self.record_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        except OSError:
            return


__all__ = ["ARENA_ARCHITECT_CONNECTOR_VERSION", "AuraArenaArchitectConnector", "PlanAssessment"]
