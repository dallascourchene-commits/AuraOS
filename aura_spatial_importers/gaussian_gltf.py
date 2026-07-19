"""Bounded adapter for the KHR_gaussian_splatting Release Candidate.

The Khronos extension currently has no numeric wire-version field. Aura therefore
negotiates one exact, named compatibility profile and rejects any additional
mandatory extension semantics. The decoded result remains a derived projection
asset with a deterministic point-cloud fallback.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
from pathlib import Path
from typing import Any

from aura_spatial_coordinate_frames import apply_coordinate_conversion

from .contracts import (
    CoordinateConversion,
    GaussianSplatData,
    ImportedPrimitive,
    SpatialImportResult,
    build_import_receipt,
    read_bounded_local_import_source,
)
from .gltf import (
    MAX_GLTF_ACCESSORS,
    MAX_GLTF_DECODED_BYTES,
    MAX_GLTF_MESHES,
    MAX_GLTF_PRIMITIVES,
    MAX_GLTF_SOURCE_BYTES,
    MAX_GLTF_VERTICES,
    _array,
    _load_buffers,
    _parse_container,
    _read_accessor,
    _validate_non_overlapping_buffer_views,
)

KHR_GAUSSIAN_SPLATTING = "KHR_gaussian_splatting"
KHR_GAUSSIAN_PROFILE = "KHR_gaussian_splatting:release-candidate:2026-07-19"
MAX_GAUSSIAN_GLTF_SPLATS = 2_000_000
MAX_GAUSSIAN_GLTF_RUNTIME_ALLOCATION_BYTES = 256 * 1024 * 1024
_C0 = 0.28209479177387814
_REQUIRED = {
    "POSITION": ("VEC3", {5126}),
    f"{KHR_GAUSSIAN_SPLATTING}:ROTATION": ("VEC4", {5120, 5122, 5126}),
    f"{KHR_GAUSSIAN_SPLATTING}:SCALE": ("VEC3", {5121, 5123, 5126}),
    f"{KHR_GAUSSIAN_SPLATTING}:OPACITY": ("SCALAR", {5121, 5123, 5126}),
    f"{KHR_GAUSSIAN_SPLATTING}:SH_DEGREE_0_COEF_0": ("VEC3", {5126}),
}


def _accessor(document: Mapping[str, Any], index: Any) -> Mapping[str, Any]:
    accessors = _array(document, "accessors", MAX_GLTF_ACCESSORS)
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(accessors):
        raise ValueError("Gaussian glTF accessor index is invalid")
    accessor = accessors[index]
    if not isinstance(accessor, Mapping):
        raise ValueError("Gaussian glTF accessor must be an object")
    return accessor


def _read_attribute(
    document: Mapping[str, Any],
    buffers: Sequence[bytes],
    attributes: Mapping[str, Any],
    semantic: str,
    expected_type: str,
    components: set[int],
) -> list[tuple[Any, ...]]:
    if semantic not in attributes:
        raise ValueError(f"Gaussian glTF requires {semantic}")
    accessor = _accessor(document, attributes[semantic])
    normalized = accessor.get("normalized", False)
    component_type = accessor.get("componentType")
    if component_type == 5126 and normalized:
        raise ValueError(f"Gaussian glTF float attribute {semantic} cannot be normalized")
    if semantic.endswith(":ROTATION") and component_type in {5120, 5122} and normalized is not True:
        raise ValueError("Gaussian integer rotations must be normalized")
    if semantic.endswith(":OPACITY") and component_type in {5121, 5123} and normalized is not True:
        raise ValueError("Gaussian integer opacities must be normalized")
    return _read_accessor(
        document,
        buffers,
        attributes[semantic],
        expected_type=expected_type,
        allowed_components=components,
        maximum_count=MAX_GAUSSIAN_GLTF_SPLATS,
        allow_normalized=True,
    )


def _sh_semantics(attributes: Mapping[str, Any]) -> tuple[int, tuple[str, ...]]:
    by_degree: dict[int, list[str]] = {0: [], 1: [], 2: [], 3: []}
    prefix = f"{KHR_GAUSSIAN_SPLATTING}:SH_DEGREE_"
    for semantic in attributes:
        if not semantic.startswith(prefix):
            continue
        tail = semantic[len(prefix) :]
        try:
            degree_text, coefficient_text = tail.split("_COEF_", 1)
            degree = int(degree_text)
            coefficient = int(coefficient_text)
        except (ValueError, TypeError) as exc:
            raise ValueError("Gaussian glTF SH attribute semantic is malformed") from exc
        if degree not in by_degree or coefficient < 0:
            raise ValueError("Gaussian glTF SH degree is unsupported")
        by_degree[degree].append(semantic)
    if by_degree[0] != [f"{prefix}0_COEF_0"]:
        raise ValueError("Gaussian glTF requires exactly one degree-zero SH coefficient")
    highest = max(degree for degree, values in by_degree.items() if values)
    ordered: list[str] = []
    for degree in range(highest + 1):
        expected = 2 * degree + 1
        values = sorted(by_degree[degree], key=lambda item: int(item.rsplit("_", 1)[1]))
        expected_names = [f"{prefix}{degree}_COEF_{index}" for index in range(expected)]
        if values != expected_names:
            raise ValueError("Gaussian glTF spherical-harmonic degrees must be complete and contiguous")
        ordered.extend(values)
    return highest, tuple(ordered)


def _fallback_colors(
    document: Mapping[str, Any],
    buffers: Sequence[bytes],
    attributes: Mapping[str, Any],
    degree_zero: Sequence[tuple[Any, ...]],
    opacities: Sequence[float],
) -> tuple[tuple[tuple[int, int, int, int], ...], str]:
    if "COLOR_0" in attributes:
        accessor = _accessor(document, attributes["COLOR_0"])
        accessor_type = accessor.get("type")
        component_type = accessor.get("componentType")
        if accessor_type not in {"VEC3", "VEC4"} or component_type not in {5121, 5123, 5126}:
            raise ValueError("Gaussian glTF COLOR_0 fallback type is unsupported")
        if component_type in {5121, 5123} and accessor.get("normalized") is not True:
            raise ValueError("Gaussian glTF integer COLOR_0 fallback must be normalized")
        values = _read_accessor(
            document,
            buffers,
            attributes["COLOR_0"],
            expected_type=accessor_type,
            allowed_components={5121, 5123, 5126},
            maximum_count=MAX_GAUSSIAN_GLTF_SPLATS,
            allow_normalized=True,
        )
        if len(values) != len(opacities):
            raise ValueError("Gaussian glTF COLOR_0 count does not match splat count")
        colors = []
        for index, value in enumerate(values):
            channels = [float(component) for component in value]
            if not all(math.isfinite(component) and 0.0 <= component <= 1.0 for component in channels):
                raise ValueError("Gaussian glTF COLOR_0 values must be finite and normalized")
            alpha = channels[3] if len(channels) == 4 else opacities[index]
            colors.append(tuple(round(component * 255) for component in (*channels[:3], alpha)))
        return tuple(colors), "DECLARED_COLOR_0"

    colors = []
    for coefficient, opacity in zip(degree_zero, opacities):
        rgb = [min(1.0, max(0.0, 0.5 + _C0 * float(component))) for component in coefficient]
        colors.append(tuple(round(component * 255) for component in (*rgb, opacity)))
    return tuple(colors), "BOUNDED_SH0_PLACEHOLDER"


def import_gaussian_gltf_bytes(
    source: bytes,
    *,
    provenance_refs: Sequence[str],
    extension_profile: str = KHR_GAUSSIAN_PROFILE,
) -> SpatialImportResult:
    if extension_profile != KHR_GAUSSIAN_PROFILE:
        raise ValueError("unsupported Gaussian glTF compatibility profile")
    if not isinstance(source, bytes) or not source or len(source) > MAX_GLTF_SOURCE_BYTES:
        raise ValueError("Gaussian glTF source must be bounded non-empty bytes")
    source_format, document, bin_chunk = _parse_container(source)
    asset = document.get("asset")
    if not isinstance(asset, Mapping) or asset.get("version") != "2.0":
        raise ValueError("Gaussian glTF asset.version must be 2.0")
    allowed_keys = {
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
    if set(document) - allowed_keys:
        raise ValueError("Gaussian glTF contains unsupported scene surfaces")
    used = document.get("extensionsUsed", [])
    required = document.get("extensionsRequired", [])
    if not isinstance(used, list) or not isinstance(required, list):
        raise ValueError("Gaussian glTF extension declarations must be arrays")
    if KHR_GAUSSIAN_SPLATTING not in used:
        raise ValueError("Gaussian glTF must declare KHR_gaussian_splatting in extensionsUsed")
    if any(item != KHR_GAUSSIAN_SPLATTING for item in required):
        raise ValueError("Gaussian glTF contains unknown mandatory extension semantics")
    if any(item != KHR_GAUSSIAN_SPLATTING for item in used):
        raise ValueError("Gaussian glTF extension composition requires a separate compatibility profile")
    for prohibited in ("animations", "skins", "cameras", "images", "nodes", "scenes"):
        if document.get(prohibited):
            raise ValueError(f"Gaussian glTF {prohibited} are outside the isolated importer boundary")

    buffers = _load_buffers(document, bin_chunk)
    _validate_non_overlapping_buffer_views(document, buffers)
    if sum(len(item) for item in buffers) > MAX_GLTF_DECODED_BYTES:
        raise ValueError("Gaussian glTF decoded byte ceiling exceeded")
    meshes = _array(document, "meshes", MAX_GLTF_MESHES)
    if len(meshes) != 1:
        raise ValueError("Gaussian glTF importer admits exactly one isolated mesh")
    mesh = meshes[0]
    if not isinstance(mesh, Mapping) or set(mesh) - {"primitives", "name", "extensions", "extras"}:
        raise ValueError("Gaussian glTF mesh keys are invalid")
    primitives_payload = mesh.get("primitives")
    if not isinstance(primitives_payload, list) or not 1 <= len(primitives_payload) <= MAX_GLTF_PRIMITIVES:
        raise ValueError("Gaussian glTF mesh requires bounded primitives")

    conversion = CoordinateConversion("RIGHT_HANDED", "Y_UP", 1.0)
    all_positions: list[tuple[float, float, float]] = []
    all_rotations: list[tuple[float, float, float, float]] = []
    all_scales: list[tuple[float, float, float]] = []
    all_opacities: list[float] = []
    all_coefficients: list[tuple[float, ...]] = []
    all_colors: list[tuple[int, int, int, int]] = []
    primitives: list[ImportedPrimitive] = []
    highest_degree = 0
    fallback_modes: set[str] = set()
    estimated_runtime_allocation = sum(len(item) for item in buffers)

    for primitive_index, primitive in enumerate(primitives_payload):
        if not isinstance(primitive, Mapping) or set(primitive) - {
            "attributes",
            "indices",
            "material",
            "mode",
            "targets",
            "extensions",
            "extras",
        }:
            raise ValueError("Gaussian glTF primitive keys are invalid")
        if primitive.get("mode") != 0 or primitive.get("targets") or "indices" in primitive:
            raise ValueError("Gaussian glTF admits non-indexed POINTS primitives only")
        extensions = primitive.get("extensions")
        if not isinstance(extensions, Mapping) or set(extensions) != {KHR_GAUSSIAN_SPLATTING}:
            raise ValueError("Gaussian glTF primitive extension set is invalid")
        extension = extensions[KHR_GAUSSIAN_SPLATTING]
        if not isinstance(extension, Mapping) or set(extension) - {
            "kernel",
            "colorSpace",
            "projection",
            "sortingMethod",
            "extensions",
            "extras",
        }:
            raise ValueError("KHR_gaussian_splatting extension object is invalid")
        if extension.get("extensions"):
            raise ValueError("nested Gaussian glTF extension semantics are not admitted")
        if extension.get("kernel") != "ellipse":
            raise ValueError("Gaussian glTF kernel is unsupported")
        if extension.get("colorSpace") not in {"srgb_rec709_display", "lin_rec709_display"}:
            raise ValueError("Gaussian glTF colorSpace is unsupported")
        if extension.get("projection", "perspective") != "perspective":
            raise ValueError("Gaussian glTF non-perspective projection is undefined")
        if extension.get("sortingMethod", "cameraDistance") != "cameraDistance":
            raise ValueError("Gaussian glTF sorting method is unsupported")

        attributes = primitive.get("attributes")
        if not isinstance(attributes, Mapping):
            raise ValueError("Gaussian glTF attributes must be an object")
        for semantic, (kind, component_types) in _REQUIRED.items():
            if semantic not in attributes:
                raise ValueError(f"Gaussian glTF requires {semantic}")
            accessor = _accessor(document, attributes[semantic])
            if accessor.get("type") != kind or accessor.get("componentType") not in component_types:
                raise ValueError(f"Gaussian glTF {semantic} accessor type is unsupported")
        allowed_prefix = f"{KHR_GAUSSIAN_SPLATTING}:SH_DEGREE_"
        allowed_semantics = {*_REQUIRED, "COLOR_0"}
        if any(
            semantic not in allowed_semantics and not semantic.startswith(allowed_prefix) for semantic in attributes
        ):
            raise ValueError("Gaussian glTF contains unsupported vertex attributes")

        degree, sh_semantics = _sh_semantics(attributes)
        position_accessor = _accessor(document, attributes["POSITION"])
        declared_count = position_accessor.get("count")
        if (
            isinstance(declared_count, bool)
            or not isinstance(declared_count, int)
            or declared_count < 1
            or len(all_positions) + declared_count > MAX_GAUSSIAN_GLTF_SPLATS
        ):
            raise ValueError("Gaussian glTF splat count exceeds bounds")
        coefficient_count = (degree + 1) ** 2 * 3
        estimated_runtime_allocation += declared_count * (384 + coefficient_count * 40)
        if estimated_runtime_allocation > MAX_GAUSSIAN_GLTF_RUNTIME_ALLOCATION_BYTES:
            raise ValueError("Gaussian glTF runtime allocation ceiling exceeded before accessor expansion")
        raw_positions = _read_attribute(document, buffers, attributes, "POSITION", "VEC3", {5126})
        raw_rotations = _read_attribute(
            document, buffers, attributes, f"{KHR_GAUSSIAN_SPLATTING}:ROTATION", "VEC4", {5120, 5122, 5126}
        )
        raw_scales = _read_attribute(
            document, buffers, attributes, f"{KHR_GAUSSIAN_SPLATTING}:SCALE", "VEC3", {5121, 5123, 5126}
        )
        raw_opacities = _read_attribute(
            document, buffers, attributes, f"{KHR_GAUSSIAN_SPLATTING}:OPACITY", "SCALAR", {5121, 5123, 5126}
        )
        sh_values = [
            _read_attribute(document, buffers, attributes, semantic, "VEC3", {5126}) for semantic in sh_semantics
        ]
        count = len(raw_positions)
        if count < 1 or len(all_positions) + count > MAX_GLTF_VERTICES:
            raise ValueError("Gaussian glTF splat count exceeds bounds")
        if any(len(values) != count for values in [raw_rotations, raw_scales, raw_opacities, *sh_values]):
            raise ValueError("Gaussian glTF attribute counts do not match")

        converted = [apply_coordinate_conversion(item, conversion.matrix) for item in raw_positions]
        rotations = []
        for value in raw_rotations:
            quaternion = tuple(float(item) for item in value)
            if not all(math.isfinite(item) for item in quaternion):
                raise ValueError("Gaussian glTF rotation contains non-finite values")
            norm = math.sqrt(sum(item * item for item in quaternion))
            if not 0.999 <= norm <= 1.001:
                raise ValueError("Gaussian glTF rotations must be unit quaternions")
            rotations.append(quaternion)
        scales = [tuple(float(item) for item in value) for value in raw_scales]
        if any(not math.isfinite(item) or item < 0.0 for value in scales for item in value):
            raise ValueError("Gaussian glTF scales must be finite and non-negative")
        opacities = [float(value[0]) for value in raw_opacities]
        if any(not math.isfinite(item) or not 0.0 <= item <= 1.0 for item in opacities):
            raise ValueError("Gaussian glTF opacities must be finite values in [0, 1]")
        coefficients = [
            tuple(float(channel) for values in sh_values for channel in values[index]) for index in range(count)
        ]
        if any(not all(math.isfinite(item) for item in value) for value in coefficients):
            raise ValueError("Gaussian glTF spherical harmonics contain non-finite values")
        colors, fallback_mode = _fallback_colors(document, buffers, attributes, sh_values[0], opacities)
        fallback_modes.add(fallback_mode)

        bounds_min = tuple(min(item[axis] for item in converted) for axis in range(3))
        bounds_max = tuple(max(item[axis] for item in converted) for axis in range(3))
        primitives.append(
            ImportedPrimitive(
                primitive_id=f"gaussian-gltf-primitive:{primitive_index}",
                topology="POINTS",
                vertex_count=count,
                index_count=0,
                bounds_min=bounds_min,
                bounds_max=bounds_max,
                attributes=tuple(attributes),
                material_ref=None,
            )
        )
        all_positions.extend(converted)
        all_rotations.extend(rotations)
        all_scales.extend(scales)
        all_opacities.extend(opacities)
        all_coefficients.extend(coefficients)
        all_colors.extend(colors)
        highest_degree = max(highest_degree, degree)

    if any(len(value) != (highest_degree + 1) ** 2 * 3 for value in all_coefficients):
        raise ValueError("Gaussian glTF primitives must use one common spherical-harmonic degree")
    receipt = build_import_receipt(
        source_format=source_format,
        source_digest=hashlib.sha256(source).hexdigest(),
        source_bytes=len(source),
        decoded_bytes=sum(len(item) for item in buffers),
        asset_type="GAUSSIAN_SPLATS",
        conversion=conversion,
        primitives=tuple(primitives),
        provenance_refs=provenance_refs,
        warnings=tuple(
            sorted(
                {
                    "KHR_gaussian_splatting is a Release Candidate compatibility profile",
                    "Gaussian center bounds do not include covariance extent",
                    *(
                        "Point fallback was derived from SH degree zero"
                        for mode in fallback_modes
                        if mode == "BOUNDED_SH0_PLACEHOLDER"
                    ),
                }
            )
        ),
    )
    return SpatialImportResult(
        receipt=receipt,
        positions=tuple(all_positions),
        colors_rgba=tuple(all_colors),
        gaussian_splats=GaussianSplatData(
            rotations_xyzw=tuple(all_rotations),
            scales_xyz=tuple(all_scales),
            opacities=tuple(all_opacities),
            sh_degree=highest_degree,
            sh_coefficients=tuple(all_coefficients),
        ),
        metadata={
            "extension": KHR_GAUSSIAN_SPLATTING,
            "extension_profile": KHR_GAUSSIAN_PROFILE,
            "extension_status": "RELEASE_CANDIDATE",
            "fallback_modes": tuple(sorted(fallback_modes)),
            "estimated_runtime_allocation_bytes": estimated_runtime_allocation,
            "training_path": False,
        },
    )


def import_gaussian_gltf_file(
    path: str | Path,
    *,
    provenance_refs: Sequence[str],
    root: str | Path | None = None,
    extension_profile: str = KHR_GAUSSIAN_PROFILE,
) -> SpatialImportResult:
    source, resolved = read_bounded_local_import_source(
        path,
        maximum_bytes=MAX_GLTF_SOURCE_BYTES,
        root=root,
        label="Gaussian glTF import",
    )
    return import_gaussian_gltf_bytes(
        source,
        provenance_refs=(*provenance_refs, f"local-file:{resolved.name}"),
        extension_profile=extension_profile,
    )
