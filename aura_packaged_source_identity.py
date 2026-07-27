"""Deterministic source manifest for packaged Aura runtimes without Git metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Iterable

MANIFEST_RELATIVE_PATH = ".aura/PACKAGED_SOURCE_MANIFEST.json"
MANIFEST_VERSION = "AURA_PACKAGED_SOURCE_MANIFEST_V1"
EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".pytest_cache",
        "Aura_Memory",
        "Aura_Staging",
        "__pycache__",
    }
)

_VERIFY_CACHE_LOCK = threading.Lock()
_VERIFY_CACHE: dict[Path, tuple[tuple[tuple[int, int], str], dict[str, Any]]] = {}


def _digest(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.blake2b(body.encode("utf-8"), digest_size=32).hexdigest()


def _excluded(path: Path) -> bool:
    return (
        path.as_posix() == MANIFEST_RELATIVE_PATH
        or any(part in EXCLUDED_PARTS for part in path.parts)
        or path.suffix in {".pyc", ".pyo"}
    )


def _iter_source_paths(root: Path) -> Iterable[Path]:
    for candidate in sorted(root.rglob("*")):
        relative = candidate.relative_to(root)
        if _excluded(relative):
            continue
        if candidate.is_symlink() or candidate.is_file():
            yield relative


def _entry(root: Path, relative: Path) -> dict[str, str]:
    candidate = root / relative
    if candidate.is_symlink():
        payload = str(candidate.readlink()).encode("utf-8", errors="surrogateescape")
        kind = "symlink"
    else:
        payload = candidate.read_bytes()
        kind = "file"
    return {
        "path": relative.as_posix(),
        "kind": kind,
        "digest": hashlib.blake2b(payload, digest_size=32).hexdigest(),
    }


def source_snapshot(root: str | Path) -> tuple[list[dict[str, str]], str]:
    resolved = Path(root).resolve()
    entries = [_entry(resolved, relative) for relative in _iter_source_paths(resolved)]
    return entries, _digest(entries)


def build_packaged_source_manifest(root: str | Path) -> dict[str, Any]:
    resolved = Path(root).resolve()
    entries, source_digest = source_snapshot(resolved)
    payload = {
        "version": MANIFEST_VERSION,
        "entries": entries,
        "source_digest": source_digest,
    }
    payload["manifest_digest"] = _digest(payload)
    target = resolved / MANIFEST_RELATIVE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def verify_packaged_source_manifest(root: str | Path) -> dict[str, Any]:
    resolved = Path(root).resolve()
    target = resolved / MANIFEST_RELATIVE_PATH
    try:
        manifest_stat = target.stat()
    except OSError as exc:
        raise ValueError("trusted packaged source manifest is unavailable") from exc
    cache_key = (int(manifest_stat.st_mtime_ns), int(manifest_stat.st_size))
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("trusted packaged source manifest is unavailable") from exc
    if not isinstance(payload, dict) or payload.get("version") != MANIFEST_VERSION:
        raise ValueError("trusted packaged source manifest is invalid")
    expected_manifest_digest = str(payload.get("manifest_digest") or "")
    unsigned = dict(payload)
    unsigned.pop("manifest_digest", None)
    if expected_manifest_digest != _digest(unsigned):
        raise ValueError("trusted packaged source manifest digest mismatch")
    entries, source_digest = source_snapshot(resolved)
    if entries != payload.get("entries") or source_digest != payload.get("source_digest"):
        raise ValueError("packaged source drift detected")
    # Cache the validated payload keyed on both manifest stat AND the freshly
    # computed source digest so in-place source drift is never masked.
    with _VERIFY_CACHE_LOCK:
        _VERIFY_CACHE[resolved] = ((cache_key, source_digest), payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    payload = (
        build_packaged_source_manifest(args.root)
        if args.command == "build"
        else verify_packaged_source_manifest(args.root)
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
