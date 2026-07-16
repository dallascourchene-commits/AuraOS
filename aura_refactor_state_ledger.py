"""Compact state ledger for long, slice-leased refactors.

The ledger replaces conversation replay with a bounded execution-state packet. It
preserves plan identity, completed/current tasks, dependencies, invariants,
verification, escalation state, and a digest chain over the complete event history
while excluding full prompts, diffs, and logs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

STATE_LEDGER_VERSION = "AURA_REFACTOR_STATE_LEDGER_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def _normalize(value: Any) -> Any:
    """Return a deterministic JSON-safe projection for evidence hashing."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return {"__nonfinite_float__": repr(value)}
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        normalized = [_normalize(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    try:
        text = str(value)
    except Exception:
        text = "<unprintable>"
    return {"__type__": f"{type(value).__module__}.{type(value).__qualname__}", "__str__": text}


def _canonical(value: Any) -> str:
    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any, *, size: int = 12) -> str:
    return hashlib.blake2b(_canonical(value).encode("utf-8"), digest_size=size).hexdigest()


def _tokens(value: Any) -> int:
    return (len(_canonical(value).encode("utf-8")) + 3) // 4


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


def _history_events(session: Any) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    sources = (
        ("turn", list(getattr(session, "turns", []) or [])),
        ("stage", list(getattr(session, "stage_results", []) or [])),
        ("verification", list(getattr(session, "verification_results", []) or [])),
    )
    sequence = 0
    for kind, items in sources:
        for item in items:
            events.append({"sequence": sequence, "kind": kind, "payload": _normalize(item)})
            sequence += 1
    return events


def _history_identity(session_id: str, events: list[dict[str, Any]]) -> tuple[int, str, str]:
    previous = _digest({"session_id": session_id, "root": "GENESIS"})
    last_event_digest = ""
    for index, event in enumerate(events):
        last_event_digest = _digest(event)
        previous = _digest(
            {
                "session_id": session_id,
                "sequence": index,
                "previous_digest": previous,
                "event_digest": last_event_digest,
            }
        )
    return len(events), previous, last_event_digest


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
    version: str = STATE_LEDGER_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False
    production_mutation: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["completed_task_ids"] = list(self.completed_task_ids)
        data["invariants"] = list(self.invariants)
        return data


def build_state_ledger(
    session: Any,
    *,
    repair_attempts_by_task: dict[str, int] | None = None,
    council_replan_count: int = 0,
) -> RefactorStateLedger:
    tasks = [dict(item) for item in list(getattr(session, "act_capsules", []) or [])]
    active_index = int(getattr(session, "active_task_index", 0) or 0)
    completed = tuple(str(task.get("task_id") or f"A{index + 1}") for index, task in enumerate(tasks[:active_index]))
    current = ""
    if 0 <= active_index < len(tasks):
        current = str(tasks[active_index].get("task_id") or f"A{active_index + 1}")
    dependencies = {
        str(task.get("task_id") or f"A{index + 1}"): _dependencies(task)
        for index, task in enumerate(tasks)
    }
    pending = getattr(session, "pending_turn", None)
    stage_results = list(getattr(session, "stage_results", []) or [])
    verification_results = list(getattr(session, "verification_results", []) or [])
    latest_stage = stage_results[-1] if stage_results else {}
    latest_verification = verification_results[-1] if verification_results else {}
    objective = str(getattr(session, "objective", "") or "")
    session_id = str(getattr(session, "session_id", "") or "")
    history_count, history_root, last_event = _history_identity(session_id, _history_events(session))
    safe_repairs: dict[str, int] = {}
    for key, value in dict(repair_attempts_by_task or {}).items():
        if isinstance(value, bool):
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if parsed >= 0:
            safe_repairs[str(key)] = parsed
    return RefactorStateLedger(
        session_id=session_id,
        plan_phase_hash=str(getattr(session, "plan_phase_hash", "") or ""),
        objective_hash=_digest(objective) if objective else "",
        active_task_index=active_index,
        task_count=len(tasks),
        completed_task_ids=completed,
        current_task_id=current,
        pending_role=str(getattr(pending, "role", "") or ""),
        task_dependencies=dependencies,
        invariants=(
            "exact_source_spans_and_hashes_only",
            "no_direct_production_mutation",
            "human_review_required",
            "staged_verifier_gated_changes",
            "complete_history_identity_digest",
        ),
        history_event_count=history_count,
        history_root_digest=history_root,
        last_event_digest=last_event,
        latest_stage_digest=_digest(latest_stage) if latest_stage else "",
        latest_verification_digest=_digest(latest_verification) if latest_verification else "",
        latest_verification_ok=(
            bool(latest_verification.get("ok"))
            if isinstance(latest_verification, dict) and "ok" in latest_verification
            else None
        ),
        repair_attempts_by_task=safe_repairs,
        council_replan_count=max(0, int(council_replan_count)),
        execution_status=str(getattr(session, "status", "") or ""),
    )


def measure_state_preservation(session: Any, ledger: RefactorStateLedger) -> dict[str, Any]:
    tasks = [dict(item) for item in list(getattr(session, "act_capsules", []) or [])]
    active_index = int(getattr(session, "active_task_index", 0) or 0)
    expected_completed = [
        str(task.get("task_id") or f"A{index + 1}") for index, task in enumerate(tasks[:active_index])
    ]
    expected_current = (
        str(tasks[active_index].get("task_id") or f"A{active_index + 1}")
        if 0 <= active_index < len(tasks)
        else ""
    )
    history_payload = {
        "turns": list(getattr(session, "turns", []) or []),
        "stage_results": list(getattr(session, "stage_results", []) or []),
        "verification_results": list(getattr(session, "verification_results", []) or []),
    }
    expected_count, expected_root, expected_last = _history_identity(ledger.session_id, _history_events(session))
    checks = {
        "plan_identity": ledger.plan_phase_hash == str(getattr(session, "plan_phase_hash", "") or ""),
        "task_count": ledger.task_count == len(tasks),
        "completed_tasks": list(ledger.completed_task_ids) == expected_completed,
        "current_task": ledger.current_task_id == expected_current,
        "dependency_map": ledger.task_dependencies == {
            str(task.get("task_id") or f"A{index + 1}"): _dependencies(task)
            for index, task in enumerate(tasks)
        },
        "history_event_count": ledger.history_event_count == expected_count,
        "history_root_identity": ledger.history_root_digest == expected_root,
        "last_event_identity": ledger.last_event_digest == expected_last,
        "authority_invariants": {
            "exact_source_spans_and_hashes_only",
            "no_direct_production_mutation",
            "human_review_required",
            "staged_verifier_gated_changes",
            "complete_history_identity_digest",
        }.issubset(set(ledger.invariants)),
    }
    matched = sum(1 for value in checks.values() if value)
    score = matched / len(checks) if checks else 1.0
    ledger_payload = ledger.to_dict()
    return {
        "state_preservation_score": round(score, 4),
        "context_drift_score": round(1.0 - score, 4),
        "checks": checks,
        "state_ledger_tokens": _tokens(ledger_payload),
        "full_history_tokens": _tokens(history_payload),
        "history_avoided_tokens": max(0, _tokens(history_payload) - _tokens(ledger_payload)),
        "ledger_to_history_ratio": round(_tokens(ledger_payload) / max(1, _tokens(history_payload)), 4),
        "ledger_digest": _digest(ledger_payload),
        "history_digest": _digest(history_payload),
        "history_root_digest": ledger.history_root_digest,
        "measurement_classes": {
            "state_preservation_score": "DERIVED_DETERMINISTIC_FACT_AND_HISTORY_MATCH",
            "context_drift_score": "DERIVED_ONE_MINUS_STATE_PRESERVATION",
            "state_ledger_tokens": "ESTIMATED_CHAR4_PROXY",
            "full_history_tokens": "ESTIMATED_CHAR4_PROXY",
        },
    }


def bounded_state_ledger_text(ledger: RefactorStateLedger, max_tokens: int = 480) -> str:
    payload = ledger.to_dict()
    text = _canonical(payload)
    if _tokens(payload) <= max_tokens:
        return text
    compact = {
        "version": ledger.version,
        "session_id": ledger.session_id,
        "plan_phase_hash": ledger.plan_phase_hash,
        "active_task_index": ledger.active_task_index,
        "task_count": ledger.task_count,
        "completed_task_ids": list(ledger.completed_task_ids),
        "current_task_id": ledger.current_task_id,
        "pending_role": ledger.pending_role,
        "history_event_count": ledger.history_event_count,
        "history_root_digest": ledger.history_root_digest,
        "last_event_digest": ledger.last_event_digest,
        "latest_verification_ok": ledger.latest_verification_ok,
        "repair_attempts_by_task": ledger.repair_attempts_by_task,
        "council_replan_count": ledger.council_replan_count,
        "execution_status": ledger.execution_status,
        "invariants": list(ledger.invariants),
        "full_ledger_digest": _digest(payload),
    }
    return _canonical(compact)


__all__ = [
    "RefactorStateLedger",
    "bounded_state_ledger_text",
    "build_state_ledger",
    "measure_state_preservation",
]
