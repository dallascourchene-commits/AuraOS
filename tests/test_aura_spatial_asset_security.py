from __future__ import annotations

import base64
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import unicodedata

import pytest

from aura_spatial_asset_registry import SpatialAssetRegistry, validate_asset_manifest
from aura_spatial_contracts import SpatialAssetManifest, SpatialAssetType
from aura_spatial_importers.gltf import import_gltf_bytes
from aura_spatial_importers.spz import import_spz_bytes, inspect_spz_v4_bytes

ROOT = Path(__file__).resolve().parents[1]
GLTF = ROOT / "tests/fixtures/spatial/gltf/triangle.gltf"
_HEADER = struct.Struct("<IIIBBBBI12s")
_TOC = struct.Struct("<QQ")


def _manifest(asset_id: str, uri: str) -> SpatialAssetManifest:
    content = asset_id.encode()
    return SpatialAssetManifest(
        asset_id=asset_id,
        asset_type=SpatialAssetType.MESH,
        uri=uri,
        media_type="model/gltf+json",
        content_digest="sha256:" + hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        frame_id="root",
        bounds_min=(0.0, 0.0, 0.0),
        bounds_max=(1.0, 1.0, 1.0),
        source_refs=(f"fixture:{asset_id}",),
    )


def test_asset_registry_rejects_case_unicode_percent_and_separator_aliases() -> None:
    with pytest.raises(ValueError, match="aliased"):
        SpatialAssetRegistry(
            (
                _manifest("asset:one", "aura://assets/Model.glb"),
                _manifest("asset:two", "aura://assets/model.glb"),
            )
        )

    nfd = unicodedata.normalize("NFD", "assets/café.glb")
    report = validate_asset_manifest(_manifest("asset:nfd", nfd))
    assert any(item["code"] == "NONCANONICAL_ASSET_UNICODE" for item in report.findings)

    for uri in ("assets/%2e%2e/secret.glb", "assets\\secret.glb", "assets//mesh.glb", "../mesh.glb"):
        report = validate_asset_manifest(_manifest("asset:path", uri))
        assert report.ok is False


def test_gltf_rejects_recursive_metadata_absurd_counts_and_overlapping_ranges() -> None:
    recursive = json.loads(GLTF.read_text())
    nested: dict[str, object] = {}
    cursor = nested
    for _ in range(40):
        child: dict[str, object] = {}
        cursor["child"] = child
        cursor = child
    recursive["extras"] = nested
    with pytest.raises(ValueError, match="depth/item"):
        import_gltf_bytes(json.dumps(recursive).encode(), provenance_refs=("fixture",))

    absurd = json.loads(GLTF.read_text())
    absurd["accessors"][0]["count"] = 2_000_001
    with pytest.raises(ValueError, match="count"):
        import_gltf_bytes(json.dumps(absurd).encode(), provenance_refs=("fixture",))

    overlap = json.loads(GLTF.read_text())
    overlap["bufferViews"].append(dict(overlap["bufferViews"][0]))
    with pytest.raises(ValueError, match=r"overlap|alias"):
        import_gltf_bytes(json.dumps(overlap).encode(), provenance_refs=("fixture",))


