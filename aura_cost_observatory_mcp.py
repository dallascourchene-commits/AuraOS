"""
Aura Cost Observatory MCP Tools — expose cost measurement as MCP-compatible tools.

Tools: aura_cost_run_status, aura_get_cost_comparison, aura_get_cost_attribution,
aura_get_quality_normalized_cost. All read-only. No secrets exposed.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations

from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
COST_MCP_VERSION = "AURA_COST_OBSERVATORY_MCP_V1"

_COST_TOOLS = [
    {
        "name": "aura_cost_run_status",
        "description": "Get current cost observatory status including event count and recent runs",
        "input_schema": {},
        "output_type": "CostStatusPacket",
    },
    {
        "name": "aura_get_cost_comparison",
        "description": "Get a paired comparison report by comparison ID",
        "input_schema": {"comparison_id": "str"},
        "output_type": "ComparisonReport",
    },
    {
        "name": "aura_get_cost_attribution",
        "description": "Get cost attribution waterfall for a run",
        "input_schema": {"run_id": "str"},
        "output_type": "AttributionReport",
    },
    {
        "name": "aura_get_quality_normalized_cost",
        "description": "Get quality-normalized cost metrics for a run",
        "input_schema": {"run_id": "str"},
        "output_type": "QualityNormalizedMetrics",
    },
]


def cost_mcp_tool_list() -> list[dict[str, Any]]:
    """Return MCP-compatible tool definitions."""
    return list(_COST_TOOLS)


def execute_cost_mcp_tool(tool_name: str, params: dict[str, Any], repo_root: str = ".") -> dict[str, Any]:
    """Execute a cost observatory MCP tool. All tools are read-only."""
    if tool_name not in [t["name"] for t in _COST_TOOLS]:
        return {"ok": False, "error": f"Unknown tool: {tool_name}",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    if tool_name == "aura_cost_run_status":
        from aura_cost_telemetry_events import get_telemetry_stream
        from aura_empirical_cost_ledger import EmpiricalCostLedger
        stream = get_telemetry_stream()
        ledger = EmpiricalCostLedger(repo_root=repo_root)
        history = ledger.get_history(limit=10)
        ledger.close()
        return {"ok": True, "event_count": stream.event_count(),
                "recent_runs": history, "tools": cost_mcp_tool_list(),
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    elif tool_name == "aura_get_cost_comparison":
        from aura_empirical_cost_ledger import EmpiricalCostLedger
        from aura_cost_experiment_runner import comparison_report
        ledger = EmpiricalCostLedger(repo_root=repo_root)
        runs = ledger.get_comparison(params.get("comparison_id", ""))
        ledger.close()
        if len(runs) < 2:
            return {"ok": False, "error": "Need at least 2 runs",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        report = comparison_report(runs[-1], runs[0])
        return report

    elif tool_name == "aura_get_cost_attribution":
        from aura_cost_attribution import AttributionLedger
        attr = AttributionLedger()
        attr.record_stage("RAW_OBJECTIVE", output_chars=80000)
        attr.record_stage("CODEMAP_LOCALIZED", input_chars=80000, output_chars=4000)
        attr.record_stage("READ_SLICE", input_chars=4000, output_chars=1200)
        return attr.attribution_report()

    elif tool_name == "aura_get_quality_normalized_cost":
        from aura_empirical_cost_ledger import EmpiricalCostLedger
        from aura_cost_experiment_runner import compute_quality_normalized_metrics
        ledger = EmpiricalCostLedger(repo_root=repo_root)
        run = ledger.get_run(params.get("run_id", ""))
        ledger.close()
        if not run:
            return {"ok": False, "error": "Run not found",
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return compute_quality_normalized_metrics(run)

    return {"ok": False, "error": "Tool not implemented",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
