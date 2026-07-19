"""Canonical, representation-independent spatial contracts for AuraOS.

The spatial substrate owns immutable projection records only. Domain owners retain
truth and authority. A renderer, device, visual selection, VSA address, Gaussian
splat, or topology coordinate can never become patch or execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from enum import Enum
import math
import re
from typing import Any

from aura_event_contracts import canonical_json, sanitize_payload, stable_digest

SPATIAL_CONTRACTS_VERSION = "AURA_SPATIAL_CONTRACTS_V1"
SPATIAL_SCENE_SCHEMA_VERSION = "1.0"
SPATIAL_RENDER_CONTRACTS_VERSION = "AURA_SPATIAL_RENDER_CONTRACTS_V1"
SPATIAL_DEVICE_PROFILE_SCHEMA_VERSION = "1.0"
SPATIAL_RENDER_PLAN_SCHEMA_VERSION = "1.0"
SPATIAL_RENDER_RECEIPT_SCHEMA_VERSION = "1.0"
SPATIAL_SESSION_SUMMARY_SCHEMA_VERSION = "1.0"
SPATIAL_DISSOLUTION_RECEIPT_SCHEMA_VERSION = "1.0"
MAX_SPATIAL_METADATA_BYTES = 65_536
MAX_SPATIAL_METADATA_DEPTH = 32
MAX_SPATIAL_METADATA_ITEMS = 8_192
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SPATIAL_EXECUTION_AUTHORITY = False

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_DIGEST = re.compile(r"^(?:sha256|blake2b-256):[0-9a-f]{64}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PROTECTED_AUTHORITY_KEYS = frozenset(
    {
        "approval",
        "authorization",
        "authority_decision",
        "automatic_commit",
        "automatic_fix",
        "automatic_merge",
        "automatic_pull_request",
        "automatic_push",
        "capability_lease",
        "execution_authority",
        "lease",
        "lease_id",
        "merge",
        "patch_authority",
        "production_mutation",
        "promotion",
        "render_authority",
        "renderer_authority",
        "renderer_input_is_authority",
        "verifier_receipt",
        "vsa_patch_authority",
    }
)
_PROTECTED_AUTHORITY_TOKENS = frozenset(re.sub(r"[^a-z0-9]+", "", item.lower()) for item in _PROTECTED_AUTHORITY_KEYS)
_RENDERER_CANONICAL_ORDER = (
    "WEBXR",
    "WEBGPU",
    "WEBGL2",
    "ACCESSIBLE_2D",
    "HEADLESS",
)


class _FrozenMapping(tuple):
    """Internal marker preserving JSON object identity, including empty objects."""


class _FrozenSequence(tuple):
    """Internal marker preserving JSON array identity, including empty arrays."""


class SpatialTruthClass(str, Enum):
    EXACT = "EXACT"
    DERIVED = "DERIVED"
    PRESENTATION = "PRESENTATION"
    HYPOTHESIS = "HYPOTHESIS"


class Handedness(str, Enum):
    RIGHT_HANDED = "RIGHT_HANDED"
    LEFT_HANDED = "LEFT_HANDED"


class UpAxis(str, Enum):
    X_UP = "X_UP"
    Y_UP = "Y_UP"
    Z_UP = "Z_UP"


class SpatialAssetType(str, Enum):
    TOPOLOGY_GRAPH = "TOPOLOGY_GRAPH"
    MESH = "MESH"
    POINT_CLOUD = "POINT_CLOUD"
    GAUSSIAN_SPLAT = "GAUSSIAN_SPLAT"
    VOXEL = "VOXEL"
    SIGNED_DISTANCE_FIELD = "SIGNED_DISTANCE_FIELD"
    PLANE = "PLANE"
    ANNOTATION = "ANNOTATION"


class SpatialEntityType(str, Enum):
    DOMAIN_NODE = "DOMAIN_NODE"
    DOMAIN_LINK = "DOMAIN_LINK"
    ASSET_INSTANCE = "ASSET_INSTANCE"
    ANCHOR = "ANCHOR"
    REGION = "REGION"
    LABEL = "LABEL"
    CONTROL = "CONTROL"


class SpatialInteractionAction(str, Enum):
    SELECT = "SELECT"
    DESELECT = "DESELECT"
    EXPAND = "EXPAND"
    CONTRACT = "CONTRACT"
    FOCUS = "FOCUS"
    OPEN_SOURCE = "OPEN_SOURCE"
    PREPARE_REPAIR_REQUEST = "PREPARE_REPAIR_REQUEST"


class SpatialRendererKind(str, Enum):
    WEBXR = "WEBXR"
    WEBGPU = "WEBGPU"
    WEBGL2 = "WEBGL2"
    ACCESSIBLE_2D = "ACCESSIBLE_2D"
    HEADLESS = "HEADLESS"


class SpatialRenderOutcome(str, Enum):
    PRESENTED = "PRESENTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNAVAILABLE = "UNAVAILABLE"


class SpatialRenderEvidenceClass(str, Enum):
    MEASURED = "MEASURED"
    DERIVED = "DERIVED"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


class SpatialSessionState(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    DISSOLVED = "DISSOLVED"


def _required(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _identifier(value: Any, field_name: str) -> str:
    text = _required(value, field_name)
    if not _IDENTIFIER.fullmatch(text):
        raise ValueError(f"{field_name} contains unsupported characters")
    return text


def _optional_identifier(value: Any, field_name: str) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return _identifier(value, field_name)


def _enum(value: str | Enum, enum_type: type[Enum], field_name: str) -> Enum:
    raw = value.value if isinstance(value, Enum) else str(value)
    try:
        return enum_type(raw)
    except ValueError as exc:
        raise ValueError(f"unknown {field_name}: {raw}") from exc


def _strict_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _bounded_int(
    value: Any,
    field_name: str,
    *,
    minimum: int = 0,
    maximum: int = 2_147_483_647,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be an integer in {minimum}..{maximum}")
    return value


def _hex_digest_value(value: Any, field_name: str) -> str:
    text = _required(value, field_name).lower()
    if not _HEX_DIGEST.fullmatch(text):
        raise ValueError(f"{field_name} must be a 64-character lowercase hex digest")
    return text


def _optional_text(value: Any, field_name: str, *, maximum: int = 2048) -> str:
    text = str(value or "").strip()
    if len(text) > maximum or any(ord(char) < 32 for char in text):
        raise ValueError(f"{field_name} exceeds its bounded text contract")
    return text


def _bounded_strings(
    values: Sequence[Any] | None,
    field_name: str,
    *,
    max_items: int,
    max_item_bytes: int,
    max_total_bytes: int,
    canonical: bool = False,
) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError(f"{field_name} must be a sequence")
    if len(values) > max_items:
        raise ValueError(f"{field_name} exceeds its {max_items}-item ceiling")
    result: list[str] = []
    total = 0
    for index, value in enumerate(values):
        text = _required(value, f"{field_name}[{index}]")
        encoded = text.encode("utf-8")
        if len(encoded) > max_item_bytes:
            raise ValueError(f"{field_name}[{index}] exceeds its byte ceiling")
        total += len(encoded)
        if total > max_total_bytes:
            raise ValueError(f"{field_name} exceeds its aggregate byte ceiling")
        if text not in result:
            result.append(text)
    if canonical:
        result.sort()
    return tuple(result)


def _bounded_identifiers(
    values: Sequence[Any] | None,
    field_name: str,
    *,
    max_items: int,
    canonical: bool = False,
) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError(f"{field_name} must be a sequence")
    if len(values) > max_items:
        raise ValueError(f"{field_name} exceeds its {max_items}-item ceiling")
    result: list[str] = []
    for index, value in enumerate(values):
        item = _identifier(value, f"{field_name}[{index}]")
        if item not in result:
            result.append(item)
    if canonical:
        result.sort()
    return tuple(result)


def _renderer_tuple(
    values: Sequence[Any],
    field_name: str,
    *,
    canonical_set: bool,
) -> tuple[SpatialRendererKind, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError(f"{field_name} must be a sequence")
    result: list[SpatialRendererKind] = []
    for index, value in enumerate(values):
        item = _enum(value, SpatialRendererKind, f"{field_name}[{index}]")
        assert isinstance(item, SpatialRendererKind)
        if item in result:
            raise ValueError(f"{field_name} values must be unique")
        result.append(item)
    if canonical_set:
        rank = {name: index for index, name in enumerate(_RENDERER_CANONICAL_ORDER)}
        result.sort(key=lambda item: rank[item.value])
    return tuple(result)


def _find_protected_authority_path(value: Any, path: str = "metadata") -> str | None:
    stack: list[tuple[Any, str, int]] = [(value, path, 0)]
    visited = 0
    while stack:
        current, current_path, depth = stack.pop()
        if depth > MAX_SPATIAL_METADATA_DEPTH:
            raise ValueError(f"{path} exceeds its nesting ceiling")
        visited += 1
        if visited > MAX_SPATIAL_METADATA_ITEMS:
            raise ValueError(f"{path} exceeds its item ceiling")
        if isinstance(current, Mapping):
            for key, item in current.items():
                token = re.sub(r"[^a-z0-9]+", "", str(key).lower())
                nested_path = f"{current_path}.{key}"
                if token in _PROTECTED_AUTHORITY_TOKENS:
                    return nested_path
                stack.append((item, nested_path, depth + 1))
        elif isinstance(current, (list, tuple)):
            for index, item in enumerate(current):
                stack.append((item, f"{current_path}[{index}]", depth + 1))
    return None


def _projection_metadata(
    value: Any,
    field_name: str,
) -> tuple[tuple[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, tuple) and all(
        isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value
    ):
        candidate: Any = {key: item for key, item in value}
    else:
        candidate = value
    if not isinstance(candidate, Mapping):
        raise ValueError(f"{field_name} must be an object")
    protected = _find_protected_authority_path(candidate, field_name)
    if protected is not None:
        raise ValueError(f"{field_name} cannot contain protected authority field: {protected}")
    return _metadata(candidate, field_name)


def _finite_number(value: Any, field_name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    return number


def _vector(
    value: Sequence[Any],
    length: int,
    field_name: str,
    *,
    positive: bool = False,
) -> tuple[float, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a sequence")
    if len(value) != length:
        raise ValueError(f"{field_name} must contain exactly {length} values")
    result = tuple(_finite_number(item, f"{field_name}[{index}]") for index, item in enumerate(value))
    if positive and any(item <= 0.0 for item in result):
        raise ValueError(f"{field_name} values must be positive")
    return result


def _quaternion(
    value: Sequence[Any],
    field_name: str,
) -> tuple[float, float, float, float]:
    result = _vector(value, 4, field_name)
    norm = math.sqrt(sum(item * item for item in result))
    if norm <= 1e-12:
        raise ValueError(f"{field_name} must not be a zero quaternion")
    normalized = tuple(item / norm for item in result)
    return (normalized[0], normalized[1], normalized[2], normalized[3])


def _strings(values: Sequence[Any] | None, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError(f"{field_name} must be a sequence")
    result: list[str] = []
    for index, value in enumerate(values):
        text = _required(value, f"{field_name}[{index}]")
        if text not in result:
            result.append(text)
    return tuple(result)


def _identifiers(values: Sequence[Any] | None, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError(f"{field_name} must be a sequence")
    result: list[str] = []
    for index, value in enumerate(values):
        item = _identifier(value, f"{field_name}[{index}]")
        if item not in result:
            result.append(item)
    return tuple(result)


def _freeze_json(value: Any, field_name: str = "metadata") -> Any:
    """Freeze JSON while preserving object/array identity for empty containers."""
    if isinstance(value, Mapping):
        return _FrozenMapping(
            (str(key), _freeze_json(item, f"{field_name}.{key}"))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    if isinstance(value, (list, tuple)):
        return _FrozenSequence(_freeze_json(item, f"{field_name}[]") for item in value)
    if isinstance(value, (set, frozenset)):
        frozen = [_freeze_json(item, f"{field_name}[]") for item in value]
        return _FrozenSequence(sorted(frozen, key=lambda item: canonical_json(_thaw_json(item))))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} contains a non-finite float")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ValueError(f"{field_name} contains a non-JSON value: {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, _FrozenMapping):
        return {key: _thaw_json(item) for key, item in value}
    if isinstance(value, _FrozenSequence):
        return [_thaw_json(item) for item in value]
    if isinstance(value, tuple):
        # Backward-compatible handling for record defaults and caller-supplied
        # already-frozen mapping tuples. Empty record metadata remains an object.
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value):
            return {key: _thaw_json(item) for key, item in value}
        return [_thaw_json(item) for item in value]
    return value


def _metadata(value: Any, field_name: str = "metadata") -> tuple[tuple[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, tuple) and all(
        isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value
    ):
        value = {key: item for key, item in value}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    try:
        raw_serialized = canonical_json(value).encode("utf-8")
    except (RecursionError, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON-compatible") from exc
    if len(raw_serialized) > MAX_SPATIAL_METADATA_BYTES:
        raise ValueError(f"{field_name} exceeds the {MAX_SPATIAL_METADATA_BYTES}-byte limit")
    try:
        value = sanitize_payload(value)
    except ValueError:
        raise
    except (RecursionError, TypeError) as exc:
        raise ValueError(f"{field_name} must be bounded JSON-compatible metadata") from exc
    try:
        serialized = canonical_json(value).encode("utf-8")
    except (RecursionError, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be bounded JSON-compatible metadata") from exc
    if len(serialized) > MAX_SPATIAL_METADATA_BYTES:
        raise ValueError(f"sanitized {field_name} exceeds the {MAX_SPATIAL_METADATA_BYTES}-byte limit")
    frozen = _freeze_json(value, field_name)
    assert isinstance(frozen, tuple)
    return frozen


class CanonicalSpatialRecord:
    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        mapping_fields = {"metadata", "intent_slots", "renderer_hints"}
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, Enum):
                result[field.name] = value.value
            elif isinstance(value, CanonicalSpatialRecord):
                result[field.name] = value.to_dict()
            elif isinstance(value, tuple) and field.name in mapping_fields:
                result[field.name] = _thaw_json(value)
            elif isinstance(value, tuple):
                result[field.name] = [_record_value(item) for item in value]
            else:
                result[field.name] = value
        return result

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict(), digest_size=32)


def _record_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, CanonicalSpatialRecord):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_record_value(item) for item in value]
    return value


@dataclass(frozen=True)
class CoordinateFrame(CanonicalSpatialRecord):
    frame_id: str
    parent_frame_id: str | None = None
    handedness: Handedness | str = Handedness.RIGHT_HANDED
    up_axis: UpAxis | str = UpAxis.Y_UP
    unit_scale_meters: float = 1.0
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_xyzw: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    source_refs: tuple[str, ...] = ()
    truth_class: SpatialTruthClass | str = SpatialTruthClass.DERIVED
    projection_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_id", _identifier(self.frame_id, "frame.frame_id"))
        object.__setattr__(
            self,
            "parent_frame_id",
            _optional_identifier(self.parent_frame_id, "frame.parent_frame_id"),
        )
        if self.parent_frame_id == self.frame_id:
            raise ValueError("frame.parent_frame_id cannot equal frame.frame_id")
        object.__setattr__(
            self,
            "handedness",
            _enum(self.handedness, Handedness, "frame.handedness"),
        )
        object.__setattr__(
            self,
            "up_axis",
            _enum(self.up_axis, UpAxis, "frame.up_axis"),
        )
        unit = _finite_number(self.unit_scale_meters, "frame.unit_scale_meters")
        if unit <= 0.0:
            raise ValueError("frame.unit_scale_meters must be positive")
        object.__setattr__(self, "unit_scale_meters", unit)
        object.__setattr__(
            self,
            "translation",
            _vector(self.translation, 3, "frame.translation"),
        )
        object.__setattr__(
            self,
            "rotation_xyzw",
            _quaternion(self.rotation_xyzw, "frame.rotation_xyzw"),
        )
        object.__setattr__(
            self,
            "scale",
            _vector(self.scale, 3, "frame.scale", positive=True),
        )
        object.__setattr__(
            self,
            "source_refs",
            _strings(self.source_refs, "frame.source_refs"),
        )
        object.__setattr__(
            self,
            "truth_class",
            _enum(self.truth_class, SpatialTruthClass, "frame.truth_class"),
        )
        object.__setattr__(
            self,
            "projection_only",
            _strict_bool(self.projection_only, "frame.projection_only"),
        )
        if not self.projection_only:
            raise ValueError("coordinate frames must remain projection-only")


@dataclass(frozen=True)
class SpatialAssetManifest(CanonicalSpatialRecord):
    asset_id: str
    asset_type: SpatialAssetType | str
    uri: str
    media_type: str
    content_digest: str
    byte_length: int
    frame_id: str
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    source_refs: tuple[str, ...]
    truth_class: SpatialTruthClass | str = SpatialTruthClass.DERIVED
    immutable: bool = True
    metadata: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", _identifier(self.asset_id, "asset.asset_id"))
        object.__setattr__(
            self,
            "asset_type",
            _enum(self.asset_type, SpatialAssetType, "asset.asset_type"),
        )
        object.__setattr__(self, "uri", _required(self.uri, "asset.uri"))
        object.__setattr__(
            self,
            "media_type",
            _required(self.media_type, "asset.media_type"),
        )
        digest = _required(self.content_digest, "asset.content_digest").lower()
        if not _DIGEST.fullmatch(digest):
            raise ValueError("asset.content_digest must be sha256:<64hex> or blake2b-256:<64hex>")
        object.__setattr__(self, "content_digest", digest)
        if type(self.byte_length) is not int or self.byte_length < 0:
            raise ValueError("asset.byte_length must be a non-negative integer")
        object.__setattr__(self, "frame_id", _identifier(self.frame_id, "asset.frame_id"))
        minimum = _vector(self.bounds_min, 3, "asset.bounds_min")
        maximum = _vector(self.bounds_max, 3, "asset.bounds_max")
        if any(low > high for low, high in zip(minimum, maximum)):
            raise ValueError("asset bounds_min must not exceed bounds_max")
        object.__setattr__(self, "bounds_min", minimum)
        object.__setattr__(self, "bounds_max", maximum)
        source_refs = _strings(self.source_refs, "asset.source_refs")
        if not source_refs:
            raise ValueError("asset.source_refs must not be empty")
        object.__setattr__(self, "source_refs", source_refs)
        object.__setattr__(
            self,
            "truth_class",
            _enum(self.truth_class, SpatialTruthClass, "asset.truth_class"),
        )
        object.__setattr__(
            self,
            "immutable",
            _strict_bool(self.immutable, "asset.immutable"),
        )
        if not self.immutable:
            raise ValueError("spatial asset manifests must be immutable")
        object.__setattr__(
            self,
            "metadata",
            _metadata(self.metadata, "asset.metadata"),
        )


@dataclass(frozen=True)
class SpatialEntity(CanonicalSpatialRecord):
    entity_id: str
    entity_type: SpatialEntityType | str
    label: str
    frame_id: str
    asset_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_xyzw: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    truth_class: SpatialTruthClass | str = SpatialTruthClass.DERIVED
    selectable: bool = True
    projection_only: bool = True
    patch_authority: bool = False
    metadata: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "entity_id",
            _identifier(self.entity_id, "entity.entity_id"),
        )
        object.__setattr__(
            self,
            "entity_type",
            _enum(self.entity_type, SpatialEntityType, "entity.entity_type"),
        )
        object.__setattr__(
            self,
            "label",
            _required(self.label, "entity.label"),
        )
        object.__setattr__(
            self,
            "frame_id",
            _identifier(self.frame_id, "entity.frame_id"),
        )
        object.__setattr__(
            self,
            "asset_ids",
            _identifiers(self.asset_ids, "entity.asset_ids"),
        )
        object.__setattr__(
            self,
            "source_refs",
            _strings(self.source_refs, "entity.source_refs"),
        )
        object.__setattr__(
            self,
            "position",
            _vector(self.position, 3, "entity.position"),
        )
        object.__setattr__(
            self,
            "rotation_xyzw",
            _quaternion(self.rotation_xyzw, "entity.rotation_xyzw"),
        )
        object.__setattr__(
            self,
            "scale",
            _vector(self.scale, 3, "entity.scale", positive=True),
        )
        object.__setattr__(
            self,
            "truth_class",
            _enum(self.truth_class, SpatialTruthClass, "entity.truth_class"),
        )
        object.__setattr__(
            self,
            "selectable",
            _strict_bool(self.selectable, "entity.selectable"),
        )
        object.__setattr__(
            self,
            "projection_only",
            _strict_bool(self.projection_only, "entity.projection_only"),
        )
        if not self.projection_only:
            raise ValueError("spatial entities must remain projection-only")
        object.__setattr__(
            self,
            "patch_authority",
            _strict_bool(self.patch_authority, "entity.patch_authority"),
        )
        if self.patch_authority:
            raise ValueError("spatial entities cannot carry patch authority")
        object.__setattr__(
            self,
            "metadata",
            _metadata(self.metadata, "entity.metadata"),
        )


@dataclass(frozen=True)
class SpatialLink(CanonicalSpatialRecord):
    link_id: str
    source_entity_id: str
    target_entity_id: str
    relation: str
    source_refs: tuple[str, ...] = ()
    truth_class: SpatialTruthClass | str = SpatialTruthClass.DERIVED
    directed: bool = True
    projection_only: bool = True
    metadata: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "link_id", _identifier(self.link_id, "link.link_id"))
        object.__setattr__(
            self,
            "source_entity_id",
            _identifier(self.source_entity_id, "link.source_entity_id"),
        )
        object.__setattr__(
            self,
            "target_entity_id",
            _identifier(self.target_entity_id, "link.target_entity_id"),
        )
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("spatial links cannot be self-referential")
        object.__setattr__(
            self,
            "relation",
            _identifier(self.relation, "link.relation"),
        )
        object.__setattr__(
            self,
            "source_refs",
            _strings(self.source_refs, "link.source_refs"),
        )
        object.__setattr__(
            self,
            "truth_class",
            _enum(self.truth_class, SpatialTruthClass, "link.truth_class"),
        )
        object.__setattr__(
            self,
            "directed",
            _strict_bool(self.directed, "link.directed"),
        )
        object.__setattr__(
            self,
            "projection_only",
            _strict_bool(self.projection_only, "link.projection_only"),
        )
        if not self.projection_only:
            raise ValueError("spatial links must remain projection-only")
        object.__setattr__(
            self,
            "metadata",
            _metadata(self.metadata, "link.metadata"),
        )


@dataclass(frozen=True)
class SpatialSceneSnapshot(CanonicalSpatialRecord):
    scene_id: str
    purpose_digest: str
    root_frame_id: str
    frames: tuple[CoordinateFrame, ...]
    assets: tuple[SpatialAssetManifest, ...]
    entities: tuple[SpatialEntity, ...]
    links: tuple[SpatialLink, ...] = ()
    source_refs: tuple[str, ...] = ()
    renderer_hints: tuple[tuple[str, Any], ...] = ()
    truth_policy: str = (
        "Domain source records are authoritative. Spatial coordinates, layouts, "
        "render assets, and interactions are bounded projections only."
    )
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    execution_authority: bool = SPATIAL_EXECUTION_AUTHORITY
    version: str = SPATIAL_CONTRACTS_VERSION
    schema_version: str = SPATIAL_SCENE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scene_id",
            _identifier(self.scene_id, "scene.scene_id"),
        )
        object.__setattr__(
            self,
            "purpose_digest",
            _required(self.purpose_digest, "scene.purpose_digest"),
        )
        object.__setattr__(
            self,
            "root_frame_id",
            _identifier(self.root_frame_id, "scene.root_frame_id"),
        )
        if not isinstance(self.frames, tuple) or not all(isinstance(item, CoordinateFrame) for item in self.frames):
            raise ValueError("scene.frames must be a tuple of CoordinateFrame records")
        if not self.frames:
            raise ValueError("scene.frames must not be empty")
        if not isinstance(self.assets, tuple) or not all(
            isinstance(item, SpatialAssetManifest) for item in self.assets
        ):
            raise ValueError("scene.assets must be a tuple of SpatialAssetManifest records")
        if not isinstance(self.entities, tuple) or not all(isinstance(item, SpatialEntity) for item in self.entities):
            raise ValueError("scene.entities must be a tuple of SpatialEntity records")
        if not isinstance(self.links, tuple) or not all(isinstance(item, SpatialLink) for item in self.links):
            raise ValueError("scene.links must be a tuple of SpatialLink records")
        object.__setattr__(
            self,
            "source_refs",
            _strings(self.source_refs, "scene.source_refs"),
        )
        object.__setattr__(
            self,
            "renderer_hints",
            _metadata(self.renderer_hints, "scene.renderer_hints"),
        )
        object.__setattr__(
            self,
            "truth_policy",
            _required(self.truth_policy, "scene.truth_policy"),
        )
        if self.patch_authority != PATCH_AUTHORITY:
            raise ValueError("scene.patch_authority must remain exact-source-only")
        if _strict_bool(self.vsa_patch_authority, "scene.vsa_patch_authority"):
            raise ValueError("scene.vsa_patch_authority must remain false")
        if _strict_bool(self.execution_authority, "scene.execution_authority"):
            raise ValueError("scene.execution_authority must remain false")
        if self.version != SPATIAL_CONTRACTS_VERSION:
            raise ValueError(f"unsupported spatial contracts version: {self.version}")
        if self.schema_version != SPATIAL_SCENE_SCHEMA_VERSION:
            raise ValueError(f"unsupported spatial scene schema version: {self.schema_version}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "purpose_digest": self.purpose_digest,
            "root_frame_id": self.root_frame_id,
            "frames": [item.to_dict() for item in self.frames],
            "assets": [item.to_dict() for item in self.assets],
            "entities": [item.to_dict() for item in self.entities],
            "links": [item.to_dict() for item in self.links],
            "source_refs": list(self.source_refs),
            "renderer_hints": _thaw_json(self.renderer_hints),
            "truth_policy": self.truth_policy,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "execution_authority": self.execution_authority,
            "version": self.version,
            "schema_version": self.schema_version,
            "scene_digest": self.scene_digest,
        }

    @property
    def scene_digest(self) -> str:
        body = {
            "scene_id": self.scene_id,
            "purpose_digest": self.purpose_digest,
            "root_frame_id": self.root_frame_id,
            "frames": [item.to_dict() for item in self.frames],
            "assets": [item.to_dict() for item in self.assets],
            "entities": [item.to_dict() for item in self.entities],
            "links": [item.to_dict() for item in self.links],
            "source_refs": list(self.source_refs),
            "renderer_hints": _thaw_json(self.renderer_hints),
            "truth_policy": self.truth_policy,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "execution_authority": self.execution_authority,
            "version": self.version,
            "schema_version": self.schema_version,
        }
        return stable_digest(body, digest_size=32)


@dataclass(frozen=True)
class SpatialRenderBudget(CanonicalSpatialRecord):
    max_entities: int = 128
    max_links: int = 320
    max_assets: int = 64
    max_asset_bytes: int = 268_435_456
    max_cpu_ms_per_frame: float = 16.667
    max_gpu_bytes: int = 536_870_912
    max_network_bytes: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_entities",
            _bounded_int(self.max_entities, "budget.max_entities", minimum=1, maximum=1_000_000),
        )
        object.__setattr__(
            self,
            "max_links",
            _bounded_int(self.max_links, "budget.max_links", minimum=0, maximum=4_000_000),
        )
        object.__setattr__(
            self,
            "max_assets",
            _bounded_int(self.max_assets, "budget.max_assets", minimum=0, maximum=100_000),
        )
        object.__setattr__(
            self,
            "max_asset_bytes",
            _bounded_int(
                self.max_asset_bytes,
                "budget.max_asset_bytes",
                minimum=0,
                maximum=1_099_511_627_776,
            ),
        )
        cpu = _finite_number(self.max_cpu_ms_per_frame, "budget.max_cpu_ms_per_frame")
        if not 0.0 < cpu <= 10_000.0:
            raise ValueError("budget.max_cpu_ms_per_frame must be in (0, 10000]")
        object.__setattr__(self, "max_cpu_ms_per_frame", cpu)
        object.__setattr__(
            self,
            "max_gpu_bytes",
            _bounded_int(
                self.max_gpu_bytes,
                "budget.max_gpu_bytes",
                minimum=0,
                maximum=1_099_511_627_776,
            ),
        )
        object.__setattr__(
            self,
            "max_network_bytes",
            _bounded_int(
                self.max_network_bytes,
                "budget.max_network_bytes",
                minimum=0,
                maximum=1_099_511_627_776,
            ),
        )


@dataclass(frozen=True)
class SpatialDeviceProfile(CanonicalSpatialRecord):
    profile_id: str
    supported_renderers: tuple[SpatialRendererKind, ...]
    budget: SpatialRenderBudget
    accessibility_required: bool = True
    xr_user_activation: bool = False
    network_allowed: bool = False
    source_refs: tuple[str, ...] = ()
    metadata: tuple[tuple[str, Any], ...] = ()
    fingerprinting_allowed: bool = False
    renderer_authority: bool = False
    execution_authority: bool = False
    patch_authority: bool = False
    version: str = SPATIAL_RENDER_CONTRACTS_VERSION
    schema_version: str = SPATIAL_DEVICE_PROFILE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", _identifier(self.profile_id, "device.profile_id"))
        renderers = _renderer_tuple(
            self.supported_renderers,
            "device.supported_renderers",
            canonical_set=True,
        )
        if not renderers:
            raise ValueError("device.supported_renderers must not be empty")
        if SpatialRendererKind.ACCESSIBLE_2D not in renderers:
            raise ValueError("device must support ACCESSIBLE_2D fallback")
        object.__setattr__(self, "supported_renderers", renderers)
        if not isinstance(self.budget, SpatialRenderBudget):
            raise ValueError("device.budget must be a SpatialRenderBudget")
        for field_name in (
            "accessibility_required",
            "xr_user_activation",
            "network_allowed",
            "fingerprinting_allowed",
            "renderer_authority",
            "execution_authority",
            "patch_authority",
        ):
            object.__setattr__(
                self,
                field_name,
                _strict_bool(getattr(self, field_name), f"device.{field_name}"),
            )
        if not self.accessibility_required:
            raise ValueError("device profiles must require accessible presentation")
        if self.fingerprinting_allowed:
            raise ValueError("device profiles cannot authorize fingerprinting")
        if self.renderer_authority or self.execution_authority or self.patch_authority:
            raise ValueError("device profiles cannot carry renderer, execution, or patch authority")
        object.__setattr__(
            self,
            "source_refs",
            _bounded_strings(
                self.source_refs,
                "device.source_refs",
                max_items=128,
                max_item_bytes=2048,
                max_total_bytes=65_536,
                canonical=True,
            ),
        )
        object.__setattr__(self, "metadata", _projection_metadata(self.metadata, "device.metadata"))
        if self.version != SPATIAL_RENDER_CONTRACTS_VERSION:
            raise ValueError(f"unsupported render contracts version: {self.version}")
        if self.schema_version != SPATIAL_DEVICE_PROFILE_SCHEMA_VERSION:
            raise ValueError(f"unsupported device profile schema version: {self.schema_version}")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "profile_id": self.profile_id,
            "supported_renderers": [item.value for item in self.supported_renderers],
            "budget": self.budget.to_dict(),
            "accessibility_required": self.accessibility_required,
            "xr_user_activation": self.xr_user_activation,
            "network_allowed": self.network_allowed,
            "source_refs": list(self.source_refs),
            "metadata": _thaw_json(self.metadata),
            "fingerprinting_allowed": self.fingerprinting_allowed,
            "renderer_authority": self.renderer_authority,
            "execution_authority": self.execution_authority,
            "patch_authority": self.patch_authority,
            "version": self.version,
            "schema_version": self.schema_version,
        }
        return {**body, "device_profile_digest": stable_digest(body, digest_size=32)}

    @property
    def device_profile_digest(self) -> str:
        return self.to_dict()["device_profile_digest"]


@dataclass(frozen=True)
class SpatialRenderPlan(CanonicalSpatialRecord):
    plan_id: str
    scene_id: str
    scene_digest: str
    device_profile_digest: str
    selected_renderer: SpatialRendererKind | str
    fallback_renderers: tuple[SpatialRendererKind, ...]
    budget: SpatialRenderBudget
    scene_entity_count: int
    scene_link_count: int
    scene_asset_count: int
    scene_asset_bytes: int
    reasons: tuple[str, ...]
    source_refs: tuple[str, ...]
    accessible_fallback_required: bool = True
    xr_user_activation_observed: bool = False
    projection_only: bool = True
    renderer_authority: bool = False
    execution_authority: bool = False
    patch_authority: bool = False
    version: str = SPATIAL_RENDER_CONTRACTS_VERSION
    schema_version: str = SPATIAL_RENDER_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _identifier(self.plan_id, "render_plan.plan_id"))
        object.__setattr__(self, "scene_id", _identifier(self.scene_id, "render_plan.scene_id"))
        object.__setattr__(self, "scene_digest", _hex_digest_value(self.scene_digest, "render_plan.scene_digest"))
        object.__setattr__(
            self,
            "device_profile_digest",
            _hex_digest_value(self.device_profile_digest, "render_plan.device_profile_digest"),
        )
        selected = _enum(self.selected_renderer, SpatialRendererKind, "render_plan.selected_renderer")
        assert isinstance(selected, SpatialRendererKind)
        object.__setattr__(self, "selected_renderer", selected)
        fallbacks = _renderer_tuple(
            self.fallback_renderers,
            "render_plan.fallback_renderers",
            canonical_set=False,
        )
        if selected in fallbacks:
            raise ValueError("selected renderer cannot also be a fallback")
        if selected is not SpatialRendererKind.ACCESSIBLE_2D and SpatialRendererKind.ACCESSIBLE_2D not in fallbacks:
            raise ValueError("render plans require an ACCESSIBLE_2D fallback")
        object.__setattr__(self, "fallback_renderers", fallbacks)
        if not isinstance(self.budget, SpatialRenderBudget):
            raise ValueError("render_plan.budget must be a SpatialRenderBudget")
        for field_name, maximum in (
            ("scene_entity_count", 1_000_000),
            ("scene_link_count", 4_000_000),
            ("scene_asset_count", 100_000),
            ("scene_asset_bytes", 1_099_511_627_776),
        ):
            object.__setattr__(
                self,
                field_name,
                _bounded_int(getattr(self, field_name), f"render_plan.{field_name}", minimum=0, maximum=maximum),
            )
        if self.scene_entity_count > self.budget.max_entities:
            raise ValueError("scene entity count exceeds the render plan budget")
        if self.scene_link_count > self.budget.max_links:
            raise ValueError("scene link count exceeds the render plan budget")
        if self.scene_asset_count > self.budget.max_assets:
            raise ValueError("scene asset count exceeds the render plan budget")
        if self.scene_asset_bytes > self.budget.max_asset_bytes:
            raise ValueError("scene asset bytes exceed the render plan budget")
        reasons = _bounded_strings(
            self.reasons,
            "render_plan.reasons",
            max_items=32,
            max_item_bytes=512,
            max_total_bytes=8192,
        )
        if not reasons:
            raise ValueError("render_plan.reasons must not be empty")
        object.__setattr__(self, "reasons", reasons)
        refs = _bounded_strings(
            self.source_refs,
            "render_plan.source_refs",
            max_items=256,
            max_item_bytes=2048,
            max_total_bytes=65_536,
            canonical=True,
        )
        if not refs:
            raise ValueError("render_plan.source_refs must not be empty")
        object.__setattr__(self, "source_refs", refs)
        for field_name in (
            "accessible_fallback_required",
            "xr_user_activation_observed",
            "projection_only",
            "renderer_authority",
            "execution_authority",
            "patch_authority",
        ):
            object.__setattr__(
                self,
                field_name,
                _strict_bool(getattr(self, field_name), f"render_plan.{field_name}"),
            )
        if not self.accessible_fallback_required or not self.projection_only:
            raise ValueError("render plans must remain accessible and projection-only")
        if self.selected_renderer is SpatialRendererKind.WEBXR and not self.xr_user_activation_observed:
            raise ValueError("WEBXR selection requires observed user activation")
        if self.renderer_authority or self.execution_authority or self.patch_authority:
            raise ValueError("render plans cannot carry renderer, execution, or patch authority")
        if self.version != SPATIAL_RENDER_CONTRACTS_VERSION:
            raise ValueError(f"unsupported render contracts version: {self.version}")
        if self.schema_version != SPATIAL_RENDER_PLAN_SCHEMA_VERSION:
            raise ValueError(f"unsupported render plan schema version: {self.schema_version}")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "plan_id": self.plan_id,
            "scene_id": self.scene_id,
            "scene_digest": self.scene_digest,
            "device_profile_digest": self.device_profile_digest,
            "selected_renderer": self.selected_renderer.value,
            "fallback_renderers": [item.value for item in self.fallback_renderers],
            "budget": self.budget.to_dict(),
            "scene_entity_count": self.scene_entity_count,
            "scene_link_count": self.scene_link_count,
            "scene_asset_count": self.scene_asset_count,
            "scene_asset_bytes": self.scene_asset_bytes,
            "reasons": list(self.reasons),
            "source_refs": list(self.source_refs),
            "accessible_fallback_required": self.accessible_fallback_required,
            "xr_user_activation_observed": self.xr_user_activation_observed,
            "projection_only": self.projection_only,
            "renderer_authority": self.renderer_authority,
            "execution_authority": self.execution_authority,
            "patch_authority": self.patch_authority,
            "version": self.version,
            "schema_version": self.schema_version,
        }
        return {**body, "render_plan_digest": stable_digest(body, digest_size=32)}

    @property
    def render_plan_digest(self) -> str:
        return self.to_dict()["render_plan_digest"]


@dataclass(frozen=True)
class SpatialRenderReceipt(CanonicalSpatialRecord):
    receipt_id: str
    scene_id: str
    scene_digest: str
    plan_id: str
    render_plan_digest: str
    device_profile_digest: str
    renderer: SpatialRendererKind | str
    outcome: SpatialRenderOutcome | str
    evidence_class: SpatialRenderEvidenceClass | str
    sequence: int
    metrics: tuple[tuple[str, Any], ...]
    source_refs: tuple[str, ...]
    renderer_disposed: bool = False
    projection_only: bool = True
    renderer_authority: bool = False
    execution_authority: bool = False
    patch_authority: bool = False
    version: str = SPATIAL_RENDER_CONTRACTS_VERSION
    schema_version: str = SPATIAL_RENDER_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _identifier(self.receipt_id, "render_receipt.receipt_id"))
        object.__setattr__(self, "scene_id", _identifier(self.scene_id, "render_receipt.scene_id"))
        object.__setattr__(self, "scene_digest", _hex_digest_value(self.scene_digest, "render_receipt.scene_digest"))
        object.__setattr__(self, "plan_id", _identifier(self.plan_id, "render_receipt.plan_id"))
        object.__setattr__(
            self,
            "render_plan_digest",
            _hex_digest_value(self.render_plan_digest, "render_receipt.render_plan_digest"),
        )
        object.__setattr__(
            self,
            "device_profile_digest",
            _hex_digest_value(self.device_profile_digest, "render_receipt.device_profile_digest"),
        )
        object.__setattr__(self, "renderer", _enum(self.renderer, SpatialRendererKind, "render_receipt.renderer"))
        object.__setattr__(self, "outcome", _enum(self.outcome, SpatialRenderOutcome, "render_receipt.outcome"))
        object.__setattr__(
            self,
            "evidence_class",
            _enum(self.evidence_class, SpatialRenderEvidenceClass, "render_receipt.evidence_class"),
        )
        object.__setattr__(self, "sequence", _bounded_int(self.sequence, "render_receipt.sequence", minimum=0))
        object.__setattr__(self, "metrics", _projection_metadata(self.metrics, "render_receipt.metrics"))
        refs = _bounded_strings(
            self.source_refs,
            "render_receipt.source_refs",
            max_items=256,
            max_item_bytes=2048,
            max_total_bytes=65_536,
            canonical=True,
        )
        if not refs:
            raise ValueError("render_receipt.source_refs must not be empty")
        object.__setattr__(self, "source_refs", refs)
        for field_name in (
            "renderer_disposed",
            "projection_only",
            "renderer_authority",
            "execution_authority",
            "patch_authority",
        ):
            object.__setattr__(
                self,
                field_name,
                _strict_bool(getattr(self, field_name), f"render_receipt.{field_name}"),
            )
        if not self.projection_only:
            raise ValueError("render receipts must remain projection-only")
        if self.renderer_authority or self.execution_authority or self.patch_authority:
            raise ValueError("render receipts cannot carry renderer, execution, or patch authority")
        if self.version != SPATIAL_RENDER_CONTRACTS_VERSION:
            raise ValueError(f"unsupported render contracts version: {self.version}")
        if self.schema_version != SPATIAL_RENDER_RECEIPT_SCHEMA_VERSION:
            raise ValueError(f"unsupported render receipt schema version: {self.schema_version}")

    def to_dict(self) -> dict[str, Any]:
        body = {
            "receipt_id": self.receipt_id,
            "scene_id": self.scene_id,
            "scene_digest": self.scene_digest,
            "plan_id": self.plan_id,
            "render_plan_digest": self.render_plan_digest,
            "device_profile_digest": self.device_profile_digest,
            "renderer": self.renderer.value,
            "outcome": self.outcome.value,
            "evidence_class": self.evidence_class.value,
            "sequence": self.sequence,
            "metrics": _thaw_json(self.metrics),
            "source_refs": list(self.source_refs),
            "renderer_disposed": self.renderer_disposed,
            "projection_only": self.projection_only,
            "renderer_authority": self.renderer_authority,
            "execution_authority": self.execution_authority,
            "patch_authority": self.patch_authority,
            "version": self.version,
            "schema_version": self.schema_version,
        }
        return {**body, "render_receipt_digest": stable_digest(body, digest_size=32)}

    @property
    def render_receipt_digest(self) -> str:
        return self.to_dict()["render_receipt_digest"]


@dataclass(frozen=True)
class SpatialProjectionSessionSummary(CanonicalSpatialRecord):
    session_id: str
    scene_id: str
    scene_digest: str
    plan_id: str
    render_plan_digest: str
    renderer: SpatialRendererKind | str
    state: SpatialSessionState | str
    created_sequence: int
    updated_sequence: int
    render_receipt_ids: tuple[str, ...] = ()
    cancellation_reason: str = ""
    source_refs: tuple[str, ...] = ()
    active: bool = False
    ephemeral: bool = True
    raw_sensor_data_retained: bool = False
    renderer_authority: bool = False
    execution_authority: bool = False
    patch_authority: bool = False
    version: str = SPATIAL_RENDER_CONTRACTS_VERSION
    schema_version: str = SPATIAL_SESSION_SUMMARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _identifier(self.session_id, "session.session_id"))
        object.__setattr__(self, "scene_id", _identifier(self.scene_id, "session.scene_id"))
        object.__setattr__(self, "scene_digest", _hex_digest_value(self.scene_digest, "session.scene_digest"))
        object.__setattr__(self, "plan_id", _identifier(self.plan_id, "session.plan_id"))
        object.__setattr__(
            self,
            "render_plan_digest",
            _hex_digest_value(self.render_plan_digest, "session.render_plan_digest"),
        )
        object.__setattr__(self, "renderer", _enum(self.renderer, SpatialRendererKind, "session.renderer"))
        state = _enum(self.state, SpatialSessionState, "session.state")
        assert isinstance(state, SpatialSessionState)
        object.__setattr__(self, "state", state)
        created = _bounded_int(self.created_sequence, "session.created_sequence", minimum=0)
        updated = _bounded_int(self.updated_sequence, "session.updated_sequence", minimum=created)
        object.__setattr__(self, "created_sequence", created)
        object.__setattr__(self, "updated_sequence", updated)
        object.__setattr__(
            self,
            "render_receipt_ids",
            _bounded_identifiers(
                self.render_receipt_ids,
                "session.render_receipt_ids",
                max_items=256,
            ),
        )
        object.__setattr__(
            self,
            "cancellation_reason",
            _optional_text(self.cancellation_reason, "session.cancellation_reason"),
        )
        object.__setattr__(
            self,
            "source_refs",
            _bounded_strings(
                self.source_refs,
                "session.source_refs",
                max_items=256,
                max_item_bytes=2048,
                max_total_bytes=65_536,
                canonical=True,
            ),
        )
        for field_name in (
            "active",
            "ephemeral",
            "raw_sensor_data_retained",
            "renderer_authority",
            "execution_authority",
            "patch_authority",
        ):
            object.__setattr__(
                self,
                field_name,
                _strict_bool(getattr(self, field_name), f"session.{field_name}"),
            )
        if self.active != (state is SpatialSessionState.ACTIVE):
            raise ValueError("session.active must match ACTIVE state exactly")
        if not self.ephemeral or self.raw_sensor_data_retained:
            raise ValueError("projection sessions must be ephemeral and retain no raw sensor data")
        if self.renderer_authority or self.execution_authority or self.patch_authority:
            raise ValueError("projection sessions cannot carry renderer, execution, or patch authority")
        if self.version != SPATIAL_RENDER_CONTRACTS_VERSION:
            raise ValueError(f"unsupported render contracts version: {self.version}")
        if self.schema_version != SPATIAL_SESSION_SUMMARY_SCHEMA_VERSION:
            raise ValueError(f"unsupported session summary schema version: {self.schema_version}")

    def to_dict(self) -> dict[str, Any]:
        body = super().to_dict()
        body["renderer"] = self.renderer.value
        body["state"] = self.state.value
        return {**body, "session_digest": stable_digest(body, digest_size=32)}

    @property
    def session_digest(self) -> str:
        return self.to_dict()["session_digest"]


@dataclass(frozen=True)
class SpatialDissolutionReceipt(CanonicalSpatialRecord):
    receipt_id: str
    session_id: str
    scene_digest: str
    render_plan_digest: str
    terminal_state: SpatialSessionState | str
    reason_code: str
    sequence: int
    render_receipt_ids: tuple[str, ...] = ()
    released_asset_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    renderer_disposed: bool = True
    leases_released: bool = True
    raw_sensor_data_retained: bool = False
    production_mutation: bool = False
    automatic_merge: bool = False
    renderer_authority: bool = False
    execution_authority: bool = False
    patch_authority: bool = False
    version: str = SPATIAL_RENDER_CONTRACTS_VERSION
    schema_version: str = SPATIAL_DISSOLUTION_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _identifier(self.receipt_id, "dissolution.receipt_id"))
        object.__setattr__(self, "session_id", _identifier(self.session_id, "dissolution.session_id"))
        object.__setattr__(
            self,
            "scene_digest",
            _hex_digest_value(self.scene_digest, "dissolution.scene_digest"),
        )
        object.__setattr__(
            self,
            "render_plan_digest",
            _hex_digest_value(self.render_plan_digest, "dissolution.render_plan_digest"),
        )
        state = _enum(self.terminal_state, SpatialSessionState, "dissolution.terminal_state")
        assert isinstance(state, SpatialSessionState)
        if state not in {
            SpatialSessionState.CANCELLED,
            SpatialSessionState.FAILED,
            SpatialSessionState.DISSOLVED,
        }:
            raise ValueError("dissolution.terminal_state must be terminal")
        object.__setattr__(self, "terminal_state", state)
        object.__setattr__(self, "reason_code", _identifier(self.reason_code, "dissolution.reason_code"))
        object.__setattr__(self, "sequence", _bounded_int(self.sequence, "dissolution.sequence", minimum=0))
        object.__setattr__(
            self,
            "render_receipt_ids",
            _bounded_identifiers(
                self.render_receipt_ids,
                "dissolution.render_receipt_ids",
                max_items=256,
            ),
        )
        object.__setattr__(
            self,
            "released_asset_ids",
            _bounded_identifiers(
                self.released_asset_ids,
                "dissolution.released_asset_ids",
                max_items=4096,
                canonical=True,
            ),
        )
        refs = _bounded_strings(
            self.source_refs,
            "dissolution.source_refs",
            max_items=256,
            max_item_bytes=2048,
            max_total_bytes=65_536,
            canonical=True,
        )
        if not refs:
            raise ValueError("dissolution.source_refs must not be empty")
        object.__setattr__(self, "source_refs", refs)
        for field_name in (
            "renderer_disposed",
            "leases_released",
            "raw_sensor_data_retained",
            "production_mutation",
            "automatic_merge",
            "renderer_authority",
            "execution_authority",
            "patch_authority",
        ):
            object.__setattr__(
                self,
                field_name,
                _strict_bool(getattr(self, field_name), f"dissolution.{field_name}"),
            )
        if not self.renderer_disposed or not self.leases_released:
            raise ValueError("dissolution receipts require renderer and lease release")
        if (
            self.raw_sensor_data_retained
            or self.production_mutation
            or self.automatic_merge
            or self.renderer_authority
            or self.execution_authority
            or self.patch_authority
        ):
            raise ValueError("dissolution receipts cannot retain data or authority")
        if self.version != SPATIAL_RENDER_CONTRACTS_VERSION:
            raise ValueError(f"unsupported render contracts version: {self.version}")
        if self.schema_version != SPATIAL_DISSOLUTION_RECEIPT_SCHEMA_VERSION:
            raise ValueError(f"unsupported dissolution receipt schema version: {self.schema_version}")

    def to_dict(self) -> dict[str, Any]:
        body = super().to_dict()
        body["terminal_state"] = self.terminal_state.value
        return {**body, "dissolution_digest": stable_digest(body, digest_size=32)}

    @property
    def dissolution_digest(self) -> str:
        return self.to_dict()["dissolution_digest"]


@dataclass(frozen=True)
class SpatialInteractionIntent(CanonicalSpatialRecord):
    interaction_id: str
    scene_id: str
    scene_digest: str
    action: SpatialInteractionAction | str
    target_entity_ids: tuple[str, ...]
    intent_slots: tuple[tuple[str, Any], ...]
    source_refs: tuple[str, ...]
    review_only: bool = True
    requires_forge: bool = False
    execution_authority: bool = False
    patch_authority: bool = False
    metadata: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "interaction_id",
            _identifier(self.interaction_id, "interaction.interaction_id"),
        )
        object.__setattr__(
            self,
            "scene_id",
            _identifier(self.scene_id, "interaction.scene_id"),
        )
        digest = _required(self.scene_digest, "interaction.scene_digest").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("interaction.scene_digest must be a 64-character hex digest")
        object.__setattr__(self, "scene_digest", digest)
        object.__setattr__(
            self,
            "action",
            _enum(self.action, SpatialInteractionAction, "interaction.action"),
        )
        targets = _identifiers(
            self.target_entity_ids,
            "interaction.target_entity_ids",
        )
        if not targets:
            raise ValueError("interaction.target_entity_ids must not be empty")
        object.__setattr__(self, "target_entity_ids", targets)
        slots = _metadata(self.intent_slots, "interaction.intent_slots")
        slot_keys = {key for key, _ in slots}
        expected = {"DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"}
        if slot_keys != expected:
            raise ValueError("interaction.intent_slots must contain exactly the six Aura slots")
        object.__setattr__(self, "intent_slots", slots)
        refs = _strings(self.source_refs, "interaction.source_refs")
        if not refs:
            raise ValueError("interaction.source_refs must not be empty")
        object.__setattr__(self, "source_refs", refs)
        object.__setattr__(
            self,
            "review_only",
            _strict_bool(self.review_only, "interaction.review_only"),
        )
        if not self.review_only:
            raise ValueError("spatial interactions must remain review-only")
        object.__setattr__(
            self,
            "requires_forge",
            _strict_bool(self.requires_forge, "interaction.requires_forge"),
        )
        object.__setattr__(
            self,
            "execution_authority",
            _strict_bool(
                self.execution_authority,
                "interaction.execution_authority",
            ),
        )
        object.__setattr__(
            self,
            "patch_authority",
            _strict_bool(self.patch_authority, "interaction.patch_authority"),
        )
        if self.execution_authority or self.patch_authority:
            raise ValueError("spatial interactions cannot carry execution or patch authority")
        if self.action is SpatialInteractionAction.PREPARE_REPAIR_REQUEST and not self.requires_forge:
            raise ValueError("repair preparation interactions must require Aura Forge")
        object.__setattr__(
            self,
            "metadata",
            _metadata(self.metadata, "interaction.metadata"),
        )


__all__ = [
    "MAX_SPATIAL_METADATA_BYTES",
    "PATCH_AUTHORITY",
    "SPATIAL_CONTRACTS_VERSION",
    "SPATIAL_DEVICE_PROFILE_SCHEMA_VERSION",
    "SPATIAL_DISSOLUTION_RECEIPT_SCHEMA_VERSION",
    "SPATIAL_EXECUTION_AUTHORITY",
    "SPATIAL_RENDER_CONTRACTS_VERSION",
    "SPATIAL_RENDER_PLAN_SCHEMA_VERSION",
    "SPATIAL_RENDER_RECEIPT_SCHEMA_VERSION",
    "SPATIAL_SCENE_SCHEMA_VERSION",
    "SPATIAL_SESSION_SUMMARY_SCHEMA_VERSION",
    "VSA_PATCH_AUTHORITY",
    "CoordinateFrame",
    "Handedness",
    "SpatialAssetManifest",
    "SpatialAssetType",
    "SpatialDeviceProfile",
    "SpatialDissolutionReceipt",
    "SpatialEntity",
    "SpatialEntityType",
    "SpatialInteractionAction",
    "SpatialInteractionIntent",
    "SpatialLink",
    "SpatialProjectionSessionSummary",
    "SpatialRenderBudget",
    "SpatialRenderEvidenceClass",
    "SpatialRenderOutcome",
    "SpatialRenderPlan",
    "SpatialRenderReceipt",
    "SpatialRendererKind",
    "SpatialSceneSnapshot",
    "SpatialSessionState",
    "SpatialTruthClass",
    "UpAxis",
]
