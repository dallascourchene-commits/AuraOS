"""Showcase adapter for B11-B15 bilateral live repair and Spatial Foundry.

The adapter reuses ``aura_showcase_server`` for every existing route and static
asset. It adds a bounded live-repair route family and injects a projection-only
Foundry panel into the existing Showcase HTML. It does not replace Showcase or
create a second domain/UI truth owner.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from aura_bilateral_live_repair_foundry import (
    BilateralIdentity,
    BilateralLiveRepairError,
    BilateralLiveRepairService,
    PreviewRollbackReceipt,
    RepairCandidateResult,
)
from aura_showcase_server import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    ShowcaseState,
    _static_response as base_static_response,
    dispatch_showcase_request as base_dispatch_showcase_request,
)
from scripts.aura_runtime_profile_v2_adapter import BilateralRuntimeProfileError

SHOWCASE_LIVE_REPAIR_VERSION = "AURA_SHOWCASE_LIVE_REPAIR_V1"
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
MAX_BODY_BYTES = 1_000_000


class LiveRepairShowcaseState(ShowcaseState):
    def __init__(
        self,
        repo_root: str | Path,
        *,
        demo_project: str,
        auto_start: bool,
        current_identity_resolver: Callable[[BilateralIdentity], BilateralIdentity] | None = None,
    ) -> None:
        super().__init__(repo_root, demo_project=demo_project, auto_start=auto_start)
        self._current_identity_resolver = current_identity_resolver
        self._live_repair: BilateralLiveRepairService | None = None
        self.live_repair_attempts: dict[tuple[str, str], RepairCandidateResult] = {}
        self.live_repair_previews: dict[str, PreviewRollbackReceipt] = {}

    @property
    def live_repair(self) -> BilateralLiveRepairService:
        if self._live_repair is None:
            self._live_repair = BilateralLiveRepairService(
                self.repo_root,
                attempt_archive=self.attempt_archive,
                current_identity_resolver=self._current_identity_resolver,
            )
        return self._live_repair

    def close(self) -> None:
        if self._live_repair is not None:
            self._live_repair.close()
        super().close()


def _json(status: int, payload: Mapping[str, Any]) -> tuple[int, str, bytes]:
    packet = {
        **dict(payload),
        "showcase_live_repair_version": SHOWCASE_LIVE_REPAIR_VERSION,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "production_mutation": False,
        "professional_authority": False,
        "physical_work_authority": False,
        "learning_promotion": False,
    }
    return status, "application/json; charset=utf-8", json.dumps(
        packet,
        indent=2,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def _error(message: str, status: int = 400) -> tuple[int, str, bytes]:
    return _json(status, {"ok": False, "error": message, "fail_closed": True})


def _parts(path: str) -> list[str]:
    return [part for part in path.strip("/").split("/") if part]


def _approved_repo_relative_path(value: Any, name: str, allowed: set[str]) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "\\" in text or "\0" in text or "\n" in text or "\r" in text:
        raise ValueError(f"{name} must be a POSIX repository-relative path")
    pure = PurePosixPath(text)
    normalized = pure.as_posix()
    if pure.is_absolute() or ".." in pure.parts or normalized not in allowed:
        raise ValueError(f"{name} must be an approved repo-relative path")
    return normalized


def dispatch_live_repair_request(
    state: LiveRepairShowcaseState,
    method: str,
    raw_path: str,
    payload: Mapping[str, Any] | None = None,
) -> tuple[int, str, bytes]:
    route = urlparse(raw_path).path.rstrip("/") or "/"
    body = dict(payload or {})
    parts = _parts(route)
    try:
        if method == "GET" and route == "/api/showcase/live-repair/status":
            return _json(200, state.live_repair.status())

        if method == "POST" and route == "/api/showcase/live-repair/capture/start":
            return _json(200, state.live_repair.start_capture(body))

        if (
            method == "POST"
            and len(parts) == 7
            and parts[:4] == ["api", "showcase", "live-repair", "capture"]
        ):
            capture_id, action = parts[4], parts[5]
            if parts[6] != "v1":
                return _error("unsupported live-repair route version", 404)
            if action == "event":
                result = state.live_repair.observe(
                    capture_id,
                    str(body.get("event_type") or "BROWSER_EVENT"),
                    body.get("payload") if isinstance(body.get("payload"), Mapping) else {},
                )
                return _json(200, result)
            if action == "mark":
                result = state.live_repair.mark(
                    capture_id,
                    str(body.get("marker") or ""),
                    body.get("payload") if isinstance(body.get("payload"), Mapping) else {},
                )
                return _json(200, result)
            if action == "finalize":
                return _json(200, state.live_repair.finalize_capture(capture_id, body))

        if method == "POST" and route == "/api/showcase/live-repair/replay/run":
            venv_path = body.get("venv_path")
            if venv_path is not None:
                venv_str = str(venv_path)
                if any(c in venv_str for c in ("\0", "\n", "\r", ";", "|", "&", "$", "`")):
                    return _error("venv_path contains unsafe characters", 400)
            profile_path = _approved_repo_relative_path(
                body.get("profile_path"),
                "profile_path",
                {".aura/runtime_profiles/construction_demo_bilateral.v2.json"},
            )
            output_dir = _approved_repo_relative_path(
                body.get("output_dir"),
                "output_dir",
                {"scripts/runtime_profile_v2_output"},
            )
            result = state.live_repair.execute_replay(
                packet_id=str(body.get("packet_id") or ""),
                profile_path=profile_path,
                confirmation_packet=str(body.get("confirmation_packet") or ""),
                output_dir=output_dir,
                venv_path=venv_path,
                baseline_receipt=body.get("baseline_receipt"),
            )
            return _json(200 if result.get("ok") else 409, result)

        if method == "POST" and route == "/api/showcase/live-repair/attempt":
            identity = BilateralIdentity.from_mapping(body.get("current_identity") or {})
            packet_id = str(body.get("packet_id") or "")
            result = state.live_repair.record_repair_attempt(
                packet_id=packet_id,
                hypothesis=body.get("hypothesis") if isinstance(body.get("hypothesis"), Mapping) else {},
                candidate_digest=str(body.get("candidate_digest") or ""),
                runtime_proof_ref=str(body.get("runtime_proof_ref") or ""),
                minimized_counterexample=(
                    body.get("minimized_counterexample")
                    if isinstance(body.get("minimized_counterexample"), Mapping)
                    else None
                ),
                current_identity=identity,
                arena_id=str(body.get("arena_id") or "coding"),
            )
            state.live_repair_attempts[(result.replay_packet_digest, result.attempt_id)] = result
            return _json(200 if result.promotion_ready else 409, {"ok": result.promotion_ready, "attempt": result.to_dict()})

        if method == "POST" and route == "/api/showcase/live-repair/preview":
            if body.get("rollback_preauthorized") is True:
                return _error("browser requests cannot manufacture a rollback adapter; use the trusted in-process preview owner", 409)
            identity = BilateralIdentity.from_mapping(body.get("current_identity") or {})
            receipt = state.live_repair.preview_candidate(
                packet_id=str(body.get("packet_id") or ""),
                current_identity=identity,
                candidate_digest=str(body.get("candidate_digest") or ""),
                last_verified_digest=str(body.get("last_verified_digest") or ""),
                health_before=body.get("health_before") if isinstance(body.get("health_before"), Mapping) else {},
                health_after=body.get("health_after") if isinstance(body.get("health_after"), Mapping) else {},
                environment_class=str(body.get("environment_class") or ""),
                rollback_preauthorized=False,
                rollback_reason=str(body.get("rollback_reason") or ""),
                restore_local=None,
            )
            state.live_repair_previews[receipt.preview_id] = receipt
            preview_ok = not receipt.degraded or receipt.technical_rollback_executed
            return _json(200 if preview_ok else 409, {"ok": preview_ok, "preview": receipt.to_dict()})

        if method == "POST" and route == "/api/showcase/live-repair/projection":
            identity = BilateralIdentity.from_mapping(body.get("current_identity") or {})
            packet_id = str(body.get("packet_id") or "")
            packet = state.live_repair._packet(packet_id)
            attempt_ids = [str(item) for item in body.get("attempt_ids") or []]
            attempts = (
                [
                    state.live_repair_attempts[(packet.packet_digest, item)]
                    for item in attempt_ids
                    if (packet.packet_digest, item) in state.live_repair_attempts
                ]
                if attempt_ids
                else list(state.live_repair.attempts_for_packet(packet_id))
            )
            preview_id = str(body.get("preview_id") or "")
            preview = (
                state.live_repair_previews.get(preview_id)
                if preview_id
                else state.live_repair.latest_preview(packet_id)
            )
            projection = state.live_repair.build_projection(
                packet_id=packet_id,
                intent=body.get("intent") if isinstance(body.get("intent"), Mapping) else {},
                plan=body.get("plan") if isinstance(body.get("plan"), Mapping) else {},
                code_targets=[item for item in body.get("code_targets") or [] if isinstance(item, Mapping)],
                attempts=attempts,
                preview=preview,
                u7_result=None,
                source_drilldown=[item for item in body.get("source_drilldown") or [] if isinstance(item, Mapping)],
                receipt_drilldown=[item for item in body.get("receipt_drilldown") or [] if isinstance(item, Mapping)],
                current_identity=identity,
            )
            return _json(200, {"ok": True, "projection": projection})

    except (BilateralLiveRepairError, BilateralRuntimeProfileError, ValueError, TypeError, KeyError) as exc:
        return _error(str(exc), 409)

    return base_dispatch_showcase_request(state, method, raw_path, body)


_FOUNDRY_MARKUP = """
<section id="foundry-view" class="view" data-surface-identity="AURA_SPATIAL_FOUNDRY">
  <section class="hero foundry-hero">
    <div>
      <p class="eyebrow">B11-B15 bilateral live repair · projection only</p>
      <h1>Aura, watch this.</h1>
      <p class="lede">Capture one explicit bounded incident, replay it against the exact bilateral contract, inspect failed repair evidence, and project proof without granting mutation or promotion authority.</p>
    </div>
    <div class="hero-actions">
      <button id="foundry-start" class="primary">Start bounded capture</button>
      <button id="foundry-mark" class="secondary" disabled>There — mark incident</button>
      <button id="foundry-finalize" class="secondary" disabled>Finalize replay</button>
    </div>
  </section>
  <section class="foundry-grid">
    <article class="foundry-card"><p class="eyebrow">Exact bilateral identity</p><textarea id="foundry-identity" aria-label="Exact bilateral identity JSON" spellcheck="false"></textarea></article>
    <article class="foundry-card"><p class="eyebrow">Contract obligations</p><label>Will do<textarea id="foundry-positive"></textarea></label><label>Will not do<textarea id="foundry-negative"></textarea></label><label>Will preserve<textarea id="foundry-preservation"></textarea></label></article>
    <article class="foundry-card foundry-timeline"><p class="eyebrow">Incident timeline</p><div id="foundry-events" aria-live="polite"></div></article>
    <article class="foundry-card foundry-proof"><p class="eyebrow">Proof and receipts</p><pre id="foundry-output">No capture active.</pre></article>
  </section>
  <section class="foundry-projection" aria-label="Spatial Foundry evidence projection">
    <article class="foundry-node foundry-center"><p class="eyebrow">Confirmed human intent</p><div id="foundry-projection-intent"></div></article>
    <article class="foundry-node foundry-left"><p class="eyebrow">Aura will not do</p><div id="foundry-projection-negative"></div></article>
    <article class="foundry-node foundry-right"><p class="eyebrow">Preservation and guardrails</p><div id="foundry-projection-guardrails"></div></article>
    <article class="foundry-node"><p class="eyebrow">Live runtime</p><div id="foundry-projection-runtime"></div></article>
    <article class="foundry-node"><p class="eyebrow">Failed attempts and counterexamples</p><div id="foundry-projection-failures"></div></article>
    <article class="foundry-node"><p class="eyebrow">P0 / P1 / current reproof</p><div id="foundry-projection-proof"></div></article>
    <article class="foundry-node"><p class="eyebrow">Human/community disposition</p><div id="foundry-projection-disposition"></div></article>
    <article class="foundry-node foundry-drilldown"><p class="eyebrow">Exact source and receipt drill-down</p><div id="foundry-projection-drilldown"></div></article>
  </section>
  <section class="foundry-authority" aria-label="Foundry authority limits">
    <strong>Projection only</strong><span>no visual truth</span><span>no patch</span><span>no commit/push/PR</span><span>no merge/deploy</span><span>no physical or professional authority</span><span>no learning promotion</span>
  </section>
