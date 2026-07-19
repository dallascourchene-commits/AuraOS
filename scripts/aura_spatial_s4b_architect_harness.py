#!/usr/bin/env python3
# ruff: noqa: E402
"""Run exact-head Aura-native architecture and S4-B Gaussian proof gates."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_agent_arena_review_learning_bridge import ReviewLearningAgentArenaBridge
from aura_spatial_asset_registry import build_imported_asset_manifest
from aura_spatial_contracts import CoordinateFrame, SpatialEntity, SpatialEntityType
from aura_spatial_importers.contracts import CoordinateConversion
from aura_spatial_importers.gaussian_gltf import KHR_GAUSSIAN_PROFILE, import_gaussian_gltf_bytes
from aura_spatial_importers.gltf import import_gltf_file
from aura_spatial_importers.ply import import_ply_file
from aura_spatial_importers.spz import SPZ_FORMAT_VERSION, import_spz_bytes
from aura_spatial_render_plan import (
    compile_gaussian_representation_budget,
    compile_spatial_device_profile,
    negotiate_spatial_render_plan,
)
from aura_spatial_scene import compile_spatial_scene
from scripts.aura_spatial_continuation_architect_harness import run as run_retained_harness

HARNESS_VERSION = "AURA_SPATIAL_S4B_ARCHITECT_HARNESS_V1"
_TARGET_FILES = [
    "aura_spatial_asset_registry.py",
    "aura_spatial_render_plan.py",
    "aura_spatial_importers/contracts.py",
    "aura_spatial_importers/gltf.py",
    "aura_spatial_importers/spz.py",
    "aura_spatial_importers/gaussian_gltf.py",
    "aura_spatial_web/gaussian_renderer.js",
    "tests/test_aura_spatial_spz.py",
    "tests/test_aura_spatial_gaussian_gltf.py",
    "tests/test_aura_spatial_mixed_scene.py",
    "tests/test_aura_spatial_asset_security.py",
    "tests/js/spatial-gaussian.test.mjs",
    "tests/js/spatial-mixed-scene.test.mjs",
    "docs/AURA_SPATIAL_DEPENDENCY_DECISIONS.md",
    "docs/AURA_SPATIAL_FORMAT_AND_COORDINATE_POLICY.md",
    "scripts/aura_spatial_s4b_architect_harness.py",
]
_TARGET_SYMBOLS = [
    "GaussianSplatData",
    "import_spz_bytes",
    "import_gaussian_gltf_bytes",
    "GaussianRenderer",
    "compile_gaussian_representation_budget",
]
_MAX_RECEIPT_BYTES = 1_048_576
_HEADER = struct.Struct("<IIIBBBBI12s")
_TOC = struct.Struct("<QQ")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _summary(packet: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {"ok": False, "status": "invalid_packet"}
    return {key: packet.get(key) for key in keys if key in packet}


def _call_preserving_generated_maps(repo_root: Path, callback: Any) -> tuple[Any, bool]:
    paths = (repo_root / ".aura" / "CODEMAP.json", repo_root / ".aura" / "CODEMAP.md")
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
        path.exists() == existed and (not existed or path.read_bytes() == content)
        for path, (existed, content) in snapshots.items()
    )
    return result, restored


def _run_s4b_architecture(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str,
    observed_head: str,
) -> dict[str, Any]:
    objective = (
        "Implement bounded Gaussian interoperability and adversarial asset security without authority escalation"
    )
    bridge = ReviewLearningAgentArenaBridge(
        repo_root=str(repo_root),
        review_learning_root=repo_root / "Aura_Staging" / "spatial_s4b_harness",
    )
    repo_digest = bridge.aura_repo_digest(include_hubs=False, max_lines=20)
    affordances = bridge.aura_find_affordances(
        objective=objective,
        target_files=_TARGET_FILES,
        target_symbols=_TARGET_SYMBOLS,
        include_affordances=True,
        top_k=3,
    )
    atomic = bridge.aura_atomic_function_inventory(
        query="SPZ Gaussian glTF renderer budgets asset security fallback",
        target_files=_TARGET_FILES,
        target_symbols=_TARGET_SYMBOLS,
        limit=40,
        include_source=False,
    )
    emergent = bridge.aura_emergent_evidence(
        {
            "objective": objective,
            "target_files": _TARGET_FILES,
            "target_symbols": _TARGET_SYMBOLS,
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
    prepared, maps_restored = _call_preserving_generated_maps(
        repo_root,
        lambda: bridge.aura_prepare_arena(
            objective=objective,
            target_file="aura_spatial_importers/spz.py",
            target_symbol="import_spz_bytes",
            acceptance_criteria=[
                "all attacker-controlled bytes are bounded before allocation",
                "Gaussian representations retain point, accessible, and headless fallbacks",
                "no importer or renderer gains truth or execution authority",
                "no capture or training path exists",
            ],
            risk_map=[
                "decompression bomb",
                "format drift",
                "GPU or sort allocation bypass",
                "fallback overclaim",
                "provenance ambiguity",
            ],
            constraints={
                "proposal_only": True,
                "automatic_fix": False,
                "automatic_merge": False,
                "observed_head": observed_head,
            },
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
            "focus_directives": [
                "allocation before validation",
                "decompression and count overflow",
                "fallback claims without execution evidence",
                "renderer or imported representation authority escalation",
            ],
            "invariants": [
                "projection_only",
                "no_network_fetch",
                "no_training",
                "exact_head_evidence",
            ],
            "risk_map": [
                "untrusted binary parsing",
                "GPU memory pressure",
                "recursive metadata",
                "coordinate basis drift",
            ],
            "agent_name": "none",
            "graph_depth": 0,
            "graph_node_budget": 30,
            "run_tests": False,
            "run_optional_tools": False,
            "metadata": {
                "harness_version": HARNESS_VERSION,
                "observed_head": observed_head,
                "phase": "S4-B",
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
    return {
        "agent_bridge": {
            "repo_digest": _summary(repo_digest, ("ok", "version", "repo_head", "file_count", "symbol_count")),
            "prepare": _summary(
                prepared,
                ("ok", "version", "status", "plan_phase_hash", "production_mutation", "patch_authority"),
            ),
            "generated_maps_restored": maps_restored,
        },
        "connectome": {
            "affordances": _summary(
                affordances,
                ("grounding", "route_frame", "recommended_affordances", "patch_authority"),
            ),
            "atomic_inventory": _summary(
                atomic,
                ("ok", "version", "inventory_digest", "total_count", "selected_count", "patch_authority"),
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


def _spz_fixture() -> bytes:
    import zstandard

    raw_streams = (
        b"\x00" * 9,
        b"\xff",
        b"\xff\x80\x00",
        b"\xa0\xa0\xa0",
        b"\x00\x00\x00\xc0",
    )
    compressor = zstandard.ZstdCompressor(level=1)
    compressed = tuple(compressor.compress(item) for item in raw_streams)
    header = _HEADER.pack(
        0x5053474E,
        SPZ_FORMAT_VERSION,
        1,
        0,
        12,
        0,
        len(raw_streams),
        _HEADER.size,
        b"\x00" * 12,
    )
    toc = b"".join(_TOC.pack(len(blob), len(raw)) for blob, raw in zip(compressed, raw_streams))
    return header + toc + b"".join(compressed)


def _gaussian_gltf_fixture() -> bytes:
    chunks: list[bytes] = []
    views: list[dict[str, int]] = []
    accessors: list[dict[str, Any]] = []

    def add(data: bytes, component_type: int, kind: str, *, normalized: bool = False) -> int:
        offset = sum(len(item) for item in chunks)
        chunks.append(data)
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data)})
        accessor: dict[str, Any] = {
            "bufferView": len(views) - 1,
            "componentType": component_type,
            "count": 1,
            "type": kind,
        }
        if normalized:
            accessor["normalized"] = True
        accessors.append(accessor)
        return len(accessors) - 1

    attributes = {
        "POSITION": add(struct.pack("<3f", 1.0, 2.0, 3.0), 5126, "VEC3"),
        "KHR_gaussian_splatting:ROTATION": add(b"\x00\x00\x00\x7f", 5120, "VEC4", normalized=True),
        "KHR_gaussian_splatting:SCALE": add(struct.pack("<3f", 1.0, 1.0, 1.0), 5126, "VEC3"),
        "KHR_gaussian_splatting:OPACITY": add(b"\xff", 5121, "SCALAR", normalized=True),
        "KHR_gaussian_splatting:SH_DEGREE_0_COEF_0": add(struct.pack("<3f", 0.1, 0.2, 0.3), 5126, "VEC3"),
        "COLOR_0": add(b"\xff\x80\x00\xff", 5121, "VEC4", normalized=True),
    }
    buffer = b"".join(chunks)
    payload = {
        "asset": {"version": "2.0"},
        "extensionsUsed": ["KHR_gaussian_splatting"],
        "extensionsRequired": ["KHR_gaussian_splatting"],
        "buffers": [
            {
                "byteLength": len(buffer),
                "uri": "data:application/octet-stream;base64," + base64.b64encode(buffer).decode("ascii"),
            }
        ],
        "bufferViews": views,
        "accessors": accessors,
        "meshes": [
            {
                "primitives": [
                    {
                        "mode": 0,
                        "attributes": attributes,
                        "extensions": {
                            "KHR_gaussian_splatting": {
                                "kernel": "ellipse",
                                "colorSpace": "lin_rec709_display",
                                "projection": "perspective",
                                "sortingMethod": "cameraDistance",
                            }
                        },
                    }
                ]
            }
        ],
    }
    return _canonical(payload)


def run(
    repo_root: Path,
    *,
    base_ref: str,
    head_ref: str,
    observed_head: str,
    structural_only: bool = False,
) -> dict[str, Any]:
    retained = run_retained_harness(
        repo_root,
        base_ref=base_ref,
        head_ref=head_ref,
        observed_head=observed_head,
        structural_only=True,
    )
    architecture = (
        {
            "mode": "structural_only",
            "agent_bridge": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "connectome": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "emergent": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "waboose": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "crucible": {"status": "not_invoked_in_structural_mode"},
        }
        if structural_only
        else _run_s4b_architecture(
            repo_root,
            base_ref=base_ref,
            head_ref=head_ref,
            observed_head=observed_head,
        )
    )
    gltf = import_gltf_file(
        repo_root / "tests/fixtures/spatial/gltf/triangle.gltf",
        provenance_refs=("harness:gltf",),
        root=repo_root,
    )
    ply = import_ply_file(
        repo_root / "tests/fixtures/spatial/ply/points_ascii.ply",
        provenance_refs=("harness:ply",),
        coordinate_conversion=CoordinateConversion("RIGHT_HANDED", "Z_UP", 1.0),
        root=repo_root,
    )
    spz = import_spz_bytes(_spz_fixture(), provenance_refs=("harness:spz",))
    gaussian_gltf = import_gaussian_gltf_bytes(
        _gaussian_gltf_fixture(),
        provenance_refs=("harness:khr-gaussian",),
        extension_profile=KHR_GAUSSIAN_PROFILE,
    )
    assets = (
        build_imported_asset_manifest(
            gltf,
            asset_id="asset:harness-mesh",
            uri="assets/harness/mesh.gltf",
            media_type="model/gltf+json",
            frame_id="root",
            source_refs=("harness:gltf",),
        ),
        build_imported_asset_manifest(
            ply,
            asset_id="asset:harness-points",
            uri="assets/harness/points.ply",
            media_type="application/octet-stream",
            frame_id="root",
            source_refs=("harness:ply",),
        ),
        build_imported_asset_manifest(
            spz,
            asset_id="asset:harness-spz",
            uri="assets/harness/splats.spz",
            media_type="application/vnd.spz",
            frame_id="root",
            source_refs=("harness:spz",),
        ),
        build_imported_asset_manifest(
            gaussian_gltf,
            asset_id="asset:harness-khr",
            uri="assets/harness/splats.gltf",
            media_type="model/gltf+json",
            frame_id="root",
            source_refs=("harness:khr-gaussian",),
        ),
    )
    scene = compile_spatial_scene(
        scene_id="harness:spatial-s4b",
        purpose_digest="purpose:spatial-s4b-harness",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root"),),
        entities=(
            SpatialEntity(
                entity_id="entity:harness-s4b",
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label="S4-B mixed scene",
                frame_id="root",
                source_refs=("harness:s4b",),
            ),
        ),
        assets=assets,
        source_refs=("harness:s4b",),
    )
    device = compile_spatial_device_profile(
        profile_id="device:harness-s4b",
        supported_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        source_refs=("harness:s4b-device",),
    )
    plan = negotiate_spatial_render_plan(
        scene,
        device,
        preferred_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
    )
    gaussian_budget = compile_gaussian_representation_budget(scene, plan)
    checks = {
        "retained_architecture_passed": retained["status"] == "PASSED",
        "exact_head_bound": retained["repository_head"] == observed_head,
        "spz_v4_decoded": spz.receipt.source_format.value == "SPZ_V4",
        "khr_profile_exact": gaussian_gltf.metadata["extension_profile"] == KHR_GAUSSIAN_PROFILE,
        "mixed_scene_bound": len(scene.assets) == 4 and plan.scene_digest == scene.scene_digest,
        "gaussian_budget_bound": gaussian_budget["declared_splats"] == 2,
        "fallbacks_present": (
            gaussian_budget["accessible_fallback_required"] is True
            and gaussian_budget["point_cloud_fallback_required"] is True
            and gaussian_budget["headless_fallback_required"] is True
        ),
        "no_network": all(not item.receipt.network_fetch_performed for item in (gltf, ply, spz, gaussian_gltf)),
        "no_training": all(not item.receipt.training_invoked for item in (gltf, ply, spz, gaussian_gltf)),
        "no_authority": all(
            not item.receipt.renderer_authority and not item.receipt.execution_authority
            for item in (gltf, ply, spz, gaussian_gltf)
        ),
        "agent_bridge_prepare_ok": structural_only or bool(architecture["agent_bridge"]["prepare"].get("ok")),
        "generated_maps_restored": structural_only or architecture["agent_bridge"]["generated_maps_restored"] is True,
        "atomic_inventory_ok": structural_only or bool(architecture["connectome"]["atomic_inventory"].get("ok")),
        "emergent_grounded": structural_only
        or (architecture["emergent"].get("ok") is True and architecture["emergent"].get("grounding_ok") is True),
        "waboose_prepare_ok": structural_only or bool(architecture["waboose"]["prepare"].get("ok")),
        "waboose_scan_ok": structural_only or bool(architecture["waboose"]["scan"].get("ok")),
        "waboose_finalize_ok": structural_only or bool(architecture["waboose"]["finalize"].get("ok")),
        "waboose_no_findings": structural_only
        or int((architecture["waboose"]["finalize"].get("summary") or {}).get("visible_findings", 0)) == 0,
        "crucible_passed": structural_only
        or (architecture["crucible"].get("status") == "PASSED" and architecture["crucible"].get("failed_count") == 0),
    }
    receipt: dict[str, Any] = {
        "version": HARNESS_VERSION,
        "repository_head": observed_head,
        "retained_architecture": retained,
        "s4b_architecture": architecture,
        "s4b_proof": {
            "scene_digest": scene.scene_digest,
            "render_plan_digest": plan.render_plan_digest,
            "asset_types": [item.asset_type.value for item in scene.assets],
            "spz_receipt_digest": spz.receipt.derived_asset_digest,
            "gaussian_gltf_receipt_digest": gaussian_gltf.receipt.derived_asset_digest,
            "gaussian_budget": gaussian_budget,
            "accessible_fallback": True,
            "headless_fallback": True,
            "point_cloud_fallback": True,
            "capture_path": False,
            "training_path": False,
            "production_mutation": False,
        },
        "checks": checks,
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "automatic_fix": False,
        "automatic_merge": False,
        "human_review_required": True,
    }
    receipt["receipt_digest"] = _digest(receipt)
    if len(_canonical(receipt)) > _MAX_RECEIPT_BYTES:
        raise RuntimeError("S4-B architecture receipt exceeds byte ceiling")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--base-ref", default=os.environ.get("AURA_BASE_REF", "HEAD~1"))
    parser.add_argument("--head-ref", default=os.environ.get("AURA_HEAD_REF", "HEAD"))
    parser.add_argument("--observed-head", default=os.environ.get("AURA_OBSERVED_HEAD_SHA", ""))
    parser.add_argument("--structural-only", action="store_true")
    parser.add_argument("--output", default="Aura_Staging/spatial_s4b_harness/architect_receipt.json")
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
