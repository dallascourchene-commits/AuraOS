#!/usr/bin/env python3
"""Read-only AuraOS runtime binding for the K27 Memory City registry.

This module binds K27Path, FrameAddress, and MemoryStore to the repository-owned
1,115-record registry without granting mutation or effect authority. Canonical
bytes are verified before use; lifecycle mutations belong only to ephemeral test
copies until a separate owner authorizes a writable store.
"""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from aura_k27_memory_city import K27Path, FrameAddress, MemoryStore, MemoryConflict, canonical
from aura_k27_memory_city.registry_recipe import build_routes_and_families

VERSION = "AURA_K27_MEMORY_CITY_RUNTIME_V1"
FRAME = "aura-memory-city-research"
GENERATION = "20260906-v1"
EXPECTED_RECORDS = 1115
EXPECTED_ROUTE_RECORDS = 1000
EXPECTED_SOURCE_DATABASE_SHA256 = "246dbded0a33eaede035b829bfcae9f8ee50d769f5c28f1a955a16073131d86f"
EXPECTED_DATABASE_SHA256 = EXPECTED_SOURCE_DATABASE_SHA256  # compatibility alias: historical source bytes
EXPECTED_COLD_SOURCE_MANIFEST_SHA256 = "6392d30664e5a17dd30025eab49a4c81f70e4ed50ce0f7bd8dfb8c1d2adbaf06"
EXPECTED_RECIPE_VERSION = "AURA_K27_MEMORY_CITY_REGISTRY_RECIPE_V1"
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