</section>
""".encode("utf-8")


def _static_response(route: str) -> tuple[int, str, bytes]:
    relative = route.lstrip("/")
    if relative in {"live-repair-foundry.js", "live-repair-foundry.css"}:
        path = (STATIC_DIR / relative).resolve()
        try:
            path.relative_to(STATIC_DIR.resolve())
        except ValueError:
            return _error("invalid static path", 400)
        if not path.is_file() or path.is_symlink():
            return _error("static asset not found", 404)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"
        return 200, content_type, path.read_bytes()

    status, content_type, body = base_static_response(route)
    if status == 200 and route in {"/", "/index.html"}:
        if b"live-repair-foundry.css" not in body:
            body = body.replace(
                b"</head>",
                b'  <link rel="stylesheet" href="live-repair-foundry.css">\n</head>',
            )
        if b'data-tab="foundry"' not in body:
            body = body.replace(
                b"</nav>",
                b'      <button class="tab" data-tab="foundry">Live Repair Foundry</button>\n    </nav>',
            )
        if b'id="foundry-view"' not in body:
            body = body.replace(b"</main>", _FOUNDRY_MARKUP + b"\n</main>")
        if b"live-repair-foundry.js" not in body:
            body = body.replace(
                b"</body>",
                b'  <script src="live-repair-foundry.js"></script>\n</body>',
            )
    return status, content_type, body


def make_handler(state: LiveRepairShowcaseState):
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
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                return {}
            if length < 0 or length > MAX_BODY_BYTES:
                return {}
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}
            return value if isinstance(value, dict) else {}

        def do_GET(self) -> None:  # noqa: N802
            route = urlparse(self.path).path
            if route.startswith("/api/"):
                self._send(*dispatch_live_repair_request(state, "GET", self.path))
            else:
                self._send(*_static_response(route))

        def do_POST(self) -> None:  # noqa: N802
            self._send(*dispatch_live_repair_request(state, "POST", self.path, self._payload()))

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def serve(*, host: str, port: int, repo_root: str | Path, demo_project: str, auto_start: bool) -> None:
    state = LiveRepairShowcaseState(repo_root, demo_project=demo_project, auto_start=auto_start)
    server = HTTPServer((host, port), make_handler(state))
    try:
        print(f"Aura Showcase + Live Repair Foundry: http://{host}:{port}")
        server.serve_forever()
    finally:
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
