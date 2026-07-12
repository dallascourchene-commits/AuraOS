"""Step metadata and ranked action menus for Aura's guided Civic projects."""
from __future__ import annotations

from typing import Any

STEP_DETAILS: dict[str, dict[str, Any]] = {
    "WELCOME": {"title": "Welcome to the Pathways Lab", "purpose": "Understand the project boundary and the authority Aura does not hold.", "human_question": "Is this the right problem to explore as a non-binding synthetic demonstration?", "actions": ()},
    "FRAME_OBJECTIVE": {"title": "Frame the community objective", "purpose": "Preserve the objective and mandatory constraints before decomposition.", "human_question": "Which outcomes must remain non-negotiable?", "actions": ()},
    "SELECT_CONTEXT": {"title": "Select jurisdiction and context", "purpose": "Activate Winnipeg jurisdiction while keeping cultural context explicit and opt-in.", "human_question": "Which context lenses are authorized for this session?", "actions": ("CivicProfileOrgan",)},
    "EXPLORE_MAP": {"title": "Explore the governed map", "purpose": "View infrastructure without mapping vulnerable people.", "human_question": "Which service-access gaps deserve closer examination?", "actions": ("CivicMapOrgan",)},
    "ADD_COMMUNITY_INPUT": {"title": "Review needs, assets, and concerns", "purpose": "Keep original statements, consent, privacy, and gaps visible.", "human_question": "Whose voice or resource is still missing?", "actions": ("CommunityContributionOrgan", "CommunityResourceMatcherOrgan")},
    "DECOMPOSE_WORK": {"title": "Decompose the work", "purpose": "Create bounded workstreams while preserving every constraint.", "human_question": "Which workstreams require independent human owners?", "actions": ("CivicMITOSISOrgan",)},
    "COMPARE_SCENARIOS": {"title": "Compare possible approaches", "purpose": "Expose weights, trade-offs, sensitivity, and Pareto information without a hidden winner.", "human_question": "Which trade-offs should the community challenge?", "actions": ("CivicMUSICOrgan", "CivicEvidenceOrgan")},
    "REVIEW_CONSENT": {"title": "Preserve consent and objections", "purpose": "Make disagreement and representation gaps first-class evidence.", "human_question": "What must be addressed before a pilot can proceed?", "actions": ("ConsentArcOrgan", "SystemicContextOrgan")},
    "RUN_WHAT_IF": {"title": "Test assumptions", "purpose": "Explore changed assumptions as simulation only, never prediction.", "human_question": "Which uncertainty would most change the decision?", "actions": ("WhatIfOrgan",)},
    "DESIGN_PILOT": {"title": "Design a reversible 90-day pilot", "purpose": "Define actions, owners, review points, stop conditions, and unresolved checks.", "human_question": "Who must accept responsibility before this pilot can start?", "actions": ("PilotTunnelOrgan",)},
    "REVIEW_PACKET": {"title": "Review the decision packet", "purpose": "Assemble evidence, scenarios, objections, gaps, legal questions, and next human decisions.", "human_question": "Is the packet ready for community review?", "actions": ("DecisionPacketOrgan",)},
    "COMPLETE": {"title": "Human review remains authoritative", "purpose": "End with a reviewable proposal, not an automated decision.", "human_question": "What should people do next, and what must Aura remain prohibited from doing?", "actions": ()},
}

ADVANCE_LABELS = {
    "WELCOME": "Begin the guided project",
    "FRAME_OBJECTIVE": "Lock the objective and constraints",
    "SELECT_CONTEXT": "Activate the Winnipeg profile",
    "EXPLORE_MAP": "Load needs and community assets",
    "ADD_COMMUNITY_INPUT": "Decompose into bounded workstreams",
    "DECOMPOSE_WORK": "Compare four possible approaches",
    "COMPARE_SCENARIOS": "Review consent, objections, and gaps",
    "REVIEW_CONSENT": "Run a non-predictive What-If",
    "RUN_WHAT_IF": "Design the reversible 90-day pilot",
    "DESIGN_PILOT": "Assemble the non-binding decision packet",
    "REVIEW_PACKET": "Complete with human authority intact",
}

BLOCKED_ACTIONS = (
    {"action_id": "BINDING_VOTE", "label": "Cast a binding community vote", "reason": "Aura may preserve responses but cannot manufacture democratic authority."},
    {"action_id": "ALLOCATE_FUNDS", "label": "Allocate or spend public funds", "reason": "Funding requires authorized human and institutional approval."},
    {"action_id": "MAP_VULNERABLE_PEOPLE", "label": "Map person-level vulnerability", "reason": "Person-level homelessness, addiction, health, poverty, crime, and identity maps are prohibited."},
    {"action_id": "AUTO_SUBMIT", "label": "Submit to government automatically", "reason": "The showcase produces a non-binding review packet only."},
)


def _slots(*, direction: str, aspect: str, capability_class: str, subject: str, voice: str, stem: str) -> dict[str, str]:
    return {"DIR": direction, "ASP": aspect, "CLASS": capability_class, "SUBJ": subject, "VOICE": voice, "STEM": stem}


def _action(action_id: str, label: str, effect: str, weight: float, why: str, *, slots: dict[str, str], activates: tuple[str, ...] = (), args: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "label": label,
        "effect": effect,
        "route_weight": round(float(weight), 3),
        "why_available": why,
        "intent_slots": slots,
        "activates": list(activates),
        "args": dict(args or {}),
        "binding": False,
    }


