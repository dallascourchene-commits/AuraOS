"""Manual-free, six-slot guidance packets for the Human Agent Arena.

The guide explains only the transitions admitted by the guarded WFST. It may teach,
clarify, and suggest, but it cannot grant capabilities or bypass a hard guard.
"""
from __future__ import annotations

from typing import Any

GUIDANCE_VERSION = "AURA_HUMAN_AGENT_GUIDANCE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

PHASE_GUIDANCE: dict[str, dict[str, Any]] = {
    "FRAME": {
        "title": "Frame the objective",
        "purpose": "State the outcome, boundaries, and success condition before tools inspect or change anything.",
        "rules": (
            "Describe the desired result rather than prescribing an ungrounded patch.",
            "Name important constraints, exclusions, and human approval requirements.",
            "Do not grant production, commit, push, or merge authority.",
        ),
        "slots": {"DIR": "active_objective", "ASP": "opening", "CLASS": "objective_framing", "SUBJ": "human_operator", "VOICE": "human_declared", "STEM": "frame"},
    },
    "GROUND": {
        "title": "Ground in exact repository evidence",
        "purpose": "Locate files, symbols, tests, risks, and existing capabilities before planning work.",
        "rules": (
            "Use exact files, symbols, line ranges, hashes, and tests as patch authority.",
            "Treat VSA and semantic similarity as navigation only.",
            "Abstain or ask for a narrower objective when grounding is insufficient.",
        ),
        "slots": {"DIR": "repository_truth", "ASP": "before_planning", "CLASS": "evidence_grounding", "SUBJ": "human_agent_arena", "VOICE": "inspect_only", "STEM": "ground"},
    },
    "PLAN": {
        "title": "Prepare the bounded Arena capsule",
        "purpose": "Convert grounded evidence into exact files, leases, constraints, tests, and acceptance criteria.",
        "rules": (
            "Select the minimum affected surface and minimum capabilities.",
            "Preserve source hashes, test targets, and rollback boundaries.",
            "A plan is not permission to mutate production.",
        ),
        "slots": {"DIR": "bounded_change_space", "ASP": "pre_action", "CLASS": "arena_planning", "SUBJ": "human_guided_worker", "VOICE": "proposal_only", "STEM": "prepare"},
    },
    "ACT": {
        "title": "Stage a candidate change",
        "purpose": "Apply the proposed change only inside an isolated, reviewable workspace.",
        "rules": (
            "Require a candidate diff and exact affected files.",
            "Keep production unchanged.",
            "Reject undeclared files, capabilities, or scope expansion.",
        ),
        "slots": {"DIR": "ephemeral_workspace", "ASP": "temporary", "CLASS": "candidate_change", "SUBJ": "bounded_worker", "VOICE": "staged_proposal", "STEM": "stage"},
    },
    "PROVE": {
        "title": "Produce measured evidence",
        "purpose": "Run focused tests and verifier gates before any human decision about promotion.",
        "rules": (
            "Measured test evidence outranks model confidence.",
            "A failed verifier returns to repair; it does not get rationalized away.",
            "Preserve test scope, outputs, receipts, and unresolved uncertainty.",
        ),
        "slots": {"DIR": "verification_boundary", "ASP": "after_staging", "CLASS": "evidence_production", "SUBJ": "independent_verifier", "VOICE": "measured", "STEM": "prove"},
    },
    "DECIDE": {
        "title": "Review and decide without automatic promotion",
        "purpose": "Present the evidence, remaining risks, and permitted review actions to the human authority.",
        "rules": (
            "Human review is explicit and recorded.",
            "No automatic commit, push, merge, deployment, or production hotswap.",
            "Blocked decisions must explain the smallest safe remediation.",
        ),
        "slots": {"DIR": "human_review_gate", "ASP": "post_verification", "CLASS": "governed_decision", "SUBJ": "human_reviewer", "VOICE": "human_authority", "STEM": "decide"},
    },
}

