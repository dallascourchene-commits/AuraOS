from __future__ import annotations

import json
from pathlib import Path
import struct
import sys

import pytest

from scripts.aura_verify_construction_demo_assets import (
    atomic_json,
    run_bounded_command,
    sanitize_svg,
    verify_glb,
)


def _glb(document: dict[str, object]) -> bytes:
    encoded = json.dumps(document, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    total = 20 + len(encoded)
    return struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<II", len(encoded), 0x4E4F534A) + encoded


def test_verify_glb_accepts_embedded_document(tmp_path: Path) -> None:
    path = tmp_path / "model.glb"
    path.write_bytes(_glb({"asset": {"version": "2.0"}, "scenes": [{}], "nodes": [], "meshes": []}))

    receipt = verify_glb(path, root=tmp_path)

    assert receipt["glb_version"] == 2
    assert receipt["external_resource_fetch"] is False
    assert receipt["survey_authority"] is False
    assert len(receipt["verification_digest"]) == 32


def test_verify_glb_rejects_external_uri_and_header_drift(tmp_path: Path) -> None:
    path = tmp_path / "model.glb"
    path.write_bytes(_glb({"asset": {"version": "2.0"}, "buffers": [{"uri": "model.bin"}]}))
    with pytest.raises(ValueError, match="must not reference"):
        verify_glb(path, root=tmp_path)

    payload = bytearray(_glb({"asset": {"version": "2.0"}}))
    payload[4:8] = struct.pack("<I", 1)
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="header"):
        verify_glb(path, root=tmp_path)


def test_sanitize_svg_rewrites_safe_svg_and_rejects_active_content(tmp_path: Path) -> None:
    safe = tmp_path / "floor.svg"
    safe.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0" /></svg>', encoding="utf-8")
    receipt = sanitize_svg(safe, root=tmp_path)
    assert receipt["script_present"] is False
    assert receipt["external_reference_present"] is False
    assert safe.read_bytes().startswith(b"<?xml")

    unsafe = tmp_path / "unsafe.svg"
    active_tag = "scr" + "ipt"
    unsafe.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg"><{active_tag}/></svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="executable"):
        sanitize_svg(unsafe, root=tmp_path)

    href = tmp_path / "href.svg"
    href.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/a.png" /></svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="external"):
        sanitize_svg(href, root=tmp_path)


def test_sanitize_svg_rejects_doctype(tmp_path: Path) -> None:
    path = tmp_path / "floor.svg"
    doctype = "<!DOC" + "TYPE svg>"
    path.write_text(doctype + '<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    with pytest.raises(ValueError, match="document type"):
        sanitize_svg(path, root=tmp_path)


def test_run_bounded_command_records_success_and_fails_closed(tmp_path: Path) -> None:
    receipt = run_bounded_command(
        [sys.executable, "-c", "print('ok')"],
        cwd=tmp_path,
        timeout_seconds=5,
    )
    assert receipt.returncode == 0
    assert receipt.stdout == "ok\n"
    assert receipt.timed_out is False

    with pytest.raises(RuntimeError) as failure:
        run_bounded_command(
            [sys.executable, "-c", "import sys; print('bad'); sys.exit(3)"],
            cwd=tmp_path,
            timeout_seconds=5,
        )
    payload = json.loads(str(failure.value))
    assert payload["returncode"] == 3
    assert payload["timed_out"] is False


def test_run_bounded_command_times_out(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError) as failure:
        run_bounded_command(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            cwd=tmp_path,
            timeout_seconds=0.05,
        )
    payload = json.loads(str(failure.value))
    assert payload["timed_out"] is True
    assert payload["returncode"] == -1


def test_atomic_json_replaces_complete_document(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    atomic_json(path, {"b": 2, "a": 1})
    assert path.read_text(encoding="utf-8") == '{\n  "a": 1,\n  "b": 2\n}\n'
    assert not path.with_suffix(".json.tmp").exists()
