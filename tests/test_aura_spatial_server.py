from __future__ import annotations

import pytest

from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialEntity,
    SpatialEntityType,
)
from aura_spatial_render_plan import compile_spatial_device_profile
from aura_spatial_scene import compile_spatial_scene
from aura_spatial_server import (
    MAX_SPATIAL_HTTP_BODY_BYTES,
    SpatialServerState,
    dispatch_spatial_request,
)


def _scene():
    return compile_spatial_scene(
        scene_id="server-scene",
        purpose_digest="purpose:server",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root"),),
        entities=(
            SpatialEntity(
                entity_id="entity:one",
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label="One",
                frame_id="root",
                source_refs=("source:one",),
            ),
        ),
    )


def _profile():
    return compile_spatial_device_profile(
        profile_id="device:server",
        supported_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        source_refs=("source:device",),
    )


def _browser_telemetry_packet(plan, device, fixture_digest: str):
    return {
        "version": "AURA_SPATIAL_BROWSER_TELEMETRY_V1",
        "scene_digest": plan["scene_digest"],
        "render_plan_digest": plan["render_plan_digest"],
        "device_profile_digest": device.device_profile_digest,
        "fixture_digest": fixture_digest,
        "renderer": "WEBGL2",
        "metrics": {
            "frame_ms": {
                "value": 10.5,
                "unit": "ms",
                "evidence_class": "MEASURED",
                "method": "performance.now",
            }
        },
        "projection_only": True,
        "renderer_authority": False,
        "execution_authority": False,
        "patch_authority": False,
        "production_mutation": False,
        "automatic_merge": False,
        "human_review_required": True,
    }


def test_server_end_to_end_is_bounded_review_only_and_dissolves():
    state = SpatialServerState()
    scene = _scene()

    capabilities = dispatch_spatial_request(
        state,
        "GET",
        "/api/spatial/capabilities",
    )
    assert capabilities.status == 200
    assert capabilities.headers["Cache-Control"].startswith("no-store")
    assert capabilities.headers["Content-Security-Policy"].startswith("default-src 'none'")
    capabilities_payload = capabilities.json()
    assert capabilities_payload["actual_renderer_implementation"] is True
    assert len(capabilities_payload["browser_fixture_digest"]) == 64
    assert set(capabilities_payload["browser_fixture_digest"]) <= set("0123456789abcdef")

    created_scene = dispatch_spatial_request(
        state,
        "POST",
        "/api/spatial/scenes",
        {"scene": scene.to_dict()},
    )
    assert created_scene.status == 201

    planned = dispatch_spatial_request(
        state,
        "POST",
        "/api/spatial/render-plans",
        {
            "scene_id": scene.scene_id,
            "device_profile": _profile().to_dict(),
            "preferred_renderers": ["WEBGL2", "ACCESSIBLE_2D", "HEADLESS"],
            "allow_xr": False,
        },
    )
    assert planned.status == 201
    plan = planned.json()["render_plan"]
    assert plan["selected_renderer"] == "WEBGL2"
    assert plan["renderer_authority"] is False

    started = dispatch_spatial_request(
        state,
        "POST",
        "/api/spatial/sessions",
        {"scene_id": scene.scene_id, "plan_id": plan["plan_id"]},
    )
    assert started.status == 201
    session_id = started.json()["session"]["session_id"]

    projection = dispatch_spatial_request(
        state,
        "GET",
        f"/api/spatial/projections/{session_id}",
    )
    assert projection.status == 200
    projection_payload = projection.json()
    assert projection_payload["scene"]["scene_digest"] == scene.scene_digest
    assert projection_payload["render_plan"]["render_plan_digest"] == plan["render_plan_digest"]
    assert projection_payload["production_mutation"] is False

    telemetry = dispatch_spatial_request(
        state,
        "POST",
        "/api/spatial/telemetry",
        {
            "session_id": session_id,
            "packet": _browser_telemetry_packet(
                plan,
                _profile(),
                capabilities_payload["browser_fixture_digest"],
            ),
        },
    )
    assert telemetry.status == 200
    telemetry_payload = telemetry.json()
    assert telemetry_payload["render_receipt"]["renderer_authority"] is False
    assert (
        telemetry_payload["render_receipt"]["metrics"]["fixture_digest"]
        == capabilities_payload["browser_fixture_digest"]
    )

    interaction = dispatch_spatial_request(
        state,
        "POST",
        "/api/spatial/interactions",
        {
            "session_id": session_id,
            "action": "SELECT",
            "target_entity_ids": ["entity:one"],
            "actor_ref": "human:local",
        },
    )
    assert interaction.status == 200
    assert interaction.json()["execution_performed"] is False
    assert interaction.json()["intent"]["review_only"] is True

    rendered = dispatch_spatial_request(
        state,
        "POST",
        f"/api/spatial/sessions/{session_id}/renders",
        {
            "outcome": "PRESENTED",
            "evidence_class": "MEASURED",
            "metrics": {"frame_ms": 11.0},
        },
    )
    assert rendered.status == 200
    assert rendered.json()["render_receipt"]["patch_authority"] is False

    dissolved = dispatch_spatial_request(
        state,
        "POST",
        f"/api/spatial/sessions/{session_id}/dissolve",
        {"reason_code": "TEST_COMPLETE"},
    )
    assert dissolved.status == 200
    assert dissolved.json()["session_active"] is False
    assert state.sessions.active_session_count == 0


