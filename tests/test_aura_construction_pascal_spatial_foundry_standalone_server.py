from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import aura_construction_pascal_spatial_foundry_standalone_server as standalone


def test_standalone_document_is_construction_only_and_uses_real_owner_surfaces() -> None:
    html = standalone._build_standalone_html().decode("utf-8")

    assert "<title>Aura Construction + Pascal Spatial Foundry</title>" in html
    assert 'data-aura-surface="CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY"' in html
    assert 'id="construction-foundry-director"' in html
    assert 'id="construction-decision-foundry"' in html
    assert 'id="pascal-construction-foundry"' in html
    assert 'id="pascal-workbench-host"' in html
    assert 'id="construction-as-built-frame"' in html

    assert "Civic Arena" not in html
    assert "Winnipeg Community Pathways Lab" not in html
    assert "Human Agent Coding Arena" not in html
    assert "Aura Observatory" not in html
    assert "Learning Arena / Crucible" not in html

    pascal_script = html.index('src="/pascal-construction-foundry.js"')
    p3_script = html.index('src="/construction-decision-foundry.js"')
    p4_script = html.index('src="/construction-foundry-director.js"')
    assert pascal_script < p3_script < p4_script


def test_standalone_root_never_delegates_to_legacy_showcase(monkeypatch) -> None:
    state = SimpleNamespace(
        standalone_available=True,
        standalone_html=b"<html>construction-only</html>",
        standalone_css=b"body{}",
        standalone_load_error="",
    )

    def forbidden_delegate(route, delegated_state):
        raise AssertionError(f"root delegated to legacy route {route!r}")

    monkeypatch.setattr(standalone, "p4_static_response", forbidden_delegate)

    status, content_type, body = standalone._static_response("/", state)
    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    assert body == state.standalone_html


def test_construction_aliases_resolve_to_the_same_standalone_document() -> None:
    state = SimpleNamespace(
        standalone_available=True,
        standalone_html=b"<html>construction-only</html>",
        standalone_css=b"body{}",
        standalone_load_error="",
    )
    for route in (
        "/",
        "/index.html",
        "/construction",
        "/construction/",
        "/construction/index.html",
    ):
        status, content_type, body = standalone._static_response(route, state)
        assert (status, content_type, body) == (
            200,
            "text/html; charset=utf-8",
            state.standalone_html,
        )


def test_legacy_showcase_is_explicit_opt_in(monkeypatch) -> None:
    state = SimpleNamespace(
        standalone_available=True,
        standalone_html=b"<html>construction-only</html>",
        standalone_css=b"body{}",
        standalone_load_error="",
    )
    calls = []

    def delegated(route, delegated_state):
        calls.append((route, delegated_state))
        return 200, "text/html; charset=utf-8", b"legacy"

    monkeypatch.setattr(standalone, "p4_static_response", delegated)

    assert standalone._static_response("/legacy-showcase", state)[2] == b"legacy"
    assert calls == [("/", state)]


def test_standalone_page_csp_is_same_origin_and_frame_capable() -> None:
    policy = standalone._content_security_policy("/")
    assert policy is not None
    assert "connect-src 'self'" in policy
    assert "frame-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "object-src 'none'" in policy


def test_pr5_browser_profile_launches_the_standalone_server() -> None:
    root = Path(__file__).resolve().parents[1]
    profile = json.loads(
        (
            root
            / ".aura/runtime_profiles/construction_pascal_spatial_foundry.v1.json"
        ).read_text(encoding="utf-8")
    )
    command = profile["server"]["command"]
    assert command[1] == (
        "aura_construction_pascal_spatial_foundry_standalone_server.py"
    )
    assert (
        "tests/test_aura_construction_pascal_spatial_foundry_standalone_server.py"
        in profile["verification_commands"][5]["command"]
    )
