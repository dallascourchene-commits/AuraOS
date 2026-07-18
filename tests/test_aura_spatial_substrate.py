"""Adversarial contracts for Aura's representation-independent spatial substrate."""
from __future__ import annotations

import hashlib
import math

import pytest

from aura_spatial_asset_registry import (
    SpatialAssetRegistry,
    validate_asset_manifest,
)
from aura_spatial_breadboard import (
    build_spatial_refactor_plan,
    compile_spatial_breadboard,
    council_v3_route_spatial_plan,
)
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialAssetType,
    SpatialEntity,
    SpatialEntityType,
    SpatialInteractionAction,
    SpatialLink,
    SpatialTruthClass,
)
from aura_spatial_coordinate_frames import (
    resolve_world_transform,
    validate_coordinate_frames,
)
from aura_spatial_interaction import (
    compile_hotswap_request_guard,
    compile_spatial_interaction,
)
from aura_spatial_projection import project_coding_topology_to_scene
from aura_spatial_scene import compile_spatial_scene, verify_spatial_scene


def _asset(content: bytes = b"scene") -> SpatialAssetManifest:
    return SpatialAssetManifest(
        asset_id="asset:scene",
        asset_type=SpatialAssetType.MESH,
        uri="assets/scene.glb",
        media_type="model/gltf-binary",
        content_digest="sha256:" + hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        frame_id="root",
        bounds_min=(-1.0, -1.0, -1.0),
        bounds_max=(1.0, 1.0, 1.0),
        source_refs=("source:assets/scene.glb",),
        truth_class=SpatialTruthClass.DERIVED,
        immutable=True,
    )


def _scene():
    root = CoordinateFrame(
        frame_id="root",
        source_refs=("source:test",),
        truth_class=SpatialTruthClass.DERIVED,
    )
    entity = SpatialEntity(
        entity_id="entity:one",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="One",
        frame_id="root",
        asset_ids=("asset:scene",),
        source_refs=("source:aura_node.py#L1-L3",),
        patch_authority=False,
        projection_only=True,
    )
    return compile_spatial_scene(
        scene_id="test-scene",
        purpose_digest="purpose:test",
        root_frame_id="root",
        frames=(root,),
        assets=(_asset(),),
        entities=(entity,),
        source_refs=("source:test",),
    )


def _topology() -> dict:
    return {
        "nodes": [
            {
                "id": "file:aura_spatial_scene.py",
                "label": "aura_spatial_scene.py",
                "node_type": "file",
                "file_path": "aura_spatial_scene.py",
                "symbol": "",
                "line_range": [1, 200],
                "x": 1.0,
                "y": 2.0,
                "z": 3.0,
                "metadata": {},
            },
            {
                "id": "function:compile_spatial_scene",
                "label": "compile_spatial_scene",
                "node_type": "function",
                "file_path": "aura_spatial_scene.py",
                "symbol": "compile_spatial_scene",
                "line_range": [30, 65],
                "x": 4.0,
                "y": 5.0,
                "z": 6.0,
                "metadata": {},
            },
            {
                "id": "test:test_spatial",
                "label": "test_aura_spatial_substrate.py",
                "node_type": "test",
                "file_path": "tests/test_aura_spatial_substrate.py",
                "symbol": "",
                "line_range": [1, 300],
                "x": 7.0,
                "y": 8.0,
                "z": 9.0,
                "metadata": {},
            },
        ],
        "links": [
            {
                "source": "file:aura_spatial_scene.py",
                "target": "function:compile_spatial_scene",
                "type": "defines",
            },
            {
                "source": "test:test_spatial",
                "target": "function:compile_spatial_scene",
                "type": "tests",
            },
        ],
        "meta": {"truth_policy": "exact"},
    }


def test_coordinate_frame_rejects_nonfinite_and_normalizes_quaternion():
    with pytest.raises(ValueError, match="finite"):
        CoordinateFrame(
            frame_id="bad",
            translation=(math.nan, 0.0, 0.0),
        )
    frame = CoordinateFrame(
        frame_id="good",
        rotation_xyzw=(0.0, 0.0, 0.0, 5.0),
    )
    assert frame.rotation_xyzw == (0.0, 0.0, 0.0, 1.0)


def test_coordinate_frame_graph_fails_closed_on_cycle_and_missing_parent():
    cycle = (
        CoordinateFrame(frame_id="a", parent_frame_id="b"),
        CoordinateFrame(frame_id="b", parent_frame_id="a"),
    )
    report = validate_coordinate_frames(cycle, root_frame_id="a")
    assert report.ok is False
    assert {item["code"] for item in report.findings} >= {
        "ROOT_FRAME_HAS_PARENT",
        "FRAME_CYCLE",
    }

    missing = (
        CoordinateFrame(frame_id="root"),
        CoordinateFrame(
            frame_id="child",
            parent_frame_id="absent",
        ),
    )
    report = validate_coordinate_frames(
        missing,
        root_frame_id="root",
    )
    assert report.ok is False
    assert "MISSING_PARENT_FRAME" in {
        item["code"] for item in report.findings
    }


