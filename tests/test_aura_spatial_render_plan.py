from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialAssetType,
    SpatialEntity,
    SpatialEntityType,
    SpatialRenderBudget,
    SpatialRendererKind,
)
from aura_spatial_render_plan import (
    compile_spatial_device_profile,
    negotiate_spatial_render_plan,
    validate_spatial_device_profile_payload,
    validate_spatial_render_plan_payload,
)
from aura_spatial_scene import compile_spatial_scene

ROOT = Path(__file__).resolve().parents[1]


def _scene(*, entities: int = 2, asset_bytes: int = 5):
    root = CoordinateFrame(frame_id="root")
    records = tuple(
        SpatialEntity(
            entity_id=f"entity:{index}",
            entity_type=SpatialEntityType.DOMAIN_NODE,
            label=f"Entity {index}",
            frame_id="root",
        )
        for index in range(entities)
    )
    assets = ()
    if asset_bytes:
        content = b"x" * asset_bytes
        assets = (
            SpatialAssetManifest(
                asset_id="asset:one",
                asset_type=SpatialAssetType.MESH,
                uri="assets/one.glb",
                media_type="model/gltf-binary",
                content_digest="sha256:" + hashlib.sha256(content).hexdigest(),
                byte_length=len(content),
                frame_id="root",
                bounds_min=(0.0, 0.0, 0.0),
                bounds_max=(1.0, 1.0, 1.0),
                source_refs=("source:assets/one.glb",),
            ),
        )
    return compile_spatial_scene(
        scene_id="render-plan-scene",
        purpose_digest="purpose:render-plan",
        root_frame_id="root",
        frames=(root,),
        assets=assets,
        entities=records,
        source_refs=("source:render-plan",),
    )


def _device(*, activation: bool = False, budget=None, renderers=None):
    return compile_spatial_device_profile(
        profile_id="device:browser",
        supported_renderers=renderers or ("HEADLESS", "ACCESSIBLE_2D", "WEBGL2", "WEBGPU", "WEBXR"),
        budget=budget or SpatialRenderBudget(),
        xr_user_activation=activation,
        source_refs=("source:device",),
    )


def test_device_profile_is_canonical_non_fingerprinting_and_schema_valid():
    first = _device()
    second = _device(renderers=("WEBXR", "WEBGPU", "WEBGL2", "ACCESSIBLE_2D", "HEADLESS"))
    assert first.device_profile_digest == second.device_profile_digest
    assert first.to_dict()["fingerprinting_allowed"] is False
    assert first.to_dict()["renderer_authority"] is False
    schema = json.loads((ROOT / "schemas/aura_spatial_device_profile.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(first.to_dict())
    assert validate_spatial_device_profile_payload(first.to_dict()) == first


def test_negotiation_is_deterministic_and_requires_accessible_fallback():
    scene = _scene()
    device = _device()
    first = negotiate_spatial_render_plan(scene, device)
    second = negotiate_spatial_render_plan(scene, device)
    assert first.render_plan_digest == second.render_plan_digest
    assert first.selected_renderer is SpatialRendererKind.WEBGPU
    assert SpatialRendererKind.ACCESSIBLE_2D in first.fallback_renderers
    assert first.renderer_authority is False
    assert first.execution_authority is False
    assert first.patch_authority is False


def test_webxr_requires_both_request_and_observed_user_activation():
    scene = _scene()
    without_activation = negotiate_spatial_render_plan(
        scene,
        _device(activation=False),
        preferred_renderers=("WEBXR", "WEBGL2", "ACCESSIBLE_2D"),
        allow_xr=True,
    )
    assert without_activation.selected_renderer is SpatialRendererKind.WEBGL2
    assert "WEBXR:user_activation_not_observed" in without_activation.reasons

    activated = negotiate_spatial_render_plan(
        scene,
        _device(activation=True),
        preferred_renderers=("WEBXR", "WEBGL2", "ACCESSIBLE_2D"),
        allow_xr=True,
    )
    assert activated.selected_renderer is SpatialRendererKind.WEBXR
    assert activated.xr_user_activation_observed is True


def test_scene_must_fit_effective_device_and_request_budgets():
    scene = _scene(entities=3, asset_bytes=8)
    device = _device(
        budget=SpatialRenderBudget(
            max_entities=2,
            max_links=10,
            max_assets=2,
            max_asset_bytes=10,
            max_cpu_ms_per_frame=20.0,
            max_gpu_bytes=1024,
            max_network_bytes=0,
        )
    )
    with pytest.raises(ValueError, match="entities"):
        negotiate_spatial_render_plan(scene, device)

    roomy = _device(
        budget=SpatialRenderBudget(
            max_entities=10,
            max_links=10,
            max_assets=2,
            max_asset_bytes=10,
            max_cpu_ms_per_frame=20.0,
            max_gpu_bytes=1024,
            max_network_bytes=0,
        )
    )
    with pytest.raises(ValueError, match="asset bytes"):
        negotiate_spatial_render_plan(
            scene,
            roomy,
            requested_budget=SpatialRenderBudget(
                max_entities=10,
                max_links=10,
                max_assets=2,
                max_asset_bytes=4,
                max_cpu_ms_per_frame=20.0,
                max_gpu_bytes=1024,
                max_network_bytes=0,
            ),
        )


def test_render_contract_metadata_rejects_authority_aliases():
    with pytest.raises(ValueError, match="protected authority"):
        compile_spatial_device_profile(
            profile_id="device:unsafe",
            supported_renderers=("ACCESSIBLE_2D",),
            metadata={"automatic-Merge": False},
        )


def test_render_plan_schema_runtime_and_digest_reject_tampering():
    plan = negotiate_spatial_render_plan(_scene(), _device())
    payload = plan.to_dict()
    schema = json.loads((ROOT / "schemas/aura_spatial_render_plan.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert validate_spatial_render_plan_payload(payload) == plan

    tampered = deepcopy(payload)
    tampered["scene_entity_count"] += 1
    with pytest.raises(ValueError, match="not canonical"):
        validate_spatial_render_plan_payload(tampered)


def test_device_runtime_matches_accessibility_schema_and_canonicalizes_source_refs():
    with pytest.raises(ValueError, match="accessible presentation"):
        compile_spatial_device_profile(
            profile_id="device:inaccessible",
            supported_renderers=("ACCESSIBLE_2D",),
            accessibility_required=False,
        )

    first = compile_spatial_device_profile(
        profile_id="device:refs",
        supported_renderers=("ACCESSIBLE_2D",),
        source_refs=("source:z", "source:a"),
    )
    second = compile_spatial_device_profile(
        profile_id="device:refs",
        supported_renderers=("ACCESSIBLE_2D",),
        source_refs=("source:a", "source:z"),
    )
    assert first.device_profile_digest == second.device_profile_digest
    assert first.to_dict()["source_refs"] == ["source:a", "source:z"]

    noncanonical = first.to_dict()
    noncanonical["source_refs"] = ["source:z", "source:a"]
    with pytest.raises(ValueError, match="not canonical"):
        validate_spatial_device_profile_payload(noncanonical)


def test_public_s3a_metadata_schemas_bound_depth_and_container_width():
    nested: object = "leaf"
    for _ in range(5):
        nested = [nested]
    wide = list(range(129))
    for filename in (
        "aura_spatial_device_profile.schema.json",
        "aura_spatial_render_receipt.schema.json",
    ):
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        safe_value = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": "#/$defs/safeValue4",
            "$defs": schema["$defs"],
        }
        validator = Draft202012Validator(safe_value)
        assert list(validator.iter_errors(nested))
        assert list(validator.iter_errors(wide))
