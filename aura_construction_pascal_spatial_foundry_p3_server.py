"""Composed P3 Construction decision lane over the P2 Pascal Spatial Foundry.

The P2 server and Pascal bridge remain the presentation owners. This server adds
only a deterministic, projection-only Construction decision lane, the retained
Aura as-built renderer, and digest-bound decision-support exports. It grants no
domain, renderer, patch, publication, or merge authority.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from aura_construction_demo_director import _safe_construction_demo_static_file
from aura_construction_foundry_decision import (
    ConstructionFoundryDecisionCompiler,
    public_projection,
)
from aura_construction_pascal_spatial_foundry_server import (
    IPv6HTTPServer,
    PascalFoundryShowcaseState,
    _content_security_policy as p2_content_security_policy,
    _error,
    _json,
    _loopback_origin,
    _static_response as p2_static_response,
    dispatch_pascal_foundry_request,
)
from aura_pascal_spatial_presentation import PascalPresentationError
from aura_showcase_live_repair_server import DEFAULT_HOST, DEFAULT_PORT, MAX_BODY_BYTES

P3_FOUNDRY_SERVER_VERSION = "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_P3_SERVER_V1"
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
_P3_STATIC_PATHS = {
    "construction-decision-foundry.css": STATIC_DIR / "construction-decision-foundry.css",
    "construction-decision-foundry.js": STATIC_DIR / "construction-decision-foundry.js",
    "construction-decision-as-built-sync.js": (
        STATIC_DIR / "construction-decision-as-built-sync.js"
    ),
}
_P3_MARKUP = b"""
<section id="construction-decision-foundry" class="foundry-grid construction-decision-grid" aria-label="Construction decision lane">
  <article class="foundry-card construction-decision-controls">
    <p class="eyebrow">P3 - Construction decision lane</p>
    <h2>Design / Floor Plan / As-built / Compare</h2>
    <p id="construction-decision-status">Decision lane not loaded.</p>
    <div class="construction-view-controls" role="group" aria-label="Construction view controls">
      <button type="button" data-construction-view="DESIGN">Design</button>
      <button type="button" data-construction-view="FLOOR_PLAN">Floor Plan</button>
      <button type="button" data-construction-view="AS_BUILT">As-built</button>
      <button type="button" data-construction-view="COMPARE">Compare</button>
    </div>
    <label>Timeline day <input id="construction-timeline" type="range" min="0" max="30" step="1" value="12"></label>
    <div id="construction-overlay-controls" class="construction-overlay-controls"></div>
  </article>
  <article class="foundry-card construction-decision-inspector">
    <h2>Evidence and obligations</h2>
    <div id="construction-selection-summary"></div>
    <div id="construction-evidence-pins"></div>
  </article>
  <article class="foundry-card construction-comparison-card">
    <div class="construction-stage-heading">
      <div><p class="eyebrow">Exact separated renderers</p><h2>Pascal design and Aura as-built</h2></div>
      <p id="construction-render-sync" class="construction-muted">Renderer synchronization not started.</p>
    </div>
    <div id="construction-geometry-stage" class="construction-geometry-stage">
      <section id="construction-design-pane" class="construction-render-pane">
        <h3>Pascal design working copy</h3>
        <div id="construction-pascal-mount"></div>
      </section>
      <section id="construction-as-built-pane" class="construction-render-pane">
        <h3>Aura-derived as-built projection</h3>
        <iframe id="construction-as-built-frame" title="Aura derived Construction as-built presentation" sandbox="allow-scripts allow-same-origin" referrerpolicy="no-referrer" src="/construction-as-built"></iframe>
      </section>
    </div>
  </article>
  <article class="foundry-card construction-candidate-card">
    <h2>Three bounded alternatives</h2>
    <div id="construction-candidates"></div>
  </article>
  <article class="foundry-card construction-decision-packet-card">
    <h2>Human decision packet</h2>
    <div id="construction-decision-packet"></div>
    <div class="construction-export-controls">
      <a href="/api/construction/decision-lane/export.json" download="aura-construction-decision.json">Export JSON</a>
      <a href="/api/construction/decision-lane/export.pdf" download="aura-construction-decision.pdf">Export PDF</a>
    </div>
  </article>
