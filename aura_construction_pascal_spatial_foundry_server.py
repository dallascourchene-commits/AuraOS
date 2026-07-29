"""Composed Aura Construction Spatial Foundry server with the PR 2 Pascal organ.

The PR 1 server remains the fallback owner. Pascal assets are served only from bytes
retained after exact fixture validation, and every mutable bridge request is bound to
the actual loopback Host and Origin headers.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import socket
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
    sha256_digest,
)

PASCAL_FOUNDRY_SERVER_VERSION = (
    "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_SERVER_V1"
)
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
_LOOPBACK_HOST = re.compile(r"^(?:localhost|127\.0\.0\.1|::1)$")

# User input is never joined into a filesystem path. Routes select one fixed path.
_PASCAL_STATIC_PATHS = {
    "pascal-construction-foundry.css": STATIC_DIR / "pascal-construction-foundry.css",
    "pascal-workbench/index.html": STATIC_DIR / "pascal-workbench/index.html",
    "pascal-workbench/pascal-workbench.css": (
        STATIC_DIR / "pascal-workbench/pascal-workbench.css"
    ),
    "pascal-workbench/pascal-workbench.js": (
        STATIC_DIR / "pascal-workbench/pascal-workbench.js"
    ),
    "pascal-workbench/fixture.json": STATIC_DIR / "pascal-workbench/fixture.json",
    "pascal-workbench/artifact-manifest.json": (
        STATIC_DIR / "pascal-workbench/artifact-manifest.json"
    ),
    "pascal-workbench/coordinate-receipt.json": (
        STATIC_DIR / "pascal-workbench/coordinate-receipt.json"
    ),
    "pascal-construction-foundry.js": STATIC_DIR / "pascal-construction-foundry.js",
}


class PascalFoundryShowcaseState(ConstructionFoundryShowcaseState):
    """PR 1 state plus one bounded and independently disposable Pascal registry."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        demo_project: str,
        auto_start: bool,
        presentation_origin: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            repo_root,
            demo_project=demo_project,
            auto_start=auto_start,
            **kwargs,
        )
        self.presentation_origin = _loopback_origin(presentation_origin)
        self.presentation_netloc = urlparse(self.presentation_origin).netloc
        self.pascal_load_error = ""
        self.pascal_source_lock = None
        self.pascal_manifest = None
        self.pascal_coordinate_receipt = None
        self.pascal_scene: dict[str, Any] | None = None
        self.pascal_registry: PascalPresentationRegistry | None = None
        self.pascal_static_assets: dict[str, bytes] = {}
        try:
            lock, manifest, coordinate, scene = load_pascal_compatibility_fixture(
                str(self.repo_root)
            )
            retained_assets = self._retain_validated_static_assets(lock, manifest, coordinate, scene)
            self.pascal_source_lock = lock
            self.pascal_manifest = manifest
            self.pascal_coordinate_receipt = coordinate
            self.pascal_scene = scene
            self.pascal_registry = PascalPresentationRegistry(
                manifest=manifest,
                coordinate_receipt=coordinate,
            )
            self.pascal_static_assets = retained_assets
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            PascalPresentationError,
            TypeError,
            ValueError,
            KeyError,
            OverflowError,
        ) as exc:
            self.pascal_load_error = str(exc)
            self.pascal_static_assets = {}

    def _retain_validated_static_assets(
        self,
        lock: Any,
        manifest: Any,
        coordinate: Any,
        scene: Mapping[str, Any],
    ) -> dict[str, bytes]:
        retained: dict[str, bytes] = {}
        locked = {path: digest for path, digest in lock.local_assets}
        for route, path in _PASCAL_STATIC_PATHS.items():
            if not path.is_file() or path.is_symlink():
                raise PascalPresentationError(
                    f"validated Pascal static asset is unavailable: {route}"
                )
            body = path.read_bytes()
            relative = f"aura_showcase/{route}"
            expected = locked.get(relative)
            if expected is not None and sha256_digest(body) != expected:
                raise PascalPresentationError(
                    f"validated Pascal static asset changed after verification: {route}"
                )
            retained[route] = body
        if json.loads(retained["pascal-workbench/fixture.json"]) != dict(scene):
            raise PascalPresentationError("retained fixture bytes differ from the verified scene")
        if json.loads(retained["pascal-workbench/artifact-manifest.json"]) != manifest.to_dict():
            raise PascalPresentationError("retained manifest bytes differ from the verified contract")
        if json.loads(retained["pascal-workbench/coordinate-receipt.json"]) != coordinate.to_dict():
            raise PascalPresentationError("retained coordinate bytes differ from the verified receipt")
        return retained

    @property
    def pascal_available(self) -> bool:
        return (
            self.pascal_registry is not None
            and self.pascal_source_lock is not None
            and self.pascal_manifest is not None
            and self.pascal_coordinate_receipt is not None
            and self.pascal_scene is not None
            and set(self.pascal_static_assets) == set(_PASCAL_STATIC_PATHS)
        )

    def require_pascal_registry(self) -> PascalPresentationRegistry:
        if not self.pascal_available or self.pascal_registry is None:
            raise PascalPresentationError(
                "Pascal presentation organ is unavailable; "
                "the PR 1 Construction Foundry remains active"
            )
        return self.pascal_registry

    def _require_pascal_contracts(self) -> tuple[Any, Any, dict[str, Any]]:
        if (
            not self.pascal_available
            or self.pascal_manifest is None
            or self.pascal_coordinate_receipt is None
            or self.pascal_scene is None
        ):
            raise PascalPresentationError(
                "Pascal contracts are unavailable; PR 1 remains active"
            )
        return (
            self.pascal_manifest,
            self.pascal_coordinate_receipt,
            self.pascal_scene,
        )

    def pascal_manifest_response(self) -> dict[str, Any]:
        if not self.pascal_available:
            return {
                "ok": False,
                "available": False,
                "reason": (
                    self.pascal_load_error
                    or "Pascal compatibility fixture is unavailable"
                ),
                "pr1_fallback_available": True,
                "construction_foundry_server_version": (
                    CONSTRUCTION_FOUNDRY_SERVER_VERSION
                ),
                "pascal_foundry_server_version": PASCAL_FOUNDRY_SERVER_VERSION,
            }
        if (
            self.pascal_source_lock is None
            or self.pascal_manifest is None
            or self.pascal_coordinate_receipt is None
        ):
            raise PascalPresentationError(
                "Pascal manifest contracts disappeared after validation"
            )
        return {
            "ok": True,
            "available": True,
            "source_lock": self.pascal_source_lock.to_dict(),
            "artifact_manifest": self.pascal_manifest.to_dict(),
            "coordinate_receipt": self.pascal_coordinate_receipt.to_dict(),
            "working_copy_only": True,
            "external_asset_fetch": False,
            "persistent_canonical_storage": False,
            "construction_truth": False,
            "survey_authority": False,
            "execution_authority": False,
            "human_review_required": True,
            "pr1_fallback_available": True,
            "construction_foundry_server_version": (
                CONSTRUCTION_FOUNDRY_SERVER_VERSION
            ),
            "pascal_foundry_server_version": PASCAL_FOUNDRY_SERVER_VERSION,
        }

    def start_pascal_session(self) -> dict[str, Any]:
        registry = self.require_pascal_registry()
        manifest, coordinate, scene = self._require_pascal_contracts()
        render_plan_digest = stable_digest(
            {
                "kind": "PASCAL_LOCAL_PRESENTATION",
                "artifact_digest": manifest.artifact_digest,
                "coordinate_receipt_digest": coordinate.receipt_digest,
                "views": ["2D", "3D"],
                "external_asset_fetch": False,
                "persistent_canonical_storage": False,
                "renderer_authority": False,
            },
            digest_size=32,
        )
        session = registry.create(
            spatial_scene_digest=coordinate.spatial_scene_digest,
            render_plan_digest=render_plan_digest,
            expected_origin=self.presentation_origin,
        )
        return {
            "ok": True,
            "session": session.status(),
            "scene": scene,
            "artifact_manifest": manifest.to_dict(),
            "workbench_path": "/pascal-workbench/index.html",
            "sandbox": "allow-scripts allow-same-origin",
            "same_origin_required": True,
            "external_asset_fetch": False,
            "persistent_canonical_storage": False,
            "construction_truth": False,
            "execution_authority": False,
        }

    def close(self) -> None:
        if self.pascal_registry is not None:
            self.pascal_registry.dissolve_all()
        self.pascal_static_assets.clear()
        super().close()


