"""Fail-closed Arena admission gate for Creator Studio/AuraOS workers.

This module intentionally does not execute project work or grant authority. It
only answers whether a worker has completed the minimum Arena-first orientation
contract before *substantive* work is allowed. Orientation and admission-repair
operations remain available while the gate is incomplete.

The contract is derived from CS-HARNESS-001:
- enter the project Arena and resolve Front Door + collaboration surface;
- bind Mission/Purpose (and any active temporary mission override);
- bind current authoritative project/head state;
- record JOIN identity/capabilities/effect ceiling;
- claim exactly one bounded work cell unless acting as an explicitly named
  reducer/coordinator/verifier;
- observe sibling claim/dependency state;
- select the lowest-cost lawful route before escalation.

A document or claim record is coordination evidence, not execution authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Iterable

SCHEMA_VERSION = "ArenaAdmissionV1"
ERROR_CODE = "ARENA_ADMISSION_REQUIRED"


class ActionClass(str, Enum):
    ORIENT = "ORIENT"
    REPAIR_ADMISSION = "REPAIR_ADMISSION"
    SUBSTANTIVE = "SUBSTANTIVE"


class AdmissionRole(str, Enum):
    WORKER = "worker"
    REDUCER = "reducer"
    COORDINATOR = "coordinator"
    VERIFIER = "verifier"


_ALLOWED_CLAIMLESS_ROLES = {
    AdmissionRole.REDUCER.value,
    AdmissionRole.COORDINATOR.value,
    AdmissionRole.VERIFIER.value,
}
_ALLOWED_ROUTES = {f"R{i}" for i in range(7)}


@dataclass(frozen=True)
class ArenaAdmissionContext:
    worker_id: str | None = None
    role: str = AdmissionRole.WORKER.value
    capabilities: tuple[str, ...] = ()
    effect_ceiling: str | None = None

    project_coordinate: str | None = None
    front_door_ref: str | None = None
    collab_board_ref: str | None = None

    mission_ref: str | None = None
    purpose_ref: str | None = None
    temporary_mission_active: bool = False
    temporary_mission_ref: str | None = None

    authoritative_head_ref: str | None = None
    currentness_current: bool = False

    join_record_ref: str | None = None
    claimed_cells: tuple[str, ...] = ()

    sibling_state_ref: str | None = None
    sibling_state_digest: str | None = None

    route_tier: str | None = None
    route_reason: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdmissionDecision:
    schema: str
    allowed: bool
    code: str
    action_class: str
    worker_id: str | None
    role: str
    missing: tuple[str, ...]
    satisfied: tuple[str, ...]
    receipt_id: str
    repair_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["missing"] = list(self.missing)
        result["satisfied"] = list(self.satisfied)
        result["repair_actions"] = list(self.repair_actions)
        return result


class ArenaAdmissionError(RuntimeError):
    def __init__(self, decision: AdmissionDecision) -> None:
        self.decision = decision
        detail = ", ".join(decision.missing) if decision.missing else "unknown"
        super().__init__(f"{ERROR_CODE}: {detail}")


def _nonempty(value: str | None) -> bool:
    return bool(value and value.strip())


def _canonical_digest(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _normalize_cells(cells: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({cell.strip() for cell in cells if cell and cell.strip()}))


def _requirement_state(ctx: ArenaAdmissionContext) -> dict[str, bool]:
    role = (ctx.role or "").strip().lower()
    cells = _normalize_cells(ctx.claimed_cells)
    claim_ok = len(cells) == 1 or (len(cells) == 0 and role in _ALLOWED_CLAIMLESS_ROLES)

    return {
        "ARENA_ENTERED": all(
            _nonempty(v)
            for v in (ctx.project_coordinate, ctx.front_door_ref, ctx.collab_board_ref)
        ),
        "MISSION_BOUND": (
            _nonempty(ctx.mission_ref)
            and _nonempty(ctx.purpose_ref)
            and (
                not ctx.temporary_mission_active
                or _nonempty(ctx.temporary_mission_ref)
            )
        ),
        "CURRENTNESS_BOUND": _nonempty(ctx.authoritative_head_ref) and ctx.currentness_current,
        "JOIN_RECORDED": (
            _nonempty(ctx.worker_id)
            and bool(tuple(c for c in ctx.capabilities if c and c.strip()))
            and _nonempty(ctx.effect_ceiling)
            and _nonempty(ctx.join_record_ref)
        ),
        "CLAIM_BOUND": claim_ok,
        "SIBLING_STATE_SEEN": _nonempty(ctx.sibling_state_ref)
        and _nonempty(ctx.sibling_state_digest),
        "ROUTE_BOUND": (
            _nonempty(ctx.route_tier)
            and ctx.route_tier in _ALLOWED_ROUTES
            and _nonempty(ctx.route_reason)
        ),
    }


_REPAIR_ACTIONS = {
    "ARENA_ENTERED": "resolve project coordinate, Front Door, and collaboration board",
    "MISSION_BOUND": "bind Mission/Purpose and any active temporary mission override",
    "CURRENTNESS_BOUND": "refresh authoritative head/source currentness",
    "JOIN_RECORDED": "record WorkerID, capabilities, effect ceiling, and JOIN receipt",
    "CLAIM_BOUND": "claim exactly one bounded eligible cell or use an explicit reducer/coordinator/verifier role",
    "SIBLING_STATE_SEEN": "read and digest active sibling claims/dependencies",
    "ROUTE_BOUND": "select and explain the lowest-cost lawful R0-R6 route",
}


def evaluate_admission(
    ctx: ArenaAdmissionContext,
    action_class: ActionClass | str = ActionClass.SUBSTANTIVE,
) -> AdmissionDecision:
    try:
        action = ActionClass(action_class)
    except ValueError as exc:
        raise ValueError(f"unknown action class: {action_class!r}") from exc

    state = _requirement_state(ctx)
    missing = tuple(name for name, ok in state.items() if not ok)
    satisfied = tuple(name for name, ok in state.items() if ok)

    # Orientation and admission repair are always allowed. They may only repair
    # the gate; they do not imply substantive project authority.
    allowed = action in {ActionClass.ORIENT, ActionClass.REPAIR_ADMISSION} or not missing
    code = "ADMITTED" if not missing else ERROR_CODE

    digest_payload = {
        "schema": SCHEMA_VERSION,
        "action_class": action.value,
        "worker_id": ctx.worker_id,
        "role": ctx.role,
        "requirements": state,
        "project_coordinate": ctx.project_coordinate,
        "front_door_ref": ctx.front_door_ref,
        "collab_board_ref": ctx.collab_board_ref,
        "mission_ref": ctx.mission_ref,
        "purpose_ref": ctx.purpose_ref,
        "temporary_mission_active": ctx.temporary_mission_active,
        "temporary_mission_ref": ctx.temporary_mission_ref,
        "authoritative_head_ref": ctx.authoritative_head_ref,
        "currentness_current": ctx.currentness_current,
        "join_record_ref": ctx.join_record_ref,
        "claimed_cells": _normalize_cells(ctx.claimed_cells),
        "sibling_state_ref": ctx.sibling_state_ref,
        "sibling_state_digest": ctx.sibling_state_digest,
        "route_tier": ctx.route_tier,
        "route_reason": ctx.route_reason,
        "effect_ceiling": ctx.effect_ceiling,
    }
    receipt_id = f"arena-admission-{_canonical_digest(digest_payload)[:20]}"

    return AdmissionDecision(
        schema=SCHEMA_VERSION,
        allowed=allowed,
        code=code,
        action_class=action.value,
        worker_id=ctx.worker_id,
        role=ctx.role,
        missing=missing,
        satisfied=satisfied,
        receipt_id=receipt_id,
        repair_actions=tuple(_REPAIR_ACTIONS[name] for name in missing),
    )


def assert_substantive_allowed(ctx: ArenaAdmissionContext) -> AdmissionDecision:
    decision = evaluate_admission(ctx, ActionClass.SUBSTANTIVE)
    if not decision.allowed:
        raise ArenaAdmissionError(decision)
    return decision


def orientation_receipt(ctx: ArenaAdmissionContext) -> dict[str, Any]:
    """Return a compact deterministic admission/orientation receipt.

    This helper is safe to call before admission. It is a state projection,
    never evidence that any project effect ran.
    """

    decision = evaluate_admission(ctx, ActionClass.ORIENT)
    return {
        **decision.to_dict(),
        "substantive_allowed": not decision.missing,
        "execution_claim": False,
        "authority_note": "coordination/admission state only; no project effect authority is created",
    }
