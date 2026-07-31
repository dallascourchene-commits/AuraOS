"""Standalone Construction + Pascal Spatial Foundry presentation server.

This entry point composes the existing P2 Pascal workbench, P3 Construction
decision lane, and P4 deterministic Director into one Construction-only page.
It deliberately does not inherit the Civic/Observatory showcase document.

The canonical owners remain unchanged:
- P4 owns Director sequencing and bounded repair/reproof coordination.
- P3 owns the Construction decision projection and synchronized views.
- P2 owns the pinned disposable Pascal 2D/3D workbench.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aura_construction_pascal_spatial_foundry_server import _PASCAL_MARKUP
from aura_construction_pascal_spatial_foundry_p3_server import (
    IPv6HTTPServer,
    _P3_MARKUP,
    _error,
    _loopback_origin,
)
from aura_construction_pascal_spatial_foundry_p4_server import (
    P4FoundryShowcaseState,
    _P4_MARKUP,
    _content_security_policy as p4_content_security_policy,
    _static_response as p4_static_response,
    dispatch_p4_foundry_request,
)
from aura_pascal_spatial_presentation import PascalPresentationError
from aura_showcase_live_repair_server import DEFAULT_HOST, MAX_BODY_BYTES

STANDALONE_FOUNDRY_SERVER_VERSION = (
    "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_STANDALONE_SERVER_V1"
)
STANDALONE_DEFAULT_PORT = 8768
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
_STANDALONE_CSS_ROUTE = "/construction-foundry-standalone.css"
_STANDALONE_CSS_PATH = STATIC_DIR / "construction-foundry-standalone.css"
_STANDALONE_ROUTES = {
    "/",
    "/index.html",
    "/construction",
    "/construction/",
    "/construction/index.html",
}
_LEGACY_ROUTE = "/legacy-showcase"


def _build_standalone_html() -> bytes:
    """Compose one Construction-only document from the retained owner markup."""

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="dark">
  <title>Aura Construction + Pascal Spatial Foundry</title>
  <link rel="stylesheet" href="/styles.css">
  <link rel="stylesheet" href="/pascal-construction-foundry.css">
  <link rel="stylesheet" href="/construction-decision-foundry.css">
  <link rel="stylesheet" href="/construction-foundry-director.css">
  <link rel="stylesheet" href="/construction-foundry-standalone.css">
</head>
<body data-aura-surface="CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY">
  <header class="construction-topbar">
    <div class="construction-brand">
      <span class="construction-brand-mark" aria-hidden="true"></span>
      <div>
        <strong>AURA CONSTRUCTION</strong>
        <small>Pascal Spatial Foundry - local deterministic demonstration</small>
      </div>
    </div>
    <div class="construction-authority">
      <span>Human review required</span>
      <span>No physical-work authority</span>
    </div>
    <a class="construction-legacy-link" href="/legacy-showcase">Legacy Aura showcase</a>
  </header>

  <main class="construction-shell">
    <section class="construction-hero" aria-labelledby="construction-demo-title">
      <div>
        <p class="eyebrow">Standalone Construction + Pascal Spatial Foundry</p>
        <h1 id="construction-demo-title">Design, floor plan, as-built, comparison, evidence, and bounded repair.</h1>
        <p class="construction-lede">
          Aura retains Construction truth, evidence, authority, verification, rollback,
          and human disposition. Pascal supplies the pinned disposable 2D/3D building
          workbench. This page contains no Civic Arena, Winnipeg map, Human Agent Arena,
          Observatory, or Crucible surface.
        </p>
      </div>
      <dl class="construction-boundary">
        <div><dt>Runtime</dt><dd>Loopback only</dd></div>
        <div><dt>Data</dt><dd>Deterministic fixture</dd></div>
        <div><dt>Decision</dt><dd>Human review</dd></div>
        <div><dt>Authority</dt><dd>Projection only</dd></div>
      </dl>
    </section>

    <section class="construction-director-band" aria-label="Guided Construction demonstration">
{_P4_MARKUP.decode("utf-8")}
    </section>

    <section class="construction-workspace" aria-label="Construction and Pascal workspace">
{_P3_MARKUP.decode("utf-8")}
    </section>

    <div id="pascal-component-staging" hidden>
{_PASCAL_MARKUP.decode("utf-8")}
    </div>

    <footer class="construction-footer">
      <strong>Aura owns truth and governance.</strong>
      <span>Pascal is a disposable presentation organ.</span>
      <span>Runtime evidence does not authorize deployment, merge, payment, access, or physical work.</span>
    </footer>
  </main>

  <noscript>This demonstration requires JavaScript for the local presentation bridge.</noscript>
  <script src="/pascal-construction-foundry.js"></script>
  <script src="/construction-decision-foundry.js"></script>
  <script src="/construction-foundry-director.js"></script>
</body>
</html>
"""
    return document.encode("utf-8")


