"""Aura Cockpit Audit Trail — records gate transitions, approvals, and audit events.

Dependencies: stdlib only. All Aura imports are lazy. Persistent symbolic trace
recording is attempted through the canonical ``record_trace_event`` API and failures
are surfaced instead of silently claiming persistence.
"""
from __future__ import annotations

from pathlib import Path
import time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
AUDIT_VERSION = "AURA_COCKPIT_AUDIT_TRAIL_V2"

_events: list[dict[str, Any]] = []
_MAX_EVENTS = 1000


def _record(event_type: str, data: dict, *, repo_root: str | Path = ".") -> dict:
    event = {
        "timestamp": time.time(),
        "event_type": event_type,
        **data,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    _events.append(event)
    if len(_events) > _MAX_EVENTS:
        del _events[:-_MAX_EVENTS]

    persistent = False
    persistence_error = ""
    trace_atom_id = ""
    try:
        from aura_symbolic_trace_memory import record_trace_event

        memory_root = Path(repo_root).resolve() / "Aura_Memory" / "symbolic_trace"
        atom = record_trace_event(event, memory_root=memory_root)
        persistent = True
        trace_atom_id = str(getattr(atom, "atom_id", ""))
    except Exception as exc:
        persistence_error = f"symbolic_trace_persistence_failed:{type(exc).__name__}"

    return {
        "ok": True,
        "recorded": True,
        "event_type": event_type,
        "persistent": persistent,
        "persistence_error": persistence_error,
        "trace_atom_id": trace_atom_id,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def record_gate_transition(from_state: str, to_state: str, evidence: dict | None = None, repo_root: str = ".") -> dict:
    return _record(
        "gate_transition",
        {"from_state": from_state, "to_state": to_state, "evidence": evidence or {}},
        repo_root=repo_root,
    )


def record_human_approval(gate_state: str, approved_by: str = "human", repo_root: str = ".") -> dict:
    return _record(
        "human_approval",
        {"gate_state": gate_state, "approved_by": approved_by},
        repo_root=repo_root,
    )


def record_agent_handoff(agent: str, handoff_packet: dict, repo_root: str = ".") -> dict:
    return _record(
        "agent_handoff",
        {"agent": agent, "handoff_summary": str(handoff_packet)[:200]},
        repo_root=repo_root,
    )


def record_verifier_result(result: dict, repo_root: str = ".") -> dict:
    return _record(
        "verifier_result",
        {"result_summary": str(result)[:200]},
        repo_root=repo_root,
    )


def record_research_evidence(evidence_packet: dict, repo_root: str = ".") -> dict:
    return _record(
        "research_evidence",
        {"evidence_summary": str(evidence_packet)[:200]},
        repo_root=repo_root,
    )


def export_cockpit_audit_packet(repo_root: str = ".") -> dict:
    return {
        "ok": True,
        "version": AUDIT_VERSION,
        "audit_packet": {"events": list(_events), "count": len(_events)},
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
