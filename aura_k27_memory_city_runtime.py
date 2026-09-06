#!/usr/bin/env python3
"""Read-only AuraOS runtime binding for the K27 Memory City registry.

This module binds K27Path, FrameAddress, and MemoryStore to the repository-owned
1,115-record registry without granting mutation or effect authority. Canonical
bytes are verified before use; lifecycle mutations belong only to ephemeral test
copies until a separate owner authorizes a writable store.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import lzma
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from aura_k27_memory_city import K27Path, MemoryStore, canonical

VERSION = "AURA_K27_MEMORY_CITY_RUNTIME_V1"
FRAME = "aura-memory-city-research"
GENERATION = "20260906-v1"
EXPECTED_RECORDS = 1115
EXPECTED_ROUTE_RECORDS = 1000
EXPECTED_DATABASE_SHA256 = "246dbded0a33eaede035b829bfcae9f8ee50d769f5c28f1a955a16073131d86f"
EXPECTED_SEMANTIC_ROOT = "7e0095415ffb6450aeb39f1faba782f27a1fb628e481fe7d1975aa5a649cf1c1"
AUTHORITY = {
    "coordinate_is_authority": False,
    "memory_write_authority": False,
    "belief_commit_authority": False,
    "use_authority": False,
    "effect_authority": False,
    "automatic_promotion": False,
    "gate10": False,
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_payload_parts(directory: Path, stem: str) -> bytes:
    direct = directory / f"{stem}.xz.b64"
    if direct.is_file() and not direct.is_symlink():
        encoded = direct.read_text(encoding="ascii").strip()
    else:
        parts = sorted(directory.glob(f"{stem}.xz.b64.part-*"))
        if not parts or any(part.is_symlink() for part in parts):
            raise RuntimeError(f"packaged K27 payload missing: {stem}")
        encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
    return lzma.decompress(base64.b64decode(encoded, validate=True))


def default_registry(repo_root: Path | str) -> Path:
    root = Path(repo_root).resolve()
    payload_dir = root / ".aura" / "k27_memory_city"
    direct = payload_dir / "research_registry.sqlite"
    if direct.is_file() and not direct.is_symlink():
        return direct
    cache_root = Path(os.environ.get("AURA_K27_RUNTIME_CACHE", Path(tempfile.gettempdir()) / "auraos-k27-memory-city"))
    target_dir = cache_root / EXPECTED_DATABASE_SHA256
    target = target_dir / "research_registry.sqlite"
    if target.is_file() and _sha256(target) == EXPECTED_DATABASE_SHA256:
        return target
    raw = _read_payload_parts(payload_dir, "research_registry.sqlite")
    if hashlib.sha256(raw).hexdigest() != EXPECTED_DATABASE_SHA256:
        raise RuntimeError("packaged K27 registry materialization hash mismatch")
    target_dir.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".sqlite.tmp")
    temporary.write_bytes(raw)
    os.replace(temporary, target)
    return target


def _semantic_root(store: MemoryStore) -> str:
    rows = store.under(FRAME, GENERATION)
    coords = [{
        "object_id": row["object_id"], "revision_id": row["revision_id"],
        "payload_sha256": row["payload_sha256"], "address": row["address"], "epoch": row["epoch"],
    } for row in rows]
    return hashlib.sha256(canonical(sorted(coords, key=lambda x: x["object_id"])).encode()).hexdigest()


class K27MemoryCityRuntime:
    """Verified read-only runtime view over the repository-owned Memory City."""
    def __init__(self, repo_root: Path | str, registry_path: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry_path = Path(registry_path).resolve() if registry_path else default_registry(self.repo_root)
        if not self.registry_path.is_file() or self.registry_path.is_symlink():
            raise RuntimeError("canonical K27 registry is missing or unsafe")
        actual_sha = _sha256(self.registry_path)
        if actual_sha != EXPECTED_DATABASE_SHA256:
            raise RuntimeError("canonical K27 registry byte identity mismatch")
        with MemoryStore(self.registry_path, read_only=True) as store:
            integrity = store.db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok": raise RuntimeError("canonical K27 registry integrity check failed")
            count = store.db.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
            if count != EXPECTED_RECORDS: raise RuntimeError("canonical K27 registry record count mismatch")
            semantic_root = _semantic_root(store)
            if semantic_root != EXPECTED_SEMANTIC_ROOT: raise RuntimeError("canonical K27 registry semantic root mismatch")
            routes = len(store.under(FRAME, GENERATION, (2,)))
            if routes != EXPECTED_ROUTE_RECORDS: raise RuntimeError("canonical K27 route projection count mismatch")
        self.database_sha256 = actual_sha; self.semantic_root = semantic_root; self.record_count = count; self.route_count = routes

    def close(self) -> None:
        return None
    def __enter__(self) -> "K27MemoryCityRuntime": return self
    def __exit__(self, *_: object) -> None: self.close()
    def status(self) -> dict[str, Any]:
        return {"version": VERSION, "frame": FRAME, "frame_generation": GENERATION,
            "database_sha256": self.database_sha256, "semantic_registry_root": self.semantic_root,
            "record_count": self.record_count, "route_count": self.route_count, "registry_mode": "read_only",
            "currentness_scope": "repository-owned local registry consistency only", "authority": dict(AUTHORITY)}
    def get(self, object_id: str) -> dict[str, Any] | None:
        with MemoryStore(self.registry_path, read_only=True) as store: return store.get(object_id)
    def under(self, prefix: tuple[int, ...] = ()) -> list[dict[str, Any]]:
        K27Path(prefix)
        with MemoryStore(self.registry_path, read_only=True) as store: return store.under(FRAME, GENERATION, prefix)


class _Handler(BaseHTTPRequestHandler):
    runtime: K27MemoryCityRuntime
    def log_message(self, *_: Any) -> None: return
    def _reply(self, status: int, value: Any) -> None:
        body = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health": self._reply(200, self.runtime.status()); return
        if parsed.path == "/object":
            key = parse_qs(parsed.query).get("id", [""])[0]
            if not key: self._reply(400, {"error": "id required"}); return
            record = self.runtime.get(key); self._reply(200 if record is not None else 404, record or {"error": "not found"}); return
        if parsed.path == "/under":
            raw = parse_qs(parsed.query).get("prefix", [""])[0]
            try: prefix = tuple(int(part) for part in raw.split(",") if part != ""); records = self.runtime.under(prefix)
            except (ValueError, TypeError): self._reply(400, {"error": "prefix must contain comma-separated K27 digits 0..26"}); return
            self._reply(200, {"prefix": list(prefix), "count": len(records), "records": records}); return
        self._reply(404, {"error": "not found"})


def serve(repo_root: Path, host: str, port: int) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}: raise SystemExit("K27 runtime refuses non-loopback binding")
    runtime = K27MemoryCityRuntime(repo_root); handler = type("K27RuntimeHandler", (_Handler,), {"runtime": runtime}); server = ThreadingHTTPServer((host, port), handler)
    try: server.serve_forever()
    finally: server.server_close(); runtime.close()


def probe_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}: raise RuntimeError("probe refuses non-loopback URL")
    with urlopen(url, timeout=5) as response: value = json.loads(response.read().decode("utf-8"))
    if value.get("database_sha256") != EXPECTED_DATABASE_SHA256 or value.get("semantic_registry_root") != EXPECTED_SEMANTIC_ROOT: raise RuntimeError("runtime probe identity mismatch")
    if value.get("authority") != AUTHORITY: raise RuntimeError("runtime probe authority contract mismatch")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--repo-root", default="."); parser.add_argument("--status", action="store_true"); parser.add_argument("--serve", action="store_true"); parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8772); parser.add_argument("--probe-url"); args = parser.parse_args()
    if args.probe_url: print(json.dumps(probe_url(args.probe_url), sort_keys=True)); return 0
    if args.serve: serve(Path(args.repo_root), args.host, args.port); return 0
    with K27MemoryCityRuntime(Path(args.repo_root)) as runtime: print(json.dumps(runtime.status(), sort_keys=True))
    return 0

if __name__ == "__main__": raise SystemExit(main())
