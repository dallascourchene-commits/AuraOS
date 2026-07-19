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
from aura_spatial_interaction import compile_spatial_interaction
from aura_spatial_scene import compile_spatial_scene


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


def test_interaction_rejects_camel_and_hyphen_authority_aliases():
    scene = _scene()
    for key in ("automaticMerge", "patch-Authority"):
        with pytest.raises(ValueError, match="authority field"):
            compile_spatial_interaction(
                scene,
                action=SpatialInteractionAction.OPEN_SOURCE,
                target_entity_ids=("entity:one",),
                metadata={key: False},
            )


def test_scene_rejects_camel_authority_alias_even_when_false():
    with pytest.raises(ValueError, match="AUTHORITY_METADATA_REJECTED"):
        _scene(metadata={"automaticMerge": False})


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


def test_schema_rejects_nested_authority_alias_and_zero_scale():
    schema = json.loads(
        Path("schemas/aura_spatial_scene.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    scene = _scene().to_dict()
    validator.validate(scene)

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
