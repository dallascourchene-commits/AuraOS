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

from aura_architect_control import control_capabilities
from aura_arena_architect_connector import AuraArenaArchitectConnector

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8091
MAX_BODY_BYTES = 1_048_576
MAX_CANDIDATES = 8
MAX_LOAD_BYTES = 5_000_000
SERVER_VERSION = "AURA_ARENA_CONNECTOR_SERVER_V3"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_COMPARE = {
    "/v1/architect/compare": "http_external",
    "/v1/coding-arena/architect/compare": "coding_arena",
    "/v1/human-agent/architect/compare": "human_agent_arena",
}
_PREPARE = {
    "/v1/architect/prepare": "http_external",
    "/v1/coding-arena/architect/prepare": "coding_arena",
    "/v1/human-agent/architect/prepare": "human_agent_arena",
}
_SURGEON_OPEN = {
    "/v1/architect/surgeon/open": "http_external",
    "/v1/coding-arena/architect/surgeon/open": "coding_arena",
    "/v1/human-agent/architect/surgeon/open": "human_agent_arena",
}
_SURGEON_NEXT = {
    "/v1/architect/surgeon/next",
    "/v1/coding-arena/architect/surgeon/next",
    "/v1/human-agent/architect/surgeon/next",
}
_SURGEON_SUBMIT = {
    "/v1/architect/surgeon/submit",
    "/v1/coding-arena/architect/surgeon/submit",
    "/v1/human-agent/architect/surgeon/submit",
}
_SURGEON_STATUS = {
    "/v1/architect/surgeon/status",
    "/v1/coding-arena/architect/surgeon/status",
    "/v1/human-agent/architect/surgeon/status",
}
_COUNCIL_REPLAN = {
    "/v1/architect/council/replan",
    "/v1/coding-arena/architect/council/replan",
    "/v1/human-agent/architect/council/replan",
}


class ArenaConnectorServerState:
    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        connector: Any | None = None,
        auth_token: str = "",
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.connector = connector or AuraArenaArchitectConnector(self.repo_root)
        self.auth_token = str(auth_token or "")


def _error(message: str, status: int = 400) -> tuple[int, dict[str, Any]]:
    return status, {
        "ok": False,
        "error": str(message),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "production_mutation": False,
    }


def _bounded(body: dict[str, Any]) -> None:
    candidates = body.get("candidates") or []
    if not isinstance(candidates, list):
        raise ValueError("candidates must be an array")
    if len(candidates) > MAX_CANDIDATES:
        raise ValueError(f"at most {MAX_CANDIDATES} candidate plans are allowed")
    if "token_budget" in body:
        if isinstance(body["token_budget"], bool):
            raise ValueError("token_budget must be an integer")
        budget = int(body["token_budget"])
        if budget < 128 or budget > 12000:
            raise ValueError("token_budget must be between 128 and 12000")
    if "limit" in body:
        limit = int(body["limit"])
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
    if "max_bytes" in body:
        maximum = int(body["max_bytes"])
        if maximum < 1 or maximum > MAX_LOAD_BYTES:
            raise ValueError(f"max_bytes must be between 1 and {MAX_LOAD_BYTES}")


def _architect_kwargs(body: dict[str, Any], *, surface: str) -> dict[str, Any]:
    bilateral_contract = body.get("bilateral_contract")
    if bilateral_contract is not None and not isinstance(bilateral_contract, dict):
        raise ValueError("bilateral_contract must be an object")
    return {
        "objective": str(body.get("objective", "")),
        "candidates": list(body.get("candidates") or []),
        "required_capabilities": list(body.get("required_capabilities") or []),
        "control": body.get("control"),
        "surface": surface,
        "run_id": str(body.get("run_id", "")),
        "bilateral_contract": bilateral_contract,
        "confirmation_session_id": str(body.get("confirmation_session_id", "")),
    }