def ranked_actions(
    step_id: str,
    *,
    next_step_id: str | None,
    can_advance: bool,
    can_go_back: bool,
    demo_issue_available: bool,
    project_id: str = "winnipeg_pathways",
) -> list[dict[str, Any]]:
    """Return the deterministic, inspectable action menu for one guide step.

    Weights rank appropriate next interactions for the demo. They do not grant
    civic authority and are not model confidence scores.
    """
    actions: list[dict[str, Any]] = []
    if can_advance and next_step_id:
        next_organs = tuple((STEP_DETAILS.get(next_step_id) or {}).get("actions") or ())
        actions.append(_action(
            "ADVANCE_STAGE",
            ADVANCE_LABELS.get(step_id, "Continue to the next governed stage"),
            "ADVANCE",
            .9,
            f"The current gate is reviewable and the next admitted stage is {next_step_id}.",
            slots=_slots(direction=next_step_id.lower(), aspect="bounded_once", capability_class="guided_transition", subject="human_reviewed_session", voice="human_guided", stem="advance"),
            activates=next_organs,
        ))

    actions.append(_action(
        "INSPECT_CURRENT_EVIDENCE",
        "Inspect evidence and authority limits",
        "INSPECT_EVIDENCE",
        .74,
        "Exact fixture records, organ receipts, and authority markers are available for inspection.",
        slots=_slots(direction="current_stage", aspect="read_only", capability_class="evidence", subject="showcase_participant", voice="inspect", stem="open"),
    ))

    if project_id == "winnipeg_pathways" and step_id in {"SELECT_CONTEXT", "EXPLORE_MAP", "ADD_COMMUNITY_INPUT"}:
        actions.append(_action(
            "FOCUS_TEST_COMMUNITY",
            "Focus the West Broadway synthetic test community",
            "FOCUS_TEST_COMMUNITY",
            .97 if step_id == "EXPLORE_MAP" else .78,
            "A recognizable Winnipeg street context helps people inspect the synthetic overlay without claiming live community data.",
            slots=_slots(direction="west_broadway_demo_zone", aspect="temporary_view", capability_class="governed_map", subject="community_viewer", voice="inspect", stem="focus"),
            args={"zoom": 14, "center": [-97.165, 49.8865]},
        ))

    if project_id == "winnipeg_pathways" and step_id == "EXPLORE_MAP":
        actions.extend([
            _action(
                "REVEAL_CANDIDATE",
                "Reveal the proposed staging site at governed zoom",
                "REVEAL_CANDIDATE",
                .94,
                "Candidate locations are intentionally suppressed below zoom 12 and may be revealed without weakening the policy.",
                slots=_slots(direction="candidate_site", aspect="temporary_view", capability_class="scenario_location", subject="community_viewer", voice="inspect", stem="reveal"),
                args={"zoom": 12, "center": [-97.176, 49.889]},
            ),
            _action(
                "RECORD_SERVICE_GAP",
                "Record a service-access concern",
                "PREFILL_RESPONSE",
                .86,
                "The map should lead to a preserved human question, not an automated conclusion.",
                slots=_slots(direction="community_record", aspect="append_only", capability_class="reservation", subject="showcase_participant", voice="human_statement", stem="record"),
                args={"response_type": "CONSENT_WITH_RESERVATION", "statement": "Evening transportation and accessible service distance must be reviewed before a pilot starts."},
            ),
        ])

    if step_id in {"ADD_COMMUNITY_INPUT", "REVIEW_CONSENT", "RUN_WHAT_IF", "DESIGN_PILOT"}:
        actions.append(_action(
            "RECORD_RESERVATION",
            "Preserve a reservation or missing voice",
            "PREFILL_RESPONSE",
            .88,
            "Unresolved concerns and representation gaps must remain visible before the project advances.",
            slots=_slots(direction="community_record", aspect="append_only", capability_class="consent_response", subject="showcase_participant", voice="human_statement", stem="record"),
            args={"response_type": "CONSENT_WITH_RESERVATION", "statement": "People with lived experience must review this stage before any real-world pilot is considered."},
        ))

    if demo_issue_available:
        actions.append(_action(
            "OPEN_HUMAN_AGENT_HANDOFF",
            "Investigate the map behavior in the Human Agent Arena",
            "OPEN_HANDOFF",
            .84,
            "The exact policy-versus-presentation question can be grounded without changing production.",
            slots=_slots(direction="coding_arena", aspect="review_only", capability_class="grounded_handoff", subject="human_agent_workflow", voice="proposal", stem="investigate"),
        ))

    if can_go_back:
        actions.append(_action(
            "REVIEW_PREVIOUS_STAGE",
            "Return to the previous stage",
            "BACK",
            .42,
            "The guide is reversible; returning does not erase the underlying evidence.",
            slots=_slots(direction="previous_stage", aspect="reversible", capability_class="guided_transition", subject="human_reviewed_session", voice="human_guided", stem="back"),
        ))

    return sorted(actions, key=lambda item: (-item["route_weight"], item["action_id"]))


def timeline(steps: tuple[str, ...], index: int) -> list[dict[str, Any]]:
    rows = []
    for position, step_id in enumerate(steps):
        detail = STEP_DETAILS.get(step_id, {"title": step_id, "actions": ()})
        rows.append({
            "index": position,
            "step_id": step_id,
            "title": detail["title"],
            "status": "COMPLETE" if position < index else ("ACTIVE" if position == index else "UPCOMING"),
            "organ_actions": list(detail.get("actions") or ()),
        })
    return rows


__all__ = ["ADVANCE_LABELS", "BLOCKED_ACTIONS", "STEP_DETAILS", "ranked_actions", "timeline"]
