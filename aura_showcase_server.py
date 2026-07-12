"""Unified Winnipeg Civic and Human Agent Arena showcase server.

The server is intentionally additive. Existing Human Agent and Civic endpoints
are delegated to Aura's established server dispatcher; guided-project endpoints
compose those systems without granting production mutation or civic authority.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path
from typing import Any, TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from aura_civic_guided_project import (
    advance_project,
    back_project,
    get_guide,
    list_projects,
    project_map,
    record_response,
    start_project,
)
from aura_human_agent_guidance import answer_guidance_question, build_guidance_packet
if TYPE_CHECKING:
    from aura_human_agent_arena_server import HumanAgentArenaServerState
from aura_showcase_handoff import import_handoff_into_workflow

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SHOWCASE_VERSION = "AURA_WINNIPEG_SHOWCASE_V3"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8091
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
MAX_BODY_BYTES = 1_000_000


class ShowcaseState:
    def __init__(self, repo_root: str | Path, *, demo_project: str, auto_start: bool) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._human_agent: Any = None
        self.demo_project = demo_project
        self.default_session_id = ""
        if auto_start:
            started = start_project(demo_project)
            if started.get("ok"):
                self.default_session_id = str(started["session"]["session_id"])

    @property
    def human_agent(self) -> "HumanAgentArenaServerState":
        """Load Human Agent modules and topology only when the handoff is used."""
        if self._human_agent is None:
            from aura_human_agent_arena_server import HumanAgentArenaServerState
            self._human_agent = HumanAgentArenaServerState(self.repo_root, demo=True)
        return self._human_agent

    def close(self) -> None:
        if self._human_agent is not None:
            self._human_agent.close()


def _json(status: int, payload: dict[str, Any]) -> tuple[int, str, bytes]:
    packet = {
        **payload,
        "patch_authority": payload.get("patch_authority", PATCH_AUTHORITY),
        "vsa_patch_authority": payload.get("vsa_patch_authority", VSA_PATCH_AUTHORITY),
    }
    body = json.dumps(packet, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    return status, "application/json; charset=utf-8", body


def _error(message: str, status: int = 400) -> tuple[int, str, bytes]:
    return _json(status, {"ok": False, "error": message})


def _parts(path: str) -> list[str]:
    return [part for part in path.strip("/").split("/") if part]


def dispatch_showcase_request(
    state: ShowcaseState,
    method: str,
    raw_path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, str, bytes]:
    parsed = urlparse(raw_path)
    route = parsed.path.rstrip("/") or "/"
    query = parse_qs(parsed.query)
    body = dict(payload or {})
    parts = _parts(route)

    if method == "GET" and route == "/api/showcase/status":
        guide = get_guide(state.default_session_id) if state.default_session_id else None
        return _json(200, {
            "ok": True,
            "version": SHOWCASE_VERSION,
            "title": "Aura Winnipeg Community Pathways Lab",
            "default_project_id": state.demo_project,
            "default_session_id": state.default_session_id,
            "guide": guide,
            "human_agent_available": True,
            "fixture_mode": True,
            "zero_raw_civic_data_network_calls": True,
            "optional_public_basemap_network_calls": True,
            "basemap_provider": "OpenStreetMap standard raster tiles",
            "basemap_offline_fallback": "Aura governed synthetic grid",
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        })

    if method == "GET" and route == "/api/showcase/projects":
        return _json(200, list_projects())

    if method == "POST" and len(parts) == 5 and parts[:3] == ["api", "showcase", "projects"] and parts[4] == "start":
        project_id = parts[3]
        result = start_project(project_id)
        if result.get("ok"):
            state.default_session_id = str(result["session"]["session_id"])
        return _json(200 if result.get("ok") else 400, result)

    if len(parts) >= 5 and parts[:3] == ["api", "showcase", "sessions"]:
        session_id = parts[3]
        action = parts[4]
        if method == "GET" and action == "guide":
            result = get_guide(session_id)
            return _json(200 if result.get("ok") else 404, result)
        if method == "GET" and action == "map":
            try:
                zoom = float(query.get("zoom", [11])[0])
            except (TypeError, ValueError):
                zoom = 11.0
            result = project_map(session_id, zoom=zoom, viewer_scope=str(query.get("viewer_scope", ["community"])[0]))
            return _json(200 if result.get("ok") else 400, result)
        if method == "POST" and action == "advance":
            result = advance_project(session_id)
            return _json(200 if result.get("ok") else 409, result)
        if method == "POST" and action == "back":
            result = back_project(session_id)
            return _json(200 if result.get("ok") else 409, result)
        if method == "POST" and action == "respond":
            result = record_response(session_id, body)
            return _json(200 if result.get("ok") else 400, result)
        if method == "POST" and action == "handoff":
            result = import_handoff_into_workflow(state.human_agent.workflow, state.repo_root, session_id)
            return _json(200 if result.get("ok") else 409, result)

    if method == "GET" and route == "/api/human-agent/guide":
        workflow = state.human_agent.workflow.get_state()
        return _json(200, build_guidance_packet(workflow))

    if method == "POST" and route == "/api/human-agent/guide/ask":
        question = str(body.get("question") or "").strip()
        if not question:
            return _error("question is required", 400)
        workflow = state.human_agent.workflow.get_state()
        guide = build_guidance_packet(workflow)
        return _json(200, answer_guidance_question(guide, question))

    if route.startswith("/api/human-agent") or route.startswith("/api/coding-workbench") or route.startswith("/api/civic"):
        from aura_human_agent_arena_server import dispatch_api_request
        status, result = dispatch_api_request(state.human_agent, method, raw_path, body)
        return _json(status, result)

    return _error("showcase route not found", 404)


def _static_response(route: str) -> tuple[int, str, bytes]:
    relative = "index.html" if route in {"/", "/index.html"} else route.lstrip("/")
    if relative not in {"index.html", "app.js", "civic.js", "human.js", "styles.css"}:
        return _error("static asset not found", 404)
    path = (STATIC_DIR / relative).resolve()
    try:
        path.relative_to(STATIC_DIR.resolve())
    except ValueError:
        return _error("invalid static path", 400)
    if not path.is_file():
        return _error("static asset not found", 404)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if mime.startswith("text/") or mime in {"application/javascript", "application/json"}:
        mime += "; charset=utf-8"
    return 200, mime, path.read_bytes()


def make_handler(state: ShowcaseState):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _payload(self) -> dict[str, Any]:
            length = min(MAX_BODY_BYTES, max(0, int(self.headers.get("Content-Length", "0") or 0)))
            if not length:
                return {}
            raw = self.rfile.read(length)
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}
            return value if isinstance(value, dict) else {}

        def do_GET(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            if route.startswith("/api/"):
                self._send(*dispatch_showcase_request(state, "GET", self.path))
            else:
                self._send(*_static_response(route))

        def do_POST(self) -> None:  # noqa: N802
            self._send(*dispatch_showcase_request(state, "POST", self.path, self._payload()))

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def serve(*, host: str, port: int, repo_root: str | Path, demo_project: str, auto_start: bool) -> None:
    state = ShowcaseState(repo_root, demo_project=demo_project, auto_start=auto_start)
    server = HTTPServer((host, port), make_handler(state))
    try:
        print(f"Aura Winnipeg showcase: http://{host}:{port}")
        server.serve_forever()
    finally:
        state.close()
        server.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aura Winnipeg Civic + Human Agent showcase")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--demo-project", default="winnipeg_pathways")
    parser.add_argument("--no-auto-start", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    serve(
        host=args.host,
        port=args.port,
        repo_root=args.repo_root,
        demo_project=args.demo_project,
        auto_start=not args.no_auto_start,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
