"""Compact, reconstructable execution state for long slice-leased refactors."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from aura_refactor_state_identity import build_projection, build_sidecar, digest, semantic_sets, verify_sidecar

STATE_LEDGER_VERSION = "AURA_REFACTOR_STATE_LEDGER_V3"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_INVARIANTS = (
    "exact_source_spans_and_hashes_only",
    "no_direct_production_mutation",
    "human_review_required",
    "staged_verifier_gated_changes",
    "complete_history_identity_digest",
    "digest_bound_state_reconstructability",
)


def _dependencies(task: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key in ("depends_on", "after", "prerequisites", "dependency_tasks"):
        value = task.get(key)
        items = [value] if isinstance(value, str) else list(value or []) if isinstance(value, (list, tuple, set)) else []
        for item in items:
            text = str(item or "").strip()
            if text and text not in result:
                result.append(text)
    return result


def _safe_count(value: Any, default: int = 0) -> int:
    if value is None or isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if parsed >= 0 else default


def _repairs(value: Mapping[str, Any] | None) -> dict[str, int]:
    result: dict[str, int] = {}
    for key, item in dict(value or {}).items():
        parsed = _safe_count(item, -1)
        if parsed >= 0:
            result[str(key)] = parsed
    return result


def _inputs(session: Any, repairs: Mapping[str, Any] | None, replans: Any) -> tuple[list[dict[str, Any]], int, dict[str, list[str]], dict[str, int], int]:
    tasks = [dict(item) for item in list(getattr(session, "act_capsules", []) or [])]
    active = _safe_count(getattr(session, "active_task_index", 0), 0)
    dependencies = {str(task.get("task_id") or f"A{index + 1}"): _dependencies(task) for index, task in enumerate(tasks)}
    return tasks, active, dependencies, _repairs(repairs), _safe_count(replans, 0)


@dataclass(frozen=True)
class RefactorStateLedger:
    session_id: str
    plan_phase_hash: str
    objective_hash: str
    active_task_index: int
    task_count: int
    completed_task_ids: tuple[str, ...]
    current_task_id: str
    pending_role: str
    task_dependencies: dict[str, list[str]]
    invariants: tuple[str, ...]
    history_event_count: int
    history_root_digest: str
    last_event_digest: str
    latest_stage_digest: str
    latest_verification_digest: str
    latest_verification_ok: bool | None
    repair_attempts_by_task: dict[str, int]
    council_replan_count: int
    execution_status: str
    last_sequence_number: int = -1
    event_sequence_mode: str = "collection_order_fallback"
    event_store_ref: str = ""
    execution_state_digest: str = ""
    dependency_frontier_digest: str = ""
    assumption_set_digest: str = ""
    unresolved_questions_digest: str = ""
    accepted_decisions_digest: str = ""
    rejected_alternatives_digest: str = ""
    reconstruction_sidecar_digest: str = ""
    version: str = STATE_LEDGER_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False
    production_mutation: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["completed_task_ids"] = list(self.completed_task_ids)
        value["invariants"] = list(self.invariants)
        return value


def _projection(session: Any, repairs: Mapping[str, Any] | None, replans: Any) -> tuple[dict[str, Any], list[dict[str, Any]], int, dict[str, list[str]], dict[str, int], int]:
    tasks, active, dependencies, clean_repairs, clean_replans = _inputs(session, repairs, replans)
    projection = build_projection(session=session, tasks=tasks, active_index=active, dependencies=dependencies, repairs=clean_repairs, council_replan_count=clean_replans)
    return projection, tasks, active, dependencies, clean_repairs, clean_replans


def build_state_sidecar(session: Any, *, repair_attempts_by_task: Mapping[str, Any] | None = None, council_replan_count: Any = 0) -> dict[str, Any]:
    projection, *_rest = _projection(session, repair_attempts_by_task, council_replan_count)
    return build_sidecar(session, projection)


def build_state_ledger(session: Any, *, repair_attempts_by_task: Mapping[str, Any] | None = None, council_replan_count: Any = 0) -> RefactorStateLedger:
    projection, tasks, active, dependencies, repairs, replans = _projection(session, repair_attempts_by_task, council_replan_count)
    sidecar = build_sidecar(session, projection)
    stages = list(getattr(session, "stage_results", []) or [])
    verifications = list(getattr(session, "verification_results", []) or [])
    latest_stage = stages[-1] if stages else {}
    latest_verification = verifications[-1] if verifications else {}
    semantics = semantic_sets(session)
    session_id = str(projection["session_id"])
    return RefactorStateLedger(
        session_id=session_id,
        plan_phase_hash=str(projection["plan_phase_hash"]),
        objective_hash=digest(str(getattr(session, "objective", "") or "")) if getattr(session, "objective", "") else "",
        active_task_index=active,
        task_count=len(tasks),
        completed_task_ids=tuple(projection["completed_task_ids"]),
        current_task_id=str(projection["current_task_id"]),
        pending_role=str(projection["pending_role"]),
        task_dependencies=dependencies,
        invariants=_INVARIANTS,
        history_event_count=int(sidecar["history_event_count"]),
        history_root_digest=str(sidecar["history_root_digest"]),
        last_event_digest=str(sidecar["last_event_digest"]),
        latest_stage_digest=digest(latest_stage) if latest_stage else "",
        latest_verification_digest=digest(latest_verification) if latest_verification else "",
        latest_verification_ok=bool(latest_verification.get("ok")) if isinstance(latest_verification, dict) and "ok" in latest_verification else None,
        repair_attempts_by_task=repairs,
        council_replan_count=replans,
        execution_status=str(projection["execution_status"]),
        last_sequence_number=int(sidecar["last_sequence_number"]),
        event_sequence_mode=str(sidecar["sequence_mode"]),
        event_store_ref=f"aura://refactor-state/{session_id or 'anonymous'}/{sidecar['sidecar_digest']}",
        execution_state_digest=digest(projection),
        dependency_frontier_digest=digest(projection["dependency_frontier"]),
        assumption_set_digest=digest(semantics["assumptions"]),
        unresolved_questions_digest=digest(semantics["unresolved_questions"]),
        accepted_decisions_digest=digest(semantics["accepted_decisions"]),
        rejected_alternatives_digest=digest(semantics["rejected_alternatives"]),
        reconstruction_sidecar_digest=str(sidecar["sidecar_digest"]),
    )


def reconstruct_state_from_ledger(ledger: RefactorStateLedger, sidecar: Mapping[str, Any]) -> dict[str, Any]:
    valid, projection = verify_sidecar(sidecar)
    if not valid:
        raise ValueError("State Ledger sidecar failed digest or history-chain verification")
    checks = (
        str(sidecar.get("sidecar_digest") or "") == ledger.reconstruction_sidecar_digest,
        str(sidecar.get("history_root_digest") or "") == ledger.history_root_digest,
        int(sidecar.get("history_event_count") or 0) == ledger.history_event_count,
        str(projection.get("session_id") or "") == ledger.session_id,
        str(projection.get("plan_phase_hash") or "") == ledger.plan_phase_hash,
        digest(projection) == ledger.execution_state_digest,
    )
    if not all(checks):
        raise ValueError("State Ledger and sidecar identities do not match")
    return projection


__all__ = ["RefactorStateLedger", "STATE_LEDGER_VERSION", "_dependencies", "_inputs", "build_state_ledger", "build_state_sidecar", "reconstruct_state_from_ledger"]
