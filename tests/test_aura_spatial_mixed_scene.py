from __future__ import annotations

import json
from pathlib import Path
import struct

import pytest
import zstandard

from aura_spatial_asset_registry import SpatialAssetRegistry, build_imported_asset_manifest
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialEntity,
    SpatialEntityType,
    SpatialRenderBudget,
    SpatialTruthClass,
)
from aura_spatial_importers.contracts import CoordinateConversion
from aura_spatial_importers.gltf import import_gltf_file
from aura_spatial_importers.ply import import_ply_file
from aura_spatial_importers.spz import import_spz_bytes
from aura_spatial_render_plan import (
    compile_gaussian_representation_budget,
    compile_spatial_device_profile,
    negotiate_spatial_render_plan,
)
from aura_spatial_scene import compile_spatial_scene

ROOT = Path(__file__).resolve().parents[1]


def _spz(*, sh_degree: int = 0) -> bytes:
    streams = [
        b"\x00" * 9,
        b"\xff",
        b"\xff\x00\xff",
        b"\xa0\xa0\xa0",
        b"\x00\x00\x00\xc0",
    ]
    if sh_degree:
        streams.append(b"\x80" * ((((sh_degree + 1) ** 2) - 1) * 3))
    compressed = [zstandard.ZstdCompressor(level=1).compress(item) for item in streams]
    header = struct.pack("<IIIBBBBI12s", 0x5053474E, 4, 1, sh_degree, 12, 0, len(streams), 32, b"\x00" * 12)
    toc = b"".join(struct.pack("<QQ", len(blob), len(raw)) for blob, raw in zip(compressed, streams))
    return header + toc + b"".join(compressed)


def _mixed_scene():
    mesh = import_gltf_file(
        ROOT / "tests/fixtures/spatial/gltf/triangle.gltf",
        provenance_refs=("fixture:mesh",),
        root=ROOT,
    )
    points = import_ply_file(
        ROOT / "tests/fixtures/spatial/ply/points_ascii.ply",
        provenance_refs=("fixture:points",),
        coordinate_conversion=CoordinateConversion("RIGHT_HANDED", "Z_UP", 1.0),
        root=ROOT,
    )
    splats = import_spz_bytes(_spz(), provenance_refs=("fixture:splats",))
    manifests = (
        build_imported_asset_manifest(
            splats,
            asset_id="asset:splats",
            uri="aura://assets/splats.spz",
            media_type="application/vnd.spz",
            frame_id="root",
        ),
        build_imported_asset_manifest(
            mesh,
            asset_id="asset:mesh",
            uri="aura://assets/mesh.gltf",
            media_type="model/gltf+json",
            frame_id="root",
        ),
        build_imported_asset_manifest(
            points,
            asset_id="asset:points",
            uri="aura://assets/points.ply",
            media_type="application/vnd.ply",
            frame_id="root",
        ),
    )
    entity = SpatialEntity(
        entity_id="entity:mixed",
        entity_type=SpatialEntityType.ASSET_INSTANCE,
        label="Mixed representation object",
        frame_id="root",
        asset_ids=("asset:splats", "asset:points", "asset:mesh"),
        source_refs=("fixture:mixed",),
        truth_class=SpatialTruthClass.DERIVED,
        selectable=True,
        projection_only=True,
        patch_authority=False,
    )
    scene = compile_spatial_scene(
        scene_id="scene:mixed",
        purpose_digest="purpose:mixed-parity",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root", source_refs=("fixture",)),),
        assets=manifests,
        entities=(entity,),
        source_refs=("fixture:mixed",),
    )
    return scene, mesh, points, splats


def test_mixed_scene_preserves_identity_order_coordinates_and_authority() -> None:
    scene, mesh, points, splats = _mixed_scene()
    assert [asset.asset_id for asset in scene.assets] == ["asset:mesh", "asset:points", "asset:splats"]
    assert scene.entities[0].asset_ids == ("asset:mesh", "asset:points", "asset:splats")
    assert mesh.receipt.coordinate_conversion.target_up_axis == "Y_UP"
    assert points.receipt.coordinate_conversion.target_up_axis == "Y_UP"
    assert splats.receipt.coordinate_conversion.target_up_axis == "Y_UP"
    assert scene.execution_authority is False
    assert scene.vsa_patch_authority is False
    assert scene.patch_authority == "exact_source_spans_and_hashes_only"
    registry = SpatialAssetRegistry(reversed(scene.assets))
    assert registry.registry_digest == SpatialAssetRegistry(scene.assets).registry_digest


def test_mixed_scene_render_budget_has_accessible_point_and_headless_parity() -> None:
    scene, *_ = _mixed_scene()
    device = compile_spatial_device_profile(
        profile_id="device:mixed",
        supported_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        budget=SpatialRenderBudget(
            max_entities=32,
            max_links=32,
            max_assets=16,
            max_asset_bytes=16 * 1024 * 1024,
            max_cpu_ms_per_frame=50,
            max_gpu_bytes=16 * 1024 * 1024,
            max_network_bytes=0,
        ),
        source_refs=("fixture:mixed",),
    )
    plan = negotiate_spatial_render_plan(scene, device, preferred_renderers=("WEBGL2",))
    budget = compile_gaussian_representation_budget(scene, plan)
    assert plan.fallback_renderers[-2:] == ("ACCESSIBLE_2D", "HEADLESS")
    assert budget["declared_splats"] == 1
    assert budget["point_cloud_fallback_required"] is True
    assert budget["accessible_fallback_required"] is True
    assert budget["headless_fallback_required"] is True
    assert budget["renderer_authority"] is False