def dispatch_connector_request(
    state: ArenaConnectorServerState,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    route = urlparse(path).path.rstrip("/") or "/"
    body = dict(payload or {})
    if method == "GET" and route in {"/health", "/v1/health"}:
        return 200, {
            "ok": True,
            "version": SERVER_VERSION,
            "surfaces": [
                "coding_arena",
                "human_agent_arena",
                "mcp_external",
                "http_external",
                "container_external",
            ],
            "model_routing": "MODEL_COGNOME_ADAPTIVE",
            "local_output_vault": "Aura_Staging/refactor_output_vault",
            "human_review_required": True,
            "production_mutation": False,
        }
    if method == "GET" and route == "/v1/capabilities":
        return 200, {
            "ok": True,
            "architect": [
                "validate_control",
                "compare_plans",
                "prepare_refactor",
                "open_surgeon",
                "next_surgeon_turn",
                "submit_surgeon_output",
                "surgeon_status",
                "council_replan",
            ],
            "output_vault": ["list_runs", "load_artifact"],
            "model_gateway": ["route_best", "execute_best"],
            "policy_modes": ["ZERO_MODEL", "DIRECT", "CASCADE", "PANEL"],
            "controls": control_capabilities("http_external"),
            "paired_live_requires_authorization": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    try:
        _bounded(body)
        if method == "POST" and route == "/v1/architect/control/validate":
            result = state.connector.validate_control(body.get("control"), surface="http_external")
            return 200, result
        if method == "POST" and route in _COMPARE:
            result = state.connector.compare_plans(
                **_architect_kwargs(body, surface=_COMPARE[route])
            )
            return 200, result
        if method == "POST" and route in _PREPARE:
            result = state.connector.prepare_refactor(
                **_architect_kwargs(body, surface=_PREPARE[route]),
                target_file=body.get("target_file"),
                target_symbol=body.get("target_symbol"),
            )
            return (200 if result.get("ok") else 409), result
        if method == "POST" and route in _SURGEON_OPEN:
            result = state.connector.open_surgeon_session(
                **_architect_kwargs(body, surface=_SURGEON_OPEN[route]),
                provider=str(body.get("provider", "external")),
                model=str(body.get("model", "")),
            )
            return (200 if result.get("ok") else 409), result
        if method == "POST" and route in _SURGEON_NEXT:
            result = state.connector.surgeon_next(str(body.get("session_id", "")))
            return (200 if result.get("ok") else 409), result
        if method == "POST" and route in _SURGEON_SUBMIT:
            result = state.connector.surgeon_submit(
                session_id=str(body.get("session_id", "")),
                turn_id=str(body.get("turn_id", "")),
                response=str(body.get("response", "")),
                provider_usage=body.get("provider_usage"),
            )
            return (200 if result.get("ok") else 409), result
        if method == "POST" and route in _SURGEON_STATUS:
            result = state.connector.surgeon_status(str(body.get("session_id", "")))
            return (200 if result.get("ok") else 404), result
        if method == "POST" and route in _COUNCIL_REPLAN:
            result = state.connector.surgeon_replan(
                session_id=str(body.get("session_id", "")),
                remaining_act_capsules=list(body.get("remaining_act_capsules") or []),
                rationale=str(body.get("rationale", "")),
                prompt=str(body.get("prompt", "")),
                response=str(body.get("response", "")),
                provider_usage=dict(body.get("provider_usage") or {}),
            )
            return (200 if result.get("ok") else 409), result
        if method == "POST" and route == "/v1/refactor-outputs/list":
            return 200, state.connector.list_refactor_outputs(limit=int(body.get("limit", 50)))
        if method == "POST" and route == "/v1/refactor-outputs/load":
            result = state.connector.load_refactor_output(
                str(body.get("relative_path", "")),
                max_bytes=int(body.get("max_bytes", 2_000_000)),
            )
            return 200, result
        if method == "POST" and route == "/v1/models/route":
            result = state.connector.route_native_model(
                objective=str(body.get("objective", "")),
                purpose_digest=str(body.get("purpose_digest", "")),
                target_files=body.get("target_files"),
                target_symbols=body.get("target_symbols"),
                task_fields=body.get("task_fields"),
                token_budget=int(body.get("token_budget", 2400)),
                forced_model=body.get("forced_model"),
            )
            return 200, result
        if method == "POST" and route == "/v1/models/execute":
            result = state.connector.execute_native_model(
                objective=str(body.get("objective", "")),
                purpose_digest=str(body.get("purpose_digest", "")),
                execution_mode=str(body.get("execution_mode", "SHADOW")),
                authorization=body.get("authorization"),
                target_files=body.get("target_files"),
                target_symbols=body.get("target_symbols"),
                task_fields=body.get("task_fields"),
                token_budget=int(body.get("token_budget", 2400)),
                forced_model=body.get("forced_model"),
            )
            return (200 if result.get("status") != "DENIED" else 409), result
    except FileNotFoundError as exc:
        return _error(str(exc), 404)
    except (OverflowError, TypeError, ValueError) as exc:
        return _error(str(exc))
    return _error(f"Unknown route: {method} {route}", 404)


def make_handler(state: ArenaConnectorServerState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AuraArenaConnector/3.0"

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
                payload = json.loads(
                    (self.rfile.read(length) if length else b"{}").decode("utf-8") or "{}"
                )
                if not isinstance(payload, dict):
                    raise ValueError("JSON body must be an object")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                self._send(*_error(str(exc)))
                return
            self._send(*dispatch_connector_request(state, "POST", self.path, payload))

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("x-content-type-options", "nosniff")
            self.send_header("content-security-policy", "default-src 'none'")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(
    repo_root: str | Path = ".",
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    auth_token: str = "",
) -> None:
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
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AURA_CONNECTOR_PORT", str(DEFAULT_PORT))),
    )
    parser.add_argument("--auth-token", default=os.getenv("AURA_CONNECTOR_AUTH_TOKEN", ""))
    args = parser.parse_args(argv)
    serve(args.repo_root, host=args.host, port=args.port, auth_token=args.auth_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
