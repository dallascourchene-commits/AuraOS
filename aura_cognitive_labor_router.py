"""Route refactor cognition between Aura's Council and sliced implementers.

The Council is strategic: cross-domain architecture, dependency sequencing,
trade-offs, invariants, and graph repair. The Surgeon is tactical: exact-file
implementation, compile-ready patches, focused tests, and bounded local repair.

Routing is descriptive and advisory. It never grants patch or promotion authority.
Untrusted failure evidence is parsed strictly and fails closed without raising.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

COGNITIVE_LABOR_ROUTER_VERSION = "AURA_COGNITIVE_LABOR_ROUTER_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_ARCHITECTURE_TERMS = {
    "architecture", "cross-domain", "cross domain", "dependency graph",
    "interface contract", "migration", "governance", "invariant",
    "rollback graph", "compatibility", "multi-module", "multi module",
}
_GRAPH_FAILURE_TERMS = {
    "dependency", "interface", "contract", "invariant", "migration",
    "topology", "downstream", "rollback graph", "plan invalid",
    "sequence invalid", "authority", "security boundary",
}
_LOCAL_FAILURE_TERMS = {
    "assertion", "syntax", "type error", "lint", "focused test",
    "unit test", "single file", "single symbol",
}
_TRUE_STRINGS = frozenset({"1", "true", "yes", "on", "breach"})
_FALSE_STRINGS = frozenset({"0", "false", "no", "off", "none", ""})
_PACKET_FLAG_FIELDS = (
    "invariant_breach",
    "interface_contract_breach",
    "dependency_graph_breach",
)


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

    visit(value)
    return " ".join(parts)


def _contains(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _strict_flag(value: Any) -> tuple[bool, bool]:
    """Return (enabled, valid). Unknown encodings are invalid, never truthy."""
    if isinstance(value, bool):
        return value, True
    if isinstance(value, int) and not isinstance(value, bool):
        if value in {0, 1}:
            return bool(value), True
        return False, False
    if isinstance(value, float):
        if not math.isfinite(value) or value not in {0.0, 1.0}:
            return False, False
        return bool(value), True
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return True, True
        if normalized in _FALSE_STRINGS:
            return False, True
        return False, False
    if value is None:
        return False, True
    return False, False


def _nonnegative_count(value: Any, *, default: int | None = None) -> tuple[int | None, bool]:
    """Parse an untrusted counter without bool coercion, NaN, or exceptions."""
    if value is None:
        return default, default is not None
    if isinstance(value, bool):
        return None, False
    if isinstance(value, int):
        return (value, True) if value >= 0 else (None, False)
    if isinstance(value, float):
        if math.isfinite(value) and value >= 0 and value.is_integer():
            return int(value), True
        return None, False
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text), True
        return None, False
    return None, False


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
    local_repair_attempts: Any = None,
    affected_task_count: Any = 1,
    affected_file_count: Any = 1,
    downstream_tasks_invalidated: Any = 0,
    invariant_breach: Any = False,
    interface_contract_breach: Any = False,
    dependency_graph_breach: Any = False,
    max_local_repairs: Any = 2,
) -> CognitiveLaborDecision:
    """Route failure evidence without allowing malformed packets to raise.

    Invalid counters or flag encodings fail closed to a Council replan. This route
    is advisory and does not grant mutation or promotion authority.
    """
    packet = dict(failure_packet or {})
    invalid: list[str] = []

    attempts_source = packet.get("repair_attempt") if local_repair_attempts is None else local_repair_attempts
    attempts, ok = _nonnegative_count(attempts_source, default=0)
    if not ok:
        invalid.append("repair_attempt")

    task_count, ok = _nonnegative_count(affected_task_count, default=1)
    if not ok:
        invalid.append("affected_task_count")
    file_count, ok = _nonnegative_count(affected_file_count, default=1)
    if not ok:
        invalid.append("affected_file_count")
    downstream_count, ok = _nonnegative_count(downstream_tasks_invalidated, default=0)
    if not ok:
        invalid.append("downstream_tasks_invalidated")
    repair_budget, ok = _nonnegative_count(max_local_repairs, default=2)
    if not ok or repair_budget == 0:
        invalid.append("max_local_repairs")

    explicit_flags = {
        "invariant_breach": invariant_breach,
        "interface_contract_breach": interface_contract_breach,
        "dependency_graph_breach": dependency_graph_breach,
    }
    normalized_flags: dict[str, bool] = {}
    for field, explicit in explicit_flags.items():
        source = packet.get(field) if field in packet and explicit is False else explicit
        enabled, valid = _strict_flag(source)
        normalized_flags[field] = enabled
        if not valid:
            invalid.append(field)

    if invalid:
        return CognitiveLaborDecision(
            route="ESCALATE_TO_COUNCIL_REPLAN",
            strategic_role="MULTI_AGENT_COUNCIL",
            execution_role="SINGLE_SLICED_PLANNER_AFTER_REPLAN",
            council_runs=1,
            local_repair_allowed=False,
            escalation_required=True,
            reasons=("invalid_failure_evidence:" + ",".join(sorted(set(invalid))),),
            confidence=0.99,
        )

    assert attempts is not None and task_count is not None and file_count is not None
    assert downstream_count is not None and repair_budget is not None
    text = _text(packet)
    graph_signal = (
        normalized_flags["invariant_breach"]
        or normalized_flags["interface_contract_breach"]
        or normalized_flags["dependency_graph_breach"]
        or downstream_count > 0
        or task_count > 1
        or file_count > 2
        or _contains(text, _GRAPH_FAILURE_TERMS)
    )
    local_signal = (
        task_count <= 1
        and file_count <= 2
        and downstream_count == 0
        and not any(normalized_flags.values())
        and (_contains(text, _LOCAL_FAILURE_TERMS) or not graph_signal)
    )
    reasons: list[str] = []
    if graph_signal:
        reasons.append("failure_invalidates_execution_graph_or_invariants")
    if attempts >= repair_budget:
        reasons.append("local_repair_budget_exhausted")
    if local_signal:
        reasons.append("failure_is_local_to_leased_capsule")

    escalate = graph_signal or attempts >= repair_budget
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
