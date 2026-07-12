"""Guided Civic project orchestration for Aura's Winnipeg showcase."""
from __future__ import annotations

import hashlib
import threading
import time
from typing import Any

from aura_civic_authority import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY
from aura_civic_guided_steps import BLOCKED_ACTIONS, STEP_DETAILS, ranked_actions, timeline
from aura_civic_project_runtime import project_for_session, run_project_organ, runtime_module
from aura_civic_projects import CivicProjectDefinition, get_project, list_projects

GUIDE_VERSION = "AURA_CIVIC_GUIDED_PROJECT_V2"

_SESSION_LOCKS: dict[str, threading.RLock] = {}
_SESSION_LOCKS_GUARD = threading.Lock()


def _session_lock(session_id: str) -> threading.RLock:
    """Return the stable in-process lock that serializes one guided session."""
    key = str(session_id)
    with _SESSION_LOCKS_GUARD:
        lock = _SESSION_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _SESSION_LOCKS[key] = lock
        return lock


def _summary(session: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    comparison = session.get("music_comparison") or {}
    if "comparison" in comparison:
        comparison = comparison.get("comparison") or {}
    return {
        "state": session.get("state", "CREATED"),
        "needs_count": len(session.get("needs") or []),
        "offers_count": len(session.get("offers") or []),
        "workstream_count": len(session.get("workstreams") or []),
        "scenario_count": len(session.get("scenarios") or []),
        "legal_question_count": len(session.get("legal_instruments") or []),
        "organ_receipt_count": len(session.get("organ_receipts") or []),
        "representation_gaps": list(fixture.get("representation_gaps") or []),
        "pareto_frontier": list(comparison.get("pareto_frontier") or []),
        "decision_packet_ready": bool(session.get("decision_packet")),
        "pilot_authority_status": (session.get("pilot") or {}).get("authority_status", "NOT_STARTED"),
    }


def get_guide(session_id: str) -> dict[str, Any]:
    runtime = runtime_module()
    current = runtime.get_session(session_id)
    if not current.get("ok"):
        return current
    session = current["session"]
    project = project_for_session(session)
    fixture = project.fixtures_factory()
    index = max(0, min(int(session.get("guide_step_index") or 0), len(project.guided_steps) - 1))
    step_id = project.guided_steps[index]
    next_step_id = project.guided_steps[index + 1] if index < len(project.guided_steps) - 1 else None
    detail = STEP_DETAILS.get(step_id, {"title": step_id, "purpose": "", "human_question": "", "actions": ()})
    session_view = {
        "session_id": session_id,
        "objective": session.get("objective", project.objective),
        "state": session.get("state", "CREATED"),
        "profile_set": session.get("profile_set", {}),
        "needs": session.get("needs", []),
        "offers": session.get("offers", []),
        "workstreams": session.get("workstreams", []),
        "scenarios": session.get("scenarios", []),
        "music_comparison": session.get("music_comparison", {}),
        "legal_instruments": session.get("legal_instruments", []),
        "consent_arc": session.get("consent_arc", {}),
        "convergence": session.get("convergence", {}),
        "systemic_context": session.get("systemic_context", {}),
        "democratic_friction": session.get("democratic_friction", {}),
        "what_if": session.get("what_if", {}),
        "pilot": session.get("pilot", {}),
        "decision_packet": session.get("decision_packet", {}),
        "organ_receipts": session.get("organ_receipts", []),
        "representation_gaps": fixture.get("representation_gaps", []),
        "concerns": fixture.get("concerns", []),
        "objections": fixture.get("objections", []),
        "pilot_template": fixture.get("pilot_template", {}),
        "guide_responses": session.get("guide_responses", []),
    }
    demo_issue_available = bool(
        project.demo_issue
        and "EXPLORE_MAP" in project.guided_steps
        and index >= project.guided_steps.index("EXPLORE_MAP")
    )
    can_go_back = index > 0
    can_advance = index < len(project.guided_steps) - 1
    available_actions = ranked_actions(
        step_id,
        next_step_id=next_step_id,
        can_advance=can_advance,
        can_go_back=can_go_back,
        demo_issue_available=demo_issue_available,
    )
    return {
        "ok": True,
        "version": GUIDE_VERSION,
        "project": project.to_dict(),
        "session": session_view,
        "summary": _summary(session, fixture),
        "current_step_index": index,
        "current_step": {
            "step_id": step_id,
            "title": detail.get("title", step_id),
            "purpose": detail.get("purpose", ""),
            "human_question": detail.get("human_question", ""),
            "organ_actions": list(detail.get("actions") or ()),
        },
        "next_step_id": next_step_id,
        "timeline": timeline(project.guided_steps, index),
        "can_go_back": can_go_back,
        "can_advance": can_advance,
        "available_actions": available_actions,
        "blocked_actions": [dict(item) for item in BLOCKED_ACTIONS],
        "route_notice": "Route weights rank deterministic demo actions. They do not represent model confidence or grant civic authority.",
        "demo_issue_available": demo_issue_available,
        "demo_issue": dict(project.demo_issue or {}),
        "truth_notice": "All project records are synthetic demonstration data. Aura does not make binding civic decisions.",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def start_project(project_id: str = "winnipeg_pathways") -> dict[str, Any]:
    project = get_project(project_id)
    if not isinstance(project, CivicProjectDefinition):
        return dict(project)
    runtime = runtime_module()
    seed = f"{project.objective}\n[guided_showcase_run:{time.time_ns()}]"
    created = runtime.create_civic_session(seed, fixture=True)
    if not created.get("ok"):
        return created
    session_id = created["session"]["session_id"]
    fixture = project.fixtures_factory()
    runtime._update_session(session_id, {
        "project_id": project.project_id,
        "story": project.project_id,
        "objective": project.objective,
        "objective_hash": hashlib.blake2b(project.objective.encode(), digest_size=12).hexdigest(),
        "mandatory_constraints": list(project.mandatory_constraints),
        "guide_step_index": 0,
        "guide_responses": [],
        "guide_execution_log": [],
        "what_if_changes": dict(fixture.get("what_if_defaults") or {}),
    })
    return get_guide(session_id)


def advance_project(session_id: str) -> dict[str, Any]:
    with _session_lock(session_id):
        runtime = runtime_module()
        current = runtime.get_session(session_id)
        if not current.get("ok"):
            return current
        session = current["session"]
        project = project_for_session(session)
        old_index = max(0, min(int(session.get("guide_step_index") or 0), len(project.guided_steps) - 1))
        if old_index >= len(project.guided_steps) - 1:
            return get_guide(session_id)
        new_index = old_index + 1
        step_id = project.guided_steps[new_index]
        log = list(session.get("guide_execution_log") or [])
        for organ_type in tuple((STEP_DETAILS.get(step_id) or {}).get("actions") or ()):
            result = run_project_organ(session_id, organ_type)
            entry = {
                "step_id": step_id, "organ_type": organ_type, "ok": bool(result.get("ok")),
                "organ_id": result.get("organ_id", ""), "manifest_digest": result.get("manifest_digest", ""),
                "receipt": result.get("receipt", {}), "executed_at": time.time(),
            }
            log.append(entry)
            if not result.get("ok"):
                return {"ok": False, "error": "guided_step_execution_failed", "failure": entry, "guide": get_guide(session_id), "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        runtime._update_session(session_id, {"guide_step_index": new_index, "guide_execution_log": log[-80:]})
        return get_guide(session_id)


def back_project(session_id: str) -> dict[str, Any]:
    with _session_lock(session_id):
        runtime = runtime_module()
        current = runtime.get_session(session_id)
        if not current.get("ok"):
            return current
        session = current["session"]
        project = project_for_session(session)
        index = max(0, min(int(session.get("guide_step_index") or 0), len(project.guided_steps) - 1))
        runtime._update_session(session_id, {"guide_step_index": max(0, index - 1)})
        return get_guide(session_id)


def record_response(session_id: str, response: dict[str, Any]) -> dict[str, Any]:
    item = {
        "response_type": str(response.get("response_type") or "NOTE"),
        "statement": str(response.get("statement") or "").strip(),
        "participant_scope": str(response.get("participant_scope") or "showcase_participant"),
        "recorded_at": time.time(), "binding": False,
    }
    if not item["statement"]:
        return {"ok": False, "error": "statement is required", "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    with _session_lock(session_id):
        runtime = runtime_module()
        current = runtime.get_session(session_id)
        if not current.get("ok"):
            return current
        session = current["session"]
        responses = list(session.get("guide_responses") or []) + [item]
        updates: dict[str, Any] = {"guide_responses": responses}
        if item["response_type"] in {"CONSENT", "CONSENT_WITH_RESERVATION", "OBJECT", "CRITICAL_OBJECTION"}:
            updates["consent_responses"] = list(session.get("consent_responses") or []) + [item]
        runtime._update_session(session_id, updates)
        return get_guide(session_id)


def project_map(session_id: str, *, zoom: float = 11, viewer_scope: str = "community") -> dict[str, Any]:
    runtime = runtime_module()
    current = runtime.get_session(session_id)
    if not current.get("ok"):
        return current
    session = current["session"]
    manifest = session.get("map_manifest") or {}
    if not manifest:
        result = run_project_organ(session_id, "CivicMapOrgan")
        if not result.get("ok"):
            return result
        session = runtime.get_session(session_id).get("session", {})
        manifest = session.get("map_manifest") or {}
    from aura_civic_map import project_map_manifest
    return project_map_manifest(manifest, zoom=zoom, jurisdiction_id=project_for_session(session).jurisdiction_id, viewer_scope=viewer_scope)


__all__ = ["GUIDE_VERSION", "advance_project", "back_project", "get_guide", "list_projects", "project_map", "record_response", "start_project"]
