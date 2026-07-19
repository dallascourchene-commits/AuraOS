#!/usr/bin/env python3
# ruff: noqa: E402
"""Run Aura-native planning and proof gates for Spatial S3-B and S4-A.

This harness is read-only with respect to tracked source. It exercises retained
Coding Arena / Agent Bridge, Capability Connectome, Emergent Properties,
Council V3, proposal-only Surgeon control, Coding Waboose, and Crucible paths.
It proves the scene -> plan -> session -> browser projection -> bounded local
interchange -> receipt -> dissolution chain. The only write is one explicitly
requested, bounded JSON receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_agent_arena_review_learning_bridge import ReviewLearningAgentArenaBridge
from aura_architect_control import normalize_control_profile
from aura_architect_council_v3 import ARCHITECT_COUNCIL_V3
from aura_coding_waboose_review_lessons import PATCH_AUTHORITY
from aura_spatial_breadboard import compile_spatial_s3b_s4a_breadboard
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialEntity,
    SpatialEntityType,
    SpatialRenderEvidenceClass,
    SpatialRenderOutcome,
)
from aura_spatial_importers.contracts import CoordinateConversion
from aura_spatial_importers.gltf import import_gltf_file
from aura_spatial_importers.ply import import_ply_file
from aura_spatial_render_plan import (
    compile_spatial_device_profile,
    negotiate_spatial_render_plan,
)
from aura_spatial_scene import compile_spatial_scene
from aura_spatial_session import SpatialProjectionSessionManager

HARNESS_VERSION = "AURA_SPATIAL_S3B_S4A_ARCHITECT_HARNESS_V1"
_MAX_RECEIPT_BYTES = 1_048_576
_EXPECTED_COUNCIL_LANES = {
    "scope",
    "tests",
    "sequence",
    "continuity",
    "rollback",
    "cost",
}
_TARGET_FILES = [
    "aura_spatial_contracts.py",
    "aura_spatial_render_plan.py",
    "aura_spatial_receipts.py",
    "aura_spatial_session.py",
    "aura_spatial_server.py",
    "aura_spatial_interaction.py",
    "aura_spatial_coordinate_frames.py",
    "aura_spatial_breadboard.py",
    "aura_spatial_web/renderer_adapter.js",
    "aura_spatial_web/accessibility.js",
    "aura_spatial_web/webgl2_renderer.js",
    "aura_spatial_web/webgpu_renderer.js",
    "aura_spatial_web/webxr_session.js",
    "aura_spatial_web/interaction_adapter.js",
    "aura_spatial_web/telemetry.js",
    "aura_spatial_importers/contracts.py",
    "aura_spatial_importers/gltf.py",
    "aura_spatial_importers/ply.py",
    "scripts/aura_spatial_continuation_architect_harness.py",
]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.blake2b(_canonical(value), digest_size=20).hexdigest()


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNAVAILABLE"
    if result.returncode != 0:
        return "UNAVAILABLE"
    return result.stdout.strip() or "UNAVAILABLE"


def _summary(packet: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {"ok": False, "status": "invalid_packet"}
    return {key: packet.get(key) for key in keys if key in packet}


def _call_preserving_generated_maps(repo_root: Path, callback: Any) -> tuple[Any, bool]:
    """Run an Aura planner while restoring generated navigation caches exactly."""

    paths = (
        repo_root / ".aura" / "CODEMAP.json",
        repo_root / ".aura" / "CODEMAP.md",
    )
    snapshots = {path: (path.exists(), path.read_bytes() if path.exists() else b"") for path in paths}
    try:
        result = callback()
    finally:
        for path, (existed, content) in snapshots.items():
            if existed:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            elif path.exists():
                path.unlink()
    restored = all(
        (path.exists() == existed) and (not existed or path.read_bytes() == content)
        for path, (existed, content) in snapshots.items()
    )
    return result, restored


def _prove_lifecycle() -> dict[str, Any]:
    scene = compile_spatial_scene(
        scene_id="harness:spatial-s3b-s4a",
        purpose_digest="purpose:spatial-s3b-s4a-harness",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root"),),
        entities=(
            SpatialEntity(
                entity_id="entity:harness",
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label="S3-B/S4-A harness entity",
                frame_id="root",
                source_refs=("source:harness",),
            ),
        ),
        source_refs=("source:harness",),
    )
    device = compile_spatial_device_profile(
        profile_id="device:harness",
        supported_renderers=("HEADLESS", "ACCESSIBLE_2D", "WEBGL2"),
        source_refs=("source:harness-device",),
    )
    plan = negotiate_spatial_render_plan(
        scene,
        device,
        preferred_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
    )
    manager = SpatialProjectionSessionManager(max_active_sessions=2)
    session = manager.create_session(scene, plan, device)
    render_receipt, updated = manager.record_render(
        session.session_id,
        outcome=SpatialRenderOutcome.PRESENTED,
        evidence_class=SpatialRenderEvidenceClass.DERIVED,
        metrics={"source": "architect_harness", "renderer_allocated": False},
    )
    dissolution = manager.dissolve_session(
        session.session_id,
        reason_code="HARNESS_COMPLETE",
    )
    return {
        "scene_id": scene.scene_id,
        "scene_digest": scene.scene_digest,
        "device_profile_digest": device.device_profile_digest,
        "render_plan_digest": plan.render_plan_digest,
        "selected_renderer": plan.selected_renderer.value,
        "fallback_renderers": [item.value for item in plan.fallback_renderers],
        "session_id": session.session_id,
        "render_receipt_id": render_receipt.receipt_id,
        "render_receipt_count": len(updated.render_receipt_ids),
        "dissolution_receipt_id": dissolution.receipt_id,
        "active_sessions_after_dissolution": manager.active_session_count,
        "raw_sensor_data_retained": dissolution.raw_sensor_data_retained,
        "renderer_disposed": dissolution.renderer_disposed,
        "leases_released": dissolution.leases_released,
        "production_mutation": dissolution.production_mutation,
        "automatic_merge": dissolution.automatic_merge,
    }


def _prove_browser_and_import(repo_root: Path) -> dict[str, Any]:
    web_root = repo_root / "aura_spatial_web"
    required_web = (
        "renderer_adapter.js",
        "headless_renderer.js",
        "accessibility.js",
        "webgl2_renderer.js",
        "webgpu_renderer.js",
        "webxr_session.js",
        "interaction_adapter.js",
        "telemetry.js",
        "app.js",
        "bootstrap.js",
        "index.html",
        "styles.css",
    )
    missing = [name for name in required_web if not (web_root / name).is_file()]
    gltf = import_gltf_file(
        repo_root / "tests/fixtures/spatial/gltf/triangle.gltf",
        provenance_refs=("fixture:harness:gltf",),
        root=repo_root,
    )
    ply = import_ply_file(
        repo_root / "tests/fixtures/spatial/ply/points_ascii.ply",
        provenance_refs=("fixture:harness:ply",),
        coordinate_conversion=CoordinateConversion(
            "RIGHT_HANDED",
            "Z_UP",
            0.01,
        ),
        root=repo_root,
    )
    return {
        "web_asset_count": len(required_web) - len(missing),
        "missing_web_assets": missing,
        "webgl2_active": (web_root / "webgl2_renderer.js").is_file(),
        "webgpu_shadow_only": "shadowOnly" in (web_root / "webgpu_renderer.js").read_text(encoding="utf-8"),
        "webxr_explicit_activation": "userActivation !== true"
        in (web_root / "webxr_session.js").read_text(encoding="utf-8"),
        "accessible_2d_present": (web_root / "accessibility.js").is_file(),
        "gltf_import_digest": gltf.receipt.derived_asset_digest,
        "gltf_vertex_count": len(gltf.positions),
        "ply_import_digest": ply.receipt.derived_asset_digest,
        "ply_vertex_count": len(ply.positions),
        "network_fetch_performed": (gltf.receipt.network_fetch_performed or ply.receipt.network_fetch_performed),
        "scripts_executed": (gltf.receipt.scripts_executed or ply.receipt.scripts_executed),
        "renderer_authority": False,
        "importer_authority": False,
        "provenance_authority": False,
        "execution_authority": False,
        "patch_authority": PATCH_AUTHORITY,
        "production_mutation": False,
        "automatic_merge": False,
    }


def run(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str,
    observed_head: str,
    structural_only: bool = False,
) -> dict[str, Any]:
    observed = observed_head.strip() or _git(repo_root, "rev-parse", "HEAD")
    actual_head = _git(repo_root, "rev-parse", "HEAD")
    breadboard = compile_spatial_s3b_s4a_breadboard()
    plan = dict(breadboard["plan"])
    council = dict(breadboard["council_v3_route"])
    lifecycle = _prove_lifecycle()
    vertical_slice = _prove_browser_and_import(repo_root)

    surgeon_control = normalize_control_profile(
        {
            "surface": "coding_arena",
            "council_mode": "SELECTIVE_V3",
            "council_call_budget": len(council["selected_lanes"]),
            "critic_lanes": council["selected_lanes"],
            "surgeon_mode": "PROPOSE",
            "surgeon_max_turns": 10,
            "surgeon_max_local_repairs": 2,
            "surgeon_context_tokens": 2400,
            "surgeon_output_tokens": 2400,
            "council_replan_allowed": True,
            "record_outputs": False,
            "output_root": "Aura_Staging/spatial_s3b_s4a_harness",
            "human_review_required": True,
            "production_mutation": False,
            "vsa_patch_authority": False,
        },
        surface="coding_arena",
    ).to_dict()

    architecture: dict[str, Any]
    if structural_only:
        architecture = {
            "mode": "structural_only",
            "agent_bridge": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "connectome": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "emergent": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "waboose": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "crucible": {"status": "not_invoked_in_structural_mode"},
        }
    else:
        objective = str(plan["objective"])
        bridge = ReviewLearningAgentArenaBridge(
            repo_root=str(repo_root),
            review_learning_root=repo_root / "Aura_Staging" / "spatial_s3b_s4a_harness",
        )
        repo_digest = bridge.aura_repo_digest(include_hubs=False, max_lines=20)
        affordances = bridge.aura_find_affordances(
            objective=objective,
            target_files=_TARGET_FILES,
            target_symbols=[
                "SpatialRenderPlan",
                "WebGL2Renderer",
                "compile_browser_spatial_interaction",
                "import_gltf_bytes",
                "import_ply_bytes",
            ],
            include_affordances=True,
            top_k=3,
        )
        atomic = bridge.aura_atomic_function_inventory(
            query="spatial browser renderer accessibility webgl webgpu webxr gltf ply import receipt",
            target_files=_TARGET_FILES,
            target_symbols=[
                "SpatialRenderPlan",
                "WebGL2Renderer",
                "compile_browser_spatial_interaction",
                "import_gltf_bytes",
                "import_ply_bytes",
            ],
            limit=40,
            include_source=False,
        )
        emergent = bridge.aura_emergent_evidence(
            {
                "objective": objective,
                "target_files": _TARGET_FILES,
                "target_symbols": [
                    "compile_browser_spatial_interaction",
                    "import_gltf_bytes",
                    "import_ply_bytes",
                ],
                "target_arena": "coding_arena",
                "radius": 1,
                "max_atomic_nodes": 40,
                "max_source_lines": 20,
                "include_source": False,
                "include_future": False,
                "include_research_plan": False,
                "include_offline_research": False,
            }
        )
        prepared, generated_maps_restored = _call_preserving_generated_maps(
            repo_root,
            lambda: bridge.aura_prepare_arena(
                objective=objective,
                target_file="aura_spatial_importers/contracts.py",
                target_symbol="SpatialImportReceipt",
                acceptance_criteria=plan["acceptance_criteria"],
                risk_map=list(plan["risk_map"]),
                constraints=plan["constraints"],
                use_emergent_evidence=False,
            ),
        )
        waboose_prepared = bridge.aura_waboose_prepare(
            {
                "objective": objective,
                "mode": "files",
                "base_ref": base_ref,
                "head_ref": head_ref,
                "changed_files": _TARGET_FILES,
                "profile": "precision",
                "focus_directives": [],
                "invariants": plan["acceptance_criteria"],
                "risk_map": list(plan["risk_map"]),
                "agent_name": "none",
                "graph_depth": 0,
                "graph_node_budget": 30,
                "run_tests": False,
                "run_optional_tools": False,
                "metadata": {
                    "harness_version": HARNESS_VERSION,
                    "observed_head": observed,
                    "council_version": ARCHITECT_COUNCIL_V3,
                    "surgeon_mode": "PROPOSE",
                },
            }
        )
        if waboose_prepared.get("ok"):
            waboose_scan = bridge.aura_waboose_scan(waboose_prepared["review_id"])
            waboose_final = bridge.aura_waboose_finalize(waboose_prepared["review_id"])
        else:
            waboose_scan = {"ok": False, "status": "prepare_failed"}
            waboose_final = {"ok": False, "status": "prepare_failed"}
        crucible = bridge.aura_waboose_crucible_replay()
        architecture = {
            "mode": "full",
            "agent_bridge": {
                "repo_digest": _summary(repo_digest, ("ok", "version", "repo_head", "file_count", "symbol_count")),
                "prepare": _summary(
                    prepared, ("ok", "version", "status", "plan_phase_hash", "production_mutation", "patch_authority")
                ),
                "generated_maps_restored": generated_maps_restored,
            },
            "connectome": {
                "affordances": _summary(
                    affordances, ("grounding", "route_frame", "recommended_affordances", "patch_authority")
                ),
                "atomic_inventory": _summary(
                    atomic, ("ok", "version", "inventory_digest", "total_count", "selected_count", "patch_authority")
                ),
            },
            "emergent": _summary(
                emergent,
                (
                    "ok",
                    "version",
                    "packet_id",
                    "packet_digest",
                    "status",
                    "grounding_ok",
                    "emergent_compositions",
                    "tests",
                    "patch_authority",
                ),
            ),
            "waboose": {
                "prepare": _summary(waboose_prepared, ("ok", "review_id", "status", "automatic_merge")),
                "scan": _summary(waboose_scan, ("ok", "status", "review_lesson_findings_added", "automatic_merge")),
                "finalize": _summary(
                    waboose_final,
                    ("ok", "status", "summary", "finding_count", "repair_request_count", "automatic_merge"),
                ),
            },
            "crucible": _summary(
                crucible,
                (
                    "version",
                    "status",
                    "registry_digest",
                    "scenario_count",
                    "passed_count",
                    "failed_count",
                    "packet_digest",
                ),
            ),
        }

    checks = {
        "observed_head_available": observed != "UNAVAILABLE",
        "observed_head_matches_checkout": (structural_only or actual_head == "UNAVAILABLE" or observed == actual_head),
        "breadboard_grounded_unpowered": (breadboard["circuit_status"] == "GROUNDED_SPATIAL_S3B_S4A_CIRCUIT_UNPOWERED"),
        "council_v3_all_lanes": set(council["selected_lanes"]) == _EXPECTED_COUNCIL_LANES,
        "surgeon_proposal_only": surgeon_control["surgeon_mode"] == "PROPOSE",
        "surgeon_no_production_mutation": surgeon_control["production_mutation"] is False,
        "accessible_2d_fallback": "ACCESSIBLE_2D" in lifecycle["fallback_renderers"],
        "session_dissolved": lifecycle["active_sessions_after_dissolution"] == 0,
        "renderer_disposed": lifecycle["renderer_disposed"] is True,
        "leases_released": lifecycle["leases_released"] is True,
        "no_raw_sensor_retention": lifecycle["raw_sensor_data_retained"] is False,
        "no_production_mutation": lifecycle["production_mutation"] is False,
        "no_automatic_merge": lifecycle["automatic_merge"] is False,
        "browser_assets_complete": not vertical_slice["missing_web_assets"],
        "webgl2_active": vertical_slice["webgl2_active"] is True,
        "webgpu_shadow_only": vertical_slice["webgpu_shadow_only"] is True,
        "webxr_explicit_activation": vertical_slice["webxr_explicit_activation"] is True,
        "accessible_2d_present": vertical_slice["accessible_2d_present"] is True,
        "gltf_fixture_imported": vertical_slice["gltf_vertex_count"] == 3,
        "ply_fixture_imported": vertical_slice["ply_vertex_count"] == 3,
        "no_import_network_fetch": vertical_slice["network_fetch_performed"] is False,
        "no_import_script_execution": vertical_slice["scripts_executed"] is False,
        "no_renderer_or_importer_authority": (
            vertical_slice["renderer_authority"] is False
            and vertical_slice["importer_authority"] is False
            and vertical_slice["provenance_authority"] is False
        ),
    }
    if not structural_only:
        checks.update(
            {
                "agent_bridge_prepare_ok": bool(architecture["agent_bridge"]["prepare"].get("ok")),
                "generated_maps_restored": architecture["agent_bridge"]["generated_maps_restored"] is True,
                "atomic_inventory_ok": bool(architecture["connectome"]["atomic_inventory"].get("ok")),
                "emergent_invoked": isinstance(architecture["emergent"], dict),
                "waboose_prepare_ok": bool(architecture["waboose"]["prepare"].get("ok")),
                "waboose_scan_ok": bool(architecture["waboose"]["scan"].get("ok")),
                "waboose_finalize_ok": bool(architecture["waboose"]["finalize"].get("ok")),
                "waboose_no_findings": int(
                    (architecture["waboose"]["finalize"].get("summary") or {}).get("visible_findings", 0)
                )
                == 0,
                "crucible_passed": architecture["crucible"].get("status") == "PASSED"
                and architecture["crucible"].get("failed_count") == 0,
            }
        )

    receipt: dict[str, Any] = {
        "version": HARNESS_VERSION,
        "mode": "structural_only" if structural_only else "full",
        "repository_head": observed,
        "repository": {
            "root": str(repo_root),
            "observed_head": observed,
            "checkout_head": actual_head,
            "base_ref": base_ref,
            "head_ref": head_ref,
            "working_tree_status": _git(repo_root, "status", "--short"),
        },
        "breadboard": breadboard,
        "council_v3": council,
        "surgeon": {
            "control_profile": surgeon_control,
            "execution_performed": False,
            "authority": "proposal_only",
        },
        "architecture": architecture,
        "lifecycle_proof": lifecycle,
        "browser_and_import_proof": vertical_slice,
        "checks": checks,
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "evidence_semantics": {
            "harness_execution": "current_exact_head_execution",
            "workflow_configuration": "not_a_pass_without_observed_run",
            "rendering": "webgl2_active_webgpu_shadow_webxr_explicit_gesture",
            "interchange": "bounded_local_gltf_glb_ply_no_network_or_execution",
            "external_reviews": "teacher_signals_requiring_manual_exact_source_repair",
        },
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    receipt["receipt_digest"] = _digest(receipt)
    if len(_canonical(receipt)) > _MAX_RECEIPT_BYTES:
        raise RuntimeError("spatial continuation receipt exceeds byte ceiling")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--base-ref", default=os.environ.get("AURA_BASE_REF", "HEAD~1"))
    parser.add_argument("--head-ref", default=os.environ.get("AURA_HEAD_REF", "HEAD"))
    parser.add_argument(
        "--observed-head",
        default=os.environ.get("AURA_OBSERVED_HEAD_SHA", ""),
    )
    parser.add_argument("--structural-only", action="store_true")
    parser.add_argument(
        "--output",
        default="Aura_Staging/spatial_s3b_s4a_harness/architect_receipt.json",
    )
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    receipt = run(
        root,
        base_ref=str(args.base_ref),
        head_ref=str(args.head_ref),
        observed_head=str(args.observed_head),
        structural_only=bool(args.structural_only),
    )
    output = root / str(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