class StandaloneConstructionFoundryState(P4FoundryShowcaseState):
    """P4 state plus retained bytes for the dedicated Construction shell."""

    def __init__(self, repo_root: str | Path, **kwargs: Any) -> None:
        super().__init__(repo_root, **kwargs)
        self.standalone_load_error = ""
        self.standalone_html = b""
        self.standalone_css = b""
        try:
            if not _STANDALONE_CSS_PATH.is_file() or _STANDALONE_CSS_PATH.is_symlink():
                raise PascalPresentationError(
                    "standalone Construction stylesheet is unavailable"
                )
            self.standalone_css = _STANDALONE_CSS_PATH.read_bytes()
            self.standalone_html = _build_standalone_html()
        except (OSError, PascalPresentationError) as exc:
            self.standalone_load_error = str(exc)
            self.standalone_html = b""
            self.standalone_css = b""

    @property
    def standalone_available(self) -> bool:
        return bool(self.standalone_html and self.standalone_css)

    def close(self) -> None:
        self.standalone_html = b""
        self.standalone_css = b""
        super().close()


def _static_response(
    route: str,
    state: StandaloneConstructionFoundryState | None = None,
) -> tuple[int, str, bytes]:
    """Serve the Construction shell first; delegate all owner assets afterward."""

    if route in _STANDALONE_ROUTES:
        if state is None or not state.standalone_available:
            reason = (
                state.standalone_load_error
                if state is not None
                else "standalone Construction state is unavailable"
            )
            return _error(reason or "standalone Construction shell is unavailable", 503)
        return 200, "text/html; charset=utf-8", state.standalone_html

    if route == _STANDALONE_CSS_ROUTE:
        if state is None or not state.standalone_available:
            return _error("standalone Construction stylesheet is unavailable", 404)
        return 200, "text/css; charset=utf-8", state.standalone_css

    if route in {_LEGACY_ROUTE, f"{_LEGACY_ROUTE}/"}:
        return p4_static_response("/", state)

    return p4_static_response(route, state)


def _content_security_policy(route: str) -> str | None:
    if route in _STANDALONE_ROUTES:
        return (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-src 'self'; "
            "object-src 'none'; base-uri 'none'; form-action 'self'; "
            "frame-ancestors 'self'"
        )
    if route == _STANDALONE_CSS_ROUTE:
        return "default-src 'none'; style-src 'self'; base-uri 'none'"
    if route in {_LEGACY_ROUTE, f"{_LEGACY_ROUTE}/"}:
        return p4_content_security_policy("/")
    return p4_content_security_policy(route)


def make_handler(state: StandaloneConstructionFoundryState):
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
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise PascalPresentationError(
                    "request body must be a JSON object"
                )
            return value

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route.startswith("/api/"):
                response = dispatch_p4_foundry_request(
                    state,
                    "GET",
                    self.path,
                    request_origin=self.headers.get("Origin"),
                    request_host=self.headers.get("Host"),
                )
            else:
                response = _static_response(route, state)
            self._send(*response, route=route)

        def do_POST(self) -> None:
            route = urlparse(self.path).path
            try:
                payload = self._payload()
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                PascalPresentationError,
            ) as exc:
                self._send(*_error(str(exc), 400), route=route)
                return
            response = dispatch_p4_foundry_request(
                state,
                "POST",
                self.path,
                payload,
                request_origin=self.headers.get("Origin"),
                request_host=self.headers.get("Host"),
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
) -> None:
    origin_host = "[::1]" if host == "::1" else host
    origin = _loopback_origin(f"http://{origin_host}:{port}")
    state = StandaloneConstructionFoundryState(
        repo_root,
        demo_project=demo_project,
        auto_start=auto_start,
        presentation_origin=origin,
        asset_pack_path=asset_pack_path,
    )
    server_type: type[HTTPServer] = IPv6HTTPServer if host == "::1" else HTTPServer
    server = server_type((host, port), make_handler(state))
    try:
        print(f"Aura standalone Construction + Pascal Spatial Foundry: {origin}")
        print(f"Legacy Aura showcase: {origin}{_LEGACY_ROUTE}")
        server.serve_forever()
    finally:
        server.server_close()
        state.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=STANDALONE_DEFAULT_PORT)
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
    "STANDALONE_DEFAULT_PORT",
    "STANDALONE_FOUNDRY_SERVER_VERSION",
    "StandaloneConstructionFoundryState",
    "dispatch_p4_foundry_request",
    "make_handler",
    "serve",
]
