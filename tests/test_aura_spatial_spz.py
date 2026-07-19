from __future__ import annotations

from pathlib import Path
import struct

import pytest
import zstandard

from aura_spatial_importers.spz import (
    MAX_SPZ_DECODED_BYTES,
    SPZ_FORMAT_VERSION,
    import_spz_bytes,
    import_spz_file,
    inspect_spz_v4_bytes,
)

_HEADER = struct.Struct("<IIIBBBBI12s")
_TOC = struct.Struct("<QQ")


def build_spz(
    *,
    positions: bytes = b"\x00" * 9,
    alphas: bytes = b"\xff",
    colors: bytes = b"\xff\x80\x00",
    scales: bytes = b"\xa0\xa0\xa0",
    rotations: bytes = b"\x00\x00\x00\xc0",
    sh: bytes = b"",
    point_count: int = 1,
    sh_degree: int = 0,
    fractional_bits: int = 12,
    flags: int = 0,
    reserved: bytes = b"\x00" * 12,
) -> bytes:
    streams = [positions, alphas, colors, scales, rotations]
    if sh:
        streams.append(sh)
    compressor = zstandard.ZstdCompressor(level=1)
    compressed = [compressor.compress(item) for item in streams]
    toc_offset = _HEADER.size
    header = _HEADER.pack(
        0x5053474E,
        SPZ_FORMAT_VERSION,
        point_count,
        sh_degree,
        fractional_bits,
        flags,
        len(streams),
        toc_offset,
        reserved,
    )
    toc = b"".join(_TOC.pack(len(blob), len(raw)) for blob, raw in zip(compressed, streams))
    return header + toc + b"".join(compressed)


def test_import_spz_v4_decodes_bounded_gaussian_and_point_fallback(tmp_path: Path) -> None:
    source = build_spz()
    result = import_spz_bytes(source, provenance_refs=("fixture:spz",))
    assert result.receipt.source_format.value == "SPZ_V4"
    assert result.receipt.asset_type == "GAUSSIAN_SPLATS"
    assert result.receipt.training_invoked is False
    assert result.positions == ((0.0, 0.0, 0.0),)
    assert result.colors_rgba == ((255, 128, 0, 255),)
    assert result.gaussian_splats is not None
    assert result.gaussian_splats.rotations_xyzw == ((0.0, 0.0, 0.0, 1.0),)
    assert result.gaussian_splats.opacities == (1.0,)
    assert result.metadata["fallback"] == "POINT_CLOUD_RGBA8"
    assert result.metadata["gaussian_color_space"] == "SPZ_INTERNAL_WIDE_RGB"
    assert result.metadata["sh_degree"] == 0

    target = tmp_path / "sample.spz"
    target.write_bytes(source)
    file_result = import_spz_file(target, provenance_refs=("fixture:file",), root=tmp_path)
    assert file_result.receipt.source_digest == result.receipt.source_digest


def test_spz_inspection_validates_before_decompression() -> None:
    source = build_spz()
    header, entries = inspect_spz_v4_bytes(source)
    assert header.point_count == 1
    assert header.stream_count == 5
    assert sum(entry[2] for entry in entries) < MAX_SPZ_DECODED_BYTES

    called = False

    def decoder(_payload: bytes, _size: int) -> bytes:
        nonlocal called
        called = True
        return b""

    malformed = bytearray(source)
    malformed[12] = 5  # unsupported SH degree
    with pytest.raises(ValueError, match="degree"):
        import_spz_bytes(bytes(malformed), provenance_refs=("fixture",), decompressor=decoder)
    assert called is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.__setitem__(slice(0, 4), b"NOPE"), "magic"),
        (lambda data: data.__setitem__(slice(4, 8), struct.pack("<I", 5)), "version"),
        (lambda data: data.__setitem__(slice(8, 12), struct.pack("<I", 0)), "point count"),
        (lambda data: data.__setitem__(13, 255), "fractionalBits"),
        (lambda data: data.__setitem__(14, 0x80), "unknown header flags"),
        (lambda data: data.__setitem__(15, 6), "stream count"),
        (lambda data: data.__setitem__(16, 33), "TOC"),
        (lambda data: data.__setitem__(20, 1), "reserved"),
    ],
)
def test_spz_rejects_malformed_header_before_allocation(mutation, message: str) -> None:
    source = bytearray(build_spz())
    mutation(source)
    with pytest.raises(ValueError, match=message):
        inspect_spz_v4_bytes(bytes(source))


def test_spz_rejects_legacy_truncation_size_mismatch_trailing_and_cancellation() -> None:
    with pytest.raises(ValueError, match="legacy gzip"):
        inspect_spz_v4_bytes(b"\x1f\x8b" + b"x" * 40)

    source = build_spz()
    with pytest.raises(ValueError, match=r"truncated|range"):
        inspect_spz_v4_bytes(source[:-1])

    mismatch = bytearray(source)
    struct.pack_into("<Q", mismatch, _HEADER.size + 8, 999)
    with pytest.raises(ValueError, match="uncompressed stream size"):
        inspect_spz_v4_bytes(bytes(mismatch))

    with pytest.raises(ValueError, match="trailing"):
        inspect_spz_v4_bytes(source + b"x")

    with pytest.raises(ValueError, match="cancelled"):
        import_spz_bytes(source, provenance_refs=("fixture",), cancelled=lambda: True)


def test_spz_rejects_runtime_expansion_before_toc_or_backend_allocation() -> None:
    source = _HEADER.pack(
        0x5053474E,
        SPZ_FORMAT_VERSION,
        200_000,
        4,
        12,
        0,
        6,
        _HEADER.size,
        b"\x00" * 12,
    )
    with pytest.raises(ValueError, match="runtime allocation"):
        inspect_spz_v4_bytes(source)


def test_spz_rejects_extension_zone_until_semantics_are_negotiated() -> None:
    source = bytearray(build_spz(flags=0x2))
    with pytest.raises(ValueError, match="vendor extensions"):
        inspect_spz_v4_bytes(bytes(source))
