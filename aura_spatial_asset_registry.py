"""Content-addressed, manifest-only asset registry for Aura spatial projections."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import hashlib
import hmac
from pathlib import PurePosixPath
import re
from typing import Any
from urllib.parse import unquote, urlparse

from aura_event_contracts import stable_digest
from aura_spatial_contracts import SpatialAssetManifest

SPATIAL_ASSET_REGISTRY_VERSION = "AURA_SPATIAL_ASSET_REGISTRY_V1"
_ALLOWED_REMOTE_SCHEMES = frozenset({"https"})
_SAFE_AUTHORITY = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class SpatialAssetValidationReport:
    ok: bool
    asset_id: str
    findings: tuple[dict[str, Any], ...]
    verified_content: bool
    manifest_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "asset_id": self.asset_id,
            "findings": [dict(item) for item in self.findings],
            "verified_content": self.verified_content,
            "manifest_digest": self.manifest_digest,
            "version": SPATIAL_ASSET_REGISTRY_VERSION,
        }


class SpatialAssetRegistry:
    """Immutable manifests only; this class never fetches or decodes assets."""

    def __init__(
        self,
        manifests: Iterable[SpatialAssetManifest] = (),
        *,
        allow_remote: bool = False,
    ) -> None:
        if type(allow_remote) is not bool:
            raise ValueError("allow_remote must be a boolean")
        by_id: dict[str, SpatialAssetManifest] = {}
        for manifest in manifests:
            if not isinstance(manifest, SpatialAssetManifest):
                raise ValueError("manifests must contain SpatialAssetManifest records")
            if manifest.asset_id in by_id:
                raise ValueError(f"duplicate spatial asset id: {manifest.asset_id}")
            report = validate_asset_manifest(
                manifest,
                allow_remote=allow_remote,
            )
            if not report.ok:
                codes = ", ".join(str(item["code"]) for item in report.findings)
                raise ValueError(f"invalid spatial asset {manifest.asset_id}: {codes}")
            by_id[manifest.asset_id] = manifest
        self._by_id = by_id
        self._registry_digest = stable_digest(
            [by_id[key].to_dict() for key in sorted(by_id)],
            digest_size=32,
        )

    @property
    def registry_digest(self) -> str:
        return self._registry_digest

    def get(self, asset_id: str) -> SpatialAssetManifest | None:
        return self._by_id.get(str(asset_id))

    def require(self, asset_id: str) -> SpatialAssetManifest:
        manifest = self.get(asset_id)
        if manifest is None:
            raise KeyError(f"unknown spatial asset: {asset_id}")
        return manifest

    def list_manifests(self) -> tuple[SpatialAssetManifest, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SPATIAL_ASSET_REGISTRY_VERSION,
            "registry_digest": self.registry_digest,
            "asset_count": len(self._by_id),
            "assets": [item.to_dict() for item in self.list_manifests()],
            "network_fetch": False,
            "asset_decode": False,
            "render_authority": False,
            "patch_authority": False,
        }


def validate_asset_manifest(
    manifest: SpatialAssetManifest,
    *,
    content: bytes | None = None,
    allow_remote: bool = False,
) -> SpatialAssetValidationReport:
    if not isinstance(manifest, SpatialAssetManifest):
        raise ValueError("manifest must be a SpatialAssetManifest")
    if type(allow_remote) is not bool:
        raise ValueError("allow_remote must be a boolean")

    findings: list[dict[str, Any]] = []
    _validate_uri(
        manifest.uri,
        allow_remote=allow_remote,
        findings=findings,
    )

    verified_content = False
    if content is not None:
        if not isinstance(content, bytes):
            raise ValueError("content must be bytes")
        if len(content) != manifest.byte_length:
            findings.append(
                _finding(
                    "ASSET_LENGTH_MISMATCH",
                    (f"manifest declares {manifest.byte_length} bytes but received {len(content)}"),
                )
            )
        expected_algorithm, expected_hex = manifest.content_digest.split(":", 1)
        if expected_algorithm == "sha256":
            observed = hashlib.sha256(content).hexdigest()
        elif expected_algorithm == "blake2b-256":
            observed = hashlib.blake2b(content, digest_size=32).hexdigest()
        else:
            observed = ""
            findings.append(
                _finding(
                    "UNSUPPORTED_CONTENT_DIGEST",
                    f"unsupported digest: {expected_algorithm}",
                )
            )
        if observed and not hmac.compare_digest(observed, expected_hex):
            findings.append(
                _finding(
                    "ASSET_DIGEST_MISMATCH",
                    "asset bytes do not match the content-addressed manifest",
                )
            )
        verified_content = not any(
            item["code"]
            in {
                "ASSET_LENGTH_MISMATCH",
                "ASSET_DIGEST_MISMATCH",
                "UNSUPPORTED_CONTENT_DIGEST",
            }
            for item in findings
        )

    findings.sort(key=lambda item: (str(item["code"]), str(item["message"])))
    return SpatialAssetValidationReport(
        ok=not findings,
        asset_id=manifest.asset_id,
        findings=tuple(findings),
        verified_content=verified_content,
        manifest_digest=manifest.digest,
    )


def _validate_uri(
    uri: str,
    *,
    allow_remote: bool,
    findings: list[dict[str, Any]],
) -> None:
    if any(ord(char) < 32 for char in uri) or "\\" in uri:
        findings.append(
            _finding(
                "UNSAFE_ASSET_PATH",
                "asset URI contains control characters or backslashes",
            )
        )
        return
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.params:
        findings.append(
            _finding(
                "UNSAFE_ASSET_URI_COMPONENTS",
                ("asset URI must not contain credentials, parameters, query, or fragment"),
            )
        )

    if scheme == "":
        _validate_relative_path(uri, findings)
        return

    if scheme == "aura":
        if not parsed.netloc or not _SAFE_AUTHORITY.fullmatch(parsed.netloc):
            findings.append(
                _finding(
                    "UNSAFE_ASSET_AUTHORITY",
                    "aura URI requires a canonical authority",
                )
            )
        _validate_uri_path(parsed.path, findings)
        return

    if scheme in _ALLOWED_REMOTE_SCHEMES:
        try:
            hostname = parsed.hostname
            _ = parsed.port
        except ValueError:
            hostname = None
            findings.append(
                _finding(
                    "REMOTE_ASSET_HOST_INVALID",
                    "https asset URI contains an invalid host or port",
                )
            )
        if not hostname:
            findings.append(
                _finding(
                    "REMOTE_ASSET_HOST_MISSING",
                    "https asset URI requires a host",
                )
            )
        _validate_uri_path(parsed.path, findings, allow_empty=True)
        if not allow_remote:
            findings.append(
                _finding(
                    "REMOTE_ASSET_NOT_ADMITTED",
                    "remote asset URI requires an explicit fetch policy",
                )
            )
        return

    findings.append(
        _finding(
            "UNSUPPORTED_ASSET_URI_SCHEME",
            f"unsupported asset URI scheme: {scheme or '<none>'}",
        )
    )


def _validate_relative_path(
    value: str,
    findings: list[dict[str, Any]],
) -> None:
    if not value or value.startswith("/"):
        findings.append(
            _finding(
                "UNSAFE_ASSET_PATH",
                "relative asset path must be non-empty and relative",
            )
        )
        return
    decoded = unquote(value)
    if decoded != value or "//" in value:
        findings.append(
            _finding(
                "NONCANONICAL_ASSET_ENCODING",
                "relative asset path must not encode separators or aliases",
            )
        )
        decoded_path = PurePosixPath(decoded)
        if (
            decoded.startswith("/")
            or any(part in {"", ".", ".."} for part in decoded_path.parts)
            or decoded_path.as_posix() != decoded
        ):
            findings.append(
                _finding(
                    "UNSAFE_ASSET_PATH",
                    "decoded asset path must remain normalized and traversal-free",
                )
            )
        return
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts) or path.as_posix() != value:
        findings.append(
            _finding(
                "UNSAFE_ASSET_PATH",
                "relative asset paths must be normalized and traversal-free",
            )
        )


def _validate_uri_path(
    value: str,
    findings: list[dict[str, Any]],
    *,
    allow_empty: bool = False,
) -> None:
    if not value:
        if not allow_empty:
            findings.append(
                _finding(
                    "UNSAFE_ASSET_PATH",
                    "asset URI path must not be empty",
                )
            )
        return
    decoded = unquote(value)
    if decoded != value:
        findings.append(
            _finding(
                "NONCANONICAL_ASSET_ENCODING",
                "asset URI path must not contain percent-encoded aliases",
            )
        )
        return
    if not value.startswith("/") or value.startswith("//") or "//" in value[1:]:
        findings.append(
            _finding(
                "UNSAFE_ASSET_PATH",
                "asset URI path must use exactly one canonical separator",
            )
        )
        return
    relative = value[1:]
    if not relative:
        if not allow_empty:
            findings.append(
                _finding(
                    "UNSAFE_ASSET_PATH",
                    "asset URI path must not be empty",
                )
            )
        return
    path = PurePosixPath(relative)
    if any(part in {"", ".", ".."} for part in path.parts) or path.as_posix() != relative:
        findings.append(
            _finding(
                "UNSAFE_ASSET_PATH",
                "asset URI path must be normalized and traversal-free",
            )
        )


def _finding(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message, "blocking": True}


__all__ = [
    "SPATIAL_ASSET_REGISTRY_VERSION",
    "SpatialAssetRegistry",
    "SpatialAssetValidationReport",
    "validate_asset_manifest",
]
