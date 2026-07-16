"""Fail-closed Council/Surgeon routing for bounded Aura refactors."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
import math
from typing import Any

COGNITIVE_LABOR_ROUTER_VERSION = "AURA_COGNITIVE_LABOR_ROUTER_V3"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_UNSET = object()
_MAX_COUNT = 1_000_000
_ARCH = {"architecture", "cross-domain", "cross domain", "dependency graph", "interface contract", "migration", "governance", "invariant", "rollback graph", "compatibility", "multi-module", "multi module"}
_GRAPH = {"dependency", "interface", "contract", "invariant", "migration", "topology", "downstream", "rollback graph", "plan invalid", "sequence invalid", "authority", "security boundary"}
_LOCAL = {"assertion", "syntax", "type error", "lint", "focused test", "unit test", "single file", "single symbol"}
_TRUE = {"1", "true", "yes", "on", "breach"}
_FALSE = {"0", "false", "no", "off", "none", ""}
_FLAGS = ("invariant_breach", "interface_contract_breach", "dependency_graph_breach")


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
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


def _packet(value: Any) -> tuple[dict[str, Any], bool]:
    if value is None:
        return {}, True
    if isinstance(value, dict):
        return dict(value), True
    if isinstance(value, Mapping):
        try:
            return {str(key): item for key, item in value.items()}, True
        except Exception:
            pass
    return {}, False


def _text(value: Any) -> str:
    parts: list[str] = []
    budget = 256

    def visit(item: Any) -> None:
        nonlocal budget
        if budget <= 0:
            return
        budget -= 1
        if isinstance(item, str):
            if item.strip():
                parts.append(item.strip().lower()[:1024])
        elif isinstance(item, Mapping):
            try:
                children = list(item.values())[:64]
            except Exception:
                children = []
            for child in children:
                visit(child)
        elif isinstance(item, (list, tuple, set, frozenset)):
            for child in list(item)[:64]:
                visit(child)

    visit(value)
    return " ".join(parts)


def _has(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _flag(value: Any) -> tuple[bool, bool]:
    if isinstance(value, bool):
        return value, True
    if isinstance(value, int) and not isinstance(value, bool):
        return (bool(value), True) if value in {0, 1} else (False, False)
    if isinstance(value, float):
        return (bool(value), True) if math.isfinite(value) and value in {0.0, 1.0} else (False, False)
    if isinstance(value, str):
        value = value.strip().lower()
        if value in _TRUE:
            return True, True
        if value in _FALSE:
            return False, True
        return False, False
    return (False, True) if value is None else (False, False)


def _count(value: Any, default: int) -> tuple[int | None, bool]:
    if value is None:
        return default, True
    if isinstance(value, bool):
        return None, False
    parsed: int | None = None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        parsed = int(value)
    elif isinstance(value, str) and value.strip().isascii() and value.strip().isdigit():
        try:
            parsed = int(value.strip())
        except (ValueError, OverflowError):
            pass
    return (parsed, True) if parsed is not None and 0 <= parsed <= _MAX_COUNT else (None, False)


def route_initial_refactor(*, objective: str, task_count: int, distinct_file_count: int, dependency_edge_count: int, sequential_depth: int, cross_domain_count: int = 0, large_task_count: int = 0) -> CognitiveLaborDecision:
    text = _text(objective)
    signals = 0
    reasons: list[str] = []
    for condition, weight, reason in (
        (_has(text, _ARCH), 2, "architectural_objective"),
        (dependency_edge_count >= 2 or sequential_depth >= 3, 2, "dependency_sequence_requires_global_plan"),
        (task_count >= 4 or distinct_file_count >= 5, 1, "multi_step_or_multi_file_scope"),
        (cross_domain_count >= 2, 2, "cross_domain_tradeoffs"),
        (large_task_count >= 2, 1, "multiple_large_capsules"),
    ):
        if condition:
            signals += weight
            reasons.append(reason)
    if signals >= 3:
        return CognitiveLaborDecision("COUNCIL_PLAN_THEN_SURGEON_EXECUTION", "MULTI_AGENT_COUNCIL", "SINGLE_SLICED_PLANNER", 1, True, False, tuple(reasons), min(0.98, 0.70 + signals * 0.04))
    return CognitiveLaborDecision("SURGEON_ONLY", "NONE", "SINGLE_SLICED_PLANNER", 0, True, False, tuple(reasons or ["localized_bounded_implementation"]), 0.88 if signals == 0 else 0.78)


def _invalid(fields: list[str]) -> CognitiveLaborDecision:
    return CognitiveLaborDecision("ESCALATE_TO_COUNCIL_REPLAN", "MULTI_AGENT_COUNCIL", "SINGLE_SLICED_PLANNER_AFTER_REPLAN", 1, False, True, ("invalid_failure_evidence:" + ",".join(sorted(set(fields))),), 0.99)


def route_failure(*, failure_packet: Any, local_repair_attempts: Any = _UNSET, affected_task_count: Any = 1, affected_file_count: Any = 1, downstream_tasks_invalidated: Any = 0, invariant_breach: Any = _UNSET, interface_contract_breach: Any = _UNSET, dependency_graph_breach: Any = _UNSET, max_local_repairs: Any = 2) -> CognitiveLaborDecision:
    """Return a typed local-repair or fail-closed Council decision; never raise on input."""
    packet, valid_packet = _packet(failure_packet)
    invalid = [] if valid_packet else ["failure_packet"]
    raw = packet.get("repair_attempt", 0) if local_repair_attempts is _UNSET else local_repair_attempts
    attempts, ok = _count(raw, 0)
    if not ok:
        invalid.append("repair_attempt")
    counts: dict[str, int | None] = {}
    for name, value, default in (
        ("affected_task_count", affected_task_count, 1),
        ("affected_file_count", affected_file_count, 1),
        ("downstream_tasks_invalidated", downstream_tasks_invalidated, 0),
        ("max_local_repairs", max_local_repairs, 2),
    ):
        counts[name], ok = _count(value, default)
        if not ok or (name == "max_local_repairs" and counts[name] == 0):
            invalid.append(name)
    explicit = {"invariant_breach": invariant_breach, "interface_contract_breach": interface_contract_breach, "dependency_graph_breach": dependency_graph_breach}
    flags: dict[str, bool] = {}
    for name in _FLAGS:
        flags[name], ok = _flag(packet.get(name) if explicit[name] is _UNSET else explicit[name])
        if not ok:
            invalid.append(name)
    if invalid:
        return _invalid(invalid)
    assert attempts is not None and all(value is not None for value in counts.values())
    tasks = int(counts["affected_task_count"] or 0)
    files = int(counts["affected_file_count"] or 0)
    downstream = int(counts["downstream_tasks_invalidated"] or 0)
    budget = int(counts["max_local_repairs"] or 0)
    graph = any(flags.values()) or downstream > 0 or tasks > 1 or files > 2 or _has(_text(packet), _GRAPH)
    reasons: list[str] = []
    if graph:
        reasons.append("failure_invalidates_execution_graph_or_invariants")
    if attempts >= budget:
        reasons.append("local_repair_budget_exhausted")
    if graph or attempts >= budget:
        return CognitiveLaborDecision("ESCALATE_TO_COUNCIL_REPLAN", "MULTI_AGENT_COUNCIL", "SINGLE_SLICED_PLANNER_AFTER_REPLAN", 1, False, True, tuple(reasons), 0.94 if graph else 0.86)
    if tasks <= 1 and files <= 2 and downstream == 0 and not any(flags.values()):
        reasons.append("failure_is_local_to_leased_capsule")
    return CognitiveLaborDecision("SURGEON_LOCAL_REPAIR", "NONE", "SINGLE_SLICED_PLANNER", 0, True, False, tuple(reasons or ["bounded_local_failure"]), 0.90)


__all__ = ["COGNITIVE_LABOR_ROUTER_VERSION", "CognitiveLaborDecision", "route_failure", "route_initial_refactor"]
