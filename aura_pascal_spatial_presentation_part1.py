"""Pinned Pascal presentation compatibility boundary for Aura Spatial Foundry PR 2.

This module defines exact source identity and bounded bridge primitives. It owns no
Construction truth, approval, persistence, patching, execution, or learning authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
import re
import struct
from typing import Any

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
MAX_RETAINED_NONCES = 4_096
MAX_SESSION_MESSAGES = MAX_RETAINED_NONCES
MAX_SAFE_INTEGER = 9_007_199_254_740_991

APPROVED_PASCAL_PACKAGES = (
    ("@pascal-app/core", "0.9.2", "ada4f58be5494e031675a40663471a24afdfc3f0"),
    ("@pascal-app/viewer", "0.9.2", "86565ea117ff1fe666f1b7e93d3c40d105f502df"),
    ("@pascal-app/editor", "0.9.2", "73d5899ffe7d80342e06f37b9cda877ffb51a768"),
    ("@pascal-app/nodes", "0.1.1", "a9eb033b1ad277cd6d0d8712bb696f01a132d487"),
)
APPROVED_LOCAL_ASSET_PATHS = frozenset(
    {
        "aura_showcase/pascal-construction-foundry.css",
        "aura_showcase/pascal-construction-foundry.js",
        "aura_showcase/pascal-workbench/fixture.json",
        "aura_showcase/pascal-workbench/index.html",
        "aura_showcase/pascal-workbench/pascal-workbench.css",
        "aura_showcase/pascal-workbench/pascal-workbench.js",
        "third_party/pascal/LICENSE",
        "third_party/pascal/package-metadata/core.package.json",
        "third_party/pascal/package-metadata/editor.package.json",
        "third_party/pascal/package-metadata/nodes.package.json",
        "third_party/pascal/package-metadata/viewer.package.json",
    }
)
# Replaced after the final local-asset hashes are computed.
PASCAL_APPROVED_LOCK_DIGEST = "672611b98aca61e3ad7a4ebcb32f278916d09d876e663452bb654610562d2e87"

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_ORIGIN = re.compile(r"^https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_BRIDGE_KEY = re.compile(r"^[\x20-\x7e]{1,256}$")

# Keep this vocabulary aligned with Aura's canonical Spatial interaction guard.
_AUTHORITY_TOKENS = frozenset(
    {
        "accessgranted",
        "approval",
        "authorization",
        "authoritydecision",
        "automaticcommit",
        "automaticexecution",
        "automaticfix",
        "automaticmerge",
        "automaticpullrequest",
        "automaticpush",
        "capabilitylease",
        "constructiontruth",
        "deployment",
        "executionauthority",
        "learningpromotion",
        "lease",
        "leaseid",
        "merge",
        "patchauthority",
        "paymentreleased",
        "physicalworkauthorized",
        "professionalapproval",
        "productionmutation",
        "promotion",
        "pullrequest",
        "push",
        "renderauthority",
        "rendererauthority",
        "rendererinputisauthority",
        "surveyauthority",
        "verifierreceipt",
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


def canonical_json(value: Any) -> str:
    """Return the repository's ordinary canonical JSON form for persisted contracts."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_digest(value: Any) -> str:
    """Hash bytes directly or ordinary canonical JSON for persisted contract identities."""
    encoded = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bridge_encode(value: Any, *, depth: int = 0) -> bytes:
    """Encode JSON values identically in Python and JavaScript.

    Numbers are type-tagged and non-integer floats use exact IEEE-754 bytes, avoiding
    JSON serializer exponent/negative-zero differences between runtimes.
    """
    if depth > MAX_BRIDGE_DEPTH:
        raise PascalPresentationError(
            f"bridge value exceeds MAX_BRIDGE_DEPTH={MAX_BRIDGE_DEPTH}"
        )
    if value is None:
        return b"n"
    if type(value) is bool:
        return b"b1" if value else b"b0"
    if type(value) is int:
        if abs(value) > MAX_SAFE_INTEGER:
            raise PascalPresentationError("bridge integer exceeds the cross-runtime safe range")
        return f"i{value};".encode("ascii")
    if type(value) is float:
        if not math.isfinite(value):
            raise PascalPresentationError("bridge numbers must be finite")
        if value.is_integer() and abs(value) <= MAX_SAFE_INTEGER:
            return f"i{int(value)};".encode("ascii")
        return b"f" + struct.pack(">d", value).hex().encode("ascii") + b";"
    if isinstance(value, str):
        encoded = value.encode("utf-8")
        return f"s{len(encoded)}:".encode("ascii") + encoded
    if isinstance(value, (list, tuple)):
        return b"[" + b"".join(_bridge_encode(item, depth=depth + 1) for item in value) + b"]"
    if isinstance(value, Mapping):
        rows: list[bytes] = []
        for raw_key in sorted(value, key=str):
            if not isinstance(raw_key, str) or not _BRIDGE_KEY.fullmatch(raw_key):
                raise PascalPresentationError("bridge object keys must be bounded printable ASCII strings")
            rows.append(_bridge_encode(raw_key, depth=depth + 1))
            rows.append(_bridge_encode(value[raw_key], depth=depth + 1))
        return b"{" + b"".join(rows) + b"}"
    raise PascalPresentationError(f"bridge value is not JSON-compatible: {type(value).__name__}")