ACTION_SLOT_PROFILES: dict[str, dict[str, str]] = {
    "set_objective": {"DIR": "active_objective", "ASP": "opening", "CLASS": "objective", "SUBJ": "human_operator", "VOICE": "human_declared", "STEM": "frame"},
    "ground_context": {"DIR": "repository_truth", "ASP": "before_planning", "CLASS": "inspection", "SUBJ": "topology_inspector", "VOICE": "read_only", "STEM": "ground"},
    "prepare_capsule": {"DIR": "bounded_change_space", "ASP": "pre_action", "CLASS": "arena_capsule", "SUBJ": "human_guided_worker", "VOICE": "proposal_only", "STEM": "prepare"},
    "stage_patch": {"DIR": "ephemeral_workspace", "ASP": "temporary", "CLASS": "candidate_patch", "SUBJ": "bounded_worker", "VOICE": "staged_proposal", "STEM": "stage"},
    "run_tests": {"DIR": "ephemeral_test_lab", "ASP": "after_staging", "CLASS": "measured_tests", "SUBJ": "test_lab", "VOICE": "measured", "STEM": "test"},
    "verify_patch": {"DIR": "verification_boundary", "ASP": "after_tests", "CLASS": "verifier_gate", "SUBJ": "independent_verifier", "VOICE": "evidence_bound", "STEM": "verify"},
    "check_hotswap": {"DIR": "review_readiness", "ASP": "post_verification", "CLASS": "readiness_check", "SUBJ": "human_agent_arena", "VOICE": "advisory", "STEM": "assess"},
    "human_review": {"DIR": "human_review_gate", "ASP": "final_review", "CLASS": "human_decision", "SUBJ": "human_reviewer", "VOICE": "human_authority", "STEM": "review"},
    "export_handoff": {"DIR": "review_packet", "ASP": "anytime_after_plan", "CLASS": "evidence_export", "SUBJ": "human_agent_arena", "VOICE": "read_only", "STEM": "export"},
}


def _action_id(item: dict[str, Any]) -> str:
    return str((item.get("provenance") or {}).get("action_id") or "")


def _slots(item: dict[str, Any], phase: str) -> dict[str, str]:
    action_id = _action_id(item)
    return dict(ACTION_SLOT_PROFILES.get(action_id) or PHASE_GUIDANCE.get(phase, {}).get("slots") or {})


def _available_row(item: dict[str, Any], phase: str) -> dict[str, Any]:
    return {
        "transition_id": str(item.get("transition_id") or ""),
        "action_id": _action_id(item),
        "label": str(item.get("label") or item.get("transition_id") or ""),
        "description": str(item.get("description") or ""),
        "from_state": str(item.get("from_state") or phase),
        "next_state": str(item.get("next_state") or phase),
        "risk": str(item.get("risk") or "unknown"),
        "required_evidence": list(item.get("required_evidence") or []),
        "produced_evidence": list(item.get("produced_evidence") or []),
        "requested_capabilities": list(item.get("requested_capabilities") or []),
        "rank": dict(item.get("rank") or {}),
        "intent_slots": _slots(item, phase),
        "why_available": "All declared hard guards passed for the current state and evidence.",
        "binding": False,
    }


def _blocked_row(item: dict[str, Any], phase: str) -> dict[str, Any]:
    failed = [str((guard or {}).get("guard_id") or (guard or {}).get("id") or "") for guard in item.get("failed_guards") or []]
    missing = list(item.get("missing_evidence") or [])
    return {
        "transition_id": str(item.get("transition_id") or ""),
        "action_id": _action_id(item),
        "label": str(item.get("label") or item.get("transition_id") or ""),
        "description": str(item.get("description") or ""),
        "failed_guards": [guard for guard in failed if guard],
        "missing_evidence": missing,
        "remediation": list(item.get("remediation") or []),
        "intent_slots": _slots(item, phase),
        "why_blocked": "The action failed a hard guard and remains unavailable until the named evidence or policy requirement is satisfied.",
        "fail_closed": True,
    }