def _load_cold_source_manifest(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / ".aura" / "k27_memory_city" / "cold_source_manifest.json"
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("K27 cold-source manifest is missing or unsafe")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_COLD_SOURCE_MANIFEST_SHA256:
        raise RuntimeError("K27 cold-source manifest identity mismatch")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("K27 cold-source manifest is not canonical UTF-8 JSON") from exc
    if not isinstance(manifest, list) or len(manifest) != 15:
        raise RuntimeError("K27 cold-source manifest count mismatch")
    required = {"object_id", "url", "version", "file", "sha256", "scope"}
    seen: set[str] = set()
    for entry in manifest:
        if not isinstance(entry, dict) or not required.issubset(entry):
            raise RuntimeError("K27 cold-source manifest entry is malformed")
        key = entry["object_id"]
        if not isinstance(key, str) or not key or key in seen:
            raise RuntimeError("K27 cold-source manifest object identity is invalid or duplicated")
        if not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64:
            raise RuntimeError("K27 cold-source manifest digest is malformed")
        seen.add(key)
    return manifest


def _rebuild_registry_from_recipe(repo_root: Path, target: Path) -> Path:
    retained = _load_cold_source_manifest(repo_root)
    routes, families = build_routes_and_families()
    if len(routes) != 1000 or len(families) != 100:
        raise RuntimeError("K27 registry recipe cardinality mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".sqlite.tmp")
    temporary.unlink(missing_ok=True)
    keys: dict[str, str] = {}
    with MemoryStore(temporary) as store:
        store.register_frame(FRAME, GENERATION, expected_generation=None)
        for i, source in enumerate(retained):
            key = source["object_id"]
            result = store.publish(
                key, source, FrameAddress(FRAME, GENERATION, (0, i), key),
                source_url=source["url"], source_version=source["version"],
            )
            keys[key] = result["revision_id"]
        primitives = list(dict.fromkeys(row["primitive"] for row in sorted(routes, key=lambda row: row["family_id"])))
        concerns = list(dict.fromkeys(row["concern"] for row in sorted(routes, key=lambda row: row["family_id"])))
        operators = sorted({row["operator"] for row in routes})
        for family_id, family in families.items():
            key = "FAMILY/" + family_id
            dependencies = {source_id: keys[source_id] for source_id in ["MC-SRC-O1O9", *family["external_source_keys"]]}
            result = store.publish(
                key, family,
                FrameAddress(FRAME, GENERATION, (1, primitives.index(family["primitive"]), concerns.index(family["concern"])), key),
                source_url=family["source_url"], source_version="O7-enriched-candidate-v1",
                dependencies=dependencies,
            )
            keys[key] = result["revision_id"]
        for route in routes:
            key = route["id"]
            family_key = "FAMILY/" + route["family_id"]
            result = store.publish(
                key, route,
                FrameAddress(FRAME, GENERATION, (2, primitives.index(route["primitive"]), concerns.index(route["concern"]), operators.index(route["operator"])), key),
                source_url=route["source_url"], source_version="O7-route-enriched-v1",
                dependencies={family_key: keys[family_key]},
            )
            keys[key] = result["revision_id"]
        if store.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("K27 recipe rebuild integrity check failed")
        if len(store.under(FRAME, GENERATION)) != EXPECTED_RECORDS:
            raise RuntimeError("K27 recipe rebuild record count mismatch")
        if len(store.under(FRAME, GENERATION, (2,))) != EXPECTED_ROUTE_RECORDS:
            raise RuntimeError("K27 recipe rebuild route count mismatch")
        if _semantic_root(store) != EXPECTED_SEMANTIC_ROOT:
            raise RuntimeError("K27 recipe rebuild semantic root mismatch")
    os.replace(temporary, target)
    return target


def default_registry(repo_root: Path | str) -> Path:
    root = Path(repo_root).resolve()
    direct = root / ".aura" / "k27_memory_city" / "research_registry.sqlite"
    if direct.is_file() and not direct.is_symlink():
        if _sha256(direct) != EXPECTED_SOURCE_DATABASE_SHA256:
            raise RuntimeError("direct K27 source registry byte identity mismatch")
        return direct
    cache_root = Path(os.environ.get("AURA_K27_RUNTIME_CACHE", Path(tempfile.gettempdir()) / "auraos-k27-memory-city"))
    target_dir = cache_root / EXPECTED_SEMANTIC_ROOT
    target = target_dir / "research_registry.sqlite"
    if target.is_file() and not target.is_symlink():
        try:
            with MemoryStore(target, read_only=True) as store:
                if store.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and _semantic_root(store) == EXPECTED_SEMANTIC_ROOT:
                    return target
        except (OSError, ValueError, sqlite3.Error):
            pass
        target.unlink(missing_ok=True)
    return _rebuild_registry_from_recipe(root, target)


def _semantic_root(store: MemoryStore) -> str:
    rows = store.under(FRAME, GENERATION)
    coords = [
        {
            "object_id": row["object_id"],
            "revision_id": row["revision_id"],
            "payload_sha256": row["payload_sha256"],
            "address": row["address"],
            "epoch": row["epoch"],
        }
        for row in rows
    ]
    return hashlib.sha256(canonical(sorted(coords, key=lambda x: x["object_id"])).encode()).hexdigest()


class K27MemoryCityRuntime:
    """Verified read-only runtime view over the repository-owned Memory City."""

    def __init__(self, repo_root: Path | str, registry_path: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry_path = Path(registry_path).resolve() if registry_path else default_registry(self.repo_root)
        if not self.registry_path.is_file() or self.registry_path.is_symlink():
            raise RuntimeError("canonical K27 registry is missing or unsafe")
        actual_sha = _sha256(self.registry_path)
        with MemoryStore(self.registry_path, read_only=True) as store:
            integrity = store.db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError("canonical K27 registry integrity check failed")
            count = store.db.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
            if count != EXPECTED_RECORDS:
                raise RuntimeError("canonical K27 registry record count mismatch")
            semantic_root = _semantic_root(store)
            if semantic_root != EXPECTED_SEMANTIC_ROOT:
                raise RuntimeError("canonical K27 registry semantic root mismatch")
            routes = len(store.under(FRAME, GENERATION, (2,)))
            if routes != EXPECTED_ROUTE_RECORDS:
                raise RuntimeError("canonical K27 route projection count mismatch")
        self.runtime_database_sha256 = actual_sha
        self.source_database_sha256 = EXPECTED_SOURCE_DATABASE_SHA256
        self.cold_source_manifest_sha256 = EXPECTED_COLD_SOURCE_MANIFEST_SHA256
        self.registry_recipe_version = EXPECTED_RECIPE_VERSION
        self.semantic_root = semantic_root
        self.record_count = count
        self.route_count = routes

    def close(self) -> None:
        # Connections are request-scoped so ThreadingHTTPServer never shares sqlite objects across threads.
        return None

    def __enter__(self) -> "K27MemoryCityRuntime":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def status(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "frame": FRAME,
            "frame_generation": GENERATION,
            "source_database_sha256": self.source_database_sha256,
            "runtime_database_sha256": self.runtime_database_sha256,
            "cold_source_manifest_sha256": self.cold_source_manifest_sha256,
            "registry_recipe_version": self.registry_recipe_version,
            "semantic_registry_root": self.semantic_root,
            "record_count": self.record_count,
            "route_count": self.route_count,
            "registry_mode": "read_only",
            "currentness_scope": "repository-owned local registry consistency only",
            "authority": dict(AUTHORITY),
        }

    def get(self, object_id: str) -> dict[str, Any] | None:
        with MemoryStore(self.registry_path, read_only=True) as store:
            return store.get(object_id)

    def under(self, prefix: tuple[int, ...] = ()) -> list[dict[str, Any]]:
        K27Path(prefix)
        with MemoryStore(self.registry_path, read_only=True) as store:
            return store.under(FRAME, GENERATION, prefix)


class _Handler(BaseHTTPRequestHandler):
    runtime: K27MemoryCityRuntime

    def log_message(self, *_: Any) -> None:
        return

    def _reply(self, status: int, value: Any) -> None:
        body = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib HTTP handler contract
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._reply(200, self.runtime.status())
            return
        if parsed.path == "/object":
            key = parse_qs(parsed.query).get("id", [""])[0]
            if not key:
                self._reply(400, {"error": "id required"})
                return
            record = self.runtime.get(key)
            self._reply(200 if record is not None else 404, record or {"error": "not found"})
            return
        if parsed.path == "/under":
            raw = parse_qs(parsed.query).get("prefix", [""])[0]
            try:
                prefix = tuple(int(part) for part in raw.split(",") if part != "")
                records = self.runtime.under(prefix)
            except (ValueError, TypeError):
                self._reply(400, {"error": "prefix must contain comma-separated K27 digits 0..26"})
                return
            self._reply(200, {"prefix": list(prefix), "count": len(records), "records": records})
            return
        self._reply(404, {"error": "not found"})


def serve(repo_root: Path, host: str, port: int) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("K27 runtime refuses non-loopback binding")
    runtime = K27MemoryCityRuntime(repo_root)
    handler = type("K27RuntimeHandler", (_Handler,), {"runtime": runtime})
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        runtime.close()


def probe_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("probe refuses non-loopback URL")
    with urlopen(url, timeout=5) as response:  # noqa: S310 - host constrained above
        value = json.loads(response.read().decode("utf-8"))
    if value.get("source_database_sha256") != EXPECTED_SOURCE_DATABASE_SHA256 or value.get("semantic_registry_root") != EXPECTED_SEMANTIC_ROOT:
        raise RuntimeError("runtime probe source/semantic identity mismatch")
    runtime_sha = value.get("runtime_database_sha256")
    if not isinstance(runtime_sha, str) or len(runtime_sha) != 64:
        raise RuntimeError("runtime probe materialized database identity is malformed")
    if value.get("authority") != AUTHORITY:
        raise RuntimeError("runtime probe authority contract mismatch")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8772)
    parser.add_argument("--probe-url")
    args = parser.parse_args()
    if args.probe_url:
        print(json.dumps(probe_url(args.probe_url), sort_keys=True))
        return 0
    if args.serve:
        serve(Path(args.repo_root), args.host, args.port)
        return 0
    with K27MemoryCityRuntime(Path(args.repo_root)) as runtime:
        print(json.dumps(runtime.status(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
