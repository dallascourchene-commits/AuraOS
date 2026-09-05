"""Exact package-source manifest verification for fail-closed AirLLM admission.

This module closes a provenance gap left by pinning only the loader class's defining
file. AirLLM loaders execute sibling package modules (for example ``utils`` and
``persist``), so security admission needs a canonical root over the whole admitted
package source generation.

The guard is deliberately D0/non-promoting. It proves only that an on-disk package tree
matches an exact allowlisted manifest at the instant it is checked. Callers that require
pre-effect guarantees must recheck immediately before invoking AirLLM and provide their
own filesystem immutability/sandbox boundary for the execution window.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import stat
from typing import Iterable, Sequence

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA = "AURA-AIRLLM-PACKAGE-SOURCE-MANIFEST-v1"
_DEFAULT_REQUIRED_PATHS = (
    "__init__.py",
    "airllm_base.py",
    "auto_model.py",
    "utils.py",
    "persist/__init__.py",
    "persist/model_persister.py",
    "persist/safetensor_model_persister.py",
)
_IGNORED_DIRS = frozenset({".git"})
_REJECTED_DIRS = frozenset({"__pycache__"})
_REJECTED_SUFFIXES = frozenset({".pyc", ".pyo"})


class SourceManifestError(RuntimeError):
    """Base class for exact package-source manifest failures."""


class InvalidManifestAllowlistError(SourceManifestError):
    """Raised when a manifest SHA-256 allowlist is malformed."""


class SourceTreeIntegrityError(SourceManifestError):
    """Raised when source-tree identity cannot be established unambiguously."""


@dataclass(frozen=True)
class VerifiedSourceManifest:
    root: str
    sha256: str
    file_count: int
    total_bytes: int
    required_paths: tuple[str, ...]


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _validate_digest(value: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise InvalidManifestAllowlistError("manifest SHA-256 values must be exact lowercase 64-hex strings")
    return value


def normalize_manifest_allowlist(values: Iterable[str] | None) -> frozenset[str]:
    if values is None or isinstance(values, (str, bytes)):
        raise InvalidManifestAllowlistError("source-manifest allowlist must be a non-empty collection of SHA-256 values")
    try:
        normalized = frozenset(_validate_digest(value) for value in values)
    except TypeError as exc:
        raise InvalidManifestAllowlistError("source-manifest allowlist must be iterable") from exc
    if not normalized:
        raise InvalidManifestAllowlistError("source-manifest allowlist must not be empty")
    return normalized


def _normalize_required_paths(paths: Sequence[str] | None) -> tuple[str, ...]:
    if paths is None:
        paths = _DEFAULT_REQUIRED_PATHS
    if isinstance(paths, (str, bytes)) or not paths:
        raise SourceTreeIntegrityError("required_paths must be a non-empty sequence")
    normalized: list[str] = []
    for raw in paths:
        if not isinstance(raw, str) or not raw or raw.strip() != raw:
            raise SourceTreeIntegrityError("required source paths must be non-empty exact strings")
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts or raw.startswith("./"):
            raise SourceTreeIntegrityError(f"unsafe required source path: {raw!r}")
        posix = path.as_posix()
        if posix in normalized:
            raise SourceTreeIntegrityError(f"duplicate required source path: {posix}")
        normalized.append(posix)
    return tuple(sorted(normalized))


def _assert_regular_file(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise SourceTreeIntegrityError(f"source artifact is not readable: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise SourceTreeIntegrityError(f"source symlinks are not admitted: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise SourceTreeIntegrityError(f"source artifact must be a regular file: {path}")
    return metadata


def _sha256_regular_file(path: Path, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    before = _assert_regular_file(path)
    digest = sha256()
    try:
        with path.open("rb", buffering=0) as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise SourceTreeIntegrityError(f"source artifact changed before hashing: {path}")
            while True:
                block = handle.read(chunk_size)
                if not block:
                    break
                digest.update(block)
            after_open = os.fstat(handle.fileno())
    except SourceTreeIntegrityError:
        raise
    except OSError as exc:
        raise SourceTreeIntegrityError(f"failed while hashing source artifact: {path}") from exc
    try:
        after_path = path.lstat()
    except OSError as exc:
        raise SourceTreeIntegrityError(f"source artifact disappeared after hashing: {path}") from exc
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_open = (after_open.st_dev, after_open.st_ino, after_open.st_size, after_open.st_mtime_ns)
    identity_after = (after_path.st_dev, after_path.st_ino, after_path.st_size, after_path.st_mtime_ns)
    if identity_before != identity_open or identity_before != identity_after:
        raise SourceTreeIntegrityError(f"source artifact changed while hashing: {path}")
    return digest.hexdigest(), before.st_size


def build_source_manifest(source_root: str | os.PathLike[str], *, required_paths: Sequence[str] | None = None) -> tuple[dict[str, object], VerifiedSourceManifest]:
    root = Path(source_root).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve(strict=False)
    try:
        root_meta = root.lstat()
    except OSError as exc:
        raise SourceTreeIntegrityError(f"AirLLM source root does not exist: {root}") from exc
    if stat.S_ISLNK(root_meta.st_mode):
        raise SourceTreeIntegrityError(f"AirLLM source root may not be a symlink: {root}")
    if not stat.S_ISDIR(root_meta.st_mode):
        raise SourceTreeIntegrityError(f"AirLLM source root must be a directory: {root}")

    required = _normalize_required_paths(required_paths)
    entries: list[dict[str, object]] = []
    observed: set[str] = set()
    total_bytes = 0

    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            candidate = current_path / dirname
            metadata = candidate.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise SourceTreeIntegrityError(f"source directory symlink is not admitted: {candidate}")
            if not stat.S_ISDIR(metadata.st_mode):
                raise SourceTreeIntegrityError(f"source tree contains non-directory entry: {candidate}")
            if dirname in _REJECTED_DIRS:
                raise SourceTreeIntegrityError(f"executable bytecode/cache directory is not admitted: {candidate}")
            if dirname not in _IGNORED_DIRS:
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames):
            candidate = current_path / filename
            relative = candidate.relative_to(root).as_posix()
            metadata = candidate.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise SourceTreeIntegrityError(f"source symlink is not admitted: {candidate}")
            if not stat.S_ISREG(metadata.st_mode):
                raise SourceTreeIntegrityError(f"source tree contains a special file: {candidate}")
            if candidate.suffix.lower() in _REJECTED_SUFFIXES:
                raise SourceTreeIntegrityError(f"executable Python bytecode is not admitted: {candidate}")
            file_digest, size = _sha256_regular_file(candidate)
            entries.append({"path": relative, "size": size, "sha256": file_digest})
            observed.add(relative)
            total_bytes += size

    missing = tuple(path for path in required if path not in observed)
    if missing:
        raise SourceTreeIntegrityError(f"required AirLLM source paths are missing: {missing!r}")
    if not entries:
        raise SourceTreeIntegrityError("AirLLM source manifest may not be empty")

    manifest: dict[str, object] = {"schema": _SCHEMA, "required_paths": list(required), "files": sorted(entries, key=lambda entry: str(entry["path"]))}
    manifest_digest = sha256(_canonical_json(manifest)).hexdigest()
    verified = VerifiedSourceManifest(root=str(root), sha256=manifest_digest, file_count=len(entries), total_bytes=total_bytes, required_paths=required)
    return manifest, verified


def verify_source_manifest(source_root: str | os.PathLike[str], allowlist: Iterable[str] | None, *, required_paths: Sequence[str] | None = None) -> VerifiedSourceManifest:
    admitted = normalize_manifest_allowlist(allowlist)
    _, verified = build_source_manifest(source_root, required_paths=required_paths)
    if not any(hmac.compare_digest(verified.sha256, digest) for digest in admitted):
        raise SourceTreeIntegrityError("AirLLM package source manifest SHA-256 is not allowlisted")
    return verified


def k27_for_manifest(manifest_sha256: str) -> tuple[int, int, int]:
    digest = bytes.fromhex(_validate_digest(manifest_sha256))
    return digest[0] % 27, digest[1] % 27, digest[2] % 27


__all__ = ["InvalidManifestAllowlistError", "SourceManifestError", "SourceTreeIntegrityError", "VerifiedSourceManifest", "build_source_manifest", "k27_for_manifest", "normalize_manifest_allowlist", "verify_source_manifest"]
