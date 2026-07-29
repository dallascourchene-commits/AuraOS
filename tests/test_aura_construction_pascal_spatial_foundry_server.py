from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest

import aura_construction_pascal_spatial_foundry_server as server_module
from aura_construction_pascal_spatial_foundry_server import (
    IPv6HTTPServer,
    PASCAL_FOUNDRY_SERVER_VERSION,
    PascalFoundryShowcaseState,
    _body_must_not_supply_identity,
    _content_security_policy,
    _loopback_origin,
    _static_response,
    dispatch_pascal_foundry_request,
)
from aura_pascal_spatial_presentation import (
    AuraPascalBridgeMessage,
    BridgeDirection,
    PascalBridgeAction,
    PascalPresentationError,
)

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8000"
HOST = "127.0.0.1:8000"


@pytest.fixture
def state():
    value = PascalFoundryShowcaseState(
        ROOT,
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin=ORIGIN,
    )
    try:
        yield value
    finally:
        value.close()


def decoded(response):
    return response[0], json.loads(response[2].decode("utf-8"))


def dispatch(state, method, path, body=None, *, origin=ORIGIN, host=HOST):
    return dispatch_pascal_foundry_request(
        state,
        method,
        path,
        body,
        request_origin=origin,
        request_host=host,
    )


def child_message(session_status, action, payload, *, sequence, nonce):
    return AuraPascalBridgeMessage.build(
        session_id=session_status["session_id"],
        sequence=sequence,
        spatial_scene_digest=session_status["spatial_scene_digest"],
        render_plan_digest=session_status["render_plan_digest"],
        pascal_artifact_digest=session_status["pascal_artifact_digest"],
        coordinate_receipt_digest=session_status["coordinate_receipt_digest"],
        state_binding_digest=session_status["state_binding_digest"],
        direction=BridgeDirection.PASCAL_TO_PARENT,
        action=action,
        payload=payload,
        nonce=nonce,
        message_id=f"PBM-{nonce}",
    ).to_dict()


def test_loopback_origin_is_exact_and_non_loopback_origins_fail_closed():
    assert _loopback_origin("http://127.0.0.1:8000") == ORIGIN
    assert _loopback_origin("http://localhost:9000/") == "http://localhost:9000"
    assert _loopback_origin("http://[::1]:8000") == "http://[::1]:8000"
    with pytest.raises(PascalPresentationError, match="loopback-only"):
        _loopback_origin("https://example.com")
    with pytest.raises(PascalPresentationError, match="path, query, or fragment"):
        _loopback_origin("http://127.0.0.1:8000/workbench")
    with pytest.raises(PascalPresentationError, match="invalid port"):
        _loopback_origin("http://127.0.0.1:99999")


def test_browser_cannot_supply_server_owned_pascal_session_identity():
    _body_must_not_supply_identity({"action": "SET_VIEW_2D", "payload": {}})
    for key in (
        "expected_origin",
        "origin",
        "spatial_scene_digest",
        "render_plan_digest",
        "pascal_artifact_digest",
        "coordinate_receipt_digest",
        "state_binding_digest",
        "sequence",
        "nonce",
        "direction",
        "message_digest",
    ):
        with pytest.raises(PascalPresentationError, match="server-owned"):
            _body_must_not_supply_identity({key: "caller-value"})


def test_manifest_and_static_assets_are_gated_by_successful_validation(state):
    status, manifest = decoded(
        dispatch(state, "GET", "/api/construction/pascal/manifest", origin=None)
    )
    assert status == 200
    assert manifest["ok"] is True
    assert manifest["available"] is True
    assert manifest["pr1_fallback_available"] is True

    status, content_type, body = _static_response(
        "/pascal-workbench/index.html",
        state,
    )
    assert status == 200
    assert content_type.startswith("text/html")
    assert b"pascal-workbench.js" in body
    status, _, body = _static_response("/", state)
    assert status == 200
    assert b'id="construction-foundry-pr1"' in body
    assert b'id="pascal-construction-foundry"' in body
    assert b"pascal-construction-foundry.css" in body

    state.pascal_registry = None
    status, unavailable = decoded(
        dispatch(state, "GET", "/api/construction/pascal/manifest", origin=None)
    )
    assert status == 503
    assert unavailable["available"] is False
    assert unavailable["pr1_fallback_available"] is True
    assert _static_response("/pascal-workbench/index.html", state)[0] == 404
    fallback = _static_response("/", state)[2]
    assert b'id="construction-foundry-pr1"' in fallback
    assert b'id="pascal-construction-foundry"' not in fallback


def test_actual_host_and_origin_are_required_for_pascal_api(state):
    assert decoded(
        dispatch(
            state,
            "GET",
            "/api/construction/pascal/manifest",
            origin=None,
            host="evil.example",
        )
    )[0] == 409
    assert decoded(
        dispatch(
            state,
            "POST",
            "/api/construction/pascal/session/start",
            {},
            origin=None,
        )
    )[0] == 409
    assert decoded(
        dispatch(
            state,
            "POST",
            "/api/construction/pascal/session/start",
            {},
            origin="http://localhost:8000",
        )
    )[0] == 409