def build_guidance_packet(workflow_state: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic teaching packet from the current guarded state."""
    phase = str(workflow_state.get("current_phase") or "FRAME")
    phase_info = dict(PHASE_GUIDANCE.get(phase) or PHASE_GUIDANCE["FRAME"])
    routing = dict(workflow_state.get("routing") or {})
    available_raw = [item for item in routing.get("available") or [] if not item.get("meta_transition") and _action_id(item)]
    blocked_raw = [item for item in routing.get("blocked") or [] if not item.get("meta_transition")]
    evidence_keys = list(workflow_state.get("evidence_keys") or [])
    evidence = dict(workflow_state.get("evidence") or {})
    available = [
        _available_row(item, phase)
        for item in available_raw
        if not (
            item.get("produced_evidence")
            and all(
                bool(evidence.get(str(key)))
                for key in item.get("produced_evidence") or []
            )
        )
    ]
    blocked = [_blocked_row(item, phase) for item in blocked_raw]
    recommended = available[:1]
    packet = {
        "ok": bool(routing.get("ok")),
        "version": GUIDANCE_VERSION,
        "current_phase": phase,
        "gate": {
            "title": phase_info["title"],
            "purpose": phase_info["purpose"],
            "rules": list(phase_info["rules"]),
            "intent_slots": dict(phase_info["slots"]),
        },
        "recommended_actions": recommended,
        "available_actions": available,
        "blocked_actions": blocked,
        "evidence_keys": evidence_keys,
        "questions_supported": [
            "What can I do?",
            "What should I do next?",
            "Why is an action blocked?",
            "What evidence do we have?",
            "Explain this gate using the six slots.",
        ],
        "ai_direction": {
            "role": "Human Agent Arena guide",
            "instruction": "Teach from this packet only. Never invent an unavailable action, bypass a hard guard, or treat rank as confidence. Explain the six-slot intent, evidence requirements, and smallest safe next step. Ask the human before consequential choices.",
            "may": ["explain", "compare admitted options", "identify missing evidence", "suggest the safest admitted next step"],
            "may_not": ["grant capabilities", "bypass guards", "mutate production", "commit", "push", "merge"],
        },
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    packet["summary"] = _summary(packet)
    return packet


def _summary(packet: dict[str, Any]) -> str:
    gate = packet.get("gate") or {}
    recommended = packet.get("recommended_actions") or []
    if recommended:
        action = recommended[0]
        return f"You are at {gate.get('title')}. The safest admitted next action is {action.get('label')}."
    blocked_count = len(packet.get("blocked_actions") or [])
    return f"You are at {gate.get('title')}. No work transition is currently admitted; inspect {blocked_count} blocked transition(s) for missing evidence."


def answer_guidance_question(packet: dict[str, Any], question: str) -> dict[str, Any]:
    """Answer common onboarding questions without using model guesswork."""
    text = str(question or "").strip()
    normalized = text.casefold()
    gate = packet.get("gate") or {}
    available = packet.get("available_actions") or []
    blocked = packet.get("blocked_actions") or []
    recommended = packet.get("recommended_actions") or []

    if any(token in normalized for token in ("what can i do", "available", "options")):
        if available:
            answer = "Available now: " + "; ".join(f"{item['label']} — {item['why_available']}" for item in available[:4])
        else:
            answer = "No work transition is currently admitted. Ask why an action is blocked to see the missing evidence."
        kind = "available_actions"
    elif any(token in normalized for token in ("what next", "should i do", "next step", "guide me")):
        if recommended:
            item = recommended[0]
            answer = f"Recommended next: {item['label']}. {item['description']} This is advisory; you choose whether to run it."
        else:
            answer = "No next work action is admitted yet. Review the blocked transitions and provide the smallest missing evidence."
        kind = "recommended_next"
    elif any(token in normalized for token in ("why blocked", "why is", "can't", "cannot", "missing")):
        if blocked:
            answer = "Blocked now: " + "; ".join(
                f"{item['label']} — missing {', '.join(item['missing_evidence']) or 'a policy or capability requirement'}"
                for item in blocked[:4]
            )
        else:
            answer = "No state-local work transition is currently blocked."
        kind = "blocked_actions"
    elif "evidence" in normalized:
        keys = packet.get("evidence_keys") or []
        answer = "Current evidence: " + (", ".join(keys) if keys else "none yet") + "."
        kind = "evidence"
    elif any(token in normalized for token in ("six slot", "six-slot", "explain this gate", "where am i", "this step")):
        slots = gate.get("intent_slots") or {}
        answer = (
            f"{gate.get('title')}: {gate.get('purpose')} "
            + " · ".join(f"{key}={value}" for key, value in slots.items())
        )
        kind = "gate_explanation"
    else:
        answer = packet.get("summary") or "The current gate is available in the guidance packet."
        kind = "summary"

    return {
        "ok": True,
        "kind": kind,
        "question": text,
        "answer": answer,
        "current_phase": packet.get("current_phase"),
        "gate": gate,
        "recommended_actions": recommended,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
