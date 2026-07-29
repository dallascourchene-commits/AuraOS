from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_construction_pascal_spatial_foundry_server import (
    PASCAL_FOUNDRY_SERVER_VERSION,
    _body_must_not_supply_identity,
    _loopback_origin,
    _static_response,
)
from aura_pascal_spatial_presentation import PascalPresentationError

ROOT = Path(__file__).resolve().parents[1]


def test_loopback_origin_is_exact_and_non_loopback_origins_fail_closed():
    assert _loopback_origin("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert _loopback_origin("http://localhost:9000/") == "http://localhost:9000"
    assert _loopback_origin("http://[::1]:8000") == "http://[::1]:8000"
    with pytest.raises(PascalPresentationError, match="loopback-only"):
        _loopback_origin("https://example.com")
    with pytest.raises(PascalPresentationError, match="path, query, or fragment"):
        _loopback_origin("http://127.0.0.1:8000/workbench")


def test_browser_cannot_supply_server_owned_pascal_session_identity():
    _body_must_not_supply_identity({"action": "SET_VIEW_2D", "payload": {}})
    for key in ("expected_origin", "spatial_scene_digest", "render_plan_digest", "pascal_artifact_digest", "coordinate_receipt_digest", "state_binding_digest", "sequence", "nonce", "direction", "message_digest"):
        with pytest.raises(PascalPresentationError, match="server-owned"):
            _body_must_not_supply_identity({key: "caller-value"})


def test_pascal_static_surface_is_same_origin_and_pr1_markup_is_retained():
    status, content_type, body = _static_response("/pascal-workbench/index.html")
    assert status == 200 and content_type.startswith("text/html")
    assert b"pascal-workbench.js" in body and b"https://" not in body and b"http://" not in body
    status, _, body = _static_response("/")
    assert status == 200
    assert b'id="construction-foundry-pr1"' in body and b'id="pascal-construction-foundry"' in body
    assert b"construction-spatial-foundry.js" in body and b"pascal-construction-foundry.js" in body


def test_pascal_contract_assets_are_served_as_exact_committed_json():
    for name in ("fixture.json", "artifact-manifest.json", "coordinate-receipt.json"):
        status, content_type, body = _static_response(f"/pascal-workbench/{name}")
        assert status == 200 and content_type.startswith("application/json")
        assert json.loads(body.decode("utf-8")) == json.loads((ROOT / "aura_showcase" / "pascal-workbench" / name).read_text(encoding="utf-8"))


def test_server_version_is_explicit_and_no_pascal_path_traversal_is_admitted():
    assert PASCAL_FOUNDRY_SERVER_VERSION == "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_SERVER_V1"
    status, _, _ = _static_response("/pascal-workbench/../fixture.json")
    assert status == 404