def test_dispatch_session_roundtrip_binds_receipts_and_finalizes_dissolution(state):
    status, start = decoded(
        dispatch(state, "POST", "/api/construction/pascal/session/start", {})
    )
    assert status == 200
    assert start["ok"] is True
    assert start["workbench_path"] == "/pascal-workbench/index.html"
    assert start["same_origin_required"] is True
    session = start["session"]
    session_id = session["session_id"]

    ready = child_message(
        session,
        PascalBridgeAction.READY,
        {
            "renderer_kind": "LOCAL_CANVAS_PASCAL_COMPATIBILITY",
            "external_requests": 0,
            "working_copy_only": True,
        },
        sequence=1,
        nonce="ready",
    )
    status, retained = decoded(
        dispatch(
            state,
            "POST",
            f"/api/construction/pascal/session/{session_id}/event",
            {"message": ready},
        )
    )
    assert status == 200
    session = retained["session"]
    assert session["state"] == "READY"

    status, issued = decoded(
        dispatch(
            state,
            "POST",
            f"/api/construction/pascal/session/{session_id}/command",
            {
                "action": "LOAD_ARTIFACT",
                "payload": {
                    "scene": start["scene"],
                    "artifact_manifest": start["artifact_manifest"],
                    "initial_view": "2D",
                    "dimensions_visible": True,
                },
            },
        )
    )
    assert status == 200
    command = issued["message"]
    session = issued["session"]

    load_receipt = child_message(
        session,
        PascalBridgeAction.LOAD_RECEIPT,
        {
            "command_message_digest": command["message_digest"],
            "loaded": True,
            "view": "2D",
            "storey_id": "L1",
            "node_id": start["artifact_manifest"]["root_node_id"],
            "dimensions_visible": True,
            "node_count": len(start["artifact_manifest"]["node_bindings"]),
            "external_requests": 0,
        },
        sequence=2,
        nonce="load",
    )
    status, retained = decoded(
        dispatch(
            state,
            "POST",
            f"/api/construction/pascal/session/{session_id}/event",
            {"message": load_receipt},
        )
    )
    assert status == 200
    session = retained["session"]
    assert session["state"] == "ACTIVE"

    status, issued = decoded(
        dispatch(
            state,
            "POST",
            f"/api/construction/pascal/session/{session_id}/command",
            {"action": "DISSOLVE", "payload": {}},
        )
    )
    assert status == 200
    command = issued["message"]
    session = issued["session"]
    dissolution = child_message(
        session,
        PascalBridgeAction.DISSOLUTION_RECEIPT,
        {
            "command_message_digest": command["message_digest"],
            "renderer_released": True,
            "listeners_released": True,
            "timers_released": True,
            "buffers_cleared": True,
            "indexeddb_deleted": True,
            "network_guards_restored": True,
            "external_requests": 0,
        },
        sequence=3,
        nonce="dissolve",
    )
    status, retained = decoded(
        dispatch(
            state,
            "POST",
            f"/api/construction/pascal/session/{session_id}/event",
            {"message": dissolution},
        )
    )
    assert status == 200
    assert retained["session"]["dissolution_complete"] is False

    status, finalized = decoded(
        dispatch(
            state,
            "POST",
            f"/api/construction/pascal/session/{session_id}/dissolution/finalize",
            {"iframe_removed": True},
        )
    )
    assert status == 200
    assert finalized["dissolution_receipt"]["iframe_removed"] is True
    assert finalized["session"]["dissolution_complete"] is True


def test_structural_fixture_type_error_keeps_pr1_server_available(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "load_pascal_compatibility_fixture",
        lambda _root: (_ for _ in ()).throw(TypeError("bad structural type")),
    )
    value = PascalFoundryShowcaseState(
        ROOT,
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin=ORIGIN,
    )
    try:
        assert value.pascal_available is False
        assert "bad structural type" in value.pascal_load_error
        status, _, body = _static_response("/", value)
        assert status == 200
        assert b'id="construction-foundry-pr1"' in body
        assert b'id="pascal-construction-foundry"' not in body
    finally:
        value.close()


def test_csp_is_scoped_to_pascal_workbench_and_preserves_pr1_basemap():
    assert _content_security_policy("/") is None
    assert _content_security_policy("/index.html") is None
    policy = _content_security_policy("/pascal-workbench/index.html")
    assert policy is not None
    assert "connect-src 'none'" in policy
    assert "frame-ancestors 'self'" in policy


def test_pascal_static_routes_do_not_admit_path_traversal(state):
    assert _static_response("/pascal-workbench/../fixture.json", state)[0] == 404
    for name in ("fixture.json", "artifact-manifest.json", "coordinate-receipt.json"):
        status, content_type, body = _static_response(
            f"/pascal-workbench/{name}",
            state,
        )
        assert status == 200
        assert content_type.startswith("application/json")
        assert isinstance(json.loads(body.decode("utf-8")), dict)


def test_ipv6_loopback_uses_ipv6_server_family():
    assert IPv6HTTPServer.address_family == socket.AF_INET6
    assert PASCAL_FOUNDRY_SERVER_VERSION == (
        "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_SERVER_V1"
    )
