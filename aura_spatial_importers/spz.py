"""Bounded SPZ v4 Gaussian importer.

The decoder accepts the current plaintext-header/Zstandard SPZ v4 container
only. It validates every declared size before decompression and keeps the
optional compression backend behind this module boundary. Legacy gzip SPZ
versions are rejected rather than silently expanding an unbounded stream.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import struct

from aura_spatial_coordinate_frames import apply_coordinate_conversion

from .contracts import (
    CoordinateConversion,
    GaussianSplatData,
    ImportedPrimitive,
    SpatialImportResult,
    SpatialSourceFormat,
    build_import_receipt,
    read_bounded_local_import_source,
)

SPZ_IMPLEMENTATION_VERSION = "AURA_SPATIAL_SPZ_V1"
SPZ_UPSTREAM_VERSION = "3.0.0"
SPZ_FORMAT_VERSION = 4
SPZ_ZSTANDARD_VERSION = "0.25.0"
MAX_SPZ_SOURCE_BYTES = 64 * 1024 * 1024
MAX_SPZ_DECODED_BYTES = 192 * 1024 * 1024
MAX_SPZ_POINTS = 2_000_000
MAX_SPZ_DECOMPRESSION_RATIO = 4096
MAX_SPZ_RUNTIME_ALLOCATION_BYTES = 256 * 1024 * 1024
MAX_SPZ_FRACTIONAL_BITS = 23
_HEADER = struct.Struct("<IIIBBBBI12s")
_TOC_ENTRY = struct.Struct("<QQ")
_MAGIC = 0x5053474E
_FLAG_ANTIALIASED = 0x1
_FLAG_EXTENSIONS = 0x2
_KNOWN_FLAGS = _FLAG_ANTIALIASED | _FLAG_EXTENSIONS
_COLOR_SCALE = 0.15
_SH_C0 = 0.28209479177387814
_SQRT_HALF = math.sqrt(0.5)


@dataclass(frozen=True)
class SpzHeader:
    point_count: int
    sh_degree: int
    fractional_bits: int
    flags: int
    stream_count: int
    toc_byte_offset: int

    @property
    def antialiased(self) -> bool:
        return bool(self.flags & _FLAG_ANTIALIASED)


def _sh_dimension(degree: int) -> int:
    return (0, 3, 8, 15, 24)[degree]


def _expected_stream_sizes(header: SpzHeader) -> tuple[int, ...]:
    count = header.point_count
    sizes = [count * 9, count, count * 3, count * 3, count * 4]
    sh_bytes = count * _sh_dimension(header.sh_degree) * 3
    if sh_bytes:
        sizes.append(sh_bytes)
    return tuple(sizes)


def _estimated_runtime_allocation_bytes(header: SpzHeader) -> int:
    """Conservatively bound Python object expansion before decompression."""

    coefficient_count = (header.sh_degree + 1) ** 2 * 3
    decoded_bytes = sum(_expected_stream_sizes(header))
    # Positions, rotations, scales, opacity, fallback RGBA, tuple/list overhead,
    # and each Python float are deliberately overestimated.
    per_splat = 384 + coefficient_count * 40
    return decoded_bytes + header.point_count * per_splat


def inspect_spz_v4_bytes(source: bytes) -> tuple[SpzHeader, tuple[tuple[int, int, int], ...]]:
    """Validate the SPZ v4 envelope without invoking a decompressor."""

    if not isinstance(source, bytes) or not source or len(source) > MAX_SPZ_SOURCE_BYTES:
        raise ValueError("SPZ source must be bounded non-empty bytes")
    if source[:2] == b"\x1f\x8b":
        raise ValueError("legacy gzip SPZ versions 1-3 are not admitted")
    if len(source) < _HEADER.size:
        raise ValueError("SPZ v4 header is truncated")
    magic, version, point_count, sh_degree, fractional_bits, flags, stream_count, toc_offset, reserved = (
        _HEADER.unpack_from(source)
    )
    if magic != _MAGIC:
        raise ValueError("SPZ magic is invalid")
    if version != SPZ_FORMAT_VERSION:
        raise ValueError(f"unsupported SPZ version: {version}")
    if not 1 <= point_count <= MAX_SPZ_POINTS:
        raise ValueError("SPZ point count exceeds bounds")
    if not 0 <= sh_degree <= 4:
        raise ValueError("SPZ spherical-harmonic degree is invalid")
    if not 0 <= fractional_bits <= MAX_SPZ_FRACTIONAL_BITS:
        raise ValueError("SPZ fractionalBits exceeds the admitted precision bound")
    if flags & ~_KNOWN_FLAGS:
        raise ValueError("SPZ contains unknown header flags")
    if reserved != b"\x00" * 12:
        raise ValueError("SPZ reserved header bytes must be zero")
    if flags & _FLAG_EXTENSIONS:
        raise ValueError("SPZ vendor extensions require a separately negotiated decoder")
    if toc_offset != _HEADER.size:
        raise ValueError("SPZ v4 without extensions must place the TOC at byte 32")

    header = SpzHeader(point_count, sh_degree, fractional_bits, flags, stream_count, toc_offset)
    expected_sizes = _expected_stream_sizes(header)
    if _estimated_runtime_allocation_bytes(header) > MAX_SPZ_RUNTIME_ALLOCATION_BYTES:
        raise ValueError("SPZ runtime allocation ceiling exceeded before decompression")
    if stream_count != len(expected_sizes):
        raise ValueError("SPZ attribute stream count does not match the declared splat layout")
    toc_end = toc_offset + stream_count * _TOC_ENTRY.size
    if toc_end > len(source):
        raise ValueError("SPZ table of contents is truncated")

    entries: list[tuple[int, int, int]] = []
    compressed_offset = toc_end
    total_decoded = 0
    for index, expected in enumerate(expected_sizes):
        compressed_size, uncompressed_size = _TOC_ENTRY.unpack_from(source, toc_offset + index * _TOC_ENTRY.size)
        if compressed_size < 1 or compressed_size > MAX_SPZ_SOURCE_BYTES:
            raise ValueError("SPZ compressed stream size is invalid")
        if uncompressed_size != expected:
            raise ValueError("SPZ uncompressed stream size does not match its declared layout")
        if uncompressed_size > compressed_size * MAX_SPZ_DECOMPRESSION_RATIO:
            raise ValueError("SPZ stream exceeds the decompression-ratio budget")
        end = compressed_offset + compressed_size
        if end < compressed_offset or end > len(source):
            raise ValueError("SPZ compressed stream range exceeds the source")
        total_decoded += uncompressed_size
        if total_decoded > MAX_SPZ_DECODED_BYTES:
            raise ValueError("SPZ decoded byte ceiling exceeded")
        entries.append((compressed_offset, int(compressed_size), int(uncompressed_size)))
        compressed_offset = end
    if compressed_offset != len(source):
        raise ValueError("SPZ contains trailing or overlapping compressed data")
    return header, tuple(entries)


def _default_zstd_decompressor(payload: bytes, expected_size: int) -> bytes:
    try:
        import zstandard  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValueError(f"SPZ decoding requires the isolated zstandard=={SPZ_ZSTANDARD_VERSION} backend") from exc
    version = getattr(zstandard, "__version__", "")
    if version != SPZ_ZSTANDARD_VERSION:
        raise ValueError(
            f"SPZ zstandard backend version mismatch: expected {SPZ_ZSTANDARD_VERSION}, got {version or 'unknown'}"
        )
    try:
        decoded = zstandard.ZstdDecompressor().decompress(payload, max_output_size=expected_size)
    except zstandard.ZstdError as exc:
        raise ValueError("SPZ Zstandard stream is malformed or truncated") from exc
    if len(decoded) != expected_size:
        raise ValueError("SPZ decompressor did not produce the exact admitted byte count")
    return decoded


def _cancelled(cancelled: Callable[[], bool] | None) -> None:
    if cancelled is not None and cancelled():
        raise ValueError("SPZ decode cancelled")


def _decode_signed24(data: bytes, offset: int) -> int:
    value = data[offset] | data[offset + 1] << 8 | data[offset + 2] << 16
    return value - (1 << 24) if value & (1 << 23) else value


def _decode_smallest_three(data: bytes, offset: int) -> tuple[float, float, float, float]:
    packed = int.from_bytes(data[offset : offset + 4], "little", signed=False)
    largest = packed >> 30
    mask = (1 << 9) - 1
    result = [0.0, 0.0, 0.0, 0.0]
    squared = 0.0
    for index in range(3, -1, -1):
        if index == largest:
            continue
        magnitude = packed & mask
        negative = (packed >> 9) & 1
        packed >>= 10
        value = _SQRT_HALF * magnitude / mask
        if negative:
            value = -value
        result[index] = value
        squared += value * value
    if squared > 1.000001:
        raise ValueError("SPZ quaternion encoding is invalid")
    result[largest] = math.sqrt(max(0.0, 1.0 - squared))
    return tuple(result)  # type: ignore[return-value]


def import_spz_bytes(
    source: bytes,
    *,
    provenance_refs: Sequence[str],
    cancelled: Callable[[], bool] | None = None,
    decompressor: Callable[[bytes, int], bytes] | None = None,
) -> SpatialImportResult:
    """Decode admitted SPZ v4 bytes into a projection-only Gaussian payload."""

    header, entries = inspect_spz_v4_bytes(source)
    decode = decompressor or _default_zstd_decompressor
    streams: list[bytes] = []
    for offset, compressed_size, expected_size in entries:
        _cancelled(cancelled)
        decoded = decode(source[offset : offset + compressed_size], expected_size)
        if not isinstance(decoded, bytes) or len(decoded) != expected_size:
            raise ValueError("SPZ decoder backend violated its exact-size contract")
        streams.append(decoded)
    _cancelled(cancelled)

    positions_raw, alphas_raw, colors_raw, scales_raw, rotations_raw, *sh_stream = streams
    sh_raw = sh_stream[0] if sh_stream else b""
    conversion = CoordinateConversion("RIGHT_HANDED", "Y_UP", 1.0)
    scale_factor = 1.0 / (1 << header.fractional_bits)
    higher_count = _sh_dimension(header.sh_degree) * 3
    positions: list[tuple[float, float, float]] = []
    rotations: list[tuple[float, float, float, float]] = []
    scales: list[tuple[float, float, float]] = []
    opacities: list[float] = []
    coefficients: list[tuple[float, ...]] = []
    fallback_colors: list[tuple[int, int, int, int]] = []

    for point in range(header.point_count):
        if point % 4096 == 0:
            _cancelled(cancelled)
        position_offset = point * 9
        raw_position = tuple(
            _decode_signed24(positions_raw, position_offset + axis * 3) * scale_factor for axis in range(3)
        )
        positions.append(apply_coordinate_conversion(raw_position, conversion.matrix))
        rotations.append(_decode_smallest_three(rotations_raw, point * 4))
        scale_offset = point * 3
        linear_scale = tuple(math.exp(scales_raw[scale_offset + axis] / 16.0 - 10.0) for axis in range(3))
        if not all(math.isfinite(item) for item in linear_scale):
            raise ValueError("SPZ scale decoding produced a non-finite value")
        scales.append(linear_scale)
        alpha = alphas_raw[point] / 255.0
        opacities.append(alpha)
        color_offset = point * 3
        rgb_bytes = colors_raw[color_offset : color_offset + 3]
        dc = tuple((component / 255.0 - 0.5) / _COLOR_SCALE for component in rgb_bytes)
        higher_offset = point * higher_count
        higher = tuple(
            (component - 128.0) / 128.0 for component in sh_raw[higher_offset : higher_offset + higher_count]
        )
        coefficients.append((*dc, *higher))
        fallback_rgb = tuple(round(min(1.0, max(0.0, 0.5 + _SH_C0 * component)) * 255.0) for component in dc)
        fallback_colors.append((*fallback_rgb, alphas_raw[point]))

    bounds_min = tuple(min(item[axis] for item in positions) for axis in range(3))
    bounds_max = tuple(max(item[axis] for item in positions) for axis in range(3))
    primitive = ImportedPrimitive(
        primitive_id="spz-gaussians:0",
        topology="POINTS",
        vertex_count=header.point_count,
        index_count=0,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        attributes=("POSITION", "ROTATION", "SCALE", "OPACITY", "SH"),
    )
    receipt = build_import_receipt(
        source_format=SpatialSourceFormat.SPZ_V4,
        source_digest=hashlib.sha256(source).hexdigest(),
        source_bytes=len(source),
        decoded_bytes=sum(len(item) for item in streams),
        asset_type="GAUSSIAN_SPLATS",
        conversion=conversion,
        primitives=(primitive,),
        provenance_refs=provenance_refs,
        warnings=(
            "SPZ RUB coordinates retain their right-handed Y-up +Z-back basis in Aura projection space",
            "SPZ Gaussian center bounds do not include covariance extent",
        ),
    )
    return SpatialImportResult(
        receipt=receipt,
        positions=tuple(positions),
        colors_rgba=tuple(fallback_colors),
        gaussian_splats=GaussianSplatData(
            rotations_xyzw=tuple(rotations),
            scales_xyz=tuple(scales),
            opacities=tuple(opacities),
            sh_degree=header.sh_degree,
            sh_coefficients=tuple(coefficients),
        ),
        metadata={
            "format_version": SPZ_FORMAT_VERSION,
            "upstream_library_version": SPZ_UPSTREAM_VERSION,
            "zstandard_version": SPZ_ZSTANDARD_VERSION,
            "source_coordinate_system": "RUB",
            "source_forward_semantics": "+Z_BACK",
            "estimated_runtime_allocation_bytes": _estimated_runtime_allocation_bytes(header),
            "antialiased": header.antialiased,
            "stream_count": header.stream_count,
            "fallback": "POINT_CLOUD_RGBA8",
            "training_path": False,
        },
    )


def import_spz_file(
    path: str | Path,
    *,
    provenance_refs: Sequence[str],
    root: str | Path | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> SpatialImportResult:
    source, resolved = read_bounded_local_import_source(
        path,
        maximum_bytes=MAX_SPZ_SOURCE_BYTES,
        root=root,
        label="SPZ import",
    )
    return import_spz_bytes(
        source,
        provenance_refs=(*provenance_refs, f"local-file:{resolved.name}"),
        cancelled=cancelled,
    )
