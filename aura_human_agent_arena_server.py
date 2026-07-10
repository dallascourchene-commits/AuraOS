"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f4-[Q-SYS:HUMAN_AGENT_ARENA_SERVER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Local Human Agent Arena HTTP Surface)
DEPENDENCIES: __future__, argparse, http.server, json, mimetypes, pathlib, urllib.parse, typing, aura_human_agent_arena
FUNCTIONS: HumanAgentArenaServerState, dispatch_api_request, make_handler, serve, main
SYNOPSIS: Stdlib HTTP server for the Human Agent Arena. Serves local state/events/command endpoints
and static UI with polling (no WebSockets). Reuses existing Coding Arena topology functions read-only.
No new dependencies. No provider APIs called.
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

from aura_human_agent_arena import HumanAgentArena


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8090
FRONTEND_DIR = Path(__file__).resolve().parent / "aura_human_agent_arena"


class HumanAgentArenaServerState:
    """Holds the HumanAgentArena instance and serves as the server state container."""

    def __init__(self, repo_root: str | Path = ".", *, demo: bool = False):
        self.repo_root = Path(repo_root).resolve()
        self.demo = bool(demo)
        self.arena = HumanAgentArena(self.repo_root, demo=self.demo)


def _handle_civic_api(method: str, route: str, parsed, body: dict) -> tuple[int, dict]:
    """Handle Civic Commons Arena API requests."""
    from urllib.parse import urlparse
    path_parts = parsed.path.strip("/").split("/")
    # /api/civic/status, /api/civic/sessions, /api/civic/sessions/{id}/...
    PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
    VSA_PATCH_AUTHORITY = False

    def _err(msg, code=400): return code, {"ok": False, "error": msg,
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    try:
        from aura_civic_runtime import (
            create_civic_session, get_session, run_full_demo,
            add_contribution, match_resources, run_mitosis, run_scenarios,
            get_consent, record_consent_response, run_what_if,
            create_pilot, get_issue_pulse, export_packet, close_session,
            civic_status, select_profiles,
        )
    except Exception as e:
        return _err(f"civic_runtime_unavailable: {e}", 503)

    # GET /api/civic/status
    if method == "GET" and route == "/api/civic/status":
        from aura_civic_snapshots import list_snapshots
        snaps = list_snapshots()
        return 200, {"ok": True, "civic_available": True, "snapshots": snaps.get("snapshots", []),
                     "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    # POST /api/civic/sessions
    if method == "POST" and route == "/api/civic/sessions":
        objective = body.get("objective", "")
        story = body.get("story", "hairstylist")
        r = create_civic_session(objective)
        if r["ok"] and story:
            from aura_civic_runtime import _update_session
            _update_session(r["session"]["session_id"], {"story": story})
        return 200, r

    # GET /api/civic/sessions/{id}
    if method == "GET" and len(path_parts) == 4 and path_parts[2] == "sessions":
        sid = path_parts[3]
        return 200, get_session(sid)

    # POST /api/civic/sessions/{id}/profiles
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "profiles":
        sid = path_parts[3]
        return 200, select_profiles(sid, body.get("profile_refs", []))

    # POST /api/civic/sessions/{id}/contributions
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "contributions":
        sid = path_parts[3]
        return 200, add_contribution(sid, body)

    # POST /api/civic/sessions/{id}/resource-match
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "resource-match":
        return 200, match_resources(path_parts[3])

    # POST /api/civic/sessions/{id}/mitosis
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "mitosis":
        return 200, run_mitosis(path_parts[3])

    # POST /api/civic/sessions/{id}/scenarios
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "scenarios":
        return 200, run_scenarios(path_parts[3])

    # POST /api/civic/sessions/{id}/responses
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "responses":
        return 200, record_consent_response(path_parts[3], body)

    # GET /api/civic/sessions/{id}/consent
    if method == "GET" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "consent":
        return 200, get_consent(path_parts[3])

    # GET /api/civic/sessions/{id}/map-manifest
    if method == "GET" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "map-manifest":
        s = get_session(path_parts[3])
        if s["ok"]:
            mm = s["session"].get("map_manifest", {})
            return 200, {"ok": True, "map_manifest": mm, "accessible_table_parity": True,
                         "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return 200, s

    # GET /api/civic/sessions/{id}/evidence/{object_id}
    if method == "GET" and len(path_parts) == 6 and path_parts[2] == "sessions" and path_parts[4] == "evidence":
        s = get_session(path_parts[3])
        if s["ok"]:
            oid = path_parts[5]
            instruments = s["session"].get("legal_instruments", [])
            for li in instruments:
                if li.get("id", li.get("source_id", "")) == oid:
                    return 200, {"ok": True, "evidence": li,
                                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return 404, _err("evidence not found", 404)

    # GET /api/civic/sessions/{id}/legal/{scenario_id}
    if method == "GET" and len(path_parts) == 6 and path_parts[2] == "sessions" and path_parts[4] == "legal":
        s = get_session(path_parts[3])
        if s["ok"]:
            scenario_id = path_parts[5]
            instruments = s["session"].get("legal_instruments", [])
            # Filter instruments by scenario_id if provided
            if scenario_id:
                filtered = [li for li in instruments if li.get("scenario_id") == scenario_id]
                instruments = filtered
            return 200, {"ok": True, "legal_instruments": instruments,
                         "no_legal_approval": True, "disclaimer": "Aura is not providing legal advice.",
                         "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return 200, s

    # GET /api/civic/sessions/{id}/issue-pulse
    if method == "GET" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "issue-pulse":
        return 200, get_issue_pulse(path_parts[3])

    # POST /api/civic/sessions/{id}/what-if
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "what-if":
        return 200, run_what_if(path_parts[3], body)

    # POST /api/civic/sessions/{id}/pilot
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "pilot":
        return 200, create_pilot(path_parts[3], body.get("scenario_id", ""))

    # POST /api/civic/sessions/{id}/export
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "export":
        return 200, export_packet(path_parts[3])

    # POST /api/civic/sessions/{id}/close
    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions" and path_parts[4] == "close":
        return 200, close_session(path_parts[3])

    return 404, _err("civic route not found", 404)


def dispatch_api_request(
    state: HumanAgentArenaServerState,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Pure dispatcher for Human Agent Arena API routes; tests can call without sockets.

    Routes:
        GET  /api/human-agent/state   — return current live state
        GET  /api/human-agent/events  — return events since ?since=<index>
        POST /api/human-agent/command — route a command and return result
        GET  /api/human-agent/topology — return the underlying topology (read-only)
    """
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    route = parsed.path.rstrip("/") or "/"
    body = dict(payload or {})

    # ---- Civic Commons Arena API ----
    if route.startswith("/api/civic"):
        return _handle_civic_api(method, route, parsed, body)

    # GET /api/human-agent/state
    if method == "GET" and route == "/api/human-agent/state":
        return 200, {
            "ok": True,
            "version": "AURA_HUMAN_AGENT_ARENA_V1",
            "state": state.arena.get_state(),
            "topology": state.arena.topology,
            "patch_authority": "exact_source_spans_and_hashes_only",
            "vsa_patch_authority": False,
        }

    # GET /api/human-agent/events
    if method == "GET" and route == "/api/human-agent/events":
        since = _query_int(query.get("since", [None])[0], default=0)
        return 200, state.arena.get_events(since=since)

    # GET /api/human-agent/topology
    if method == "GET" and route == "/api/human-agent/topology":
        return 200, state.arena.topology

    # GET /api/human-agent/cost-telemetry — Cost Observatory panel data
    if method == "GET" and route == "/api/human-agent/cost-telemetry":
        try:
            from aura_cost_telemetry_events import get_telemetry_stream, visual_state_for_measurement_class, visual_state_for_savings
            from aura_empirical_cost_ledger import EmpiricalCostLedger
            stream = get_telemetry_stream()
            ledger = EmpiricalCostLedger(repo_root=state.repo_root)
            history = ledger.get_history(limit=10)
            ledger.close()
            return 200, {
                "ok": True,
                "event_count": stream.event_count(),
                "recent_events": stream.get_events(limit=20),
                "recent_runs": history,
                "visual_states": {
                    "measured": "green",
                    "estimated": "yellow",
                    "unavailable": "grey",
                    "verified": "green",
                    "invalidated": "red",
                    "counterfactual": "purple",
                },
                "patch_authority": "exact_source_spans_and_hashes_only",
                "vsa_patch_authority": False,
            }
        except Exception as exc:
            return 200, {
                "ok": True,
                "event_count": 0,
                "recent_events": [],
                "recent_runs": [],
                "note": f"Cost telemetry unavailable: {exc}",
                "patch_authority": "exact_source_spans_and_hashes_only",
                "vsa_patch_authority": False,
            }

    # GET /api/human-agent/cost-events — SSE-style event stream
    if method == "GET" and route == "/api/human-agent/cost-events":
        try:
            from aura_cost_telemetry_events import get_telemetry_stream
            since = _query_float(query.get("since", [None])[0], default=0.0)
            stream = get_telemetry_stream()
            events = stream.get_events(since=since, limit=100)
            return 200, {"ok": True, "events": events, "count": len(events),
                         "patch_authority": "exact_source_spans_and_hashes_only",
                         "vsa_patch_authority": False}
        except Exception as exc:
            return 200, {"ok": True, "events": [], "count": 0,
                         "note": f"Cost events unavailable: {exc}",
                         "patch_authority": "exact_source_spans_and_hashes_only",
                         "vsa_patch_authority": False}

    # POST /api/human-agent/command
    if method == "POST" and route == "/api/human-agent/command":
        command = str(body.get("command") or "")
        if not command.strip():
            return 400, {"ok": False, "error": "command is required"}
        selected_node_ids = _node_ids(body)
        mode = str(body.get("mode") or "explore").strip()
        if mode not in {"explore", "diagnose", "hypothesize", "prepare"}:
            mode = "explore"
        result = state.arena.route_command(
            command,
            selected_node_ids=selected_node_ids,
            mode=mode,
        )
        return 200, result

    return 404, {"ok": False, "error": f"Unknown route: {method} {route}"}


def make_handler(state: HumanAgentArenaServerState):
    class HumanAgentArenaHandler(BaseHTTPRequestHandler):
        server_version = "AuraHumanAgentArena/0.1"

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

    return HumanAgentArenaHandler


def serve(
    repo_root: str | Path = ".",
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    demo: bool = False,
) -> HTTPServer:
    state = HumanAgentArenaServerState(repo_root, demo=demo)
    server = HTTPServer((host, int(port)), make_handler(state))
    print(f"Aura Human Agent Arena listening on http://{host}:{port}")
    print("No model/provider APIs are called by this server.")
    print("Polling /api/human-agent/state for live updates (no WebSockets).")
    server.serve_forever()
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aura's local Human Agent Arena MVP.")
    parser.add_argument("--repo-root", default=".", help="AuraOS repository root")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--demo", action="store_true", help="Use the built-in offline demo topology")
    args = parser.parse_args(argv)
    serve(args.repo_root, host=args.host, port=args.port, demo=args.demo)
    return 0


def _node_ids(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("selected_node_ids", payload.get("node_ids", []))
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if item]
    return []


def _query_int(value: str | None, *, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        return default


def _query_float(value: str | None, *, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return max(0.0, float(value))
    except (ValueError, TypeError):
        return default


if __name__ == "__main__":
    raise SystemExit(main())