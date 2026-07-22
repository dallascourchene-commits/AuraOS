from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import sys

import pytest

from scripts.aura_verify_construction_demo_assets import (
    CommandReceipt,
    MAX_COMMAND_OUTPUT_BYTES,
    atomic_json,
    run_bounded_command,
    sanitize_svg,
    verify_glb,
)


def _chunk(chunk_type: int, payload: bytes) -> bytes:
    return struct.pack("<II", len(payload), chunk_type) + payload


def _glb(document: dict[str, object], *extra_chunks: tuple[int, bytes]) -> bytes:
    encoded = json.dumps(document, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    chunks = [_chunk(0x4E4F534A, encoded)]
    for chunk_type, payload in extra_chunks:
        assert len(payload) % 4 == 0
        chunks.append(_chunk(chunk_type, payload))
    body = b"".join(chunks)
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body


def test_verify_glb_accepts_embedded_document(tmp_path: Path) -> None:
    path = tmp_path / "model.glb"
    path.write_bytes(
        _glb(
            {
                "asset": {"version": "2.0"},
                "buffers": [{"byteLength": 4}],
                "scenes": [{}],
                "nodes": [],
                "meshes": [],
            },
            (0x004E4942, b"\x00\x00\x00\x00"),
        )
    )

    receipt = verify_glb(path, root=tmp_path)

    assert receipt["glb_version"] == 2
    assert receipt["gltf_asset_version"] == "2.0"
    assert receipt["chunk_count"] == 2
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


def test_verify_glb_rejects_invalid_chunk_layout_and_metadata(tmp_path: Path) -> None:
    path = tmp_path / "model.glb"

    missing_asset = _glb({"scenes": []})
    path.write_bytes(missing_asset)
    with pytest.raises(ValueError, match="asset metadata"):
        verify_glb(path, root=tmp_path)

    path.write_bytes(_glb({"asset": {"version": "1.0"}}))
    with pytest.raises(ValueError, match="version 2"):
        verify_glb(path, root=tmp_path)

    misaligned_json = json.dumps({"asset": {"version": "2.0"}}).encode("utf-8")
    body = _chunk(0x4E4F534A, misaligned_json)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    with pytest.raises(ValueError, match="4-byte aligned"):
        verify_glb(path, root=tmp_path)

    valid = bytearray(_glb({"asset": {"version": "2.0"}}))
    valid.extend(b"JUNK")
    valid[8:12] = struct.pack("<I", len(valid))
    path.write_bytes(valid)
    with pytest.raises(ValueError, match="trailing chunk header"):
        verify_glb(path, root=tmp_path)

    duplicate_json = _glb(
        {"asset": {"version": "2.0"}},
        (0x4E4F534A, b"{}  "),
    )
    path.write_bytes(duplicate_json)
    with pytest.raises(ValueError, match="exactly one JSON"):
        verify_glb(path, root=tmp_path)


def test_sanitize_svg_rewrites_safe_svg_and_rejects_active_content(tmp_path: Path) -> None:
    safe = tmp_path / "floor.svg"
    safe.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><defs><clipPath id="c"/></defs>'
        '<path style="clip-path:url(#c)" d="M0 0" /></svg>',
        encoding="utf-8",
    )
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


def test_sanitize_svg_rejects_css_external_references(tmp_path: Path) -> None:
    style_attribute = tmp_path / "style-attribute.svg"
    style_attribute.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:url(https://example.invalid/a.svg)"/></svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="external"):
        sanitize_svg(style_attribute, root=tmp_path)

    style_element = tmp_path / "style-element.svg"
    style_element.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url("https://example.invalid/a.css");</style></svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="external"):
        sanitize_svg(style_element, root=tmp_path)


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
    assert receipt.output_limit_exceeded is False

    with pytest.raises(RuntimeError) as failure:
        run_bounded_command(
            [sys.executable, "-c", "import sys; print('bad'); sys.exit(3)"],
            cwd=tmp_path,
            timeout_seconds=5,
        )
    payload = json.loads(str(failure.value))
    assert payload["returncode"] == 3
    assert payload["timed_out"] is False


def test_run_bounded_command_enforces_output_limit_while_running(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError) as failure:
        run_bounded_command(
            [
                sys.executable,
                "-c",
                f"import sys; sys.stdout.buffer.write(b'x' * {MAX_COMMAND_OUTPUT_BYTES + 65536}); sys.stdout.flush()",
            ],
            cwd=tmp_path,
            timeout_seconds=5,
        )
    payload = json.loads(str(failure.value))
    assert payload["output_limit_exceeded"] is True
    assert payload["returncode"] == -2
    assert payload["stdout_truncated"] is True
    assert len(payload["stdout"].encode("utf-8")) <= MAX_COMMAND_OUTPUT_BYTES


def test_run_bounded_command_times_out_and_terminates_process_group(tmp_path: Path) -> None:
    marker = tmp_path / "child-finished"
    code = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable, '-c', \"import time,pathlib; time.sleep(1); pathlib.Path(r'{marker}').write_text('bad')\"]); "
        "time.sleep(2)"
    )
    with pytest.raises(RuntimeError) as failure:
        run_bounded_command([sys.executable, "-c", code], cwd=tmp_path, timeout_seconds=0.05)
    payload = json.loads(str(failure.value))
    assert payload["timed_out"] is True
    assert payload["returncode"] == -1
    if os.name != "nt":
        import time

        time.sleep(1.1)
        assert not marker.exists()