</section>
"""
_P3_STYLE = b'  <link rel="stylesheet" href="construction-decision-foundry.css">\n'
_P3_SCRIPT = b'  <script src="construction-decision-foundry.js"></script>\n'
_AS_BUILT_HTML = b"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>Aura P3 As-built</title>
  <link rel="stylesheet" href="/aura_spatial_web/construction_demo.css">
</head>
<body>
  <main class="arena-shell">
    <section class="viewport-wrap" aria-label="Aura derived as-built presentation">
      <canvas id="construction-canvas" width="1280" height="720"></canvas>
      <svg id="construction-mesh-overlay" aria-hidden="true"></svg>
      <div class="viewport-hud">
        <p id="intent-line">Initializing exact as-built projection.</p>
        <p id="scene-state">Loading</p>
      </div>
    </section>
  </main>
  <script type="module" src="/construction-decision-as-built-sync.js"></script>
</body>
</html>
"""
_AS_BUILT_REQUIRED_ASSETS = (
    "/aura_spatial_web/construction_demo.css",
    "/aura_spatial_web/construction_scene_renderer.js",
    "/aura_spatial_web/construction_wireframe_pass.js",
    "/aura_spatial_web/construction_mesh_pass.js",
    "/aura_spatial_web/construction_overlay_pass.js",
    "/aura_spatial_web/gaussian_renderer.js",
    "/aura_spatial_web/renderer_adapter.js",
    "/aura_spatial_web/webgl2_renderer.js",
    "/aura_spatial_web/webgl2_gaussian_pass.js",
)


