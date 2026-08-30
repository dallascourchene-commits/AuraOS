"""Deterministic Aura Arena WorkGraph / continual-work harness.

This module is deliberately control-plane-only:
- it projects machine-readable worker/cell/claim state;
- enforces dependency, capability, currentness and claim-collision gates;
- compiles compare-and-swap transitions for claim/release/complete/add-cell;
- recovers expired coordination claims without treating them as runtime liveness;
- emits wake/delivery *intent* only when changed state exposes eligible work.

It does NOT wake ChatGPT, call providers, prove a worker is running, or widen authority.
An external Arena/Resident adapter must persist transitions and deliver a real turn.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

WORKGRAPH_SCHEMA = "AuraArenaWorkGraphStateV1"
PROJECTION_SCHEMA = "AuraArenaWorkGraphProjectionV1"
RECEIPT_SCHEMA = "AuraArenaWorkGraphTransitionReceiptV1"
WAKE_SCHEMA = "AuraArenaWorkGraphWakeIntentV1"

CELL_STATES = frozenset({"OPEN", "CLAIMED", "BLOCKED", "COMPLETE", "SUPERSEDED"})
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
ACTIONS = frozenset({"CLAIM", "RELEASE", "COMPLETE", "BLOCK", "REOPEN", "ADD_CELL"})
AUTONOMOUS_EFFECT_CEILING = "D0"


class WorkGraphError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _text(value: Any, *, code: str) -> str:
    out = str(value or "").strip()
    if not out:
        raise WorkGraphError(code)
    return out


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WorkGraphError("NONCANONICAL_STATE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _sorted_unique_text(values: Any, *, code: str) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str) or not isinstance(values, Sequence):
        raise WorkGraphError(code)
    out = [_text(item, code=code) for item in values]
    if len(set(out)) != len(out):
        raise WorkGraphError(code)
    return sorted(out)


def _normalize_worker(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise WorkGraphError("WORKER_NOT_OBJECT")
    worker_id = _text(raw.get("worker_id"), code="WORKER_ID_REQUIRED")
    return {
        "worker_id": worker_id,
        "capabilities": _sorted_unique_text(raw.get("capabilities") or [], code="WORKER_CAPABILITIES_INVALID"),
        "currentness_ref": _text(raw.get("currentness_ref"), code="WORKER_CURRENTNESS_REQUIRED"),
        "joined": raw.get("joined") is True,
        "effect_ceiling": str(raw.get("effect_ceiling") or AUTONOMOUS_EFFECT_CEILING).strip().upper(),
        "eligible": raw.get("eligible", True) is True,
    }


def _normalize_cell(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise WorkGraphError("CELL_NOT_OBJECT")
    cell_id = _text(raw.get("cell_id"), code="CELL_ID_REQUIRED")
    state = str(raw.get("state") or "").strip().upper()
    if state not in CELL_STATES:
        raise WorkGraphError("CELL_STATE_INVALID")
    priority = str(raw.get("priority") or "P4").strip().upper()
    if priority not in PRIORITY_ORDER:
        raise WorkGraphError("CELL_PRIORITY_INVALID")
    effect_class = str(raw.get("effect_class") or AUTONOMOUS_EFFECT_CEILING).strip().upper()
    reuse_value = raw.get("reuse_value", 0)
    estimated_effort = raw.get("estimated_effort", 1)
    if isinstance(reuse_value, bool) or not isinstance(reuse_value, int) or reuse_value < 0:
        raise WorkGraphError("CELL_REUSE_VALUE_INVALID")
    if isinstance(estimated_effort, bool) or not isinstance(estimated_effort, int) or estimated_effort < 1:
        raise WorkGraphError("CELL_EFFORT_INVALID")
    return {
        "cell_id": cell_id,
        "state": state,
        "priority": priority,
        "dependencies": _sorted_unique_text(raw.get("dependencies") or [], code="CELL_DEPENDENCIES_INVALID"),
        "required_capabilities": _sorted_unique_text(
            raw.get("required_capabilities") or [], code="CELL_CAPABILITIES_INVALID"
        ),
        "effect_class": effect_class,
        "reuse_value": reuse_value,
        "estimated_effort": estimated_effort,
        "currentness_ref": str(raw.get("currentness_ref") or "").strip(),
        "reopen_trigger": str(raw.get("reopen_trigger") or "").strip(),
    }


def _normalize_claim(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise WorkGraphError("CLAIM_NOT_OBJECT")
    claimed_at_ms = raw.get("claimed_at_ms")
    lease_expires_at_ms = raw.get("lease_expires_at_ms")
    for value in (claimed_at_ms, lease_expires_at_ms):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise WorkGraphError("CLAIM_TIME_INVALID")
    if lease_expires_at_ms <= claimed_at_ms:
        raise WorkGraphError("CLAIM_LEASE_INVALID")
    return {
        "claim_id": _text(raw.get("claim_id"), code="CLAIM_ID_REQUIRED"),
        "cell_id": _text(raw.get("cell_id"), code="CLAIM_CELL_REQUIRED"),
        "worker_id": _text(raw.get("worker_id"), code="CLAIM_WORKER_REQUIRED"),
        "claimed_at_ms": claimed_at_ms,
        "lease_expires_at_ms": lease_expires_at_ms,
        "active": raw.get("active", True) is True,
        "generation": int(raw.get("generation", 1)),
    }


def normalize_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or raw.get("schema") != WORKGRAPH_SCHEMA:
        raise WorkGraphError("WORKGRAPH_SCHEMA_MISMATCH")
    project_id = _text(raw.get("project_id"), code="PROJECT_ID_REQUIRED")
    mission_ref = _text(raw.get("mission_ref"), code="MISSION_REF_REQUIRED")
    currentness_ref = _text(raw.get("currentness_ref"), code="CURRENTNESS_REF_REQUIRED")
    workers = [_normalize_worker(item) for item in raw.get("workers", [])]
    cells = [_normalize_cell(item) for item in raw.get("cells", [])]
    claims = [_normalize_claim(item) for item in raw.get("claims", [])]

    def _unique(rows: Sequence[Mapping[str, Any]], key: str, code: str) -> None:
        values = [row[key] for row in rows]
        if len(values) != len(set(values)):
            raise WorkGraphError(code)

    _unique(workers, "worker_id", "WORKER_ID_DUPLICATE")
    _unique(cells, "cell_id", "CELL_ID_DUPLICATE")
    _unique(claims, "claim_id", "CLAIM_ID_DUPLICATE")

    worker_ids = {row["worker_id"] for row in workers}
    cell_ids = {row["cell_id"] for row in cells}
    for cell in cells:
        if cell["cell_id"] in cell["dependencies"]:
            raise WorkGraphError("CELL_SELF_DEPENDENCY")
        unknown = set(cell["dependencies"]) - cell_ids
        if unknown:
            raise WorkGraphError("CELL_DEPENDENCY_UNKNOWN")
    for claim in claims:
        if claim["worker_id"] not in worker_ids:
            raise WorkGraphError("CLAIM_WORKER_UNKNOWN")
        if claim["cell_id"] not in cell_ids:
            raise WorkGraphError("CLAIM_CELL_UNKNOWN")

    _assert_acyclic(cells)
    return {
        "schema": WORKGRAPH_SCHEMA,
        "project_id": project_id,
        "mission_ref": mission_ref,
        "currentness_ref": currentness_ref,
        "workers": sorted(workers, key=lambda item: item["worker_id"]),
        "cells": sorted(cells, key=lambda item: item["cell_id"]),
        "claims": sorted(claims, key=lambda item: item["claim_id"]),
    }


def _assert_acyclic(cells: Sequence[Mapping[str, Any]]) -> None:
    graph = {cell["cell_id"]: tuple(cell["dependencies"]) for cell in cells}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise WorkGraphError("CELL_DEPENDENCY_CYCLE")
        visiting.add(node)
        for dep in graph[node]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)


def state_digest(state: Mapping[str, Any]) -> str:
    normalized = normalize_state(state)
    return _digest("AURA_ARENA_WORKGRAPH_STATE_V1", normalized)


def project_workgraph(state: Mapping[str, Any], *, now_ms: int) -> dict[str, Any]:
    if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
        raise WorkGraphError("NOW_INVALID")
    s = normalize_state(state)
    cells = {item["cell_id"]: item for item in s["cells"]}
    completed = {cid for cid, cell in cells.items() if cell["state"] == "COMPLETE"}

    active_claims: dict[str, list[dict[str, Any]]] = {}
    stale_claims: list[dict[str, Any]] = []
    for claim in s["claims"]:
        if not claim["active"]:
            continue
        if now_ms >= claim["lease_expires_at_ms"]:
            stale_claims.append({**claim, "recovery_code": "STALE_CLAIM_RECOVERED"})
            continue
        active_claims.setdefault(claim["cell_id"], []).append(claim)

    collisions = {
        cell_id: rows
        for cell_id, rows in active_claims.items()
        if len(rows) > 1
    }

    rows: list[dict[str, Any]] = []
    for cell_id in sorted(cells):
        cell = cells[cell_id]
        unmet = sorted(set(cell["dependencies"]) - completed)
        claims = sorted(active_claims.get(cell_id, []), key=lambda item: item["claim_id"])
        reasons: list[str] = []
        effective_state = cell["state"]

        if cell_id in collisions:
            effective_state = "BLOCKED"
            reasons.append("ACTIVE_CLAIM_COLLISION_FAIL_CLOSED")
        elif cell["state"] in {"COMPLETE", "SUPERSEDED"}:
            effective_state = cell["state"]
        elif unmet:
            effective_state = "BLOCKED"
            reasons.append("DEPENDENCY_INCOMPLETE")
        elif claims:
            effective_state = "CLAIMED"
        elif cell["state"] == "BLOCKED":
            effective_state = "BLOCKED"
            reasons.append("DECLARED_BLOCKED")
        else:
            effective_state = "OPEN"

        rows.append({
            **cell,
            "effective_state": effective_state,
            "unmet_dependencies": unmet,
            "active_claims": claims,
            "eligible_for_selection": effective_state == "OPEN",
            "projection_reasons": reasons,
            "runtime_execution_proven": False,
        })

    stable_basis = {
        "project_id": s["project_id"],
        "mission_ref": s["mission_ref"],
        "currentness_ref": s["currentness_ref"],
        "workers": s["workers"],
        "cells": rows,
        "stale_claims": sorted(stale_claims, key=lambda item: item["claim_id"]),
        "collision_cell_ids": sorted(collisions),
    }
    # Wall-clock movement alone must not wake cognition. The digest changes only
    # when projected consequence state changes (for example, a lease becomes stale).
    graph_digest = _digest("AURA_ARENA_WORKGRAPH_PROJECTION_V1", stable_basis)
    return {
        "schema": PROJECTION_SCHEMA,
        **stable_basis,
        "now_ms": now_ms,
        "graph_digest": graph_digest,
        "advisory_only": True,
        "provider_calls": 0,
        "background_execution_proven": False,
    }


def _worker(projection: Mapping[str, Any], worker_id: str) -> dict[str, Any]:
    for worker in projection.get("workers", []):
        if worker.get("worker_id") == worker_id:
            return dict(worker)
    raise WorkGraphError("WORKER_NOT_JOINED")


def eligible_cells(projection: Mapping[str, Any], *, worker_id: str) -> list[dict[str, Any]]:
    worker = _worker(projection, worker_id)
    if not worker["joined"] or not worker["eligible"]:
        return []
    if worker["currentness_ref"] != projection.get("currentness_ref"):
        return []
    if worker["effect_ceiling"] != AUTONOMOUS_EFFECT_CEILING:
        return []
    capabilities = set(worker["capabilities"])
    rows: list[dict[str, Any]] = []
    for cell in projection.get("cells", []):
        if not cell.get("eligible_for_selection"):
            continue
        if cell.get("effect_class") != AUTONOMOUS_EFFECT_CEILING:
            continue
        if cell.get("currentness_ref") and cell["currentness_ref"] != projection.get("currentness_ref"):
            continue
        if not set(cell.get("required_capabilities", [])).issubset(capabilities):
            continue
        rows.append(dict(cell))
    rows.sort(
        key=lambda item: (
            PRIORITY_ORDER[item["priority"]],
            -item["reuse_value"],
            item["estimated_effort"],
            item["cell_id"],
        )
    )
    return rows


def continuity_tick(
    projection: Mapping[str, Any],
    *,
    worker_id: str,
    previous_graph_digest: str | None = None,
) -> dict[str, Any]:
    if projection.get("schema") != PROJECTION_SCHEMA:
        raise WorkGraphError("PROJECTION_SCHEMA_MISMATCH")
    worker = _worker(projection, worker_id)
    current_digest = str(projection.get("graph_digest") or "")
    if previous_graph_digest and previous_graph_digest == current_digest:
        return _wake_intent(
            worker_id=worker_id,
            graph_digest=current_digest,
            disposition="NO_CHANGE_NO_MODEL",
            delivery_required=False,
        )
    if worker["currentness_ref"] != projection.get("currentness_ref"):
        return _wake_intent(
            worker_id=worker_id,
            graph_digest=current_digest,
            disposition="SUPERSEDED_CURRENTNESS",
            delivery_required=False,
        )
    own_claims = [
        cell for cell in projection.get("cells", [])
        if any(c.get("worker_id") == worker_id for c in cell.get("active_claims", []))
    ]
    if own_claims:
        return _wake_intent(
            worker_id=worker_id,
            graph_digest=current_digest,
            disposition="CURRENT_CLAIM_ACTIVE",
            delivery_required=False,
            selected_cell_id=sorted(c["cell_id"] for c in own_claims)[0],
        )
    eligible = eligible_cells(projection, worker_id=worker_id)
    if not eligible:
        return _wake_intent(
            worker_id=worker_id,
            graph_digest=current_digest,
            disposition="NO_ELIGIBLE_WORK_AFTER_REVIEW",
            delivery_required=False,
        )
    selected = eligible[0]
    return _wake_intent(
        worker_id=worker_id,
        graph_digest=current_digest,
        disposition="SELECT_NEXT_WORK",
        delivery_required=True,
        selected_cell_id=selected["cell_id"],
    )


def _wake_intent(
    *,
    worker_id: str,
    graph_digest: str,
    disposition: str,
    delivery_required: bool,
    selected_cell_id: str = "",
) -> dict[str, Any]:
    return {
        "schema": WAKE_SCHEMA,
        "worker_id": worker_id,
        "basis_graph_digest": graph_digest,
        "disposition": disposition,
        "selected_cell_id": selected_cell_id,
        "delivery_required": delivery_required,
        "requires_external_authorized_turn_delivery": delivery_required,
        "model_call_required_for_scheduler_tick": False,
        "runtime_execution_proven": False,
    }


def apply_action(
    state: Mapping[str, Any],
    *,
    action: Mapping[str, Any],
    now_ms: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply one compare-and-swap coordination transition.

    This is a deterministic reference transaction. A production adapter must persist
    the returned state atomically under the same basis digest.
    """
    if not isinstance(action, Mapping):
        raise WorkGraphError("ACTION_NOT_OBJECT")
    projection = project_workgraph(state, now_ms=now_ms)
    basis = _text(action.get("basis_graph_digest"), code="ACTION_BASIS_REQUIRED")
    if basis != projection["graph_digest"]:
        raise WorkGraphError("STALE_GRAPH_BASIS")
    kind = str(action.get("action") or "").strip().upper()
    if kind not in ACTIONS:
        raise WorkGraphError("ACTION_INVALID")

    s = normalize_state(state)
    next_state = deepcopy(s)
    cell_id = str(action.get("cell_id") or "").strip()
    worker_id = str(action.get("worker_id") or "").strip()
    before_digest = state_digest(s)

    if not worker_id or worker_id not in {w["worker_id"] for w in next_state["workers"]}:
        raise WorkGraphError("ACTION_WORKER_UNKNOWN")
    acting_worker = _worker(projection, worker_id)
    if not acting_worker["joined"] or not acting_worker["eligible"]:
        raise WorkGraphError("ACTION_WORKER_NOT_ADMITTED")
    if acting_worker["currentness_ref"] != projection["currentness_ref"]:
        raise WorkGraphError("ACTION_WORKER_STALE_CURRENTNESS")
    if acting_worker["effect_ceiling"] != AUTONOMOUS_EFFECT_CEILING:
        raise WorkGraphError("ACTION_EFFECT_CEILING_EXCEEDED")

    if kind == "ADD_CELL":
        new_cell = _normalize_cell(action.get("cell") or {})
        if any(c["cell_id"] == new_cell["cell_id"] for c in next_state["cells"]):
            raise WorkGraphError("CELL_ID_DUPLICATE")
        next_state["cells"].append(new_cell)
        next_state = normalize_state(next_state)
        cell_id = new_cell["cell_id"]
    else:
        if not cell_id or cell_id not in {c["cell_id"] for c in next_state["cells"]}:
            raise WorkGraphError("ACTION_CELL_UNKNOWN")
        current_cell = next(c for c in projection["cells"] if c["cell_id"] == cell_id)

        if kind == "CLAIM":
            if current_cell["effective_state"] != "OPEN":
                raise WorkGraphError("CELL_NOT_ELIGIBLE")
            if cell_id not in {c["cell_id"] for c in eligible_cells(projection, worker_id=worker_id)}:
                raise WorkGraphError("WORKER_NOT_ELIGIBLE_FOR_CELL")
            lease_ms = action.get("lease_ms", 600_000)
            if isinstance(lease_ms, bool) or not isinstance(lease_ms, int) or lease_ms <= 0:
                raise WorkGraphError("CLAIM_LEASE_INVALID")
            claim_id = _digest(
                "AURA_ARENA_WORKGRAPH_CLAIM_V1",
                {
                    "basis": basis,
                    "cell_id": cell_id,
                    "worker_id": worker_id,
                    "claimed_at_ms": now_ms,
                },
            )
            next_state["claims"].append({
                "claim_id": claim_id,
                "cell_id": cell_id,
                "worker_id": worker_id,
                "claimed_at_ms": now_ms,
                "lease_expires_at_ms": now_ms + lease_ms,
                "active": True,
                "generation": 1,
            })
            for cell in next_state["cells"]:
                if cell["cell_id"] == cell_id:
                    cell["state"] = "CLAIMED"
                    break
        elif kind in {"RELEASE", "COMPLETE", "BLOCK"}:
            if current_cell["effective_state"] != "CLAIMED":
                raise WorkGraphError("CELL_NOT_EXCLUSIVELY_CLAIMED")
            owned = [
                c for c in next_state["claims"]
                if c["active"] and c["cell_id"] == cell_id and c["worker_id"] == worker_id
                and now_ms < c["lease_expires_at_ms"]
            ]
            if not owned:
                raise WorkGraphError("ACTIVE_OWNED_CLAIM_REQUIRED")
            for claim in next_state["claims"]:
                if claim["active"] and claim["cell_id"] == cell_id and claim["worker_id"] == worker_id:
                    claim["active"] = False
            target = {"RELEASE": "OPEN", "COMPLETE": "COMPLETE", "BLOCK": "BLOCKED"}[kind]
            for cell in next_state["cells"]:
                if cell["cell_id"] == cell_id:
                    cell["state"] = target
                    if kind == "BLOCK":
                        cell["reopen_trigger"] = str(action.get("reopen_trigger") or cell["reopen_trigger"]).strip()
                    break
        elif kind == "REOPEN":
            for cell in next_state["cells"]:
                if cell["cell_id"] == cell_id:
                    if cell["state"] not in {"BLOCKED", "COMPLETE", "SUPERSEDED"}:
                        raise WorkGraphError("CELL_NOT_REOPENABLE")
                    cell["state"] = "OPEN"
                    break

        next_state = normalize_state(next_state)

    after_projection = project_workgraph(next_state, now_ms=now_ms)
    receipt_body = {
        "action": kind,
        "project_id": next_state["project_id"],
        "worker_id": worker_id,
        "cell_id": cell_id,
        "basis_graph_digest": basis,
        "before_state_digest": before_digest,
        "after_state_digest": state_digest(next_state),
        "after_graph_digest": after_projection["graph_digest"],
        "now_ms": now_ms,
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        **receipt_body,
        "receipt_digest": _digest("AURA_ARENA_WORKGRAPH_TRANSITION_RECEIPT_V1", receipt_body),
        "runtime_execution_proven": False,
        "provider_calls": 0,
    }
    return next_state, receipt
