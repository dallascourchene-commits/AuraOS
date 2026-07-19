"""Bounded HTTP/API and browser surface for Aura S3-B spatial projection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
from pathlib import Path
import re
import threading
from typing import Any
from urllib.parse import urlparse

from aura_event_contracts import canonical_json
from aura_source_integrity import SourceIntegrityError, read_utf8_source
from aura_spatial_contracts import (
    PATCH_AUTHORITY,
    SpatialDeviceProfile,
    SpatialRenderEvidenceClass,
    SpatialRenderOutcome,
    SpatialRenderPlan,
    SpatialSceneSnapshot,
)
from aura_spatial_interaction import compile_spatial_interaction
from aura_spatial_render_plan import (
    negotiate_spatial_render_plan,
    validate_spatial_device_profile_payload,
)
from aura_spatial_scene import validate_spatial_scene_payload
from aura_spatial_session import SpatialProjectionSessionManager

SPATIAL_SERVER_VERSION = "AURA_SPATIAL_SERVER_V1"
MAX_SPATIAL_HTTP_BODY_BYTES = 1_048_576
MAX_SPATIAL_HTTP_RESPONSE_BYTES = 4_194_304
MAX_STORED_SPATIAL_SCENES = 64
MAX_STORED_DEVICE_PROFILES = 64
MAX_STORED_RENDER_PLANS = 128
MAX_SPATIAL_JSON_DEPTH = 32
MAX_SPATIAL_JSON_ITEMS = 32_768
MAX_SPATIAL_JSON_STRING_BYTES = 262_144
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")

SPATIAL_WEB_ROOT = Path(__file__).with_name("aura_spatial_web")
MAX_SPATIAL_WEB_ASSET_BYTES = 524_288
_SPATIAL_WEB_ASSETS = frozenset(
    {
        "index.html",
        "styles.css",
        "app.js",
        "bootstrap.js",
        "renderer_adapter.js",
        "headless_renderer.js",
        "scene_decoder.js",
        "accessibility.js",
        "webgl2_renderer.js",
        "webgpu_renderer.js",
        "webxr_session.js",
        "interaction_adapter.js",
        "telemetry.js",
    }
)
_SPATIAL_WEB_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


@dataclass(frozen=True)
class SpatialHTTPResponse:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> dict[str, Any]:
        value = json.loads(self.body.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("spatial response body is not an object")
        return value


class SpatialServerState:
    """In-memory scene/plan/session registry with no persistence or fetch authority."""

    def __init__(
        self,
        *,
        max_scenes: int = MAX_STORED_SPATIAL_SCENES,
        max_device_profiles: int = MAX_STORED_DEVICE_PROFILES,
        max_render_plans: int = MAX_STORED_RENDER_PLANS,
    ) -> None:
        self._max_scenes = _bounded_limit(max_scenes, "max_scenes", maximum=1024)
        self._max_device_profiles = _bounded_limit(
            max_device_profiles,
            "max_device_profiles",
            maximum=1024,
        )
        self._max_render_plans = _bounded_limit(
            max_render_plans,
            "max_render_plans",
            maximum=4096,
        )
        self.scenes: dict[str, SpatialSceneSnapshot] = {}
        self.devices_by_digest: dict[str, SpatialDeviceProfile] = {}
        self.plans: dict[str, SpatialRenderPlan] = {}
        self.sessions = SpatialProjectionSessionManager()
        self._lock = threading.RLock()

    def register_scene(self, scene: SpatialSceneSnapshot) -> None:
        if not isinstance(scene, SpatialSceneSnapshot):
            raise ValueError("scene must be a SpatialSceneSnapshot")
        _required_id(scene.scene_id, "scene.scene_id")
        with self._lock:
            existing = self.scenes.get(scene.scene_id)
            if existing is not None:
                if existing.scene_digest != scene.scene_digest:
                    raise ValueError("scene_id already exists with a different digest")
                return
            if len(self.scenes) >= self._max_scenes:
                raise ValueError("stored spatial scene ceiling reached")
            self.scenes[scene.scene_id] = scene

    def register_device(self, device: SpatialDeviceProfile) -> None:
        if not isinstance(device, SpatialDeviceProfile):
            raise ValueError("device must be a SpatialDeviceProfile")
        with self._lock:
            digest = device.device_profile_digest
            if digest in self.devices_by_digest:
                return
            if len(self.devices_by_digest) >= self._max_device_profiles:
                raise ValueError("stored device profile ceiling reached")
            self.devices_by_digest[digest] = device

    def register_plan(self, plan: SpatialRenderPlan) -> None:
        if not isinstance(plan, SpatialRenderPlan):
            raise ValueError("plan must be a SpatialRenderPlan")
        _required_id(plan.plan_id, "render_plan.plan_id")
        with self._lock:
            existing = self.plans.get(plan.plan_id)
            if existing is not None:
                if existing.render_plan_digest != plan.render_plan_digest:
                    raise ValueError("plan_id already exists with a different digest")
                return
            if len(self.plans) >= self._max_render_plans:
                raise ValueError("stored render plan ceiling reached")
            self.plans[plan.plan_id] = plan

    def close(self) -> tuple[Any, ...]:
        return self.sessions.close()


def dispatch_spatial_request(
    state: SpatialServerState,
    method: str,
    raw_path: str,
    body: Mapping[str, Any] | None = None,
) -> SpatialHTTPResponse:
    if not isinstance(state, SpatialServerState):
        raise ValueError("state must be a SpatialServerState")
    verb = str(method or "").upper()
    if verb not in {"GET", "POST"}:
        return _error(405, "METHOD_NOT_ALLOWED", "only GET and POST are admitted")
    parsed = urlparse(str(raw_path or ""))
    if parsed.scheme or parsed.netloc:
        return _error(400, "NONCANONICAL_ROUTE", "absolute request targets are prohibited")
    if parsed.query or parsed.fragment or parsed.params:
        return _error(400, "NONCANONICAL_ROUTE", "query, fragment, and params are prohibited")
    route = parsed.path
    if body is not None and not isinstance(body, Mapping):
        return _error(400, "INVALID_SPATIAL_REQUEST", "request body must be an object")
    supplied = dict(body or {})
    try:
        _bound_payload(supplied)
        if verb == "GET" and supplied:
            raise ValueError("GET requests cannot include a spatial request body")
        if verb == "GET" and (route == "/spatial" or route == "/spatial/"):
            return _spatial_web_response("index.html")
        if verb == "GET" and route.startswith("/spatial/"):
            asset_name = route[len("/spatial/") :]
            if not asset_name or "/" in asset_name or "\\" in asset_name:
                return _error(404, "SPATIAL_WEB_ASSET_NOT_FOUND", "unknown spatial browser asset")
            return _spatial_web_response(asset_name)

        if verb == "GET" and route == "/api/spatial/capabilities":
            try:
                browser_fixture_digest = _spatial_web_fixture_digest()
            except (OSError, SourceIntegrityError, ValueError) as exc:
                return _error(503, "SPATIAL_WEB_UNAVAILABLE", str(exc))
            return _json_response(
                200,
                {
                    "ok": True,
                    "version": SPATIAL_SERVER_VERSION,
                    "renderers": ["WEBXR", "WEBGPU", "WEBGL2", "ACCESSIBLE_2D", "HEADLESS"],
                    "actual_renderer_implementation": True,
                    "browser_fixture_digest": browser_fixture_digest,
                    "renderer_implementations": {
                        "WEBGL2": "ACTIVE",
                        "WEBGPU": "SHADOW_ONLY",
                        "WEBXR": "CAPABILITY_ONLY_EXPLICIT_GESTURE",
                        "ACCESSIBLE_2D": "ACTIVE",
                        "HEADLESS": "ACTIVE",
                    },
                    "webxr_requires_user_activation": True,
                    "accessible_2d_required": True,
                    "network_fetch": False,
                    "raw_sensor_data_retained": False,
                    "production_mutation": False,
                    "automatic_merge": False,
                    "renderer_authority": False,
                    "execution_authority": False,
                    "patch_authority": PATCH_AUTHORITY,
                    "human_review_required": True,
                    "session_status": state.sessions.status_packet(),
                },
            )

        if verb == "POST" and route == "/api/spatial/scenes":
            _exact_body_keys(supplied, {"scene"}, "scene request")
            scene_payload = supplied.get("scene")
            if not isinstance(scene_payload, Mapping):
                raise ValueError("scene must be an object")
            scene = validate_spatial_scene_payload(scene_payload)
            state.register_scene(scene)
            return _json_response(201, {"ok": True, "scene": scene.to_dict()})

        if verb == "GET" and route.startswith("/api/spatial/projections/"):
            session_id = _route_id(route, "/api/spatial/projections/")
            try:
                summary = state.sessions.get_summary(session_id)
                scene = state.sessions.get_scene(session_id)
                plan = state.sessions.get_plan(session_id)
            except KeyError:
                return _error(404, "SESSION_NOT_FOUND", "unknown or dissolved spatial session")
            return _json_response(
                200,
                {
                    "ok": True,
                    "session_id": session_id,
                    "session": summary.to_dict(),
                    "scene": scene.to_dict(),
                    "render_plan": plan.to_dict(),
                    "production_mutation": False,
                    "automatic_merge": False,
                    "human_review_required": True,
                },
            )

        if verb == "GET" and route.startswith("/api/spatial/scenes/"):
            scene_id = _route_id(route, "/api/spatial/scenes/")
            scene = state.scenes.get(scene_id)
            if scene is None:
                return _error(404, "SCENE_NOT_FOUND", "unknown spatial scene")
            return _json_response(200, {"ok": True, "scene": scene.to_dict()})

        if verb == "POST" and route == "/api/spatial/render-plans":
            _exact_body_keys(
                supplied,
                {"scene_id", "device_profile", "preferred_renderers", "requested_budget", "allow_xr"},
                "render-plan request",
            )
            scene_id = _required_id(supplied.get("scene_id"), "scene_id")
            scene = state.scenes.get(scene_id)
            if scene is None:
                return _error(404, "SCENE_NOT_FOUND", "unknown spatial scene")
            profile_payload = supplied.get("device_profile")
            if not isinstance(profile_payload, Mapping):
                raise ValueError("device_profile must be an object")
            device = validate_spatial_device_profile_payload(profile_payload)
            preferred = supplied.get("preferred_renderers", ())
            if isinstance(preferred, (str, bytes, bytearray)) or not isinstance(preferred, Sequence):
                raise ValueError("preferred_renderers must be an array")
            requested_budget = supplied.get("requested_budget")
            if requested_budget is not None and not isinstance(requested_budget, Mapping):
                raise ValueError("requested_budget must be an object")
            allow_xr = supplied.get("allow_xr", False)
            if type(allow_xr) is not bool:
                raise ValueError("allow_xr must be a boolean")
            plan = negotiate_spatial_render_plan(
                scene,
                device,
                preferred_renderers=tuple(preferred),
                requested_budget=requested_budget,
                allow_xr=allow_xr,
            )
            state.register_device(device)
            state.register_plan(plan)
            return _json_response(201, {"ok": True, "render_plan": plan.to_dict()})

        if verb == "POST" and route == "/api/spatial/sessions":
            _exact_body_keys(supplied, {"scene_id", "plan_id"}, "session request")
            scene_id = _required_id(supplied.get("scene_id"), "scene_id")
            plan_id = _required_id(supplied.get("plan_id"), "plan_id")
            scene = state.scenes.get(scene_id)
            plan = state.plans.get(plan_id)
            if scene is None:
                return _error(404, "SCENE_NOT_FOUND", "unknown spatial scene")
            if plan is None:
                return _error(404, "PLAN_NOT_FOUND", "unknown spatial render plan")
            device = state.devices_by_digest.get(plan.device_profile_digest)
            if device is None:
                return _error(409, "DEVICE_PROFILE_MISSING", "render plan device profile is unavailable")
            summary = state.sessions.create_session(scene, plan, device)
            return _json_response(201, {"ok": True, "session": summary.to_dict()})

        if verb == "GET" and route.startswith("/api/spatial/sessions/"):
            session_id = _route_id(route, "/api/spatial/sessions/")
            try:
                summary = state.sessions.get_summary(session_id)
            except KeyError:
                return _error(404, "SESSION_NOT_FOUND", "unknown or dissolved spatial session")
            return _json_response(200, {"ok": True, "session": summary.to_dict()})

        if verb == "POST" and route == "/api/spatial/telemetry":
            _exact_body_keys(supplied, {"session_id", "packet"}, "telemetry request")
            session_id = _required_id(supplied.get("session_id"), "session_id")
            packet = supplied.get("packet")
            if not isinstance(packet, Mapping):
                raise ValueError("packet must be an object")
            try:
                receipt, summary = state.sessions.record_browser_telemetry(
                    session_id,
                    packet,
                )
            except KeyError:
                return _error(404, "SESSION_NOT_FOUND", "unknown or dissolved spatial session")
            return _json_response(
                200,
                {
                    "ok": True,
                    "render_receipt": receipt.to_dict(),
                    "session": summary.to_dict(),
                    "execution_performed": False,
                    "human_review_required": True,
                },
            )

        if verb == "POST" and route == "/api/spatial/interactions":
            _exact_body_keys(
                supplied,
                {"session_id", "action", "target_entity_ids", "actor_ref", "metadata"},
                "interaction request",
            )
            session_id = _required_id(supplied.get("session_id"), "session_id")
            try:
                scene = state.sessions.get_scene(session_id)
            except KeyError:
                return _error(404, "SESSION_NOT_FOUND", "unknown or dissolved spatial session")
            targets = supplied.get("target_entity_ids", ())
            if isinstance(targets, (str, bytes, bytearray)) or not isinstance(targets, Sequence):
                raise ValueError("target_entity_ids must be an array")
            metadata = supplied.get("metadata")
            if metadata is not None and not isinstance(metadata, Mapping):
                raise ValueError("metadata must be an object")
            intent = compile_spatial_interaction(
                scene,
                action=supplied.get("action"),
                target_entity_ids=tuple(targets),
                actor_ref=str(supplied.get("actor_ref") or "human:local"),
                metadata=dict(metadata or {}),
            )
            return _json_response(
                200,
                {
                    "ok": True,
                    "session_id": session_id,
                    "intent": intent.to_dict(),
                    "execution_performed": False,
                    "human_review_required": True,
                },
            )

        render_match = re.fullmatch(r"/api/spatial/sessions/(.+)/renders", route)
        if verb == "POST" and render_match:
            _exact_body_keys(
                supplied,
                {"outcome", "evidence_class", "metrics", "renderer_disposed"},
                "render receipt request",
            )
            session_id = _route_identifier(render_match.group(1), "session_id")
            try:
                receipt, summary = state.sessions.record_render(
                    session_id,
                    outcome=SpatialRenderOutcome(str(supplied.get("outcome"))),
                    evidence_class=SpatialRenderEvidenceClass(str(supplied.get("evidence_class"))),
                    metrics=(
                        dict(supplied.get("metrics") or {})
                        if isinstance(supplied.get("metrics") or {}, Mapping)
                        else _raise("metrics must be an object")
                    ),
                    renderer_disposed=supplied.get("renderer_disposed", False),
                )
            except KeyError:
                return _error(404, "SESSION_NOT_FOUND", "unknown or dissolved spatial session")
            return _json_response(
                200,
                {
                    "ok": True,
                    "render_receipt": receipt.to_dict(),
                    "session": summary.to_dict(),
                },
            )

        cancel_match = re.fullmatch(r"/api/spatial/sessions/(.+)/cancel", route)
        if verb == "POST" and cancel_match:
            _exact_body_keys(supplied, {"reason"}, "cancel request")
            session_id = _route_identifier(cancel_match.group(1), "session_id")
            try:
                summary = state.sessions.cancel_session(
                    session_id,
                    reason=str(supplied.get("reason") or "USER_CANCELLED"),
                )
            except KeyError:
                return _error(404, "SESSION_NOT_FOUND", "unknown or dissolved spatial session")
            return _json_response(200, {"ok": True, "session": summary.to_dict()})

        dissolve_match = re.fullmatch(r"/api/spatial/sessions/(.+)/dissolve", route)
        if verb == "POST" and dissolve_match:
            _exact_body_keys(supplied, {"reason_code"}, "dissolve request")
            session_id = _route_identifier(dissolve_match.group(1), "session_id")
            try:
                receipt = state.sessions.dissolve_session(
                    session_id,
                    reason_code=str(supplied.get("reason_code") or "SESSION_COMPLETE"),
                )
            except KeyError:
                return _error(404, "SESSION_NOT_FOUND", "unknown or dissolved spatial session")
            return _json_response(
                200,
                {
                    "ok": True,
                    "dissolution_receipt": receipt.to_dict(),
                    "session_active": False,
                },
            )
    except (TypeError, ValueError) as exc:
        return _error(400, "INVALID_SPATIAL_REQUEST", str(exc))

    return _error(404, "SPATIAL_ROUTE_NOT_FOUND", "unknown spatial API route")


def make_spatial_handler(state: SpatialServerState):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, response: SpatialHTTPResponse) -> None:
            self.send_response(response.status)
            for name, value in response.headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def _payload(self) -> Mapping[str, Any]:
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Transfer-Encoding is not admitted")
            raw_length = self.headers.get("Content-Length", "0") or "0"
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("Content-Length must be an integer") from exc
            if length < 0 or length > MAX_SPATIAL_HTTP_BODY_BYTES:
                raise ValueError("spatial request body exceeds the byte ceiling")
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
                raise ValueError("spatial request body must be bounded UTF-8 JSON") from exc
            if not isinstance(value, Mapping):
                raise ValueError("spatial request body must be an object")
            return value

        def do_GET(self) -> None:
            self._send(dispatch_spatial_request(state, "GET", self.path))

        def do_POST(self) -> None:
            try:
                payload = self._payload()
            except ValueError as exc:
                self._send(_error(413, "INVALID_HTTP_BODY", str(exc)))
                return
            self._send(dispatch_spatial_request(state, "POST", self.path, payload))

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def serve_spatial(
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
    state: SpatialServerState | None = None,
) -> None:
    server_state = state or SpatialServerState()
    server = HTTPServer((host, port), make_spatial_handler(server_state))
    try:
        server.serve_forever()
    finally:
        server_state.close()
        server.server_close()


def _bound_payload(value: Mapping[str, Any]) -> None:
    _preflight_json_shape(value)
    try:
        encoded = canonical_json(value).encode("utf-8")
    except (RecursionError, TypeError, ValueError) as exc:
        raise ValueError("spatial request body is not canonical JSON") from exc
    if len(encoded) > MAX_SPATIAL_HTTP_BODY_BYTES:
        raise ValueError("spatial request body exceeds the byte ceiling")


def _preflight_json_shape(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    item_count = 0
    string_bytes = 0
    while stack:
        current, depth = stack.pop()
        if depth > MAX_SPATIAL_JSON_DEPTH:
            raise ValueError("spatial request body exceeds the nesting ceiling")
        item_count += 1
        if item_count > MAX_SPATIAL_JSON_ITEMS:
            raise ValueError("spatial request body exceeds the item ceiling")
        if isinstance(current, Mapping):
            for key, item in current.items():
                if not isinstance(key, str):
                    raise ValueError("spatial request object keys must be strings")
                string_bytes += len(key.encode("utf-8"))
                stack.append((item, depth + 1))
        elif isinstance(current, Sequence) and not isinstance(
            current,
            (str, bytes, bytearray),
        ):
            stack.extend((item, depth + 1) for item in current)
        elif isinstance(current, str):
            string_bytes += len(current.encode("utf-8"))
        elif current is None or type(current) in {bool, int}:
            pass
        elif isinstance(current, float):
            if not math.isfinite(current):
                raise ValueError("spatial request numbers must be finite")
        else:
            raise ValueError("spatial request body contains a non-JSON value")
        if string_bytes > MAX_SPATIAL_JSON_STRING_BYTES:
            raise ValueError("spatial request strings exceed the byte ceiling")


def _spatial_web_response(asset_name: str) -> SpatialHTTPResponse:
    if asset_name not in _SPATIAL_WEB_ASSETS:
        return _error(404, "SPATIAL_WEB_ASSET_NOT_FOUND", "unknown spatial browser asset")
    candidate = SPATIAL_WEB_ROOT / asset_name
    try:
        body = read_utf8_source(
            candidate,
            maximum_bytes=MAX_SPATIAL_WEB_ASSET_BYTES,
        ).encode("utf-8")
    except (OSError, SourceIntegrityError) as exc:
        return _error(404, "SPATIAL_WEB_ASSET_NOT_FOUND", str(exc))
    content_type = _SPATIAL_WEB_CONTENT_TYPES.get(candidate.suffix)
    if content_type is None:
        return _error(415, "SPATIAL_WEB_ASSET_TYPE", "unsupported browser asset type")
    headers = {
        "Content-Type": content_type,
        "Cache-Control": "no-store, max-age=0",
        "Content-Security-Policy": (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        ),
        "Cross-Origin-Resource-Policy": "same-origin",
        "Permissions-Policy": ("camera=(), microphone=(), geolocation=(), xr-spatial-tracking=(self)"),
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }
    return SpatialHTTPResponse(status=200, headers=headers, body=body)


def _spatial_web_fixture_digest() -> str:
    hasher = hashlib.sha256()
    for asset_name in sorted(_SPATIAL_WEB_ASSETS):
        candidate = SPATIAL_WEB_ROOT / asset_name
        source = read_utf8_source(
            candidate,
            maximum_bytes=MAX_SPATIAL_WEB_ASSET_BYTES,
        ).encode("utf-8")
        name_bytes = asset_name.encode("utf-8")
        hasher.update(len(name_bytes).to_bytes(8, "big"))
        hasher.update(name_bytes)
        hasher.update(len(source).to_bytes(8, "big"))
        hasher.update(source)
    return hasher.hexdigest()


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store, max-age=0",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), xr-spatial-tracking=()",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }


def _json_response(status: int, value: Mapping[str, Any]) -> SpatialHTTPResponse:
    body = canonical_json(dict(value)).encode("utf-8")
    if len(body) > MAX_SPATIAL_HTTP_RESPONSE_BYTES:
        return _error(507, "SPATIAL_RESPONSE_TOO_LARGE", "spatial response exceeds its byte ceiling")
    return SpatialHTTPResponse(status=status, headers=_headers(), body=body)


def _error(status: int, code: str, message: str) -> SpatialHTTPResponse:
    body = canonical_json(
        {
            "ok": False,
            "code": code,
            "error": str(message)[:2048],
            "production_mutation": False,
            "automatic_merge": False,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
        }
    ).encode("utf-8")
    return SpatialHTTPResponse(status=status, headers=_headers(), body=body)


def _route_id(route: str, prefix: str) -> str:
    return _route_identifier(route[len(prefix) :], "route identifier")


def _route_identifier(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if "/" in text or "\\" in text:
        raise ValueError(f"{field_name} must be one canonical path segment")
    return _required_id(text, field_name)


def _exact_body_keys(value: Mapping[str, Any], allowed: set[str], label: str) -> None:
    extra = set(value) - allowed
    if extra:
        raise ValueError(f"{label} contains unsupported keys: {sorted(extra)}")


def _bounded_limit(value: Any, field_name: str, *, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{field_name} must be an integer in 1..{maximum}")
    return value


def _required_id(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not _ID.fullmatch(text):
        raise ValueError(f"{field_name} contains unsupported characters")
    return text


def _raise(message: str):
    raise ValueError(message)


__all__ = [
    "MAX_SPATIAL_HTTP_BODY_BYTES",
    "MAX_SPATIAL_HTTP_RESPONSE_BYTES",
    "MAX_SPATIAL_WEB_ASSET_BYTES",
    "MAX_STORED_DEVICE_PROFILES",
    "MAX_STORED_RENDER_PLANS",
    "MAX_STORED_SPATIAL_SCENES",
    "SPATIAL_SERVER_VERSION",
    "SPATIAL_WEB_ROOT",
    "SpatialHTTPResponse",
    "SpatialServerState",
    "dispatch_spatial_request",
    "make_spatial_handler",
    "serve_spatial",
]