class P3FoundryShowcaseState(PascalFoundryShowcaseState):
    """P2 state plus one disposable P3 compiler and retained renderer assets."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        asset_pack_path: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(repo_root, **kwargs)
        self.p3_load_error = ""
        self.p3_compiler: ConstructionFoundryDecisionCompiler | None = None
        self.p3_static_assets: dict[str, bytes] = {}
        self.p3_renderer_assets: dict[str, bytes] = {}
        self.p3_as_built_html = b""
        if not self.pascal_available:
            self.p3_load_error = (
                self.pascal_load_error or "P2 Pascal presentation is unavailable"
            )
            return
        try:
            if self.pascal_manifest is None or self.pascal_coordinate_receipt is None:
                raise PascalPresentationError(
                    "P2 Pascal contracts disappeared after validation"
                )
            path = (
                Path(asset_pack_path).expanduser().resolve()
                if asset_pack_path
                else None
            )
            compiler = ConstructionFoundryDecisionCompiler(
                manifest=self.pascal_manifest,
                coordinate_receipt=self.pascal_coordinate_receipt,
                asset_pack_path=path,
            )
            # Compile before exposing P3 routes or markup. Broken P3 work fails back
            # to the retained P2 surface without weakening P2 availability.
            compiler.compile()
            retained: dict[str, bytes] = {}
            for route, source in _P3_STATIC_PATHS.items():
                if not source.is_file() or source.is_symlink():
                    raise PascalPresentationError(
                        f"P3 static asset is unavailable: {route}"
                    )
                retained[route] = source.read_bytes()
            renderer_retained: dict[str, bytes] = {}
            for required_route in _AS_BUILT_REQUIRED_ASSETS:
                resolved = _safe_construction_demo_static_file(
                    self.repo_root,
                    required_route,
                )
                if resolved is None:
                    raise PascalPresentationError(
                        f"retained Aura Construction renderer asset is unavailable: {required_route}"
                    )
                _route, source_path = resolved
                if not source_path.is_file() or source_path.is_symlink():
                    raise PascalPresentationError(
                        f"retained Aura Construction renderer asset is invalid: {required_route}"
                    )
                renderer_retained[required_route] = source_path.read_bytes()
            as_built_html = _AS_BUILT_HTML
            self.p3_compiler = compiler
            self.p3_static_assets = retained
            self.p3_renderer_assets = renderer_retained
            self.p3_as_built_html = as_built_html
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
            self.p3_load_error = str(exc)
            self.p3_compiler = None
            self.p3_static_assets = {}
            self.p3_renderer_assets = {}
            self.p3_as_built_html = b""

    @property
    def p3_available(self) -> bool:
        return (
            self.pascal_available
            and self.p3_compiler is not None
            and set(self.p3_static_assets) == set(_P3_STATIC_PATHS)
            and set(self.p3_renderer_assets) == set(_AS_BUILT_REQUIRED_ASSETS)
            and bool(self.p3_as_built_html)
        )

    def require_p3(self) -> ConstructionFoundryDecisionCompiler:
        if not self.p3_available or self.p3_compiler is None:
            raise PascalPresentationError(
                "P3 Construction decision lane is unavailable; "
                "the P2 Pascal Foundry remains active"
            )
        return self.p3_compiler

    def close(self) -> None:
        self.p3_static_assets.clear()
        self.p3_renderer_assets.clear()
        self.p3_as_built_html = b""
        self.p3_compiler = None
        super().close()


def _validate_request_context(
    state: P3FoundryShowcaseState,
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
        if _loopback_origin(request_origin) != state.presentation_origin:
            raise PascalPresentationError(
                "request Origin differs from the exact loopback presentation origin"
            )
    elif method != "GET":
        raise PascalPresentationError(
            "mutable P3 requests require an exact Origin header"
        )


_IDENTITY_KEYS = (
    "state_digest",
    "runtime_packet_digest",
    "pascal_artifact_digest",
    "coordinate_receipt_digest",
    "as_built_scene_digest",
)
_SELECTION_KEYS = (
    "active_view",
    "selected_storey",
    "selected_node",
    "selected_issue_id",
    "selected_candidate_id",
    "selected_candidate_digest",
)
_ALLOWED_QUERY_KEYS = frozenset(_IDENTITY_KEYS + _SELECTION_KEYS + ("timeline_day",))


def _assert_exact_identities_from_projection(
    projection: Mapping[str, Any],
    body: Mapping[str, Any],
    *,
    require_all: bool = False,
) -> None:
    """Validate identities from an already-compiled projection.

    This avoids the double fixture/runtime/scene compilation that occurred
    when _assert_exact_identities called exact_identities() and then
    compile() rebuilt the same objects.
    """
    expected = {
        "state_digest": projection["domain"]["state_digest"],
        "runtime_packet_digest": projection["domain"]["runtime_packet_digest"],
        "pascal_artifact_digest": projection["artifacts"]["pascal_artifact_digest"],
        "coordinate_receipt_digest": projection["artifacts"]["coordinate_receipt_digest"],
        "as_built_scene_digest": projection["artifacts"]["as_built_scene_digest"],
    }
    for name, actual in expected.items():
        supplied = body.get(name)
        if require_all and supplied is None:
            raise PascalPresentationError(
                f"{name} is required for stateful P3 requests but was omitted"
            )
        if supplied is not None and supplied != actual:
            raise PascalPresentationError(
                f"{name} is stale or belongs to another P3 decision lane"
            )


def _compile_from_request(
    state: P3FoundryShowcaseState,
    body: Mapping[str, Any],
    *,
    require_identities: bool = False,
) -> dict[str, Any]:
    allowed = _ALLOWED_QUERY_KEYS
    unknown = sorted(set(body) - allowed)
    if unknown:
        raise PascalPresentationError(
            f"P3 projection request contains unknown fields: {unknown}"
        )
    # Compile once, then validate identities from the compiled projection
    # instead of calling exact_identities() which rebuilds the same objects.
    projection = state.require_p3().compile(
        active_view=body.get("active_view", "DESIGN"),
        selected_storey=body.get("selected_storey"),
        selected_node=body.get("selected_node"),
        selected_issue_id=body.get("selected_issue_id"),
        selected_candidate_id=body.get("selected_candidate_id"),
        selected_candidate_digest=body.get("selected_candidate_digest"),
        timeline_day=body.get("timeline_day", 12.0),
    )
    _assert_exact_identities_from_projection(
        projection, body, require_all=require_identities
    )
    return projection


def _query_projection_body(raw_path: str) -> dict[str, Any]:
    query = parse_qs(urlparse(raw_path).query, keep_blank_values=True)
    body: dict[str, Any] = {}
    for key in _ALLOWED_QUERY_KEYS:
        if key in query:
            values = query[key]
            if len(values) != 1:
                raise PascalPresentationError(
                    f"P3 projection query field must occur once: {key}"
                )
            value = values[0]
            if not value or not value.strip():
                raise PascalPresentationError(
                    f"P3 projection query field must not be blank: {key}"
                )
            if key == "timeline_day":
                body[key] = float(value)
            else:
                body[key] = value
    unknown = sorted(set(query) - _ALLOWED_QUERY_KEYS)
    if unknown:
        raise PascalPresentationError(
            f"P3 projection query contains unknown fields: {unknown}"
        )
    return body


def dispatch_p3_foundry_request(
    state: P3FoundryShowcaseState,
    method: str,
    raw_path: str,
    payload: Mapping[str, Any] | None = None,
    *,
    request_origin: str | None = None,
    request_host: str | None = None,
) -> tuple[int, str, bytes]:
    route = urlparse(raw_path).path.rstrip("/") or "/"
    if route != "/api/construction-demo" and not route.startswith(
        "/api/construction/decision-lane"
    ):
        return dispatch_pascal_foundry_request(
            state,
            method,
            raw_path,
            payload,
            request_origin=request_origin,
            request_host=request_host,
        )
    body = dict(payload or {})
    try:
        _validate_request_context(
            state,
            method,
            request_origin=request_origin,
            request_host=request_host,
        )
        if method == "GET" and route == "/api/construction-demo":
            projection = state.require_p3().compile()
            return (
                200,
                "application/json; charset=utf-8",
                projection["_as_built_packet_json"],
            )
        if method == "GET" and route == "/api/construction/decision-lane/status":
            return _json(
                200 if state.p3_available else 503,
                {
                    "ok": state.p3_available,
                    "available": state.p3_available,
                    "reason": state.p3_load_error,
                    "p3_server_version": P3_FOUNDRY_SERVER_VERSION,
                    "p2_fallback_available": state.pascal_available,
                    "aura_as_built_renderer_available": bool(
                        state.p3_as_built_html
                    ),
                    "human_review_required": True,
                    "physical_work_authorized": False,
                    "automatic_execution": False,
                },
            )
        if method == "GET" and route == "/api/construction/decision-lane":
            projection = _compile_from_request(
                state,
                _query_projection_body(raw_path),
            )
            return _json(
                200,
                {"ok": True, "projection": public_projection(projection)},
            )
        if method == "POST" and route == "/api/construction/decision-lane/project":
            projection = _compile_from_request(state, body, require_identities=True)
            return _json(
                200,
                {"ok": True, "projection": public_projection(projection)},
            )
        if method == "GET" and route in {
            "/api/construction/decision-lane/export.json",
            "/api/construction/decision-lane/export.pdf",
        }:
            projection = _compile_from_request(
                state,
                _query_projection_body(raw_path),
                require_identities=True,
            )
            if route.endswith(".json"):
                return (
                    200,
                    "application/json; charset=utf-8",
                    projection["_export_json"],
                )
            return 200, "application/pdf", projection["_export_pdf"]
        return _error("unknown P3 Construction decision-lane route", 404)
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
        return _error(str(exc), 409)


def _static_response(
    route: str,
    state: P3FoundryShowcaseState | None = None,
) -> tuple[int, str, bytes]:
    normalized = route.lstrip("/")
    if normalized in _P3_STATIC_PATHS:
        if state is None or not state.p3_available:
            return _error("P3 static asset is unavailable", 404)
        body = state.p3_static_assets.get(normalized)
        if body is None:
            return _error("P3 static asset is unavailable", 404)
        suffix = _P3_STATIC_PATHS[normalized].suffix
        content_type = (
            "application/javascript; charset=utf-8"
            if suffix == ".js"
            else "text/css; charset=utf-8"
        )
        return 200, content_type, body
    if route in {"/construction-as-built", "/construction-as-built/"}:
        if state is None or not state.p3_available:
            return _error("Aura as-built renderer is unavailable", 404)
        return 200, "text/html; charset=utf-8", state.p3_as_built_html
    if route.startswith("/aura_spatial_web/") or route.startswith("/demo_assets/"):
        if state is None or not state.p3_available:
            return _error("Aura as-built renderer asset is unavailable", 404)
        retained_bytes = state.p3_renderer_assets.get(route)
        if retained_bytes is not None:
            suffix = Path(route).suffix
            if suffix == ".js":
                media_type = "application/javascript; charset=utf-8"
            elif suffix == ".css":
                media_type = "text/css; charset=utf-8"
            else:
                media_type = mimetypes.guess_type(route)[0] or "application/octet-stream"
                if media_type.startswith("text/") or suffix in {".json", ".svg"}:
                    media_type += "; charset=utf-8"
            return 200, media_type, retained_bytes
        # Reject unretained renderer-prefixed routes instead of falling back
        # to the live filesystem.  Every reachable as-built asset must be
        # retained at startup; serving mutable on-disk bytes after startup
        # would break the startup-bound identity contract.
        return _error("Aura as-built renderer asset is not retained", 404)
    status, content_type, body = p2_static_response(route, state)
    if (
        status == 200
        and route in {"/", "/index.html"}
        and state is not None
        and state.p3_available
    ):
        # Recompute the lowercase body after each insertion so subsequent
        # anchors are found at their post-mutation offsets, not the stale
        # pre-mutation positions.
        body_lower = body.lower()
        if b"construction-decision-foundry.css" not in body_lower:
            head_idx = body_lower.find(b"</head>")
            if head_idx == -1:
                return _error("P2 markup lacks a </head> anchor for P3 injection", 500)
            body = body[:head_idx] + _P3_STYLE + body[head_idx:]
            body_lower = body.lower()
        if b'id="construction-decision-foundry"' not in body_lower:
            section_idx = body_lower.find(b'<section class="foundry-authority"')
            if section_idx == -1:
                return _error(
                    "P2 markup lacks a foundry-authority anchor for P3 injection", 500
                )
            body = body[:section_idx] + _P3_MARKUP + b"\n  " + body[section_idx:]
            body_lower = body.lower()
        if b"construction-decision-foundry.js" not in body_lower:
            body_idx = body_lower.find(b"</body>")
            if body_idx == -1:
                return _error("P2 markup lacks a </body> anchor for P3 injection", 500)
            body = body[:body_idx] + _P3_SCRIPT + body[body_idx:]
    return status, content_type, body


def _content_security_policy(route: str) -> str | None:
    retained = p2_content_security_policy(route)
    if retained is not None:
        return retained
    if (
        route in {"/construction-as-built", "/construction-as-built/"}
        or route.startswith("/aura_spatial_web/")
        or route.startswith("/demo_assets/")
        or route == "/construction-decision-as-built-sync.js"
    ):
        return (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-src 'none'; "
            "object-src 'none'; base-uri 'none'; form-action 'none'; "
            "frame-ancestors 'self'"
        )
    return None


def make_handler(state: P3FoundryShowcaseState):
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
            for name, value in (
                ("Content-Type", content_type),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
                ("Referrer-Policy", "no-referrer"),
            ):
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
                raise PascalPresentationError("request body must be a JSON object")
            return value

        def _context(self) -> tuple[str | None, str | None]:
            return self.headers.get("Origin"), self.headers.get("Host")

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route.startswith("/api/"):
                origin, host = self._context()
                response = dispatch_p3_foundry_request(
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
            origin, host = self._context()
            response = dispatch_p3_foundry_request(
                state,
                "POST",
                self.path,
                payload,
                request_origin=origin,
                request_host=host,
            )
            self._send(*response, route=route)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    return Handler


def serve(
    *,
    host: str,
    port: int,
    repo_root: str | Path,
    demo_project: str,
    auto_start: bool,
    asset_pack_path: str | Path | None = None,
    **kwargs: Any,
) -> None:
    origin_host = "[::1]" if host == "::1" else host
    origin = _loopback_origin(f"http://{origin_host}:{port}")
    state = P3FoundryShowcaseState(
        repo_root,
        demo_project=demo_project,
        auto_start=auto_start,
        presentation_origin=origin,
        asset_pack_path=asset_pack_path,
        **kwargs,
    )
    server_type = IPv6HTTPServer if host == "::1" else HTTPServer
    server = server_type((host, port), make_handler(state))
    try:
        print(f"Aura Construction Pascal Spatial Foundry P3: {origin}")
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
    parser.add_argument("--asset-pack")
    parser.add_argument("--no-auto-start", action="store_true")
    args = parser.parse_args()
    serve(
        host=args.host,
        port=args.port,
        repo_root=args.repo_root,
        demo_project=args.demo_project,
        auto_start=not args.no_auto_start,
        asset_pack_path=args.asset_pack,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "P3_FOUNDRY_SERVER_VERSION",
    "P3FoundryShowcaseState",
    "dispatch_p3_foundry_request",
    "make_handler",
    "serve",
]
