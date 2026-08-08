from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.aura_source_anchor_map import generate, resolve_anchor


def _codemap() -> dict:
    return {
        "files": [{"path": "aura_demo.py", "digest8": "cafebabe"}],
        "symbol_index": {
            "demo": [{
                "file": "aura_demo.py",
                "kind": "function",
                "line": 10,
                "end_line": 22,
                "semantic_id": "aura_demo.py#function:demo:stable",
                "signature_hash": "deadbeef",
            }]
        },
    }


def test_resolve_anchor_uses_codemap_identity_and_current_span() -> None:
    result = resolve_anchor(_codemap(), {
        "anchor_id": "demo",
        "mechanism": "Demo",
        "path": "aura_demo.py",
        "symbol": "demo",
        "kind": "function",
        "role": "test",
    })
    assert result["line"] == 10
    assert result["end_line"] == 22
    assert result["semantic_id"].endswith(":stable")
    assert result["signature_hash"] == "deadbeef"


def test_resolve_anchor_fails_closed_on_ambiguity() -> None:
    codemap = _codemap()
    codemap["symbol_index"]["demo"].append(dict(codemap["symbol_index"]["demo"][0]))
    with pytest.raises(ValueError, match="expected exactly one"):
        resolve_anchor(codemap, {
            "anchor_id": "demo",
            "path": "aura_demo.py",
            "symbol": "demo",
            "kind": "function",
        })


def test_generate_regenerates_line_projection(tmp_path: Path) -> None:
    (tmp_path / ".aura").mkdir()
    codemap = _codemap()
    (tmp_path / ".aura/CODEMAP.json").write_text(json.dumps(codemap), encoding="utf-8")
    manifest = {
        "version": "AURA_SOURCE_ANCHOR_MANIFEST_V1",
        "anchors": [{
            "anchor_id": "demo",
            "mechanism": "Demo",
            "path": "aura_demo.py",
            "symbol": "demo",
            "kind": "function",
            "role": "test",
        }],
    }
    (tmp_path / ".aura/source_anchor_manifest.v1.json").write_text(json.dumps(manifest), encoding="utf-8")
    first = generate(
        root=tmp_path,
        codemap_path=Path(".aura/CODEMAP.json"),
        manifest_path=Path(".aura/source_anchor_manifest.v1.json"),
    )
    assert "L10-L22" in first
    codemap["symbol_index"]["demo"][0]["line"] = 40
    codemap["symbol_index"]["demo"][0]["end_line"] = 52
    (tmp_path / ".aura/CODEMAP.json").write_text(json.dumps(codemap), encoding="utf-8")
    second = generate(
        root=tmp_path,
        codemap_path=Path(".aura/CODEMAP.json"),
        manifest_path=Path(".aura/source_anchor_manifest.v1.json"),
    )
    assert "L40-L52" in second
    assert "L10-L22" not in second
