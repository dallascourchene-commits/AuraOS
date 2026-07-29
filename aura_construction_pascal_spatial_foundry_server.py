"""Composed Aura Construction Spatial Foundry server with the PR 2 Pascal organ.

The module extends the PR 1 composed server without replacing it. Pascal is a
same-origin, local-only, disposable presentation surface. If its pinned fixture
is absent or invalid, every existing PR 1 route and static surface remains
available and the Pascal API fails closed as unavailable.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from aura_bilateral_live_repair_foundry import BilateralLiveRepairError
from aura_construction_spatial_foundry_server import (
    CONSTRUCTION_FOUNDRY_SERVER_VERSION,
    ConstructionFoundryShowcaseState,
    _error,
    _json,
    _static_response as construction_static_response,
    dispatch_construction_foundry_request,
)
from aura_event_contracts import stable_digest
from aura_showcase_live_repair_server import DEFAULT_HOST, DEFAULT_PORT, MAX_BODY_BYTES
from aura_pascal_spatial_presentation import (
    AuraPascalBridgeMessage,
    PascalBridgeAction,
    PascalPresentationError,
    PascalPresentationRegistry,
    load_pascal_compatibility_fixture,
)

PASCAL_FOUNDRY_SERVER_VERSION = "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_SERVER_V1"
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
LOGGER = logging.getLogger(__name__)
_LOOPBACK_HOST = re.compile(r"^(?:localhost|127\.0\.0\.1|::1)$")
_SAFE_STATIC = frozenset(
    {
        "pascal-workbench/index.html",
        "pascal-workbench/pascal-workbench.css",
        "pascal-workbench/pascal-workbench.js",
        "pascal-workbench/fixture.json",
        "pascal-workbench/artifact-manifest.json",
        "pascal-workbench/coordinate-receipt.json",
        "pascal-construction-foundry.js",
    }
)


class PascalFoundryShowcaseState(ConstructionFoundryShowcaseState):
    """PR 1 state plus one bounded Pascal presentation registry."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        demo_project: str,
        auto_start: bool,
        presentation_origin: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(repo_root, demo_project=demo_project, auto_start=auto_start, **kwargs)
        self.presentation_origin = _loopback_origin(presentation_origin)
        self.pascal_load_error = ""
        self.pascal_source_lock = None
        self.pascal_manifest = None
        self.pascal_coordinate_receipt = None
        self.pascal_scene: dict[str, Any] | None = None
        self.pascal_registry: PascalPresentationRegistry | None = None
        try:
            lock, manifest, coordinate, scene = load_pascal_compatibility_fixture(str(self.repo_root))
            self.pascal_source_lock = lock
            self.pascal_manifest = manifest
            self.pascal_coordinate_receipt = coordinate
            self.pascal_scene = scene
            self.pascal_registry = PascalPresentationRegistry(manifest=manifest, coordinate_receipt=coordinate)
        except (OSError, json.JSONDecodeError, PascalPresentationError, ValueError) as exc:
            self.pascal_load_error = str(exc)

    @property
    def pascal_available(self) -> bool:
        return all((self.pascal_registry, self.pascal_source_lock, self.pascal_manifest, self.pascal_coordinate_receipt, self.pascal_scene))

    def require_pascal_registry(self) -> PascalPresentationRegistry:
        if not self.pascal_available or self.pascal_registry is None:
            raise PascalPresentationError("Pascal presentation organ is unavailable; the PR 1 Construction Foundry remains active")
        return self.pascal_registry

    def pascal_manifest_response(self) -> dict[str, Any]:
        if not self.pascal_available:
            return {"ok": False, "available": False, "reason": self.pascal_load_error or "Pascal compatibility fixture is unavailable", "pr1_fallback_available": True, "construction_foundry_server_version": CONSTRUCTION_FOUNDRY_SERVER_VERSION, "pascal_foundry_server_version": PASCAL_FOUNDRY_SERVER_VERSION}
        assert self.pascal_source_lock is not None
        assert self.pascal_manifest is not None
        assert self.pascal_coordinate_receipt is not None
        return {"ok": True, "available": True, "source_lock": self.pascal_source_lock.to_dict(), "artifact_manifest": self.pascal_manifest.to_dict(), "coordinate_receipt": self.pascal_coordinate_receipt.to_dict(), "working_copy_only": True, "external_asset_fetch": False, "persistent_canonical_storage": False, "construction_truth": False, "survey_authority": False, "execution_authority": False, "human_review_required": True, "construction_foundry_server_version": CONSTRUCTION_FOUNDRY_SERVER_VERSION, "pascal_foundry_server_version": PASCAL_FOUNDRY_SERVER_VERSION}

    def start_pascal_session(self) -> dict[str, Any]:
        registry = self.require_pascal_registry()
        assert self.pascal_manifest is not None and self.pascal_coordinate_receipt is not None and self.pascal_scene is not None
        render_plan_digest = stable_digest({"kind": "PASCAL_LOCAL_PRESENTATION", "artifact_digest": self.pascal_manifest.artifact_digest, "coordinate_receipt_digest": self.pascal_coordinate_receipt.receipt_digest, "views": ["2D", "3D"], "external_asset_fetch": False, "persistent_canonical_storage": False, "renderer_authority": False}, digest_size=32)
        session = registry.create(spatial_scene_digest=self.pascal_coordinate_receipt.spatial_scene_digest, render_plan_digest=render_plan_digest, expected_origin=self.presentation_origin)
        return {"ok": True, "session": session.status(), "scene": self.pascal_scene, "artifact_manifest": self.pascal_manifest.to_dict(), "workbench_path": "/pascal-workbench/index.html", "sandbox": "allow-scripts allow-same-origin", "same_origin_required": True, "external_asset_fetch": False, "persistent_canonical_storage": False, "construction_truth": False, "execution_authority": False}

    def close(self) -> None:
        if self.pascal_registry is not None:
            self.pascal_registry.dissolve_all()
        super().close()


