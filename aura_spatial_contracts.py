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
MAX_SPATIAL_METADATA_BYTES = 65_536
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SPATIAL_EXECUTION_AUTHORITY = False

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_DIGEST = re.compile(r"^(?:sha256|blake2b-256):[0-9a-f]{64}$")


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
    result = tuple(
        _finite_number(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )
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
    """Freeze a JSON-compatible value into immutable tuples."""
    if isinstance(value, Mapping):
        return tuple(
            (str(key), _freeze_json(item, f"{field_name}.{key}"))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{field_name}[]") for item in value)
    if isinstance(value, (set, frozenset)):
        frozen = [_freeze_json(item, f"{field_name}[]") for item in value]
        return tuple(
            sorted(frozen, key=lambda item: canonical_json(_thaw_json(item)))
        )
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} contains a non-finite float")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ValueError(
        f"{field_name} contains a non-JSON value: {type(value).__name__}"
    )


def _thaw_json(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], str)
            for item in value
        ):
            return {key: _thaw_json(item) for key, item in value}
        return [_thaw_json(item) for item in value]
    return value


def _metadata(value: Any, field_name: str = "metadata") -> tuple[tuple[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, tuple) and all(
        isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
        for item in value
    ):
        value = {key: item for key, item in value}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    value = sanitize_payload(value)
    serialized = canonical_json(value).encode("utf-8")
    if len(serialized) > MAX_SPATIAL_METADATA_BYTES:
        raise ValueError(
            f"{field_name} exceeds the {MAX_SPATIAL_METADATA_BYTES}-byte limit"
        )
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
        object.__setattr__(
            self, "frame_id", _identifier(self.frame_id, "frame.frame_id")
        )
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
        object.__setattr__(
            self, "asset_id", _identifier(self.asset_id, "asset.asset_id")
        )
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
            raise ValueError(
                "asset.content_digest must be sha256:<64hex> or blake2b-256:<64hex>"
            )
        object.__setattr__(self, "content_digest", digest)
        if type(self.byte_length) is not int or self.byte_length < 0:
            raise ValueError("asset.byte_length must be a non-negative integer")
        object.__setattr__(
            self, "frame_id", _identifier(self.frame_id, "asset.frame_id")
        )
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
        object.__setattr__(
            self, "link_id", _identifier(self.link_id, "link.link_id")
        )
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
        if not isinstance(self.frames, tuple) or not all(
            isinstance(item, CoordinateFrame) for item in self.frames
        ):
            raise ValueError("scene.frames must be a tuple of CoordinateFrame records")
        if not self.frames:
            raise ValueError("scene.frames must not be empty")
        if not isinstance(self.assets, tuple) or not all(
            isinstance(item, SpatialAssetManifest) for item in self.assets
        ):
            raise ValueError(
                "scene.assets must be a tuple of SpatialAssetManifest records"
            )
        if not isinstance(self.entities, tuple) or not all(
            isinstance(item, SpatialEntity) for item in self.entities
        ):
            raise ValueError("scene.entities must be a tuple of SpatialEntity records")
        if not isinstance(self.links, tuple) or not all(
            isinstance(item, SpatialLink) for item in self.links
        ):
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
            raise ValueError(
                f"unsupported spatial contracts version: {self.version}"
            )
        if self.schema_version != SPATIAL_SCENE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported spatial scene schema version: {self.schema_version}"
            )

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
            raise ValueError(
                "interaction.scene_digest must be a 64-character hex digest"
            )
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
            raise ValueError(
                "interaction.intent_slots must contain exactly the six Aura slots"
            )
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
            raise ValueError(
                "spatial interactions cannot carry execution or patch authority"
            )
        if (
            self.action is SpatialInteractionAction.PREPARE_REPAIR_REQUEST
            and not self.requires_forge
        ):
            raise ValueError(
                "repair preparation interactions must require Aura Forge"
            )
        object.__setattr__(
            self,
            "metadata",
            _metadata(self.metadata, "interaction.metadata"),
        )


__all__ = [
    "CoordinateFrame",
    "Handedness",
    "MAX_SPATIAL_METADATA_BYTES",
    "PATCH_AUTHORITY",
    "SPATIAL_CONTRACTS_VERSION",
    "SPATIAL_EXECUTION_AUTHORITY",
    "SPATIAL_SCENE_SCHEMA_VERSION",
    "SpatialAssetManifest",
    "SpatialAssetType",
    "SpatialEntity",
    "SpatialEntityType",
    "SpatialInteractionAction",
    "SpatialInteractionIntent",
    "SpatialLink",
    "SpatialSceneSnapshot",
    "SpatialTruthClass",
    "UpAxis",
    "VSA_PATCH_AUTHORITY",
]
