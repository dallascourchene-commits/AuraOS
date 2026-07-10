"""
Aura Cockpit Swarm — multi-agent SwarmPlan builder.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SWARM_VERSION = "AURA_COCKPIT_SWARM_V1"

_AGENT_COMPAT = {
    "hermes": ["mitosis_decomposition_lane", "goap_planner_lane", "live_architect_lane",
               "research_arxiv_lane", "skillweaver_lane", "phase_capsule_lane"],
    "codex": ["mitosis_decomposition_lane", "goap_planner_lane", "skillweaver_lane"],
    "fireworks": ["music_coding_lane"],
    "local": ["goap_planner_lane", "phase_capsule_lane", "audit_staking_lane"],
    "mcp_agent": ["mcp_gateway_lane", "plugin_registry_lane"],
}


def build_swarm_plan(objective: str, agents: list[str] | None = None, repo_root: str = ".") -> dict:
    """Build a multi-agent swarm plan."""
    if not agents:
        agents = ["hermes"]
    assignments = []
    token_budgets = {}
    for agent in agents:
        role = "primary" if agent == agents[0] else "secondary"
        assignments.append({"agent": agent, "role": role, "lanes": _AGENT_COMPAT.get(agent, [])})
        token_budgets[agent] = 2000  # 2000 token budget per worker
    return {"ok": True, "objective": objective,
             "swarm_plan": {"agents": agents, "assignments": assignments, "token_budgets": token_budgets},
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
             "note": "No worker executes automatically. Human approval required before each handoff."}


def assign_agent_roles(objective: str, agents: list[str], repo_root: str = ".") -> dict:
    """Assign roles to agents."""
    assignments = []
    for i, agent in enumerate(agents):
        assignments.append({"agent": agent, "role": "primary" if i == 0 else "secondary",
                             "compatible_lanes": _AGENT_COMPAT.get(agent, [])})
    return {"ok": True, "assignments": assignments, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def agent_lane_compatibility(agent: str, repo_root: str = ".") -> dict:
    """Check which lanes an agent is compatible with."""
    return {"ok": True, "agent": agent,
             "compatible_lanes": _AGENT_COMPAT.get(agent, []),
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def swarm_plan_to_agent_handoffs(swarm_plan: dict, repo_root: str = ".") -> dict:
    """Convert swarm plan to individual agent handoff packets."""
    handoffs = []
    for assignment in swarm_plan.get("assignments", []):
        handoffs.append({"agent": assignment.get("agent", ""),
                          "role": assignment.get("role", ""),
                          "lanes": assignment.get("lanes", []),
                          "human_approval_required": True,
                          "patch_authority": PATCH_AUTHORITY,
                          "vsa_patch_authority": VSA_PATCH_AUTHORITY})
    return {"ok": True, "handoffs": handoffs, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}
