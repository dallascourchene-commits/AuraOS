"""
Aura Cockpit Planner — GOAP + Phase Capsule planning.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
PLANNER_VERSION = "AURA_COCKPIT_PLANNER_V1"

_PHASES = [
    ("discovery", "Discover relevant files and symbols through CODEMAP."),
    ("grounding", "Ground through Coding Arena for exact source spans."),
    ("planning", "Plan the approach using FST routing and GOAP."),
    ("agent_handoff", "Prepare agent handoff packet."),
    ("patch", "Agent proposes patch through Arena staging."),
    ("verification", "Run verifier and tests."),
    ("repair", "Produce repair packet if tests fail."),
    ("approval", "Human approves commit."),
    ("pr", "Open pull request."),
]


def plan_objective_with_goap(objective: str, repo_root: str = ".",
                              initial_state: dict | None = None,
                              goal_conditions: dict | None = None) -> dict:
    """Plan objective with GOAP planner."""
    plan = {"phases": [], "actions": []}
    try:
        from aura_goal_planner import AuraGOAPPlanner
        planner = AuraGOAPPlanner()
        result = planner.plan(objective, initial_state or {}, goal_conditions or {})
        if hasattr(result, "actions"):
            plan["actions"] = [a.to_dict() if hasattr(a, "to_dict") else a for a in result.actions]
    except Exception:
        pass
    # Build phases
    for phase_name, desc in _PHASES:
        plan["phases"].append({
            "phase": phase_name, "description": desc,
            "allowed_actions": [f"{phase_name}_step"],
            "blocked_actions": ["patch"] if phase_name in ("discovery", "grounding", "planning") else [],
            "required_evidence": ["grounding_ok"] if phase_name == "grounding" else [],
            "token_budget": {},
            "output_packet": f"{phase_name}_packet",
            "human_approval_required": phase_name in ("agent_handoff", "approval", "pr"),
        })
    return {"ok": True, "objective": objective, "plan": plan,
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def objective_to_phase_capsules(objective: str, repo_root: str = ".") -> dict:
    """Decompose objective into phase capsules."""
    capsules = []
    for phase_name, desc in _PHASES:
        capsules.append({
            "phase": phase_name, "description": desc, "objective": objective,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        })
    return {"ok": True, "phase_capsules": capsules, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def phase_capsules_to_workflow_gates(phase_capsules: list, repo_root: str = ".") -> dict:
    """Map phase capsules to workflow gate states."""
    mapping = {
        "discovery": "CODEMAP_LOCALIZED", "grounding": "CODEMAP_LOCALIZED",
        "planning": "PLAN_READY", "agent_handoff": "HUMAN_APPROVED_FOR_AGENT",
        "patch": "PATCH_PROPOSED", "verification": "VERIFIED",
        "repair": "REPAIR_REQUIRED", "approval": "HUMAN_APPROVED_FOR_COMMIT",
        "pr": "PR_READY",
    }
    gate_mapping = []
    for cap in phase_capsules:
        phase = cap.get("phase", "")
        gate_mapping.append({"phase": phase, "gate": mapping.get(phase, "INGESTED")})
    return {"ok": True, "gate_mapping": gate_mapping, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def phase_capsules_to_agent_runbook(phase_capsules: list, repo_root: str = ".") -> dict:
    """Convert phase capsules to agent runbook."""
    steps = []
    for cap in phase_capsules:
        steps.append(f"# Phase: {cap.get('phase', '')}\n# Description: {cap.get('description', '')}")
    runbook = "\n\n".join(steps)
    return {"ok": True, "runbook": runbook, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}