def test_command_receipt_digest_excludes_volatile_duration() -> None:
    first = CommandReceipt(
        command=("tool", "--version"),
        returncode=0,
        duration_seconds=0.1,
        stdout="tool 1.0\n",
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
        timed_out=False,
    )
    second = CommandReceipt(
        command=("tool", "--version"),
        returncode=0,
        duration_seconds=9.9,
        stdout="tool 1.0\n",
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
        timed_out=False,
    )

    assert first.receipt_digest == second.receipt_digest
    assert first.to_content_dict() == second.to_content_dict()
    assert first.to_dict()["duration_seconds"] != second.to_dict()["duration_seconds"]


def test_run_bounded_command_terminates_descendants_after_parent_success(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("POSIX process-group semantics required")
    marker = tmp_path / "orphan-finished"
    child_code = (
        "import time,pathlib; "
        "time.sleep(0.4); "
        f"pathlib.Path(r'{marker}').write_text('bad')"
    )
    code = (
        "import subprocess,sys; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "print('parent-done')"
    )

    receipt = run_bounded_command(
        [sys.executable, "-c", code], cwd=tmp_path, timeout_seconds=5
    )
    assert receipt.returncode == 0
    import time

    time.sleep(0.6)
    assert not marker.exists()


def test_sanitize_svg_rejects_relative_resource_references(tmp_path: Path) -> None:
    relative_href = tmp_path / "relative-href.svg"
    relative_href.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="other.svg" /></svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="external"):
        sanitize_svg(relative_href, root=tmp_path)

    relative_css = tmp_path / "relative-css.svg"
    relative_css.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:url(other.svg)" /></svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="external"):
        sanitize_svg(relative_css, root=tmp_path)


def test_atomic_json_rejects_symlinked_parent_outside_root(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    generated.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    receipts = generated / "receipts"
    try:
        receipts.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")

    with pytest.raises(ValueError, match="allowed root"):
        atomic_json(receipts / "escape.json", {"ok": False}, root=generated)
    assert not (outside / "escape.json").exists()


def test_atomic_json_replaces_complete_document_without_predictable_temp(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    legacy_temp = path.with_suffix(".json.tmp")
    victim = tmp_path / "victim.txt"
    victim.write_text("untouched", encoding="utf-8")
    try:
        legacy_temp.symlink_to(victim)
    except OSError:
        pytest.skip("symlinks unavailable")

    atomic_json(path, {"b": 2, "a": 1}, root=tmp_path)

    assert path.read_text(encoding="utf-8") == '{\n  "a": 1,\n  "b": 2\n}\n'
    assert victim.read_text(encoding="utf-8") == "untouched"
    assert legacy_temp.is_symlink()
    assert not list(tmp_path.glob(".receipt.json.*.tmp"))


def test_verify_glb_rejects_missing_bin_and_invalid_ranges(tmp_path: Path) -> None:
    path = tmp_path / "ranges.glb"
    path.write_bytes(
        _glb({"asset": {"version": "2.0"}, "buffers": [{"byteLength": 4}]})
    )
    with pytest.raises(ValueError, match="BIN chunk"):
        verify_glb(path, root=tmp_path)

    path.write_bytes(
        _glb(
            {
                "asset": {"version": "2.0"},
                "buffers": [{"byteLength": 4}],
                "bufferViews": [{"buffer": 0, "byteOffset": 2, "byteLength": 4}],
            },
            (0x004E4942, b"\x00\x00\x00\x00"),
        )
    )
    with pytest.raises(ValueError, match="bufferView"):
        verify_glb(path, root=tmp_path)

    path.write_bytes(
        _glb(
            {
                "asset": {"version": "2.0"},
                "buffers": [{"byteLength": 4}],
                "bufferViews": [{"buffer": 0, "byteLength": 4}],
                "accessors": [
                    {"bufferView": 0, "componentType": 5126, "count": 2, "type": "SCALAR"}
                ],
            },
            (0x004E4942, b"\x00\x00\x00\x00"),
        )
    )
    with pytest.raises(ValueError, match="accessor range"):
        verify_glb(path, root=tmp_path)

    path.write_bytes(
        _glb(
            {
                "asset": {"version": "2.0"},
                "buffers": [{"byteLength": 4}],
                "bufferViews": [{"buffer": 0, "byteLength": 4}],
                "accessors": [
                    {"bufferView": 0, "componentType": 5126, "count": 1, "type": "SCALAR"}
                ],
                "meshes": [{"primitives": [{"attributes": {"POSITION": 1}}]}],
            },
            (0x004E4942, b"\x00\x00\x00\x00"),
        )
    )
    with pytest.raises(ValueError, match="accessor index"):
        verify_glb(path, root=tmp_path)


def test_sanitize_svg_rejects_css_escaped_url_identifier(tmp_path: Path) -> None:
    path = tmp_path / "escaped-url.svg"
    path.write_text(
        r'<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:u\72l(https://example.invalid/a.svg)"/></svg>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="external"):
        sanitize_svg(path, root=tmp_path)
