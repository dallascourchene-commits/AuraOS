"""Purpose-bound Aura Gate authority wrapper for Aura Forge.

Aura Gate compiles verified OIDC identity, a static deny-by-default policy, the
exact retained Forge evidence contract, and a canonical Arena lease into one
durable authority envelope.  Every consequential transition is revalidated and
recorded before Aura Forge or an egress boundary is invoked.

This module grants no commit, merge, policy-promotion, release, or production
mutation authority.  Completed Forge work stops at human review.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import math
from pathlib import Path, PurePosixPath
import re
import sqlite3
import time
from typing import Any

from aura_event_contracts import ActorType
from aura_forge import (
    REVIEW_READY_STATUS,
    SUPPORTED_REQUIRED_GATES,
    AuraForgeRuntime,
    ForgeRunRequest,
    forge_contract_digest,
    validate_forge_contract,
)
from aura_gate_audit import GateAuditError, GateAuditLedger
from aura_gate_egress import (
    GateEgressDenied,
    GateEgressGovernor,
    GateEgressGrant,
    GovernedEgress,
)
from aura_gate_oidc import VerifiedGateIdentity
from aura_liquid_planning_arena import ArenaLease

GATE_VERSION = "AURA_GATE_V1"
GATE_POLICY_VERSION = "AURA_GATE_POLICY_V1"
GATE_AUTHORITY_VERSION = "AURA_GATE_AUTHORITY_ENVELOPE_V1"
GATE_LEASE_STORE_VERSION = "AURA_GATE_LEASE_STORE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_POLICY_PREFIX = "GATE-POLICY-sha256:"
_AUTHORITY_PREFIX = "GATE-AUTH-sha256:"
_PURPOSE_PREFIX = "sha256:"
_SAFE_PROTOCOLS = frozenset({"NATIVE", "MCP", "A2A"})
_LEASE_STATUSES = frozenset({"ACTIVE", "STARTING", "STARTED", "REVOKED", "EXPIRED", "DISSOLVED"})
_TERMINAL_STATUSES = frozenset({"REVOKED", "EXPIRED", "DISSOLVED"})
_BOUNDED_CONTEXT_EGRESS_FIELDS = frozenset(
    {
        "act_capsule",
        "compressed_context",
        "failure_packet",
        "instruction",
        "output_contract",
        "source_slices",
        "test_slices",
    }
)
_CAPABILITY_IMPLICATIONS = {
    "FORGE_START": frozenset({"READ.REPOSITORY", "PROPOSE.PATCH"}),
    "FORGE_SUBMIT": frozenset({"READ.REPOSITORY", "PROPOSE.PATCH", "RUN.TESTS"}),
}
_MAX_STRING_BYTES = 4096
_MAX_VALUES = 256
_CAPABILITY_RE = re.compile(r"^[A-Z][A-Z0-9_.:-]{1,127}$")
_DIGEST_RE = re.compile(r"^(?:sha256|blake2b-256):[0-9a-f]{32,128}$")


class GateError(ValueError):
    """A bounded, safe-to-report Aura Gate failure."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(f"Aura Gate denied the operation: {self.code}")


def _deny(code: str) -> None:
    raise GateError(code)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise GateError("invalid_json_contract") from exc


def _sha256(value: Any) -> str:
    encoded = _canonical_json(value).encode("utf-8")
    return _PURPOSE_PREFIX + hashlib.sha256(encoded).hexdigest()


def gate_purpose_digest(objective: str) -> str:
    """Bind a Gate purpose to one exact, bounded objective string."""

    return _sha256({"objective": _text(objective, "objective", limit=16_000)})


def _text(value: Any, field: str, *, limit: int = _MAX_STRING_BYTES) -> str:
    if type(value) is not str or not value or value != value.strip():
        _deny(f"invalid_{field}")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        _deny(f"invalid_{field}")
    if len(encoded) > limit or "\x00" in value:
        _deny(f"invalid_{field}")
    return value


def _optional_text(value: Any, field: str, *, limit: int = _MAX_STRING_BYTES) -> str:
    if value in (None, ""):
        return ""
    return _text(value, field, limit=limit)


