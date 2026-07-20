#!/usr/bin/env python3
"""Narrow CLI for validating and demonstrating the governed Spatial Arena."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaAdapter,
    ConstructionArenaMode,
)
from aura_construction_fixtures import build_sco_construction_demo_fixture
from aura_spatial_agent_bridge import AuraSpatialAgentBridge

SPATIAL_CLI_VERSION = "AURA_SPATIAL_CLI_V1"


def _head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    value = result.stdout.strip().lower()
    return value if result.returncode == 0 and 7 <= len(value) <= 64 else "0" * 40


def _validate_route(root: Path) -> dict[str, Any]:
    result = load_and_compile_arena_grammar(root / ".aura/arena_routes/spatial.v1.json")
    return {
        "ok": result.ok,
        "version": SPATIAL_CLI_VERSION,
        "route": result.to_dict(),
        "production_mutation": False,
        "automatic_merge": False,
    }


def _synthetic_construction_demo(root: Path) -> dict[str, Any]:
    fixture = build_sco_construction_demo_fixture()
    packet = ConstructionArenaAdapter().build_runtime_packet(
        objective="review synthetic Construction alternatives spatially",
        state=fixture.state,
        scope=fixture.focus_scope,
        candidates=fixture.candidates,
        now=10.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=fixture.probabilistic_signals,
    )
    with tempfile.TemporaryDirectory(prefix="aura-spatial-cli-") as state_dir:
        state_root = Path(state_dir)
        route_dir = state_root / ".aura" / "arena_routes"
        route_dir.mkdir(parents=True)
        shutil.copy2(root / ".aura/arena_routes/spatial.v1.json", route_dir / "spatial.v1.json")
        bridge = AuraSpatialAgentBridge(state_root)
        try:
            prepared = bridge.prepare_construction_projection(
                objective="review synthetic Construction alternatives spatially",
                state=fixture.state,
                construction_runtime_packet=packet,
            )
            run_id = prepared["run_id"]
            proof = bridge.prove(
                run_id,
                repo_head=_head(root),
                metrics={"fixture": "synthetic", "renderer_allocated": False},
            )
            decision = bridge.decide(run_id, decision="await authorized human Construction review")
            status = bridge.status(run_id)
            dissolution = bridge.dissolve(
                run_id,
                renderer_cleanup_receipt={
                    "state": "NOT_ALLOCATED",
                    "renderer_allocated": False,
                    "evidence_class": "CLIENT_REPORTED",
                    "session_id": status["session_id"],
                    "scene_digest": status["scene_digest"],
                    "render_plan_digest": status["render_plan_digest"],
                    "renderer_authority": False,
                    "execution_authority": False,
                },
                reason_code="SYNTHETIC_DEMO_COMPLETE",
            )
        finally:
            bridge.close()
    return {
        "ok": True,
        "version": SPATIAL_CLI_VERSION,
        "synthetic": True,
        "private_data_used": False,
        "production_connectors_used": False,
        "persistent_demo_state_written": False,
        "scene_digest": prepared["scene"]["scene_digest"],
        "render_plan_digest": prepared["render_plan"]["render_plan_digest"],
        "proof_receipt_id": proof["render_receipt"]["receipt_id"],
        "checkpoint_id": proof["checkpoint"]["checkpoint"]["checkpoint_id"],
        "decision_digest": decision["decision_packet"]["decision_digest"],
        "dissolution_digest": dissolution["dissolution_receipt"]["dissolution_digest"],
        "lease_released": dissolution["lease_released"],
        "renderer_allocated": dissolution["renderer_allocated"],
        "renderer_resources_released": dissolution["renderer_resources_released"],
        "renderer_resources_released_verified": dissolution["renderer_resources_released_verified"],
        "renderer_resource_boundary_satisfied": dissolution["renderer_resource_boundary_satisfied"],
        "physical_work_authorized": False,
        "payment_released": False,
        "access_controlled": False,
        "automatic_merge": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-route")
    subparsers.add_parser("synthetic-construction-demo")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    packet = _validate_route(root) if args.command == "validate-route" else _synthetic_construction_demo(root)
    print(json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str))
    return 0 if packet.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
