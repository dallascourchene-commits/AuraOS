"""Regression coverage for the final Codex spatial review findings."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from aura_spatial_asset_registry import validate_asset_manifest
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialAssetType,
    SpatialEntity,
    SpatialEntityType,
    SpatialInteractionAction,
)
from aura_spatial_coordinate_frames import resolve_world_transform
from aura_spatial_interaction import (
    MAX_INTERACTION_EVIDENCE_BYTES,
    compile_spatial_interaction,
)
from aura_spatial_scene import (
    compile_spatial_scene,
    validate_spatial_scene_payload,
)
from aura_spatial_ws_guard import compile_ar_hotswap_handoff


def _scene(*, metadata=None):
    root = CoordinateFrame(frame_id="root")
    entity = SpatialEntity(
        entity_id="entity:one",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="One",
        frame_id="root",
        source_refs=("source:one.py",),
        metadata=metadata or {},
    )
    return compile_spatial_scene(
        scene_id="codex-followup-scene",
        purpose_digest="purpose:codex-followup",
        root_frame_id="root",
        frames=(root,),
        entities=(entity,),
    )


def _asset(uri: str) -> SpatialAssetManifest:
    content = b"asset"
    return SpatialAssetManifest(
        asset_id="asset:one",
        asset_type=SpatialAssetType.MESH,
        uri=uri,
        media_type="model/gltf-binary",
        content_digest=(
            "sha256:" + hashlib.sha256(content).hexdigest()
        ),
        byte_length=len(content),
        frame_id="root",
        bounds_min=(0.0, 0.0, 0.0),
        bounds_max=(1.0, 1.0, 1.0),
        source_refs=("source:asset",),
    )


def test_interaction_rejects_mixed_case_and_separator_authority_aliases():
    scene = _scene()
    for key in (
        "automaticMerge",
        "automaticmErge",
        "patch-Authority",
        "pAtchAuthority",
        "executionaUthority",
        "authoritydEcIsion",
    ):
        with pytest.raises(ValueError, match="authority field"):
            compile_spatial_interaction(
                scene,
                action=SpatialInteractionAction.OPEN_SOURCE,
                target_entity_ids=("entity:one",),
                metadata={key: False},
            )


def test_scene_rejects_mixed_case_authority_alias_even_when_false():
    for key in (
        "automaticMerge",
        "automaticmErge",
        "pAtchAuthority",
        "authoritydEcIsion",
    ):
        with pytest.raises(ValueError, match="AUTHORITY_METADATA_REJECTED"):
            _scene(metadata={key: False})


def test_asset_uri_rejects_encoded_and_repeated_separators():
    cases = (
        "assets/a%2fb.glb",
        "aura://coding/%2fetc",
        "https://example.invalid//path.glb",
    )
    for uri in cases:
        report = validate_asset_manifest(
            _asset(uri),
            allow_remote=uri.startswith("https://"),
        )
        assert report.ok is False
        assert {
            item["code"] for item in report.findings
        } & {
            "NONCANONICAL_ASSET_ENCODING",
            "UNSAFE_ASSET_PATH",
        }


def test_nested_absolute_frame_units_do_not_double_scale():
    frames = (
        CoordinateFrame(
            frame_id="root",
            unit_scale_meters=0.01,
        ),
        CoordinateFrame(
            frame_id="child",
            parent_frame_id="root",
            unit_scale_meters=0.01,
            translation=(100.0, 0.0, 0.0),
        ),
    )
    resolved = resolve_world_transform(
        frames,
        root_frame_id="root",
        frame_id="child",
    )
    assert resolved.translation == pytest.approx((1.0, 0.0, 0.0))
    assert resolved.scale == pytest.approx((0.01, 0.01, 0.01))


def test_interaction_rejects_large_serialized_evidence():
    root = CoordinateFrame(frame_id="root")
    entity = SpatialEntity(
        entity_id="entity:large",
        entity_type=SpatialEntityType.DOMAIN_NODE,
        label="Large",
        frame_id="root",
        source_refs=(
            "source:" + "x" * MAX_INTERACTION_EVIDENCE_BYTES,
        ),
    )
    scene = compile_spatial_scene(
        scene_id="large-evidence-scene",
        purpose_digest="purpose:large-evidence",
        root_frame_id="root",
        frames=(root,),
        entities=(entity,),
    )
    with pytest.raises(ValueError, match="interaction evidence"):
        compile_spatial_interaction(
            scene,
            action=SpatialInteractionAction.OPEN_SOURCE,
            target_entity_ids=("entity:large",),
        )


def test_ws_guard_omits_dot_segment_source_anchors():
    for path in ("./aura_topology_ws_bridge.py", "pkg/./module.py"):
        packet = compile_ar_hotswap_handoff(
            target_id="node:one",
            new_function={"source": "return 1"},
            shapes={
                "node:one": {
                    "metadata": {
                        "ast_data": {
                            "file_path": path,
                            "line_range": [1, 2],
                        }
                    }
                }
            },
            actor_ref="ar-session:test",
        )
        assert packet["source_anchor_present"] is False
        assert all(
            not ref.startswith("source:")
            for ref in packet["intent"]["source_refs"]
        )


def test_schema_and_runtime_interchange_reject_invalid_contracts():
    schema = json.loads(
        Path("schemas/aura_spatial_scene.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    scene = _scene().to_dict()
    validator.validate(scene)
    assert validate_spatial_scene_payload(scene).scene_digest == scene["scene_digest"]

    authority_alias = deepcopy(scene)
    authority_alias["entities"][0]["metadata"] = {
        "automaticMerge": False
    }
    assert list(validator.iter_errors(authority_alias))

    zero_scale = deepcopy(scene)
    zero_scale["frames"][0]["scale"] = [0.0, 1.0, 1.0]
    assert list(validator.iter_errors(zero_scale))

    zero_quaternion = deepcopy(scene)
    zero_quaternion["frames"][0]["rotation_xyzw"] = [
        0.0,
        0.0,
        0.0,
        0.0,
    ]
    assert list(validator.iter_errors(zero_quaternion))

    root = CoordinateFrame(frame_id="root")
    asset_scene = compile_spatial_scene(
        scene_id="asset-bounds-scene",
        purpose_digest="purpose:asset-bounds",
        root_frame_id="root",
        frames=(root,),
        assets=(_asset("assets/one.glb"),),
    ).to_dict()
    invalid_bounds = deepcopy(asset_scene)
    invalid_bounds["assets"][0]["bounds_min"] = [2.0, 0.0, 0.0]
    invalid_bounds["assets"][0]["bounds_max"] = [1.0, 1.0, 1.0]
    with pytest.raises(ValueError, match="bounds_min"):
        validate_spatial_scene_payload(invalid_bounds)
