"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9eb-[Q-SYS:HUMAN_3D_CODING_ARENA_SERVER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Local Human Control Surface)
DEPENDENCIES: __future__, argparse, http.server, json, mimetypes, pathlib, urllib.parse, typing, aura_coding_arena_3d
FUNCTIONS: CodingArenaServerState, dispatch_api_request, make_handler, serve, main
SYNOPSIS: Stdlib HTTP server for Aura's human-first 3D Coding Arena. Serves local topology APIs and static UI without provider calls.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from aura_coding_arena_3d import (
    apply_marked_edge,
    compile_action_capsule,
    load_arena_topology,
    select_micro_arena,
    simulate_model_route,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
FRONTEND_DIR = Path(__file__).resolve().parent / "aura_coding_arena"


class CodingArenaServerState:
    def __init__(self, repo_root: str | Path = ".", *, demo: bool = False):
        self.repo_root = Path(repo_root).resolve()
        self.demo = bool(demo)
        self.topology = load_arena_topology(self.repo_root, demo=self.demo)
        self.last_capsule: dict[str, Any] | None = None
        self.last_selection: dict[str, Any] | None = None

    def refresh(self, *, demo: bool | None = None) -> dict[str, Any]:
        if demo is not None:
            self.demo = bool(demo)
        self.topology = load_arena_topology(self.repo_root, demo=self.demo)
        return self.topology


def dispatch_api_request(
    state: CodingArenaServerState,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Pure dispatcher for API routes; tests can call this without opening sockets."""
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    route = parsed.path.rstrip("/") or "/"
    body = dict(payload or {})
    if method == "GET" and route == "/api/topology":
        demo = _query_bool(query.get("demo", [None])[0])
        if demo is not None and demo != state.demo:
            graph = state.refresh(demo=demo)
        else:
            graph = state.topology
        return 200, graph
    if method == "POST" and route in {"/api/select", "/api/expand"}:
        node_ids = _node_ids(body)
        depth = int(body.get("depth", 1 if route == "/api/select" else 2) or 1)
        result = select_micro_arena(
            state.topology,
            node_ids,
            depth=depth,
            human_instruction=str(body.get("human_instruction") or body.get("command") or ""),
        )
        state.last_selection = result
        return 200, result
    if method == "POST" and route == "/api/compile-capsule":
        node_ids = _node_ids(body)
        if not node_ids and state.last_selection:
            node_ids = list(state.last_selection.get("selected_node_ids", []) or [])
        capsule = compile_action_capsule(
            state.topology,
            node_ids,
            depth=int(body.get("depth", 1) or 1),
            human_instruction=str(body.get("human_instruction") or body.get("command") or ""),
        )
        state.last_capsule = capsule
        return 200, capsule
    if method == "POST" and route == "/api/simulate-route":
        capsule = body.get("capsule") if isinstance(body.get("capsule"), dict) else state.last_capsule
        if capsule is None:
            capsule = compile_action_capsule(
                state.topology,
                _node_ids(body),
                human_instruction=str(body.get("human_instruction") or body.get("command") or "simulate route"),
            )
        return 200, simulate_model_route(capsule).to_dict()
    if method == "POST" and route == "/api/mark-edge":
        source = str(body.get("source") or "")
        target = str(body.get("target") or "")
        if not source or not target:
            return 400, {"ok": False, "error": "source and target are required"}
        state.topology = apply_marked_edge(
            state.topology,
            source,
            target,
            kind=str(body.get("kind") or "candidate_missing_route"),
            status=str(body.get("status") or "missing"),
        )
        return 200, {"ok": True, "topology": state.topology}
    if method == "POST" and route == "/api/voice-intent":
        command = str(body.get("command") or "")
        node_ids = _node_ids(body)
        action = _voice_action(command)
        if action == "compile":
            capsule = compile_action_capsule(state.topology, node_ids, human_instruction=command)
            state.last_capsule = capsule
            return 200, {"action": action, "capsule": capsule}
        if action == "route":
            capsule = compile_action_capsule(state.topology, node_ids, human_instruction=command)
            state.last_capsule = capsule
            return 200, {"action": action, "capsule": capsule, "route_decision": capsule.get("route_decision")}
        if action == "expand":
            selection = select_micro_arena(state.topology, node_ids, depth=2, human_instruction=command)
            state.last_selection = selection
            return 200, {"action": action, "selection": selection}
        if action == "mark_missing":
            return 200, {"action": action, "message": "Choose a source and target node, then call /api/mark-edge."}
        selection = select_micro_arena(state.topology, node_ids, depth=1, human_instruction=command)
        state.last_selection = selection
        return 200, {"action": action, "selection": selection}
    return 404, {"ok": False, "error": f"Unknown route: {method} {route}"}


def make_handler(state: CodingArenaServerState):
    class CodingArenaHandler(BaseHTTPRequestHandler):
        server_version = "AuraCodingArena/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._send_json(*dispatch_api_request(state, "GET", self.path))
                return
            self._serve_static(parsed.path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    payload = {}
            except json.JSONDecodeError:
                self._send_json(400, {"ok": False, "error": "invalid JSON"})
                return
            self._send_json(*dispatch_api_request(state, "POST", parsed.path, payload))

        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_static(self, request_path: str) -> None:
            rel = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
            candidate = (FRONTEND_DIR / rel).resolve()
            try:
                candidate.relative_to(FRONTEND_DIR.resolve())
            except ValueError:
                self.send_error(403)
                return
            if not candidate.exists() or not candidate.is_file():
                self.send_error(404)
                return
            body = candidate.read_bytes()
            mime = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("content-type", mime)
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return CodingArenaHandler


def serve(
    repo_root: str | Path = ".",
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    demo: bool = False,
) -> HTTPServer:
    state = CodingArenaServerState(repo_root, demo=demo)
    server = HTTPServer((host, int(port)), make_handler(state))
    print(f"Aura Coding Arena listening on http://{host}:{port}")
    print("No model/provider APIs are called by this server.")
    server.serve_forever()
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aura's local 3D Coding Arena MVP.")
    parser.add_argument("--repo-root", default=".", help="AuraOS repository root")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--demo", action="store_true", help="Use the built-in offline demo topology")
    parser.add_argument("--print-topology", action="store_true", help="Print topology JSON and exit")
    args = parser.parse_args(argv)
    if args.print_topology:
        print(json.dumps(load_arena_topology(args.repo_root, demo=args.demo), indent=2, sort_keys=True))
        return 0
    serve(args.repo_root, host=args.host, port=args.port, demo=args.demo)
    return 0


def _node_ids(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("node_ids", payload.get("selected_node_ids", []))
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if item]
    return []


def _voice_action(command: str) -> str:
    lowered = str(command or "").lower()
    if "compile" in lowered or "capsule" in lowered:
        return "compile"
    if "send to worker" in lowered or "simulate route" in lowered or "route" in lowered:
        return "route"
    if "expand" in lowered or "show dependencies" in lowered or "isolate" in lowered:
        return "expand"
    if "mark missing" in lowered or "missing route" in lowered:
        return "mark_missing"
    return "select"


def _query_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on", "demo"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return None


if __name__ == "__main__":
    raise SystemExit(main())