def _strings(
    value: Any,
    field: str,
    *,
    allow_empty: bool = False,
    upper: bool = False,
    sort: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        _deny(f"invalid_{field}")
    raw = tuple(value)
    if not allow_empty and not raw:
        _deny(f"invalid_{field}")
    if len(raw) > _MAX_VALUES:
        _deny(f"invalid_{field}")
    values = tuple(_text(item, field, limit=512) for item in raw)
    if upper:
        values = tuple(item.upper() for item in values)
    if len(values) != len(set(values)):
        _deny(f"invalid_{field}")
    return tuple(sorted(values)) if sort else values


def _strict_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _deny(f"invalid_{field}")
    return value


def _strict_float(value: Any, field: str, minimum: float, maximum: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        _deny(f"invalid_{field}")
    parsed = float(value)
    if not minimum <= parsed <= maximum:
        _deny(f"invalid_{field}")
    return parsed


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        _deny(f"invalid_{field}")
    return value


def _repo_path(value: Any, field: str) -> str:
    text = _text(value, field, limit=1024).replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        _deny(f"invalid_{field}")
    return path.as_posix()


def _digest_text(value: Any, field: str) -> str:
    text = _text(value, field, limit=256)
    if _DIGEST_RE.fullmatch(text) is None:
        _deny(f"invalid_{field}")
    return text


def _policy_id(basis: Mapping[str, Any]) -> str:
    return _POLICY_PREFIX + hashlib.sha256(_canonical_json(basis).encode("utf-8")).hexdigest()


def _authority_id(basis: Mapping[str, Any]) -> str:
    return _AUTHORITY_PREFIX + hashlib.sha256(_canonical_json(basis).encode("utf-8")).hexdigest()


def _nonce_digest(actor_ref: str, policy_id: str, nonce: str) -> str:
    """Bind a one-use request nonce without indexing its raw value."""

    return _sha256(
        {
            "actor_ref": _text(actor_ref, "actor_ref", limit=256),
            "policy_id": _text(policy_id, "policy_id", limit=256),
            "nonce": _text(nonce, "nonce", limit=256),
        }
    )


def _lease_issue_operation_id(actor_ref: str, policy_id: str, nonce: str) -> str:
    digest = _nonce_digest(actor_ref, policy_id, nonce).removeprefix(_PURPOSE_PREFIX)
    return f"ISSUE-NONCE-{digest[:48]}"


def _identity_basis(identity: VerifiedGateIdentity) -> dict[str, Any]:
    return {
        "actor_ref": identity.actor_ref,
        "issuer": identity.issuer,
        "audiences": sorted(identity.audiences),
        "authorized_party": identity.authorized_party,
        "roles": sorted(identity.roles),
        "groups": sorted(identity.groups),
        "jwks_digest": identity.jwks_digest,
    }


@dataclass(frozen=True, slots=True)
class GatePolicyManifest:
    """One immutable, deny-by-default Forge-specific Gate policy."""

    policy_id: str
    name: str
    allowed_purpose_digests: tuple[str, ...]
    allowed_capabilities: tuple[str, ...]
    allowed_files: tuple[str, ...]
    allowed_destinations: tuple[str, ...]
    allowed_providers: tuple[str, ...]
    allowed_models: tuple[str, ...]
    allowed_data_classes: tuple[str, ...]
    allowed_egress_fields: tuple[str, ...]
    allowed_retention_classes: tuple[str, ...]
    allowed_protocols: tuple[str, ...]
    required_verifiers: tuple[str, ...]
    required_roles: tuple[str, ...]
    required_groups: tuple[str, ...]
    max_lease_ttl_seconds: float
    max_payload_bytes: int
    max_token_estimate: int
    max_context_tokens: int
    max_output_tokens: int
    max_turns: int
    max_local_repairs: int
    max_provider_calls: int
    private_only: bool = True
    human_review_required: bool = True
    production_mutation: bool = False
    automatic_promotion: bool = False
    version: str = GATE_POLICY_VERSION

    def __post_init__(self) -> None:
        basis = self.identity_basis()
        if self.policy_id != _policy_id(basis):
            _deny("invalid_policy_id")
        if self.version != GATE_POLICY_VERSION:
            _deny("unsupported_policy_version")
        if (
            _strict_bool(self.private_only, "private_only") is not True
            or _strict_bool(self.human_review_required, "human_review_required") is not True
            or _strict_bool(self.production_mutation, "production_mutation") is not False
            or _strict_bool(self.automatic_promotion, "automatic_promotion") is not False
        ):
            _deny("invalid_policy_authority")
        if not set(self.required_verifiers).issubset(SUPPORTED_REQUIRED_GATES):
            _deny("unsupported_policy_verifier")

    def identity_basis(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "allowed_purpose_digests": list(self.allowed_purpose_digests),
            "allowed_capabilities": list(self.allowed_capabilities),
            "allowed_files": list(self.allowed_files),
            "allowed_destinations": list(self.allowed_destinations),
            "allowed_providers": list(self.allowed_providers),
            "allowed_models": list(self.allowed_models),
            "allowed_data_classes": list(self.allowed_data_classes),
            "allowed_egress_fields": list(self.allowed_egress_fields),
            "allowed_retention_classes": list(self.allowed_retention_classes),
            "allowed_protocols": list(self.allowed_protocols),
            "required_verifiers": list(self.required_verifiers),
            "required_roles": list(self.required_roles),
            "required_groups": list(self.required_groups),
            "max_lease_ttl_seconds": self.max_lease_ttl_seconds,
            "max_payload_bytes": self.max_payload_bytes,
            "max_token_estimate": self.max_token_estimate,
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_turns": self.max_turns,
            "max_local_repairs": self.max_local_repairs,
            "max_provider_calls": self.max_provider_calls,
            "private_only": self.private_only,
            "human_review_required": self.human_review_required,
            "production_mutation": self.production_mutation,
            "automatic_promotion": self.automatic_promotion,
            "version": self.version,
        }

    @property
    def policy_digest(self) -> str:
        return _sha256(self.to_dict())

    @classmethod
    def create(
        cls,
        *,
        name: str,
        allowed_purpose_digests: Sequence[str],
        allowed_capabilities: Sequence[str],
        allowed_files: Sequence[str],
        allowed_destinations: Sequence[str],
        allowed_providers: Sequence[str],
        allowed_models: Sequence[str],
        allowed_data_classes: Sequence[str],
        allowed_egress_fields: Sequence[str],
        allowed_retention_classes: Sequence[str],
        allowed_protocols: Sequence[str],
        required_verifiers: Sequence[str],
        required_roles: Sequence[str] = (),
        required_groups: Sequence[str] = (),
        max_lease_ttl_seconds: float = 900.0,
        max_payload_bytes: int = 64_000,
        max_token_estimate: int = 16_000,
        max_context_tokens: int = 2200,
        max_output_tokens: int = 2400,
        max_turns: int = 12,
        max_local_repairs: int = 2,
        max_provider_calls: int = 12,
    ) -> GatePolicyManifest:
        purposes = tuple(_digest_text(item, "purpose_digest") for item in allowed_purpose_digests)
        capabilities = _strings(allowed_capabilities, "capabilities", upper=True)
        if any(_CAPABILITY_RE.fullmatch(item) is None for item in capabilities):
            _deny("invalid_capabilities")
        files = tuple(sorted(_repo_path(item, "allowed_file") for item in allowed_files))
        protocols = _strings(allowed_protocols, "protocols", upper=True)
        if not set(protocols).issubset(_SAFE_PROTOCOLS):
            _deny("invalid_protocols")
        values = {
            "name": _text(name, "policy_name", limit=256),
            "allowed_purpose_digests": tuple(sorted(purposes)),
            "allowed_capabilities": capabilities,
            "allowed_files": files,
            "allowed_destinations": _strings(allowed_destinations, "destinations"),
            "allowed_providers": _strings(allowed_providers, "providers"),
            "allowed_models": _strings(allowed_models, "models"),
            "allowed_data_classes": _strings(allowed_data_classes, "data_classes"),
            "allowed_egress_fields": _strings(allowed_egress_fields, "egress_fields"),
            "allowed_retention_classes": _strings(allowed_retention_classes, "retention_classes"),
            "allowed_protocols": protocols,
            "required_verifiers": _strings(required_verifiers, "verifiers"),
            "required_roles": _strings(required_roles, "roles", allow_empty=True),
            "required_groups": _strings(required_groups, "groups", allow_empty=True),
            "max_lease_ttl_seconds": _strict_float(max_lease_ttl_seconds, "max_lease_ttl_seconds", 1.0, 86_400.0),
            "max_payload_bytes": _strict_int(max_payload_bytes, "max_payload_bytes", 1, 10_000_000),
            "max_token_estimate": _strict_int(max_token_estimate, "max_token_estimate", 1, 2_500_000),
            "max_context_tokens": _strict_int(max_context_tokens, "max_context_tokens", 256, 16_000),
            "max_output_tokens": _strict_int(max_output_tokens, "max_output_tokens", 128, 16_000),
            "max_turns": _strict_int(max_turns, "max_turns", 1, 40),
            "max_local_repairs": _strict_int(max_local_repairs, "max_local_repairs", 0, 8),
            "max_provider_calls": _strict_int(max_provider_calls, "max_provider_calls", 1, 128),
            "private_only": True,
            "human_review_required": True,
            "production_mutation": False,
            "automatic_promotion": False,
            "version": GATE_POLICY_VERSION,
        }
        return cls(policy_id=_policy_id(values), **values)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> GatePolicyManifest:
        if not isinstance(value, Mapping):
            _deny("invalid_policy")
        raw = dict(value)
        expected = {field.name for field in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        if set(raw) != expected:
            _deny("invalid_policy_fields")
        policy = cls(
            policy_id=_text(raw["policy_id"], "policy_id", limit=256),
            name=_text(raw["name"], "policy_name", limit=256),
            allowed_purpose_digests=tuple(
                _digest_text(item, "purpose_digest")
                for item in _strings(raw["allowed_purpose_digests"], "purpose_digests")
            ),
            allowed_capabilities=_strings(raw["allowed_capabilities"], "capabilities", upper=True),
            allowed_files=tuple(
                _repo_path(item, "allowed_file") for item in _strings(raw["allowed_files"], "allowed_files")
            ),
            allowed_destinations=_strings(raw["allowed_destinations"], "destinations"),
            allowed_providers=_strings(raw["allowed_providers"], "providers"),
            allowed_models=_strings(raw["allowed_models"], "models"),
            allowed_data_classes=_strings(raw["allowed_data_classes"], "data_classes"),
            allowed_egress_fields=_strings(raw["allowed_egress_fields"], "egress_fields"),
            allowed_retention_classes=_strings(raw["allowed_retention_classes"], "retention_classes"),
            allowed_protocols=_strings(raw["allowed_protocols"], "protocols", upper=True),
            required_verifiers=_strings(raw["required_verifiers"], "verifiers"),
            required_roles=_strings(raw["required_roles"], "roles", allow_empty=True),
            required_groups=_strings(raw["required_groups"], "groups", allow_empty=True),
            max_lease_ttl_seconds=_strict_float(raw["max_lease_ttl_seconds"], "max_lease_ttl_seconds", 1.0, 86_400.0),
            max_payload_bytes=_strict_int(raw["max_payload_bytes"], "max_payload_bytes", 1, 10_000_000),
            max_token_estimate=_strict_int(raw["max_token_estimate"], "max_token_estimate", 1, 2_500_000),
            max_context_tokens=_strict_int(raw["max_context_tokens"], "max_context_tokens", 256, 16_000),
            max_output_tokens=_strict_int(raw["max_output_tokens"], "max_output_tokens", 128, 16_000),
            max_turns=_strict_int(raw["max_turns"], "max_turns", 1, 40),
            max_local_repairs=_strict_int(raw["max_local_repairs"], "max_local_repairs", 0, 8),
            max_provider_calls=_strict_int(raw["max_provider_calls"], "max_provider_calls", 1, 128),
            private_only=_strict_bool(raw["private_only"], "private_only"),
            human_review_required=_strict_bool(raw["human_review_required"], "human_review_required"),
            production_mutation=_strict_bool(raw["production_mutation"], "production_mutation"),
            automatic_promotion=_strict_bool(raw["automatic_promotion"], "automatic_promotion"),
            version=_text(raw["version"], "policy_version", limit=64),
        )
        return policy

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for name in (
            "allowed_purpose_digests",
            "allowed_capabilities",
            "allowed_files",
            "allowed_destinations",
            "allowed_providers",
            "allowed_models",
            "allowed_data_classes",
            "allowed_egress_fields",
            "allowed_retention_classes",
            "allowed_protocols",
            "required_verifiers",
            "required_roles",
            "required_groups",
        ):
            payload[name] = list(payload[name])
        return payload


@dataclass(frozen=True, slots=True)
class GateRunRequest:
    policy_id: str
    purpose_digest: str
    objective: str
    target_file: str
    target_symbol: str
    acceptance_criteria: tuple[str, ...]
    risk_map: tuple[str, ...]
    constraints: tuple[str, ...]
    capabilities: tuple[str, ...]
    destination: str
    provider: str
    model: str
    data_classes: tuple[str, ...]
    retention_class: str
    egress_fields: tuple[str, ...]
    protocol: str
    lease_ttl_seconds: float
    nonce: str
    council_mode: str
    max_context_tokens: int
    max_output_tokens: int
    max_turns: int
    max_local_repairs: int
    max_provider_calls: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> GateRunRequest:
        if not isinstance(value, Mapping):
            _deny("invalid_gate_request")
        raw = dict(value)
        required = {
            "policy_id",
            "purpose_digest",
            "objective",
            "target_file",
            "target_symbol",
            "acceptance_criteria",
            "risk_map",
            "constraints",
            "capabilities",
            "destination",
            "provider",
            "model",
            "data_classes",
            "retention_class",
            "egress_fields",
            "protocol",
            "lease_ttl_seconds",
            "nonce",
            "council_mode",
            "max_context_tokens",
            "max_output_tokens",
            "max_turns",
            "max_local_repairs",
            "max_provider_calls",
        }
        if set(raw) != required:
            _deny("invalid_gate_request_fields")
        capabilities = _strings(raw["capabilities"], "capabilities", upper=True)
        if any(_CAPABILITY_RE.fullmatch(item) is None for item in capabilities):
            _deny("invalid_capabilities")
        protocol = _text(raw["protocol"], "protocol", limit=32).upper()
        if protocol not in _SAFE_PROTOCOLS:
            _deny("invalid_protocol")
        request = cls(
            policy_id=_text(raw["policy_id"], "policy_id", limit=256),
            purpose_digest=_digest_text(raw["purpose_digest"], "purpose_digest"),
            objective=_text(raw["objective"], "objective", limit=16_000),
            target_file=_repo_path(raw["target_file"], "target_file"),
            target_symbol=_text(raw["target_symbol"], "target_symbol", limit=512),
            acceptance_criteria=_strings(raw["acceptance_criteria"], "acceptance_criteria"),
            risk_map=_strings(raw["risk_map"], "risk_map"),
            constraints=_strings(raw["constraints"], "constraints", allow_empty=True),
            capabilities=capabilities,
            destination=_text(raw["destination"], "destination", limit=2048),
            provider=_text(raw["provider"], "provider", limit=256),
            model=_text(raw["model"], "model", limit=256),
            data_classes=_strings(raw["data_classes"], "data_classes"),
            retention_class=_text(raw["retention_class"], "retention_class", limit=256),
            egress_fields=_strings(raw["egress_fields"], "egress_fields"),
            protocol=protocol,
            lease_ttl_seconds=_strict_float(raw["lease_ttl_seconds"], "lease_ttl_seconds", 1.0, 86_400.0),
            nonce=_text(raw["nonce"], "nonce", limit=256),
            council_mode=_text(raw["council_mode"], "council_mode", limit=32).upper(),
            max_context_tokens=_strict_int(raw["max_context_tokens"], "max_context_tokens", 256, 16_000),
            max_output_tokens=_strict_int(raw["max_output_tokens"], "max_output_tokens", 128, 16_000),
            max_turns=_strict_int(raw["max_turns"], "max_turns", 1, 40),
            max_local_repairs=_strict_int(raw["max_local_repairs"], "max_local_repairs", 0, 8),
            max_provider_calls=_strict_int(raw["max_provider_calls"], "max_provider_calls", 1, 128),
        )
        if not hmac.compare_digest(
            request.purpose_digest.encode("utf-8"),
            gate_purpose_digest(request.objective).encode("utf-8"),
        ):
            _deny("purpose_objective_mismatch")
        if request.council_mode not in {"AUTO", "SELECTIVE_V3", "FULL_V2"}:
            _deny("invalid_council_mode")
        for trigger, implied in _CAPABILITY_IMPLICATIONS.items():
            if trigger in request.capabilities and not implied.issubset(request.capabilities):
                _deny("capability_bundle_incomplete")
        return request

    def to_forge_request(self, *, required_gates: Sequence[str]) -> ForgeRunRequest:
        return ForgeRunRequest.from_value(
            {
                "objective": self.objective,
                "target_file": self.target_file,
                "target_symbol": self.target_symbol,
                "acceptance_criteria": list(self.acceptance_criteria),
                "risk_map": list(self.risk_map),
                "constraints": list(self.constraints),
                "provider": self.provider,
                "model": self.model,
                "council_mode": self.council_mode,
                "max_context_tokens": self.max_context_tokens,
                "max_output_tokens": self.max_output_tokens,
                "max_turns": self.max_turns,
                "max_local_repairs": self.max_local_repairs,
                "required_gates": list(required_gates),
                "metadata": {
                    "gate_policy_id": self.policy_id,
                    "gate_purpose_digest": self.purpose_digest,
                    "gate_protocol": self.protocol,
                },
            }
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for name in (
            "acceptance_criteria",
            "risk_map",
            "constraints",
            "capabilities",
            "data_classes",
            "egress_fields",
        ):
            payload[name] = list(payload[name])
        return payload


@dataclass(frozen=True, slots=True)
class GateAuthorityEnvelope:
    authority_id: str
    gate_run_id: str
    actor_ref: str
    identity_basis_digest: str
    policy_id: str
    policy_digest: str
    purpose_digest: str
    forge_run_id: str
    forge_contract_id: str
    forge_contract_digest: str
    repository_digest: str
    arena_lease_json: str
    arena_lease_digest: str
    capabilities: tuple[str, ...]
    allowed_files: tuple[str, ...]
    destinations: tuple[str, ...]
    providers: tuple[str, ...]
    models: tuple[str, ...]
    data_classes: tuple[str, ...]
    egress_fields: tuple[str, ...]
    retention_classes: tuple[str, ...]
    required_verifiers: tuple[str, ...]
    protocol: str
    max_payload_bytes: int
    max_token_estimate: int
    max_output_tokens: int
    max_provider_calls: int
    nonce: str
    issued_at: float
    expires_at: float
    human_review_required: bool = True
    production_mutation: bool = False
    automatic_commit: bool = False
    automatic_push: bool = False
    automatic_pull_request: bool = False
    automatic_merge: bool = False
    automatic_promotion: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    version: str = GATE_AUTHORITY_VERSION

    def __post_init__(self) -> None:
        self.validate_integrity()

    def identity_basis(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("authority_id")
        payload.pop("gate_run_id")
        return payload

    def validate_integrity(self) -> None:
        if self.version != GATE_AUTHORITY_VERSION or self.patch_authority != PATCH_AUTHORITY:
            _deny("invalid_authority_envelope")
        for name in (
            "human_review_required",
            "production_mutation",
            "automatic_commit",
            "automatic_push",
            "automatic_pull_request",
            "automatic_merge",
            "automatic_promotion",
            "vsa_patch_authority",
        ):
            _strict_bool(getattr(self, name), name)
        if (
            self.human_review_required is not True
            or self.production_mutation is not False
            or self.automatic_commit is not False
            or self.automatic_push is not False
            or self.automatic_pull_request is not False
            or self.automatic_merge is not False
            or self.automatic_promotion is not False
            or self.vsa_patch_authority is not False
        ):
            _deny("invalid_authority_boundary")
        try:
            lease = json.loads(self.arena_lease_json)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GateError("invalid_arena_lease_snapshot") from exc
        if type(lease) is not dict or _sha256(lease) != self.arena_lease_digest:
            _deny("invalid_arena_lease_snapshot")
        expected = _authority_id(self.identity_basis())
        if self.authority_id != expected:
            _deny("invalid_authority_id")
        if self.gate_run_id != f"GATE-{expected.removeprefix(_AUTHORITY_PREFIX)[:24]}":
            _deny("invalid_gate_run_id")
        if not math.isfinite(self.issued_at) or not math.isfinite(self.expires_at):
            _deny("invalid_authority_time")
        if self.issued_at < 0 or self.expires_at <= self.issued_at:
            _deny("invalid_authority_time")

    @property
    def arena_lease(self) -> dict[str, Any]:
        return json.loads(self.arena_lease_json)

    @classmethod
    def create(
        cls,
        *,
        identity: VerifiedGateIdentity,
        policy: GatePolicyManifest,
        request: GateRunRequest,
        forge_result: Mapping[str, Any],
        arena_lease: ArenaLease,
        issued_at: float,
    ) -> GateAuthorityEnvelope:
        contract = dict(forge_result["contract"])
        lease_payload = arena_lease.to_dict()
        expiry = min(issued_at + request.lease_ttl_seconds, identity.expires_at)
        if expiry <= issued_at:
            _deny("identity_expires_before_lease")
        values = {
            "actor_ref": identity.actor_ref,
            "identity_basis_digest": _sha256(_identity_basis(identity)),
            "policy_id": policy.policy_id,
            "policy_digest": policy.policy_digest,
            "purpose_digest": request.purpose_digest,
            "forge_run_id": _text(forge_result["run_id"], "forge_run_id", limit=256),
            "forge_contract_id": _text(contract["contract_id"], "forge_contract_id", limit=256),
            "forge_contract_digest": _text(forge_result["contract_digest"], "forge_contract_digest", limit=256),
            "repository_digest": _sha256(contract["repository"]),
            "arena_lease_json": _canonical_json(lease_payload),
            "arena_lease_digest": _sha256(lease_payload),
            "capabilities": request.capabilities,
            "allowed_files": tuple(contract["allowed_files"]),
            "destinations": (request.destination,),
            "providers": (request.provider,),
            "models": (request.model,),
            "data_classes": request.data_classes,
            "egress_fields": request.egress_fields,
            "retention_classes": (request.retention_class,),
            "required_verifiers": policy.required_verifiers,
            "protocol": request.protocol,
            "max_payload_bytes": policy.max_payload_bytes,
            # Forge's context budget applies only to bounded context components.
            # Gate's egress ceiling covers the complete serialized turn wrapper.
            "max_token_estimate": policy.max_token_estimate,
            "max_output_tokens": request.max_output_tokens,
            "max_provider_calls": request.max_provider_calls,
            "nonce": request.nonce,
            "issued_at": float(issued_at),
            "expires_at": float(expiry),
            "human_review_required": True,
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "automatic_promotion": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "version": GATE_AUTHORITY_VERSION,
        }
        authority_id = _authority_id(values)
        return cls(
            authority_id=authority_id,
            gate_run_id=f"GATE-{authority_id.removeprefix(_AUTHORITY_PREFIX)[:24]}",
            **values,
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> GateAuthorityEnvelope:
        if not isinstance(value, Mapping):
            _deny("invalid_authority_envelope")
        raw = dict(value)
        expected = {field.name for field in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        if set(raw) != expected:
            _deny("invalid_authority_fields")
        return cls(
            authority_id=_text(raw["authority_id"], "authority_id", limit=256),
            gate_run_id=_text(raw["gate_run_id"], "gate_run_id", limit=256),
            actor_ref=_text(raw["actor_ref"], "actor_ref", limit=256),
            identity_basis_digest=_digest_text(raw["identity_basis_digest"], "identity_basis_digest"),
            policy_id=_text(raw["policy_id"], "policy_id", limit=256),
            policy_digest=_digest_text(raw["policy_digest"], "policy_digest"),
            purpose_digest=_digest_text(raw["purpose_digest"], "purpose_digest"),
            forge_run_id=_text(raw["forge_run_id"], "forge_run_id", limit=256),
            forge_contract_id=_text(raw["forge_contract_id"], "forge_contract_id", limit=256),
            forge_contract_digest=_digest_text(raw["forge_contract_digest"], "forge_contract_digest"),
            repository_digest=_digest_text(raw["repository_digest"], "repository_digest"),
            arena_lease_json=_text(raw["arena_lease_json"], "arena_lease_json", limit=1_000_000),
            arena_lease_digest=_digest_text(raw["arena_lease_digest"], "arena_lease_digest"),
            capabilities=_strings(raw["capabilities"], "capabilities", upper=True, sort=False),
            allowed_files=_strings(raw["allowed_files"], "allowed_files", sort=False),
            destinations=_strings(raw["destinations"], "destinations", sort=False),
            providers=_strings(raw["providers"], "providers", sort=False),
            models=_strings(raw["models"], "models", sort=False),
            data_classes=_strings(raw["data_classes"], "data_classes", sort=False),
            egress_fields=_strings(raw["egress_fields"], "egress_fields", sort=False),
            retention_classes=_strings(raw["retention_classes"], "retention_classes", sort=False),
            required_verifiers=_strings(raw["required_verifiers"], "required_verifiers", sort=False),
            protocol=_text(raw["protocol"], "protocol", limit=32).upper(),
            max_payload_bytes=_strict_int(raw["max_payload_bytes"], "max_payload_bytes", 1, 10_000_000),
            max_token_estimate=_strict_int(raw["max_token_estimate"], "max_token_estimate", 1, 2_500_000),
            max_output_tokens=_strict_int(raw["max_output_tokens"], "max_output_tokens", 128, 16_000),
            max_provider_calls=_strict_int(raw["max_provider_calls"], "max_provider_calls", 1, 128),
            nonce=_text(raw["nonce"], "nonce", limit=256),
            issued_at=_strict_float(raw["issued_at"], "issued_at", 0.0, 10_000_000_000.0),
            expires_at=_strict_float(raw["expires_at"], "expires_at", 0.0, 10_000_000_000.0),
            human_review_required=_strict_bool(raw["human_review_required"], "human_review_required"),
            production_mutation=_strict_bool(raw["production_mutation"], "production_mutation"),
            automatic_commit=_strict_bool(raw["automatic_commit"], "automatic_commit"),
            automatic_push=_strict_bool(raw["automatic_push"], "automatic_push"),
            automatic_pull_request=_strict_bool(raw["automatic_pull_request"], "automatic_pull_request"),
            automatic_merge=_strict_bool(raw["automatic_merge"], "automatic_merge"),
            automatic_promotion=_strict_bool(raw["automatic_promotion"], "automatic_promotion"),
            patch_authority=_text(raw["patch_authority"], "patch_authority", limit=256),
            vsa_patch_authority=_strict_bool(raw["vsa_patch_authority"], "vsa_patch_authority"),
            version=_text(raw["version"], "authority_version", limit=64),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for name in (
            "capabilities",
            "allowed_files",
            "destinations",
            "providers",
            "models",
            "data_classes",
            "egress_fields",
            "retention_classes",
            "required_verifiers",
        ):
            payload[name] = list(payload[name])
        return payload

    def egress_grant(self) -> GateEgressGrant:
        return GateEgressGrant(
            authority_id=self.authority_id,
            gate_run_id=self.gate_run_id,
            purpose_digest=self.purpose_digest,
            expires_at=self.expires_at,
            allowed_destinations=self.destinations,
            allowed_providers=self.providers,
            allowed_models=self.models,
            allowed_data_classes=self.data_classes,
            allowed_top_level_fields=self.egress_fields,
            allowed_retention_classes=self.retention_classes,
            max_payload_bytes=self.max_payload_bytes,
            max_token_estimate=self.max_token_estimate,
        )


class GateLeaseStore:
    """Durable operational lease state; canonical evidence remains GateAuditLedger."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS gate_leases (
                        gate_run_id TEXT PRIMARY KEY,
                        authority_id TEXT NOT NULL UNIQUE,
                        envelope_json TEXT NOT NULL,
                        envelope_digest TEXT NOT NULL,
                        status TEXT NOT NULL,
                        provider_calls_used INTEGER NOT NULL DEFAULT 0,
                        updated_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS gate_lease_transitions (
                        operation_id TEXT PRIMARY KEY,
                        gate_run_id TEXT NOT NULL,
                        from_status TEXT NOT NULL,
                        to_status TEXT NOT NULL,
                        operation_digest TEXT NOT NULL,
                        created_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS gate_provider_call_consumptions (
                        operation_id TEXT PRIMARY KEY,
                        gate_run_id TEXT NOT NULL,
                        operation_digest TEXT NOT NULL,
                        call_number INTEGER NOT NULL,
                        created_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS gate_prepare_nonces (
                        nonce_digest TEXT PRIMARY KEY,
                        actor_ref TEXT NOT NULL,
                        policy_id TEXT NOT NULL,
                        gate_run_id TEXT NOT NULL UNIQUE,
                        created_at REAL NOT NULL
                    );
                    """
                )
                columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(gate_leases)").fetchall()}
                if "provider_calls_used" not in columns:
                    connection.execute(
                        "ALTER TABLE gate_leases ADD COLUMN provider_calls_used INTEGER NOT NULL DEFAULT 0"
                    )
                self._backfill_nonce_index(connection)
        except sqlite3.Error as exc:
            raise GateError("lease_store_unavailable") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @staticmethod
    def _backfill_nonce_index(connection: sqlite3.Connection) -> None:
        """Fail closed while indexing leases created before nonce replay protection."""

        rows = connection.execute(
            "SELECT gate_run_id, envelope_json, envelope_digest, updated_at FROM gate_leases"
        ).fetchall()
        for row in rows:
            try:
                raw = json.loads(row["envelope_json"])
                if _sha256(raw) != row["envelope_digest"]:
                    _deny("lease_store_integrity")
                envelope = GateAuthorityEnvelope.from_mapping(raw)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise GateError("lease_store_integrity") from exc
            if envelope.gate_run_id != row["gate_run_id"]:
                _deny("lease_store_integrity")
            digest = _nonce_digest(envelope.actor_ref, envelope.policy_id, envelope.nonce)
            existing = connection.execute(
                "SELECT actor_ref, policy_id, gate_run_id FROM gate_prepare_nonces WHERE nonce_digest = ?",
                (digest,),
            ).fetchone()
            binding = (envelope.actor_ref, envelope.policy_id, envelope.gate_run_id)
            if existing is not None:
                recorded = (
                    str(existing["actor_ref"]),
                    str(existing["policy_id"]),
                    str(existing["gate_run_id"]),
                )
                if recorded != binding:
                    _deny("lease_store_integrity")
                continue
            connection.execute(
                "INSERT INTO gate_prepare_nonces VALUES (?, ?, ?, ?, ?)",
                (digest, *binding, float(row["updated_at"])),
            )

    def assert_nonce_available(self, actor_ref: str, policy_id: str, nonce: str) -> None:
        """Reject a previously issued actor/policy nonce before Forge preparation."""

        digest = _nonce_digest(actor_ref, policy_id, nonce)
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT actor_ref, policy_id FROM gate_prepare_nonces WHERE nonce_digest = ?",
                    (digest,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise GateError("lease_store_unavailable") from exc
        if row is not None:
            if str(row["actor_ref"]) != actor_ref or str(row["policy_id"]) != policy_id:
                _deny("lease_store_integrity")
            _deny("lease_nonce_replay")

    def issue(self, envelope: GateAuthorityEnvelope, *, operation_id: str, now: float) -> str:
        envelope.validate_integrity()
        encoded = _canonical_json(envelope.to_dict())
        digest = _sha256(envelope.to_dict())
        operation = _text(operation_id, "operation_id", limit=256)
        expected_operation = _lease_issue_operation_id(envelope.actor_ref, envelope.policy_id, envelope.nonce)
        if not hmac.compare_digest(operation, expected_operation):
            _deny("invalid_lease_issue_operation")
        nonce_digest = _nonce_digest(envelope.actor_ref, envelope.policy_id, envelope.nonce)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT envelope_digest, status FROM gate_leases WHERE gate_run_id = ?",
                    (envelope.gate_run_id,),
                ).fetchone()
                if existing is not None:
                    if existing["envelope_digest"] != digest:
                        _deny("lease_identity_collision")
                    connection.commit()
                    return str(existing["status"])
                nonce_row = connection.execute(
                    "SELECT actor_ref, policy_id, gate_run_id FROM gate_prepare_nonces WHERE nonce_digest = ?",
                    (nonce_digest,),
                ).fetchone()
                if nonce_row is not None:
                    binding = (
                        str(nonce_row["actor_ref"]),
                        str(nonce_row["policy_id"]),
                    )
                    if binding != (envelope.actor_ref, envelope.policy_id):
                        _deny("lease_store_integrity")
                    _deny("lease_nonce_replay")
                connection.execute(
                    "INSERT INTO gate_leases ("
                    "gate_run_id, authority_id, envelope_json, envelope_digest, "
                    "status, provider_calls_used, updated_at"
                    ") VALUES (?, ?, ?, ?, 'ACTIVE', 0, ?)",
                    (envelope.gate_run_id, envelope.authority_id, encoded, digest, float(now)),
                )
                operation_digest = _sha256(
                    {
                        "operation_id": operation,
                        "gate_run_id": envelope.gate_run_id,
                        "from": "NONE",
                        "to": "ACTIVE",
                    }
                )
                connection.execute(
                    "INSERT INTO gate_lease_transitions VALUES (?, ?, 'NONE', 'ACTIVE', ?, ?)",
                    (operation, envelope.gate_run_id, operation_digest, float(now)),
                )
                connection.execute(
                    "INSERT INTO gate_prepare_nonces VALUES (?, ?, ?, ?, ?)",
                    (
                        nonce_digest,
                        envelope.actor_ref,
                        envelope.policy_id,
                        envelope.gate_run_id,
                        float(now),
                    ),
                )
                connection.commit()
                return "ACTIVE"
        except GateError:
            raise
        except sqlite3.IntegrityError as exc:
            raise GateError("lease_operation_replay") from exc
        except sqlite3.Error as exc:
            raise GateError("lease_store_unavailable") from exc

    def get(self, gate_run_id: str) -> tuple[GateAuthorityEnvelope, str]:
        key = _text(gate_run_id, "gate_run_id", limit=256)
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT authority_id, envelope_json, envelope_digest, status "
                    "FROM gate_leases WHERE gate_run_id = ?",
                    (key,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise GateError("lease_store_unavailable") from exc
        if row is None:
            _deny("gate_run_not_found")
        try:
            raw = json.loads(row["envelope_json"])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GateError("lease_store_integrity") from exc
        if _sha256(raw) != row["envelope_digest"]:
            _deny("lease_store_integrity")
        try:
            envelope = GateAuthorityEnvelope.from_mapping(raw)
        except (GateError, KeyError, TypeError, ValueError) as exc:
            raise GateError("lease_store_integrity") from exc
        if envelope.gate_run_id != key or envelope.authority_id != row["authority_id"]:
            _deny("lease_store_integrity")
        status = str(row["status"])
        if status not in _LEASE_STATUSES:
            _deny("lease_store_integrity")
        return envelope, status

    def consume_provider_call(
        self,
        gate_run_id: str,
        *,
        max_provider_calls: int,
        operation_id: str,
        now: float,
    ) -> int:
        """Atomically consume one idempotent outbound-call allowance."""

        key = _text(gate_run_id, "gate_run_id", limit=256)
        maximum = _strict_int(max_provider_calls, "max_provider_calls", 1, 128)
        operation = _text(operation_id, "operation_id", limit=256)
        operation_digest = _sha256(
            {
                "operation_id": operation,
                "gate_run_id": key,
                "max_provider_calls": maximum,
            }
        )
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                replay = connection.execute(
                    "SELECT operation_digest, call_number FROM gate_provider_call_consumptions WHERE operation_id = ?",
                    (operation,),
                ).fetchone()
                if replay is not None:
                    if replay["operation_digest"] != operation_digest:
                        _deny("provider_call_operation_collision")
                    connection.commit()
                    return int(replay["call_number"])
                row = connection.execute(
                    "SELECT status, provider_calls_used FROM gate_leases WHERE gate_run_id = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    _deny("gate_run_not_found")
                if str(row["status"]) not in {"STARTING", "STARTED"}:
                    _deny("invalid_lease_state")
                used = int(row["provider_calls_used"])
                if used < 0 or used >= maximum:
                    _deny("provider_call_budget_exceeded")
                call_number = used + 1
                connection.execute(
                    "UPDATE gate_leases SET provider_calls_used = ?, updated_at = ? WHERE gate_run_id = ?",
                    (call_number, float(now), key),
                )
                connection.execute(
                    "INSERT INTO gate_provider_call_consumptions VALUES (?, ?, ?, ?, ?)",
                    (operation, key, operation_digest, call_number, float(now)),
                )
                connection.commit()
                return call_number
        except GateError:
            raise
        except (OverflowError, TypeError, ValueError) as exc:
            raise GateError("lease_store_integrity") from exc
        except sqlite3.Error as exc:
            raise GateError("lease_store_unavailable") from exc

    def provider_call_usage(self, gate_run_id: str) -> int:
        """Return the bounded operational call count for diagnostics/tests."""

        key = _text(gate_run_id, "gate_run_id", limit=256)
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT provider_calls_used FROM gate_leases WHERE gate_run_id = ?",
                    (key,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise GateError("lease_store_unavailable") from exc
        if row is None:
            _deny("gate_run_not_found")
        try:
            value = int(row["provider_calls_used"])
        except (OverflowError, TypeError, ValueError) as exc:
            raise GateError("lease_store_integrity") from exc
        if value < 0 or value > 128:
            _deny("lease_store_integrity")
        return value

    def transition(
        self,
        gate_run_id: str,
        *,
        expected_statuses: Sequence[str],
        new_status: str,
        operation_id: str,
        now: float,
    ) -> str:
        key = _text(gate_run_id, "gate_run_id", limit=256)
        expected = _strings(expected_statuses, "expected_statuses", upper=True)
        target = _text(new_status, "lease_status", limit=32).upper()
        if not set(expected).issubset(_LEASE_STATUSES) or target not in _LEASE_STATUSES:
            _deny("invalid_lease_transition")
        operation = _text(operation_id, "operation_id", limit=256)
        operation_digest = _sha256(
            {"operation_id": operation, "gate_run_id": key, "from": list(expected), "to": target}
        )
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                replay = connection.execute(
                    "SELECT operation_digest, to_status FROM gate_lease_transitions WHERE operation_id = ?",
                    (operation,),
                ).fetchone()
                if replay is not None:
                    if replay["operation_digest"] != operation_digest:
                        _deny("lease_operation_collision")
                    connection.commit()
                    return str(replay["to_status"])
                row = connection.execute("SELECT status FROM gate_leases WHERE gate_run_id = ?", (key,)).fetchone()
                if row is None:
                    _deny("gate_run_not_found")
                current = str(row["status"])
                if current not in expected:
                    _deny("invalid_lease_state")
                connection.execute(
                    "UPDATE gate_leases SET status = ?, updated_at = ? WHERE gate_run_id = ?",
                    (target, float(now), key),
                )
                connection.execute(
                    "INSERT INTO gate_lease_transitions VALUES (?, ?, ?, ?, ?, ?)",
                    (operation, key, current, target, operation_digest, float(now)),
                )
                connection.commit()
                return target
        except GateError:
            raise
        except sqlite3.Error as exc:
            raise GateError("lease_store_unavailable") from exc


class AuraGateRuntime:
    """One policy/lease/audit boundary around an injected AuraForgeRuntime."""

    def __init__(
        self,
        *,
        forge: AuraForgeRuntime,
        policies: Sequence[GatePolicyManifest],
        lease_store: GateLeaseStore,
        audit: GateAuditLedger,
        clock: Any = time.time,
    ) -> None:
        if not isinstance(forge, AuraForgeRuntime):
            _deny("invalid_forge_runtime")
        if not callable(clock):
            _deny("invalid_clock")
        normalized_policies = [GatePolicyManifest.from_mapping(policy.to_dict()) for policy in policies]
        policy_map = {policy.policy_id: policy for policy in normalized_policies}
        if not policy_map or len(policy_map) != len(normalized_policies):
            _deny("invalid_policy_registry")
        self.forge = forge
        self.policies = policy_map
        self.lease_store = lease_store
        self.audit = audit
        self.clock = clock

    @staticmethod
    def _error(code: str, *, stage: str) -> dict[str, Any]:
        return {
            "ok": False,
            "version": GATE_VERSION,
            "error": code,
            "stage": stage,
            "human_review_required": True,
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "automatic_promotion": False,
        }

    def _now(self) -> float:
        return _strict_float(self.clock(), "evaluation_time", 0.0, 10_000_000_000.0)

    @staticmethod
    def _verify_identity(identity: VerifiedGateIdentity, now: float) -> None:
        if type(identity) is not VerifiedGateIdentity:
            _deny("verified_identity_required")
        if now < identity.issued_at or now >= identity.expires_at:
            _deny("verified_identity_inactive")

    @staticmethod
    def _policy_allows(
        policy: GatePolicyManifest,
        identity: VerifiedGateIdentity,
        request: GateRunRequest,
    ) -> None:
        checks = (
            (request.purpose_digest in policy.allowed_purpose_digests, "purpose_not_allowed"),
            (set(request.capabilities).issubset(policy.allowed_capabilities), "capability_not_allowed"),
            (request.target_file in policy.allowed_files, "file_not_allowed"),
            (request.destination in policy.allowed_destinations, "destination_not_allowed"),
            (request.provider in policy.allowed_providers, "provider_not_allowed"),
            (request.model in policy.allowed_models, "model_not_allowed"),
            (set(request.data_classes).issubset(policy.allowed_data_classes), "data_class_not_allowed"),
            (set(request.egress_fields).issubset(policy.allowed_egress_fields), "egress_field_not_allowed"),
            (request.retention_class in policy.allowed_retention_classes, "retention_not_allowed"),
            (request.protocol in policy.allowed_protocols, "protocol_not_allowed"),
            (set(policy.required_roles).issubset(identity.roles), "required_role_missing"),
            (set(policy.required_groups).issubset(identity.groups), "required_group_missing"),
            (request.lease_ttl_seconds <= policy.max_lease_ttl_seconds, "lease_ttl_exceeded"),
            (request.max_context_tokens <= policy.max_context_tokens, "context_budget_exceeded"),
            (request.max_output_tokens <= policy.max_output_tokens, "output_budget_exceeded"),
            (request.max_turns <= policy.max_turns, "turn_budget_exceeded"),
            (request.max_local_repairs <= policy.max_local_repairs, "repair_budget_exceeded"),
            (request.max_provider_calls <= policy.max_provider_calls, "provider_call_budget_exceeded"),
        )
        for allowed, code in checks:
            if not allowed:
                _deny(code)
        if set(request.egress_fields) & _BOUNDED_CONTEXT_EGRESS_FIELDS and (
            "BOUNDED_SOURCE_CONTEXT" not in request.data_classes
        ):
            _deny("egress_data_class_binding_missing")

    @staticmethod
    def _policy_allows_envelope(
        policy: GatePolicyManifest,
        envelope: GateAuthorityEnvelope,
    ) -> None:
        """Revalidate persisted operational state against immutable policy authority."""

        checks = (
            (envelope.purpose_digest in policy.allowed_purpose_digests, "policy_drift"),
            (set(envelope.capabilities).issubset(policy.allowed_capabilities), "policy_drift"),
            (set(envelope.allowed_files).issubset(policy.allowed_files), "policy_drift"),
            (set(envelope.destinations).issubset(policy.allowed_destinations), "policy_drift"),
            (set(envelope.providers).issubset(policy.allowed_providers), "policy_drift"),
            (set(envelope.models).issubset(policy.allowed_models), "policy_drift"),
            (set(envelope.data_classes).issubset(policy.allowed_data_classes), "policy_drift"),
            (set(envelope.egress_fields).issubset(policy.allowed_egress_fields), "policy_drift"),
            (
                set(envelope.retention_classes).issubset(policy.allowed_retention_classes),
                "policy_drift",
            ),
            (envelope.protocol in policy.allowed_protocols, "policy_drift"),
            (envelope.required_verifiers == policy.required_verifiers, "policy_drift"),
            (envelope.max_payload_bytes <= policy.max_payload_bytes, "policy_drift"),
            (envelope.max_token_estimate <= policy.max_token_estimate, "policy_drift"),
            (envelope.max_output_tokens <= policy.max_output_tokens, "policy_drift"),
            (envelope.max_provider_calls <= policy.max_provider_calls, "policy_drift"),
            (
                envelope.expires_at - envelope.issued_at <= policy.max_lease_ttl_seconds,
                "policy_drift",
            ),
        )
        for allowed, code in checks:
            if not allowed:
                _deny(code)
        if set(envelope.egress_fields) & _BOUNDED_CONTEXT_EGRESS_FIELDS and (
            "BOUNDED_SOURCE_CONTEXT" not in envelope.data_classes
        ):
            _deny("policy_drift")

    def prepare(
        self,
        identity: VerifiedGateIdentity,
        value: GateRunRequest | Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            now = self._now()
            self._verify_identity(identity, now)
            request = GateRunRequest.from_mapping(value.to_dict() if isinstance(value, GateRunRequest) else value)
            policy = self.policies.get(request.policy_id)
            if policy is None:
                _deny("policy_not_found")
            self._policy_allows(policy, identity, request)
            self.lease_store.assert_nonce_available(identity.actor_ref, policy.policy_id, request.nonce)
            forge_result = self.forge.prepare(request.to_forge_request(required_gates=policy.required_verifiers))
            if not forge_result.get("ok"):
                return self._error("forge_prepare_denied", stage="PREPARE")
            contract = dict(forge_result.get("contract") or {})
            if validate_forge_contract(contract):
                _deny("invalid_forge_contract")
            if forge_contract_digest(contract) != forge_result.get("contract_digest"):
                _deny("forge_contract_digest_mismatch")
            if not set(contract.get("allowed_files") or []).issubset(policy.allowed_files):
                _deny("forge_file_expansion")
            if tuple(contract.get("required_gates") or ()) != policy.required_verifiers:
                _deny("forge_verifier_drift")
            worker = dict(contract.get("worker_contract") or {})
            if worker.get("provider") != request.provider or worker.get("model") != request.model:
                _deny("forge_worker_expansion")
            arena_lease = ArenaLease.create(
                domain="code",
                capsule_id=str(contract["contract_id"]),
                holder=identity.actor_ref,
                regions=[{"path": path, "authority": "exact_contract_only"} for path in contract["allowed_files"]],
                allowed_actions=list(request.capabilities),
                forbidden_actions=[
                    "COMMIT",
                    "PUSH",
                    "PULL_REQUEST",
                    "MERGE",
                    "RELEASE",
                    "PROMOTE_POLICY",
                    "PRODUCTION_MUTATION",
                ],
                metadata={
                    "policy_id": policy.policy_id,
                    "purpose_digest": request.purpose_digest,
                    "forge_contract_id": contract["contract_id"],
                },
            )
            envelope = GateAuthorityEnvelope.create(
                identity=identity,
                policy=policy,
                request=request,
                forge_result=forge_result,
                arena_lease=arena_lease,
                issued_at=now,
            )
            issue_operation_id = _lease_issue_operation_id(envelope.actor_ref, envelope.policy_id, envelope.nonce)
            audit_result = self._record(
                envelope,
                identity,
                operation_id=issue_operation_id,
                phase="PRE_ACTION",
                action="LEASE_ISSUE",
                decision="ALLOW",
            )
            status = self.lease_store.issue(
                envelope,
                operation_id=issue_operation_id,
                now=now,
            )
            return {
                "ok": True,
                "version": GATE_VERSION,
                "gate_run_id": envelope.gate_run_id,
                "authority_id": envelope.authority_id,
                "status": status,
                "expires_at": envelope.expires_at,
                "forge_contract_id": envelope.forge_contract_id,
                "forge_contract_digest": envelope.forge_contract_digest,
                "policy_id": envelope.policy_id,
                "purpose_digest": envelope.purpose_digest,
                "audit": audit_result,
                "human_review_required": True,
                "production_mutation": False,
            }
        except (GateError, GateAuditError, GateEgressDenied) as exc:
            return self._error(getattr(exc, "code", "gate_prepare_denied"), stage="PREPARE")

    def _authorize(
        self,
        identity: VerifiedGateIdentity,
        gate_run_id: str,
        *,
        capabilities: Sequence[str],
        statuses: Sequence[str],
    ) -> tuple[GateAuthorityEnvelope, str, GatePolicyManifest, float]:
        now = self._now()
        self._verify_identity(identity, now)
        envelope, status = self.lease_store.get(gate_run_id)
        if status not in statuses:
            _deny("invalid_lease_state")
        policy = self.policies.get(envelope.policy_id)
        if policy is None or policy.policy_digest != envelope.policy_digest:
            _deny("policy_drift")
        self._policy_allows_envelope(policy, envelope)
        if envelope.actor_ref != identity.actor_ref:
            _deny("actor_mismatch")
        if envelope.identity_basis_digest != _sha256(_identity_basis(identity)):
            _deny("identity_authority_mismatch")
        if not set(policy.required_roles).issubset(identity.roles) or not set(policy.required_groups).issubset(
            identity.groups
        ):
            _deny("identity_entitlement_mismatch")
        lease = envelope.arena_lease
        verifier = envelope.required_verifiers[0] if envelope.required_verifiers else ""
        self.audit.require_authority_issuance(
            operation_id=_lease_issue_operation_id(envelope.actor_ref, envelope.policy_id, envelope.nonce),
            actor_id=envelope.actor_ref,
            purpose_digest=envelope.purpose_digest,
            policy_id=envelope.policy_id,
            policy_digest=envelope.policy_digest,
            lease_id=str(lease["lease_id"]),
            protocol=envelope.protocol,
            destination=envelope.destinations[0],
            verifier_id=verifier,
            arena_id=str(lease["capsule_id"]),
            objective_id=envelope.gate_run_id,
            evidence_refs=(
                envelope.authority_id,
                envelope.forge_contract_id,
                envelope.forge_contract_digest,
            ),
        )
        if now >= envelope.expires_at and status not in _TERMINAL_STATUSES:
            self._record(
                envelope,
                identity,
                operation_id=f"EXPIRE-{envelope.gate_run_id}",
                phase="PRE_ACTION",
                action="LEASE_EXPIRE",
                decision="ALLOW",
            )
            self.lease_store.transition(
                envelope.gate_run_id,
                expected_statuses=(status,),
                new_status="EXPIRED",
                operation_id=f"EXPIRE-{envelope.gate_run_id}",
                now=now,
            )
            _deny("lease_expired")
        required = {item.upper() for item in capabilities}
        if not required.issubset(envelope.capabilities):
            _deny("capability_not_leased")
        return envelope, status, policy, now

    def start(self, identity: VerifiedGateIdentity, gate_run_id: str) -> dict[str, Any]:
        try:
            envelope, _status, _policy, now = self._authorize(
                identity,
                gate_run_id,
                capabilities=("FORGE_START", "READ.REPOSITORY", "PROPOSE.PATCH"),
                statuses=("ACTIVE",),
            )
            self._record(
                envelope,
                identity,
                operation_id=f"START-{envelope.gate_run_id}",
                phase="PRE_ACTION",
                action="FORGE_START",
                decision="ALLOW",
            )
            self.lease_store.transition(
                envelope.gate_run_id,
                expected_statuses=("ACTIVE",),
                new_status="STARTING",
                operation_id=f"START-{envelope.gate_run_id}",
                now=now,
            )
            result = self.forge.start_prepared(
                envelope.forge_run_id,
                expected_contract_id=envelope.forge_contract_id,
                expected_contract_digest=envelope.forge_contract_digest,
            )
            if not result.get("ok"):
                self._revoke_internal(identity, envelope, "FORGE_START_DENIED", now)
                return self._error("forge_start_denied", stage="START")
            try:
                governed = self._govern_egress(identity, envelope, dict(result.get("turn") or {}), now)
            except (GateError, GateAuditError, GateEgressDenied):
                self._revoke_internal(identity, envelope, "EGRESS_DENIED", now)
                raise
            self.lease_store.transition(
                envelope.gate_run_id,
                expected_statuses=("STARTING",),
                new_status="STARTED",
                operation_id=f"STARTED-{envelope.gate_run_id}",
                now=now,
            )
            return {
                "ok": True,
                "version": GATE_VERSION,
                "gate_run_id": envelope.gate_run_id,
                "status": "STARTED",
                "turn": governed.decoded_payload(),
                "egress_capsule": governed.capsule.to_dict(),
                "human_review_required": True,
                "production_mutation": False,
            }
        except (GateError, GateAuditError, GateEgressDenied) as exc:
            return self._error(getattr(exc, "code", "gate_start_denied"), stage="START")

    def submit(
        self,
        identity: VerifiedGateIdentity,
        gate_run_id: str,
        *,
        turn_id: str,
        response: str,
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            envelope, _status, _policy, now = self._authorize(
                identity,
                gate_run_id,
                capabilities=(
                    "FORGE_SUBMIT",
                    "READ.REPOSITORY",
                    "PROPOSE.PATCH",
                    "RUN.TESTS",
                ),
                statuses=("STARTED",),
            )
            turn = _text(turn_id, "turn_id", limit=256)
            answer = _text(response, "model_response", limit=envelope.max_payload_bytes)
            if (len(answer.encode("utf-8")) + 3) // 4 > envelope.max_output_tokens:
                _deny("output_budget_exceeded")
            usage = self._safe_usage(provider_usage or {})
            usage_error = self._usage_budget_error(envelope, usage)
            if usage_error:
                self._revoke_internal(identity, envelope, usage_error.upper(), now)
                _deny(usage_error)
            operation_digest = hashlib.sha256(f"{turn}\x00{answer}".encode()).hexdigest()[:32]
            self._record(
                envelope,
                identity,
                operation_id=f"SUBMIT-{envelope.gate_run_id}-{operation_digest}",
                phase="PRE_ACTION",
                action="FORGE_SUBMIT",
                decision="ALLOW",
            )
            result = self.forge.submit(
                run_id=envelope.forge_run_id,
                turn_id=turn,
                response=answer,
                provider_usage=usage,
            )
            if not result.get("ok"):
                self._revoke_internal(identity, envelope, "FORGE_SUBMIT_DENIED", now)
                return self._error("forge_submit_denied", stage="SUBMIT")
            status = str(result.get("status") or "")
            governed: GovernedEgress | None = None
            if isinstance(result.get("turn"), Mapping) and result.get("turn"):
                try:
                    governed = self._govern_egress(identity, envelope, dict(result["turn"]), now)
                except (GateError, GateAuditError, GateEgressDenied):
                    self._revoke_internal(identity, envelope, "EGRESS_DENIED", now)
                    raise
            if status == REVIEW_READY_STATUS:
                self._record(
                    envelope,
                    identity,
                    operation_id=f"DISSOLVE-{envelope.gate_run_id}",
                    phase="PRE_ACTION",
                    action="LEASE_DISSOLVE",
                    decision="ALLOW",
                    dissolution_reason="HUMAN_REVIEW_READY",
                )
                self.lease_store.transition(
                    envelope.gate_run_id,
                    expected_statuses=("STARTED",),
                    new_status="DISSOLVED",
                    operation_id=f"DISSOLVE-{envelope.gate_run_id}",
                    now=now,
                )
            response_payload: dict[str, Any] = {
                "ok": True,
                "version": GATE_VERSION,
                "gate_run_id": envelope.gate_run_id,
                "status": "DISSOLVED" if status == REVIEW_READY_STATUS else "STARTED",
                "forge_status": status,
                "decision_eligible": bool(
                    status == REVIEW_READY_STATUS
                    and dict(result.get("human_review_packet") or {}).get("decision_eligible") is True
                ),
                "human_review_required": True,
                "production_mutation": False,
                "automatic_promotion": False,
            }
            if governed is not None:
                response_payload["turn"] = governed.decoded_payload()
                response_payload["egress_capsule"] = governed.capsule.to_dict()
            return response_payload
        except (GateError, GateAuditError, GateEgressDenied) as exc:
            return self._error(getattr(exc, "code", "gate_submit_denied"), stage="SUBMIT")

    def status(self, identity: VerifiedGateIdentity, gate_run_id: str) -> dict[str, Any]:
        try:
            envelope, status, _policy, now = self._authorize(
                identity,
                gate_run_id,
                capabilities=("FORGE_STATUS",),
                statuses=("ACTIVE", "STARTING", "STARTED", "DISSOLVED", "REVOKED", "EXPIRED"),
            )
            if status in _TERMINAL_STATUSES:
                return {
                    "ok": True,
                    "version": GATE_VERSION,
                    "gate_run_id": envelope.gate_run_id,
                    "authority_id": envelope.authority_id,
                    "status": status,
                    "forge_status": None,
                    "decision_eligible": status == "DISSOLVED",
                    "expires_at": envelope.expires_at,
                    "human_review_required": True,
                    "production_mutation": False,
                    "automatic_promotion": False,
                }
            forge_status = self.forge.status(envelope.forge_run_id)
            if forge_status.get("ok") is not True:
                self._revoke_internal(identity, envelope, "FORGE_STATE_UNAVAILABLE", now)
                return self._error("forge_state_unavailable", stage="STATUS")
            return {
                "ok": True,
                "version": GATE_VERSION,
                "gate_run_id": envelope.gate_run_id,
                "authority_id": envelope.authority_id,
                "status": status,
                "forge_status": forge_status.get("status"),
                "decision_eligible": forge_status.get("decision_eligible") is True,
                "expires_at": envelope.expires_at,
                "human_review_required": True,
                "production_mutation": False,
                "automatic_promotion": False,
            }
        except (GateError, GateAuditError) as exc:
            return self._error(getattr(exc, "code", "gate_status_denied"), stage="STATUS")

    def revoke(
        self,
        identity: VerifiedGateIdentity,
        gate_run_id: str,
        *,
        reason_code: str,
    ) -> dict[str, Any]:
        try:
            envelope, status, _policy, now = self._authorize(
                identity,
                gate_run_id,
                capabilities=("FORGE_REVOKE",),
                statuses=("ACTIVE", "STARTING", "STARTED"),
            )
            reason = _text(reason_code, "revocation_reason", limit=128).upper()
            reason_digest = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:24]
            self._record(
                envelope,
                identity,
                operation_id=f"REVOKE-{envelope.gate_run_id}-{reason_digest}",
                phase="PRE_ACTION",
                action="LEASE_REVOKE",
                decision="ALLOW",
                revocation_reason=reason,
            )
            self.lease_store.transition(
                envelope.gate_run_id,
                expected_statuses=(status,),
                new_status="REVOKED",
                operation_id=f"REVOKE-{envelope.gate_run_id}-{reason_digest}",
                now=now,
            )
            return {
                "ok": True,
                "version": GATE_VERSION,
                "gate_run_id": envelope.gate_run_id,
                "status": "REVOKED",
                "human_review_required": True,
                "production_mutation": False,
            }
        except (GateError, GateAuditError) as exc:
            return self._error(getattr(exc, "code", "gate_revoke_denied"), stage="REVOKE")

    def export_siem(
        self,
        identity: VerifiedGateIdentity,
        output_path: str | Path,
    ) -> dict[str, Any]:
        try:
            now = self._now()
            self._verify_identity(identity, now)
            if "aura-gate-auditor" not in identity.roles:
                _deny("audit_role_required")
            result = self.audit.export_siem(output_path)
            return {"ok": True, "version": GATE_VERSION, **result}
        except (GateError, GateAuditError) as exc:
            return self._error(getattr(exc, "code", "gate_export_denied"), stage="EXPORT")

    def _record(
        self,
        envelope: GateAuthorityEnvelope,
        identity: VerifiedGateIdentity,
        *,
        operation_id: str,
        phase: str,
        action: str,
        decision: str,
        revocation_reason: str = "",
        dissolution_reason: str = "",
        evidence_refs: Sequence[str] = (),
    ) -> dict[str, Any]:
        lease = envelope.arena_lease
        verifier = envelope.required_verifiers[0] if envelope.required_verifiers else ""
        return self.audit.record(
            operation_id=operation_id,
            phase=phase,
            action=action,
            actor_id=identity.actor_ref,
            actor_type=ActorType.HUMAN,
            purpose_digest=envelope.purpose_digest,
            policy_id=envelope.policy_id,
            policy_digest=envelope.policy_digest,
            lease_id=str(lease["lease_id"]),
            decision=decision,
            protocol=envelope.protocol,
            destination=envelope.destinations[0],
            verifier_id=verifier,
            verifier_status="REQUIRED" if verifier else "",
            cost_class="BOUNDED",
            revocation_reason=revocation_reason,
            dissolution_reason=dissolution_reason,
            arena_id=str(lease["capsule_id"]),
            objective_id=envelope.gate_run_id,
            evidence_refs=(
                envelope.authority_id,
                envelope.forge_contract_id,
                envelope.forge_contract_digest,
                *evidence_refs,
            ),
        )

    def _govern_egress(
        self,
        identity: VerifiedGateIdentity,
        envelope: GateAuthorityEnvelope,
        payload: dict[str, Any],
        now: float,
    ) -> GovernedEgress:
        governed = GateEgressGovernor.compile(
            envelope.egress_grant(),
            payload,
            purpose_digest=envelope.purpose_digest,
            destination=envelope.destinations[0],
            provider=envelope.providers[0],
            model=envelope.models[0],
            data_classes=envelope.data_classes,
            retention_class=envelope.retention_classes[0],
            now=now,
        )
        operation_id = f"EGRESS-{governed.capsule.capsule_id[-48:]}"
        self.lease_store.consume_provider_call(
            envelope.gate_run_id,
            max_provider_calls=envelope.max_provider_calls,
            operation_id=operation_id,
            now=now,
        )
        self._record(
            envelope,
            identity,
            operation_id=operation_id,
            phase="PRE_ACTION",
            action="EGRESS_RELEASE",
            decision="ALLOW",
            evidence_refs=(governed.capsule.capsule_id, governed.capsule.payload_digest),
        )
        return governed

    def _revoke_internal(
        self,
        identity: VerifiedGateIdentity,
        envelope: GateAuthorityEnvelope,
        reason: str,
        now: float,
    ) -> None:
        self._record(
            envelope,
            identity,
            operation_id=f"REVOKE-{envelope.gate_run_id}-{reason}",
            phase="PRE_ACTION",
            action="LEASE_REVOKE",
            decision="ALLOW",
            revocation_reason=reason,
        )
        _current_envelope, current = self.lease_store.get(envelope.gate_run_id)
        if current not in _TERMINAL_STATUSES:
            self.lease_store.transition(
                envelope.gate_run_id,
                expected_statuses=(current,),
                new_status="REVOKED",
                operation_id=f"REVOKE-{envelope.gate_run_id}-{reason}",
                now=now,
            )

    @staticmethod
    def _safe_usage(value: Mapping[str, Any]) -> dict[str, int | float]:
        if not isinstance(value, Mapping):
            _deny("invalid_provider_usage")
        allowed = {"input_tokens", "output_tokens", "total_tokens", "cost_usd", "latency_ms"}
        if not set(value).issubset(allowed):
            _deny("invalid_provider_usage")
        result: dict[str, int | float] = {}
        for key, item in value.items():
            if key.endswith("tokens"):
                result[key] = _strict_int(item, "provider_usage", 0, 100_000_000)
            else:
                result[key] = _strict_float(item, "provider_usage", 0.0, 1_000_000_000.0)
        return result

    @staticmethod
    def _usage_budget_error(
        envelope: GateAuthorityEnvelope,
        usage: Mapping[str, int | float],
    ) -> str:
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
        if type(input_tokens) is int and input_tokens > envelope.max_token_estimate:
            return "provider_input_usage_exceeded"
        if type(output_tokens) is int and output_tokens > envelope.max_output_tokens:
            return "provider_output_usage_exceeded"
        if (
            type(input_tokens) is int
            and type(output_tokens) is int
            and type(total_tokens) is int
            and total_tokens != input_tokens + output_tokens
        ):
            return "provider_total_usage_inconsistent"
        return ""


__all__ = [
    "GATE_AUTHORITY_VERSION",
    "GATE_POLICY_VERSION",
    "GATE_VERSION",
    "AuraGateRuntime",
    "GateAuthorityEnvelope",
    "GateError",
    "GateLeaseStore",
    "GatePolicyManifest",
    "GateRunRequest",
    "gate_purpose_digest",
]
