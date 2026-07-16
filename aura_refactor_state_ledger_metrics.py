"""Preservation metrics and bounded serialization for State Ledger V3."""
from __future__ import annotations

from typing import Any

from aura_refactor_state_identity import canonical, digest, history_events, history_identity, tokens
from aura_refactor_state_ledger_core import RefactorStateLedger, _inputs, build_state_sidecar, reconstruct_state_from_ledger

_INVARIANTS = ("exact_source_spans_and_hashes_only", "no_direct_production_mutation", "human_review_required", "staged_verifier_gated_changes", "complete_history_identity_digest", "digest_bound_state_reconstructability")


def measure_state_preservation(session: Any, ledger: RefactorStateLedger) -> dict[str, Any]:
    sidecar = build_state_sidecar(session, repair_attempts_by_task=ledger.repair_attempts_by_task, council_replan_count=ledger.council_replan_count)
    try:
        projection = reconstruct_state_from_ledger(ledger, sidecar)
        reconstructable = True
    except ValueError:
        projection, reconstructable = {}, False
    tasks, active, dependencies, _repairs, _replans = _inputs(session, ledger.repair_attempts_by_task, ledger.council_replan_count)
    events, _mode = history_events(session)
    history = history_identity(ledger.session_id, events)
    completed = [str(task.get("task_id") or f"A{index + 1}") for index, task in enumerate(tasks[:active])]
    current = str(tasks[active].get("task_id") or f"A{active + 1}") if 0 <= active < len(tasks) else ""
    checks = {
        "plan_identity": ledger.plan_phase_hash == str(getattr(session, "plan_phase_hash", "") or ""),
        "task_count": ledger.task_count == len(tasks),
        "completed_tasks": list(ledger.completed_task_ids) == completed,
        "current_task": ledger.current_task_id == current,
        "dependency_map": ledger.task_dependencies == dependencies,
        "history_event_count": ledger.history_event_count == history["history_event_count"],
        "history_root_identity": ledger.history_root_digest == history["history_root_digest"],
        "last_event_identity": ledger.last_event_digest == history["last_event_digest"],
        "execution_state_identity": bool(projection) and digest(projection) == ledger.execution_state_digest,
        "sidecar_reconstructability": reconstructable,
        "authority_invariants": set(_INVARIANTS).issubset(set(ledger.invariants)),
    }
    score = sum(bool(value) for value in checks.values()) / len(checks)
    history_payload = {"turns": list(getattr(session, "turns", []) or []), "stage_results": list(getattr(session, "stage_results", []) or []), "verification_results": list(getattr(session, "verification_results", []) or [])}
    ledger_payload = ledger.to_dict()
    return {"state_preservation_score": round(score, 4), "context_drift_score": round(1.0 - score, 4), "checks": checks, "state_ledger_tokens": tokens(ledger_payload), "full_history_tokens": tokens(history_payload), "history_avoided_tokens": max(0, tokens(history_payload) - tokens(ledger_payload)), "ledger_to_history_ratio": round(tokens(ledger_payload) / max(1, tokens(history_payload)), 4), "ledger_digest": digest(ledger_payload), "history_digest": digest(history_payload), "history_root_digest": ledger.history_root_digest, "execution_state_digest": ledger.execution_state_digest, "measurement_classes": {"state_preservation_score": "DERIVED_PROVENANCE_STATE_AND_RECONSTRUCTION_MATCH", "context_drift_score": "DERIVED_ONE_MINUS_STATE_PRESERVATION", "state_ledger_tokens": "ESTIMATED_CHAR4_PROXY", "full_history_tokens": "ESTIMATED_CHAR4_PROXY"}}


def bounded_state_ledger_text(ledger: RefactorStateLedger, max_tokens: int = 480) -> str:
    payload = ledger.to_dict()
    if tokens(payload) <= max_tokens:
        return canonical(payload)
    keep = ("version", "session_id", "plan_phase_hash", "active_task_index", "task_count", "completed_task_ids", "current_task_id", "pending_role", "history_event_count", "history_root_digest", "last_event_digest", "last_sequence_number", "event_sequence_mode", "event_store_ref", "execution_state_digest", "dependency_frontier_digest", "latest_verification_ok", "repair_attempts_by_task", "council_replan_count", "execution_status", "invariants", "reconstruction_sidecar_digest")
    compact = {key: payload[key] for key in keep}
    compact["full_ledger_digest"] = digest(payload)
    return canonical(compact)


__all__ = ["bounded_state_ledger_text", "measure_state_preservation"]
