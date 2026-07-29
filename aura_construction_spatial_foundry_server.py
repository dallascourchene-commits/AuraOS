"""Composed Construction Spatial Foundry server for PR 1.

This adapter reuses the merged Showcase and B15 live-repair routes.  It adds a
trusted identity-handle boundary, exact Construction arena attribution, required
asset intake, and V2 domain projection while retaining all legacy routes.
"""
from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aura_bilateral_live_repair_foundry import (
    BilateralIdentity,
    BilateralLiveRepairError,
    PreviewRollbackReceipt,
    RepairCandidateResult,
)
from aura_construction_spatial_foundry import (
    ArenaBoundBilateralLiveRepairService,
    TrustedBilateralIdentityBroker,
    reject_raw_identity_currency_claim,
)
from aura_showcase_live_repair_server import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    MAX_BODY_BYTES,
    LiveRepairShowcaseState,
    _error,
    _json,
    _static_response as base_static_response,
    dispatch_live_repair_request as base_dispatch_live_repair_request,
)
from scripts.aura_runtime_profile_v2_adapter import BilateralRuntimeProfileError

CONSTRUCTION_FOUNDRY_SERVER_VERSION = "AURA_CONSTRUCTION_SPATIAL_FOUNDRY_SERVER_V1"
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
LOGGER = logging.getLogger(__name__)


class ConstructionFoundryShowcaseState(LiveRepairShowcaseState):
    def __init__(
        self,
        repo_root: str | Path,
        *,
        demo_project: str,
        auto_start: bool,
        trusted_identity_provider: Callable[[], BilateralIdentity] | None = None,
        current_identity_resolver: Callable[[BilateralIdentity], BilateralIdentity] | None = None,
    ) -> None:
        effective_resolver = current_identity_resolver
        if effective_resolver is None and trusted_identity_provider is not None:
            effective_resolver = lambda _expected: trusted_identity_provider()
        super().__init__(
            repo_root,
            demo_project=demo_project,
            auto_start=auto_start,
            current_identity_resolver=effective_resolver,
        )
        self._trusted_identity_provider = trusted_identity_provider
        self._identity_broker = (
            TrustedBilateralIdentityBroker(
                trusted_identity_provider,
                current_identity_resolver=effective_resolver,
            )
            if trusted_identity_provider is not None
            else None
        )

    @property
    def live_repair(self) -> ArenaBoundBilateralLiveRepairService:
        if self._live_repair is None:
            self._live_repair = ArenaBoundBilateralLiveRepairService(
                self.repo_root,
                attempt_archive=self.attempt_archive,
                current_identity_resolver=self._current_identity_resolver,
            )
        return self._live_repair

    def issue_current_identity_summary(self) -> dict[str, Any]:
        if self._identity_broker is None:
            raise BilateralLiveRepairError(
                "trusted current identity provider is not configured"
            )
        return self._identity_broker.issue_summary()

    def resolve_request_identity(
        self,
        body: Mapping[str, Any],
        *,
        expected: BilateralIdentity | None = None,
        legacy_field: str = "current_identity",
    ) -> BilateralIdentity:
        reject_raw_identity_currency_claim(body)
        handle = str(body.get("identity_handle") or "").strip()
        if handle:
            if self._identity_broker is None:
                raise BilateralLiveRepairError(
                    "trusted identity handle cannot be resolved by this server"
                )
            return self._identity_broker.resolve(handle, expected=expected)
        if self._identity_broker is not None:
            raise BilateralLiveRepairError(
                "polished Construction flow requires a server-issued identity_handle"
            )
        raw = body.get(legacy_field)
        item = BilateralIdentity.from_mapping(raw or {})
        if expected is not None:
            expected.assert_current(item)
        return item


def _identity_provider_from_path(path: str | Path) -> Callable[[], BilateralIdentity]:
    source = Path(path)
    if source.is_symlink():
        raise BilateralLiveRepairError("trusted identity packet must not be a symlink")
    resolved = source.resolve()

    def provide() -> BilateralIdentity:
        if not resolved.is_file():
            raise BilateralLiveRepairError("trusted identity packet is unavailable")
        try:
            value = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BilateralLiveRepairError("trusted identity packet is invalid") from exc
        return BilateralIdentity.from_mapping(value)

    return provide


def _is_v2_projection(body: Mapping[str, Any]) -> bool:
    return bool(
        body.get("projection_version") == "AURA_SPATIAL_FOUNDRY_PROJECTION_V2"
        or any(
            key in body
            for key in (
                "domain",
                "domain_targets",
                "domain_artifacts",
                "presentation",
                "construction",
                "coordination_candidates",
                "domain_decision",
            )
        )
    )


