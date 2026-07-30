"""Strict immutable contracts for bounded spatial interchange.

Imported bytes remain derived projection assets. Receipts report exactly what
was decoded and converted; they never grant provenance, execution, renderer,
patch, promotion, or production authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib
import math
import os
from pathlib import Path
import re
import stat
import struct
from types import MappingProxyType
from typing import Any

from aura_event_contracts import canonical_json, stable_digest
from aura_spatial_contracts import PATCH_AUTHORITY
from aura_spatial_coordinate_frames import compile_coordinate_conversion_matrix

SPATIAL_IMPORT_CONTRACTS_VERSION = "AURA_SPATIAL_IMPORT_CONTRACTS_V1"
SPATIAL_IMPORT_RECEIPT_SCHEMA_VERSION = "AURA_SPATIAL_IMPORT_RECEIPT_SCHEMA_V1"
GAUSSIAN_REPRESENTATION_DIGEST_VERSION = "AURA_GAUSSIAN_REPRESENTATION_V1"
MAX_IMPORT_PRIMITIVES = 4096
MAX_IMPORT_SOURCE_REFS = 256
MAX_IMPORT_SOURCE_REF_BYTES = 2_048
MAX_IMPORT_SOURCE_REFS_BYTES = 65_536
MAX_IMPORT_WARNINGS = 256
MAX_IMPORT_METADATA_DEPTH = 12
MAX_IMPORT_METADATA_ITEMS = 1024
MAX_IMPORT_METADATA_BYTES = 65_536
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class SpatialSourceFormat(str, Enum):
    GLTF = "GLTF"
    GLB = "GLB"
    PLY_ASCII = "PLY_ASCII"
    PLY_BINARY_LE = "PLY_BINARY_LE"
    PLY_BINARY_BE = "PLY_BINARY_BE"
    SPZ_V4 = "SPZ_V4"


def _identifier(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not _ID.fullmatch(text):
        raise ValueError(f"{field_name} is not a canonical identifier")
    return text


def _digest(value: Any, field_name: str) -> str:
    text = str(value or "").strip().lower()
    if not _DIGEST.fullmatch(text):
        raise ValueError(f"{field_name} must be lowercase sha256")
    return text


def _positive_int(value: Any, field_name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
        raise ValueError(f"{field_name} must be an integer in [0, {maximum}]")
    return value


def _finite_tuple(values: Sequence[Any], length: int, field_name: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes, bytearray)) or len(values) != length:
        raise ValueError(f"{field_name} must contain {length} finite numbers")
    result = tuple(float(item) for item in values)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{field_name} must contain finite numbers")
    return result


def _freeze_import_metadata(
    value: Any,
    *,
    depth: int = 0,
    counter: list[int] | None = None,
    active: set[int] | None = None,
) -> Any:
    """Freeze a bounded JSON tree while rejecting cycles and non-finite values."""

    if counter is None:
        counter = [0]
    if active is None:
        active = set()
    counter[0] += 1
    if counter[0] > MAX_IMPORT_METADATA_ITEMS or depth > MAX_IMPORT_METADATA_DEPTH:
        raise ValueError("import metadata exceeds depth/item ceilings")
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in active:
            raise ValueError("import metadata contains a recursive container")
        active.add(identity)
        try:
            frozen: dict[str, Any] = {}
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
                if not isinstance(key, str) or not key or len(key.encode("utf-8")) > 256:
                    raise ValueError("import metadata keys must be bounded non-empty strings")
                frozen[key] = _freeze_import_metadata(item, depth=depth + 1, counter=counter, active=active)
            return MappingProxyType(frozen)
        finally:
            active.remove(identity)
    if isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in active:
            raise ValueError("import metadata contains a recursive container")
        active.add(identity)
        try:
            return tuple(
                _freeze_import_metadata(item, depth=depth + 1, counter=counter, active=active) for item in value
            )
        finally:
            active.remove(identity)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("import metadata contains a non-finite float")
        return value
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise ValueError(f"import metadata contains a non-JSON value: {type(value).__name__}")


def _thaw_import_metadata(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_import_metadata(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_import_metadata(item) for item in value]
    return value


@dataclass(frozen=True)
class CoordinateConversion:
    source_handedness: str
    source_up_axis: str
    source_meters_per_unit: float
    target_handedness: str = "RIGHT_HANDED"
    target_up_axis: str = "Y_UP"
    target_meters_per_unit: float = 1.0
    matrix: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        matrix = compile_coordinate_conversion_matrix(
            source_handedness=self.source_handedness,
            source_up_axis=self.source_up_axis,
            source_meters_per_unit=self.source_meters_per_unit,
            target_handedness=self.target_handedness,
            target_up_axis=self.target_up_axis,
            target_meters_per_unit=self.target_meters_per_unit,
        )
        if self.matrix and _finite_tuple(self.matrix, 16, "conversion.matrix") != matrix:
            raise ValueError("coordinate conversion matrix does not match declared basis")
        object.__setattr__(self, "matrix", matrix)
        object.__setattr__(self, "source_meters_per_unit", float(self.source_meters_per_unit))
        object.__setattr__(self, "target_meters_per_unit", float(self.target_meters_per_unit))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_handedness": self.source_handedness,
            "source_up_axis": self.source_up_axis,
            "source_meters_per_unit": self.source_meters_per_unit,
            "target_handedness": self.target_handedness,
            "target_up_axis": self.target_up_axis,
            "target_meters_per_unit": self.target_meters_per_unit,
            "matrix": list(self.matrix),
        }


@dataclass(frozen=True)
class ImportedPrimitive:
    primitive_id: str
    topology: str
    vertex_count: int
    index_count: int
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    attributes: tuple[str, ...]
    material_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "primitive_id", _identifier(self.primitive_id, "primitive_id"))
        if self.topology not in {"TRIANGLES", "POINTS"}:
            raise ValueError("unsupported imported primitive topology")
        object.__setattr__(self, "vertex_count", _positive_int(self.vertex_count, "vertex_count", 10_000_000))
        object.__setattr__(self, "index_count", _positive_int(self.index_count, "index_count", 30_000_000))
        minimum = _finite_tuple(self.bounds_min, 3, "bounds_min")
        maximum = _finite_tuple(self.bounds_max, 3, "bounds_max")
        if any(low > high for low, high in zip(minimum, maximum)):
            raise ValueError("primitive bounds are inverted")
        object.__setattr__(self, "bounds_min", minimum)
        object.__setattr__(self, "bounds_max", maximum)
        attrs = tuple(sorted({_identifier(item, "primitive attribute") for item in self.attributes}))
        if not attrs or len(attrs) > 32:
            raise ValueError("primitive attributes must be bounded and non-empty")
        object.__setattr__(self, "attributes", attrs)
        if self.material_ref is not None:
            object.__setattr__(self, "material_ref", _identifier(self.material_ref, "material_ref"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "topology": self.topology,
            "vertex_count": self.vertex_count,
            "index_count": self.index_count,
            "bounds_min": list(self.bounds_min),
            "bounds_max": list(self.bounds_max),
            "attributes": list(self.attributes),
            "material_ref": self.material_ref,
        }


@dataclass(frozen=True)
class SpatialImportReceipt:
    receipt_id: str
    source_format: SpatialSourceFormat | str
    source_digest: str
    source_bytes: int
    decoded_bytes: int
    element_count: int
    asset_type: str
    coordinate_conversion: CoordinateConversion
    primitives: tuple[ImportedPrimitive, ...]
    provenance_refs: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    status: str = "IMPORTED"
    local_only: bool = True
    scripts_executed: bool = False
    shaders_executed: bool = False
    network_fetch_performed: bool = False
    training_invoked: bool = False
    projection_only: bool = True
    provenance_authority: bool = False
    renderer_authority: bool = False
    execution_authority: bool = False
    patch_authority: str = PATCH_AUTHORITY
    production_mutation: bool = False
    automatic_merge: bool = False
    human_review_required: bool = True
    version: str = SPATIAL_IMPORT_CONTRACTS_VERSION
    schema_version: str = SPATIAL_IMPORT_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _identifier(self.receipt_id, "receipt_id"))
        fmt = (
            self.source_format
            if isinstance(self.source_format, SpatialSourceFormat)
            else SpatialSourceFormat(str(self.source_format))
        )
        object.__setattr__(self, "source_format", fmt)
        object.__setattr__(self, "source_digest", _digest(self.source_digest, "source_digest"))
        object.__setattr__(self, "source_bytes", _positive_int(self.source_bytes, "source_bytes", 1_073_741_824))
        object.__setattr__(self, "decoded_bytes", _positive_int(self.decoded_bytes, "decoded_bytes", 4_294_967_296))
        object.__setattr__(self, "element_count", _positive_int(self.element_count, "element_count", 30_000_000))
        if self.asset_type not in {"MESH", "POINT_CLOUD", "GAUSSIAN_SPLATS"}:
            raise ValueError("unsupported imported asset type")
        if not isinstance(self.coordinate_conversion, CoordinateConversion):
            raise ValueError("coordinate_conversion must be a CoordinateConversion")
        if (
            not isinstance(self.primitives, tuple)
            or not self.primitives
            or len(self.primitives) > MAX_IMPORT_PRIMITIVES
            or not all(isinstance(item, ImportedPrimitive) for item in self.primitives)
        ):
            raise ValueError("primitives must be a bounded non-empty tuple")
        refs = tuple(sorted({str(item).strip() for item in self.provenance_refs if str(item).strip()}))
        if (
            not refs
            or len(refs) > MAX_IMPORT_SOURCE_REFS
            or any(len(item.encode("utf-8")) > MAX_IMPORT_SOURCE_REF_BYTES for item in refs)
            or sum(len(item.encode("utf-8")) for item in refs) > MAX_IMPORT_SOURCE_REFS_BYTES
        ):
            raise ValueError("provenance_refs must be bounded and non-empty")
        object.__setattr__(self, "provenance_refs", refs)
        warnings = tuple(sorted({str(item) for item in self.warnings}))
        if len(warnings) > MAX_IMPORT_WARNINGS or any(len(item) > 512 for item in warnings):
            raise ValueError("warnings must be bounded")
        object.__setattr__(self, "warnings", warnings)
        if (
            self.status != "IMPORTED"
            or self.version != SPATIAL_IMPORT_CONTRACTS_VERSION
            or self.schema_version != SPATIAL_IMPORT_RECEIPT_SCHEMA_VERSION
        ):
            raise ValueError("unsupported import receipt contract")
        required = {
            "local_only": True,
            "scripts_executed": False,
            "shaders_executed": False,
            "network_fetch_performed": False,
            "training_invoked": False,
            "projection_only": True,
            "provenance_authority": False,
            "renderer_authority": False,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "production_mutation": False,
            "automatic_merge": False,
            "human_review_required": True,
        }
        for name, expected in required.items():
            value = getattr(self, name)
            if type(value) is not type(expected) or value != expected:
                raise ValueError(f"import receipt {name} boundary is invalid")

    def _body(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "source_format": self.source_format.value,
            "source_digest": self.source_digest,
            "source_bytes": self.source_bytes,
            "decoded_bytes": self.decoded_bytes,
            "element_count": self.element_count,
            "asset_type": self.asset_type,
            "coordinate_conversion": self.coordinate_conversion.to_dict(),
            "primitives": [item.to_dict() for item in self.primitives],
            "provenance_refs": list(self.provenance_refs),
            "warnings": list(self.warnings),
            "status": self.status,
            "local_only": self.local_only,
            "scripts_executed": self.scripts_executed,
            "shaders_executed": self.shaders_executed,
            "network_fetch_performed": self.network_fetch_performed,
            "training_invoked": self.training_invoked,
            "projection_only": self.projection_only,
            "provenance_authority": self.provenance_authority,
            "renderer_authority": self.renderer_authority,
            "execution_authority": self.execution_authority,
            "patch_authority": self.patch_authority,
            "production_mutation": self.production_mutation,
            "automatic_merge": self.automatic_merge,
            "human_review_required": self.human_review_required,
            "version": self.version,
            "schema_version": self.schema_version,
        }

    @property
    def derived_asset_digest(self) -> str:
        return stable_digest({k: v for k, v in self._body().items() if k != "receipt_id"}, digest_size=32)

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "derived_asset_digest": self.derived_asset_digest}


@dataclass(frozen=True)
class GaussianSplatData:
    """Explicit, bounded Gaussian attributes detached from scene authority."""

    rotations_xyzw: tuple[tuple[float, float, float, float], ...]
    scales_xyz: tuple[tuple[float, float, float], ...]
    opacities: tuple[float, ...]
    sh_degree: int
    sh_coefficients: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        rotations = tuple(_finite_tuple(item, 4, "gaussian rotation") for item in self.rotations_xyzw)
        scales = tuple(_finite_tuple(item, 3, "gaussian scale") for item in self.scales_xyz)
        opacities = tuple(float(item) for item in self.opacities)
        if not all(math.isfinite(item) and 0.0 <= item <= 1.0 for item in opacities):
            raise ValueError("gaussian opacities must be finite values in [0, 1]")
        if isinstance(self.sh_degree, bool) or not isinstance(self.sh_degree, int) or not 0 <= self.sh_degree <= 4:
            raise ValueError("gaussian sh_degree must be in [0, 4]")
        coefficient_count = (self.sh_degree + 1) ** 2 * 3
        coefficients = tuple(
            _finite_tuple(item, coefficient_count, "gaussian spherical harmonics") for item in self.sh_coefficients
        )
        count = len(rotations)
        if count < 1 or count > 2_000_000:
            raise ValueError("gaussian splat count exceeds bounds")
        if len(scales) != count or len(opacities) != count or len(coefficients) != count:
            raise ValueError("gaussian attributes must have identical counts")
        for rotation in rotations:
            norm = math.sqrt(sum(component * component for component in rotation))
            if not 0.999 <= norm <= 1.001:
                raise ValueError("gaussian rotations must be normalized quaternions")
        if any(component < 0.0 for scale in scales for component in scale):
            raise ValueError("gaussian scales must be non-negative")
        object.__setattr__(self, "rotations_xyzw", rotations)
        object.__setattr__(self, "scales_xyz", scales)
        object.__setattr__(self, "opacities", opacities)
        object.__setattr__(self, "sh_coefficients", coefficients)

    @property
    def count(self) -> int:
        return len(self.rotations_xyzw)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rotations_xyzw": [list(item) for item in self.rotations_xyzw],
            "scales_xyz": [list(item) for item in self.scales_xyz],
            "opacities": list(self.opacities),
            "sh_degree": self.sh_degree,
            "sh_coefficients": [list(item) for item in self.sh_coefficients],
        }


def _float32_bytes(value: float, field_name: str) -> bytes:
    try:
        packed = struct.pack("<f", float(value))
    except (OverflowError, struct.error) as exc:
        raise ValueError(f"{field_name} exceeds finite Float32 representation") from exc
    if not math.isfinite(struct.unpack("<f", packed)[0]):
        raise ValueError(f"{field_name} exceeds finite Float32 representation")
    return packed


def gaussian_representation_digest(
    positions: Sequence[Sequence[Any]],
    colors_rgba: Sequence[Sequence[Any]],
    gaussian_splats: GaussianSplatData,
) -> str:
    """Hash the exact bounded Float32/RGBA8 representation consumed by renderers."""

    if not isinstance(gaussian_splats, GaussianSplatData):
        raise ValueError("gaussian_splats must be GaussianSplatData")
    count = gaussian_splats.count
    if len(positions) != count or len(colors_rgba) != count:
        raise ValueError("Gaussian digest inputs must have identical counts")
    coefficient_count = (gaussian_splats.sh_degree + 1) ** 2 * 3
    digest = hashlib.sha256()
    digest.update(GAUSSIAN_REPRESENTATION_DIGEST_VERSION.encode("ascii") + b"\x00")
    digest.update(struct.pack("<IBI", count, gaussian_splats.sh_degree, coefficient_count))
    for label, values, width in (
        ("position", positions, 3),
        ("rotation", gaussian_splats.rotations_xyzw, 4),
        ("scale", gaussian_splats.scales_xyz, 3),
    ):
        for vector in values:
            if len(vector) != width:
                raise ValueError(f"Gaussian {label} width is invalid")
            for component in vector:
                digest.update(_float32_bytes(float(component), f"Gaussian {label}"))
    for opacity in gaussian_splats.opacities:
        digest.update(_float32_bytes(opacity, "Gaussian opacity"))
    for coefficients in gaussian_splats.sh_coefficients:
        if len(coefficients) != coefficient_count:
            raise ValueError("Gaussian coefficient width is invalid")
        for component in coefficients:
            digest.update(_float32_bytes(component, "Gaussian spherical harmonic"))
    for color in colors_rgba:
        channels = tuple(int(item) for item in color)
        if len(channels) != 4 or any(item < 0 or item > 255 for item in channels):
            raise ValueError("Gaussian digest colors must be RGBA8")
        digest.update(bytes(channels))
    return digest.hexdigest()


@dataclass(frozen=True)
class SpatialImportResult:
    receipt: SpatialImportReceipt
    positions: tuple[tuple[float, float, float], ...]
    indices: tuple[int, ...] = ()
    colors_rgba: tuple[tuple[int, int, int, int], ...] = ()
    gaussian_splats: GaussianSplatData | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, SpatialImportReceipt):
            raise ValueError("receipt must be a SpatialImportReceipt")
        positions = tuple(_finite_tuple(item, 3, "position") for item in self.positions)
        if len(positions) != self.receipt.element_count:
            raise ValueError("position count does not match receipt element_count")
        object.__setattr__(self, "positions", positions)
        indices = tuple(_positive_int(item, "index", max(0, len(positions) - 1)) for item in self.indices)
        object.__setattr__(self, "indices", indices)
        colors = tuple(tuple(int(v) for v in color) for color in self.colors_rgba)
        if colors and (
            len(colors) != len(positions) or any(len(c) != 4 or any(v < 0 or v > 255 for v in c) for c in colors)
        ):
            raise ValueError("colors_rgba must align with positions")
        object.__setattr__(self, "colors_rgba", colors)
        if self.receipt.asset_type == "GAUSSIAN_SPLATS":
            if not isinstance(self.gaussian_splats, GaussianSplatData):
                raise ValueError("Gaussian imports require explicit GaussianSplatData")
            if self.gaussian_splats.count != len(positions):
                raise ValueError("gaussian splat count must align with positions")
        elif self.gaussian_splats is not None:
            raise ValueError("non-Gaussian imports cannot carry GaussianSplatData")
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
        if not isinstance(self.metadata, Mapping):
            raise ValueError("import metadata must be an object")
        metadata = dict(self.metadata)
        if self.gaussian_splats is not None:
            representation_digest = gaussian_representation_digest(positions, colors, self.gaussian_splats)
            supplied_digest = metadata.get("representation_digest")
            if supplied_digest is not None and supplied_digest != representation_digest:
                raise ValueError("Gaussian representation digest does not match decoded attributes")
            coefficient_count = (self.gaussian_splats.sh_degree + 1) ** 2 * 3
            metadata["representation_digest"] = representation_digest
            metadata["representation_digest_version"] = GAUSSIAN_REPRESENTATION_DIGEST_VERSION
            metadata["representation_bytes_per_splat"] = 48 + coefficient_count * 4
            metadata["sh_degree"] = self.gaussian_splats.sh_degree
            metadata["gaussian_sh_degree"] = self.gaussian_splats.sh_degree
        if len(metadata) > 64:
            raise ValueError("import metadata exceeds key ceiling")
        frozen_metadata = _freeze_import_metadata(metadata)
        thawed_metadata = _thaw_import_metadata(frozen_metadata)
        if len(canonical_json(thawed_metadata).encode("utf-8")) > MAX_IMPORT_METADATA_BYTES:
            raise ValueError("import metadata exceeds byte ceiling")
        object.__setattr__(self, "metadata", frozen_metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt": self.receipt.to_dict(),
            "positions": [list(item) for item in self.positions],
            "indices": list(self.indices),
            "colors_rgba": [list(item) for item in self.colors_rgba],
            "gaussian_splats": None if self.gaussian_splats is None else self.gaussian_splats.to_dict(),
            "metadata": _thaw_import_metadata(self.metadata),
        }


def read_bounded_local_import_source(
    path: str | Path,
    *,
    maximum_bytes: int,
    root: str | Path | None = None,
    label: str = "spatial import",
) -> tuple[bytes, Path]:
    """Read a regular local file through an identity-bound no-follow descriptor."""

    if isinstance(maximum_bytes, bool) or not isinstance(maximum_bytes, int) or maximum_bytes < 1:
        raise ValueError("maximum_bytes must be a positive integer")
    candidate = Path(path)
    try:
        before = candidate.lstat()
    except OSError as exc:
        raise ValueError(f"{label} source cannot be inspected: {exc}") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError(f"{label} requires a regular local file")
    if before.st_size > maximum_bytes:
        raise ValueError(f"{label} source byte ceiling exceeded")
    try:
        resolved = candidate.resolve(strict=True)
        root_path = Path(root).resolve(strict=True) if root is not None else None
        if root_path is not None:
            resolved.relative_to(root_path)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label} source is outside the admitted local root") from exc

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(resolved, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"{label} requires a regular local file")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError(f"{label} source identity changed while opening")
        if opened.st_size > maximum_bytes:
            raise ValueError(f"{label} source byte ceiling exceeded")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = None
            source = handle.read(maximum_bytes + 1)
            after = os.fstat(handle.fileno())
        identity_before = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if identity_before != identity_after:
            raise ValueError(f"{label} source changed while being read")
    except OSError as exc:
        raise ValueError(f"{label} source cannot be read safely: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(source) > maximum_bytes:
        raise ValueError(f"{label} source byte ceiling exceeded")
    try:
        path_after = candidate.lstat()
        resolved_after = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} source changed after reading") from exc
    if (
        stat.S_ISLNK(path_after.st_mode)
        or resolved_after != resolved
        or (path_after.st_dev, path_after.st_ino) != (after.st_dev, after.st_ino)
    ):
        raise ValueError(f"{label} source identity changed during reading")
    return source, resolved


def build_import_receipt(
    *,
    source_format: SpatialSourceFormat,
    source_digest: str,
    source_bytes: int,
    decoded_bytes: int,
    asset_type: str,
    conversion: CoordinateConversion,
    primitives: tuple[ImportedPrimitive, ...],
    provenance_refs: Sequence[str],
    warnings: Sequence[str] = (),
) -> SpatialImportReceipt:
    body = {
        "source_format": source_format.value,
        "source_digest": source_digest,
        "source_bytes": source_bytes,
        "decoded_bytes": decoded_bytes,
        "asset_type": asset_type,
        "conversion": conversion.to_dict(),
        "primitives": [item.to_dict() for item in primitives],
        "provenance_refs": sorted(set(provenance_refs)),
        "warnings": sorted(set(warnings)),
    }
    receipt_id = "spatial-import:" + stable_digest(body, digest_size=12)
    return SpatialImportReceipt(
        receipt_id=receipt_id,
        source_format=source_format,
        source_digest=source_digest,
        source_bytes=source_bytes,
        decoded_bytes=decoded_bytes,
        element_count=sum(item.vertex_count for item in primitives),
        asset_type=asset_type,
        coordinate_conversion=conversion,
        primitives=primitives,
        provenance_refs=tuple(provenance_refs),
        warnings=tuple(warnings),
    )


def canonical_receipt_json(receipt: SpatialImportReceipt) -> str:
    return canonical_json(receipt.to_dict())


def _exact_payload_keys(payload: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(payload)
    if actual != expected:
        raise ValueError(
            f"{label} keys mismatch: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


def validate_spatial_import_receipt_payload(
    payload: Mapping[str, Any],
) -> SpatialImportReceipt:
    """Validate exact runtime/schema parity for a canonical import receipt."""

    if not isinstance(payload, Mapping):
        raise ValueError("import receipt payload must be an object")
    expected = {
        "receipt_id",
        "source_format",
        "source_digest",
        "source_bytes",
        "decoded_bytes",
        "element_count",
        "asset_type",
        "coordinate_conversion",
        "primitives",
        "provenance_refs",
        "warnings",
        "status",
        "local_only",
        "scripts_executed",
        "shaders_executed",
        "network_fetch_performed",
        "training_invoked",
        "projection_only",
        "provenance_authority",
        "renderer_authority",
        "execution_authority",
        "patch_authority",
        "production_mutation",
        "automatic_merge",
        "human_review_required",
        "version",
        "schema_version",
        "derived_asset_digest",
    }
    _exact_payload_keys(payload, expected, "import receipt")
    conversion_payload = payload["coordinate_conversion"]
    if not isinstance(conversion_payload, Mapping):
        raise ValueError("coordinate_conversion must be an object")
    _exact_payload_keys(
        conversion_payload,
        {
            "source_handedness",
            "source_up_axis",
            "source_meters_per_unit",
            "target_handedness",
            "target_up_axis",
            "target_meters_per_unit",
            "matrix",
        },
        "coordinate_conversion",
    )
    conversion = CoordinateConversion(
        source_handedness=conversion_payload["source_handedness"],
        source_up_axis=conversion_payload["source_up_axis"],
        source_meters_per_unit=conversion_payload["source_meters_per_unit"],
        target_handedness=conversion_payload["target_handedness"],
        target_up_axis=conversion_payload["target_up_axis"],
        target_meters_per_unit=conversion_payload["target_meters_per_unit"],
        matrix=tuple(conversion_payload["matrix"]),
    )
    primitive_payloads = payload["primitives"]
    if not isinstance(primitive_payloads, Sequence) or isinstance(primitive_payloads, (str, bytes, bytearray)):
        raise ValueError("primitives must be an array")
    primitive_keys = {
        "primitive_id",
        "topology",
        "vertex_count",
        "index_count",
        "bounds_min",
        "bounds_max",
        "attributes",
        "material_ref",
    }
    primitive_records: list[ImportedPrimitive] = []
    for item in primitive_payloads:
        if not isinstance(item, Mapping):
            raise ValueError("primitive payloads must be objects")
        _exact_payload_keys(item, primitive_keys, "import primitive")
        primitive_records.append(
            ImportedPrimitive(
                primitive_id=item["primitive_id"],
                topology=item["topology"],
                vertex_count=item["vertex_count"],
                index_count=item["index_count"],
                bounds_min=tuple(item["bounds_min"]),
                bounds_max=tuple(item["bounds_max"]),
                attributes=tuple(item["attributes"]),
                material_ref=item["material_ref"],
            )
        )
    primitives = tuple(primitive_records)
    for name in ("provenance_refs", "warnings"):
        value = payload[name]
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise ValueError(f"{name} must be an array")
    receipt = SpatialImportReceipt(
        receipt_id=payload["receipt_id"],
        source_format=payload["source_format"],
        source_digest=payload["source_digest"],
        source_bytes=payload["source_bytes"],
        decoded_bytes=payload["decoded_bytes"],
        element_count=payload["element_count"],
        asset_type=payload["asset_type"],
        coordinate_conversion=conversion,
        primitives=primitives,
        provenance_refs=tuple(payload["provenance_refs"]),
        warnings=tuple(payload["warnings"]),
        status=payload["status"],
        local_only=payload["local_only"],
        scripts_executed=payload["scripts_executed"],
        shaders_executed=payload["shaders_executed"],
        network_fetch_performed=payload["network_fetch_performed"],
        training_invoked=payload["training_invoked"],
        projection_only=payload["projection_only"],
        provenance_authority=payload["provenance_authority"],
        renderer_authority=payload["renderer_authority"],
        execution_authority=payload["execution_authority"],
        patch_authority=payload["patch_authority"],
        production_mutation=payload["production_mutation"],
        automatic_merge=payload["automatic_merge"],
        human_review_required=payload["human_review_required"],
        version=payload["version"],
        schema_version=payload["schema_version"],
    )
    if receipt.to_dict() != dict(payload):
        raise ValueError("import receipt payload is not canonical")
    return receipt