def test_gltf_accepts_adjacent_non_overlapping_buffer_view_boundary() -> None:
    document = json.loads(GLTF.read_text())
    encoded = document["buffers"][0]["uri"].split(",", 1)[1]
    raw = base64.b64decode(encoded) + b"\x00\x00\x00\x00"
    original_length = document["buffers"][0]["byteLength"]
    document["buffers"][0]["byteLength"] = len(raw)
    document["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(raw).decode()
    document["bufferViews"].append({"buffer": 0, "byteOffset": original_length, "byteLength": 4})
    result = import_gltf_bytes(json.dumps(document).encode(), provenance_refs=("fixture",))
    assert result.receipt.element_count == 3


def test_spz_rejects_bomb_geometry_overflow_and_provenance_gap_before_decode() -> None:
    # One byte cannot expand to the exact declared position stream under Aura's ratio ceiling.
    point_count = 500_000
    expected = [point_count * 9, point_count, point_count * 3, point_count * 3, point_count * 4]
    header = _HEADER.pack(0x5053474E, 4, point_count, 0, 12, 0, 5, 32, b"\x00" * 12)
    toc = b"".join(_TOC.pack(1, size) for size in expected)
    source = header + toc + b"x" * 5
    with pytest.raises(ValueError, match="decompression-ratio"):
        inspect_spz_v4_bytes(source)

    overflow = bytearray(header + toc + b"x" * 5)
    struct.pack_into("<Q", overflow, 32, 2**64 - 1)
    with pytest.raises(ValueError, match="compressed stream size"):
        inspect_spz_v4_bytes(bytes(overflow))

    # A valid empty provenance packet must fail at the receipt boundary, not invent provenance.
    valid = _minimal_spz()
    with pytest.raises(ValueError, match="provenance"):
        import_spz_bytes(valid, provenance_refs=())


def _minimal_spz() -> bytes:
    import zstandard

    streams = [b"\x00" * 9, b"\xff", b"\x80\x80\x80", b"\xa0\xa0\xa0", b"\x00\x00\x00\xc0"]
    compressed = [zstandard.ZstdCompressor(level=1).compress(item) for item in streams]
    header = _HEADER.pack(0x5053474E, 4, 1, 0, 12, 0, 5, 32, b"\x00" * 12)
    toc = b"".join(_TOC.pack(len(blob), len(raw)) for blob, raw in zip(compressed, streams))
    return header + toc + b"".join(compressed)


def test_spz_validation_and_cancellation_precede_backend_allocation() -> None:
    calls = 0

    def backend(_payload: bytes, expected: int) -> bytes:
        nonlocal calls
        calls += 1
        return b"\x00" * expected

    malformed = bytearray(_minimal_spz())
    malformed[20] = 1  # reserved field
    with pytest.raises(ValueError, match="reserved"):
        import_spz_bytes(bytes(malformed), provenance_refs=("fixture",), decompressor=backend)
    assert calls == 0

    with pytest.raises(ValueError, match="cancelled"):
        import_spz_bytes(
            _minimal_spz(),
            provenance_refs=("fixture",),
            cancelled=lambda: True,
            decompressor=backend,
        )
    assert calls == 0


def test_valid_security_boundaries_do_not_false_positive() -> None:
    result = import_spz_bytes(_minimal_spz(), provenance_refs=("fixture:valid-boundary",))
    assert result.receipt.element_count == 1
    report = validate_asset_manifest(_manifest("asset:valid", "aura://assets/valid-1.0.spz"))
    assert report.ok is True


def test_import_result_metadata_is_recursively_frozen_and_bounded() -> None:
    base = import_spz_bytes(_minimal_spz(), provenance_refs=("fixture:metadata",))
    result = replace(
        base,
        metadata={
            "outer": {"items": [{"value": 1}, {"value": 2}]},
            "flags": [True, False],
        },
    )
    assert result.metadata["outer"]["items"][0]["value"] == 1
    with pytest.raises(TypeError):
        result.metadata["outer"]["items"][0]["value"] = 3
    exported = result.to_dict()
    exported["metadata"]["outer"]["items"][0]["value"] = 9
    assert result.metadata["outer"]["items"][0]["value"] == 1

    recursive: dict[str, object] = {}
    recursive["self"] = recursive
    with pytest.raises(ValueError, match="recursive"):
        replace(base, metadata=recursive)

    deep: dict[str, object] = {}
    cursor = deep
    for _ in range(14):
        child: dict[str, object] = {}
        cursor["child"] = child
        cursor = child
    with pytest.raises(ValueError, match="depth/item"):
        replace(base, metadata=deep)

    with pytest.raises(ValueError, match="non-finite"):
        replace(base, metadata={"value": float("nan")})
