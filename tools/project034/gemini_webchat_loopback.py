from __future__ import annotations

import argparse
import json
import secrets
from dataclasses import fields
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib.parse import parse_qs, urlparse

from gemini_webchat_endpoint import (
    ArenaTurnEnvelopeV1,
    ArenaTurnResultV1,
    AuraToolRequestV1,
    BridgeRefusal,
    compile_bootstrap_prompt,
)
from gemini_webchat_relay import RelayStoreV1


class LoopbackContextV1:
    def __init__(self, root: str | Path) -> None:
        self.store = RelayStoreV1(root)
        self.root = self.store.root
        self.token_path = self.store.state_dir / "loopback_token.txt"
        self.currentness_path = self.store.state_dir / "arena_currentness_v1.json"
        self.token = self._load_or_create_token()

    def _load_or_create_token(self) -> str:
        if self.token_path.exists():
            token = self.token_path.read_text(encoding="utf-8").strip()
            if len(token) < 32:
                raise BridgeRefusal("LOOPBACK_TOKEN_INVALID")
            return token
        token = secrets.token_urlsafe(32)
        self.token_path.write_text(token + "\n", encoding="utf-8")
        try:
            self.token_path.chmod(0o600)
        except OSError:
            pass
        return token

    def currentness(self) -> Mapping[str, str]:
        if not self.currentness_path.exists():
            raise BridgeRefusal("CURRENTNESS_STATE_MISSING")
        data = json.loads(self.currentness_path.read_text(encoding="utf-8"))
        required = ("arena_sid", "arena_head", "currentness_hash")
        if any(not str(data.get(key, "")).strip() for key in required):
            raise BridgeRefusal("CURRENTNESS_STATE_INCOMPLETE")
        return {key: str(data[key]) for key in required}

    def load_turn(self, turn_id: str) -> ArenaTurnEnvelopeV1:
        path = self.store.turn_outbox / f"{turn_id}.json"
        if not path.exists():
            raise BridgeRefusal("TURN_NOT_FOUND", turn_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.pop("schema", None) != "ArenaTurnEnvelopeV1":
            raise BridgeRefusal("TURN_SCHEMA_MISMATCH", turn_id)
        return ArenaTurnEnvelopeV1(**data)


class GeminiLoopbackHandler(BaseHTTPRequestHandler):
    server_version = "AuraGeminiLoopback/0.1"

    @property
    def ctx(self) -> LoopbackContextV1:
        return self.server.ctx  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: Mapping[str, Any]) -> None:
        body = (json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {self.ctx.token}"

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._json(HTTPStatus.UNAUTHORIZED, {"status": "REFUSED", "code": "LOOPBACK_AUTH_REQUIRED"})
        return False

    def _read_json(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise BridgeRefusal("INVALID_CONTENT_LENGTH") from exc
        if length <= 0 or length > 2_000_000:
            raise BridgeRefusal("INVALID_BODY_LENGTH", str(length))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BridgeRefusal("INVALID_JSON_BODY") from exc
        if not isinstance(data, dict):
            raise BridgeRefusal("JSON_OBJECT_REQUIRED")
        return data

    def _handle_refusal(self, exc: BridgeRefusal) -> None:
        self._json(HTTPStatus.CONFLICT, {"status": "REFUSED", "code": exc.code, "message": exc.message})

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/v1/health":
                self._json(HTTPStatus.OK, {"status": "OK", "schema": "AuraGeminiLoopbackV1"})
                return
            if not self._require_auth():
                return
            if parsed.path == "/v1/turns/next":
                self._get_next_turn(parse_qs(parsed.query))
                return
            self._json(HTTPStatus.NOT_FOUND, {"status": "ERROR", "code": "NOT_FOUND"})
        except BridgeRefusal as exc:
            self._handle_refusal(exc)
        except Exception as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "ERROR", "code": "UNEXPECTED", "message": type(exc).__name__})

    def _get_next_turn(self, query: Mapping[str, list[str]]) -> None:
        binding = self.ctx.store.load_binding()
        endpoint_id = (query.get("endpoint_id") or [""])[0]
        visit_id = (query.get("visit_id") or [""])[0]
        if endpoint_id != binding.endpoint_id or visit_id != binding.visit_id:
            raise BridgeRefusal("ENDPOINT_POLL_BINDING_MISMATCH")
        pending = list(self.ctx.store.list_pending_turns())
        if not pending:
            self._json(HTTPStatus.OK, {"status": "EMPTY"})
            return
        turn_id = pending[0].stem
        envelope = self.ctx.load_turn(turn_id)
        current = self.ctx.currentness()
        if envelope.arena_sid != current["arena_sid"]:
            raise BridgeRefusal("ARENA_MISMATCH", envelope.arena_sid)
        from gemini_webchat_endpoint import admit_turn

        admit_turn(
            binding,
            envelope,
            current_arena_head=current["arena_head"],
            currentness_hash=current["currentness_hash"],
        )
        self._json(
            HTTPStatus.OK,
            {
                "status": "TURN_READY",
                "turn_id": envelope.turn_id,
                "capsule_id": envelope.capsule_id,
                "prompt_text": compile_bootstrap_prompt(binding, envelope),
                "envelope": {name.name: getattr(envelope, name.name) for name in fields(envelope)},
            },
        )

    def do_POST(self) -> None:
        try:
            if not self._require_auth():
                return
            parsed = urlparse(self.path)
            data = self._read_json()
            if parsed.path == "/v1/results":
                self._post_result(data)
                return
            if parsed.path == "/v1/tool-requests":
                self._post_tool_request(data)
                return
            self._json(HTTPStatus.NOT_FOUND, {"status": "ERROR", "code": "NOT_FOUND"})
        except BridgeRefusal as exc:
            self._handle_refusal(exc)
        except TypeError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"status": "REFUSED", "code": "SCHEMA_TYPE_ERROR", "message": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "ERROR", "code": "UNEXPECTED", "message": type(exc).__name__})

    def _post_result(self, data: Mapping[str, Any]) -> None:
        result = ArenaTurnResultV1(**data)
        envelope = self.ctx.load_turn(result.turn_id)
        current = self.ctx.currentness()
        out = self.ctx.store.accept_turn_result(
            envelope,
            result,
            current_arena_head=current["arena_head"],
            currentness_hash=current["currentness_hash"],
        )
        self._json(HTTPStatus.OK, {"status": "ACCEPTED", **out})

    def _post_tool_request(self, data: Mapping[str, Any]) -> None:
        request = AuraToolRequestV1(**data)
        envelope = self.ctx.load_turn(request.turn_id)
        current = self.ctx.currentness()
        tool_policy_path = self.ctx.store.state_dir / "tool_effect_classes_v1.json"
        if not tool_policy_path.exists():
            raise BridgeRefusal("TOOL_POLICY_MISSING")
        policy = json.loads(tool_policy_path.read_text(encoding="utf-8"))
        if not isinstance(policy, dict):
            raise BridgeRefusal("TOOL_POLICY_INVALID")
        out = self.ctx.store.accept_tool_request(
            envelope,
            request,
            current_arena_head=current["arena_head"],
            currentness_hash=current["currentness_hash"],
            tool_effect_classes={str(k): str(v) for k, v in policy.items()},
        )
        self._json(HTTPStatus.OK, {"status": "ACCEPTED", **out})


class GeminiLoopbackServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], ctx: LoopbackContextV1) -> None:
        super().__init__(address, GeminiLoopbackHandler)
        self.ctx = ctx


def serve(root: str | Path, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise BridgeRefusal("NON_LOOPBACK_BIND_REFUSED", host)
    ctx = LoopbackContextV1(root)
    server = GeminiLoopbackServer((host, port), ctx)
    print(f"Aura Gemini loopback listening on http://{host}:{port}")
    print(f"Bridge token file: {ctx.token_path}")
    server.serve_forever()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Aura Gemini web-chat local loopback relay")
    parser.add_argument("--root", default="~/.aura/gemini_webchat_bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    serve(args.root, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
