"""Fail-closed Creator Studio harness cost/swarm route policy.

This module is pure policy. It performs no provider/model calls and does not own
effect authority. It compiles one current task plus preflighted route candidates
into exactly one lawful route decision. A failed route is returned to the
harness as a residual; this module never performs implicit fallback.

CS-HARNESS-001 / H-D invariants:
- R0..R6 are ordered free/reuse-first.
- External routes bind exact provider + model, never a model-role alias.
- Paid routes require explicit inherited authority and known finite cost within ceiling.
- Swarms are off by default. Owner-deployed swarm authority or one typed earned
  parallelism reason is required, plus separate effect authority.
- External DeepSeek swarms require the AWJ-033 integrity/currentness gate.
- DeepSeek V4 Pro requires a typed earned escalation reference.
- Route semantics, not caller-declared flags, determine whether effect authority
  and route/provider/cost constraints apply.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

SCHEMA = "CreatorStudioHarnessRouteDecisionV1"

ROUTE_RANK = {
    "R0_REUSE": 0,
    "R1_LOCAL_DETERMINISTIC": 1,
    "R2_AURA_NATIVE": 2,
    "R3_CHATGPT": 3,
    "R4_LOW_MARGIN_SPECIALIST": 4,
    "R5_SWARM": 5,
    "R6_PAID_EXTERNAL": 6,
}

_GENERIC_MODEL_ALIASES = frozenset(
    {
        "default", "primary", "best", "premium", "reasoner", "coding",
        "cheap", "budget", "fast", "flash", "deepseek", "cheap_builder",
        "shadow", "summarizer",
    }
)

EARNED_SWARM_REASONS = frozenset(
    {"BLIND_SPLIT", "BENCHMARK_FALSIFICATION", "INDEPENDENT_FRONTIER", "MEASURED_ECONOMIC_PARALLELISM"}
)


class HarnessRoutePolicyError(ValueError):
    """Typed invalid-input error for the deterministic route compiler."""
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _text(value: Any) -> str:
    return str(value or "").strip()


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _candidate_id(candidate: Mapping[str, Any], ordinal: int) -> str:
    return _text(candidate.get("route_id")) or f"candidate-{ordinal}"


def _validate_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise HarnessRoutePolicyError("ROUTE_REQUEST_NOT_OBJECT")
    if not _text(request.get("task_id")):
        raise HarnessRoutePolicyError("TASK_ID_REQUIRED")
    if request.get("cost_ceiling_usd") is not None:
        ceiling = request.get("cost_ceiling_usd")
        if not _is_finite_number(ceiling) or ceiling < 0:
            raise HarnessRoutePolicyError("INVALID_COST_CEILING")


def _route_attribute_rejection(candidate: Mapping[str, Any]) -> str | None:
    """Reject rank/semantics spoofing between route class and effect attributes."""
    route_class = _text(candidate.get("route_class"))
    external = candidate.get("external_provider") is True
    paid = candidate.get("paid") is True

    # R0-R3 are the free/reuse/local/native/current-ChatGPT substrate. They
    # cannot be relabeled external or paid merely to acquire a cheaper rank.
    if route_class in {
        "R0_REUSE",
        "R1_LOCAL_DETERMINISTIC",
        "R2_AURA_NATIVE",
        "R3_CHATGPT",
    } and (external or paid):
        return "ROUTE_ATTRIBUTE_MISMATCH"

    # R4 may be local or an exact external specialist, but it is not the paid
    # fallback class. A paid specialist must route as R6 so cost/authority
    # semantics cannot hide behind a lower rank.
    if route_class == "R4_LOW_MARGIN_SPECIALIST" and paid:
        return "ROUTE_ATTRIBUTE_MISMATCH"

    # R6 is definitionally an exact paid external route.
    if route_class == "R6_PAID_EXTERNAL" and not (external and paid):
        return "ROUTE_ATTRIBUTE_MISMATCH"

    return None


def _candidate_rejection(request: Mapping[str, Any], candidate: Mapping[str, Any]) -> str | None:
    if not isinstance(candidate, Mapping):
        return "CANDIDATE_NOT_OBJECT"
    route_class = _text(candidate.get("route_class"))
    if route_class not in ROUTE_RANK:
        return "UNKNOWN_ROUTE_CLASS"

    mismatch = _route_attribute_rejection(candidate)
    if mismatch is not None:
        return mismatch

    if candidate.get("currentness") != "CURRENT":
        return "CANDIDATE_NOT_CURRENT"
    if candidate.get("capability_fit") is not True:
        return "CAPABILITY_MISMATCH"
    if candidate.get("adequacy") not in {"ADEQUATE", "ELIGIBLE"}:
        return "ADEQUACY_NOT_ESTABLISHED"

    # Effect requirement is not caller-optional for external/paid/swarm routes.
    effect_required = (
        candidate.get("requires_effect") is True
        or candidate.get("external_provider") is True
        or candidate.get("paid") is True
        or route_class in {"R5_SWARM", "R6_PAID_EXTERNAL"}
    )
    if effect_required and candidate.get("effect_authorized") is not True:
        return "EFFECT_AUTHORITY_REQUIRED"

    cost = candidate.get("estimated_marginal_cost_usd")
    if cost is not None and (not _is_finite_number(cost) or cost < 0):
        return "PAID_COST_UNKNOWN_OR_INVALID" if candidate.get("paid") is True else "COST_INVALID"

    if candidate.get("external_provider") is True:
        provider = _text(candidate.get("provider_id"))
        model = _text(candidate.get("model_id"))
        if not provider or not model:
            return "EXACT_PROVIDER_MODEL_REQUIRED"
        if model.casefold() in _GENERIC_MODEL_ALIASES:
            return "MODEL_ROLE_ALIAS_FORBIDDEN"
        if candidate.get("allow_provider_fallback") is not False:
            return "IMPLICIT_PROVIDER_FALLBACK_FORBIDDEN"

    if candidate.get("paid") is True:
        if request.get("paid_provider_authorized") is not True:
            return "PAID_PROVIDER_AUTHORITY_REQUIRED"
        if cost is None or not _is_finite_number(cost) or cost < 0:
            return "PAID_COST_UNKNOWN_OR_INVALID"
        ceiling = request.get("cost_ceiling_usd")
        if ceiling is not None and cost > ceiling:
            return "COST_CEILING_EXCEEDED"

    if route_class == "R5_SWARM":
        owner_deploy = request.get("owner_swarm_deploy_authorized") is True
        earned_reason = _text(request.get("earned_swarm_reason")).upper()
        if not owner_deploy and earned_reason not in EARNED_SWARM_REASONS:
            return "SWARM_NOT_AUTHORIZED_OR_EARNED"
        if candidate.get("effect_authorized") is not True:
            return "SWARM_EFFECT_AUTHORITY_REQUIRED"

        # A candidate cannot opt itself out of the AWJ-033 gate with a false
        # `deepseek_physical_swarm` flag. External DeepSeek R5 is derived here.
        deepseek_physical = (
            candidate.get("external_provider") is True
            and _text(candidate.get("provider_id")).casefold() == "deepseek"
        )
        if deepseek_physical and request.get("awj033_physical_swarm_ready") is not True:
            return "AWJ033_PHYSICAL_SWARM_GATE_REQUIRED"

    if _text(candidate.get("model_id")).casefold() == "deepseek-v4-pro":
        if request.get("pro_escalation_earned") is not True or not _text(request.get("pro_escalation_ref")):
            return "DEEPSEEK_PRO_ESCALATION_REQUIRED"
    return None


def _cost_key(candidate: Mapping[str, Any]) -> float:
    cost = candidate.get("estimated_marginal_cost_usd")
    if _is_finite_number(cost):
        return float(cost)
    # UNKNOWN remains UNKNOWN in the receipt; this only stabilizes same-rank order.
    return float("inf")


def select_creator_studio_route(request: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return one exact fail-closed route decision without executing it."""
    _validate_request(request)
    if request.get("project_currentness") != "CURRENT":
        return {"schema": SCHEMA, "task_id": _text(request.get("task_id")), "decision": "REBASE_REQUIRED", "selected_route": None, "reason_codes": ["PROJECT_CURRENTNESS_NOT_CURRENT"], "fallback_allowed": False, "evaluated": []}
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise HarnessRoutePolicyError("CANDIDATES_NOT_SEQUENCE")

    evaluated: list[dict[str, Any]] = []
    eligible: list[tuple[int, Mapping[str, Any]]] = []
    for ordinal, candidate in enumerate(candidates):
        rejection = _candidate_rejection(request, candidate)
        evaluated.append({
            "route_id": _candidate_id(candidate, ordinal) if isinstance(candidate, Mapping) else f"candidate-{ordinal}",
            "route_class": _text(candidate.get("route_class")) if isinstance(candidate, Mapping) else "UNKNOWN",
            "eligible": rejection is None,
            "rejection_code": rejection,
        })
        if rejection is None:
            eligible.append((ordinal, candidate))

    if not eligible:
        return {"schema": SCHEMA, "task_id": _text(request.get("task_id")), "decision": "NO_ELIGIBLE_ROUTE", "selected_route": None, "reason_codes": sorted({x["rejection_code"] for x in evaluated if x["rejection_code"]}), "fallback_allowed": False, "evaluated": evaluated}

    def sort_key(item: tuple[int, Mapping[str, Any]]) -> tuple[Any, ...]:
        ordinal, candidate = item
        return (ROUTE_RANK[_text(candidate.get("route_class"))], _cost_key(candidate), _candidate_id(candidate, ordinal))

    selected_ordinal, selected = min(eligible, key=sort_key)
    derived_deepseek_physical = (
        _text(selected.get("route_class")) == "R5_SWARM"
        and selected.get("external_provider") is True
        and _text(selected.get("provider_id")).casefold() == "deepseek"
    )
    selected_route = {
        "route_id": _candidate_id(selected, selected_ordinal),
        "route_class": _text(selected.get("route_class")),
        "provider_id": _text(selected.get("provider_id")) or None,
        "model_id": _text(selected.get("model_id")) or None,
        "paid": selected.get("paid") is True,
        "estimated_marginal_cost_usd": selected.get("estimated_marginal_cost_usd"),
        "effect_authorized": selected.get("effect_authorized") is True,
        "deepseek_physical_swarm": derived_deepseek_physical,
    }
    return {"schema": SCHEMA, "task_id": _text(request.get("task_id")), "decision": "ROUTE_SELECTED", "selected_route": selected_route, "reason_codes": ["FREE_FIRST_LOWEST_LAWFUL_ROUTE"], "fallback_allowed": False, "evaluated": evaluated}
