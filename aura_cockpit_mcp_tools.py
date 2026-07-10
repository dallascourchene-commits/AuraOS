"""
Aura Cockpit MCP Tools — expose cockpit operations as MCP-compatible tools.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
MCP_TOOLS_VERSION = "AURA_COCKPIT_MCP_TOOLS_V1"

_COCKPIT_TOOLS = [
    {"name": "list_capability_lanes", "description": "List all cockpit capability lanes", "input_schema": {}, "output_type": "LaneRegistryPacket"},
    {"name": "route_capability_lanes", "description": "Route an objective to lanes", "input_schema": {"objective": "str"}, "output_type": "CapabilityRoutePacket"},
    {"name": "run_music_rank", "description": "Run MUSIC advisory ranking", "input_schema": {"objective": "str"}, "output_type": "MusicRankPacket"},
    {"name": "split_mitosis", "description": "Split objective into child capsules", "input_schema": {"objective": "str"}, "output_type": "MitosisSplitPacket"},
    {"name": "search_research_manifest", "description": "Search research manifest", "input_schema": {"query": "str"}, "output_type": "ResearchEvidencePacket"},
    {"name": "recall_paper_memory", "description": "Recall from paper memory", "input_schema": {"query": "str"}, "output_type": "PaperMemoryPacket"},
    {"name": "discover_skills", "description": "Discover skills for objective", "input_schema": {"objective": "str"}, "output_type": "SkillDiscoveryPacket"},
    {"name": "plan_goap", "description": "Plan with GOAP", "input_schema": {"objective": "str"}, "output_type": "GOAPPlanPacket"},
    {"name": "build_swarm_plan", "description": "Build multi-agent swarm plan", "input_schema": {"objective": "str", "agents": "list"}, "output_type": "SwarmPlanPacket"},
    {"name": "create_phase_capsules", "description": "Create phase capsules", "input_schema": {"objective": "str"}, "output_type": "PhaseCapsulePacket"},
    {"name": "stage_live_architect_review", "description": "Create live architect stage plan", "input_schema": {"objective": "str"}, "output_type": "LiveArchitectPlanPacket"},
    {"name": "export_audit_trace", "description": "Export audit packet", "input_schema": {}, "output_type": "AuditTrailPacket"},
]


def list_capability_lanes(repo_root: str = ".") -> dict:
    return {"ok": True, "tools": _COCKPIT_TOOLS, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def route_capability_lanes_mcp(objective: str, repo_root: str = ".") -> dict:
    from aura_cockpit_capability_router import route_capability_lanes
    result = route_capability_lanes(objective)
    return {"ok": True, "route_packet": result, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def cockpit_mcp_tool_list(repo_root: str = ".") -> list[dict]:
    return list(_COCKPIT_TOOLS)


def register_cockpit_mcp_tools(repo_root: str = ".") -> dict:
    try:
        from aura_mcp_gateway import AuraMCPGateway, AuraMCPTool
        gateway = AuraMCPGateway()
        registered_count = 0
        for tool_def in _COCKPIT_TOOLS:
            try:
                # Create a minimal tool wrapper for each definition
                tool = AuraMCPTool(
                    tool_name=tool_def["name"],
                    description=tool_def["description"],
                    input_schema=tool_def.get("input_schema", {}),
                    required_inputs=list(tool_def.get("input_schema", {}).keys()),
                    handler=lambda args, **kwargs: {"ok": True, "result": "placeholder"},
                    aura_safe=True,
                )
                gateway.register(tool)
                registered_count += 1
            except Exception:
                pass
        return {"ok": True, "registered": registered_count, "patch_authority": PATCH_AUTHORITY,
                 "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    except Exception:
        return {"ok": False, "registered": 0, "note": "MCP gateway creation failed",
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
