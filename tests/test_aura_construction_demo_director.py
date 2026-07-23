from __future__ import annotations

from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading

import pytest

from aura_construction_demo_director import (
    CONSTRUCTION_DEMO_TOURS,
    FALLBACK_GAUSSIAN_REPRESENTATION_DIGEST,
    _ConstructionDemoHandler,
    _safe_construction_demo_static_file,
    _safe_construction_demo_static_path,
    build_fallback_construction_demo_asset_pack,
    compile_construction_demo_packet,
    write_construction_demo_packet,
)


def test_g7_fallback_pack_is_complete_and_browser_admissible() -> None:
    pack = build_fallback_construction_demo_asset_pack()

    assert len(pack.storeys) == 5
    assert len(pack.assets) == 15
    assert all(item.survey_authority is False for item in pack.assets)
    gaussian_assets = [item for item in pack.assets if item.representation == "GAUSSIAN_SPZ"]
    assert len(gaussian_assets) == 5
    assert all(item.representation_digest == FALLBACK_GAUSSIAN_REPRESENTATION_DIGEST for item in gaussian_assets)
    assert all(len(item.import_receipt_digest) == 64 for item in gaussian_assets)


def test_g7_full_tour_packet_is_deterministic_and_review_only() -> None:
    first = compile_construction_demo_packet(tour="full")
    second = compile_construction_demo_packet(tour="full")

    assert first == second
    assert first["fallback_asset_pack"] is True
    assert first["scene"]["scene_digest"] == second["scene"]["scene_digest"]
    assert first["render_plan"]["selected_renderer"] == "WEBGL2"
    assert len(first["tour_steps"]) == 18
    assert first["tour_steps"][-1]["action"] == "DISSOLVE"
    assert first["physical_work_authorized"] is False
    assert first["payment_released"] is False
    assert first["automatic_execution"] is False
    assert first["automatic_merge"] is False
    assert first["human_review_required"] is True

    gaussian_assets = [item for item in first["scene"]["assets"] if item["asset_type"] == "GAUSSIAN_SPLAT"]
    assert gaussian_assets
    assert all(
        item["metadata"]["representation_digest"] == FALLBACK_GAUSSIAN_REPRESENTATION_DIGEST for item in gaussian_assets
    )
    assert all(item["metadata"]["gaussian_sh_degree"] == 0 for item in gaussian_assets)


def test_g7_bounded_tours_are_subsets_of_full_tour() -> None:
    full_ids = {item["step_id"] for item in compile_construction_demo_packet(tour="full")["tour_steps"]}
    for tour in CONSTRUCTION_DEMO_TOURS:
        packet = compile_construction_demo_packet(tour=tour)
        ids = {item["step_id"] for item in packet["tour_steps"]}
        assert ids
        assert ids.issubset(full_ids)
        assert packet["tour"] == tour


def test_g7_packet_writer_uses_canonical_json(tmp_path: Path) -> None:
    packet = compile_construction_demo_packet(tour="alternatives")
    output = write_construction_demo_packet(packet, tmp_path / "packet.json")

    text = output.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == packet
    assert " " not in text.splitlines()[0][:20]


def test_g7_rejects_unknown_tour() -> None:
    with pytest.raises(ValueError, match="unsupported Construction demo tour"):
        compile_construction_demo_packet(tour="unbounded")


def test_g7_local_static_boundary_rejects_repository_exposure() -> None:
    assert (
        _safe_construction_demo_static_path("/aura_spatial_web/construction_demo.html")
        == "/aura_spatial_web/construction_demo.html"
    )
    assert (
        _safe_construction_demo_static_path(
            "/demo_assets/construction_tuwien/generated/storeys/storey-00/storey-00.glb"
        )
        == "/demo_assets/construction_tuwien/generated/storeys/storey-00/storey-00.glb"
    )
    for rejected in (
        "/README.md",
        "/../README.md",
        "/%2e%2e/README.md",
        "/aura_spatial_web/%252e%252e/README.md",
        "/aura_spatial_web/%25252e%25252e/README.md",
        "/aura_spatial_web/../README.md",
        "\\README.md",
    ):
        assert _safe_construction_demo_static_path(rejected) is None


def test_g7_local_static_boundary_rejects_symlink_escape(tmp_path: Path) -> None:
    spatial = tmp_path / "aura_spatial_web"
    generated = tmp_path / "demo_assets" / "construction_tuwien" / "generated"
    spatial.mkdir(parents=True)
    generated.mkdir(parents=True)
    outside = tmp_path / "private.txt"
    outside.write_text("secret", encoding="utf-8")
    link = spatial / "escape.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    assert _safe_construction_demo_static_file(tmp_path, "/aura_spatial_web/escape.txt") is None


def test_g7_http_get_and_head_share_the_static_allowlist(tmp_path: Path) -> None:
    spatial = tmp_path / "aura_spatial_web"
    spatial.mkdir()
    (spatial / "construction_demo.html").write_text("demo", encoding="utf-8")
    (tmp_path / "README.md").write_text("private", encoding="utf-8")
    handler_type = type("TestConstructionDemoHandler", (_ConstructionDemoHandler,), {"packet": b"{}\n"})
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(handler_type, directory=str(tmp_path)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        for method, path, expected in (
            ("GET", "/demo/construction", 200),
            ("HEAD", "/demo/construction", 200),
            ("GET", "/aura_spatial_web/%252e%252e/README.md", 404),
            ("HEAD", "/README.md", 404),
        ):
            connection.request(method, path)
            response = connection.getresponse()
            response.read()
            assert response.status == expected
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
