"""Composed Construction Spatial Foundry server for PR 1.

This adapter reuses the merged Showcase and B15 live-repair routes.  It adds a
trusted identity-handle boundary, exact Construction arena attribution, required
asset intake, and V2 domain projection while retaining all legacy routes.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from aura_bilateral_live_repair_foundry import (
    BilateralIdentity,
    BilateralLiveRepairError,
    PreviewRollbackReceipt,
    RepairCandidateResult,
)
from aura_bilateral_live_repair_foundry_contracts import PROJECTION_VERSION
from aura_construction_spatial_foundry import (
    ArenaBoundBilateralLiveRepairService,
    TrustedBilateralIdentityBroker,
    reject_raw_identity_currency_claim,
)
from aura_construction_state import ConstructionProjectState
from aura_event_contracts import stable_digest
from aura_showcase_live_repair_server import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    MAX_BODY_BYTES,
    LiveRepairShowcaseState,
    _error,
    _json,
)
from aura_showcase_live_repair_server import (
    _static_response as base_static_response,
)
from aura_showcase_live_repair_server import (
    dispatch_live_repair_request as base_dispatch_live_repair_request,
)
from aura_spatial_receipts import validate_spatial_dissolution_receipt_payload
from scripts.aura_runtime_profile_v2_adapter import BilateralRuntimeProfileError

CONSTRUCTION_FOUNDRY_SERVER_VERSION = "AURA_CONSTRUCTION_SPATIAL_FOUNDRY_SERVER_V1"
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
LOGGER = logging.getLogger(__name__)
_STATE_DIGEST = re.compile(r"^[0-9a-f]{32}$|^[0-9a-f]{40,64}$")
_MISSING = object()
_V2_PROJECTION_VERSION = "AURA_SPATIAL_FOUNDRY_PROJECTION_V2"
_V2_DOMAIN_FIELDS = frozenset(
    {
        "domain",
        "domain_targets",
        "domain_artifacts",
        "presentation",
        "construction",
        "coordination_candidates",
        "domain_decision",
    }
)


class ConstructionFoundryShowcaseState(LiveRepairShowcaseState):
    def __init__(
        self,
        repo_root: str | Path,
        *,
        demo_project: str,
        auto_start: bool,
        trusted_identity_provider: Callable[[], BilateralIdentity] | None = None,
        current_identity_resolver: Callable[[BilateralIdentity], BilateralIdentity] | None = None,
        construction_state_digest_provider: Callable[[str], str] | None = None,
        presentation_dissolution_provider: Callable[[str], bool] | None = None,
    ) -> None:
        effective_resolver = current_identity_resolver
        if effective_resolver is None and trusted_identity_provider is not None:

            def resolve_provider(_expected: BilateralIdentity) -> BilateralIdentity:
                return trusted_identity_provider()

            effective_resolver = resolve_provider
        if effective_resolver is None:
            # Preserve the explicitly documented local legacy flow: its capture
            # identity is pinned for the lifetime of that capture. Broker-backed
            # deployments still re-resolve through their trusted provider.
            def retain_legacy_identity(
                expected: BilateralIdentity,
            ) -> BilateralIdentity:
                return expected

            effective_resolver = retain_legacy_identity
        super().__init__(
            repo_root,
            demo_project=demo_project,
            auto_start=auto_start,
            current_identity_resolver=effective_resolver,
        )
        self._trusted_identity_provider = trusted_identity_provider
        self._construction_state_digest_provider = construction_state_digest_provider
        self._presentation_dissolution_provider = presentation_dissolution_provider
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
        retained = self._live_repair
        if not isinstance(retained, ArenaBoundBilateralLiveRepairService):
            raise BilateralLiveRepairError("Construction Foundry live-repair service type is invalid")
        return retained

    def issue_current_identity_summary(self) -> dict[str, Any]:
        if self._identity_broker is None:
            raise BilateralLiveRepairError("trusted current identity provider is not configured")
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
                raise BilateralLiveRepairError("trusted identity handle cannot be resolved by this server")
            return self._identity_broker.resolve(handle, expected=expected)
        if self._identity_broker is not None:
            raise BilateralLiveRepairError("polished Construction flow requires a server-issued identity_handle")
        raw = body.get(legacy_field)
        item = BilateralIdentity.from_mapping(raw or {})
        if expected is not None:
            expected.assert_current(item)
        return item

    def resolve_construction_state_digest(
        self,
        packet_id: str,
        requested_digest: Any = _MISSING,
        *,
        required: bool,
    ) -> str:
        requested = ""
        if requested_digest is not _MISSING:
            if not isinstance(requested_digest, str):
                raise BilateralLiveRepairError(
                    "domain.state_digest must be a string when supplied"
                )
            requested = requested_digest.strip().lower()
            if requested and not _STATE_DIGEST.fullmatch(requested):
                raise BilateralLiveRepairError(
                    "domain.state_digest must be empty or a canonical digest"
                )
        if self._construction_state_digest_provider is None:
            if required:
                raise BilateralLiveRepairError(
                    "trusted Construction state digest provider is not configured"
                )
            return ""
        resolved = str(self._construction_state_digest_provider(packet_id) or "").strip().lower()
        if not _STATE_DIGEST.fullmatch(resolved):
            raise BilateralLiveRepairError("trusted Construction state digest is invalid")
        if requested and requested != resolved:
            raise BilateralLiveRepairError(
                "requested domain.state_digest differs from trusted Construction state"
            )
        return resolved

    def presentation_resources_dissolved(self, packet_id: str) -> bool:
        if self._presentation_dissolution_provider is None:
            return False
        return self._presentation_dissolution_provider(packet_id) is True


def _identity_provider_from_path(path: str | Path) -> Callable[[], BilateralIdentity]:
    load = _trusted_mapping_provider_from_path(path, "identity packet")

    def provide() -> BilateralIdentity:
        return BilateralIdentity.from_mapping(load())

    return provide


def _trusted_mapping_provider_from_path(
    path: str | Path,
    label: str,
) -> Callable[[], dict[str, Any]]:
    source = Path(path).absolute()
    if source.is_symlink():
        raise BilateralLiveRepairError(f"trusted {label} must not be a symlink")
    resolved = source.resolve()

    def provide() -> dict[str, Any]:
        if source.is_symlink() or source.resolve() != resolved or not source.is_file():
            raise BilateralLiveRepairError(f"trusted {label} is unavailable")
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BilateralLiveRepairError(f"trusted {label} is invalid") from exc
        if not isinstance(value, dict):
            raise BilateralLiveRepairError(f"trusted {label} must be a JSON object")
        return value

    return provide


def _construction_state_digest_provider_from_path(
    path: str | Path,
) -> Callable[[str], str]:
    load = _trusted_mapping_provider_from_path(path, "Construction state packet")

    def provide(_packet_id: str) -> str:
        try:
            raw = load()
            state = ConstructionProjectState.from_dict(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise BilateralLiveRepairError("trusted Construction state packet is invalid") from exc
        canonical = json.loads(json.dumps(state.to_dict(), sort_keys=True))
        if canonical != raw:
            raise BilateralLiveRepairError("trusted Construction state packet is not canonical")
        return state.state_digest

    return provide


def _presentation_dissolution_provider_from_path(
    path: str | Path,
) -> Callable[[str], bool]:
    load = _trusted_mapping_provider_from_path(path, "presentation dissolution packet")

    def provide(packet_id: str) -> bool:
        raw = load()
        if raw.get("packet_id") != packet_id:
            raise BilateralLiveRepairError("trusted presentation dissolution packet belongs to another replay packet")
        dissolution_raw = raw.get("dissolution_receipt")
        cleanup = raw.get("renderer_cleanup_receipt")
        if not isinstance(dissolution_raw, Mapping) or not isinstance(cleanup, Mapping):
            raise BilateralLiveRepairError("trusted presentation dissolution packet lacks canonical cleanup receipts")
        try:
            dissolution = validate_spatial_dissolution_receipt_payload(dissolution_raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise BilateralLiveRepairError("trusted presentation dissolution receipt is invalid") from exc
        required_cleanup = {
            "state",
            "renderer_allocated",
            "evidence_class",
            "session_id",
            "scene_digest",
            "render_plan_digest",
            "renderer_authority",
            "execution_authority",
            "renderer_resources_released",
            "renderer_resources_released_verified",
            "raw_sensor_data_retained",
        }
        if set(cleanup) != required_cleanup:
            raise BilateralLiveRepairError("trusted renderer cleanup receipt has unexpected fields")
        renderer_allocated = cleanup.get("renderer_allocated")
        expected_state = "DISPOSED" if renderer_allocated is True else "NOT_ALLOCATED"
        expected_released = renderer_allocated is True
        if (
            not isinstance(renderer_allocated, bool)
            or cleanup.get("state") != expected_state
            or cleanup.get("evidence_class") != "CLIENT_REPORTED"
            or cleanup.get("session_id") != dissolution.session_id
            or cleanup.get("scene_digest") != dissolution.scene_digest
            or cleanup.get("render_plan_digest") != dissolution.render_plan_digest
            or cleanup.get("renderer_authority") is not False
            or cleanup.get("execution_authority") is not False
            or cleanup.get("renderer_resources_released") is not expected_released
            or cleanup.get("renderer_resources_released_verified") is not False
            or cleanup.get("raw_sensor_data_retained") is not False
        ):
            raise BilateralLiveRepairError("trusted renderer cleanup receipt is invalid or stale")
        supplied_cleanup_digest = raw.get("renderer_cleanup_digest")
        if supplied_cleanup_digest != stable_digest(cleanup, digest_size=32):
            raise BilateralLiveRepairError("trusted renderer cleanup digest is invalid")
        return (
            dissolution.to_dict()["terminal_state"] == "DISSOLVED"
            and raw.get("renderer_cleanup_observed") is True
            and raw.get("lease_released") is True
            and raw.get("renderer_resource_boundary_satisfied") is True
        )

    return provide


def _is_v2_projection(body: Mapping[str, Any]) -> bool:
    has_domain_fields = any(key in body for key in _V2_DOMAIN_FIELDS)
    if "projection_version" not in body:
        return has_domain_fields
    version = body.get("projection_version")
    if version not in {PROJECTION_VERSION, _V2_PROJECTION_VERSION}:
        raise BilateralLiveRepairError("unsupported projection_version")
    if version == PROJECTION_VERSION and has_domain_fields:
        raise BilateralLiveRepairError(
            "Spatial Foundry V1 projection cannot include V2 domain fields"
        )
    return version == _V2_PROJECTION_VERSION


def _mapping_rows(body: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    if key not in body:
        return []
    value = body[key]
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise BilateralLiveRepairError(f"{key} must be an array")
    rows = list(value)
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise BilateralLiveRepairError(f"{key}[{index}] must be an object")
    return rows


def _optional_mapping(body: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    if key not in body:
        return {}
    value = body[key]
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
            raise BilateralLiveRepairError(f"required_assets[{index}].path must be non-empty")
        previous = seen.get(path)
        if previous is not None:
            detail = "conflicting hashes" if previous != sha256 else "duplicate path"
            raise BilateralLiveRepairError(f"required_assets[{index}] has {detail}: {path}")
        seen[path] = sha256


def _selected_attempts(
    state: ConstructionFoundryShowcaseState,
    packet_id: str,
    body: Mapping[str, Any],
) -> list[RepairCandidateResult]:
    attempts = list(state.live_repair.attempts_for_packet(packet_id))
    raw_ids = body.get("attempt_ids", ())
    if isinstance(raw_ids, (str, bytes, bytearray)) or not isinstance(raw_ids, Sequence):
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
        raise BilateralLiveRepairError(f"requested attempts are not retained for this packet: {missing}")
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
    preview = state.live_repair.preview_for_packet(
        packet_id,
        preview_id,
    )
    if preview_id and preview is None:
        raise BilateralLiveRepairError("requested preview is not retained for this packet")
    if preview is not None and preview.replay_packet_digest != packet.packet_digest:
        raise BilateralLiveRepairError("requested preview belongs to another incident")
    if preview is not None and preview.candidate_digest not in {item.candidate_digest for item in attempts}:
        raise BilateralLiveRepairError("selected preview is not bound to a selected repair attempt")
    if "u7_result" in body:
        raise BilateralLiveRepairError("V2 projection cannot accept client-authored U7 evidence")
    verified_candidate_digests = {
        item.candidate_digest for item in attempts if item.promotion_ready is True
    }
    u7_candidate_digests: list[str] = []
    if preview is not None:
        if preview.candidate_digest not in verified_candidate_digests:
            raise BilateralLiveRepairError(
                "selected preview candidate is not a promotion-ready selected repair attempt"
            )
        u7_candidate_digests.append(preview.candidate_digest)
    u7_result = state.live_repair.latest_u7_result(
        packet_id,
        candidate_digests=u7_candidate_digests,
    )
    if u7_result is not None and (
        preview is None or u7_result.get("candidate_digest") != preview.candidate_digest
    ):
        raise BilateralLiveRepairError("retained U7 evidence differs from the selected preview candidate")
    runtime_proof_retained = state.live_repair.has_retained_runtime_proof(packet_id)
    transition_state, transition_evidence = _derive_transition_state(
        packet,
        attempts,
        preview,
        u7_result,
        runtime_proof_retained=runtime_proof_retained,
        presentation_resources_dissolved=state.presentation_resources_dissolved(packet_id),
    )
    raw_domain = _optional_mapping(body, "domain")
    requested_arena = raw_domain.get("arena_id")
    if requested_arena not in {None, "", "construction"}:
        raise BilateralLiveRepairError("Construction server domain.arena_id must be construction")
    requested_type = raw_domain.get("domain_type")
    if requested_type not in {None, "", "CONSTRUCTION"}:
        raise BilateralLiveRepairError("Construction server domain.domain_type must be CONSTRUCTION")
    coordination_candidates = _mapping_rows(body, "coordination_candidates")
    trusted_state_digest = state.resolve_construction_state_digest(
        packet_id,
        (
            raw_domain["state_digest"]
            if "state_digest" in raw_domain
            else _MISSING
        ),
        required=bool(raw_domain.get("state_digest")) or bool(coordination_candidates),
    )
    domain = {
        **dict(raw_domain),
        "arena_id": "construction",
        "domain_type": "CONSTRUCTION",
        "runtime_packet_digest": packet.packet_digest,
    }
    if trusted_state_digest:
        domain["state_digest"] = trusted_state_digest
    else:
        domain.pop("state_digest", None)
    try:
        projection = state.live_repair.build_projection_v2(
            packet_id=packet_id,
            intent=_optional_mapping(body, "intent"),
            plan=_optional_mapping(body, "plan"),
            code_targets=_mapping_rows(body, "code_targets"),
            attempts=attempts,
            preview=preview,
            u7_result=u7_result,
            source_drilldown=_mapping_rows(body, "source_drilldown"),
            receipt_drilldown=_mapping_rows(body, "receipt_drilldown"),
            current_identity=identity,
            domain=domain,
            domain_targets=_mapping_rows(body, "domain_targets"),
            domain_artifacts=_mapping_rows(body, "domain_artifacts"),
            presentation=_optional_mapping(body, "presentation"),
            construction=_optional_mapping(body, "construction"),
            coordination_candidates=coordination_candidates,
            domain_decision=(_optional_mapping(body, "domain_decision") if "domain_decision" in body else None),
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
    *,
    runtime_proof_retained: bool,
    presentation_resources_dissolved: bool = False,
) -> tuple[str, dict[str, bool]]:
    def required_asset_is_bound(item: Any) -> bool:
        if isinstance(item, Mapping):
            return bool(item.get("path")) and bool(item.get("sha256"))
        return bool(getattr(item, "path", "")) and bool(getattr(item, "sha256", ""))

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
        "required_assets_bound": all(required_asset_is_bound(item) for item in packet.required_assets),
        "runtime_proof_retained": runtime_proof_retained is True,
        "repair_attempt_retained": bool(attempts),
        "preview_receipt_retained": preview is not None,
        "u7_current_reproof_retained": bool(u7_result) and u7_result.get("ok") is True,
        "human_disposition_retained": bool(dict((u7_result or {}).get("finalization") or {}).get("human_disposition")),
        "resources_dissolved": presentation_resources_dissolved is True,
    }
    state = "INCIDENT_MARKED"
    ordered_stages = (
        (
            "REPLAY_READY",
            evidence["capture_dissolved"] and evidence["required_assets_bound"],
        ),
        ("RUNTIME_PROVEN", evidence["runtime_proof_retained"]),
        ("REPAIR_ASSESSED", evidence["repair_attempt_retained"]),
        ("PREVIEWED", evidence["preview_receipt_retained"]),
        ("REPROOF_RETAINED", evidence["u7_current_reproof_retained"]),
        (
            "DISSOLVED",
            evidence["human_disposition_retained"] and evidence["resources_dissolved"],
        ),
    )
    for next_state, requirements_satisfied in ordered_stages:
        if not requirements_satisfied:
            break
        state = next_state
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
                raise BilateralLiveRepairError("browser requests cannot supply guarded WFST state or evidence")

        if method == "POST" and route == "/api/showcase/live-repair/capture/start":
            if body.get("identity_handle"):
                identity = state.resolve_request_identity(body, legacy_field="identity")
                body["identity"] = asdict(identity)
                body.pop("identity_handle", None)
            elif state._identity_broker is not None:
                raise BilateralLiveRepairError("capture start requires a server-issued identity_handle")
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

        if method == "POST" and route == "/api/showcase/live-repair/projection" and _is_v2_projection(body):
            return _v2_projection_response(state, body)

        if method == "POST" and route == "/api/showcase/live-repair/projection":
            packet_id = str(body.get("packet_id") or "")
            packet = state.live_repair.packet(packet_id)
            identity = state.resolve_request_identity(body, expected=packet.identity)
            body["current_identity"] = asdict(identity)
            body.pop("identity_handle", None)
            return base_dispatch_live_repair_request(state, method, raw_path, body)

        capture_parts = tuple(part for part in route.split("/") if part)
        if (
            method == "POST"
            and len(capture_parts) == 7
            and capture_parts[:4] == ("api", "showcase", "live-repair", "capture")
            and capture_parts[5] in {"event", "mark", "finalize"}
            and capture_parts[6] == "v1"
        ):
            capture_id = capture_parts[4]
            if state._identity_broker is not None:
                expected_identity = state.live_repair.capture_identity(capture_id)
                state.resolve_request_identity(body, expected=expected_identity)
                body.pop("identity_handle", None)
            else:
                state.live_repair.assert_current_capture_identity(capture_id)
            if capture_parts[5] == "finalize":
                _validate_required_asset_paths(body)
                body["arena_id"] = "construction"

    except (
        BilateralLiveRepairError,
        BilateralRuntimeProfileError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        return _error(str(exc), 409)
    except Exception:  # pylint: disable=broad-exception-caught
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
            except (TypeError, ValueError) as exc:
                raise BilateralLiveRepairError("Content-Length must be a valid integer") from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise BilateralLiveRepairError(f"request body must be between 0 and {MAX_BODY_BYTES} bytes")
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BilateralLiveRepairError("request body must be valid UTF-8 JSON") from exc
            if not isinstance(value, dict):
                raise BilateralLiveRepairError("request body must be a JSON object")
            return value

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route.startswith("/api/"):
                self._send(*dispatch_construction_foundry_request(state, "GET", self.path))
            else:
                self._send(*_static_response(route))

        def do_POST(self) -> None:
            try:
                payload = self._payload()
            except BilateralLiveRepairError as exc:
                self._send(*_error(str(exc), 400))
                return
            self._send(*dispatch_construction_foundry_request(state, "POST", self.path, payload))

        def log_message(  # pylint: disable=redefined-builtin
            self,
            format: str,
            *args: Any,
        ) -> None:
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
    construction_state_packet: str | Path | None = None,
    presentation_dissolution_packet: str | Path | None = None,
) -> None:
    provider = _identity_provider_from_path(trusted_identity_packet) if trusted_identity_packet else None
    state_provider = (
        _construction_state_digest_provider_from_path(construction_state_packet) if construction_state_packet else None
    )
    dissolution_provider = (
        _presentation_dissolution_provider_from_path(presentation_dissolution_packet)
        if presentation_dissolution_packet
        else None
    )
    state = ConstructionFoundryShowcaseState(
        repo_root,
        demo_project=demo_project,
        auto_start=auto_start,
        trusted_identity_provider=provider,
        construction_state_digest_provider=state_provider,
        presentation_dissolution_provider=dissolution_provider,
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
    parser.add_argument("--construction-state-packet", default="")
    parser.add_argument("--presentation-dissolution-packet", default="")
    parser.add_argument("--no-auto-start", action="store_true")
    args = parser.parse_args()
    serve(
        host=args.host,
        port=args.port,
        repo_root=args.repo_root,
        demo_project=args.demo_project,
        auto_start=not args.no_auto_start,
        trusted_identity_packet=args.trusted_identity_packet or None,
        construction_state_packet=args.construction_state_packet or None,
        presentation_dissolution_packet=args.presentation_dissolution_packet or None,
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
