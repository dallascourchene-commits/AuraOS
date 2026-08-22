"""Governed Project006 WP06/WP05 -> WP04 provider handoff seam.

This is the narrow executable seam immediately in front of the reviewed
``ProviderSidecarReference``.  It does not assign workers, mint leases/fences,
resolve Drive messages, or decide that work is authorized.  The caller must
supply a pre-validated dispatch handoff carrying the existing WP05 dispatch
identity and WP06 lease/fence/currentness witnesses.

The module is deliberately runnable as a one-request JSON stdin/stdout process
so the local Aura bridge/Resident can invoke the provider-facing membrane
without giving the network-incapable Resident credentials or arbitrary URLs.
"""
from __future__ import annotations

import hashlib
import json
import sys
from typing import Any, Mapping, Sequence

from aura_api_rotator import load_secrets, provider_key_pool
from tools.project006.provider_sidecar_reference.provider_sidecar import (
    DispatchBinding,
    ProviderSidecarReference,
    SidecarStatus,
)

HANDOFF_VERSION = "PROJECT006_PROVIDER_HANDOFF_V1"
RECEIPT_VERSION = "PROJECT006_PROVIDER_HANDOFF_RECEIPT_V1"

_REQUIRED_FIELDS = frozenset(
    {
        "handoff_version",
        "root_dispatch_id",
        "dispatch_generation",
        "intent_digest",
        "validation_receipt_ref",
        "route_ref",
        "capsule_id",
        "lease_generation",
        "fencing_token",
        "currentness_ref",
        "messages",
    }
)
_OPTIONAL_FIELDS = frozenset(
    {"max_tokens", "temperature_milli", "deadline_ms", "retry_budget"}
)
_ALLOWED_ROLES = frozenset({"system", "user", "assistant"})
_MAX_MESSAGES = 64
_MAX_MESSAGE_CHARS = 128_000
_MAX_TOTAL_MESSAGE_CHARS = 512_000


class HandoffError(ValueError):
    """Typed fail-closed handoff validation failure."""


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
        raise HandoffError(f"INVALID_{name.upper()}")
    value = value.strip()
    if not value or len(value) > maximum or any(ord(ch) < 32 for ch in value):
        raise HandoffError(f"INVALID_{name.upper()}")
    return value


def _require_digest(name: str, value: Any) -> str:
    value = _require_ref(name, value, maximum=64)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise HandoffError(f"INVALID_{name.upper()}")
    return value


