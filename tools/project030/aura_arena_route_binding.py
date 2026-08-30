"""Exact route-policy/currentness generation binding for Arena harness composition.

This module wraps an existing deterministic route selector. It does not own route
semantics, WorkGraph state, claims, effects, providers, or execution. Its only job
is to prove that the route request and the candidate selected by the underlying
router were preflighted against the exact policy/currentness generation supplied
by the canonical WorkGraph projection.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any, Callable

from aura_creator_studio_harness_router import select_creator_studio_route

SCHEMA = "AuraArenaRouteBindingV1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _digest(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _candidate_id(candidate: Mapping[str, Any], ordinal: int) -> str:
    return _text(candidate.get("route_id")) or f"candidate-{ordinal}"


def _receipt(
    *,
    task_id: str,
    decision: str,
    reason_codes: Sequence[str],
    route_policy_ref: str,
    currentness_ref: str,
    selected_route: Mapping[str, Any] | None,
    underlying: Mapping[str, Any] | None = None,
    filtered_candidates: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "task_id": task_id,
        "decision": decision,
        "reason_codes": sorted(set(str(x) for x in reason_codes if str(x).strip())),
        "route_policy_ref": route_policy_ref,
        "currentness_ref": currentness_ref,
        "selected_route": dict(selected_route) if selected_route is not None else None,
        "filtered_candidates": [dict(x) for x in filtered_candidates],
        "underlying_route_schema": _text((underlying or {}).get("schema")) or None,
        "underlying_route_decision": _text((underlying or {}).get("decision")) or None,
        "execution_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
        "provider_calls": 0,
    }
    body["route_binding_receipt_id"] = "arena-route-binding-" + _digest(body)[:24]
    return body


def select_exact_bound_route(
    *,
    request: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    expected_route_policy_ref: str,
    expected_currentness_ref: str,
    selector: Callable[[Mapping[str, Any], Sequence[Mapping[str, Any]]], Mapping[str, Any]] = select_creator_studio_route,
) -> dict[str, Any]:
    """Select only among candidates bound to the exact WorkGraph policy generation."""
    policy_ref = _text(expected_route_policy_ref)
    currentness_ref = _text(expected_currentness_ref)
    if not policy_ref:
        raise ValueError("ROUTE_POLICY_REF_REQUIRED")
    if not currentness_ref:
        raise ValueError("CURRENTNESS_REF_REQUIRED")
    if not isinstance(request, Mapping):
        raise ValueError("ROUTE_REQUEST_NOT_OBJECT")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise ValueError("CANDIDATES_NOT_SEQUENCE")

    task_id = _text(request.get("task_id"))
    request_failures: list[str] = []
    if _text(request.get("route_policy_ref")) != policy_ref:
        request_failures.append("ROUTE_POLICY_REF_MISMATCH")
    if _text(request.get("currentness_ref")) != currentness_ref:
        request_failures.append("ROUTE_CURRENTNESS_REF_MISMATCH")
    if request_failures:
        return _receipt(
            task_id=task_id,
            decision="REBASE_REQUIRED",
            reason_codes=request_failures,
            route_policy_ref=policy_ref,
            currentness_ref=currentness_ref,
            selected_route=None,
        )

    bound: list[Mapping[str, Any]] = []
    filtered: list[dict[str, Any]] = []
    for ordinal, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            filtered.append({
                "route_id": f"candidate-{ordinal}",
                "reason_code": "CANDIDATE_NOT_OBJECT",
            })
            continue
        reason_codes: list[str] = []
        if _text(candidate.get("route_policy_ref")) != policy_ref:
            reason_codes.append("CANDIDATE_ROUTE_POLICY_REF_MISMATCH")
        if _text(candidate.get("currentness_ref")) != currentness_ref:
            reason_codes.append("CANDIDATE_CURRENTNESS_REF_MISMATCH")
        if reason_codes:
            filtered.append({
                "route_id": _candidate_id(candidate, ordinal),
                "reason_codes": reason_codes,
            })
            continue
        bound.append(candidate)

    if not bound:
        reasons = [
            code
            for row in filtered
            for code in (row.get("reason_codes") or [row.get("reason_code")])
            if code
        ]
        return _receipt(
            task_id=task_id,
            decision="NO_EXACT_BOUND_ROUTE",
            reason_codes=reasons or ["NO_EXACT_BOUND_ROUTE"],
            route_policy_ref=policy_ref,
            currentness_ref=currentness_ref,
            selected_route=None,
            filtered_candidates=filtered,
        )

    underlying = selector(request, bound)
    if not isinstance(underlying, Mapping):
        raise ValueError("UNDERLYING_ROUTE_RESULT_NOT_OBJECT")
    if underlying.get("decision") != "ROUTE_SELECTED" or not isinstance(underlying.get("selected_route"), Mapping):
        return _receipt(
            task_id=task_id,
            decision=_text(underlying.get("decision")) or "ROUTE_REQUIRED",
            reason_codes=underlying.get("reason_codes") or ["NO_ELIGIBLE_ROUTE"],
            route_policy_ref=policy_ref,
            currentness_ref=currentness_ref,
            selected_route=None,
            underlying=underlying,
            filtered_candidates=filtered,
        )

    selected = dict(underlying["selected_route"])
    selected_id = _text(selected.get("route_id"))
    source_candidate = next(
        (row for ordinal, row in enumerate(bound) if _candidate_id(row, ordinal) == selected_id),
        None,
    )
    if source_candidate is None:
        return _receipt(
            task_id=task_id,
            decision="REBASE_REQUIRED",
            reason_codes=["SELECTED_ROUTE_SOURCE_BINDING_MISSING"],
            route_policy_ref=policy_ref,
            currentness_ref=currentness_ref,
            selected_route=None,
            underlying=underlying,
            filtered_candidates=filtered,
        )
    if _text(source_candidate.get("route_policy_ref")) != policy_ref:
        return _receipt(
            task_id=task_id,
            decision="REBASE_REQUIRED",
            reason_codes=["SELECTED_ROUTE_POLICY_REF_MISMATCH"],
            route_policy_ref=policy_ref,
            currentness_ref=currentness_ref,
            selected_route=None,
            underlying=underlying,
            filtered_candidates=filtered,
        )
    if _text(source_candidate.get("currentness_ref")) != currentness_ref:
        return _receipt(
            task_id=task_id,
            decision="REBASE_REQUIRED",
            reason_codes=["SELECTED_ROUTE_CURRENTNESS_REF_MISMATCH"],
            route_policy_ref=policy_ref,
            currentness_ref=currentness_ref,
            selected_route=None,
            underlying=underlying,
            filtered_candidates=filtered,
        )

    selected["route_policy_ref"] = policy_ref
    selected["currentness_ref"] = currentness_ref
    return _receipt(
        task_id=task_id,
        decision="ROUTE_SELECTED",
        reason_codes=["EXACT_ROUTE_POLICY_CURRENTNESS_BOUND"],
        route_policy_ref=policy_ref,
        currentness_ref=currentness_ref,
        selected_route=selected,
        underlying=underlying,
        filtered_candidates=filtered,
    )
