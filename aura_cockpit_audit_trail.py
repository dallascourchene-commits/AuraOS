"""
Aura Cockpit Audit Trail — records gate transitions, approvals, and audit events.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
import time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
AUDIT_VERSION = "AURA_COCKPIT_AUDIT_TRAIL_V1"

# In-memory event store (fallback when backends unavailable)
_events: list[dict[str, Any]] = []


def _record(event_type: str, data: dict) -> dict:
    event = {"timestamp": time.time(), "event_type": event_type, **data,
              "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    _events.append(event)
    # Try symbolic trace memory
    try:
        from aura_symbolic_trace_memory import record_trace
        record_trace(event)
    except Exception:
        pass
    return {"ok": True, "recorded": True, "event_type": event_type,
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def record_gate_transition(from_state: str, to_state: str, evidence: dict | None = None, repo_root: str = ".") -> dict:
    return _record("gate_transition", {"from_state": from_state, "to_state": to_state, "evidence": evidence or {}})


def record_human_approval(gate_state: str, approved_by: str = "human", repo_root: str = ".") -> dict:
    return _record("human_approval", {"gate_state": gate_state, "approved_by": approved_by})


def record_agent_handoff(agent: str, handoff_packet: dict, repo_root: str = ".") -> dict:
    return _record("agent_handoff", {"agent": agent, "handoff_summary": str(handoff_packet)[:200]})


def record_verifier_result(result: dict, repo_root: str = ".") -> dict:
    return _record("verifier_result", {"result_summary": str(result)[:200]})


def record_research_evidence(evidence_packet: dict, repo_root: str = ".") -> dict:
    return _record("research_evidence", {"evidence_summary": str(evidence_packet)[:200]})


def export_cockpit_audit_packet(repo_root: str = ".") -> dict:
    return {"ok": True, "audit_packet": {"events": list(_events), "count": len(_events)},
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
