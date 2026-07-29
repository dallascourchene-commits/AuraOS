"""Pinned Pascal presentation compatibility boundary for Aura Spatial Foundry PR 2.

The module owns only disposable presentation-session state and exact bridge
validation. ConstructionProjectState, Spatial scene truth, evidence, guarded
routing, approval, learning, persistence, and physical-work authority remain
with their canonical Aura owners.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
import re
import secrets
from typing import Any

from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialEntity,
    SpatialEntityType,
    SpatialInteractionAction,
    SpatialSceneSnapshot,
    SpatialTruthClass,
)
from aura_spatial_interaction import compile_spatial_interaction

PASCAL_REPOSITORY = "pascalorg/editor"
PASCAL_COMMIT = "42ac4be1ce5f3fee74806aa093267b6fee77d47d"
PASCAL_LICENSE = "MIT"
PASCAL_SOURCE_LOCK_VERSION = "AURA_PASCAL_SOURCE_LOCK_V1"
PASCAL_SCENE_ARTIFACT_VERSION = "AURA_PASCAL_SCENE_ARTIFACT_MANIFEST_V1"
PASCAL_COORDINATE_RECEIPT_VERSION = "AURA_PASCAL_COORDINATE_RECEIPT_V1"
PASCAL_PRESENTATION_BRIDGE_VERSION = "AURA_PASCAL_PRESENTATION_BRIDGE_V1"
PASCAL_PRESENTATION_WFST_VERSION = "AURA_PASCAL_PRESENTATION_WFST_EXTENSION_V1"
PASCAL_PRESENTATION_SESSION_VERSION = "AURA_PASCAL_PRESENTATION_SESSION_V1"
MAX_BRIDGE_PAYLOAD_BYTES = 262_144
MAX_BRIDGE_DEPTH = 16
MAX_RETAINED_NONCES = 1_024
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_ORIGIN = re.compile(r"^https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_AUTHORITY_TOKENS = frozenset(
    {
        "approval",
        "authorization",
        "automaticcommit",
        "automaticexecution",
        "automaticmerge",
        "automaticpullrequest",
        "automaticpush",
        "constructiontruth",
        "deployment",
        "executionauthority",
        "learningpromotion",
        "merge",
        "patchauthority",
        "paymentreleased",
        "physicalworkauthorized",
        "professionalapproval",
        "productionmutation",
        "pullrequest",
        "push",
        "rendererauthority",
        "surveyauthority",
        "visualtruth",
    }
)


class PascalPresentationError(ValueError):
    """Fail-closed Pascal presentation contract error."""


class BridgeDirection(str, Enum):
    PARENT_TO_PASCAL = "PARENT_TO_PASCAL"
    PASCAL_TO_PARENT = "PASCAL_TO_PARENT"


class PascalBridgeAction(str, Enum):
    LOAD_ARTIFACT = "LOAD_ARTIFACT"
    SET_VIEW_2D = "SET_VIEW_2D"
    SET_VIEW_3D = "SET_VIEW_3D"
    SET_STOREY = "SET_STOREY"
    SET_SELECTION = "SET_SELECTION"
    SET_DIMENSIONS = "SET_DIMENSIONS"
    RESET_CAMERA = "RESET_CAMERA"
    DISSOLVE = "DISSOLVE"
    READY = "READY"
    LOAD_RECEIPT = "LOAD_RECEIPT"
    VIEW_STATE = "VIEW_STATE"
    SELECTION_CHANGED = "SELECTION_CHANGED"
    RENDER_RECEIPT = "RENDER_RECEIPT"
    PRESENTATION_ERROR = "PRESENTATION_ERROR"
    DISSOLUTION_RECEIPT = "DISSOLUTION_RECEIPT"


class PascalPresentationState(str, Enum):
    CREATED = "CREATED"
    READY = "READY"
    ACTIVE = "ACTIVE"
    DISSOLVING = "DISSOLVING"
    DISSOLVED = "DISSOLVED"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256(value: Any) -> str:
    encoded = value if isinstance(value, bytes) else _canonical_json(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_text(value: Any, name: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PascalPresentationError(f"{name} must be a non-empty string")
    text = value.strip()
    if len(text.encode("utf-8")) > maximum:
        raise PascalPresentationError(f"{name} exceeds {maximum} UTF-8 bytes")
    return text


def _identifier(value: Any, name: str) -> str:
    text = _required_text(value, name, maximum=192)
    if not _IDENTIFIER.fullmatch(text):
        raise PascalPresentationError(f"{name} contains unsupported characters")
    return text


def _hex40(value: Any, name: str) -> str:
    text = _required_text(value, name, maximum=40).lower()
    if not _HEX40.fullmatch(text):
        raise PascalPresentationError(f"{name} must be a 40-character lowercase hex digest")
    return text


def _hex64(value: Any, name: str) -> str:
    text = _required_text(value, name, maximum=64).lower()
    if not _HEX64.fullmatch(text):
        raise PascalPresentationError(f"{name} must be a 64-character lowercase hex digest")
    return text




def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _timestamp(value: Any, name: str = "sent_at") -> str:
    text = _required_text(value, name, maximum=32)
    if not _TIMESTAMP.fullmatch(text):
        raise PascalPresentationError(f"{name} must be an ISO-8601 UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise PascalPresentationError(f"{name} is not a valid UTC timestamp") from exc
    return text

def _strict_bool(value: Any, name: str, expected: bool) -> bool:
    if value is not expected:
        raise PascalPresentationError(f"{name} must remain {str(expected).lower()}")
    return expected


def _strict_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    supplied = set(value)
    if supplied != expected:
        raise PascalPresentationError(
            f"{name} keys mismatch; missing={sorted(expected - supplied)}, "
            f"unknown={sorted(supplied - expected)}"
        )


def _authority_path(value: Any, path: str = "payload", depth: int = 0) -> str | None:
    if depth > MAX_BRIDGE_DEPTH:
        raise PascalPresentationError(f"{path} exceeds {MAX_BRIDGE_DEPTH} nesting levels")
    if isinstance(value, Mapping):
        for key, child in value.items():
            token = re.sub(r"[^a-z0-9]+", "", str(key).casefold())
            child_path = f"{path}.{key}"
            if token in _AUTHORITY_TOKENS and child is not False:
                return child_path
            found = _authority_path(child, child_path, depth + 1)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found = _authority_path(child, f"{path}[{index}]", depth + 1)
            if found:
                return found
    return None


def _clean_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PascalPresentationError("payload must be an object")
    authority = _authority_path(value)
    if authority is not None:
        raise PascalPresentationError(f"bridge payload cannot supply authority field: {authority}")
    try:
        encoded = _canonical_json(value).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise PascalPresentationError("payload must be bounded JSON") from exc
    if len(encoded) > MAX_BRIDGE_PAYLOAD_BYTES:
        raise PascalPresentationError("payload exceeds the bridge byte ceiling")
    return json.loads(encoded.decode("utf-8"))


@dataclass(frozen=True)
class PascalPackagePin:
    name: str
    version: str
    package_json_blob_sha1: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "package.name", maximum=128))
        object.__setattr__(self, "version", _required_text(self.version, "package.version", maximum=64))
        object.__setattr__(
            self,
            "package_json_blob_sha1",
            _hex40(self.package_json_blob_sha1, "package.package_json_blob_sha1"),
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PascalPackagePin":
        _strict_keys(value, {field.name for field in fields(cls)}, "PascalPackagePin")
        return cls(**dict(value))


@dataclass(frozen=True)
class PascalSourceLock:
    packages: tuple[PascalPackagePin, ...]
    local_assets: tuple[tuple[str, str], ...]
    repository: str = PASCAL_REPOSITORY
    commit: str = PASCAL_COMMIT
    license: str = PASCAL_LICENSE
    external_asset_fetch: bool = False
    remote_plugin_fetch: bool = False
    persistent_canonical_storage: bool = False
    version: str = PASCAL_SOURCE_LOCK_VERSION
    lock_digest: str = ""

    def __post_init__(self) -> None:
        if self.repository != PASCAL_REPOSITORY:
            raise PascalPresentationError("Pascal repository pin differs from the approved source")
        if self.commit != PASCAL_COMMIT:
            raise PascalPresentationError("Pascal commit pin differs from the approved baseline")
        if self.license != PASCAL_LICENSE:
            raise PascalPresentationError("Pascal license must remain MIT")
        if self.version != PASCAL_SOURCE_LOCK_VERSION:
            raise PascalPresentationError("unsupported Pascal source-lock version")
        for name in ("external_asset_fetch", "remote_plugin_fetch", "persistent_canonical_storage"):
            _strict_bool(getattr(self, name), f"source_lock.{name}", False)
        if not isinstance(self.packages, tuple) or not self.packages:
            raise PascalPresentationError("source_lock.packages must be a non-empty tuple")
        if not all(isinstance(item, PascalPackagePin) for item in self.packages):
            raise PascalPresentationError("source_lock.packages contains an invalid package pin")
        if len({item.name for item in self.packages}) != len(self.packages):
            raise PascalPresentationError("source_lock.packages must not duplicate package names")
        assets: list[tuple[str, str]] = []
        for index, item in enumerate(self.local_assets):
            if not isinstance(item, tuple) or len(item) != 2:
                raise PascalPresentationError(f"source_lock.local_assets[{index}] must be a path/digest pair")
            path = _required_text(item[0], f"source_lock.local_assets[{index}].path", maximum=512)
            if path.startswith("/") or ".." in path.split("/"):
                raise PascalPresentationError("local asset paths must remain repository-relative")
            assets.append((path, _hex64(item[1], f"source_lock.local_assets[{index}].sha256")))
        if len({item[0] for item in assets}) != len(assets):
            raise PascalPresentationError("source_lock.local_assets must not duplicate paths")
        object.__setattr__(self, "local_assets", tuple(sorted(assets)))
        expected = _sha256(self._body())
        supplied = _hex64(self.lock_digest, "source_lock.lock_digest")
        if supplied != expected:
            raise PascalPresentationError("Pascal source-lock digest is invalid")

    def _body(self) -> dict[str, Any]:
        return {
            "packages": [asdict(item) for item in self.packages],
            "local_assets": [{"path": path, "sha256": digest} for path, digest in self.local_assets],
            "repository": self.repository,
            "commit": self.commit,
            "license": self.license,
            "external_asset_fetch": self.external_asset_fetch,
            "remote_plugin_fetch": self.remote_plugin_fetch,
            "persistent_canonical_storage": self.persistent_canonical_storage,
            "version": self.version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "lock_digest": self.lock_digest}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PascalSourceLock":
        expected = {
            "packages",
            "local_assets",
            "repository",
            "commit",
            "license",
            "external_asset_fetch",
            "remote_plugin_fetch",
            "persistent_canonical_storage",
            "version",
            "lock_digest",
        }
        _strict_keys(value, expected, "PascalSourceLock")
        packages_raw = value["packages"]
        assets_raw = value["local_assets"]
        if isinstance(packages_raw, (str, bytes, bytearray)) or not isinstance(packages_raw, Sequence):
            raise PascalPresentationError("source_lock.packages must be an array")
        if isinstance(assets_raw, (str, bytes, bytearray)) or not isinstance(assets_raw, Sequence):
            raise PascalPresentationError("source_lock.local_assets must be an array")
        if any(not isinstance(item, Mapping) for item in packages_raw):
            raise PascalPresentationError("source_lock.packages rows must be objects")
        if any(not isinstance(item, Mapping) for item in assets_raw):
            raise PascalPresentationError("source_lock.local_assets rows must be objects")
        return cls(
            packages=tuple(PascalPackagePin.from_mapping(item) for item in packages_raw),
            local_assets=tuple(
                (
                    _required_text(item.get("path"), "local_asset.path", maximum=512),
                    _hex64(item.get("sha256"), "local_asset.sha256"),
                )
                for item in assets_raw
            ),
            repository=value["repository"],
            commit=value["commit"],
            license=value["license"],
            external_asset_fetch=value["external_asset_fetch"],
            remote_plugin_fetch=value["remote_plugin_fetch"],
            persistent_canonical_storage=value["persistent_canonical_storage"],
            version=value["version"],
            lock_digest=value["lock_digest"],
        )

__all__ = ['Any', 'BridgeDirection', 'Callable', 'CoordinateFrame', 'Enum', 'MAX_BRIDGE_DEPTH', 'MAX_BRIDGE_PAYLOAD_BYTES', 'MAX_RETAINED_NONCES', 'Mapping', 'OrderedDict', 'PASCAL_COMMIT', 'PASCAL_COORDINATE_RECEIPT_VERSION', 'PASCAL_LICENSE', 'PASCAL_PRESENTATION_BRIDGE_VERSION', 'PASCAL_PRESENTATION_SESSION_VERSION', 'PASCAL_PRESENTATION_WFST_VERSION', 'PASCAL_REPOSITORY', 'PASCAL_SCENE_ARTIFACT_VERSION', 'PASCAL_SOURCE_LOCK_VERSION', 'PascalBridgeAction', 'PascalPackagePin', 'PascalPresentationError', 'PascalPresentationState', 'PascalSourceLock', 'Sequence', 'SpatialEntity', 'SpatialEntityType', 'SpatialInteractionAction', 'SpatialSceneSnapshot', 'SpatialTruthClass', '_AUTHORITY_TOKENS', '_HEX40', '_HEX64', '_IDENTIFIER', '_ORIGIN', '_TIMESTAMP', '_authority_path', '_canonical_json', '_clean_payload', '_hex40', '_hex64', '_identifier', '_required_text', '_sha256', '_strict_bool', '_strict_keys', '_timestamp', '_utc_timestamp', 'annotations', 'asdict', 'compile_spatial_interaction', 'dataclass', 'datetime', 'fields', 'hashlib', 'json', 'math', 're', 'secrets', 'timezone']
