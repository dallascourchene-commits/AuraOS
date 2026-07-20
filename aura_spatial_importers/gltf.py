"""Bounded glTF 2.0 / GLB mesh importer with no network or executable paths."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping, Sequence
import hashlib
import json
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

MAX_GLTF_SOURCE_BYTES = 16 * 1024 * 1024
MAX_GLTF_DECODED_BYTES = 64 * 1024 * 1024
MAX_GLTF_JSON_DEPTH = 32
MAX_GLTF_JSON_ITEMS = 100_000
MAX_GLTF_BUFFERS = 16
MAX_GLTF_BUFFER_VIEWS = 4096
MAX_GLTF_ACCESSORS = 4096
MAX_GLTF_MESHES = 2048
MAX_GLTF_PRIMITIVES = 4096
MAX_GLTF_VERTICES = 2_000_000
MAX_GLTF_INDICES = 6_000_000
_JSON_CHUNK = 0x4E4F534A
_BIN_CHUNK = 0x004E4942
_COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_TYPE_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
_BLOCKED_KEYS = {
    "script",
    "scripts",
    "shader",
    "shaders",
    "uri_template",
    "javascript",
    "execution_authority",
    "patch_authority",
    "production_mutation",
}


def _object_no_duplicates(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate glTF JSON key: {key}")
        result[key] = value
    return result


def _bounded_json(value: Any, *, depth: int = 0, counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_GLTF_JSON_ITEMS or depth > MAX_GLTF_JSON_DEPTH:
        raise ValueError("glTF JSON exceeds bounded depth/item limits")
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = "".join(ch for ch in str(key).lower() if ch.isalnum() or ch == "_")
            if normalized in _BLOCKED_KEYS:
                raise ValueError(f"glTF executable/authority metadata is prohibited: {key}")
            _bounded_json(item, depth=depth + 1, counter=counter)
    elif isinstance(value, list):
        for item in value:
            _bounded_json(item, depth=depth + 1, counter=counter)
    elif isinstance(value, str) and len(value.encode("utf-8")) > 262_144:
        raise ValueError("glTF string exceeds byte ceiling")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("glTF JSON contains NaN or infinity")


def _parse_container(source: bytes) -> tuple[SpatialSourceFormat, dict[str, Any], bytes | None]:
    if source.startswith(b"glTF"):
        if len(source) < 20:
            raise ValueError("GLB header is truncated")
        magic, version, declared = struct.unpack_from("<4sII", source, 0)
        if magic != b"glTF" or version != 2 or declared != len(source):
            raise ValueError("GLB header/version/length is invalid")
        offset = 12
        chunks: list[tuple[int, bytes]] = []
        while offset < len(source):
            if offset + 8 > len(source):
                raise ValueError("GLB chunk header is truncated")
            length, kind = struct.unpack_from("<II", source, offset)
            offset += 8
            if length % 4 or offset + length > len(source):
                raise ValueError("GLB chunk length is invalid")
            chunks.append((kind, source[offset : offset + length]))
            offset += length
        if (
            not chunks
            or chunks[0][0] != _JSON_CHUNK
            or sum(1 for k, _ in chunks if k == _JSON_CHUNK) != 1
            or sum(1 for k, _ in chunks if k == _BIN_CHUNK) > 1
        ):
            raise ValueError("GLB requires one leading JSON chunk and at most one BIN chunk")
        json_bytes = chunks[0][1].rstrip(b" \t\r\n\x00")
        bin_chunk = next((data for kind, data in chunks if kind == _BIN_CHUNK), None)
        fmt = SpatialSourceFormat.GLB
    else:
        json_bytes = source
        bin_chunk = None
        fmt = SpatialSourceFormat.GLTF
    try:
        document = json.loads(
            json_bytes.decode("utf-8", errors="strict"),
            object_pairs_hook=_object_no_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON constant {value}")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid glTF JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("glTF document must be an object")
    _bounded_json(document)
    return fmt, document, bin_chunk


def _decode_data_uri(uri: str) -> bytes:
    prefix = "data:application/octet-stream;base64,"
    if not uri.startswith(prefix) or any(token in uri[: len(prefix)].lower() for token in (";charset", "%")):
        raise ValueError("glTF buffers must be GLB-local or canonical base64 octet-stream data URIs")
    try:
        return base64.b64decode(uri[len(prefix) :], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid glTF base64 buffer") from exc


def _load_buffers(document: Mapping[str, Any], bin_chunk: bytes | None) -> list[bytes]:
    entries = document.get("buffers", [])
    if not isinstance(entries, list) or not entries or len(entries) > MAX_GLTF_BUFFERS:
        raise ValueError("glTF buffers must be a bounded non-empty array")
    result: list[bytes] = []
    decoded = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping) or set(entry) - {"byteLength", "uri", "name", "extensions", "extras"}:
            raise ValueError("glTF buffer keys are invalid")
        if entry.get("extensions"):
            raise ValueError("glTF buffer extensions are not admitted in S4-A")
        length = entry.get("byteLength")
        if isinstance(length, bool) or not isinstance(length, int) or length < 0:
            raise ValueError("glTF buffer byteLength is invalid")
        if "uri" in entry:
            uri = entry["uri"]
            if not isinstance(uri, str):
                raise ValueError("glTF buffer URI must be a string")
            data = _decode_data_uri(uri)
        elif index == 0 and bin_chunk is not None:
            data = bin_chunk
        else:
            raise ValueError("glTF buffer requires local embedded bytes")
        if len(data) < length or len(data) - length > 3:
            raise ValueError("glTF buffer length does not match declared byteLength")
        data = data[:length]
        decoded += len(data)
        if decoded > MAX_GLTF_DECODED_BYTES:
            raise ValueError("glTF decoded buffer ceiling exceeded")
        result.append(data)
    return result


def _array(document: Mapping[str, Any], key: str, maximum: int) -> list[Any]:
    value = document.get(key, [])
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f"glTF {key} must be a bounded array")
    return value


def _validate_non_overlapping_buffer_views(document: Mapping[str, Any], buffers: Sequence[bytes]) -> None:
    """Reject aliased view ranges before accessor expansion."""

    views = _array(document, "bufferViews", MAX_GLTF_BUFFER_VIEWS)
    ranges: dict[int, list[tuple[int, int]]] = {}
    for view in views:
        if not isinstance(view, Mapping):
            raise ValueError("glTF bufferView must be an object")
        buffer_index = view.get("buffer")
        offset = view.get("byteOffset", 0)
        length = view.get("byteLength")
        if (
            isinstance(buffer_index, bool)
            or not isinstance(buffer_index, int)
            or not 0 <= buffer_index < len(buffers)
            or isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
            or isinstance(length, bool)
            or not isinstance(length, int)
            or length < 0
        ):
            raise ValueError("glTF bufferView range is invalid")
        end = offset + length
        if end < offset or end > len(buffers[buffer_index]):
            raise ValueError("glTF bufferView range exceeds its buffer")
        for existing_start, existing_end in ranges.setdefault(buffer_index, []):
            if offset < existing_end and existing_start < end:
                raise ValueError("glTF bufferViews must not overlap or alias")
        ranges[buffer_index].append((offset, end))


def _read_accessor(
    document: Mapping[str, Any],
    buffers: Sequence[bytes],
    accessor_index: int,
    *,
    expected_type: str,
    allowed_components: set[int],
    maximum_count: int,
    allow_normalized: bool = False,
) -> list[tuple[Any, ...]]:
    accessors = _array(document, "accessors", MAX_GLTF_ACCESSORS)
    views = _array(document, "bufferViews", MAX_GLTF_BUFFER_VIEWS)
    if (
        isinstance(accessor_index, bool)
        or not isinstance(accessor_index, int)
        or accessor_index < 0
        or accessor_index >= len(accessors)
    ):
        raise ValueError("glTF accessor index is invalid")
    accessor = accessors[accessor_index]
    if not isinstance(accessor, Mapping) or set(accessor) - {
        "bufferView",
        "byteOffset",
        "componentType",
        "count",
        "type",
        "normalized",
        "min",
        "max",
        "name",
        "extensions",
        "extras",
    }:
        raise ValueError("glTF accessor keys are invalid")
    normalized = accessor.get("normalized", False)
    if "sparse" in accessor or type(normalized) is not bool or (normalized and not allow_normalized):
        raise ValueError("sparse/normalized glTF accessor is not admitted")
    if accessor.get("extensions"):
        raise ValueError("glTF accessor extensions are not admitted in S4-A")
    if accessor.get("type") != expected_type or accessor.get("componentType") not in allowed_components:
        raise ValueError("glTF accessor type/component is unsupported")
    count = accessor.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > maximum_count:
        raise ValueError("glTF accessor count exceeds bounds")
    view_index = accessor.get("bufferView")
    if isinstance(view_index, bool) or not isinstance(view_index, int) or view_index < 0 or view_index >= len(views):
        raise ValueError("glTF accessor bufferView is invalid")
    view = views[view_index]
    if not isinstance(view, Mapping) or set(view) - {
        "buffer",
        "byteOffset",
        "byteLength",
        "byteStride",
        "target",
        "name",
        "extensions",
        "extras",
    }:
        raise ValueError("glTF bufferView keys are invalid")
    if view.get("extensions"):
        raise ValueError("glTF bufferView extensions are not admitted in S4-A")
    buffer_index = view.get("buffer")
    if (
        isinstance(buffer_index, bool)
        or not isinstance(buffer_index, int)
        or buffer_index < 0
        or buffer_index >= len(buffers)
    ):
        raise ValueError("glTF bufferView buffer index is invalid")
    component_type = int(accessor["componentType"])
    fmt, component_size = _COMPONENT[component_type]
    components = _TYPE_COMPONENTS[expected_type]
    element_size = component_size * components
    stride = view.get("byteStride", element_size)
    if (
        isinstance(stride, bool)
        or not isinstance(stride, int)
        or stride < element_size
        or stride > 256
        or stride % component_size
    ):
        raise ValueError("glTF byteStride is invalid")
    view_offset = view.get("byteOffset", 0)
    accessor_offset = accessor.get("byteOffset", 0)
    view_length = view.get("byteLength")
    for value, label in (
        (view_offset, "bufferView byteOffset"),
        (accessor_offset, "accessor byteOffset"),
        (view_length, "bufferView byteLength"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"glTF {label} is invalid")
    start = view_offset + accessor_offset
    required = 0 if count == 0 else (count - 1) * stride + element_size
    if accessor_offset + required > view_length or start + required > len(buffers[buffer_index]):
        raise ValueError("glTF accessor range exceeds its bufferView")
    unpack = struct.Struct("<" + fmt * components)
    data = buffers[buffer_index]
    values = [unpack.unpack_from(data, start + index * stride) for index in range(count)]
    if not normalized:
        return values
    if component_type == 5120:
        return [tuple(max(-1.0, item / 127.0) for item in value) for value in values]
    if component_type == 5121:
        return [tuple(item / 255.0 for item in value) for value in values]
    if component_type == 5122:
        return [tuple(max(-1.0, item / 32767.0) for item in value) for value in values]
    if component_type == 5123:
        return [tuple(item / 65535.0 for item in value) for value in values]
    raise ValueError("normalized glTF accessor component type is unsupported")


def import_gltf_bytes(source: bytes, *, provenance_refs: Sequence[str]) -> SpatialImportResult:
    if not isinstance(source, bytes) or not source or len(source) > MAX_GLTF_SOURCE_BYTES:
        raise ValueError("glTF source must be bounded non-empty bytes")
    fmt, document, bin_chunk = _parse_container(source)
    asset = document.get("asset")
    if not isinstance(asset, Mapping) or asset.get("version") != "2.0":
        raise ValueError("glTF asset.version must be 2.0")
    allowed_document_keys = {
        "asset",
        "buffers",
        "bufferViews",
        "accessors",
        "meshes",
        "materials",
        "extensionsUsed",
        "extensionsRequired",
        "extras",
    }
    if set(document) - allowed_document_keys:
        raise ValueError("glTF contains unsupported top-level scene or extension surfaces")
    if document.get("extensionsRequired") or document.get("extensionsUsed"):
        raise ValueError("glTF extensions are not admitted in S4-A")
    for prohibited in ("animations", "skins", "cameras", "images", "nodes", "scenes"):
        if document.get(prohibited):
            raise ValueError(f"glTF {prohibited} are outside the S4-A mesh boundary")
    buffers = _load_buffers(document, bin_chunk)
    _validate_non_overlapping_buffer_views(document, buffers)
    meshes = _array(document, "meshes", MAX_GLTF_MESHES)
    if not meshes:
        raise ValueError("glTF contains no meshes")
    conversion = CoordinateConversion("RIGHT_HANDED", "Y_UP", 1.0)
    positions: list[tuple[float, float, float]] = []
    indices: list[int] = []
    primitives: list[ImportedPrimitive] = []
    primitive_count = 0
    for mesh_index, mesh in enumerate(meshes):
        if not isinstance(mesh, Mapping) or not isinstance(mesh.get("primitives"), list):
            raise ValueError("glTF mesh primitives are invalid")
        for primitive_index, primitive in enumerate(mesh["primitives"]):
            primitive_count += 1
            if primitive_count > MAX_GLTF_PRIMITIVES or not isinstance(primitive, Mapping):
                raise ValueError("glTF primitive ceiling exceeded")
            if set(primitive) - {"attributes", "indices", "material", "mode", "targets", "extensions", "extras"}:
                raise ValueError("glTF primitive keys are invalid")
            if primitive.get("extensions"):
                raise ValueError("glTF primitive extensions are not admitted in S4-A")
            if primitive.get("mode", 4) != 4 or primitive.get("targets"):
                raise ValueError("S4-A admits only static TRIANGLES primitives")
            attributes = primitive.get("attributes")
            if not isinstance(attributes, Mapping) or "POSITION" not in attributes:
                raise ValueError("glTF primitive requires POSITION")
            if set(attributes) != {"POSITION"}:
                raise ValueError("S4-A glTF primitives admit only decoded POSITION attributes")
            raw_positions = _read_accessor(
                document,
                buffers,
                attributes["POSITION"],
                expected_type="VEC3",
                allowed_components={5126},
                maximum_count=MAX_GLTF_VERTICES,
            )
            if not raw_positions or len(positions) + len(raw_positions) > MAX_GLTF_VERTICES:
                raise ValueError("glTF vertex ceiling exceeded")
            converted = [apply_coordinate_conversion(item, conversion.matrix) for item in raw_positions]
            base = len(positions)
            positions.extend(converted)
            if "indices" in primitive:
                raw_indices = _read_accessor(
                    document,
                    buffers,
                    primitive["indices"],
                    expected_type="SCALAR",
                    allowed_components={5121, 5123, 5125},
                    maximum_count=MAX_GLTF_INDICES,
                )
                primitive_indices = [int(item[0]) for item in raw_indices]
                if (
                    any(item < 0 or item >= len(raw_positions) for item in primitive_indices)
                    or len(indices) + len(primitive_indices) > MAX_GLTF_INDICES
                ):
                    raise ValueError("glTF indices are out of range or exceed bounds")
            else:
                primitive_indices = list(range(len(raw_positions)))
            if len(primitive_indices) % 3:
                raise ValueError("TRIANGLES index count must be divisible by three")
            indices.extend(base + item for item in primitive_indices)
            bounds_min = tuple(min(item[axis] for item in converted) for axis in range(3))
            bounds_max = tuple(max(item[axis] for item in converted) for axis in range(3))
            material = primitive.get("material")
            material_ref = None
            if material is not None:
                materials = _array(document, "materials", 2048)
                if (
                    isinstance(material, bool)
                    or not isinstance(material, int)
                    or material < 0
                    or material >= len(materials)
                ):
                    raise ValueError("glTF material index is invalid")
                material_ref = f"material:{material}"
            primitives.append(
                ImportedPrimitive(
                    primitive_id=f"gltf-primitive:{mesh_index}:{primitive_index}",
                    topology="TRIANGLES",
                    vertex_count=len(converted),
                    index_count=len(primitive_indices),
                    bounds_min=bounds_min,
                    bounds_max=bounds_max,
                    attributes=tuple(attributes),
                    material_ref=material_ref,
                )
            )
    source_digest = hashlib.sha256(source).hexdigest()
    receipt = build_import_receipt(
        source_format=fmt,
        source_digest=source_digest,
        source_bytes=len(source),
        decoded_bytes=sum(len(item) for item in buffers),
        asset_type="MESH",
        conversion=conversion,
        primitives=tuple(primitives),
        provenance_refs=provenance_refs,
    )
    return SpatialImportResult(
        receipt=receipt,
        positions=tuple(positions),
        indices=tuple(indices),
        metadata={"mesh_count": len(meshes), "primitive_count": primitive_count},
    )


def import_gltf_file(
    path: str | Path, *, provenance_refs: Sequence[str], root: str | Path | None = None
) -> SpatialImportResult:
    source, resolved = read_bounded_local_import_source(
        path,
        maximum_bytes=MAX_GLTF_SOURCE_BYTES,
        root=root,
        label="glTF import",
    )
    return import_gltf_bytes(
        source,
        provenance_refs=(*provenance_refs, f"local-file:{resolved.name}"),
    )
