"""Bounded HTTP/container surface for Aura's shared Arena connector."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aura_arena_architect_connector import AuraArenaArchitectConnector

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8091
MAX_BODY_BYTES = 1_048_576
MAX_CANDIDATES = 8
SERVER_VERSION = "AURA_ARENA_CONNECTOR_SERVER_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class ArenaConnectorServerState:
    def __init__(self, repo_root: str | Path = ".", *, connector: Any | None = None, auth_token: str = "") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.connector = connector or AuraArenaArchitectConnector(self.repo_root)
        self.auth_token = str(auth_token or "")


def _error(message: str, status: int = 400) -> tuple[int, dict[str, Any]]:
    return status, {"ok": False, "error": str(message), "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def _bounded(body: dict[str, Any]) -> None:
    candidates = list(body.get("candidates") or [])
    if len(candidates) > MAX_CANDIDATES:
        raise ValueError(f"at most {MAX_CANDIDATES} candidate plans are allowed")
    budget = int(body.get("token_budget", 2400))
    if budget < 128 or budget > 12000:
        raise ValueError("token_budget must be between 128 and 12000")


def dispatch_connector_request(state: ArenaConnectorServerState, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    route = urlparse(path).path.rstrip("/") or "/"
    body = dict(payload or {})
    if method == "GET" and route in {"/health", "/v1/health"}:
        return 200, {"ok": True, "version": SERVER_VERSION, "surfaces": ["coding_arena", "human_agent_arena", "mcp", "container"], "model_routing": "MODEL_COGNOME_ADAPTIVE", "production_mutation": False}
    if method == "GET" and route == "/v1/capabilities":
        return 200, {"ok": True, "architect": ["compare_plans", "prepare_refactor"], "model_gateway": ["route_best", "execute_best"], "policy_modes": ["ZERO_MODEL", "DIRECT", "CASCADE", "PANEL"], "paired_live_requires_authorization": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    compare = {"/v1/architect/compare", "/v1/coding-arena/architect/compare", "/v1/human-agent/architect/compare"}
    prepare = {"/v1/architect/prepare", "/v1/coding-arena/architect/prepare", "/v1/human-agent/architect/prepare"}
    try:
        _bounded(body)
        if method == "POST" and route in compare:
            return 200, state.connector.compare_plans(objective=str(body.get("objective", "")), candidates=list(body.get("candidates") or []), required_capabilities=list(body.get("required_capabilities") or []))
        if method == "POST" and route in prepare:
            result = state.connector.prepare_refactor(objective=str(body.get("objective", "")), candidates=list(body.get("candidates") or []), required_capabilities=list(body.get("required_capabilities") or []), target_file=body.get("target_file"), target_symbol=body.get("target_symbol"))
            return (200 if result.get("ok") else 409), result
        if method == "POST" and route == "/v1/models/route":
            result = state.connector.route_native_model(objective=str(body.get("objective", "")), purpose_digest=str(body.get("purpose_digest", "")), target_files=body.get("target_files"), target_symbols=body.get("target_symbols"), task_fields=body.get("task_fields"), token_budget=int(body.get("token_budget", 2400)), forced_model=body.get("forced_model"))
            return 200, result
        if method == "POST" and route == "/v1/models/execute":
            result = state.connector.execute_native_model(objective=str(body.get("objective", "")), purpose_digest=str(body.get("purpose_digest", "")), execution_mode=str(body.get("execution_mode", "SHADOW")), authorization=body.get("authorization"), target_files=body.get("target_files"), target_symbols=body.get("target_symbols"), task_fields=body.get("task_fields"), token_budget=int(body.get("token_budget", 2400)), forced_model=body.get("forced_model"))
            return (200 if result.get("status") != "DENIED" else 409), result
    except (TypeError, ValueError) as exc:
        return _error(str(exc))
    return _error(f"Unknown route: {method} {route}", 404)


def make_handler(state: ArenaConnectorServerState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AuraArenaConnector/2.0"

        def do_GET(self) -> None:
            self._send(*dispatch_connector_request(state, "GET", self.path))

        def do_POST(self) -> None:
            if state.auth_token:
                supplied = self.headers.get("authorization", "").removeprefix("Bearer ").strip()
                if not hmac.compare_digest(supplied, state.auth_token):
                    self._send(*_error("unauthorized", 401))
                    return
            try:
                length = int(self.headers.get("content-length") or 0)
            except ValueError:
                self._send(*_error("invalid content-length"))
                return
            if length < 0 or length > MAX_BODY_BYTES:
                self._send(*_error("request body exceeds limit", 413))
                return
            try:
                payload = json.loads((self.rfile.read(length) if length else b"{}").decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("JSON body must be an object")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                self._send(*_error(str(exc)))
                return
            self._send(*dispatch_connector_request(state, "POST", self.path, payload))

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("x-content-type-options", "nosniff")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(repo_root: str | Path = ".", *, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, auth_token: str = "") -> None:
    state = ArenaConnectorServerState(repo_root, auth_token=auth_token)
    server = ThreadingHTTPServer((host, int(port)), make_handler(state))
    print(f"Aura Arena connector listening on http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aura's bounded Arena connector.")
    parser.add_argument("--repo-root", default=os.getenv("AURA_REPO_ROOT", "."))
    parser.add_argument("--host", default=os.getenv("AURA_CONNECTOR_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("AURA_CONNECTOR_PORT", str(DEFAULT_PORT))))
    parser.add_argument("--auth-token", default=os.getenv("AURA_CONNECTOR_AUTH_TOKEN", ""))
    args = parser.parse_args(argv)
    serve(args.repo_root, host=args.host, port=args.port, auth_token=args.auth_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
