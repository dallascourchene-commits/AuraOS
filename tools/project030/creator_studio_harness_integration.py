"""Cross-lane fail-closed integration seam for CS-HARNESS-001.

This module composes existing owners instead of creating another scheduler:
- H-A owns Arena admission/orientation.
- the canonical AuraArenaWorkGraphStateV1 owner owns eligibility/claim/currentness.
- H-D owns deterministic free-first route selection.
- continuation/wake owners consume the resulting coordination state.

The seam may say that a bounded substantive turn is *ready to be attempted*; it
never grants provider/effect authority, proves execution, wakes a background
worker, or persists a WorkGraph transition.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from aura_arena_admission import ActionClass, ArenaAdmissionContext, evaluate_admission
from aura_arena_workgraph import continuity_tick, project_workgraph
from aura_creator_studio_harness_router import select_creator_studio_route

SCHEMA = "CreatorStudioHarnessIntegrationV1"
READY = "READY_FOR_BOUNDED_ACT"


def _digest(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _result(
    decision: str,
    reason_codes: Sequence[str],
    *,
    worker_id: str | None,
    cell_id: str | None = None,
    graph_digest: str | None = None,
    admission_receipt_id: str | None = None,
    claim_id: str | None = None,
    route_id: str | None = None,
    route_class: str | None = None,
    board_revision: str | None = None,
    currentness_ref: str | None = None,
) -> dict[str, Any]:
    body = {
        "schema": SCHEMA,
        "decision": decision,
        "reason_codes": sorted(set(reason_codes)),
        "worker_id": worker_id,
        "cell_id": cell_id,
        "graph_digest": graph_digest,
        "admission_receipt_id": admission_receipt_id,
        "claim_id": claim_id,
        "route_id": route_id,
        "route_class": route_class,
        "board_revision": board_revision,
        "currentness_ref": currentness_ref,
        "execution_authorized": False,
        "runtime_execution_proven": False,
        "provider_calls": 0,
        "background_execution_claimed": False,
    }
    body["integration_receipt_id"] = f"cs-harness-integration-{_digest(body)[:24]}"
    return body


def plan_idle_worker_wake(
    workgraph_state: Mapping[str, Any],
    *,
    worker_id: str,
    now_ms: int,
    previous_graph_digest: str | None = None,
) -> dict[str, Any]:
    """Project one deterministic wake/select intent without execution authority."""
    projection = project_workgraph(workgraph_state, now_ms=now_ms)
    wake = continuity_tick(
        projection,
        worker_id=worker_id,
        previous_graph_digest=previous_graph_digest,
    )
    # Defensive cross-lane assertion: this seam must never launder wake into ACT.
    if wake.get("runtime_execution_proven") is not False or wake.get("effect_allowed") is not False:
        raise ValueError("WAKE_AUTHORITY_WIDENING")
    return wake


def prepare_substantive_act(
    *,
    admission_ctx: ArenaAdmissionContext,
    workgraph_state: Mapping[str, Any],
    worker_id: str,
    now_ms: int,
    route_request: Mapping[str, Any],
    route_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind admission + current WorkGraph claim + route before substantive ACT.

    The return value is coordination/admission evidence only. Even READY does not
    execute a model/provider/tool effect; the downstream effect owner must perform
    its own currentness/authority/idempotency checks immediately before effect.
    """
    admission = evaluate_admission(admission_ctx, ActionClass.SUBSTANTIVE)
    if not admission.allowed:
        return _result(
            "ADMISSION_REQUIRED",
            tuple(admission.missing) or (admission.code,),
            worker_id=worker_id,
            admission_receipt_id=admission.receipt_id,
        )
    if admission.worker_id != worker_id:
        return _result(
            "ADMISSION_BINDING_MISMATCH",
            ("WORKER_ID_MISMATCH",),
            worker_id=worker_id,
            admission_receipt_id=admission.receipt_id,
        )

    projection = project_workgraph(workgraph_state, now_ms=now_ms)
    graph_digest = str(projection.get("graph_digest") or "")
    board_revision = str(projection.get("board_revision") or "")
    currentness_ref = str(projection.get("currentness_ref") or "")

    binding_failures: list[str] = []
    if admission_ctx.collab_board_ref != projection.get("board_ref"):
        binding_failures.append("BOARD_REF_MISMATCH")
    if admission_ctx.sibling_state_ref != board_revision:
        binding_failures.append("BOARD_REVISION_MISMATCH")
    if admission_ctx.sibling_state_digest != graph_digest:
        binding_failures.append("GRAPH_DIGEST_MISMATCH")
    if admission_ctx.authoritative_head_ref != currentness_ref:
        binding_failures.append("CURRENTNESS_REF_MISMATCH")
    if admission_ctx.mission_ref != projection.get("mission_ref"):
        binding_failures.append("MISSION_REF_MISMATCH")
    if binding_failures:
        return _result(
            "REBASE_REQUIRED",
            binding_failures,
            worker_id=worker_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )

    admitted_cells = tuple(sorted(set(admission_ctx.claimed_cells)))
    if len(admitted_cells) != 1:
        return _result(
            "CLAIM_REQUIRED",
            ("ADMISSION_EXACT_ONE_CLAIM_REQUIRED",),
            worker_id=worker_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )
    admitted_cell_id = admitted_cells[0]

    # Reconciliation beats reacquisition. An expired claim with any possibly
    # started effect cannot be translated into a fresh ACT-ready turn.
    admitted_projection_cell = next(
        (cell for cell in projection.get("cells", []) if cell.get("cell_id") == admitted_cell_id),
        None,
    )
    if admitted_projection_cell and admitted_projection_cell.get("ambiguous_stale_claims"):
        return _result(
            "RECONCILE_EFFECT_STATE_REQUIRED",
            ("AMBIGUOUS_STALE_CLAIM",),
            worker_id=worker_id,
            cell_id=admitted_cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )

    owned: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for cell in projection.get("cells", []):
        for claim in cell.get("active_claims", []):
            if claim.get("worker_id") == worker_id:
                owned.append((dict(cell), dict(claim)))
    if not owned:
        return _result(
            "CLAIM_REQUIRED",
            ("NO_ACTIVE_OWNED_CLAIM",),
            worker_id=worker_id,
            cell_id=admitted_cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )
    if len(owned) != 1:
        return _result(
            "CLAIM_CONFLICT",
            ("WORKER_HAS_MULTIPLE_ACTIVE_CLAIMS",),
            worker_id=worker_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )

    cell, claim = owned[0]
    cell_id = str(cell.get("cell_id") or "")
    claim_id = str(claim.get("claim_id") or "")
    claim_failures: list[str] = []
    if cell_id != admitted_cell_id:
        claim_failures.append("ADMISSION_CLAIM_CELL_MISMATCH")
    if claim.get("currentness_ref") != currentness_ref:
        claim_failures.append("CLAIM_CURRENTNESS_MISMATCH")
    if cell.get("effective_state") != "CLAIMED":
        claim_failures.append("CELL_NOT_EXCLUSIVELY_CLAIMED")
    if cell.get("effect_class") != "D0":
        claim_failures.append("NON_D0_REQUIRES_SEPARATE_EFFECT_ADMISSION")
    if claim_failures:
        return _result(
            "CLAIM_NOT_ACT_READY",
            claim_failures,
            worker_id=worker_id,
            cell_id=cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            claim_id=claim_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )

    if str(route_request.get("task_id") or "").strip() != cell_id:
        return _result(
            "ROUTE_BINDING_MISMATCH",
            ("ROUTE_TASK_CELL_MISMATCH",),
            worker_id=worker_id,
            cell_id=cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            claim_id=claim_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )
    if route_request.get("project_currentness") != "CURRENT":
        return _result(
            "REBASE_REQUIRED",
            ("ROUTE_CURRENTNESS_NOT_CURRENT",),
            worker_id=worker_id,
            cell_id=cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            claim_id=claim_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )

    request_ceiling = route_request.get("cost_ceiling_usd")
    cell_ceiling = cell.get("cost_ceiling_provider_usd", 0.0)
    if request_ceiling is None:
        request_ceiling = cell_ceiling
    if isinstance(request_ceiling, bool) or not isinstance(request_ceiling, (int, float)):
        return _result(
            "ROUTE_BINDING_MISMATCH",
            ("ROUTE_COST_CEILING_INVALID",),
            worker_id=worker_id,
            cell_id=cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            claim_id=claim_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )
    if float(request_ceiling) > float(cell_ceiling):
        return _result(
            "ROUTE_BINDING_MISMATCH",
            ("ROUTE_COST_CEILING_WIDENING",),
            worker_id=worker_id,
            cell_id=cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            claim_id=claim_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )

    route = select_creator_studio_route(route_request, route_candidates)
    if route.get("decision") != "ROUTE_SELECTED" or not route.get("selected_route"):
        return _result(
            "ROUTE_REQUIRED",
            tuple(route.get("reason_codes") or ("NO_ELIGIBLE_ROUTE",)),
            worker_id=worker_id,
            cell_id=cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            claim_id=claim_id,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )

    selected = route["selected_route"]
    route_class = str(selected.get("route_class") or "")
    selected_tier = route_class.split("_", 1)[0]
    if admission_ctx.route_tier != selected_tier:
        return _result(
            "ROUTE_BINDING_MISMATCH",
            ("ADMISSION_ROUTE_TIER_MISMATCH",),
            worker_id=worker_id,
            cell_id=cell_id,
            graph_digest=graph_digest,
            admission_receipt_id=admission.receipt_id,
            claim_id=claim_id,
            route_id=str(selected.get("route_id") or ""),
            route_class=route_class,
            board_revision=board_revision,
            currentness_ref=currentness_ref,
        )

    return _result(
        READY,
        ("ADMISSION_WORKGRAPH_ROUTE_BOUND", "NO_EXECUTION_AUTHORITY_CREATED"),
        worker_id=worker_id,
        cell_id=cell_id,
        graph_digest=graph_digest,
        admission_receipt_id=admission.receipt_id,
        claim_id=claim_id,
        route_id=str(selected.get("route_id") or ""),
        route_class=route_class,
        board_revision=board_revision,
        currentness_ref=currentness_ref,
    )
