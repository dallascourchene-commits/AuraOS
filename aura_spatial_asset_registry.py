"""Content-addressed, manifest-only asset registry for Aura spatial projections."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import PurePosixPath
from typing import Any, Iterable
from urllib.parse import urlparse

from aura_event_contracts import stable_digest
from aura_spatial_contracts import SpatialAssetManifest

SPATIAL_ASSET_REGISTRY_VERSION = "AURA_SPATIAL_ASSET_REGISTRY_V1"
_ALLOWED_REMOTE_SCHEMES = frozenset({"https"})
_ALLOWED_LOCAL_SCHEMES = frozenset({"", "file", "aura"})


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
    """Immutable-manifest registry. It never fetches, decodes, trains, or renders assets."""

    def __init__(self, manifests: Iterable[SpatialAssetManifest] = ()) -> None:
        by_id: dict[str, SpatialAssetManifest] = {}
        for manifest in manifests:
            if not isinstance(manifest, SpatialAssetManifest):
                raise ValueError(
                    "manifests must contain SpatialAssetManifest records"
                )
            if manifest.asset_id in by_id:
                raise ValueError(
                    f"duplicate spatial asset id: {manifest.asset_id}"
                )
            report = validate_asset_manifest(manifest)
            if not report.ok:
                codes = ", ".join(item["code"] for item in report.findings)
                raise ValueError(
                    f"invalid spatial asset {manifest.asset_id}: {codes}"
                )
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
    findings: list[dict[str, Any]] = []
    parsed = urlparse(manifest.uri)
    scheme = parsed.scheme.lower()
    if scheme in _ALLOWED_LOCAL_SCHEMES:
        if scheme == "":
            path = PurePosixPath(manifest.uri)
            if manifest.uri.startswith("/") or any(
                part in {"", ".", ".."} for part in path.parts
            ):
                findings.append(
                    _finding(
                        "UNSAFE_ASSET_PATH",
                        "relative asset paths must be normalized and traversal-free",
                    )
                )
    elif scheme in _ALLOWED_REMOTE_SCHEMES:
        if not allow_remote:
            findings.append(
                _finding(
                    "REMOTE_ASSET_NOT_ADMITTED",
                    "remote asset URI requires an explicit fetch policy",
                )
            )
    else:
        findings.append(
            _finding(
                "UNSUPPORTED_ASSET_URI_SCHEME",
                f"unsupported asset URI scheme: {scheme or '<none>'}",
            )
        )

    verified_content = False
    if content is not None:
        if not isinstance(content, bytes):
            raise ValueError("content must be bytes")
        if len(content) != manifest.byte_length:
            findings.append(
                _finding(
                    "ASSET_LENGTH_MISMATCH",
                    (
                        f"manifest declares {manifest.byte_length} bytes "
                        f"but received {len(content)}"
                    ),
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
        if observed and observed != expected_hex:
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

    return SpatialAssetValidationReport(
        ok=not findings,
        asset_id=manifest.asset_id,
        findings=tuple(findings),
        verified_content=verified_content,
        manifest_digest=manifest.digest,
    )


def _finding(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message, "blocking": True}


__all__ = [
    "SPATIAL_ASSET_REGISTRY_VERSION",
    "SpatialAssetRegistry",
    "SpatialAssetValidationReport",
    "validate_asset_manifest",
]
