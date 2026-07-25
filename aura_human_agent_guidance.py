"""Manual-free guidance packets for the Human Agent Arena.

Guidance explains only transitions admitted by the guarded WFST and projects
bilateral refinement evidence when supplied.  It may teach, clarify, and suggest,
but it cannot remove a hard guard, grant capability, or bypass human confirmation.
"""
from __future__ import annotations

from typing import Any, Mapping

GUIDANCE_VERSION = "AURA_HUMAN_AGENT_GUIDANCE_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

PHASE_GUIDANCE: dict[str, dict[str, Any]] = {
    "FRAME": {
        "title": "Frame the objective",
        "purpose": "State the outcome, bilateral boundaries, and success condition before tools inspect or change anything.",
        "rules": (
            "Describe both the desired result and outcomes that must not occur.",
            "Name important constraints, exclusions, and human approval requirements.",
            "Do not grant production, commit, push, pull-request, or merge authority.",
        ),
        "slots": {"DIR": "active_objective", "ASP": "opening", "CLASS": "objective_framing", "SUBJ": "human_operator", "VOICE": "human_declared", "STEM": "frame"},
    },
    "GROUND": {
        "title": "Ground in exact repository evidence",
        "purpose": "Locate files, symbols, tests, risks, definitions, and existing capabilities before planning work.",
        "rules": (
            "Use exact files, symbols, line ranges, hashes, schemas, tests, and receipts as authority-bearing evidence.",
            "Treat VSA, topology, and semantic similarity as navigation only.",
            "Abstain or ask a targeted clarification when grounding is insufficient.",
        ),
        "slots": {"DIR": "repository_truth", "ASP": "before_planning", "CLASS": "evidence_grounding", "SUBJ": "human_agent_arena", "VOICE": "inspect_only", "STEM": "ground"},
    },
    "PLAN": {
        "title": "Prepare the bounded Arena capsule",
        "purpose": "Convert confirmed intent and grounded evidence into exact files, leases, constraints, tests, and acceptance criteria.",
        "rules": (
            "Select the minimum affected surface and minimum capabilities.",
            "Carry positive requirements, negative requirements, guardrails, source hashes, and rollback boundaries.",
            "A plan is not permission to mutate production.",
        ),
        "slots": {"DIR": "bounded_change_space", "ASP": "pre_action", "CLASS": "arena_planning", "SUBJ": "human_guided_worker", "VOICE": "proposal_only", "STEM": "prepare"},
    },
    "ACT": {
        "title": "Stage a candidate change",
        "purpose": "Apply the proposed change only inside an isolated, reviewable workspace.",
        "rules": (
            "Require a current confirmation receipt, candidate diff, and exact affected files.",
            "Keep production unchanged.",
            "Reject undeclared files, capabilities, effects, or scope expansion.",
        ),
        "slots": {"DIR": "ephemeral_workspace", "ASP": "temporary", "CLASS": "candidate_change", "SUBJ": "bounded_worker", "VOICE": "staged_proposal", "STEM": "stage"},
    },
    "PROVE": {
        "title": "Produce measured evidence",
        "purpose": "Prove required behavior, prohibited behavior, preservation, and lifecycle cleanup before promotion review.",
        "rules": (
            "Measured test evidence outranks model confidence.",
            "A failed verifier returns to repair; it does not get rationalized away.",
            "Preserve positive proof, negative proof, test scope, outputs, receipts, and unresolved uncertainty.",
        ),
        "slots": {"DIR": "verification_boundary", "ASP": "after_staging", "CLASS": "evidence_production", "SUBJ": "independent_verifier", "VOICE": "measured", "STEM": "prove"},
    },
    "DECIDE": {
        "title": "Review and decide without automatic promotion",
        "purpose": "Present exact evidence, remaining risks, stale conditions, and permitted review actions to the human authority.",
        "rules": (
            "Human review is explicit and recorded.",
            "No automatic commit, push, merge, deployment, professional action, physical work, or learning promotion.",
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


def _action_id(item: Mapping[str, Any]) -> str:
    return str((item.get("provenance") or {}).get("action_id") or "")


def _slots(item: Mapping[str, Any], phase: str) -> dict[str, str]:
    return dict(
        ACTION_SLOT_PROFILES.get(_action_id(item))
        or PHASE_GUIDANCE.get(phase, {}).get("slots")
        or {}
    )


def _available_row(item: Mapping[str, Any], phase: str) -> dict[str, Any]:
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


def _blocked_row(item: Mapping[str, Any], phase: str) -> dict[str, Any]:
    failed = [
        str((guard or {}).get("guard_id") or (guard or {}).get("id") or "")
        for guard in item.get("failed_guards") or []
    ]
    return {
        "transition_id": str(item.get("transition_id") or ""),
        "action_id": _action_id(item),
        "label": str(item.get("label") or item.get("transition_id") or ""),
        "description": str(item.get("description") or ""),
        "failed_guards": [guard for guard in failed if guard],
        "missing_evidence": list(item.get("missing_evidence") or []),
        "remediation": list(item.get("remediation") or []),
        "intent_slots": _slots(item, phase),
        "why_blocked": "The action failed a hard guard and remains unavailable until the named evidence, confirmation, or policy requirement is satisfied.",
        "fail_closed": True,
    }


def _refinement_projection(refinement: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(refinement or {})
    hard = [dict(item) for item in source.get("hard_guardrails") or [] if isinstance(item, Mapping)]
    editable = [dict(item) for item in source.get("editable_guardrails") or [] if isinstance(item, Mapping)]
    unresolved = [dict(item) for item in source.get("unresolved_ambiguities") or [] if isinstance(item, Mapping)]
    return {
        "stage": str(source.get("stage") or ""),
        "confirmation_status": str(source.get("confirmation_status") or "PENDING"),
        "positive_requirements": list(source.get("positive_requirements") or []),
        "negative_requirements": list(source.get("negative_requirements") or []),
        "hard_guardrails": [
            {
                **item,
                "why_required": str(item.get("rationale") or "Architectural or authority evidence requires this guardrail."),
                "removal_possible": False,
            }
            for item in hard
        ],
        "editable_guardrails": [
            {
                **item,
                "why_required": str(item.get("rationale") or "Proposed from current repository or domain evidence."),
                "removal_possible": True,
            }
            for item in editable
        ],
        "missing_human_decisions": [
            {
                "question_id": str(item.get("question_id") or ""),
                "question": str(item.get("question") or ""),
                "why_it_changes_execution": str(item.get("why_it_changes_execution") or ""),
            }
            for item in unresolved
        ],
        "hard_guardrail_removal_possible": False,
    }


def build_guidance_packet(
    workflow_state: dict[str, Any],
    refinement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic guidance from guarded workflow and bilateral state."""
    phase = str(workflow_state.get("current_phase") or "FRAME")
    phase_info = dict(PHASE_GUIDANCE.get(phase) or PHASE_GUIDANCE["FRAME"])
    routing = dict(workflow_state.get("routing") or {})
    available_raw = [
        item
        for item in routing.get("available") or []
        if not item.get("meta_transition") and _action_id(item)
    ]
    blocked_raw = [
        item
        for item in routing.get("blocked") or []
        if not item.get("meta_transition")
    ]
    available = [_available_row(item, phase) for item in available_raw]
    blocked = [_blocked_row(item, phase) for item in blocked_raw]
    bilateral = _refinement_projection(refinement)
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
        "recommended_actions": available[:1],
        "available_actions": available,
        "blocked_actions": blocked,
        "evidence_keys": list(workflow_state.get("evidence_keys") or []),
        "bilateral_intent": bilateral,
        "hard_guardrails": bilateral["hard_guardrails"],
        "editable_guardrails": bilateral["editable_guardrails"],
        "missing_human_decisions": bilateral["missing_human_decisions"],
        "questions_supported": [
            "What can I do?",
            "What should I do next?",
            "Why is an action blocked?",
            "Which hard guardrails apply?",
            "Can this guardrail be removed?",
            "What human decision is missing?",
            "What evidence do we have?",
            "Explain this gate using the six slots.",
        ],
        "ai_direction": {
            "role": "Human Agent Arena guide",
            "instruction": "Teach from this packet only. Never invent an action, remove a hard guard, bypass confirmation, or treat rank as confidence. Explain positive and negative intent, six-slot routing, evidence requirements, and the smallest safe next step.",
            "may": ["explain", "compare admitted options", "identify missing evidence or decisions", "suggest the safest admitted next step"],
            "may_not": ["grant capabilities", "remove hard guardrails", "bypass guards", "mutate production", "commit", "push", "open or merge a pull request", "promote learning"],
        },
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    packet["summary"] = _summary(packet)
    return packet


def _summary(packet: Mapping[str, Any]) -> str:
    gate = packet.get("gate") or {}
    missing = packet.get("missing_human_decisions") or []
    if missing:
        return f"You are at {gate.get('title')}. Intent confirmation is blocked by {len(missing)} missing human decision(s)."
    recommended = packet.get("recommended_actions") or []
    if recommended:
        return f"You are at {gate.get('title')}. The safest admitted next action is {recommended[0].get('label')}."
    blocked_count = len(packet.get("blocked_actions") or [])
    return f"You are at {gate.get('title')}. No work transition is currently admitted; inspect {blocked_count} blocked transition(s)."


def answer_guidance_question(packet: dict[str, Any], question: str) -> dict[str, Any]:
    """Answer common questions without model guesswork."""
    text = str(question or "").strip()
    normalized = text.casefold()
    gate = packet.get("gate") or {}
    available = packet.get("available_actions") or []
    blocked = packet.get("blocked_actions") or []
    recommended = packet.get("recommended_actions") or []
    hard = packet.get("hard_guardrails") or []
    editable = packet.get("editable_guardrails") or []
    missing = packet.get("missing_human_decisions") or []

    if "guardrail" in normalized and any(token in normalized for token in ("remove", "reject", "disable", "optional")):
        requested = hard[0] if hard else (editable[0] if editable else {})
        if requested and requested.get("removal_possible") is False:
            answer = f"{requested.get('statement')} cannot be removed through Gate Dialogue because it is architectural, authority-bound, or domain-required."
        elif requested:
            answer = f"{requested.get('statement')} is editable, but changing it stales confirmation and requires a revised teach-back."
        else:
            answer = "No projected guardrail matched the question."
        kind = "guardrail_removability"
    elif "guardrail" in normalized:
        rows = [*hard, *editable]
        answer = "Current guardrails: " + (
            "; ".join(
                f"{item.get('statement')} — {item.get('why_required')}"
                for item in rows[:8]
            )
            if rows
            else "none projected yet"
        )
        kind = "guardrails"
    elif any(token in normalized for token in ("decision", "clarif", "confirm")):
        answer = "Missing human decisions: " + (
            "; ".join(item.get("question") or "" for item in missing[:6])
            if missing
            else "none; review the paired teach-back before explicit confirmation"
        )
        kind = "missing_human_decisions"
    elif any(token in normalized for token in ("what can i do", "available", "options")):
        answer = "Available now: " + (
            "; ".join(f"{item['label']} — {item['why_available']}" for item in available[:4])
            if available
            else "no work transition is currently admitted"
        )
        kind = "available_actions"
    elif any(token in normalized for token in ("what next", "should i do", "next step", "guide me")):
        if missing:
            answer = f"Answer this first: {missing[0].get('question')}"
        elif recommended:
            item = recommended[0]
            answer = f"Recommended next: {item['label']}. {item['description']} This is advisory."
        else:
            answer = "No next work action is admitted yet. Review blocked transitions and missing evidence."
        kind = "recommended_next"
    elif any(token in normalized for token in ("why blocked", "why is", "can't", "cannot", "missing")):
        answer = "Blocked now: " + (
            "; ".join(
                f"{item['label']} — missing {', '.join(item['missing_evidence']) or 'a policy, confirmation, or capability requirement'}"
                for item in blocked[:4]
            )
            if blocked
            else "no state-local work transition is currently blocked"
        )
        kind = "blocked_actions"
    elif "evidence" in normalized:
        keys = packet.get("evidence_keys") or []
        answer = "Current evidence: " + (", ".join(keys) if keys else "none yet") + "."
        kind = "evidence"
    elif any(token in normalized for token in ("six slot", "six-slot", "explain this gate", "where am i", "this step")):
        slots = gate.get("intent_slots") or {}
        answer = f"{gate.get('title')}: {gate.get('purpose')} " + " · ".join(
            f"{key}={value}" for key, value in slots.items()
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


__all__ = ["answer_guidance_question", "build_guidance_packet"]
