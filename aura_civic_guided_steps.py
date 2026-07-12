"""Step metadata for Aura's guided Civic projects."""
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
