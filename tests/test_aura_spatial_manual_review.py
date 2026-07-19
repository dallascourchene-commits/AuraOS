"""Manual-review regressions for Aura Spatial S0-S2."""
from __future__ import annotations

import hashlib

import pytest

import aura_spatial_projection as projection
from aura_spatial_asset_registry import validate_asset_manifest
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialAssetType,
    SpatialEntity,
    SpatialEntityType,
    SpatialInteractionAction,
)
from aura_spatial_coordinate_frames import (
    resolve_world_transform,
    validate_coordinate_frames,
)
from aura_spatial_interaction import compile_spatial_interaction
from aura_spatial_scene import compile_spatial_scene
from aura_spatial_ws_guard import (
    MAX_PROPOSAL_BYTES,
    compile_ar_hotswap_handoff,
)


def _asset(uri: str = "assets/scene.glb") -> SpatialAssetManifest:
    content = b"scene"
    return SpatialAssetManifest(
        asset_id="asset:scene",
        asset_type=SpatialAssetType.MESH,
        uri=uri,
        media_type="model/gltf-binary",
        content_digest=(
            "sha256:" + hashlib.sha256(content).hexdigest()
        ),
        byte_length=len(content),
        frame_id="root",
        bounds_min=(-1.0, -1.0, -1.0),
        bounds_max=(1.0, 1.0, 1.0),
        source_refs=("source:assets/scene.glb",),
    )


def _scene(
    *,
    metadata=None,
    source_refs=("source:b", "source:a"),
):
    root = CoordinateFrame(
        frame_id="root",
        source_refs=("source:z", "source:a"),
    )
    entity = SpatialEntity(
        entity_id="entity:one",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="One",
        frame_id="root",
        source_refs=source_refs,
        metadata=metadata or {},
    )
    return compile_spatial_scene(
        scene_id="manual-review-scene",
        purpose_digest="purpose:manual-review",
        root_frame_id="root",
        frames=(root,),
        entities=(entity,),
        source_refs=source_refs,
    )


def test_asset_uri_rejects_credentials_query_and_encoded_traversal():
    report = validate_asset_manifest(
        _asset(
            "https://user:pass@example.invalid/"
            "a/../scene.glb?token=secret"
        ),
        allow_remote=True,
    )
    assert report.ok is False
    assert {item["code"] for item in report.findings} >= {
        "UNSAFE_ASSET_URI_COMPONENTS",
        "UNSAFE_ASSET_PATH",
    }
    report = validate_asset_manifest(
        _asset("assets/%2e%2e/scene.glb")
    )
    assert report.ok is False
    assert "UNSAFE_ASSET_PATH" in {
        item["code"] for item in report.findings
    }


def test_interaction_metadata_cannot_override_authority_guards():
    with pytest.raises(ValueError, match="authority field"):
        compile_spatial_interaction(
            _scene(),
            action=SpatialInteractionAction.OPEN_SOURCE,
            target_entity_ids=("entity:one",),
            metadata={"automatic_merge": True},
        )


def test_scene_rejects_affirmative_authority_metadata():
    with pytest.raises(ValueError, match="AUTHORITY_METADATA_REJECTED"):
        _scene(metadata={"patch_authority": True})


def test_scene_normalizes_set_like_source_reference_order():
    scene_a = _scene(source_refs=("source:b", "source:a"))
    scene_b = _scene(source_refs=("source:a", "source:b"))
    assert scene_a.scene_digest == scene_b.scene_digest
    assert scene_a.source_refs == ("source:a", "source:b")
    assert scene_a.entities[0].source_refs == (
        "source:a",
        "source:b",
    )


def test_coordinate_resolution_applies_units_and_rejects_basis_change():
    frames = (
        CoordinateFrame(frame_id="root"),
        CoordinateFrame(
            frame_id="centimeters",
            parent_frame_id="root",
            unit_scale_meters=0.01,
            translation=(100.0, 0.0, 0.0),
        ),
    )
    resolved = resolve_world_transform(
        frames,
        root_frame_id="root",
        frame_id="centimeters",
    )
    assert resolved.translation == pytest.approx((1.0, 0.0, 0.0))

    mixed = (
        CoordinateFrame(frame_id="root"),
        CoordinateFrame(
            frame_id="z-up",
            parent_frame_id="root",
            up_axis="Z_UP",
        ),
    )
    report = validate_coordinate_frames(
        mixed,
        root_frame_id="root",
    )
    assert report.ok is False
    assert "FRAME_BASIS_CONVERSION_UNSUPPORTED" in {
        item["code"] for item in report.findings
    }


def test_projection_sorts_equivalent_link_sets(monkeypatch):
    nodes = [
        {
            "id": "node:a",
            "label": "A",
            "node_type": "function",
            "metadata": {},
        },
        {
            "id": "node:b",
            "label": "B",
            "node_type": "function",
            "metadata": {},
        },
        {
            "id": "node:c",
            "label": "C",
            "node_type": "function",
            "metadata": {},
        },
    ]
    links = [
        {
            "source": "node:c",
            "target": "node:a",
            "type": "calls",
        },
        {
            "source": "node:a",
            "target": "node:b",
            "type": "defines",
        },
    ]

    def fake_selector(_topology, selected, **_kwargs):
        return {
            "version": "test",
            "selected_node_ids": list(selected),
            "nodes": list(nodes),
            "links": list(fake_selector.links),
            "depth": 1,
            "human_instruction": "inspect",
            "token_cost": 1,
        }

    fake_selector.links = links
    monkeypatch.setattr(
        projection,
        "select_micro_arena",
        fake_selector,
    )
    scene_a = projection.project_coding_topology_to_scene(
        {"nodes": nodes, "links": links},
        ("node:a",),
    )
    fake_selector.links = list(reversed(links))
    scene_b = projection.project_coding_topology_to_scene(
        {"nodes": nodes, "links": list(reversed(links))},
        ("node:a",),
    )
    assert scene_a.scene_digest == scene_b.scene_digest


def test_ws_guard_rejects_unbounded_proposal_before_handoff():
    with pytest.raises(ValueError, match="bounded review payload"):
        compile_ar_hotswap_handoff(
            target_id="node:one",
            new_function={
                "source": "x" * (MAX_PROPOSAL_BYTES + 1)
            },
            shapes={
                "node:one": {"metadata": {"ast_data": {}}}
            },
            actor_ref="ar-session:test",
        )
