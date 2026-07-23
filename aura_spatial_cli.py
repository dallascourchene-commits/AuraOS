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
from aura_construction_demo_director import (
    CONSTRUCTION_DEMO_TOURS,
    compile_construction_demo_packet,
    serve_construction_demo,
    write_construction_demo_packet,
)
from aura_construction_fixtures import build_sco_construction_demo_fixture
from aura_spatial_agent_bridge import AuraSpatialAgentBridge

SPATIAL_CLI_VERSION = "AURA_SPATIAL_CLI_V2"


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


def _construction_video_demo(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    asset_pack = Path(args.asset_pack) if args.asset_pack else None
    packet = compile_construction_demo_packet(asset_pack_path=asset_pack, tour=args.tour)
    output_path = None
    if args.output:
        output_path = write_construction_demo_packet(packet, Path(args.output))
    summary = {
        "ok": True,
        "version": SPATIAL_CLI_VERSION,
        "command": "construction-video-demo",
        "tour": args.tour,
        "scene_digest": packet["scene"]["scene_digest"],
        "render_plan_digest": packet["render_plan"]["render_plan_digest"],
        "fixture_digest": packet["fixture_digest"],
        "asset_pack_digest": packet["asset_pack_digest"],
        "fallback_asset_pack": packet["fallback_asset_pack"],
        "output": str(output_path) if output_path else None,
        "url": f"http://{args.host}:{args.port}/demo/construction?tour={args.tour}",
        "physical_work_authorized": False,
        "payment_released": False,
        "automatic_execution": False,
        "automatic_merge": False,
        "human_review_required": True,
    }
    if args.serve:
        print(json.dumps(summary, sort_keys=True, separators=(",", ":"), default=str), flush=True)
        serve_construction_demo(root, packet, host=args.host, port=args.port)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-route")
    subparsers.add_parser("synthetic-construction-demo")
    video = subparsers.add_parser("construction-video-demo")
    video.add_argument("--asset-pack")
    video.add_argument("--tour", choices=CONSTRUCTION_DEMO_TOURS, default="full")
    video.add_argument("--host", default="127.0.0.1")
    video.add_argument("--port", type=int, default=8767)
    video.add_argument("--output")
    video.add_argument("--serve", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    if args.command == "validate-route":
        packet = _validate_route(root)
    elif args.command == "synthetic-construction-demo":
        packet = _synthetic_construction_demo(root)
    else:
        packet = _construction_video_demo(root, args)
        if args.serve:
            return 0
    print(json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str))
    return 0 if packet.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