def test_server_rejects_noncanonical_routes_and_oversized_bodies():
    state = SpatialServerState()
    query = dispatch_spatial_request(
        state,
        "GET",
        "/api/spatial/capabilities?token=secret",
    )
    assert query.status == 400
    oversized = dispatch_spatial_request(
        state,
        "POST",
        "/api/spatial/scenes",
        {"payload": "x" * (MAX_SPATIAL_HTTP_BODY_BYTES + 1)},
    )
    assert oversized.status == 400
    assert oversized.json()["patch_authority"] == "exact_source_spans_and_hashes_only"


def test_server_rejects_ambiguous_shapes_absolute_targets_and_get_bodies():
    state = SpatialServerState()
    non_object = dispatch_spatial_request(
        state,
        "POST",
        "/api/spatial/scenes",
        ["not", "an", "object"],  # type: ignore[arg-type]
    )
    assert non_object.status == 400

    absolute = dispatch_spatial_request(
        state,
        "GET",
        "https://example.invalid/api/spatial/capabilities",
    )
    assert absolute.status == 400

    get_body = dispatch_spatial_request(
        state,
        "GET",
        "/api/spatial/capabilities",
        {"unexpected": True},
    )
    assert get_body.status == 400

    extra = dispatch_spatial_request(
        state,
        "POST",
        "/api/spatial/scenes",
        {"scene": _scene().to_dict(), "automatic_merge": False},
    )
    assert extra.status == 400


def test_server_bounds_registry_counts_and_deep_direct_payloads():
    state = SpatialServerState(max_scenes=1)
    state.register_scene(_scene())
    other = compile_spatial_scene(
        scene_id="server-scene-two",
        purpose_digest="purpose:server-two",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root"),),
    )
    with pytest.raises(ValueError, match="scene ceiling"):
        state.register_scene(other)

    nested: object = "leaf"
    for _ in range(40):
        nested = {"next": nested}
    response = dispatch_spatial_request(
        SpatialServerState(),
        "POST",
        "/api/spatial/scenes",
        {"scene": nested},
    )
    assert response.status == 400
    assert "nesting ceiling" in response.json()["error"]


def test_browser_vertical_slice_assets_are_allowlisted_no_store_and_csp_bound():
    state = SpatialServerState()
    page = dispatch_spatial_request(state, "GET", "/spatial/")
    assert page.status == 200
    assert page.headers["Content-Type"].startswith("text/html")
    assert page.headers["Cache-Control"] == "no-store, max-age=0"
    assert "script-src 'self'" in page.headers["Content-Security-Policy"]
    assert "xr-spatial-tracking=(self)" in page.headers["Permissions-Policy"]
    assert b"Aura Spatial Projection" in page.body

    module = dispatch_spatial_request(state, "GET", "/spatial/webgl2_renderer.js")
    assert module.status == 200
    assert module.headers["Content-Type"].startswith("text/javascript")
    assert b"class WebGL2Renderer" in module.body

    bootstrap = dispatch_spatial_request(state, "GET", "/spatial/bootstrap.js")
    assert bootstrap.status == 200
    assert b"bootSpatialApp" in bootstrap.body

    assert dispatch_spatial_request(state, "GET", "/spatial/../aura_node.py").status == 404
    assert dispatch_spatial_request(state, "GET", "/spatial/unknown.js").status == 404


def test_capabilities_report_real_browser_slice_without_renderer_authority():
    response = dispatch_spatial_request(SpatialServerState(), "GET", "/api/spatial/capabilities")
    payload = response.json()
    assert payload["actual_renderer_implementation"] is True
    assert payload["renderer_implementations"]["WEBGPU"] == "SHADOW_ONLY"
    assert payload["renderer_implementations"]["WEBXR"] == "CAPABILITY_ONLY_EXPLICIT_GESTURE"
    assert payload["renderer_authority"] is False
    assert payload["execution_authority"] is False


def test_dynamic_routes_reject_embedded_path_segments():
    state = SpatialServerState()
    assert dispatch_spatial_request(state, "GET", "/api/spatial/projections/a/b").status == 400
    assert dispatch_spatial_request(state, "GET", "/api/spatial/scenes/a/b").status == 400
    assert dispatch_spatial_request(state, "GET", "/api/spatial/sessions/a/b").status == 400
