"""Review-only MCP-style tools for Aura Spatial Arena."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from aura_spatial_agent_bridge import AuraSpatialAgentBridge

SPATIAL_MCP_VERSION = "AURA_SPATIAL_MCP_V1"


class SpatialArenaMCPTools:
    """Small in-process tool surface; no direct renderer or domain mutation."""

    def __init__(self, repo_root: str | Path = ".", *, bridge: AuraSpatialAgentBridge | None = None) -> None:
        self.bridge = bridge or AuraSpatialAgentBridge(repo_root)

    def tool_manifest(self) -> dict[str, Any]:
        return {
            "version": SPATIAL_MCP_VERSION,
            "tools": [
                "spatial.status",
                "spatial.interact",
                "spatial.prove",
                "spatial.prove_browser_telemetry",
                "spatial.decide",
                "spatial.observatory",
                "spatial.restore_assessment",
                "spatial.dissolve",
            ],
            "construction_prepare_requires_typed_python_contracts": True,
            "raw_sensor_payloads_accepted": False,
            "domain_mutation": False,
            "automatic_execution": False,
            "automatic_merge": False,
            "human_review_required": True,
        }

    def call(self, tool_name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, Mapping):
            raise ValueError("MCP arguments must be an object")
        args = dict(arguments)
        if tool_name == "spatial.status":
            return self.bridge.status(str(args["run_id"]))
        if tool_name == "spatial.interact":
            return self.bridge.interact(
                str(args["run_id"]),
                action=args["action"],
                target_entity_ids=tuple(args["target_entity_ids"]),
                metadata=dict(args.get("metadata") or {}),
            )
        if tool_name == "spatial.prove":
            return self.bridge.prove(
                str(args["run_id"]),
                repo_head=str(args["repo_head"]),
                outcome=args.get("outcome", "PRESENTED"),
                evidence_class=args.get("evidence_class", "DERIVED"),
                metrics=dict(args.get("metrics") or {}),
                branch_name=str(args.get("branch_name") or ""),
            )
        if tool_name == "spatial.prove_browser_telemetry":
            telemetry = args.get("telemetry_packet")
            if not isinstance(telemetry, Mapping):
                raise ValueError("telemetry_packet must be an object")
            return self.bridge.prove_browser_telemetry(
                str(args["run_id"]),
                telemetry_packet=dict(telemetry),
                repo_head=str(args["repo_head"]),
                branch_name=str(args.get("branch_name") or ""),
            )
        if tool_name == "spatial.decide":
            return self.bridge.decide(
                str(args["run_id"]),
                decision=str(args["decision"]),
                decision_ref=str(args.get("decision_ref") or "human:pending"),
            )
        if tool_name == "spatial.observatory":
            return self.bridge.observatory(str(args["run_id"]))
        if tool_name == "spatial.restore_assessment":
            return self.bridge.restore_assessment(
                str(args["run_id"]),
                current_repo_head=str(args["current_repo_head"]),
            )
        if tool_name == "spatial.dissolve":
            return self.bridge.dissolve(
                str(args["run_id"]),
                renderer_cleanup_receipt=dict(args["renderer_cleanup_receipt"]),
                reason_code=str(args.get("reason_code") or "SPATIAL_ARENA_COMPLETE"),
            )
        raise ValueError(f"unknown Spatial MCP tool: {tool_name}")


__all__ = ["SPATIAL_MCP_VERSION", "SpatialArenaMCPTools"]