def _loopback_origin(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise PascalPresentationError(
            "presentation_origin must be an HTTP(S) loopback origin"
        )
    if not _LOOPBACK_HOST.fullmatch(parsed.hostname):
        raise PascalPresentationError(
            "presentation_origin must remain loopback-only"
        )
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise PascalPresentationError(
            "presentation_origin must not contain a path, query, or fragment"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise PascalPresentationError(
            "presentation_origin contains an invalid port"
        ) from exc
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    return f"{parsed.scheme}://{host}{f':{port}' if port is not None else ''}"


def _validate_request_context(
    state: PascalFoundryShowcaseState,
    method: str,
    *,
    request_origin: str | None,
    request_host: str | None,
) -> None:
    host = str(request_host or "").strip().casefold()
    if host != state.presentation_netloc.casefold():
        raise PascalPresentationError(
            "request Host differs from the exact loopback presentation origin"
        )
    if request_origin:
        origin = _loopback_origin(request_origin)
        if origin != state.presentation_origin:
            raise PascalPresentationError(
                "request Origin differs from the exact loopback presentation origin"
            )
    elif method != "GET":
        raise PascalPresentationError(
            "mutable Pascal requests require an exact Origin header"
        )


def _session_route(route: str) -> tuple[str, str] | None:
    parts = tuple(part for part in route.split("/") if part)
    if (
        len(parts) < 5
        or parts[:4] != ("api", "construction", "pascal", "session")
    ):
        return None
    return parts[4], "/".join(parts[5:])


def _body_must_not_supply_identity(body: Mapping[str, Any]) -> None:
    forbidden = {
        "expected_origin",
        "origin",
        "spatial_scene_digest",
        "render_plan_digest",
        "pascal_artifact_digest",
        "coordinate_receipt_digest",
        "state_binding_digest",
        "sequence",
        "nonce",
        "direction",
        "message_digest",
    }
    supplied = sorted(forbidden.intersection(body))
    if supplied:
        raise PascalPresentationError(
            f"request cannot supply server-owned Pascal session identity: {supplied}"
        )


def dispatch_pascal_foundry_request(
    state: PascalFoundryShowcaseState,
    method: str,
    raw_path: str,
    payload: Mapping[str, Any] | None = None,
    *,
    request_origin: str | None = None,
    request_host: str | None = None,
) -> tuple[int, str, bytes]:
    """Dispatch one request without substituting caller-controlled identity."""
    route = urlparse(raw_path).path.rstrip("/") or "/"
    body = dict(payload or {})
    is_pascal_route = route.startswith("/api/construction/pascal/")
    if not is_pascal_route:
        return dispatch_construction_foundry_request(
            state,
            method,
            raw_path,
            body,
        )
    try:
        _validate_request_context(
            state,
            method,
            request_origin=request_origin,
            request_host=request_host,
        )
        if method == "GET" and route == "/api/construction/pascal/manifest":
            response = state.pascal_manifest_response()
            return _json(200 if response["available"] else 503, response)

        if method == "POST" and route == "/api/construction/pascal/session/start":
            if body:
                _body_must_not_supply_identity(body)
                if set(body) != {"client_request_id"}:
                    raise PascalPresentationError(
                        "Pascal session start accepts only an optional client_request_id"
                    )
            return _json(200, state.start_pascal_session())

        parsed = _session_route(route)
        if parsed is not None:
            session_id, suffix = parsed
            session = state.require_pascal_registry().get(session_id)
            if method == "GET" and not suffix:
                return _json(200, {"ok": True, "session": session.status()})
            if method == "POST" and suffix == "command":
                if (
                    set(body) != {"action", "payload"}
                    or not isinstance(body.get("payload"), Mapping)
                ):
                    raise PascalPresentationError(
                        "command request requires exactly action and payload"
                    )
                message = session.issue_parent_message(
                    PascalBridgeAction(str(body["action"])),
                    body["payload"],
                )
                return _json(
                    200,
                    {
                        "ok": True,
                        "message": message.to_dict(),
                        "session": session.status(),
                    },
                )
            if method == "POST" and suffix == "event":
                if set(body) != {"message"} or not isinstance(
                    body.get("message"),
                    Mapping,
                ):
                    raise PascalPresentationError(
                        "event request requires exactly one message object"
                    )
                message = AuraPascalBridgeMessage.from_mapping(body["message"])
                if request_origin is None:
                    raise PascalPresentationError(
                        "event request requires an exact Origin header"
                    )
                result = session.accept(message, origin=_loopback_origin(request_origin))
                return _json(
                    200,
                    {
                        "ok": True,
                        "acceptance": result,
                        "session": session.status(),
                    },
                )
            if method == "POST" and suffix == "dissolution/finalize":
                if set(body) != {"iframe_removed"} or body.get("iframe_removed") is not True:
                    raise PascalPresentationError(
                        "dissolution finalization requires iframe_removed=true"
                    )
                receipt = session.mark_iframe_removed()
                return _json(
                    200,
                    {
                        "ok": True,
                        "dissolution_receipt": receipt,
                        "session": session.status(),
                    },
                )
        return _error("unknown Pascal Construction Foundry route", 404)
    except (
        PascalPresentationError,
        BilateralLiveRepairError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        KeyError,
        OverflowError,
    ) as exc:
        return _error(str(exc), 409)


_PASCAL_MARKUP = b"""
<section id="pascal-construction-foundry" class="foundry-grid" aria-label="Pascal Construction presentation organ">
  <article class="foundry-card pascal-controller">
    <p class="eyebrow">PR 2 - Pascal presentation organ</p>
    <h2>Local 2D / 3D workbench</h2>
    <p id="pascal-foundry-status">Pascal workbench not started.</p>
    <div class="pascal-controls" role="group" aria-label="Pascal presentation controls">
      <button type="button" data-pascal-action="launch">Launch</button>
      <button type="button" data-pascal-action="2d" disabled>2D</button>
      <button type="button" data-pascal-action="3d" disabled>3D</button>
      <button type="button" data-pascal-action="storey" disabled>Next storey</button>
      <button type="button" data-pascal-action="dimensions" disabled>Dimensions</button>
      <button type="button" data-pascal-action="reset" disabled>Reset</button>
      <button type="button" data-pascal-action="dissolve" disabled>Dissolve</button>
    </div>
    <pre id="pascal-foundry-receipt">No Pascal receipt retained.</pre>
  </article>
  <article class="foundry-card pascal-stage-card">
    <div id="pascal-workbench-host" class="pascal-workbench-host" aria-live="polite"></div>
  </article>
</section>
"""
_PASCAL_STYLE = b'  <link rel="stylesheet" href="pascal-construction-foundry.css">\n'
_PASCAL_SCRIPT = b'  <script src="pascal-construction-foundry.js"></script>\n'


def _static_response(
    route: str,
    state: PascalFoundryShowcaseState | None = None,
) -> tuple[int, str, bytes]:
    normalized = route.lstrip("/")
    if normalized == "pascal-workbench":
        normalized = "pascal-workbench/index.html"
    if normalized in _PASCAL_STATIC_PATHS:
        if state is None or not state.pascal_available:
            return _error("Pascal static asset is unavailable", 404)
        body = state.pascal_static_assets.get(normalized)
        if body is None:
            return _error("Pascal static asset is unavailable", 404)
        suffix = _PASCAL_STATIC_PATHS[normalized].suffix
        media_type = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
        }.get(suffix, "application/octet-stream")
        return 200, media_type, body

    status, content_type, body = construction_static_response(route)
    if (
        status == 200
        and route in {"/", "/index.html"}
        and state is not None
        and state.pascal_available
    ):
        if b"pascal-construction-foundry.css" not in body:
            body = body.replace(b"</head>", _PASCAL_STYLE + b"</head>", 1)
        if b'id="pascal-construction-foundry"' not in body:
            body = body.replace(
                b'<section class="foundry-authority"',
                _PASCAL_MARKUP + b'\n  <section class="foundry-authority"',
                1,
            )
        if b"pascal-construction-foundry.js" not in body:
            body = body.replace(b"</body>", _PASCAL_SCRIPT + b"</body>", 1)
    return status, content_type, body


def _content_security_policy(route: str) -> str | None:
    """Use strict isolation only for the disposable workbench, not the PR 1 map."""
    if route.startswith("/pascal-workbench"):
        return (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'none'; frame-src 'none'; "
            "object-src 'none'; base-uri 'none'; form-action 'none'; "
            "frame-ancestors 'self'"
        )
    return None


def make_handler(state: PascalFoundryShowcaseState):
    class Handler(BaseHTTPRequestHandler):
        def _send(
            self,
            status: int,
            content_type: str,
            body: bytes,
            *,
            route: str,
        ) -> None:
            self.send_response(status)
            headers = (
                ("Content-Type", content_type),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
                ("Referrer-Policy", "no-referrer"),
            )
            for name, value in headers:
                self.send_header(name, value)
            policy = _content_security_policy(route)
            if policy is not None:
                self.send_header("Content-Security-Policy", policy)
            self.end_headers()
            self.wfile.write(body)

        def _payload(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
            except (TypeError, ValueError) as exc:
                raise PascalPresentationError(
                    "Content-Length must be a valid integer"
                ) from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise PascalPresentationError(
                    f"request body must be between 0 and {MAX_BODY_BYTES} bytes"
                )
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PascalPresentationError(
                    "request body must be valid UTF-8 JSON"
                ) from exc
            if not isinstance(value, dict):
                raise PascalPresentationError(
                    "request body must be a JSON object"
                )
            return value

        def _request_context(self) -> tuple[str | None, str | None]:
            return self.headers.get("Origin"), self.headers.get("Host")

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route.startswith("/api/"):
                origin, host = self._request_context()
                response = dispatch_pascal_foundry_request(
                    state,
                    "GET",
                    self.path,
                    request_origin=origin,
                    request_host=host,
                )
            else:
                response = _static_response(route, state)
            self._send(*response, route=route)

        def do_POST(self) -> None:
            route = urlparse(self.path).path
            try:
                payload = self._payload()
            except PascalPresentationError as exc:
                self._send(*_error(str(exc), 400), route=route)
                return
            origin, host = self._request_context()
            response = dispatch_pascal_foundry_request(
                state,
                "POST",
                self.path,
                payload,
                request_origin=origin,
                request_host=host,
            )
            self._send(*response, route=route)

        def log_message(self, message_format: str, *args: Any) -> None:
            del message_format, args

    return Handler


class IPv6HTTPServer(HTTPServer):
    address_family = socket.AF_INET6


def serve(
    *,
    host: str,
    port: int,
    repo_root: str | Path,
    demo_project: str,
    auto_start: bool,
    **kwargs: Any,
) -> None:
    origin_host = "[::1]" if host == "::1" else host
    origin = _loopback_origin(f"http://{origin_host}:{port}")
    state = PascalFoundryShowcaseState(
        repo_root,
        demo_project=demo_project,
        auto_start=auto_start,
        presentation_origin=origin,
        **kwargs,
    )
    server_type = IPv6HTTPServer if host == "::1" else HTTPServer
    server = server_type((host, port), make_handler(state))
    try:
        print(f"Aura Construction Pascal Spatial Foundry: {origin}")
        server.serve_forever()
    finally:
        server.server_close()
        state.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--demo-project", default="winnipeg_pathways")
    parser.add_argument("--no-auto-start", action="store_true")
    args = parser.parse_args()
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


__all__ = [
    "IPv6HTTPServer",
    "PASCAL_FOUNDRY_SERVER_VERSION",
    "PascalFoundryShowcaseState",
    "dispatch_pascal_foundry_request",
    "make_handler",
    "serve",
]