def test_mixed_scene_digest_is_input_order_independent_and_json_stable() -> None:
    scene, *_ = _mixed_scene()
    rebuilt = compile_spatial_scene(
        scene_id=scene.scene_id,
        purpose_digest=scene.purpose_digest,
        root_frame_id=scene.root_frame_id,
        frames=reversed(scene.frames),
        assets=reversed(scene.assets),
        entities=reversed(scene.entities),
        links=reversed(scene.links),
        source_refs=reversed(scene.source_refs),
    )
    assert rebuilt.scene_digest == scene.scene_digest
    assert json.dumps(rebuilt.to_dict(), sort_keys=True) == json.dumps(scene.to_dict(), sort_keys=True)


def test_gaussian_manifest_and_budget_account_for_high_order_spherical_harmonics() -> None:
    splats = import_spz_bytes(_spz(sh_degree=4), provenance_refs=("fixture:high-sh",))
    manifest = build_imported_asset_manifest(
        splats,
        asset_id="asset:high-sh",
        uri="aura://assets/high-sh.spz",
        media_type="application/vnd.spz",
        frame_id="root",
    )
    metadata = dict(manifest.metadata)
    assert metadata["gaussian_sh_degree"] == 4
    assert metadata["gaussian_color_space"] == "SPZ_INTERNAL_WIDE_RGB"
    assert metadata["import_receipt_digest"] == splats.receipt.derived_asset_digest

    scene = compile_spatial_scene(
        scene_id="scene:high-sh",
        purpose_digest="purpose:high-sh-budget",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root", source_refs=("fixture",)),),
        assets=(manifest,),
        entities=(
            SpatialEntity(
                entity_id="entity:high-sh",
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label="High SH Gaussian",
                frame_id="root",
                asset_ids=(manifest.asset_id,),
                source_refs=("fixture:high-sh",),
                truth_class=SpatialTruthClass.DERIVED,
                projection_only=True,
                patch_authority=False,
            ),
        ),
        source_refs=("fixture:high-sh",),
    )
    device = compile_spatial_device_profile(
        profile_id="device:high-sh",
        supported_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        budget=SpatialRenderBudget(
            max_entities=8,
            max_links=8,
            max_assets=4,
            max_asset_bytes=1024 * 1024,
            max_cpu_ms_per_frame=50,
            max_gpu_bytes=1024 * 1024,
            max_network_bytes=0,
        ),
        source_refs=("fixture:high-sh",),
    )
    plan = negotiate_spatial_render_plan(scene, device, preferred_renderers=("WEBGL2",))
    budget = compile_gaussian_representation_budget(scene, plan)
    assert budget["max_bytes_per_splat"] == 348
    assert budget["declared_gpu_bytes"] == 348
    assert budget["max_gpu_bytes"] >= 348


def test_gaussian_budget_rejects_aggregate_decoded_and_runtime_bytes_against_plan() -> None:
    from dataclasses import replace

    scene, *_ = _mixed_scene()
    device = compile_spatial_device_profile(
        profile_id="device:mixed-tight",
        supported_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        budget=SpatialRenderBudget(
            max_entities=32,
            max_links=32,
            max_assets=16,
            max_asset_bytes=2_048,
            max_cpu_ms_per_frame=50,
            max_gpu_bytes=16 * 1024 * 1024,
            max_network_bytes=0,
        ),
        source_refs=("fixture:mixed",),
    )
    plan = negotiate_spatial_render_plan(scene, device, preferred_renderers=("WEBGL2",))
    with pytest.raises(ValueError, match="runtime allocation"):
        compile_gaussian_representation_budget(scene, plan)

    assets = []
    for asset in scene.assets:
        if asset.asset_id != "asset:splats":
            assets.append(asset)
            continue
        metadata = dict(asset.metadata)
        metadata["decoded_bytes"] = 3_000
        metadata["estimated_runtime_allocation_bytes"] = 3_000
        assets.append(replace(asset, metadata=metadata))
    decoded_scene = compile_spatial_scene(
        scene_id=scene.scene_id,
        purpose_digest=scene.purpose_digest,
        root_frame_id=scene.root_frame_id,
        frames=scene.frames,
        assets=tuple(assets),
        entities=scene.entities,
        links=scene.links,
        source_refs=scene.source_refs,
    )
    decoded_plan = negotiate_spatial_render_plan(decoded_scene, device, preferred_renderers=("WEBGL2",))
    with pytest.raises(ValueError, match="decoded bytes"):
        compile_gaussian_representation_budget(decoded_scene, decoded_plan)
