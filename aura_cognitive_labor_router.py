"""Route refactor cognition between Aura's Council and sliced implementers.

The Council is strategic: cross-domain architecture, dependency sequencing,
trade-offs, invariants, and graph repair. The Surgeon is tactical: exact-file
implementation, compile-ready patches, focused tests, and bounded local repair.

Routing is descriptive and advisory. It never grants patch or promotion authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

COGNITIVE_LABOR_ROUTER_VERSION = "AURA_COGNITIVE_LABOR_ROUTER_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_ARCHITECTURE_TERMS = {
    "architecture",
    "cross-domain",
    "cross domain",
    "dependency graph",
    "interface contract",
    "migration",
    "governance",
    "invariant",
    "rollback graph",
    "compatibility",
    "multi-module",
    "multi module",
}
_GRAPH_FAILURE_TERMS = {
    "dependency",
    "interface",
    "contract",
    "invariant",
    "migration",
    "topology",
    "downstream",
    "rollback graph",
    "plan invalid",
    "sequence invalid",
}
_LOCAL_FAILURE_TERMS = {
    "assertion",
    "syntax",
    "type error",
    "lint",
    "focused test",
    "unit test",
    "single file",
    "single symbol",
}


@dataclass(frozen=True)
class CognitiveLaborDecision:
    route: str
    strategic_role: str
    execution_role: str
    council_runs: int
    local_repair_allowed: bool
    escalation_required: bool
    reasons: tuple[str, ...]
    confidence: float
    version: str = COGNITIVE_LABOR_ROUTER_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False
    production_mutation: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


def _text(value: Any) -> str:
    """Collect human evidence values without treating schema keys as evidence."""
    parts: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, str):
            text = item.strip().lower()
            if text:
                parts.append(text)
            return
        if isinstance(item, dict):
            for child in item.values():
                visit(child)
            return
        if isinstance(item, (list, tuple, set)):
            for child in item:
                visit(child)
            return
        # Booleans and numeric scope fields are evaluated explicitly by route_failure.

    visit(value)
    return " ".join(parts)


def _contains(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def route_initial_refactor(
    *,
    objective: str,
    task_count: int,
    distinct_file_count: int,
    dependency_edge_count: int,
    sequential_depth: int,
    cross_domain_count: int = 0,
    large_task_count: int = 0,
) -> CognitiveLaborDecision:
    text = _text(objective)
    strategic_signals = 0
    reasons: list[str] = []
    if _contains(text, _ARCHITECTURE_TERMS):
        strategic_signals += 2
        reasons.append("architectural_objective")
    if dependency_edge_count >= 2 or sequential_depth >= 3:
        strategic_signals += 2
        reasons.append("dependency_sequence_requires_global_plan")
    if task_count >= 4 or distinct_file_count >= 5:
        strategic_signals += 1
        reasons.append("multi_step_or_multi_file_scope")
    if cross_domain_count >= 2:
        strategic_signals += 2
        reasons.append("cross_domain_tradeoffs")
    if large_task_count >= 2:
        strategic_signals += 1
        reasons.append("multiple_large_capsules")

    if strategic_signals >= 3:
        return CognitiveLaborDecision(
            route="COUNCIL_PLAN_THEN_SURGEON_EXECUTION",
            strategic_role="MULTI_AGENT_COUNCIL",
            execution_role="SINGLE_SLICED_PLANNER",
            council_runs=1,
            local_repair_allowed=True,
            escalation_required=False,
            reasons=tuple(reasons or ["global_plan_required"]),
            confidence=min(0.98, 0.70 + strategic_signals * 0.04),
        )
    return CognitiveLaborDecision(
        route="SURGEON_ONLY",
        strategic_role="NONE",
        execution_role="SINGLE_SLICED_PLANNER",
        council_runs=0,
        local_repair_allowed=True,
        escalation_required=False,
        reasons=tuple(reasons or ["localized_bounded_implementation"]),
        confidence=0.88 if strategic_signals == 0 else 0.78,
    )


def route_failure(
    *,
    failure_packet: dict[str, Any],
    local_repair_attempts: int,
    affected_task_count: int = 1,
    affected_file_count: int = 1,
    downstream_tasks_invalidated: int = 0,
    invariant_breach: bool = False,
    interface_contract_breach: bool = False,
    dependency_graph_breach: bool = False,
    max_local_repairs: int = 2,
) -> CognitiveLaborDecision:
    text = _text(failure_packet)
    graph_signal = (
        invariant_breach
        or interface_contract_breach
        or dependency_graph_breach
        or downstream_tasks_invalidated > 0
        or affected_task_count > 1
        or affected_file_count > 2
        or _contains(text, _GRAPH_FAILURE_TERMS)
    )
    local_signal = (
        affected_task_count <= 1
        and affected_file_count <= 2
        and downstream_tasks_invalidated == 0
        and not invariant_breach
        and not interface_contract_breach
        and not dependency_graph_breach
        and (_contains(text, _LOCAL_FAILURE_TERMS) or not graph_signal)
    )
    reasons: list[str] = []
    if graph_signal:
        reasons.append("failure_invalidates_execution_graph_or_invariants")
    if local_repair_attempts >= max_local_repairs:
        reasons.append("local_repair_budget_exhausted")
    if local_signal:
        reasons.append("failure_is_local_to_leased_capsule")

    escalate = graph_signal or local_repair_attempts >= max_local_repairs
    if escalate:
        return CognitiveLaborDecision(
            route="ESCALATE_TO_COUNCIL_REPLAN",
            strategic_role="MULTI_AGENT_COUNCIL",
            execution_role="SINGLE_SLICED_PLANNER_AFTER_REPLAN",
            council_runs=1,
            local_repair_allowed=False,
            escalation_required=True,
            reasons=tuple(reasons),
            confidence=0.94 if graph_signal else 0.86,
        )
    return CognitiveLaborDecision(
        route="SURGEON_LOCAL_REPAIR",
        strategic_role="NONE",
        execution_role="SINGLE_SLICED_PLANNER",
        council_runs=0,
        local_repair_allowed=True,
        escalation_required=False,
        reasons=tuple(reasons or ["bounded_local_failure"]),
        confidence=0.90,
    )


__all__ = [
    "COGNITIVE_LABOR_ROUTER_VERSION",
    "CognitiveLaborDecision",
    "route_failure",
    "route_initial_refactor",
]
