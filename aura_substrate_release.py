"""Deterministic public artifacts for the P9 cognitive-substrate contract."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

from aura_event_contracts import canonical_json
from aura_substrate_contracts import (
    SUBSTRATE_MANIFEST_VERSION,
    SUBSTRATE_RELEASE_INDEX_VERSION,
    SubstrateManifest,
)
from aura_substrate_manifest import MANIFEST_PATH, RELEASE_INDEX_PATH, build_substrate_manifest

_ALLOWED_SUFFIXES = frozenset({".py", ".md"})
_FORBIDDEN_PARTS = frozenset(
    {
        ".git",
        ".github",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "Aura_Memory",
        "Aura_Sandbox",
        "Aura_Vault",
        "node_modules",
        "venv",
    }
)
_FORBIDDEN_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        "topology_map.json",
        "CODEMAP.json",
        "CODEMAP.md",
    }
)
_MAX_FILE_BYTES = 2_000_000
_FILE_PART_SIZE = 8
_PHASE_PART_SIZE = 3


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _chunks(values: tuple[Any, ...], size: int) -> tuple[tuple[Any, ...], ...]:
    return tuple(values[index:index + size] for index in range(0, len(values), size))


def build_manifest_artifacts(
    manifest: SubstrateManifest | None = None,
) -> tuple[dict[str, Any], tuple[tuple[str, dict[str, Any]], ...]]:
    active = manifest or build_substrate_manifest()
    parts: list[tuple[str, dict[str, Any]]] = []
    for index, chunk in enumerate(_chunks(active.files, _FILE_PART_SIZE), start=1):
        parts.append(
            (
                f"docs/aura_substrate_manifest.files.{index:02d}.json",
                {
                    "version": SUBSTRATE_MANIFEST_VERSION,
                    "kind": "files",
                    "part": index,
                    "records": [item.to_dict() for item in chunk],
                },
            )
        )
    for index, chunk in enumerate(_chunks(active.phases, _PHASE_PART_SIZE), start=1):
        parts.append(
            (
                f"docs/aura_substrate_manifest.phases.{index:02d}.json",
                {
                    "version": SUBSTRATE_MANIFEST_VERSION,
                    "kind": "phases",
                    "part": index,
                    "records": [item.to_dict() for item in chunk],
                },
            )
        )
    part_receipts = []
    for path, payload in parts:
        data = _canonical_bytes(payload)
        part_receipts.append(
            {
                "path": path,
                "kind": payload["kind"],
                "part": payload["part"],
                "record_count": len(payload["records"]),
                "sha256": hashlib.sha256(data).hexdigest(),
                "byte_length": len(data),
            }
        )
    receipt = {
        "version": SUBSTRATE_MANIFEST_VERSION,
        "manifest_digest": active.digest,
        "file_count": len(active.files),
        "phase_count": len(active.phases),
        "retained_external_surfaces": list(active.retained_external_surfaces),
        "parts": part_receipts,
    }
    return receipt, tuple(parts)


def write_manifest_artifacts(
    output_root: str | Path = ".",
    manifest: SubstrateManifest | None = None,
) -> dict[str, Any]:
    root = Path(output_root)
    receipt, parts = build_manifest_artifacts(manifest)
    for relative, payload in parts:
        output = root / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(_canonical_bytes(payload))
    receipt_output = root / MANIFEST_PATH
    receipt_output.parent.mkdir(parents=True, exist_ok=True)
    receipt_output.write_bytes(_canonical_bytes(receipt))
    return receipt


def _safe_release_path(root: Path, relative: str) -> Path:
    candidate = root / relative
    resolved_root = root.resolve()
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"release file unavailable: {relative}") from exc
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"release file escapes repository: {relative}") from exc
    if candidate.is_symlink() or not resolved.is_file():
        raise ValueError(f"release file must be a regular non-symlink file: {relative}")
    relative_path = Path(relative)
    if set(relative_path.parts) & _FORBIDDEN_PARTS or relative_path.name in _FORBIDDEN_NAMES:
        raise ValueError(f"release file is forbidden: {relative}")
    if relative_path.suffix not in _ALLOWED_SUFFIXES:
        raise ValueError(f"release file type is not allowlisted: {relative}")
    return resolved


def _file_index(root: Path, record: Any) -> dict[str, Any]:
    path = _safe_release_path(root, record.path)
    data = path.read_bytes()
    if len(data) > _MAX_FILE_BYTES:
        raise ValueError(f"release file exceeds size limit: {record.path}")
    if b"\x00" in data:
        raise ValueError(f"release file contains NUL bytes: {record.path}")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"release file is not UTF-8: {record.path}") from exc
    blob_sha1 = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
    return {
        "path": record.path,
        "role": record.role.value,
        "byte_length": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": blob_sha1,
    }


def _payload(root: str | Path, manifest: SubstrateManifest) -> dict[str, Any]:
    base = Path(root)
    files = tuple(
        _file_index(base, record)
        for record in manifest.files
        if record.release_included
    )
    paths = tuple(item["path"] for item in files)
    if paths != tuple(sorted(set(paths))):
        raise ValueError("release index paths must be unique and sorted")
    return {
        "version": SUBSTRATE_RELEASE_INDEX_VERSION,
        "manifest_digest": manifest.digest,
        "package_format": "INDEX_ONLY",
        "publication_performed": False,
        "files": list(files),
    }


def build_release_index(
    root: str | Path = ".",
    manifest: SubstrateManifest | None = None,
) -> dict[str, Any]:
    active = manifest or build_substrate_manifest()
    payload = _payload(root, active)
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return {**payload, "index_digest": digest}


def write_release_index(
    root: str | Path = ".",
    path: str | Path = RELEASE_INDEX_PATH,
) -> dict[str, Any]:
    payload = build_release_index(root)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default=str(RELEASE_INDEX_PATH))
    parser.add_argument("--manifest-output-root")
    args = parser.parse_args()
    if args.manifest_output_root:
        write_manifest_artifacts(args.manifest_output_root)
    write_release_index(args.root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "build_manifest_artifacts",
    "build_release_index",
    "write_manifest_artifacts",
    "write_release_index",
]