def test_world_transform_composes_parent_translation_and_scale():
    frames = (
        CoordinateFrame(
            frame_id="root",
            translation=(1.0, 0.0, 0.0),
            scale=(2.0, 2.0, 2.0),
        ),
        CoordinateFrame(
            frame_id="child",
            parent_frame_id="root",
            translation=(1.0, 0.0, 0.0),
        ),
    )
    result = resolve_world_transform(
        frames,
        root_frame_id="root",
        frame_id="child",
    )
    assert result.translation == pytest.approx((3.0, 0.0, 0.0))
    assert result.scale == pytest.approx((2.0, 2.0, 2.0))
    assert result.chain == ("root", "child")


def test_asset_registry_verifies_digest_and_blocks_remote_without_policy():
    content = b"scene"
    manifest = _asset(content)
    report = validate_asset_manifest(manifest, content=content)
    assert report.ok is True
    assert report.verified_content is True
    assert (
        SpatialAssetRegistry((manifest,)).require(manifest.asset_id)
        == manifest
    )

    remote = SpatialAssetManifest(
        **{
            **manifest.to_dict(),
            "asset_id": "asset:remote",
            "uri": "https://example.invalid/scene.glb",
            "metadata": {},
        }
    )
    report = validate_asset_manifest(remote)
    assert report.ok is False
    assert report.findings[0]["code"] == "REMOTE_ASSET_NOT_ADMITTED"


def test_scene_snapshot_is_deterministic_and_rejects_dangling_references():
    scene_a = _scene()
    scene_b = _scene()
    assert scene_a.scene_digest == scene_b.scene_digest
    assert (
        scene_a.to_dict()["patch_authority"]
        == "exact_source_spans_and_hashes_only"
    )
    assert scene_a.to_dict()["vsa_patch_authority"] is False
    assert scene_a.to_dict()["execution_authority"] is False
    assert verify_spatial_scene(scene_a).ok is True

    root = CoordinateFrame(frame_id="root")
    dangling = SpatialEntity(
        entity_id="entity:dangling",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="Dangling",
        frame_id="missing",
    )
    with pytest.raises(ValueError, match="ENTITY_FRAME_MISSING"):
        compile_spatial_scene(
            scene_id="bad-scene",
            purpose_digest="purpose:bad",
            root_frame_id="root",
            frames=(root,),
            entities=(dangling,),
        )


def test_scene_rejects_spatial_patch_authority():
    with pytest.raises(ValueError, match="patch authority"):
        SpatialEntity(
            entity_id="entity:bad",
            entity_type=SpatialEntityType.DOMAIN_NODE,
            label="Bad",
            frame_id="root",
            patch_authority=True,
        )


def test_coding_projection_reuses_micro_arena_and_keeps_truth_separate():
    scene = project_coding_topology_to_scene(
        _topology(),
        ("function:compile_spatial_scene",),
        depth=1,
        human_instruction="inspect spatial scene compiler",
    )
    assert len(scene.entities) == 3
    assert len(scene.links) == 2
    assert all(entity.patch_authority is False for entity in scene.entities)
    assert all(entity.projection_only is True for entity in scene.entities)
    assert scene.renderer_hints
    assert scene.assets[0].asset_type is SpatialAssetType.TOPOLOGY_GRAPH
    assert scene.assets[0].metadata
    assert (
        scene.to_dict()["renderer_hints"]["renderer_is_replaceable"]
        is True
    )


def test_spatial_interaction_compiles_exact_six_slots_without_authority():
    scene = _scene()
    intent = compile_spatial_interaction(
        scene,
        action=SpatialInteractionAction.OPEN_SOURCE,
        target_entity_ids=("entity:one",),
    )
    assert set(intent.to_dict()["intent_slots"]) == {
        "DIR",
        "ASP",
        "CLASS",
        "SUBJ",
        "VOICE",
        "STEM",
    }
    assert intent.execution_authority is False
    assert intent.patch_authority is False
    assert intent.requires_forge is False


def test_hotswap_guard_never_reports_queued_success():
    packet = compile_hotswap_request_guard(
        _scene(),
        target_entity_ids=("entity:one",),
        proposed_change_digest="a" * 64,
    )
    assert packet["ok"] is False
    assert packet["success"] is False
    assert packet["queued"] is False
    assert packet["status"] == "REQUIRES_GOVERNED_REPAIR_HANDOFF"
    assert packet["next_owner"] == "aura_forge"
    assert packet["intent"]["requires_forge"] is True
    assert packet["automatic_merge"] is False


