"""Pure, purpose-bound egress compilation for Aura Gate.

This module makes no network, provider, audit, or mutation calls.  It either
returns the exact canonical bytes of a JSON-safe payload plus a content-bound
authority capsule, or raises a bounded-code denial.  Permitted payloads are
never silently redacted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
import re
import time
from typing import Any

GATE_EGRESS_CAPSULE_VERSION = "AURA_GATE_EGRESS_CAPSULE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_MAX_ALLOWLIST_VALUES = 256
_MAX_ALLOWLIST_VALUE_BYTES = 512
_MAX_JSON_DEPTH = 32
_MAX_JSON_NODES = 20_000
_MAX_KEY_BYTES = 512
_MAX_STRING_BYTES = 4 * 1024 * 1024
_CAPSULE_PREFIX = "gate-egress-capsule:sha256:"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CAPSULE_ID_RE = re.compile(r"^gate-egress-capsule:sha256:[0-9a-f]{64}$")

_DENIAL_CODES = frozenset(
    {
        "expired_authority",
        "forbidden_material",
        "forbidden_payload_key",
        "invalid_authority_id",
        "invalid_budget",
        "invalid_capsule",
        "invalid_data_classes",
        "invalid_destination",
        "invalid_gate_run_id",
        "invalid_grant",
        "invalid_json_payload",
        "invalid_model",
        "invalid_payload_fields",
        "invalid_provider",
        "invalid_purpose",
        "invalid_retention_class",
        "invalid_time",
        "payload_byte_budget_exceeded",
        "payload_token_budget_exceeded",
        "unauthorized_data_class",
        "unauthorized_destination",
        "unauthorized_model",
        "unauthorized_payload_field",
        "unauthorized_provider",
        "unauthorized_retention_class",
    }
)


class GateEgressDenied(ValueError):
    """A safe, payload-independent egress denial with a bounded reason code."""

    def __init__(self, code: str) -> None:
        bounded_code = code if code in _DENIAL_CODES else "invalid_grant"
        self.code = bounded_code
        super().__init__(f"Aura Gate egress denied: {bounded_code}")


def _deny(code: str) -> None:
    raise GateEgressDenied(code)


def _bounded_text(value: Any, *, code: str, max_bytes: int = _MAX_ALLOWLIST_VALUE_BYTES) -> str:
    if type(value) is not str or not value or value != value.strip():
        _deny(code)
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        _deny(code)
    if size > max_bytes:
        _deny(code)
    return value


def _strict_allowlist(value: Any, *, code: str, allow_empty: bool = False) -> tuple[str, ...]:
    if type(value) is not tuple:
        _deny(code)
    if (not allow_empty and not value) or len(value) > _MAX_ALLOWLIST_VALUES:
        _deny(code)
    items = tuple(_bounded_text(item, code=code) for item in value)
    if len(items) != len(set(items)):
        _deny(code)
    return items


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        _deny("invalid_json_payload")


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _normalize_key(value: str) -> str:
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


_PRIVATE_REASONING_KEYS = frozenset(
    {
        "chain_of_thought",
        "cot",
        "hidden_reasoning",
        "inner_thought",
        "private_reasoning",
        "scratch_pad",
        "scratchpad",
    }
)
_SECRET_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth_token",
        "authorization",
        "bearer",
        "client_secret",
        "cookie",
        "credential",
        "id_token",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "set_cookie",
        "token",
    }
)
_SOURCE_DIFF_KEYS = frozenset(
    {
        "diff",
        "patch",
        "source_diff",
        "source_patch",
        "unified_diff",
    }
)
_FORBIDDEN_KEYS = _PRIVATE_REASONING_KEYS | _SECRET_KEYS | _SOURCE_DIFF_KEYS
_FORBIDDEN_KEY_SUFFIXES = tuple("_" + value for value in sorted(_FORBIDDEN_KEYS) if len(value) >= 5)
_COMPACT_PRIVATE_REASONING_KEYS = frozenset(value.replace("_", "") for value in _PRIVATE_REASONING_KEYS)

_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/%=-]{8,}")
_BASIC_PATTERN = re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/=]{8,}")
_JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")
_PRIVATE_KEY_PATTERN = re.compile(r"(?is)-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?-----END [^-\r\n]*PRIVATE KEY-----")
_PRIVATE_REASONING_PATTERN = re.compile(
    r"(?i)\b(?:chain[ _-]?of[ _-]?thought|hidden[ _-]?reasoning|private[ _-]?reasoning|scratch[ _-]?pad)\s*[:=]"
)
_SOURCE_DIFF_PATTERN = re.compile(
    r"(?m)(?:^diff --git\s|^@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@|^\*\*\* Begin Patch\s*$)"
)
_PROVIDER_SECRET_PATTERN = re.compile(r"\b(?:sk-[A-Za-z0-9._~+/%=-]{20,}|AKIA[0-9A-Z]{16})\b")


def _forbidden_key(key: str) -> bool:
    normalized = _normalize_key(key)
    compact = normalized.replace("_", "")
    return (
        normalized in _FORBIDDEN_KEYS
        or normalized.endswith(_FORBIDDEN_KEY_SUFFIXES)
        or compact in _COMPACT_PRIVATE_REASONING_KEYS
    )


def _contains_forbidden_string(value: str) -> bool:
    return any(
        pattern.search(value) is not None
        for pattern in (
            _BEARER_PATTERN,
            _BASIC_PATTERN,
            _JWT_PATTERN,
            _PRIVATE_KEY_PATTERN,
            _PRIVATE_REASONING_PATTERN,
            _SOURCE_DIFF_PATTERN,
            _PROVIDER_SECRET_PATTERN,
        )
    )


def _validate_json_tree(value: Any) -> None:
    nodes = 0

    def visit(item: Any, *, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_JSON_NODES or depth > _MAX_JSON_DEPTH:
            _deny("invalid_json_payload")
        if item is None or type(item) is bool:
            return
        if type(item) is int:
            return
        if type(item) is float:
            if not math.isfinite(item):
                _deny("invalid_json_payload")
            return
        if type(item) is str:
            try:
                if len(item.encode("utf-8")) > _MAX_STRING_BYTES:
                    _deny("invalid_json_payload")
            except UnicodeError:
                _deny("invalid_json_payload")
            if _contains_forbidden_string(item):
                _deny("forbidden_material")
            return
        if type(item) is list:
            for nested in item:
                visit(nested, depth=depth + 1)
            return
        if type(item) is dict:
            for key, nested in item.items():
                if type(key) is not str or not key or key != key.strip():
                    _deny("invalid_json_payload")
                try:
                    if len(key.encode("utf-8")) > _MAX_KEY_BYTES:
                        _deny("invalid_json_payload")
                except UnicodeError:
                    _deny("invalid_json_payload")
                if _forbidden_key(key):
                    _deny("forbidden_payload_key")
                visit(nested, depth=depth + 1)
            return
        _deny("invalid_json_payload")

    visit(value, depth=0)


@dataclass(frozen=True, slots=True)
class GateEgressGrant:
    """Exact authority and allowlists for one class of governed egress."""

    authority_id: str
    gate_run_id: str
    purpose_digest: str
    expires_at: float
    allowed_destinations: tuple[str, ...]
    allowed_providers: tuple[str, ...]
    allowed_models: tuple[str, ...]
    allowed_data_classes: tuple[str, ...]
    allowed_top_level_fields: tuple[str, ...]
    allowed_retention_classes: tuple[str, ...]
    max_payload_bytes: int
    max_token_estimate: int

    def __post_init__(self) -> None:
        _bounded_text(self.authority_id, code="invalid_authority_id")
        _bounded_text(self.gate_run_id, code="invalid_gate_run_id")
        _bounded_text(self.purpose_digest, code="invalid_purpose")
        if type(self.expires_at) not in (int, float) or not math.isfinite(float(self.expires_at)):
            _deny("invalid_grant")
        if float(self.expires_at) <= 0:
            _deny("invalid_grant")
        if type(self.expires_at) is int:
            object.__setattr__(self, "expires_at", float(self.expires_at))

        for name, code in (
            ("allowed_destinations", "invalid_destination"),
            ("allowed_providers", "invalid_provider"),
            ("allowed_models", "invalid_model"),
            ("allowed_data_classes", "invalid_data_classes"),
            ("allowed_top_level_fields", "invalid_payload_fields"),
            ("allowed_retention_classes", "invalid_retention_class"),
        ):
            values = _strict_allowlist(getattr(self, name), code=code)
            if name == "allowed_top_level_fields" and any(_forbidden_key(item) for item in values):
                _deny("forbidden_payload_key")

        for name in ("max_payload_bytes", "max_token_estimate"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                _deny("invalid_budget")


@dataclass(frozen=True, slots=True)
class GateEgressCapsule:
    """Content-addressed proof of the exact bytes admitted by the governor."""

    capsule_id: str
    authority_id: str
    gate_run_id: str
    purpose_digest: str
    destination: str
    provider: str
    model: str
    data_classes: tuple[str, ...]
    retention_class: str
    included_fields: tuple[str, ...]
    payload_digest: str
    payload_bytes: int
    token_estimate: int
    compiled_at: float
    source_mutation_performed: bool = False
    production_promotion_authority: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    version: str = GATE_EGRESS_CAPSULE_VERSION

    def __post_init__(self) -> None:
        for value in (
            self.authority_id,
            self.gate_run_id,
            self.purpose_digest,
            self.destination,
            self.provider,
            self.model,
            self.retention_class,
        ):
            _bounded_text(value, code="invalid_capsule")
        classes = _strict_allowlist(self.data_classes, code="invalid_capsule")
        fields = _strict_allowlist(self.included_fields, code="invalid_capsule")
        if classes != tuple(sorted(classes)) or fields != tuple(sorted(fields)):
            _deny("invalid_capsule")
        if type(self.payload_digest) is not str or _SHA256_RE.fullmatch(self.payload_digest) is None:
            _deny("invalid_capsule")
        if type(self.payload_bytes) is not int or self.payload_bytes <= 0:
            _deny("invalid_capsule")
        if type(self.token_estimate) is not int or self.token_estimate <= 0:
            _deny("invalid_capsule")
        if type(self.compiled_at) not in (int, float) or not math.isfinite(float(self.compiled_at)):
            _deny("invalid_capsule")
        if float(self.compiled_at) < 0:
            _deny("invalid_capsule")
        if type(self.capsule_id) is not str or _CAPSULE_ID_RE.fullmatch(self.capsule_id) is None:
            _deny("invalid_capsule")
        if type(self.source_mutation_performed) is not bool or self.source_mutation_performed:
            _deny("invalid_capsule")
        if type(self.production_promotion_authority) is not bool or self.production_promotion_authority:
            _deny("invalid_capsule")
        if type(self.vsa_patch_authority) is not bool or self.vsa_patch_authority:
            _deny("invalid_capsule")
        if self.patch_authority != PATCH_AUTHORITY or self.version != GATE_EGRESS_CAPSULE_VERSION:
            _deny("invalid_capsule")
        if self.capsule_id != self.content_id(self.identity_basis()):
            _deny("invalid_capsule")

    def identity_basis(self) -> dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            "gate_run_id": self.gate_run_id,
            "purpose_digest": self.purpose_digest,
            "destination": self.destination,
            "provider": self.provider,
            "model": self.model,
            "data_classes": list(self.data_classes),
            "retention_class": self.retention_class,
            "included_fields": list(self.included_fields),
            "payload_digest": self.payload_digest,
            "payload_bytes": self.payload_bytes,
            "token_estimate": self.token_estimate,
            "compiled_at": self.compiled_at,
            "source_mutation_performed": self.source_mutation_performed,
            "production_promotion_authority": self.production_promotion_authority,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "version": self.version,
        }

    @staticmethod
    def content_id(basis: dict[str, Any]) -> str:
        return _CAPSULE_PREFIX + hashlib.sha256(_canonical_json(basis)).hexdigest()

    @classmethod
    def create(cls, **values: Any) -> GateEgressCapsule:
        basis = dict(values)
        basis.update(
            {
                "source_mutation_performed": False,
                "production_promotion_authority": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                "version": GATE_EGRESS_CAPSULE_VERSION,
            }
        )
        return cls(capsule_id=cls.content_id(basis), **basis)

    def to_dict(self) -> dict[str, Any]:
        return {"capsule_id": self.capsule_id, **self.identity_basis()}


@dataclass(frozen=True, slots=True)
class GovernedEgress:
    """The exact safe bytes and the capsule that authorizes only those bytes."""

    capsule: GateEgressCapsule
    canonical_payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.canonical_payload) is not bytes:
            _deny("invalid_capsule")
        if self.capsule.payload_bytes != len(self.canonical_payload):
            _deny("invalid_capsule")
        if not hmac.compare_digest(self.capsule.payload_digest, _sha256(self.canonical_payload)):
            _deny("invalid_capsule")
        try:
            decoded = json.loads(self.canonical_payload.decode("utf-8"))
            if type(decoded) is not dict or not decoded:
                _deny("invalid_capsule")
            _validate_json_tree(decoded)
            canonical = _canonical_json(decoded)
        except GateEgressDenied:
            _deny("invalid_capsule")
        except (UnicodeError, ValueError, TypeError):
            _deny("invalid_capsule")
        if canonical != self.canonical_payload:
            _deny("invalid_capsule")
        if tuple(sorted(decoded)) != self.capsule.included_fields:
            _deny("invalid_capsule")

    def decoded_payload(self) -> dict[str, Any]:
        """Return a fresh decode of the exact admitted bytes for a transport."""

        value = json.loads(self.canonical_payload.decode("utf-8"))
        if type(value) is not dict:  # pragma: no cover - guarded during compilation
            _deny("invalid_capsule")
        return value


class GateEgressGovernor:
    """Compile purpose-limited egress without performing an external effect."""

    @staticmethod
    def compile(
        grant: GateEgressGrant,
        payload: dict[str, Any],
        *,
        purpose_digest: str,
        destination: str,
        provider: str,
        model: str,
        data_classes: tuple[str, ...],
        retention_class: str,
        now: float | None = None,
    ) -> GovernedEgress:
        if type(grant) is not GateEgressGrant:
            _deny("invalid_grant")
        evaluation_time = time.time() if now is None else now
        if type(evaluation_time) not in (int, float) or not math.isfinite(float(evaluation_time)):
            _deny("invalid_time")
        evaluation_time = float(evaluation_time)
        if evaluation_time < 0:
            _deny("invalid_time")
        if evaluation_time >= grant.expires_at:
            _deny("expired_authority")

        supplied_purpose = _bounded_text(purpose_digest, code="invalid_purpose")
        if not hmac.compare_digest(supplied_purpose.encode("utf-8"), grant.purpose_digest.encode("utf-8")):
            _deny("invalid_purpose")
        selected_destination = _bounded_text(destination, code="invalid_destination")
        if selected_destination not in grant.allowed_destinations:
            _deny("unauthorized_destination")
        selected_provider = _bounded_text(provider, code="invalid_provider")
        if selected_provider not in grant.allowed_providers:
            _deny("unauthorized_provider")
        selected_model = _bounded_text(model, code="invalid_model")
        if selected_model not in grant.allowed_models:
            _deny("unauthorized_model")
        selected_classes = _strict_allowlist(data_classes, code="invalid_data_classes")
        if not set(selected_classes).issubset(grant.allowed_data_classes):
            _deny("unauthorized_data_class")
        selected_retention = _bounded_text(retention_class, code="invalid_retention_class")
        if selected_retention not in grant.allowed_retention_classes:
            _deny("unauthorized_retention_class")

        if type(payload) is not dict or not payload:
            _deny("invalid_json_payload")
        if any(type(item) is not str for item in payload):
            _deny("invalid_json_payload")
        top_level_fields = tuple(sorted(payload))
        if not set(top_level_fields).issubset(grant.allowed_top_level_fields):
            _deny("unauthorized_payload_field")
        _validate_json_tree(payload)
        serialized = _canonical_json(payload)
        payload_bytes = len(serialized)
        token_estimate = (payload_bytes + 3) // 4
        if payload_bytes > grant.max_payload_bytes:
            _deny("payload_byte_budget_exceeded")
        if token_estimate > grant.max_token_estimate:
            _deny("payload_token_budget_exceeded")

        capsule = GateEgressCapsule.create(
            authority_id=grant.authority_id,
            gate_run_id=grant.gate_run_id,
            purpose_digest=grant.purpose_digest,
            destination=selected_destination,
            provider=selected_provider,
            model=selected_model,
            data_classes=tuple(sorted(selected_classes)),
            retention_class=selected_retention,
            included_fields=top_level_fields,
            payload_digest=_sha256(serialized),
            payload_bytes=payload_bytes,
            token_estimate=token_estimate,
            compiled_at=evaluation_time,
        )
        return GovernedEgress(capsule=capsule, canonical_payload=serialized)


__all__ = [
    "GATE_EGRESS_CAPSULE_VERSION",
    "GateEgressCapsule",
    "GateEgressDenied",
    "GateEgressGovernor",
    "GateEgressGrant",
    "GovernedEgress",
]