def _require_int(name: str, value: Any, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise HandoffError(f"INVALID_{name.upper()}")
    if value < minimum or value > maximum:
        raise HandoffError(f"INVALID_{name.upper()}")
    return value


def _validate_messages(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value or len(value) > _MAX_MESSAGES:
        raise HandoffError("INVALID_MESSAGES")
    out: list[dict[str, str]] = []
    total = 0
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"role", "content"}:
            raise HandoffError("INVALID_MESSAGE_SHAPE")
        role = str(item.get("role") or "").strip().lower()
        content = item.get("content")
        if role not in _ALLOWED_ROLES or not isinstance(content, str):
            raise HandoffError("INVALID_MESSAGE_VALUE")
        if not content or len(content) > _MAX_MESSAGE_CHARS:
            raise HandoffError("INVALID_MESSAGE_VALUE")
        total += len(content)
        if total > _MAX_TOTAL_MESSAGE_CHARS:
            raise HandoffError("MESSAGES_TOO_LARGE")
        out.append({"role": role, "content": content})
    return out


def validate_handoff(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact scheduler-to-provider handoff shape.

    Network destinations and credentials are impossible at this boundary because
    unknown top-level fields fail closed and the provider sidecar accepts only a
    logical ``route_ref``.
    """
    if not isinstance(raw, Mapping):
        raise HandoffError("HANDOFF_NOT_OBJECT")
    keys = set(raw)
    missing = _REQUIRED_FIELDS - keys
    unknown = keys - (_REQUIRED_FIELDS | _OPTIONAL_FIELDS)
    if missing:
        raise HandoffError("HANDOFF_MISSING_REQUIRED_FIELD")
    if unknown:
        raise HandoffError("HANDOFF_UNKNOWN_FIELD")
    if raw.get("handoff_version") != HANDOFF_VERSION:
        raise HandoffError("UNSUPPORTED_HANDOFF_VERSION")

    root_dispatch_id = _require_ref("root_dispatch_id", raw["root_dispatch_id"])
    dispatch_generation = _require_int(
        "dispatch_generation", raw["dispatch_generation"], minimum=0, maximum=2**53 - 1
    )
    intent_digest = _require_digest("intent_digest", raw["intent_digest"])
    validation_receipt_ref = _require_ref(
        "validation_receipt_ref", raw["validation_receipt_ref"]
    )
    route_ref = ProviderSidecarReference.validate_route_ref(str(raw["route_ref"]))
    capsule_id = _require_ref("capsule_id", raw["capsule_id"])
    lease_generation = _require_int(
        "lease_generation", raw["lease_generation"], minimum=0, maximum=2**53 - 1
    )
    fencing_token = _require_ref("fencing_token", raw["fencing_token"], maximum=1024)
    currentness_ref = _require_ref("currentness_ref", raw["currentness_ref"])
    messages = _validate_messages(raw["messages"])

    max_tokens = _require_int(
        "max_tokens", raw.get("max_tokens", 900), minimum=1, maximum=16_000
    )
    temperature_milli = _require_int(
        "temperature_milli", raw.get("temperature_milli", 0), minimum=0, maximum=2_000
    )
    deadline_ms = _require_int(
        "deadline_ms", raw.get("deadline_ms", 60_000), minimum=1, maximum=300_000
    )
    retry_budget = _require_int(
        "retry_budget", raw.get("retry_budget", 1), minimum=0, maximum=3
    )

    return {
        "handoff_version": HANDOFF_VERSION,
        "root_dispatch_id": root_dispatch_id,
        "dispatch_generation": dispatch_generation,
        "intent_digest": intent_digest,
        "validation_receipt_ref": validation_receipt_ref,
        "route_ref": route_ref,
        "capsule_id": capsule_id,
        "lease_generation": lease_generation,
        "fencing_token": fencing_token,
        "currentness_ref": currentness_ref,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature_milli": temperature_milli,
        "deadline_ms": deadline_ms,
        "retry_budget": retry_budget,
    }


def dispatch_handoff(
    raw: Mapping[str, Any],
    *,
    sidecar: ProviderSidecarReference,
) -> dict[str, Any]:
    """Execute one already-authorized, already-leased provider handoff."""
    handoff = validate_handoff(raw)
    # The private fencing token participates in both the handoff digest and the
    # provider attempt binding but is never emitted in the receipt.
    handoff_digest = _sha256_json(handoff)
    binding = DispatchBinding(
        capsule_id=handoff["capsule_id"],
        lease_generation=handoff["lease_generation"],
        fencing_token=handoff["fencing_token"],
        currentness_ref=handoff["currentness_ref"],
    )
    result = sidecar.dispatch(
        route_ref=handoff["route_ref"],
        binding=binding,
        messages=handoff["messages"],
        max_tokens=handoff["max_tokens"],
        temperature=handoff["temperature_milli"] / 1000.0,
        total_deadline_sec=handoff["deadline_ms"] / 1000.0,
        retry_budget=handoff["retry_budget"],
    )
    provider_receipt = result.receipt.to_jsonable()
    response = dict(result.response) if isinstance(result.response, Mapping) else None
    response_digest = _sha256_json(response) if response is not None else None
    return {
        "receipt_version": RECEIPT_VERSION,
        "root_dispatch_id": handoff["root_dispatch_id"],
        "dispatch_generation": handoff["dispatch_generation"],
        "intent_digest": handoff["intent_digest"],
        "validation_receipt_ref": handoff["validation_receipt_ref"],
        "capsule_id": handoff["capsule_id"],
        "lease_generation": handoff["lease_generation"],
        "currentness_ref": handoff["currentness_ref"],
        "handoff_digest": handoff_digest,
        "provider_attempt_status": provider_receipt["status"],
        "provider_receipt": provider_receipt,
        "response_digest": response_digest,
        "response": response,
    }


def _credential_resolver(provider: str, cfg: Mapping[str, Any]) -> Sequence[str]:
    """Resolve credentials locally without serializing or logging their values."""
    names = [
        str(name)
        for name in [cfg.get("api_key_env") or cfg.get("key"), *cfg.get("api_key_aliases", [])]
        if name
    ]
    return tuple(provider_key_pool(provider, load_secrets(), key_names=names))


def main() -> int:
    try:
        raw = json.load(sys.stdin)
        sidecar = ProviderSidecarReference(credential_resolver=_credential_resolver)
        receipt = dispatch_handoff(raw, sidecar=sidecar)
    except HandoffError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    except Exception as exc:  # fail closed; never serialize credential-bearing internals
        print(
            json.dumps(
                {"ok": False, "error": "PROVIDER_HANDOFF_INTERNAL_FAILURE", "type": type(exc).__name__},
                sort_keys=True,
            )
        )
        return 3

    ok = receipt["provider_attempt_status"] == SidecarStatus.OK.value
    print(json.dumps({"ok": ok, "receipt": receipt}, sort_keys=True))
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