def _mapping_rows(body: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = body.get(key) or []
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise BilateralLiveRepairError(f"{key} must be an array")
    rows = list(value)
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise BilateralLiveRepairError(f"{key}[{index}] must be an object")
    return rows


def _optional_mapping(body: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = body.get(key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise BilateralLiveRepairError(f"{key} must be an object")
    return value


def _validate_required_asset_paths(body: Mapping[str, Any]) -> None:
    assets = _mapping_rows(body, "required_assets")
    seen: dict[str, str] = {}
    for index, row in enumerate(assets):
        path = str(row.get("path") or "").strip()
        sha256 = str(row.get("sha256") or "").strip().lower()
        if not path:
            raise BilateralLiveRepairError(
                f"required_assets[{index}].path must be non-empty"
            )
        previous = seen.get(path)
        if previous is not None:
            detail = "conflicting hashes" if previous != sha256 else "duplicate path"
            raise BilateralLiveRepairError(
                f"required_assets[{index}] has {detail}: {path}"
            )
        seen[path] = sha256


def _selected_attempts(
    state: ConstructionFoundryShowcaseState,
    packet_id: str,
    body: Mapping[str, Any],
) -> list[RepairCandidateResult]:
    attempts = list(state.live_repair.attempts_for_packet(packet_id))
    raw_ids = body.get("attempt_ids") or []
    if isinstance(raw_ids, (str, bytes, bytearray)) or not isinstance(
        raw_ids, Sequence
    ):
        raise BilateralLiveRepairError("attempt_ids must be an array")
    if not raw_ids:
        return attempts
    attempt_ids = [str(item or "").strip() for item in raw_ids]
    if any(not item for item in attempt_ids):
        raise BilateralLiveRepairError("attempt_ids must contain non-empty strings")
    if len(attempt_ids) != len(set(attempt_ids)):
        raise BilateralLiveRepairError("attempt_ids must not contain duplicates")
    by_id = {item.attempt_id: item for item in attempts}
    missing = [item for item in attempt_ids if item not in by_id]
    if missing:
        raise BilateralLiveRepairError(
            f"requested attempts are not retained for this packet: {missing}"
        )
    return [by_id[item] for item in attempt_ids]


def _v2_projection_response(
    state: ConstructionFoundryShowcaseState,
    body: Mapping[str, Any],
) -> tuple[int, str, bytes]:
    packet_id = str(body.get("packet_id") or "")
    packet = state.live_repair.packet(packet_id)
    identity = state.resolve_request_identity(body, expected=packet.identity)
    attempts = _selected_attempts(state, packet_id, body)
    preview_id = str(body.get("preview_id") or "")
    preview: PreviewRollbackReceipt | None = (
        state.live_repair_previews.get(preview_id)
        if preview_id
        else state.live_repair.latest_preview(packet_id)
    )
    if preview_id and preview is None:
        raise BilateralLiveRepairError(
            "requested preview is not retained for this packet"
        )
    if "u7_result" in body:
        raise BilateralLiveRepairError(
            "V2 projection cannot accept client-authored U7 evidence"
        )
    transition_state, transition_evidence = _derive_transition_state(
        packet, attempts, preview, None
    )
    raw_domain = _optional_mapping(body, "domain")
    requested_arena = raw_domain.get("arena_id")
    if requested_arena not in {None, "", "construction"}:
        raise BilateralLiveRepairError(
            "Construction server domain.arena_id must be construction"
        )
    requested_type = raw_domain.get("domain_type")
    if requested_type not in {None, "", "CONSTRUCTION"}:
        raise BilateralLiveRepairError(
            "Construction server domain.domain_type must be CONSTRUCTION"
        )
    domain = {
        **dict(raw_domain),
        "arena_id": "construction",
        "domain_type": "CONSTRUCTION",
        "runtime_packet_digest": packet.packet_digest,
    }
    try:
        projection = state.live_repair.build_projection_v2(
            packet_id=packet_id,
            intent=body.get("intent")
            if isinstance(body.get("intent"), Mapping)
            else {},
            plan=body.get("plan") if isinstance(body.get("plan"), Mapping) else {},
            code_targets=_mapping_rows(body, "code_targets"),
            attempts=attempts,
            preview=preview,
            u7_result=None,
            source_drilldown=_mapping_rows(body, "source_drilldown"),
            receipt_drilldown=_mapping_rows(body, "receipt_drilldown"),
            current_identity=identity,
            domain=domain,
            domain_targets=_mapping_rows(body, "domain_targets"),
            domain_artifacts=_mapping_rows(body, "domain_artifacts"),
            presentation=_optional_mapping(body, "presentation"),
            construction=_optional_mapping(body, "construction"),
            coordination_candidates=_mapping_rows(
                body, "coordination_candidates"
            ),
            domain_decision=(
                _optional_mapping(body, "domain_decision")
                if "domain_decision" in body
                else None
            ),
            transition_state=transition_state,
            transition_evidence=transition_evidence,
        )
    except ValueError as exc:
        raise BilateralLiveRepairError(str(exc)) from exc
    return _json(
        200,
        {
            "ok": True,
            "projection": projection,
            "construction_foundry_server_version": CONSTRUCTION_FOUNDRY_SERVER_VERSION,
        },
    )


def _derive_transition_state(
    packet: Any,
    attempts: list[RepairCandidateResult],
    preview: PreviewRollbackReceipt | None,
    u7_result: Mapping[str, Any] | None,
) -> tuple[str, dict[str, bool]]:
    dissolution = packet.dissolution_receipt
    capture_dissolved = (
        dissolution.terminal_state == "DISSOLVED"
        and dissolution.buffers_cleared is True
        and dissolution.timers_released is True
        and dissolution.listeners_released is True
    )
    evidence = {
        "identity_current": True,
        "operator_authorized": packet.privacy_receipt.get("unrestricted_recording") is False,
        "incident_marker_present": packet.marker_event.event_type == "INCIDENT_MARKER",
        "capture_dissolved": capture_dissolved,
        "required_assets_bound": bool(packet.required_assets),
        "runtime_proof_retained": bool(attempts),
        "repair_attempt_retained": bool(attempts),
        "preview_receipt_retained": preview is not None,
        "u7_current_reproof_retained": bool(u7_result),
        "human_disposition_retained": bool(
            dict((u7_result or {}).get("finalization") or {}).get("human_disposition")
        ),
        "resources_dissolved": capture_dissolved,
    }
    state = "INCIDENT_MARKED"
    if evidence["capture_dissolved"] and evidence["required_assets_bound"]:
        state = "REPLAY_READY"
    if evidence["runtime_proof_retained"]:
        state = "RUNTIME_PROVEN"
    if evidence["repair_attempt_retained"]:
        state = "REPAIR_ASSESSED"
    if evidence["preview_receipt_retained"]:
        state = "PREVIEWED"
    if evidence["u7_current_reproof_retained"]:
        state = "REPROOF_RETAINED"
    if evidence["human_disposition_retained"] and evidence["resources_dissolved"]:
        state = "DISSOLVED"
    return state, evidence


def dispatch_construction_foundry_request(
    state: ConstructionFoundryShowcaseState,
    method: str,
    raw_path: str,
    payload: Mapping[str, Any] | None = None,
) -> tuple[int, str, bytes]:
    route = urlparse(raw_path).path.rstrip("/") or "/"
    body = dict(payload or {})
    try:
        if method == "GET" and route == "/api/showcase/live-repair/identity/current":
            result = state.issue_current_identity_summary()
            return _json(
                200,
                {
                    **result,
                    "construction_foundry_server_version": CONSTRUCTION_FOUNDRY_SERVER_VERSION,
                },
            )

        if method == "POST":
            reject_raw_identity_currency_claim(body)
            if "transition_state" in body or "transition_evidence" in body:
                raise BilateralLiveRepairError(
                    "browser requests cannot supply guarded WFST state or evidence"
                )

        if method == "POST" and route == "/api/showcase/live-repair/capture/start":
            if body.get("identity_handle"):
                identity = state.resolve_request_identity(body, legacy_field="identity")
                body["identity"] = asdict(identity)
                body.pop("identity_handle", None)
            elif state._identity_broker is not None:
                raise BilateralLiveRepairError(
                    "capture start requires a server-issued identity_handle"
                )
            body["arena_id"] = "construction"
            return base_dispatch_live_repair_request(state, method, raw_path, body)

        if method == "POST" and route == "/api/showcase/live-repair/attempt":
            packet_id = str(body.get("packet_id") or "")
            packet = state.live_repair.packet(packet_id)
            identity = state.resolve_request_identity(body, expected=packet.identity)
            body["current_identity"] = asdict(identity)
            body["arena_id"] = state.live_repair.arena_for_packet(packet_id)
            body.pop("identity_handle", None)
            return base_dispatch_live_repair_request(state, method, raw_path, body)

        if method == "POST" and route == "/api/showcase/live-repair/preview":
            packet_id = str(body.get("packet_id") or "")
            packet = state.live_repair.packet(packet_id)
            identity = state.resolve_request_identity(body, expected=packet.identity)
            body["current_identity"] = asdict(identity)
            body.pop("identity_handle", None)
            return base_dispatch_live_repair_request(state, method, raw_path, body)

        if method == "POST" and route == "/api/showcase/live-repair/replay/run":
            packet_id = str(body.get("packet_id") or "")
            packet = state.live_repair.packet(packet_id)
            if state._identity_broker is not None:
                state.resolve_request_identity(body, expected=packet.identity)
                body.pop("identity_handle", None)
            elif state._current_identity_resolver is not None:
                state.live_repair.assert_current_identity(packet_id)
            return base_dispatch_live_repair_request(state, method, raw_path, body)

        if (
            method == "POST"
            and route == "/api/showcase/live-repair/projection"
            and _is_v2_projection(body)
        ):
            return _v2_projection_response(state, body)

        if method == "POST" and route == "/api/showcase/live-repair/projection":
            packet_id = str(body.get("packet_id") or "")
            packet = state.live_repair.packet(packet_id)
            identity = state.resolve_request_identity(body, expected=packet.identity)
            body["current_identity"] = asdict(identity)
            body.pop("identity_handle", None)
            return base_dispatch_live_repair_request(state, method, raw_path, body)

        if (
            method == "POST"
            and route.startswith("/api/showcase/live-repair/capture/")
            and route.endswith("/finalize/v1")
        ):
            _validate_required_asset_paths(body)
            body["arena_id"] = "construction"

    except (BilateralLiveRepairError, BilateralRuntimeProfileError) as exc:
        return _error(str(exc), 409)
    except Exception:  # noqa: BLE001
        LOGGER.exception("unexpected Construction Foundry request failure")
        return _error("internal Construction Foundry error", 500)

    return base_dispatch_live_repair_request(state, method, raw_path, body)


_CONSTRUCTION_MARKUP = b"""
<section id="construction-foundry-pr1" class="foundry-grid" aria-label="Construction Foundry PR1 bindings">
  <article class="foundry-card">
    <p class="eyebrow">Trusted current identity</p>
    <pre id="construction-foundry-identity-summary">Server identity not loaded.</pre>
  </article>
  <article class="foundry-card">
    <p class="eyebrow">Required asset identities</p>
    <label>JSON array of path / sha256 pairs
      <textarea id="construction-foundry-required-assets" spellcheck="false">[]</textarea>
    </label>
  </article>
</section>
"""

_SCRIPT = b'  <script src="construction-spatial-foundry.js"></script>\n'


def _static_response(route: str) -> tuple[int, str, bytes]:
    if route.lstrip("/") == "construction-spatial-foundry.js":
        path = STATIC_DIR / "construction-spatial-foundry.js"
        if not path.is_file() or path.is_symlink():
            return _error("Construction Foundry static asset not found", 404)
        return 200, "application/javascript; charset=utf-8", path.read_bytes()

    status, content_type, body = base_static_response(route)
    if status == 200 and route in {"/", "/index.html"}:
        if b'id="construction-foundry-pr1"' not in body:
            body = body.replace(
                b'<section class="foundry-authority"',
                _CONSTRUCTION_MARKUP + b'\n  <section class="foundry-authority"',
                1,
            )
        if b"construction-spatial-foundry.js" not in body:
            body = body.replace(b"</body>", _SCRIPT + b"</body>", 1)
    return status, content_type, body


def make_handler(state: ConstructionFoundryShowcaseState):
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
                self._send(
                    *dispatch_construction_foundry_request(state, "GET", self.path)
                )
            else:
                self._send(*_static_response(route))

        def do_POST(self) -> None:  # noqa: N802
            self._send(
                *dispatch_construction_foundry_request(
                    state, "POST", self.path, self._payload()
                )
            )

        def log_message(self, message_format: str, *args: Any) -> None:
            return

    return Handler


def serve(
    *,
    host: str,
    port: int,
    repo_root: str | Path,
    demo_project: str,
    auto_start: bool,
    trusted_identity_packet: str | Path | None = None,
) -> None:
    provider = (
        _identity_provider_from_path(trusted_identity_packet)
        if trusted_identity_packet
        else None
    )
    state = ConstructionFoundryShowcaseState(
        repo_root,
        demo_project=demo_project,
        auto_start=auto_start,
        trusted_identity_provider=provider,
    )
    server = HTTPServer((host, port), make_handler(state))
    try:
        print(f"Aura Construction Spatial Foundry: http://{host}:{port}")
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
    parser.add_argument("--trusted-identity-packet", default="")
    parser.add_argument("--no-auto-start", action="store_true")
    args = parser.parse_args()
    serve(
        host=args.host,
        port=args.port,
        repo_root=args.repo_root,
        demo_project=args.demo_project,
        auto_start=not args.no_auto_start,
        trusted_identity_packet=args.trusted_identity_packet or None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONSTRUCTION_FOUNDRY_SERVER_VERSION",
    "ConstructionFoundryShowcaseState",
    "dispatch_construction_foundry_request",
    "make_handler",
    "serve",
]
