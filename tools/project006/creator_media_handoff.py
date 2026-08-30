"""Governed Project006 Creator Studio media handoff with Higgsfield adapter.

This module is a sibling to the LLM provider handoff. It deliberately keeps
media generation separate because Higgsfield uses provider-specific create
routes, `Authorization: Key ...`, and asynchronous status polling.

The caller supplies only an Aura-owned logical media route plus already-issued
lease/currentness/spend witnesses. Provider URL/path and credential values are
resolved inside this provider-facing process and are never accepted from the
Arena command payload.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import os
import socket
import ssl
import sys
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlparse, urlunparse
import urllib.error
import urllib.request

HANDOFF_VERSION = "PROJECT006_CREATOR_MEDIA_HANDOFF_V1"
RECEIPT_VERSION = "PROJECT006_CREATOR_MEDIA_RECEIPT_V1"
HIGGSFIELD_BASE_URL = "https://platform.higgsfield.ai"
HIGGSFIELD_CREDENTIAL_ALIAS = "HIGGSFIELD_API_CREDENTIAL"

# Logical route refs are Aura-owned. The Arena never supplies a URL/path.
_ROUTE_TABLE: dict[str, tuple[str, str]] = {
    "higgsfield.qwen-image-3": ("image", "/alibaba/qwen-image-3/text-to-image"),
    "higgsfield.nano-banana-2-lite": ("image", "/nano-banana-2/lite/text-to-image"),
    "higgsfield.gpt-image-2": ("image", "/openai/gpt-image-2"),
    "higgsfield.minimax-h3": ("video", "/minimax/h3/text-to-video"),
    "higgsfield.ltx-2.5-pro": ("video", "/lightricks/ltx-2.5/text-to-video/pro"),
    "higgsfield.kling-3.0": ("video", "/kling-video/v3.0/std/text-to-video"),
    "higgsfield.veo-3.1-fast": ("video", "/veo3.1/fast/text-to-video"),
}

_REQUIRED_FIELDS = frozenset(
    {
        "handoff_version",
        "root_dispatch_id",
        "dispatch_generation",
        "intent_digest",
        "validation_receipt_ref",
        "media_route_ref",
        "capsule_id",
        "lease_generation",
        "fencing_token",
        "currentness_ref",
        "spend_grant_ref",
        "prompt",
    }
)
_OPTIONAL_FIELDS = frozenset({"deadline_ms", "poll_initial_ms", "poll_max_ms"})
_MAX_PROMPT_CHARS = 20_000


class MediaStatus(str, Enum):
    OK = "OK"
    INVALID_REQUEST = "INVALID_REQUEST"
    NO_CREDENTIAL = "NO_CREDENTIAL"
    PROVIDER_REJECTED = "PROVIDER_REJECTED"
    TIMEOUT = "TIMEOUT"
    TLS_FAILURE = "TLS_FAILURE"
    REDIRECT_BLOCKED = "REDIRECT_BLOCKED"
    STATUS_URL_REJECTED = "STATUS_URL_REJECTED"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    PROVIDER_FAILED = "PROVIDER_FAILED"


class MediaHandoffError(ValueError):
    """Typed fail-closed media-handoff validation failure."""


class StatusUrlRejected(RuntimeError):
    """Provider returned a poll URL outside the pinned Higgsfield origin."""


class RedirectBlocked(RuntimeError):
    """HTTP redirect was attempted for a credential-bearing request."""


@dataclass(frozen=True)
class MediaRoute:
    route_ref: str
    media_kind: str
    create_path: str


@dataclass(frozen=True)
class MediaReceipt:
    receipt_version: str
    status: str
    root_dispatch_id: str
    dispatch_generation: int
    intent_digest: str
    validation_receipt_ref: str
    capsule_id: str
    lease_generation: int
    currentness_ref: str
    spend_grant_ref: str
    media_route_ref: str
    provider: str
    media_kind: str
    request_digest: str
    provider_request_id: str | None
    provider_terminal_status: str | None
    asset_url: str | None
    attempts: int

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_json(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _require_ref(name: str, value: Any, *, maximum: int = 512) -> str:
    if not isinstance(value, str):
        raise MediaHandoffError(f"INVALID_{name.upper()}")
    value = value.strip()
    if not value or len(value) > maximum or any(ord(ch) < 32 for ch in value):
        raise MediaHandoffError(f"INVALID_{name.upper()}")
    return value


def _require_digest(name: str, value: Any) -> str:
    value = _require_ref(name, value, maximum=64)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise MediaHandoffError(f"INVALID_{name.upper()}")
    return value


def _require_int(name: str, value: Any, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise MediaHandoffError(f"INVALID_{name.upper()}")
    if value < minimum or value > maximum:
        raise MediaHandoffError(f"INVALID_{name.upper()}")
    return value


def resolve_route(route_ref: Any) -> MediaRoute:
    ref = _require_ref("media_route_ref", route_ref, maximum=128).lower()
    if any(marker in ref for marker in ("://", "\\", "@")) or ref.count("/"):
        raise MediaHandoffError("INVALID_MEDIA_ROUTE_REF")
    entry = _ROUTE_TABLE.get(ref)
    if entry is None:
        raise MediaHandoffError("UNREGISTERED_MEDIA_ROUTE")
    media_kind, create_path = entry
    return MediaRoute(route_ref=ref, media_kind=media_kind, create_path=create_path)


def validate_handoff(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise MediaHandoffError("HANDOFF_NOT_OBJECT")
    keys = set(raw)
    missing = _REQUIRED_FIELDS - keys
    unknown = keys - (_REQUIRED_FIELDS | _OPTIONAL_FIELDS)
    if missing:
        raise MediaHandoffError("HANDOFF_MISSING_REQUIRED_FIELD")
    if unknown:
        # Prevent endpoint/api-key/model/provider injection from the Arena.
        raise MediaHandoffError("HANDOFF_UNKNOWN_FIELD")
    if raw.get("handoff_version") != HANDOFF_VERSION:
        raise MediaHandoffError("UNSUPPORTED_HANDOFF_VERSION")

    route = resolve_route(raw["media_route_ref"])
    prompt = _require_ref("prompt", raw["prompt"], maximum=_MAX_PROMPT_CHARS)
    return {
        "handoff_version": HANDOFF_VERSION,
        "root_dispatch_id": _require_ref("root_dispatch_id", raw["root_dispatch_id"]),
        "dispatch_generation": _require_int(
            "dispatch_generation", raw["dispatch_generation"], minimum=0, maximum=2**53 - 1
        ),
        "intent_digest": _require_digest("intent_digest", raw["intent_digest"]),
        "validation_receipt_ref": _require_ref(
            "validation_receipt_ref", raw["validation_receipt_ref"]
        ),
        "media_route_ref": route.route_ref,
        "media_kind": route.media_kind,
        "create_path": route.create_path,
        "capsule_id": _require_ref("capsule_id", raw["capsule_id"]),
        "lease_generation": _require_int(
            "lease_generation", raw["lease_generation"], minimum=0, maximum=2**53 - 1
        ),
        # Required for attempt identity, but never emitted.
        "fencing_token": _require_ref("fencing_token", raw["fencing_token"], maximum=1024),
        "currentness_ref": _require_ref("currentness_ref", raw["currentness_ref"]),
        # Semantic validity is owned upstream; presence is required here so paid
        # media cannot bypass the existing human spend gate by omission.
        "spend_grant_ref": _require_ref("spend_grant_ref", raw["spend_grant_ref"]),
        "prompt": prompt,
        "deadline_ms": _require_int(
            "deadline_ms", raw.get("deadline_ms", 180_000), minimum=1_000, maximum=900_000
        ),
        "poll_initial_ms": _require_int(
            "poll_initial_ms", raw.get("poll_initial_ms", 2_000), minimum=100, maximum=30_000
        ),
        "poll_max_ms": _require_int(
            "poll_max_ms", raw.get("poll_max_ms", 10_000), minimum=100, maximum=60_000
        ),
    }


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class HiggsfieldTransport:
    """Strict JSON create/poll transport pinned to Higgsfield's API origin."""

    def __init__(self, *, opener: Any | None = None, max_response_bytes: int = 4 * 1024 * 1024) -> None:
        self._opener = opener or urllib.request.build_opener(_NoRedirectHandler())
        self.max_response_bytes = int(max_response_bytes)

    def _json_request(
        self,
        *,
        method: str,
        url: str,
        credential: str,
        payload: Mapping[str, Any] | None,
        timeout: float,
    ) -> Mapping[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme.lower() != "https" or parsed.hostname != "platform.higgsfield.ai":
            raise StatusUrlRejected("Higgsfield URL escaped the pinned provider origin")
        data = None if payload is None else json.dumps(dict(payload)).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Key {credential}",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=timeout) as response:
                content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
                if content_type and not (content_type == "application/json" or content_type.endswith("+json")):
                    raise ValueError("provider response must be JSON")
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise ValueError("provider response too large")
        except urllib.error.HTTPError as exc:
            if 300 <= int(exc.code) < 400:
                raise RedirectBlocked("credential-bearing redirect blocked") from exc
            raise
        except ssl.SSLError:
            raise
        decoded = json.loads(raw.decode("utf-8"))
        if not isinstance(decoded, Mapping):
            raise ValueError("provider response must be a JSON object")
        return decoded

    def create(self, path: str, *, credential: str, prompt: str, timeout: float) -> Mapping[str, Any]:
        return self._json_request(
            method="POST",
            url=HIGGSFIELD_BASE_URL + path,
            credential=credential,
            payload={"prompt": prompt},
            timeout=timeout,
        )

    def poll(self, status_url: str, *, credential: str, timeout: float) -> Mapping[str, Any]:
        # Validate the absolute URL, then reconstruct from the pinned origin. This
        # prevents a provider-controlled status_url from exfiltrating credentials.
        parsed = urlparse(str(status_url or ""))
        if parsed.scheme.lower() != "https" or parsed.hostname != "platform.higgsfield.ai":
            raise StatusUrlRejected("status_url escaped the pinned Higgsfield origin")
        safe_url = urlunparse(("https", "platform.higgsfield.ai", parsed.path, "", parsed.query, ""))
        return self._json_request(
            method="GET",
            url=safe_url,
            credential=credential,
            payload=None,
            timeout=timeout,
        )


CredentialResolver = Callable[[], str | None]
_TERMINAL = frozenset({"completed", "failed", "nsfw", "canceled"})


def _default_credential_resolver() -> str | None:
    # Project-006/NONO may inject this alias into the provider-facing process.
    # The raw value is never logged or serialized by this module.
    value = os.environ.get(HIGGSFIELD_CREDENTIAL_ALIAS)
    if not value:
        return None
    value = value.strip()
    if ":" not in value:
        return None
    key_id, secret = value.split(":", 1)
    if not key_id.strip() or not secret.strip():
        return None
    return value


def _asset_url(result: Mapping[str, Any], media_kind: str) -> str | None:
    if media_kind == "image":
        images = result.get("images")
        if isinstance(images, list) and images and isinstance(images[0], Mapping):
            url = images[0].get("url")
            return str(url) if isinstance(url, str) and url else None
    video = result.get("video")
    if isinstance(video, Mapping):
        url = video.get("url")
        return str(url) if isinstance(url, str) and url else None
    return None


def dispatch_media_handoff(
    raw: Mapping[str, Any],
    *,
    credential_resolver: CredentialResolver = _default_credential_resolver,
    transport: HiggsfieldTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    handoff = validate_handoff(raw)
    credential = credential_resolver()
    if not credential:
        return MediaReceipt(
            receipt_version=RECEIPT_VERSION,
            status=MediaStatus.NO_CREDENTIAL.value,
            root_dispatch_id=handoff["root_dispatch_id"],
            dispatch_generation=handoff["dispatch_generation"],
            intent_digest=handoff["intent_digest"],
            validation_receipt_ref=handoff["validation_receipt_ref"],
            capsule_id=handoff["capsule_id"],
            lease_generation=handoff["lease_generation"],
            currentness_ref=handoff["currentness_ref"],
            spend_grant_ref=handoff["spend_grant_ref"],
            media_route_ref=handoff["media_route_ref"],
            provider="higgsfield",
            media_kind=handoff["media_kind"],
            request_digest=_sha256_json({k: v for k, v in handoff.items() if k != "fencing_token"}),
            provider_request_id=None,
            provider_terminal_status=None,
            asset_url=None,
            attempts=0,
        ).to_jsonable()

    tx = transport or HiggsfieldTransport()
    request_digest = _sha256_json({
        "root_dispatch_id": handoff["root_dispatch_id"],
        "dispatch_generation": handoff["dispatch_generation"],
        "intent_digest": handoff["intent_digest"],
        "capsule_id": handoff["capsule_id"],
        "lease_generation": handoff["lease_generation"],
        "fencing_token_digest": hashlib.sha256(handoff["fencing_token"].encode("utf-8")).hexdigest(),
        "currentness_ref": handoff["currentness_ref"],
        "spend_grant_ref": handoff["spend_grant_ref"],
        "media_route_ref": handoff["media_route_ref"],
        "prompt": handoff["prompt"],
    })
    deadline = monotonic() + handoff["deadline_ms"] / 1000.0
    attempts = 0
    try:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise socket.timeout("deadline reached")
        job = tx.create(
            handoff["create_path"],
            credential=credential,
            prompt=handoff["prompt"],
            timeout=min(60.0, remaining),
        )
        attempts += 1
        request_id = _require_ref("provider_request_id", job.get("request_id"), maximum=512)
        status_url = _require_ref("status_url", job.get("status_url"), maximum=4096)
        delay_ms = handoff["poll_initial_ms"]
        result: Mapping[str, Any] | None = None
        terminal_status: str | None = None
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise socket.timeout("media generation deadline reached")
            sleep(min(delay_ms / 1000.0, remaining))
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise socket.timeout("media generation deadline reached")
            result = tx.poll(status_url, credential=credential, timeout=min(30.0, remaining))
            attempts += 1
            status = str(result.get("status") or "").strip().lower()
            if not status:
                raise ValueError("provider status missing")
            if status in _TERMINAL:
                terminal_status = status
                break
            delay_ms = min(int(delay_ms * 1.5), handoff["poll_max_ms"])

        if terminal_status != "completed":
            status = MediaStatus.PROVIDER_FAILED.value
            asset_url = None
        else:
            asset_url = _asset_url(result or {}, handoff["media_kind"])
            if not asset_url:
                raise ValueError("completed provider response omitted media asset")
            status = MediaStatus.OK.value
        return MediaReceipt(
            receipt_version=RECEIPT_VERSION,
            status=status,
            root_dispatch_id=handoff["root_dispatch_id"],
            dispatch_generation=handoff["dispatch_generation"],
            intent_digest=handoff["intent_digest"],
            validation_receipt_ref=handoff["validation_receipt_ref"],
            capsule_id=handoff["capsule_id"],
            lease_generation=handoff["lease_generation"],
            currentness_ref=handoff["currentness_ref"],
            spend_grant_ref=handoff["spend_grant_ref"],
            media_route_ref=handoff["media_route_ref"],
            provider="higgsfield",
            media_kind=handoff["media_kind"],
            request_digest=request_digest,
            provider_request_id=request_id,
            provider_terminal_status=terminal_status,
            asset_url=asset_url,
            attempts=attempts,
        ).to_jsonable()
    except StatusUrlRejected:
        status = MediaStatus.STATUS_URL_REJECTED.value
    except RedirectBlocked:
        status = MediaStatus.REDIRECT_BLOCKED.value
    except ssl.SSLError:
        status = MediaStatus.TLS_FAILURE.value
    except (socket.timeout, TimeoutError):
        status = MediaStatus.TIMEOUT.value
    except urllib.error.HTTPError:
        status = MediaStatus.PROVIDER_REJECTED.value
    except Exception:
        # Never serialize exception text; it may contain provider or credential data.
        status = MediaStatus.MALFORMED_RESPONSE.value

    return MediaReceipt(
        receipt_version=RECEIPT_VERSION,
        status=status,
        root_dispatch_id=handoff["root_dispatch_id"],
        dispatch_generation=handoff["dispatch_generation"],
        intent_digest=handoff["intent_digest"],
        validation_receipt_ref=handoff["validation_receipt_ref"],
        capsule_id=handoff["capsule_id"],
        lease_generation=handoff["lease_generation"],
        currentness_ref=handoff["currentness_ref"],
        spend_grant_ref=handoff["spend_grant_ref"],
        media_route_ref=handoff["media_route_ref"],
        provider="higgsfield",
        media_kind=handoff["media_kind"],
        request_digest=request_digest,
        provider_request_id=None,
        provider_terminal_status=None,
        asset_url=None,
        attempts=attempts,
    ).to_jsonable()


def main() -> int:
    try:
        raw = json.load(sys.stdin)
        receipt = dispatch_media_handoff(raw)
    except MediaHandoffError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    except Exception:
        print(json.dumps({"ok": False, "error": "CREATOR_MEDIA_HANDOFF_INTERNAL_FAILURE"}, sort_keys=True))
        return 3
    ok = receipt["status"] == MediaStatus.OK.value
    print(json.dumps({"ok": ok, "receipt": receipt}, sort_keys=True))
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
