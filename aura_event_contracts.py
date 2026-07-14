"""Hardened canonical Aura event contracts.

The reviewed P1 implementation is preserved in ``aura_event_contracts_legacy``.
This facade strengthens privacy filtering while retaining the existing public
API and patching the core module globals used by its dataclasses and stores.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
import math
import re
from typing import Any

import aura_event_contracts_legacy as _legacy


# Match credentials in free-form JSON, YAML, header, query-string, and log text.
# Values may contain base64/base64url and common opaque-token characters,
# including '/', '+', '~', and '='.
_SECRET_PATTERNS = (
    re.compile(
        r"(?ix)"
        r"[\"']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|"
        r"authorization|secret|password|private[_-]?key|token|[a-z0-9_.-]+[_-]token)"
        r"[\"']?\s*[:=]\s*(?:bearer\s+)?[\"']?[^\s,\"'{}&]+[\"']?"
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=\-]+"),
    re.compile(r"\bsk-[A-Za-z0-9._~+/=\-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)

_PRIVATE_REASONING_KEYS = frozenset(
    {
        "chain_of_thought",
        "chain-of-thought",
        "cot",
        "hidden_reasoning",
        "private_reasoning",
        "inner_thought",
        "innerthought",
        "scratchpad",
        "scratch_pad",
    }
)
_NORMALIZED_PRIVATE_REASONING_KEYS = frozenset(
    _legacy._normalize_field_name(item) for item in _PRIVATE_REASONING_KEYS
)
_COMPACT_PRIVATE_REASONING_KEYS = frozenset(
    item.replace("_", "") for item in _NORMALIZED_PRIVATE_REASONING_KEYS
)
_PRIVATE_REASONING_SUFFIXES = tuple(
    f"_{item}" for item in sorted(_NORMALIZED_PRIVATE_REASONING_KEYS)
)
_SECRET_FIELDS = _legacy._SECRET_FIELDS
_SECRET_SUFFIXES = _legacy._SECRET_SUFFIXES


def _is_private_reasoning_field(normalized: str) -> bool:
    compact = normalized.replace("_", "")
    return (
        normalized in _NORMALIZED_PRIVATE_REASONING_KEYS
        or normalized.endswith(_PRIVATE_REASONING_SUFFIXES)
        or compact in _COMPACT_PRIVATE_REASONING_KEYS
        or any(compact.endswith(item) for item in _COMPACT_PRIVATE_REASONING_KEYS)
    )


def redact_secrets(value: str) -> str:
    """Redact credentials from structured-looking or free-form text."""
    redacted = str(value)
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _sanitize_payload(value: Any) -> tuple[Any, bool]:
    """Return a JSON-safe value plus whether conversion/redaction occurred."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        changed = not isinstance(value, dict)
        for key, item in value.items():
            key_text = str(key)
            changed = changed or not isinstance(key, str)
            normalized = _legacy._normalize_field_name(key_text)
            if _is_private_reasoning_field(normalized):
                raise ValueError(f"private reasoning field is prohibited: {key_text}")
            if normalized in _SECRET_FIELDS or normalized.endswith(_SECRET_SUFFIXES):
                result[key_text] = "[REDACTED]"
                changed = True
            else:
                sanitized, item_changed = _sanitize_payload(item)
                result[key_text] = sanitized
                changed = changed or item_changed
        return result, changed
    if isinstance(value, list):
        result = []
        changed = False
        for item in value:
            sanitized, item_changed = _sanitize_payload(item)
            result.append(sanitized)
            changed = changed or item_changed
        return result, changed
    if isinstance(value, tuple):
        result, _changed = _sanitize_payload(list(value))
        return result, True
    if isinstance(value, (set, frozenset)):
        result, _changed = _sanitize_payload(sorted(value, key=str))
        return result, True
    if isinstance(value, str):
        redacted = redact_secrets(value)
        return redacted, redacted != value
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}, True
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite floats are not permitted in event payloads")
    if value is None or isinstance(value, (bool, int, float)):
        return value, False
    if isinstance(value, Enum):
        sanitized, _changed = _sanitize_payload(value.value)
        return sanitized, True
    if is_dataclass(value):
        sanitized, _changed = _sanitize_payload(asdict(value))
        return sanitized, True
    text = redact_secrets(str(value))
    return text, True


def sanitize_payload(value: Any) -> Any:
    """Redact secrets and reject private-reasoning fields before hashing."""
    sanitized, _changed = _sanitize_payload(value)
    return sanitized


# Patch the preserved implementation's globals. Methods defined there resolve
# these names at call time, so existing ToolDecisionRecord, ToolResultRecord,
# and AppendOnlyEventStore behavior is hardened without changing their API.
_legacy._SECRET_PATTERNS = _SECRET_PATTERNS
_legacy._PRIVATE_REASONING_KEYS = _PRIVATE_REASONING_KEYS
_legacy._NORMALIZED_PRIVATE_REASONING_KEYS = _NORMALIZED_PRIVATE_REASONING_KEYS
_legacy._SECRET_FIELDS = _SECRET_FIELDS
_legacy._SECRET_SUFFIXES = _SECRET_SUFFIXES
_legacy.redact_secrets = redact_secrets
_legacy._sanitize_payload = _sanitize_payload
_legacy.sanitize_payload = sanitize_payload

# Re-export the complete prior surface, including internal compatibility names.
for _name, _value in vars(_legacy).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

# Ensure the hardened functions remain the canonical exports.
globals()["redact_secrets"] = redact_secrets
globals()["_sanitize_payload"] = _sanitize_payload
globals()["sanitize_payload"] = sanitize_payload
