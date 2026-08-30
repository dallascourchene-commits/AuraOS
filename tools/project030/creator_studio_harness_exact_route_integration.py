"""Exact route-generation binding wrapper for the current H-I integration seam.

This is a non-owner composition layer. It does not create WorkGraph, claim, route,
continuation, wake, or effect authority. It binds the current WorkGraph's exact
route-policy/currentness generation to a route-selection receipt, then delegates
only that exact selected candidate to the existing H-I admission/claim integration.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from aura_arena_workgraph import project_workgraph
from aura_arena_route_binding import select_exact_bound_route
from creator_studio_harness_integration import READY, prepare_substantive_act

SCHEMA = "CreatorStudioHarnessExactRouteIntegrationV1"


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


def _result(
    *,
    decision: str,
    reason_codes: Sequence[str],
    route_policy_ref: str,
    currentness_ref: str,
    route_binding_receipt_id: str | None = None,
    underlying_integration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    underlying = dict(underlying_integration or {})
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "decision": decision,
        "reason_codes": sorted(set(str(x) for x in reason_codes if str(x).strip())),
        "route_policy_ref": route_policy_ref,
        "currentness_ref": currentness_ref,
        "route_binding_receipt_id": route_binding_receipt_id,
        "underlying_integration_receipt_id": underlying.get("integration_receipt_id"),
        "worker_id": underlying.get("worker_id"),
        "cell_id": underlying.get("cell_id"),
        "graph_digest": underlying.get("graph_digest"),
        "claim_id": underlying.get("claim_id"),
        "route_id": underlying.get("route_id"),
        "route_class": underlying.get("route_class"),
        "board_revision": underlying.get("board_revision"),
        "execution_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
        "provider_calls": 0,
    }
    body["exact_integration_receipt_id"] = "cs-harness-exact-route-" + _digest(body)[:24]
    return body


def prepare_exact_bound_substantive_act(
    *,
    admission_ctx: Any,
    workgraph_state: Mapping[str, Any],
    worker_id: str,
    now_ms: int,
    route_request: Mapping[str, Any],
    route_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Require exact policy-generation binding before the existing H-I READY path."""
    projection = project_workgraph(workgraph_state, now_ms=now_ms)
    route_policy_ref = _text(projection.get("route_policy_ref"))
    currentness_ref = _text(projection.get("currentness_ref"))
    if not route_policy_ref or not currentness_ref:
        return _result(
            decision="REBASE_REQUIRED",
            reason_codes=["WORKGRAPH_ROUTE_GENERATION_BINDING_MISSING"],
            route_policy_ref=route_policy_ref,
            currentness_ref=currentness_ref,
        )

    binding = select_exact_bound_route(
        request=route_request,
        candidates=route_candidates,
        expected_route_policy_ref=route_policy_ref,
        expected_currentness_ref=currentness_ref,
    )
    if binding.get("decision") != "ROUTE_SELECTED" or not isinstance(binding.get("selected_route"), Mapping):
        decision = "REBASE_REQUIRED" if binding.get("decision") == "REBASE_REQUIRED" else "ROUTE_REQUIRED"
        return _result(
            decision=decision,
            reason_codes=binding.get("reason_codes") or ["NO_EXACT_BOUND_ROUTE"],
            route_policy_ref=route_policy_ref,
            currentness_ref=currentness_ref,
            route_binding_receipt_id=_text(binding.get("route_binding_receipt_id")) or None,
        )

    selected = binding["selected_route"]
    selected_id = _text(selected.get("route_id"))
    exact_candidates = [
        row
        for row in route_candidates
        if isinstance(row, Mapping)
        and _text(row.get("route_id")) == selected_id
        and _text(row.get("route_policy_ref")) == route_policy_ref
        and _text(row.get("currentness_ref")) == currentness_ref
    ]
    if len(exact_candidates) != 1:
        return _result(
            decision="REBASE_REQUIRED",
            reason_codes=["EXACT_SELECTED_CANDIDATE_NOT_UNIQUE"],
            route_policy_ref=route_policy_ref,
            currentness_ref=currentness_ref,
            route_binding_receipt_id=_text(binding.get("route_binding_receipt_id")) or None,
        )

    underlying = prepare_substantive_act(
        admission_ctx=admission_ctx,
        workgraph_state=workgraph_state,
        worker_id=worker_id,
        now_ms=now_ms,
        route_request=route_request,
        route_candidates=exact_candidates,
    )
    if not isinstance(underlying, Mapping):
        raise ValueError("UNDERLYING_INTEGRATION_RESULT_NOT_OBJECT")
    if underlying.get("decision") != READY:
        return _result(
            decision=_text(underlying.get("decision")) or "UNDERLYING_INTEGRATION_REFUSED",
            reason_codes=underlying.get("reason_codes") or ["UNDERLYING_INTEGRATION_REFUSED"],
            route_policy_ref=route_policy_ref,
            currentness_ref=currentness_ref,
            route_binding_receipt_id=_text(binding.get("route_binding_receipt_id")) or None,
            underlying_integration=underlying,
        )

    if _text(underlying.get("route_id")) != selected_id:
        return _result(
            decision="REBASE_REQUIRED",
            reason_codes=["UNDERLYING_ROUTE_SELECTION_MISMATCH"],
            route_policy_ref=route_policy_ref,
            currentness_ref=currentness_ref,
            route_binding_receipt_id=_text(binding.get("route_binding_receipt_id")) or None,
            underlying_integration=underlying,
        )

    return _result(
        decision=READY,
        reason_codes=["EXACT_ROUTE_POLICY_CURRENTNESS_BOUND", "NO_EXECUTION_AUTHORITY_CREATED"],
        route_policy_ref=route_policy_ref,
        currentness_ref=currentness_ref,
        route_binding_receipt_id=_text(binding.get("route_binding_receipt_id")) or None,
        underlying_integration=underlying,
    )
