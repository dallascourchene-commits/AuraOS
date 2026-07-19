from __future__ import annotations

from copy import deepcopy

import pytest

from aura_spatial_contracts import CoordinateFrame, SpatialEntity, SpatialEntityType
from aura_spatial_receipts import compile_spatial_browser_telemetry_receipt
from aura_spatial_render_plan import compile_spatial_device_profile, negotiate_spatial_render_plan
from aura_spatial_scene import compile_spatial_scene


def _plan_device():
    scene = compile_spatial_scene(
        scene_id="telemetry-scene",
        purpose_digest="purpose:telemetry",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root"),),
        assets=(),
        entities=(
            SpatialEntity(entity_id="entity:a", entity_type=SpatialEntityType.DOMAIN_NODE, label="A", frame_id="root"),
        ),
        source_refs=("source:telemetry",),
    )
    device = compile_spatial_device_profile(
        profile_id="device:telemetry",
        supported_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        source_refs=("source:device",),
    )
    plan = negotiate_spatial_render_plan(scene, device, preferred_renderers=("WEBGL2", "ACCESSIBLE_2D"))
    return plan, device


def _packet(plan, device):
    return {
        "version": "AURA_SPATIAL_BROWSER_TELEMETRY_V1",
        "scene_digest": plan.scene_digest,
        "render_plan_digest": plan.render_plan_digest,
        "device_profile_digest": device.device_profile_digest,
        "fixture_digest": "d" * 64,
        "renderer": "WEBGL2",
        "metrics": {
            "frame_ms": {"value": 12.5, "unit": "ms", "evidence_class": "MEASURED", "method": "performance.now"},
            "gpu_bytes": {
                "value": None,
                "unit": "bytes",
                "evidence_class": "UNAVAILABLE",
                "method": "browser API unavailable",
            },
        },
        "projection_only": True,
        "renderer_authority": False,
        "execution_authority": False,
        "patch_authority": False,
        "production_mutation": False,
        "automatic_merge": False,
        "human_review_required": True,
    }


def test_browser_telemetry_compiles_empirical_digest_bound_receipt():
    plan, device = _plan_device()
    receipt = compile_spatial_browser_telemetry_receipt(plan, device, _packet(plan, device), sequence=1)
    payload = receipt.to_dict()
    assert payload["evidence_class"] == "MEASURED"
    assert payload["metrics"]["fixture_digest"] == "d" * 64
    assert payload["renderer_authority"] is False
    assert payload["execution_authority"] is False


def test_browser_telemetry_rejects_stale_or_unsupported_claims():
    plan, device = _plan_device()
    stale = _packet(plan, device)
    stale["scene_digest"] = "0" * 64
    with pytest.raises(ValueError, match="stale"):
        compile_spatial_browser_telemetry_receipt(plan, device, stale, sequence=1)
    unsupported = deepcopy(_packet(plan, device))
    unsupported["metrics"]["frame_ms"]["evidence_class"] = "PROVEN"
    with pytest.raises(ValueError, match="evidence"):
        compile_spatial_browser_telemetry_receipt(plan, device, unsupported, sequence=1)
    non_finite = deepcopy(_packet(plan, device))
    non_finite["metrics"]["frame_ms"]["value"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        compile_spatial_browser_telemetry_receipt(plan, device, non_finite, sequence=1)


def test_browser_telemetry_accepts_large_finite_integer_without_float_overflow():
    plan, device = _plan_device()
    packet = _packet(plan, device)
    value = 10**400
    packet["metrics"]["frame_ms"]["value"] = value
    receipt = compile_spatial_browser_telemetry_receipt(plan, device, packet, sequence=1)
    assert receipt.to_dict()["metrics"]["browser_metrics"]["frame_ms"]["value"] == value