def _loopback_origin(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise PascalPresentationError("presentation_origin must be an HTTP(S) loopback origin")
    if not _LOOPBACK_HOST.fullmatch(parsed.hostname):
        raise PascalPresentationError("presentation_origin must remain loopback-only")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise PascalPresentationError("presentation_origin must not contain a path, query, or fragment")
    port = parsed.port
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    return f"{parsed.scheme}://{host}{f':{port}' if port is not None else ''}"


def _session_route(route: str) -> tuple[str, str] | None:
    parts = tuple(part for part in route.split("/") if part)
    if len(parts) < 5 or parts[:4] != ("api", "construction", "pascal", "session"):
        return None
    return parts[4], "/".join(parts[5:])


def _body_must_not_supply_identity(body: Mapping[str, Any]) -> None:
    forbidden = {"expected_origin", "origin", "spatial_scene_digest", "render_plan_digest", "pascal_artifact_digest", "coordinate_receipt_digest", "state_binding_digest", "sequence", "nonce", "direction", "message_digest"}
    supplied = sorted(forbidden.intersection(body))
    if supplied:
        raise PascalPresentationError(f"request cannot supply server-owned Pascal session identity: {supplied}")


def dispatch_pascal_foundry_request(state: PascalFoundryShowcaseState, method: str, raw_path: str, payload: Mapping[str, Any] | None = None, request_origin: str | None = None) -> tuple[int, str, bytes]:
    route = urlparse(raw_path).path.rstrip("/") or "/"
    body = dict(payload or {})
    try:
        if method == "GET" and route == "/api/construction/pascal/manifest":
            response = state.pascal_manifest_response()
            return _json(200 if response["available"] else 503, response)
        if method == "POST" and route == "/api/construction/pascal/session/start":
            if body:
                _body_must_not_supply_identity(body)
                if set(body) != {"client_request_id"}:
                    raise PascalPresentationError("Pascal session start accepts only an optional client_request_id")
            return _json(200, state.start_pascal_session())
        parsed = _session_route(route)
        if parsed is not None:
            session_id, suffix = parsed
            session = state.require_pascal_registry().get(session_id)
            if method == "GET" and not suffix:
                return _json(200, {"ok": True, "session": session.status()})
            if method == "POST" and suffix == "command":
                if set(body) != {"action", "payload"} or not isinstance(body.get("payload"), Mapping):
                    raise PascalPresentationError("command request requires exactly action and payload")
                message = session.issue_parent_message(PascalBridgeAction(str(body["action"])), body["payload"])
                return _json(200, {"ok": True, "message": message.to_dict(), "session": session.status()})
            if method == "POST" and suffix == "event":
                if set(body) != {"message"} or not isinstance(body["message"], Mapping):
                    raise PascalPresentationError("event request requires exactly one message object")
                message = AuraPascalBridgeMessage.from_mapping(body["message"])
                result = session.accept(message, origin=request_origin)
                return _json(200, {"ok": True, "acceptance": result, "session": session.status()})
            if method == "POST" and suffix == "dissolution/finalize":
                if set(body) != {"iframe_removed"} or body["iframe_removed"] is not True:
                    raise PascalPresentationError("dissolution finalization requires iframe_removed=true")
                receipt = session.mark_iframe_removed()
                return _json(200, {"ok": True, "dissolution_receipt": receipt, "session": session.status()})
    except (PascalPresentationError, BilateralLiveRepairError, TypeError, ValueError, KeyError) as exc:
        return _error(str(exc), 409)
    except Exception:
        LOGGER.exception("unexpected Pascal Construction Foundry request failure")
        return _error("internal Pascal Construction Foundry error", 500)
    return dispatch_construction_foundry_request(state, method, raw_path, body)


_PASCAL_MARKUP = b"""
<section id="pascal-construction-foundry" class="foundry-grid" aria-label="Pascal Construction presentation organ">
  <article class="foundry-card pascal-controller">
    <p class="eyebrow">PR 2 - Pascal presentation organ</p><h2>Local 2D / 3D workbench</h2>
    <p id="pascal-foundry-status">Pascal workbench not started.</p>
    <div class="pascal-controls" role="group" aria-label="Pascal presentation controls">
      <button type="button" data-pascal-action="launch">Launch</button><button type="button" data-pascal-action="2d" disabled>2D</button><button type="button" data-pascal-action="3d" disabled>3D</button><button type="button" data-pascal-action="storey" disabled>Next storey</button><button type="button" data-pascal-action="dimensions" disabled>Dimensions</button><button type="button" data-pascal-action="reset" disabled>Reset</button><button type="button" data-pascal-action="dissolve" disabled>Dissolve</button>
    </div><pre id="pascal-foundry-receipt">No Pascal receipt retained.</pre>
  </article><article class="foundry-card pascal-stage-card"><div id="pascal-workbench-host" class="pascal-workbench-host" aria-live="polite"></div></article>
</section>
"""
_PASCAL_SCRIPT = b'  <script src="pascal-construction-foundry.js"></script>\n'


def _static_response(route: str) -> tuple[int, str, bytes]:
    normalized = route.lstrip("/")
    if normalized == "pascal-workbench":
        normalized = "pascal-workbench/index.html"
    if normalized in _SAFE_STATIC:
        path = STATIC_DIR / normalized
        if not path.is_file() or path.is_symlink():
            return _error("Pascal static asset not found", 404)
        media_type = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8"}.get(path.suffix, "application/octet-stream")
        return 200, media_type, path.read_bytes()
    status, content_type, body = construction_static_response(route)
    if status == 200 and route in {"/", "/index.html"}:
        if b'id="pascal-construction-foundry"' not in body:
            body = body.replace(b'<section class="foundry-authority"', _PASCAL_MARKUP + b'\n  <section class="foundry-authority"', 1)
        if b"pascal-construction-foundry.js" not in body:
            body = body.replace(b"</body>", _PASCAL_SCRIPT + b"</body>", 1)
    return status, content_type, body


def make_handler(state: PascalFoundryShowcaseState):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            for name, value in (("Content-Type", content_type), ("Content-Length", str(len(body))), ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"), ("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https://tile.openstreetmap.org data:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'")):
                self.send_header(name, value)
            self.end_headers(); self.wfile.write(body)

        def _payload(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
            except (TypeError, ValueError) as exc:
                raise PascalPresentationError("Content-Length must be a valid integer") from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise PascalPresentationError(f"request body must be between 0 and {MAX_BODY_BYTES} bytes")
            raw = self.rfile.read(length) if length else b""
            if not raw: return {}
            try: value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise PascalPresentationError("request body must be valid UTF-8 JSON") from exc
            if not isinstance(value, dict): raise PascalPresentationError("request body must be a JSON object")
            return value

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            self._send(*(dispatch_pascal_foundry_request(state, "GET", self.path) if route.startswith("/api/") else _static_response(route)))

        def do_POST(self) -> None:
            try: payload = self._payload()
            except PascalPresentationError as exc:
                self._send(*_error(str(exc), 400)); return
            request_origin = self.headers.get("Origin")
            self._send(*dispatch_pascal_foundry_request(state, "POST", self.path, payload, request_origin=request_origin))

        def log_message(self, format: str, *args: Any) -> None:
            return
    return Handler


def serve(*, host: str, port: int, repo_root: str | Path, demo_project: str, auto_start: bool, **kwargs: Any) -> None:
    normalized_host = "localhost" if host == "::1" else host
    origin = _loopback_origin(f"http://{normalized_host}:{port}")
    state = PascalFoundryShowcaseState(repo_root, demo_project=demo_project, auto_start=auto_start, presentation_origin=origin, **kwargs)
    server = HTTPServer((host, port), make_handler(state))
    try:
        print(f"Aura Construction Pascal Spatial Foundry: {origin}")
        server.serve_forever()
    finally:
        server.server_close(); state.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST); parser.add_argument("--port", type=int, default=DEFAULT_PORT); parser.add_argument("--repo-root", default="."); parser.add_argument("--demo-project", default="winnipeg_pathways"); parser.add_argument("--no-auto-start", action="store_true")
    args = parser.parse_args()
    serve(host=args.host, port=args.port, repo_root=args.repo_root, demo_project=args.demo_project, auto_start=not args.no_auto_start)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["PASCAL_FOUNDRY_SERVER_VERSION", "PascalFoundryShowcaseState", "dispatch_pascal_foundry_request", "make_handler", "serve"]
