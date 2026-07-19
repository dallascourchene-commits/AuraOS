"""Local-only bounded PLY point-cloud importer."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import math
from pathlib import Path
import struct
from typing import Any

from aura_spatial_coordinate_frames import apply_coordinate_conversion

from .contracts import (
    CoordinateConversion,
    ImportedPrimitive,
    SpatialImportResult,
    SpatialSourceFormat,
    build_import_receipt,
    read_bounded_local_import_source,
)

MAX_PLY_SOURCE_BYTES = 32 * 1024 * 1024
MAX_PLY_VERTICES = 2_000_000
MAX_PLY_PROPERTIES = 32
MAX_PLY_HEADER_BYTES = 65_536
MAX_PLY_LINE_BYTES = 4096
_SCALARS: dict[str, tuple[str, int, type]] = {
    "char": ("b", 1, int),
    "int8": ("b", 1, int),
    "uchar": ("B", 1, int),
    "uint8": ("B", 1, int),
    "short": ("h", 2, int),
    "int16": ("h", 2, int),
    "ushort": ("H", 2, int),
    "uint16": ("H", 2, int),
    "int": ("i", 4, int),
    "int32": ("i", 4, int),
    "uint": ("I", 4, int),
    "uint32": ("I", 4, int),
    "float": ("f", 4, float),
    "float32": ("f", 4, float),
    "double": ("d", 8, float),
    "float64": ("d", 8, float),
}


def _split_header(source: bytes) -> tuple[list[str], bytes]:
    marker = b"end_header\n"
    offset = source.find(marker)
    marker_len = len(marker)
    if offset < 0:
        marker = b"end_header\r\n"
        offset = source.find(marker)
        marker_len = len(marker)
    if offset < 0 or offset + marker_len > MAX_PLY_HEADER_BYTES:
        raise ValueError("PLY header is missing or exceeds its byte ceiling")
    header_bytes = source[: offset + marker_len]
    try:
        lines = header_bytes.decode("ascii", errors="strict").replace("\r\n", "\n").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("PLY header must be ASCII") from exc
    if any(len(line.encode("ascii")) > MAX_PLY_LINE_BYTES for line in lines):
        raise ValueError("PLY header line exceeds byte ceiling")
    return lines, source[offset + marker_len :]


def import_ply_bytes(
    source: bytes,
    *,
    provenance_refs: Sequence[str],
    coordinate_conversion: CoordinateConversion,
) -> SpatialImportResult:
    if not isinstance(source, bytes) or not source or len(source) > MAX_PLY_SOURCE_BYTES:
        raise ValueError("PLY source must be bounded non-empty bytes")
    if not isinstance(coordinate_conversion, CoordinateConversion):
        raise ValueError("PLY import requires an explicit CoordinateConversion")
    lines, payload = _split_header(source)
    if not lines or lines[0] != "ply":
        raise ValueError("PLY magic is invalid")
    fmt: SpatialSourceFormat | None = None
    vertex_count: int | None = None
    properties: list[tuple[str, str]] = []
    active_element: str | None = None
    for line in lines[1:]:
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] in {"comment", "obj_info", "end_header"}:
            continue
        if tokens[0] == "format":
            if len(tokens) != 3 or tokens[2] != "1.0" or fmt is not None:
                raise ValueError("PLY format declaration is invalid")
            fmt = {
                "ascii": SpatialSourceFormat.PLY_ASCII,
                "binary_little_endian": SpatialSourceFormat.PLY_BINARY_LE,
                "binary_big_endian": SpatialSourceFormat.PLY_BINARY_BE,
            }.get(tokens[1])
            if fmt is None:
                raise ValueError("unsupported PLY format")
        elif tokens[0] == "element":
            if len(tokens) != 3:
                raise ValueError("PLY element declaration is invalid")
            active_element = tokens[1]
            try:
                count = int(tokens[2])
            except ValueError as exc:
                raise ValueError("PLY element count is invalid") from exc
            if count < 0:
                raise ValueError("PLY element count must be non-negative")
            if active_element == "vertex":
                if vertex_count is not None or count > MAX_PLY_VERTICES:
                    raise ValueError("PLY vertex element is duplicated or exceeds bounds")
                vertex_count = count
            elif count:
                raise ValueError("S4-A PLY admits point-cloud vertex elements only")
        elif tokens[0] == "property":
            if active_element != "vertex" or len(tokens) != 3 or tokens[1] == "list":
                raise ValueError("S4-A PLY admits scalar vertex properties only")
            if tokens[1] not in _SCALARS or len(properties) >= MAX_PLY_PROPERTIES:
                raise ValueError("PLY property type/count is unsupported")
            if any(name == tokens[2] for _, name in properties):
                raise ValueError("PLY vertex property is duplicated")
            properties.append((tokens[1], tokens[2]))
        else:
            raise ValueError(f"unsupported PLY header directive: {tokens[0]}")
    if fmt is None or vertex_count is None or vertex_count < 1:
        raise ValueError("PLY requires format and non-empty vertex element")
    names = [name for _, name in properties]
    if not all(name in names for name in ("x", "y", "z")):
        raise ValueError("PLY point cloud requires x/y/z properties")
    allowed = {"x", "y", "z", "red", "green", "blue", "alpha", "r", "g", "b", "a"}
    if any(name not in allowed for name in names):
        raise ValueError("PLY contains unsupported vertex properties")

    rows: list[tuple[Any, ...]] = []
    if fmt is SpatialSourceFormat.PLY_ASCII:
        try:
            text = payload.decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("ASCII PLY payload must be ASCII") from exc
        data_lines = [line for line in text.replace("\r\n", "\n").splitlines() if line.strip()]
        if len(data_lines) != vertex_count:
            raise ValueError("ASCII PLY vertex count does not match header")
        for line in data_lines:
            if len(line.encode("ascii")) > MAX_PLY_LINE_BYTES:
                raise ValueError("ASCII PLY line exceeds byte ceiling")
            tokens = line.split()
            if len(tokens) != len(properties):
                raise ValueError("ASCII PLY property count mismatch")
            converted: list[Any] = []
            for token, (type_name, _) in zip(tokens, properties):
                caster = _SCALARS[type_name][2]
                try:
                    value = caster(token)
                except ValueError as exc:
                    raise ValueError("ASCII PLY scalar is invalid") from exc
                converted.append(value)
            rows.append(tuple(converted))
        decoded_bytes = len(payload)
    else:
        endian = "<" if fmt is SpatialSourceFormat.PLY_BINARY_LE else ">"
        row_struct = struct.Struct(endian + "".join(_SCALARS[type_name][0] for type_name, _ in properties))
        expected = row_struct.size * vertex_count
        if len(payload) != expected:
            raise ValueError("binary PLY payload length does not match header")
        rows = [row_struct.unpack_from(payload, index * row_struct.size) for index in range(vertex_count)]
        decoded_bytes = expected

    index = {name: idx for idx, (_, name) in enumerate(properties)}
    positions: list[tuple[float, float, float]] = []
    colors: list[tuple[int, int, int, int]] = []
    color_groups = [
        group
        for group in (("red", "green", "blue", "alpha"), ("r", "g", "b", "a"))
        if all(name in index for name in group[:3])
    ]
    if len(color_groups) > 1:
        raise ValueError("PLY color aliases are ambiguous")
    color_names = color_groups[0] if color_groups else None
    if color_names:
        property_types = {name: type_name for type_name, name in properties}
        present_color_names = [name for name in color_names if name in index]
        if any(property_types[name] not in {"uchar", "uint8"} for name in present_color_names):
            raise ValueError("PLY colors must use unsigned 8-bit properties")
    for row in rows:
        point = tuple(float(row[index[name]]) for name in ("x", "y", "z"))
        if not all(math.isfinite(item) for item in point):
            raise ValueError("PLY coordinates must be finite")
        positions.append(apply_coordinate_conversion(point, coordinate_conversion.matrix))
        if color_names:
            values = [int(row[index[name]]) for name in color_names[:3]]
            alpha = int(row[index[color_names[3]]]) if color_names[3] in index else 255
            if any(value < 0 or value > 255 for value in (*values, alpha)):
                raise ValueError("PLY colors must be 8-bit values")
            colors.append((values[0], values[1], values[2], alpha))
    bounds_min = tuple(min(item[axis] for item in positions) for axis in range(3))
    bounds_max = tuple(max(item[axis] for item in positions) for axis in range(3))
    primitive = ImportedPrimitive(
        primitive_id="ply-primitive:0",
        topology="POINTS",
        vertex_count=len(positions),
        index_count=0,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        attributes=tuple(name.upper() for name in names),
    )
    receipt = build_import_receipt(
        source_format=fmt,
        source_digest=hashlib.sha256(source).hexdigest(),
        source_bytes=len(source),
        decoded_bytes=decoded_bytes,
        asset_type="POINT_CLOUD",
        conversion=coordinate_conversion,
        primitives=(primitive,),
        provenance_refs=provenance_refs,
    )
    return SpatialImportResult(
        receipt=receipt,
        positions=tuple(positions),
        colors_rgba=tuple(colors),
        metadata={"property_names": names},
    )


def import_ply_file(
    path: str | Path,
    *,
    provenance_refs: Sequence[str],
    coordinate_conversion: CoordinateConversion,
    root: str | Path | None = None,
) -> SpatialImportResult:
    source, resolved = read_bounded_local_import_source(
        path,
        maximum_bytes=MAX_PLY_SOURCE_BYTES,
        root=root,
        label="PLY import",
    )
    return import_ply_bytes(
        source,
        provenance_refs=(*provenance_refs, f"local-file:{resolved.name}"),
        coordinate_conversion=coordinate_conversion,
    )