def bridge_sha256(value: Any) -> str:
    """Hash the cross-runtime typed bridge encoding."""
    return hashlib.sha256(_bridge_encode(value)).hexdigest()


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
        raise PascalPresentationError(
            f"{path} exceeds MAX_BRIDGE_DEPTH={MAX_BRIDGE_DEPTH}"
        )
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
        raise PascalPresentationError("payload must be a mapping object")
    authority = _authority_path(value)
    if authority is not None:
        raise PascalPresentationError(f"bridge payload cannot supply authority field: {authority}")
    try:
        encoded = canonical_json(value).encode("utf-8")
        # Also validate every value against the cross-runtime digest grammar.
        _bridge_encode(value)
    except (TypeError, ValueError, RecursionError) as exc:
        if isinstance(exc, PascalPresentationError):
            raise
        raise PascalPresentationError("payload must be bounded JSON") from exc
    if len(encoded) > MAX_BRIDGE_PAYLOAD_BYTES:
        raise PascalPresentationError(
            f"payload exceeds MAX_BRIDGE_PAYLOAD_BYTES={MAX_BRIDGE_PAYLOAD_BYTES}"
        )
    decoded = json.loads(encoded.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise PascalPresentationError("payload must remain an object")
    return decoded


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
        if not isinstance(value, Mapping):
            raise PascalPresentationError("PascalPackagePin must be an object")
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
        actual_packages = tuple(
            sorted(
                (item.name, item.version, item.package_json_blob_sha1)
                for item in self.packages
            )
        )
        if actual_packages != tuple(sorted(APPROVED_PASCAL_PACKAGES)):
            raise PascalPresentationError("Pascal package identities differ from the approved source lock")

        assets: list[tuple[str, str]] = []
        for index, item in enumerate(self.local_assets):
            if not isinstance(item, tuple) or len(item) != 2:
                raise PascalPresentationError(
                    f"source_lock.local_assets[{index}] must be a path/digest pair"
                )
            path = _required_text(item[0], f"source_lock.local_assets[{index}].path", maximum=512)
            if path.startswith("/") or ".." in path.split("/"):
                raise PascalPresentationError("local asset paths must remain repository-relative")
            assets.append((path, _hex64(item[1], f"source_lock.local_assets[{index}].sha256")))
        if len({item[0] for item in assets}) != len(assets):
            raise PascalPresentationError("source_lock.local_assets must not duplicate paths")
        if {item[0] for item in assets} != APPROVED_LOCAL_ASSET_PATHS:
            raise PascalPresentationError("Pascal local asset set differs from the approved source lock")
        object.__setattr__(self, "local_assets", tuple(sorted(assets)))

        expected = sha256_digest(self._body())
        supplied = _hex64(self.lock_digest, "source_lock.lock_digest")
        if supplied != expected:
            raise PascalPresentationError("Pascal source-lock digest is invalid")
        if supplied != PASCAL_APPROVED_LOCK_DIGEST:
            raise PascalPresentationError(
                "Pascal source-lock digest differs from the trusted runtime anchor"
            )
        object.__setattr__(self, "lock_digest", supplied)

    def _body(self) -> dict[str, Any]:
        return {
            "packages": [asdict(item) for item in self.packages],
            "local_assets": [
                {"path": path, "sha256": digest}
                for path, digest in self.local_assets
            ],
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
        if not isinstance(value, Mapping):
            raise PascalPresentationError("PascalSourceLock must be an object")
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


__all__ = [
    "APPROVED_LOCAL_ASSET_PATHS",
    "APPROVED_PASCAL_PACKAGES",
    "BridgeDirection",
    "MAX_BRIDGE_DEPTH",
    "MAX_BRIDGE_PAYLOAD_BYTES",
    "MAX_RETAINED_NONCES",
    "MAX_SESSION_MESSAGES",
    "PASCAL_APPROVED_LOCK_DIGEST",
    "PASCAL_COMMIT",
    "PASCAL_COORDINATE_RECEIPT_VERSION",
    "PASCAL_LICENSE",
    "PASCAL_PRESENTATION_BRIDGE_VERSION",
    "PASCAL_PRESENTATION_SESSION_VERSION",
    "PASCAL_PRESENTATION_WFST_VERSION",
    "PASCAL_REPOSITORY",
    "PASCAL_SCENE_ARTIFACT_VERSION",
    "PASCAL_SOURCE_LOCK_VERSION",
    "PascalBridgeAction",
    "PascalPackagePin",
    "PascalPresentationError",
    "PascalPresentationState",
    "PascalSourceLock",
    "bridge_sha256",
    "canonical_json",
    "sha256_digest",
]