def test_council_v3_routes_all_lanes_for_spatial_program():
    route = council_v3_route_spatial_plan()
    assert route["native_model_calls_claimed"] is False
    assert route["selected_lanes"] == [
        "scope",
        "tests",
        "sequence",
        "continuity",
        "rollback",
        "cost",
    ]
    assert route["length_profile"]["task_count"] == 10
    assert route["length_profile"]["council_recommended"] is True


def test_spatial_breadboard_preserves_bc4_until_receipts_are_bound():
    plan = build_spatial_refactor_plan()
    component_ids = [
        item["task_id"] for item in plan["act_tasks"]
    ]
    unpowered = compile_spatial_breadboard()
    assert (
        unpowered["circuit_status"]
        == "GROUNDED_SPATIAL_S0_S2_CIRCUIT_UNPOWERED"
    )
    assert all(
        item["continuity"] == "BC4_AUTHORIZED"
        for item in unpowered["components"]
    )
    assert unpowered["authority"]["automatic_merge"] is False
    assert unpowered["deferred_explicit_mocks"]

    verified = compile_spatial_breadboard(
        energized_component_ids=component_ids,
        phase="VERIFIED",
    )
    assert (
        verified["circuit_status"]
        == "VERIFIED_SPATIAL_S0_S2_CIRCUIT"
    )
    assert verified["continuity"]["continuity_complete"] is True
    assert all(
        item["continuity"] == "BC5_VERIFIED"
        for item in verified["components"]
    )


def test_link_rejects_self_reference():
    with pytest.raises(ValueError, match="self-referential"):
        SpatialLink(
            link_id="link:self",
            source_entity_id="entity:one",
            target_entity_id="entity:one",
            relation="related",
        )

def test_empty_sequence_contract_fields_serialize_as_arrays():
    frame = CoordinateFrame(frame_id="root")
    entity = SpatialEntity(
        entity_id="entity:empty",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="Empty",
        frame_id="root",
    )
    assert frame.to_dict()["source_refs"] == []
    assert entity.to_dict()["asset_ids"] == []
    assert entity.to_dict()["source_refs"] == []
    assert entity.to_dict()["metadata"] == {}


def test_unknown_coding_selection_fails_closed():
    with pytest.raises(ValueError, match="unknown selected topology nodes"):
        project_coding_topology_to_scene(
            _topology(),
            ("missing:node",),
        )


def test_file_asset_uri_is_not_admitted():
    manifest = _asset()
    file_uri = SpatialAssetManifest(
        **{
            **manifest.to_dict(),
            "asset_id": "asset:file-uri",
            "uri": "file:///tmp/scene.glb",
            "metadata": {},
        }
    )
    report = validate_asset_manifest(file_uri)
    assert report.ok is False
    assert report.findings[0]["code"] == "UNSUPPORTED_ASSET_URI_SCHEME"

def test_projection_only_contracts_fail_closed():
    with pytest.raises(ValueError, match="projection-only"):
        CoordinateFrame(frame_id="frame:not-projection", projection_only=False)
    with pytest.raises(ValueError, match="projection-only"):
        SpatialEntity(
            entity_id="entity:not-projection",
            entity_type=SpatialEntityType.DOMAIN_NODE,
            label="Not projection",
            frame_id="root",
            projection_only=False,
        )
    with pytest.raises(ValueError, match="projection-only"):
        SpatialLink(
            link_id="link:not-projection",
            source_entity_id="entity:one",
            target_entity_id="entity:two",
            relation="related",
            projection_only=False,
        )


def test_selected_node_survives_spatial_node_cap():
    selected_id = "node:129"
    nodes = [
        {
            "id": f"node:{index}",
            "label": f"Node {index}",
            "node_type": "function",
            "file_path": f"pkg/module_{index}.py",
            "symbol": f"function_{index}",
            "line_range": [1, 2],
            "metadata": {},
        }
        for index in range(130)
    ]
    links = [
        {
            "source": selected_id,
            "target": f"node:{index}",
            "type": "calls",
        }
        for index in range(129)
    ]
    scene = project_coding_topology_to_scene(
        {"nodes": nodes, "links": links},
        (selected_id,),
        depth=1,
    )
    assert len(scene.entities) == 128
    assert any(
        f"topology:{selected_id}" in entity.source_refs
        for entity in scene.entities
    )


def test_spatial_metadata_redacts_secrets_and_rejects_private_reasoning():
    entity = SpatialEntity(
        entity_id="entity:sanitized",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="Sanitized",
        frame_id="root",
        metadata={"api_key": "sk-secret-value-12345678901234567890"},
    )
    assert entity.to_dict()["metadata"]["api_key"] == "[REDACTED]"
    with pytest.raises(ValueError, match="private reasoning field"):
        SpatialEntity(
            entity_id="entity:private-reasoning",
            entity_type=SpatialEntityType.DOMAIN_NODE,
            label="Private reasoning",
            frame_id="root",
            metadata={"chain_of_thought": "not allowed"},
        )
