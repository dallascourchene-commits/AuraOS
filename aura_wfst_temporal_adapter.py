"""Temporal guard adapter for Aura WFST projections.

Temporal labels are advisory guard inputs. They never mutate active grammar,
grant authority, or apply restored state. A stale or branched observation fails
closed and requests a refresh/re-verification packet.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
from typing import Any, Mapping

from aura_refactor_state_identity import digest
from aura_temporal_persistence import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, TemporalCheckpoint

TEMPORAL_WFST_ADAPTER_VERSION = "AURA_WFST_TEMPORAL_ADAPTER_V1"


class TemporalAspect(str, Enum):
    CURRENT = "TEMP:CURRENT"
    STALE = "TEMP:STALE"
    BRANCH_OFFSET = "TEMP:BRANCH_OFFSET"
    FUTURE = "TEMP:FUTURE"
    UNKNOWN = "TEMP:UNKNOWN"


@dataclass(frozen=True)
class TemporalGuardDecision:
    allowed: bool
    aspect: str
    reason: str
    checkpoint_id: str
    current_checkpoint_id: str
    observed_at: float | None
    evaluated_at: float
    refresh_required: bool
    restoration_council_required: bool
    human_review_required: bool = True
    active_grammar_mutated: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    version: str = TEMPORAL_WFST_ADAPTER_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite_time(value: Any, name: str, *, allow_none: bool = False) -> float | None:
    if value is None and allow_none:
        return None
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


def classify_temporal_state(
    checkpoint: TemporalCheckpoint,
    *,
    observed_at: float | None,
    evaluated_at: float,
    current_checkpoint_id: str = "",
    max_age_seconds: float | None = None,
) -> TemporalGuardDecision:
    """Classify a state observation against an exact checkpoint lineage."""
    if type(checkpoint) is not TemporalCheckpoint:
        raise ValueError("checkpoint must be an exact TemporalCheckpoint")
    observed = _finite_time(observed_at, "observed_at", allow_none=True)
    evaluated = _finite_time(evaluated_at, "evaluated_at")
    assert evaluated is not None
    max_age = _finite_time(max_age_seconds, "max_age_seconds", allow_none=True)

    current_id = str(current_checkpoint_id or "")
    if current_id and current_id != checkpoint.checkpoint_id:
        return TemporalGuardDecision(
            allowed=False,
            aspect=TemporalAspect.BRANCH_OFFSET.value,
            reason="requested state belongs to another checkpoint branch",
            checkpoint_id=checkpoint.checkpoint_id,
            current_checkpoint_id=current_id,
            observed_at=observed,
            evaluated_at=evaluated,
            refresh_required=True,
            restoration_council_required=True,
        )
    if observed is None:
        return TemporalGuardDecision(
            allowed=False,
            aspect=TemporalAspect.UNKNOWN.value,
            reason="state observation time is missing",
            checkpoint_id=checkpoint.checkpoint_id,
            current_checkpoint_id=current_id,
            observed_at=None,
            evaluated_at=evaluated,
            refresh_required=True,
            restoration_council_required=False,
        )
    if observed > evaluated:
        return TemporalGuardDecision(
            allowed=False,
            aspect=TemporalAspect.FUTURE.value,
            reason="state observation is later than evaluation time",
            checkpoint_id=checkpoint.checkpoint_id,
            current_checkpoint_id=current_id,
            observed_at=observed,
            evaluated_at=evaluated,
            refresh_required=True,
            restoration_council_required=True,
        )
    if observed < checkpoint.created_at:
        return TemporalGuardDecision(
            allowed=False,
            aspect=TemporalAspect.STALE.value,
            reason="state observation predates the selected checkpoint",
            checkpoint_id=checkpoint.checkpoint_id,
            current_checkpoint_id=current_id,
            observed_at=observed,
            evaluated_at=evaluated,
            refresh_required=True,
            restoration_council_required=False,
        )
    if max_age is not None and evaluated - observed > max_age:
        return TemporalGuardDecision(
            allowed=False,
            aspect=TemporalAspect.STALE.value,
            reason="state observation exceeded its allowed freshness window",
            checkpoint_id=checkpoint.checkpoint_id,
            current_checkpoint_id=current_id,
            observed_at=observed,
            evaluated_at=evaluated,
            refresh_required=True,
            restoration_council_required=False,
        )
    return TemporalGuardDecision(
        allowed=True,
        aspect=TemporalAspect.CURRENT.value,
        reason="state observation is current for this checkpoint lineage",
        checkpoint_id=checkpoint.checkpoint_id,
        current_checkpoint_id=current_id or checkpoint.checkpoint_id,
        observed_at=observed,
        evaluated_at=evaluated,
        refresh_required=False,
        restoration_council_required=False,
    )


def guard_temporal_action(
    checkpoint: TemporalCheckpoint,
    *,
    action_scope: Mapping[str, Any],
    stored_state: Mapping[str, Any],
    evaluated_at: float,
    current_checkpoint_id: str = "",
    max_age_seconds: float | None = None,
) -> dict[str, Any]:
    """Fail closed when an action is based on stale or branch-offset state."""
    action = dict(action_scope)
    state = dict(stored_state)
    observed_at = state.get("observed_at")
    decision = classify_temporal_state(
        checkpoint,
        observed_at=observed_at,
        evaluated_at=evaluated_at,
        current_checkpoint_id=current_checkpoint_id,
        max_age_seconds=max_age_seconds,
    )
    blockers: list[str] = []
    if not decision.allowed:
        blockers.append(decision.aspect)
    state_aspect = str(state.get("aspect") or "").strip().upper()
    if state_aspect in {"BLOCKED", "HOLD", "DENIED", "CLOSED"}:
        blockers.append(f"ASP:{state_aspect}")
    requested_direction = str(action.get("direction") or action.get("dir") or "")
    stored_direction = str(state.get("direction") or state.get("dir") or "")
    if requested_direction and stored_direction and requested_direction != stored_direction:
        blockers.append("DIR:SCOPE_MISMATCH")

    packet = {
        "ok": not blockers,
        "allowed": not blockers,
        "temporal": decision.to_dict(),
        "action_scope_digest": digest(action, size=16),
        "stored_state_digest": digest(state, size=16),
        "blockers": sorted(set(blockers)),
        "refresh_required": bool(blockers),
        "state_applied": False,
        "active_grammar_mutated": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "version": TEMPORAL_WFST_ADAPTER_VERSION,
    }
    if blockers:
        packet["next_gate"] = (
            "RESTORATION_COUNCIL"
            if decision.restoration_council_required
            else "REFRESH_AND_VERIFY"
        )
    else:
        packet["next_gate"] = "EXISTING_ARENA_GUARDS"
    return packet


__all__ = [
    "TEMPORAL_WFST_ADAPTER_VERSION",
    "TemporalAspect",
    "TemporalGuardDecision",
    "classify_temporal_state",
    "guard_temporal_action",
]
