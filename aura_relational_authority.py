"""Domain-neutral, action-bound relational authority contracts for AuraOS.

Planning may propose and tools may act within leases, but consequential authority
belongs to verified people and communities. These immutable contracts bind
authority to exact action digests, preserve dissent, enforce delegation and
quorum rules, and remain proposal-only. They never execute tools, patch code,
commit, merge, promote policy, or make civic decisions.

The module is stdlib-only. External identity, attestation, consent, and checkpoint
references are treated as opaque references and must be supplied through trusted
reference sets by the caller. Hashes prove content identity; they do not prove
actor authenticity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json
import math
import re
import time
from typing import Any, Iterable, Mapping, Sequence


AUTHORITY_CONTRACTS_VERSION = "AURA_RELATIONAL_AUTHORITY_V1"
SCHEMA_VERSION = "1.0"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
PROPOSAL_ONLY = True
GENESIS_CHAIN_DIGEST = "GENESIS"
DEFAULT_RATIONALE_LIMIT = 240


class AttestationDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"


class RiskClass(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class GovernanceFunction(str, Enum):
    PROPOSE = "PROPOSE"
    VERIFY = "VERIFY"
    GUARD = "GUARD"
    MEDIATE = "MEDIATE"
    APPROVE = "APPROVE"
    RECALL = "RECALL"
    REVIEW = "REVIEW"


_SECRET_PATTERNS = (
    re.compile(
        r"""(?ix)
        ["']?
        (?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|
           authorization|secret|password|private[_-]?key|token|
           [a-z0-9_.-]+[_-]token)
        ["']?\s*[:=]\s*
        (?:(?:bearer|basic)\s+)?
        (?:
            "(?:\\.|[^"\\])*"
          | '(?:\\.|[^'\\])*'
          | [^\s,{}&;]+
        )
        """
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=%\-]+"),
    re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/=]+"),
    re.compile(
        r"(?is)-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?"
        r"-----END [^-\r\n]*PRIVATE KEY-----"
    ),
    re.compile(r"\bsk-[A-Za-z0-9._~+/=%\-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return _canonicalize(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
        }
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonicalize(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite floats are not permitted")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_digest(value: Any, *, digest_size: int = 16) -> str:
    if not 1 <= int(digest_size) <= 64:
        raise ValueError("digest_size must be between 1 and 64 bytes")
    return hashlib.blake2b(
        canonical_json(value).encode("utf-8"), digest_size=int(digest_size)
    ).hexdigest()


def stable_id(prefix: str, value: Any, *, digest_size: int = 12) -> str:
    clean = "".join(
        ch if ch.isalnum() or ch in "-_" else "-"
        for ch in str(prefix).strip().lower()
    )
    if not clean:
        raise ValueError("stable_id prefix must not be empty")
    return f"{clean}_{stable_digest(value, digest_size=digest_size)}"


def redact_secrets(value: Any) -> str:
    redacted = str(value)
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _required(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _bounded(
    value: Any,
    field_name: str,
    *,
    limit: int = DEFAULT_RATIONALE_LIMIT,
    required: bool = True,
) -> str:
    normalized = " ".join(str(value or "").split())
    if required and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) > int(limit):
        raise ValueError(f"{field_name} exceeds {limit} characters")
    return redact_secrets(normalized)


def _timestamp(value: Any, field_name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    return number


def _now(value: float | None = None) -> float:
    return time.time() if value is None else _timestamp(value, "now")


def _enum_value(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:
    raw = value.value if isinstance(value, Enum) else str(value).upper()
    permitted = {item.value for item in enum_type}
    if raw not in permitted:
        raise ValueError(f"unknown {field_name}: {raw}")
    return raw


def _strict_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _normalized_strings(
    values: Iterable[Any],
    field_name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(sorted({_required(item, field_name) for item in values}))
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _trusted_set(values: Iterable[Any], field_name: str) -> frozenset[str]:
    trusted = frozenset(str(item).strip() for item in values if str(item).strip())
    if not trusted:
        raise ValueError(f"{field_name} must contain at least one verified reference")
    return trusted


def _normalize_role_pair(pair: Sequence[Any]) -> tuple[str, str]:
    if len(pair) != 2:
        raise ValueError("separation-of-duties pairs must contain exactly two roles")
    first = _required(pair[0], "separation role").upper()
    second = _required(pair[1], "separation role").upper()
    if first == second:
        raise ValueError("separation-of-duties roles must be different")
    return tuple(sorted((first, second)))


def _canonical_payload(instance: Any, *, exclude: Iterable[str]) -> dict[str, Any]:
    data = asdict(instance)
    for key in exclude:
        data.pop(key, None)
    return data


@dataclass(frozen=True)
class AuthorityGrant:
    grant_id: str
    grant_digest: str
    principal_id: str
    authorized_functional_roles: tuple[str, ...]
    policy_scopes: tuple[str, ...]
    capability_scopes: tuple[str, ...]
    valid_from: float
    expires_at: float
    maximum_delegation_depth: int
    current_delegation_depth: int
    parent_grant_ref: str
    externally_verified_authority_ref: str
    schema_version: str = SCHEMA_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def create(
        cls,
        *,
        principal_id: str,
        authorized_functional_roles: Iterable[str],
        policy_scopes: Iterable[str],
        capability_scopes: Iterable[str],
        valid_from: float,
        expires_at: float,
        maximum_delegation_depth: int = 0,
        current_delegation_depth: int = 0,
        parent_grant: "AuthorityGrant | None" = None,
        parent_grant_ref: str = "",
        externally_verified_authority_ref: str,
        verified_authority_refs: Iterable[str],
        now: float | None = None,
    ) -> "AuthorityGrant":
        current_time = _now(now)
        trusted = _trusted_set(verified_authority_refs, "verified_authority_refs")
        verification_ref = _required(
            externally_verified_authority_ref,
            "externally_verified_authority_ref",
        )
        if verification_ref not in trusted:
            raise ValueError("authority verification reference is not externally trusted")

        start = _timestamp(valid_from, "valid_from")
        expiry = _timestamp(expires_at, "expires_at")
        if expiry <= start:
            raise ValueError("expires_at must be greater than valid_from")
        if expiry <= current_time:
            raise ValueError("expired grants are not permitted")

        maximum = int(maximum_delegation_depth)
        depth = int(current_delegation_depth)
        if maximum < 0 or depth < 0:
            raise ValueError("delegation depths must be non-negative")
        if depth > maximum:
            raise ValueError("current delegation depth exceeds maximum")

        roles = _normalized_strings(
            (str(item).upper() for item in authorized_functional_roles),
            "authorized_functional_roles",
        )
        policies = _normalized_strings(policy_scopes, "policy_scopes")
        capabilities = _normalized_strings(capability_scopes, "capability_scopes")

        supplied_parent_ref = str(parent_grant_ref or "").strip()
        if parent_grant is None:
            if supplied_parent_ref:
                raise ValueError("parent grant object is required for delegated authority")
            if depth != 0:
                raise ValueError("root grants must have delegation depth zero")
            resolved_parent_ref = ""
        else:
            parent_grant.validate(
                now=current_time,
                verified_authority_refs=trusted,
            )
            parent_grant._validate_identity()
            resolved_parent_ref = parent_grant.grant_id
            if supplied_parent_ref and supplied_parent_ref != resolved_parent_ref:
                raise ValueError("parent_grant_ref does not match parent grant")
            if depth != parent_grant.current_delegation_depth + 1:
                raise ValueError("delegation depth must advance exactly one level")
            if depth > parent_grant.maximum_delegation_depth:
                raise ValueError("parent grant delegation depth exceeded")
            if maximum > parent_grant.maximum_delegation_depth:
                raise ValueError("child maximum delegation depth exceeds parent")
            if not set(roles).issubset(parent_grant.authorized_functional_roles):
                raise ValueError("child roles exceed parent grant")
            if not set(policies).issubset(parent_grant.policy_scopes):
                raise ValueError("child policy scopes exceed parent grant")
            if not set(capabilities).issubset(parent_grant.capability_scopes):
                raise ValueError("child capability scopes exceed parent grant")
            if start < parent_grant.valid_from or expiry > parent_grant.expires_at:
                raise ValueError("child validity window exceeds parent grant")

        payload = {
            "principal_id": _required(principal_id, "principal_id"),
            "authorized_functional_roles": roles,
            "policy_scopes": policies,
            "capability_scopes": capabilities,
            "valid_from": start,
            "expires_at": expiry,
            "maximum_delegation_depth": maximum,
            "current_delegation_depth": depth,
            "parent_grant_ref": resolved_parent_ref,
            "externally_verified_authority_ref": verification_ref,
            "schema_version": SCHEMA_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        digest = stable_digest(payload)
        return cls(
            grant_id=stable_id("authority-grant", payload),
            grant_digest=digest,
            **payload,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        verified_authority_refs: Iterable[str],
        now: float | None = None,
    ) -> "AuthorityGrant":
        data = dict(value)
        grant = cls(
            grant_id=_required(data.get("grant_id"), "grant_id"),
            grant_digest=_required(data.get("grant_digest"), "grant_digest"),
            principal_id=_required(data.get("principal_id"), "principal_id"),
            authorized_functional_roles=tuple(data.get("authorized_functional_roles", ())),
            policy_scopes=tuple(data.get("policy_scopes", ())),
            capability_scopes=tuple(data.get("capability_scopes", ())),
            valid_from=float(data.get("valid_from")),
            expires_at=float(data.get("expires_at")),
            maximum_delegation_depth=int(data.get("maximum_delegation_depth", 0)),
            current_delegation_depth=int(data.get("current_delegation_depth", 0)),
            parent_grant_ref=str(data.get("parent_grant_ref", "")),
            externally_verified_authority_ref=_required(
                data.get("externally_verified_authority_ref"),
                "externally_verified_authority_ref",
            ),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
            proposal_only=_strict_bool(data.get("proposal_only", True), "proposal_only"),
            patch_authority=str(data.get("patch_authority", PATCH_AUTHORITY)),
            vsa_patch_authority=_strict_bool(
                data.get("vsa_patch_authority", False), "vsa_patch_authority"
            ),
        )
        grant.validate(now=now, verified_authority_refs=verified_authority_refs)
        grant._validate_identity()
        return grant

    def _validate_identity(self) -> None:
        payload = _canonical_payload(self, exclude=("grant_id", "grant_digest"))
        expected_digest = stable_digest(payload)
        expected_id = stable_id("authority-grant", payload)
        if self.grant_digest != expected_digest or self.grant_id != expected_id:
            raise ValueError("authority grant digest or ID does not match its content")

    def validate(
        self,
        *,
        now: float | None,
        verified_authority_refs: Iterable[str],
    ) -> None:
        current_time = _now(now)
        trusted = _trusted_set(verified_authority_refs, "verified_authority_refs")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported authority grant schema version")
        if self.proposal_only is not True:
            raise ValueError("authority grants must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("authority grant patch-authority boundary was modified")
        _required(self.principal_id, "principal_id")
        if not self.authorized_functional_roles:
            raise ValueError("authorized_functional_roles must not be empty")
        if not self.policy_scopes:
            raise ValueError("policy_scopes must not be empty")
        if not self.capability_scopes:
            raise ValueError("capability_scopes must not be empty")
        if self.expires_at <= self.valid_from:
            raise ValueError("invalid grant validity window")
        if current_time < self.valid_from:
            raise ValueError("authority grant is not active yet")
        if current_time >= self.expires_at:
            raise ValueError("authority grant is expired")
        if self.current_delegation_depth < 0 or self.maximum_delegation_depth < 0:
            raise ValueError("delegation depths must be non-negative")
        if self.current_delegation_depth > self.maximum_delegation_depth:
            raise ValueError("delegation depth exceeded")
        if (
            self.externally_verified_authority_ref not in trusted
        ):
            raise ValueError("authority verification reference is not externally trusted")

    def validate_delegation_from(self, parent: "AuthorityGrant") -> None:
        if not self.parent_grant_ref or self.parent_grant_ref != parent.grant_id:
            raise ValueError("delegated grant is not bound to the supplied parent")
        if self.current_delegation_depth != parent.current_delegation_depth + 1:
            raise ValueError("delegation depth does not follow parent")
        if self.current_delegation_depth > parent.maximum_delegation_depth:
            raise ValueError("parent delegation depth exceeded")
        if self.maximum_delegation_depth > parent.maximum_delegation_depth:
            raise ValueError("child maximum delegation depth exceeds parent")
        if not set(self.authorized_functional_roles).issubset(
            parent.authorized_functional_roles
        ):
            raise ValueError("delegated roles exceed parent grant")
        if not set(self.policy_scopes).issubset(parent.policy_scopes):
            raise ValueError("delegated policy scopes exceed parent grant")
        if not set(self.capability_scopes).issubset(parent.capability_scopes):
            raise ValueError("delegated capability scopes exceed parent grant")
        if self.valid_from < parent.valid_from or self.expires_at > parent.expires_at:
            raise ValueError("delegated validity window exceeds parent grant")

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class ApprovalAttestation:
    attestation_id: str
    attestation_digest: str
    action_id: str
    action_payload_digest: str
    principal_id: str
    grant_ref: str
    decision: str
    functional_role: str
    policy_scope: str
    capability_scope: str
    public_rationale: str
    evidence_refs: tuple[str, ...]
    externally_verified_attestation_ref: str
    created_at: float
    expires_at: float
    schema_version: str = SCHEMA_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def create(
        cls,
        *,
        action_id: str,
        action_payload_digest: str,
        principal_id: str,
        grant: AuthorityGrant,
        decision: str | AttestationDecision,
        functional_role: str,
        policy_scope: str,
        capability_scope: str,
        public_rationale: str,
        evidence_refs: Iterable[str],
        externally_verified_attestation_ref: str,
        verified_authority_refs: Iterable[str],
        verified_attestation_refs: Iterable[str],
        created_at: float | None = None,
        expires_at: float,
        now: float | None = None,
    ) -> "ApprovalAttestation":
        current_time = _now(now)
        created = current_time if created_at is None else _timestamp(created_at, "created_at")
        expiry = _timestamp(expires_at, "expires_at")
        if expiry <= created:
            raise ValueError("attestation expires_at must be after created_at")
        if expiry <= current_time:
            raise ValueError("attestation is already expired")
        if expiry > grant.expires_at:
            raise ValueError("attestation cannot outlive its authority grant")
        grant.validate(
            now=current_time,
            verified_authority_refs=verified_authority_refs,
        )
        grant._validate_identity()
        if created < grant.valid_from:
            raise ValueError("attestation cannot predate its authority grant")

        principal = _required(principal_id, "principal_id")
        if principal != grant.principal_id:
            raise ValueError("attestation principal does not match authority grant")
        role = _required(functional_role, "functional_role").upper()
        policy = _required(policy_scope, "policy_scope")
        capability = _required(capability_scope, "capability_scope")
        if role not in grant.authorized_functional_roles:
            raise ValueError("functional role is outside the authority grant")
        if policy not in grant.policy_scopes:
            raise ValueError("policy scope is outside the authority grant")
        if capability not in grant.capability_scopes:
            raise ValueError("capability scope is outside the authority grant")

        trusted_attestations = _trusted_set(
            verified_attestation_refs, "verified_attestation_refs"
        )
        external_ref = _required(
            externally_verified_attestation_ref,
            "externally_verified_attestation_ref",
        )
        if external_ref not in trusted_attestations:
            raise ValueError("attestation verification reference is not externally trusted")

        refs = _normalized_strings(evidence_refs, "evidence_refs")
        payload = {
            "action_id": _required(action_id, "action_id"),
            "action_payload_digest": _required(
                action_payload_digest, "action_payload_digest"
            ),
            "principal_id": principal,
            "grant_ref": grant.grant_id,
            "decision": _enum_value(decision, AttestationDecision, "decision"),
            "functional_role": role,
            "policy_scope": policy,
            "capability_scope": capability,
            "public_rationale": _bounded(public_rationale, "public_rationale"),
            "evidence_refs": refs,
            "externally_verified_attestation_ref": external_ref,
            "created_at": created,
            "expires_at": expiry,
            "schema_version": SCHEMA_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return cls(
            attestation_id=stable_id("approval-attestation", payload),
            attestation_digest=stable_digest(payload),
            **payload,
        )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        verified_attestation_refs: Iterable[str],
    ) -> "ApprovalAttestation":
        data = dict(value)
        attestation = cls(
            attestation_id=_required(data.get("attestation_id"), "attestation_id"),
            attestation_digest=_required(
                data.get("attestation_digest"), "attestation_digest"
            ),
            action_id=_required(data.get("action_id"), "action_id"),
            action_payload_digest=_required(
                data.get("action_payload_digest"), "action_payload_digest"
            ),
            principal_id=_required(data.get("principal_id"), "principal_id"),
            grant_ref=_required(data.get("grant_ref"), "grant_ref"),
            decision=_enum_value(
                data.get("decision"), AttestationDecision, "decision"
            ),
            functional_role=_required(
                data.get("functional_role"), "functional_role"
            ).upper(),
            policy_scope=_required(data.get("policy_scope"), "policy_scope"),
            capability_scope=_required(
                data.get("capability_scope"), "capability_scope"
            ),
            public_rationale=_bounded(
                data.get("public_rationale"), "public_rationale"
            ),
            evidence_refs=tuple(data.get("evidence_refs", ())),
            externally_verified_attestation_ref=_required(
                data.get("externally_verified_attestation_ref"),
                "externally_verified_attestation_ref",
            ),
            created_at=float(data.get("created_at")),
            expires_at=float(data.get("expires_at")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
            proposal_only=_strict_bool(data.get("proposal_only", True), "proposal_only"),
            patch_authority=str(data.get("patch_authority", PATCH_AUTHORITY)),
            vsa_patch_authority=_strict_bool(
                data.get("vsa_patch_authority", False), "vsa_patch_authority"
            ),
        )
        trusted = _trusted_set(
            verified_attestation_refs, "verified_attestation_refs"
        )
        if attestation.externally_verified_attestation_ref not in trusted:
            raise ValueError("attestation verification reference is not externally trusted")
        attestation._validate_identity()
        return attestation

    def _validate_identity(self) -> None:
        payload = _canonical_payload(
            self, exclude=("attestation_id", "attestation_digest")
        )
        if self.attestation_digest != stable_digest(payload):
            raise ValueError("attestation digest does not match its content")
        if self.attestation_id != stable_id("approval-attestation", payload):
            raise ValueError("attestation ID does not match its content")

    def validate_against(
        self,
        *,
        action_id: str,
        action_payload_digest: str,
        policy_scope: str,
        capability_scope: str,
        grant: AuthorityGrant,
        now: float | None,
        verified_authority_refs: Iterable[str],
        verified_attestation_refs: Iterable[str],
    ) -> None:
        current_time = _now(now)
        self._validate_identity()
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported attestation schema version")
        if self.proposal_only is not True:
            raise ValueError("attestations must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("attestation patch-authority boundary was modified")
        if self.action_id != _required(action_id, "action_id"):
            raise ValueError("attestation is bound to another action ID")
        if self.action_payload_digest != _required(
            action_payload_digest, "action_payload_digest"
        ):
            raise ValueError("attestation replayed against another action digest")
        if self.policy_scope != _required(policy_scope, "policy_scope"):
            raise ValueError("attestation policy scope does not match the action")
        if self.capability_scope != _required(capability_scope, "capability_scope"):
            raise ValueError("attestation capability scope does not match the action")
        if self.grant_ref != grant.grant_id:
            raise ValueError("attestation references another authority grant")
        if self.principal_id != grant.principal_id:
            raise ValueError("attestation principal does not match authority grant")
        if self.functional_role not in grant.authorized_functional_roles:
            raise ValueError("attestation uses an unauthorized functional role")
        if self.policy_scope not in grant.policy_scopes:
            raise ValueError("attestation uses an unauthorized policy scope")
        if self.capability_scope not in grant.capability_scopes:
            raise ValueError("attestation uses an unauthorized capability scope")
        if self.created_at < grant.valid_from:
            raise ValueError("attestation predates its authority grant")
        if self.expires_at > grant.expires_at:
            raise ValueError("attestation outlives its authority grant")
        if current_time < self.created_at:
            raise ValueError("attestation is not active yet")
        if current_time >= self.expires_at:
            raise ValueError("attestation is expired")
        if not self.evidence_refs:
            raise ValueError("attestation must preserve exact evidence references")
        trusted_attestations = _trusted_set(
            verified_attestation_refs, "verified_attestation_refs"
        )
        if self.externally_verified_attestation_ref not in trusted_attestations:
            raise ValueError("attestation verification reference is not externally trusted")
        grant.validate(
            now=current_time,
            verified_authority_refs=verified_authority_refs,
        )

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class QuorumPolicy:
    policy_id: str
    policy_digest: str
    risk_class: str
    minimum_approval_count: int
    required_functional_roles: tuple[str, ...]
    minimum_distinct_principals: int
    separation_of_duties: tuple[tuple[str, str], ...]
    rejection_blocks_authorization: bool
    preserve_abstentions: bool
    proposer_approval_allowed: bool
    emergency_ttl_seconds: int
    mandatory_post_event_review: bool
    emergency_allowed_policy_scopes: tuple[str, ...]
    emergency_allowed_capability_scopes: tuple[str, ...]
    baseline_policy_id: str
    baseline_policy_digest: str
    schema_version: str = SCHEMA_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def create(
        cls,
        *,
        risk_class: str | RiskClass,
        minimum_approval_count: int,
        required_functional_roles: Iterable[str],
        minimum_distinct_principals: int,
        separation_of_duties: Iterable[Sequence[str]] = (),
        rejection_blocks_authorization: bool = True,
        preserve_abstentions: bool = True,
        proposer_approval_allowed: bool = True,
        emergency_ttl_seconds: int = 0,
        mandatory_post_event_review: bool = False,
        emergency_allowed_policy_scopes: Iterable[str] = (),
        emergency_allowed_capability_scopes: Iterable[str] = (),
        normal_policy: "QuorumPolicy | None" = None,
    ) -> "QuorumPolicy":
        risk = _enum_value(risk_class, RiskClass, "risk_class")
        approvals = int(minimum_approval_count)
        distinct = int(minimum_distinct_principals)
        if approvals < 1:
            raise ValueError("minimum_approval_count must be at least one")
        if distinct < 1 or distinct > approvals:
            raise ValueError(
                "minimum_distinct_principals must be between one and approval count"
            )
        roles = _normalized_strings(
            (str(item).upper() for item in required_functional_roles),
            "required_functional_roles",
        )
        separations = tuple(
            sorted({_normalize_role_pair(pair) for pair in separation_of_duties})
        )
        ttl = int(emergency_ttl_seconds)
        emergency_policies = _normalized_strings(
            emergency_allowed_policy_scopes,
            "emergency_allowed_policy_scopes",
            allow_empty=True,
        )
        emergency_capabilities = _normalized_strings(
            emergency_allowed_capability_scopes,
            "emergency_allowed_capability_scopes",
            allow_empty=True,
        )
        baseline_id = ""
        baseline_digest = ""

        if risk == RiskClass.EMERGENCY.value:
            if normal_policy is None:
                raise ValueError("emergency quorum policy requires a normal baseline policy")
            normal_policy.validate()
            if normal_policy.risk_class == RiskClass.EMERGENCY.value:
                raise ValueError("emergency baseline must be a non-emergency policy")
            if approvals < normal_policy.minimum_approval_count:
                raise ValueError("emergency approval threshold cannot be lower")
            if distinct < normal_policy.minimum_distinct_principals:
                raise ValueError("emergency distinct-principal threshold cannot be lower")
            if not set(roles).issuperset(normal_policy.required_functional_roles):
                raise ValueError("emergency required roles cannot be weaker")
            if not set(separations).issuperset(normal_policy.separation_of_duties):
                raise ValueError("emergency separation of duties cannot be weaker")
            if (
                normal_policy.rejection_blocks_authorization
                and not rejection_blocks_authorization
            ):
                raise ValueError("emergency rejection behavior cannot be weaker")
            if (
                not normal_policy.proposer_approval_allowed
                and proposer_approval_allowed
            ):
                raise ValueError("emergency proposer separation cannot be weaker")
            if ttl <= 0:
                raise ValueError("emergency_ttl_seconds must be positive")
            if not mandatory_post_event_review:
                raise ValueError("emergency policy must require post-event review")
            if not emergency_policies or not emergency_capabilities:
                raise ValueError("emergency authority must be narrowly scoped")
            baseline_id = normal_policy.policy_id
            baseline_digest = normal_policy.policy_digest
        else:
            if ttl != 0:
                raise ValueError("non-emergency policies cannot define emergency TTL")
            if emergency_policies or emergency_capabilities:
                raise ValueError("non-emergency policies cannot define emergency scopes")
            if mandatory_post_event_review:
                raise ValueError(
                    "mandatory emergency review is only valid for emergency policy"
                )
            if normal_policy is not None:
                raise ValueError("normal_policy is only valid for emergency policies")

        payload = {
            "risk_class": risk,
            "minimum_approval_count": approvals,
            "required_functional_roles": roles,
            "minimum_distinct_principals": distinct,
            "separation_of_duties": separations,
            "rejection_blocks_authorization": _strict_bool(
                rejection_blocks_authorization, "rejection_blocks_authorization"
            ),
            "preserve_abstentions": _strict_bool(
                preserve_abstentions, "preserve_abstentions"
            ),
            "proposer_approval_allowed": _strict_bool(
                proposer_approval_allowed, "proposer_approval_allowed"
            ),
            "emergency_ttl_seconds": ttl,
            "mandatory_post_event_review": _strict_bool(
                mandatory_post_event_review, "mandatory_post_event_review"
            ),
            "emergency_allowed_policy_scopes": emergency_policies,
            "emergency_allowed_capability_scopes": emergency_capabilities,
            "baseline_policy_id": baseline_id,
            "baseline_policy_digest": baseline_digest,
            "schema_version": SCHEMA_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return cls(
            policy_id=stable_id("quorum-policy", payload),
            policy_digest=stable_digest(payload),
            **payload,
        )

    def validate(self) -> None:
        payload = _canonical_payload(self, exclude=("policy_id", "policy_digest"))
        if self.policy_id != stable_id("quorum-policy", payload):
            raise ValueError("quorum policy ID does not match its content")
        if self.policy_digest != stable_digest(payload):
            raise ValueError("quorum policy digest does not match its content")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported quorum policy schema version")
        if self.proposal_only is not True:
            raise ValueError("quorum policies must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("quorum policy patch-authority boundary was modified")
        _enum_value(self.risk_class, RiskClass, "risk_class")
        if self.minimum_approval_count < 1:
            raise ValueError("minimum_approval_count must be at least one")
        if not 1 <= self.minimum_distinct_principals <= self.minimum_approval_count:
            raise ValueError("invalid minimum_distinct_principals")
        if not self.required_functional_roles:
            raise ValueError("required_functional_roles must not be empty")
        for pair in self.separation_of_duties:
            _normalize_role_pair(pair)
        if self.risk_class == RiskClass.EMERGENCY.value:
            if self.emergency_ttl_seconds <= 0:
                raise ValueError("emergency TTL must be positive")
            if not self.mandatory_post_event_review:
                raise ValueError("emergency review must be mandatory")
            if not self.emergency_allowed_policy_scopes:
                raise ValueError("emergency policy scopes must be narrow and explicit")
            if not self.emergency_allowed_capability_scopes:
                raise ValueError("emergency capability scopes must be narrow and explicit")
            if not self.baseline_policy_id or not self.baseline_policy_digest:
                raise ValueError("emergency policy must reference its baseline")
        else:
            if self.emergency_ttl_seconds != 0:
                raise ValueError("non-emergency policy has an emergency TTL")
            if self.emergency_allowed_policy_scopes:
                raise ValueError("non-emergency policy has emergency policy scopes")
            if self.emergency_allowed_capability_scopes:
                raise ValueError("non-emergency policy has emergency capability scopes")
            if self.mandatory_post_event_review:
                raise ValueError("non-emergency policy requires emergency review")
            if self.baseline_policy_id or self.baseline_policy_digest:
                raise ValueError("non-emergency policy references an emergency baseline")

    def validate_emergency_against(self, normal_policy: "QuorumPolicy") -> None:
        self.validate()
        normal_policy.validate()
        if self.risk_class != RiskClass.EMERGENCY.value:
            raise ValueError("policy is not an emergency policy")
        if (
            self.baseline_policy_id != normal_policy.policy_id
            or self.baseline_policy_digest != normal_policy.policy_digest
        ):
            raise ValueError("emergency policy baseline does not match")
        if self.minimum_approval_count < normal_policy.minimum_approval_count:
            raise ValueError("emergency approval threshold is lower than normal")
        if self.minimum_distinct_principals < normal_policy.minimum_distinct_principals:
            raise ValueError("emergency distinct-principal threshold is lower")
        if not set(self.required_functional_roles).issuperset(
            normal_policy.required_functional_roles
        ):
            raise ValueError("emergency roles are weaker than normal")
        if not set(self.separation_of_duties).issuperset(
            normal_policy.separation_of_duties
        ):
            raise ValueError("emergency separation of duties is weaker")
        if (
            normal_policy.rejection_blocks_authorization
            and not self.rejection_blocks_authorization
        ):
            raise ValueError("emergency rejection behavior is weaker")
        if (
            not normal_policy.proposer_approval_allowed
            and self.proposer_approval_allowed
        ):
            raise ValueError("emergency proposer separation is weaker")

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    decision_digest: str
    action_id: str
    action_payload_digest: str
    policy_scope: str
    capability_scope: str
    risk_class: str
    quorum_policy_id: str
    authorized: bool
    valid_attestation_ids: tuple[str, ...]
    invalid_attestation_ids: tuple[str, ...]
    approval_attestation_ids: tuple[str, ...]
    rejection_attestation_ids: tuple[str, ...]
    abstention_attestation_ids: tuple[str, ...]
    preserved_dissent_refs: tuple[str, ...]
    missing_functional_roles: tuple[str, ...]
    missing_quorum_count: int
    missing_distinct_principals: int
    separation_of_duties_failures: tuple[str, ...]
    authority_missing_reasons: tuple[str, ...]
    expires_at: float
    emergency_reason: str
    emergency_review_required: bool
    post_event_review_due_at: float | None
    created_at: float
    schema_version: str = SCHEMA_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernanceDecision":
        data = dict(value)
        decision = cls(
            decision_id=_required(data.get("decision_id"), "decision_id"),
            decision_digest=_required(data.get("decision_digest"), "decision_digest"),
            action_id=_required(data.get("action_id"), "action_id"),
            action_payload_digest=_required(
                data.get("action_payload_digest"), "action_payload_digest"
            ),
            policy_scope=_required(data.get("policy_scope"), "policy_scope"),
            capability_scope=_required(
                data.get("capability_scope"), "capability_scope"
            ),
            risk_class=_enum_value(data.get("risk_class"), RiskClass, "risk_class"),
            quorum_policy_id=_required(
                data.get("quorum_policy_id"), "quorum_policy_id"
            ),
            authorized=_strict_bool(data.get("authorized", False), "authorized"),
            valid_attestation_ids=tuple(data.get("valid_attestation_ids", ())),
            invalid_attestation_ids=tuple(data.get("invalid_attestation_ids", ())),
            approval_attestation_ids=tuple(
                data.get("approval_attestation_ids", ())
            ),
            rejection_attestation_ids=tuple(
                data.get("rejection_attestation_ids", ())
            ),
            abstention_attestation_ids=tuple(
                data.get("abstention_attestation_ids", ())
            ),
            preserved_dissent_refs=tuple(data.get("preserved_dissent_refs", ())),
            missing_functional_roles=tuple(
                data.get("missing_functional_roles", ())
            ),
            missing_quorum_count=int(data.get("missing_quorum_count", 0)),
            missing_distinct_principals=int(
                data.get("missing_distinct_principals", 0)
            ),
            separation_of_duties_failures=tuple(
                data.get("separation_of_duties_failures", ())
            ),
            authority_missing_reasons=tuple(
                data.get("authority_missing_reasons", ())
            ),
            expires_at=float(data.get("expires_at")),
            emergency_reason=str(data.get("emergency_reason", "")),
            emergency_review_required=_strict_bool(
                data.get("emergency_review_required", False),
                "emergency_review_required",
            ),
            post_event_review_due_at=(
                None
                if data.get("post_event_review_due_at") is None
                else float(data.get("post_event_review_due_at"))
            ),
            created_at=float(data.get("created_at")),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
            proposal_only=_strict_bool(data.get("proposal_only", True), "proposal_only"),
            patch_authority=str(data.get("patch_authority", PATCH_AUTHORITY)),
            vsa_patch_authority=_strict_bool(
                data.get("vsa_patch_authority", False), "vsa_patch_authority"
            ),
        )
        decision.validate_integrity()
        return decision

    def validate_integrity(self) -> None:
        payload = _canonical_payload(self, exclude=("decision_id", "decision_digest"))
        if self.decision_digest != stable_digest(payload):
            raise ValueError("governance decision digest does not match its content")
        if self.decision_id != stable_id("governance-decision", payload):
            raise ValueError("governance decision ID does not match its content")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported governance decision schema version")
        if self.proposal_only is not True:
            raise ValueError("governance decisions must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("governance decision patch-authority boundary was modified")
        if self.authorized and self.authority_missing_reasons:
            raise ValueError("authorized decision cannot retain missing-authority reasons")
        if self.authorized and (
            self.missing_quorum_count
            or self.missing_distinct_principals
            or self.missing_functional_roles
            or self.separation_of_duties_failures
        ):
            raise ValueError("authorized decision contains unresolved quorum failures")

    def validate_for_action(
        self,
        *,
        action_id: str,
        action_payload_digest: str,
        policy_scope: str,
        capability_scope: str,
        now: float | None = None,
    ) -> None:
        self.validate_integrity()
        current_time = _now(now)
        if current_time < self.created_at:
            raise ValueError("governance decision is not active yet")
        if not self.authorized:
            raise ValueError("governance decision is not authorized")
        if self.action_id != _required(action_id, "action_id"):
            raise ValueError("governance decision is bound to another action ID")
        if self.action_payload_digest != _required(
            action_payload_digest, "action_payload_digest"
        ):
            raise ValueError("governance decision is bound to another action digest")
        if self.policy_scope != _required(policy_scope, "policy_scope"):
            raise ValueError("governance decision policy scope does not match")
        if self.capability_scope != _required(
            capability_scope, "capability_scope"
        ):
            raise ValueError("governance decision capability scope does not match")
        if current_time >= self.expires_at:
            raise ValueError("governance decision is expired")

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


def _validate_grant_chain(
    grant: AuthorityGrant,
    *,
    grants_by_id: Mapping[str, AuthorityGrant],
    verified_authority_refs: Iterable[str],
    now: float,
    visited: set[str] | None = None,
) -> None:
    seen = set() if visited is None else set(visited)
    if grant.grant_id in seen:
        raise ValueError("authority grant delegation cycle detected")
    seen.add(grant.grant_id)
    grant._validate_identity()
    grant.validate(now=now, verified_authority_refs=verified_authority_refs)
    if grant.parent_grant_ref:
        parent = grants_by_id.get(grant.parent_grant_ref)
        if parent is None:
            raise ValueError("delegated authority parent grant is missing")
        _validate_grant_chain(
            parent,
            grants_by_id=grants_by_id,
            verified_authority_refs=verified_authority_refs,
            now=now,
            visited=seen,
        )
        grant.validate_delegation_from(parent)
    elif grant.current_delegation_depth != 0:
        raise ValueError("non-root grant is missing its parent")


def evaluate_governance(
    *,
    action_id: str,
    action_payload_digest: str,
    policy_scope: str,
    capability_scope: str,
    grants: Iterable[AuthorityGrant],
    attestations: Iterable[ApprovalAttestation],
    quorum_policy: QuorumPolicy,
    verified_authority_refs: Iterable[str],
    verified_attestation_refs: Iterable[str],
    proposer_principal_id: str = "",
    normal_policy: QuorumPolicy | None = None,
    emergency_reason: str = "",
    now: float | None = None,
) -> GovernanceDecision:
    """Project grants and attestations into a deterministic, proposal-only decision."""
    current_time = _now(now)
    exact_action_id = _required(action_id, "action_id")
    exact_action_digest = _required(action_payload_digest, "action_payload_digest")
    exact_policy_scope = _required(policy_scope, "policy_scope")
    exact_capability_scope = _required(capability_scope, "capability_scope")
    proposer = str(proposer_principal_id or "").strip()
    quorum_policy.validate()

    reasons: list[str] = []
    if quorum_policy.risk_class == RiskClass.EMERGENCY.value:
        if normal_policy is None:
            reasons.append("emergency_baseline_policy_missing")
        else:
            try:
                quorum_policy.validate_emergency_against(normal_policy)
            except ValueError as exc:
                reasons.append(f"emergency_policy_invalid:{exc}")
        if exact_policy_scope not in quorum_policy.emergency_allowed_policy_scopes:
            reasons.append("emergency_policy_scope_outside_boundary")
        if exact_capability_scope not in quorum_policy.emergency_allowed_capability_scopes:
            reasons.append("emergency_capability_scope_outside_boundary")
        try:
            bounded_emergency_reason = _bounded(
                emergency_reason, "emergency_reason"
            )
        except ValueError as exc:
            bounded_emergency_reason = ""
            reasons.append(f"emergency_reason_invalid:{exc}")
    else:
        bounded_emergency_reason = ""
        if emergency_reason:
            reasons.append("emergency_reason_on_non_emergency_policy")

    trusted_authority = _trusted_set(
        verified_authority_refs, "verified_authority_refs"
    )
    trusted_attestations = _trusted_set(
        verified_attestation_refs, "verified_attestation_refs"
    )
    grant_map: dict[str, AuthorityGrant] = {}
    for grant in grants:
        if grant.grant_id in grant_map and grant_map[grant.grant_id] != grant:
            reasons.append(f"conflicting_grant:{grant.grant_id}")
        grant_map[grant.grant_id] = grant

    valid: list[ApprovalAttestation] = []
    invalid_ids: list[str] = []
    supplied = sorted(tuple(attestations), key=lambda item: item.attestation_id)
    preserved_dissent = sorted(
        {
            item.attestation_id
            for item in supplied
            if item.decision
            in (AttestationDecision.REJECT.value, AttestationDecision.ABSTAIN.value)
        }
    )

    seen_attestation_ids: set[str] = set()
    for attestation in supplied:
        if attestation.attestation_id in seen_attestation_ids:
            reasons.append(f"duplicate_attestation:{attestation.attestation_id}")
            continue
        seen_attestation_ids.add(attestation.attestation_id)
        try:
            grant = grant_map.get(attestation.grant_ref)
            if grant is None:
                raise ValueError("referenced authority grant is missing")
            _validate_grant_chain(
                grant,
                grants_by_id=grant_map,
                verified_authority_refs=trusted_authority,
                now=current_time,
            )
            attestation.validate_against(
                action_id=exact_action_id,
                action_payload_digest=exact_action_digest,
                policy_scope=exact_policy_scope,
                capability_scope=exact_capability_scope,
                grant=grant,
                now=current_time,
                verified_authority_refs=trusted_authority,
                verified_attestation_refs=trusted_attestations,
            )
            valid.append(attestation)
        except (TypeError, ValueError) as exc:
            invalid_ids.append(attestation.attestation_id)
            reasons.append(
                f"invalid_attestation:{attestation.attestation_id}:{exc}"
            )

    approvals = [
        item for item in valid if item.decision == AttestationDecision.APPROVE.value
    ]
    rejections = [
        item for item in valid if item.decision == AttestationDecision.REJECT.value
    ]
    abstentions = [
        item for item in valid if item.decision == AttestationDecision.ABSTAIN.value
    ]

    counted_approvals: list[ApprovalAttestation] = []
    seen_principal_roles: set[tuple[str, str]] = set()
    for approval in approvals:
        principal_role = (approval.principal_id, approval.functional_role)
        if principal_role in seen_principal_roles:
            reasons.append(
                "duplicate_principal_role_approval:"
                f"{approval.principal_id}:{approval.functional_role}"
            )
            continue
        seen_principal_roles.add(principal_role)
        counted_approvals.append(approval)

    role_to_principals: dict[str, set[str]] = {}
    for approval in counted_approvals:
        role_to_principals.setdefault(approval.functional_role, set()).add(
            approval.principal_id
        )
    approval_principals = {item.principal_id for item in counted_approvals}
    missing_roles = sorted(
        set(quorum_policy.required_functional_roles) - set(role_to_principals)
    )
    missing_quorum = max(
        0, quorum_policy.minimum_approval_count - len(counted_approvals)
    )
    missing_distinct = max(
        0,
        quorum_policy.minimum_distinct_principals - len(approval_principals),
    )

    separation_failures: list[str] = []
    for first, second in quorum_policy.separation_of_duties:
        overlap = role_to_principals.get(first, set()) & role_to_principals.get(
            second, set()
        )
        if overlap:
            separation_failures.append(
                f"{first}/{second}:same_principal:{','.join(sorted(overlap))}"
            )

    if (
        proposer
        and not quorum_policy.proposer_approval_allowed
        and proposer in approval_principals
    ):
        separation_failures.append(
            f"proposer_self_approval:{proposer}"
        )

    if missing_roles:
        reasons.append("required_functional_roles_missing")
    if missing_quorum:
        reasons.append("approval_quorum_missing")
    if missing_distinct:
        reasons.append("distinct_principal_quorum_missing")
    if separation_failures:
        reasons.append("separation_of_duties_failed")
    if quorum_policy.rejection_blocks_authorization and rejections:
        reasons.append("authorized_rejection_blocks")
    if invalid_ids:
        reasons.append("invalid_attestations_present")

    valid_expiries = [item.expires_at for item in counted_approvals]
    for approval in counted_approvals:
        grant = grant_map.get(approval.grant_ref)
        if grant is not None:
            valid_expiries.append(grant.expires_at)
    if valid_expiries:
        expiry = min(valid_expiries)
    else:
        expiry = current_time

    emergency_review_required = (
        quorum_policy.risk_class == RiskClass.EMERGENCY.value
        and quorum_policy.mandatory_post_event_review
    )
    review_due: float | None = None
    if quorum_policy.risk_class == RiskClass.EMERGENCY.value:
        emergency_limit = current_time + quorum_policy.emergency_ttl_seconds
        expiry = min(expiry, emergency_limit)
        review_due = expiry

    authorized = not reasons and current_time < expiry
    if current_time >= expiry and "decision_expired" not in reasons:
        reasons.append("decision_expired")
        authorized = False

    payload = {
        "action_id": exact_action_id,
        "action_payload_digest": exact_action_digest,
        "policy_scope": exact_policy_scope,
        "capability_scope": exact_capability_scope,
        "risk_class": quorum_policy.risk_class,
        "quorum_policy_id": quorum_policy.policy_id,
        "authorized": authorized,
        "valid_attestation_ids": tuple(
            sorted(item.attestation_id for item in valid)
        ),
        "invalid_attestation_ids": tuple(sorted(set(invalid_ids))),
        "approval_attestation_ids": tuple(
            sorted(item.attestation_id for item in approvals)
        ),
        "rejection_attestation_ids": tuple(
            sorted(item.attestation_id for item in rejections)
        ),
        "abstention_attestation_ids": tuple(
            sorted(item.attestation_id for item in abstentions)
            if quorum_policy.preserve_abstentions
            else ()
        ),
        "preserved_dissent_refs": tuple(preserved_dissent),
        "missing_functional_roles": tuple(missing_roles),
        "missing_quorum_count": missing_quorum,
        "missing_distinct_principals": missing_distinct,
        "separation_of_duties_failures": tuple(sorted(separation_failures)),
        "authority_missing_reasons": tuple(sorted(set(reasons))),
        "expires_at": expiry,
        "emergency_reason": bounded_emergency_reason,
        "emergency_review_required": emergency_review_required,
        "post_event_review_due_at": review_due,
        "created_at": current_time,
        "schema_version": SCHEMA_VERSION,
        "proposal_only": PROPOSAL_ONLY,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    return GovernanceDecision(
        decision_id=stable_id("governance-decision", payload),
        decision_digest=stable_digest(payload),
        **payload,
    )


@dataclass(frozen=True)
class SovereignGovernanceProfile:
    profile_id: str
    profile_digest: str
    profile_name: str
    sovereign_owner_id: str
    function_mappings: dict[str, tuple[str, ...]]
    jurisdiction_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    externally_verified_profile_ref: str
    active: bool
    activation_mode: str
    activation_consent_refs: tuple[str, ...]
    activated_by_principal_id: str
    created_at: float
    activated_at: float | None
    schema_version: str = SCHEMA_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def create(
        cls,
        *,
        profile_name: str,
        sovereign_owner_id: str,
        function_mappings: Mapping[str, Iterable[str]],
        jurisdiction_refs: Iterable[str],
        provenance_refs: Iterable[str],
        externally_verified_profile_ref: str,
        verified_profile_refs: Iterable[str],
        created_at: float | None = None,
    ) -> "SovereignGovernanceProfile":
        trusted_profiles = _trusted_set(
            verified_profile_refs, "verified_profile_refs"
        )
        external_ref = _required(
            externally_verified_profile_ref,
            "externally_verified_profile_ref",
        )
        if external_ref not in trusted_profiles:
            raise ValueError("governance profile reference is not externally trusted")

        mappings: dict[str, tuple[str, ...]] = {}
        permitted = {item.value for item in GovernanceFunction}
        for local_term, functions in dict(function_mappings).items():
            term = _required(local_term, "local governance term")
            mapped = _normalized_strings(
                (
                    item.value
                    if isinstance(item, GovernanceFunction)
                    else str(item).upper()
                    for item in functions
                ),
                f"function mappings for {term}",
            )
            unknown = set(mapped) - permitted
            if unknown:
                raise ValueError(
                    f"unknown neutral governance functions for {term}: {sorted(unknown)}"
                )
            mappings[term] = mapped
        if not mappings:
            raise ValueError("function_mappings must not be empty")

        payload = {
            "profile_name": _required(profile_name, "profile_name"),
            "sovereign_owner_id": _required(
                sovereign_owner_id, "sovereign_owner_id"
            ),
            "function_mappings": {
                key: mappings[key] for key in sorted(mappings)
            },
            "jurisdiction_refs": _normalized_strings(
                jurisdiction_refs, "jurisdiction_refs"
            ),
            "provenance_refs": _normalized_strings(
                provenance_refs, "provenance_refs"
            ),
            "externally_verified_profile_ref": external_ref,
            "active": False,
            "activation_mode": "INACTIVE",
            "activation_consent_refs": (),
            "activated_by_principal_id": "",
            "created_at": _now(created_at),
            "activated_at": None,
            "schema_version": SCHEMA_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return cls(
            profile_id=stable_id("sovereign-governance-profile", payload),
            profile_digest=stable_digest(payload),
            **payload,
        )

    def activate(
        self,
        *,
        consent_refs: Iterable[str],
        verified_consent_refs: Iterable[str],
        activated_by_principal_id: str,
        activated_at: float | None = None,
    ) -> "SovereignGovernanceProfile":
        self.validate_integrity()
        if self.active:
            return self
        trusted_consents = _trusted_set(
            verified_consent_refs, "verified_consent_refs"
        )
        consents = _normalized_strings(consent_refs, "consent_refs")
        missing = set(consents) - trusted_consents
        if missing:
            raise ValueError(
                f"profile activation consent is not externally verified: {sorted(missing)}"
            )
        payload = {
            **_canonical_payload(
                self, exclude=("profile_id", "profile_digest")
            ),
            "active": True,
            "activation_mode": "EXPLICIT_GOVERNED_CONSENT",
            "activation_consent_refs": consents,
            "activated_by_principal_id": _required(
                activated_by_principal_id, "activated_by_principal_id"
            ),
            "activated_at": _now(activated_at),
        }
        return type(self)(
            profile_id=stable_id("sovereign-governance-profile", payload),
            profile_digest=stable_digest(payload),
            **payload,
        )

    def validate_integrity(self) -> None:
        payload = _canonical_payload(self, exclude=("profile_id", "profile_digest"))
        if self.profile_id != stable_id("sovereign-governance-profile", payload):
            raise ValueError("governance profile ID does not match its content")
        if self.profile_digest != stable_digest(payload):
            raise ValueError("governance profile digest does not match its content")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported governance profile schema version")
        if self.proposal_only is not True:
            raise ValueError("governance profiles must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("governance profile patch-authority boundary was modified")
        permitted = {item.value for item in GovernanceFunction}
        for functions in self.function_mappings.values():
            if not functions or not set(functions).issubset(permitted):
                raise ValueError("profile contains an invalid neutral function mapping")
        if not self.provenance_refs or not self.jurisdiction_refs:
            raise ValueError("governance profile must remain provenance-bearing")
        if self.active:
            if self.activation_mode != "EXPLICIT_GOVERNED_CONSENT":
                raise ValueError("active profile lacks explicit governed consent")
            if not self.activation_consent_refs:
                raise ValueError("active profile lacks consent references")
            if not self.activated_by_principal_id or self.activated_at is None:
                raise ValueError("active profile lacks activation authority metadata")
        elif self.activation_mode != "INACTIVE":
            raise ValueError("inactive profile has an invalid activation mode")

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class TrustedCheckpoint:
    checkpoint_id: str
    ledger_id: str
    sequence_number: int
    chain_digest: str
    externally_signed_checkpoint_ref: str
    created_at: float
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        ledger_id: str,
        sequence_number: int,
        chain_digest: str,
        externally_signed_checkpoint_ref: str,
        verified_checkpoint_refs: Iterable[str],
        created_at: float | None = None,
    ) -> "TrustedCheckpoint":
        trusted = _trusted_set(
            verified_checkpoint_refs, "verified_checkpoint_refs"
        )
        external_ref = _required(
            externally_signed_checkpoint_ref,
            "externally_signed_checkpoint_ref",
        )
        if external_ref not in trusted:
            raise ValueError("checkpoint signature reference is not externally trusted")
        sequence = int(sequence_number)
        if sequence < 0:
            raise ValueError("checkpoint sequence_number must be non-negative")
        payload = {
            "ledger_id": _required(ledger_id, "ledger_id"),
            "sequence_number": sequence,
            "chain_digest": _required(chain_digest, "chain_digest"),
            "externally_signed_checkpoint_ref": external_ref,
            "created_at": _now(created_at),
            "schema_version": SCHEMA_VERSION,
        }
        return cls(
            checkpoint_id=stable_id("authority-checkpoint", payload),
            **payload,
        )

    def validate_integrity(
        self, *, verified_checkpoint_refs: Iterable[str]
    ) -> None:
        trusted = _trusted_set(
            verified_checkpoint_refs, "verified_checkpoint_refs"
        )
        if self.externally_signed_checkpoint_ref not in trusted:
            raise ValueError("checkpoint signature reference is not externally trusted")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported checkpoint schema version")
        if self.sequence_number < 0:
            raise ValueError("checkpoint sequence_number must be non-negative")
        payload = _canonical_payload(self, exclude=("checkpoint_id",))
        if self.checkpoint_id != stable_id("authority-checkpoint", payload):
            raise ValueError("checkpoint ID does not match its content")


@dataclass(frozen=True)
class ChainedAuthorityReceipt:
    receipt_id: str
    ledger_id: str
    sequence_number: int
    previous_chain_digest: str
    record_id: str
    record_digest: str
    chain_digest: str
    created_at: float
    checkpoint_ref: str
    schema_version: str = SCHEMA_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def create(
        cls,
        *,
        ledger_id: str,
        sequence_number: int,
        previous_chain_digest: str,
        record_id: str,
        record_digest: str,
        created_at: float | None = None,
        checkpoint_ref: str = "",
    ) -> "ChainedAuthorityReceipt":
        sequence = int(sequence_number)
        if sequence < 1:
            raise ValueError("receipt sequence_number must be at least one")
        previous = _required(previous_chain_digest, "previous_chain_digest")
        if sequence == 1 and previous != GENESIS_CHAIN_DIGEST:
            raise ValueError("first receipt must use the genesis chain digest")
        payload = {
            "ledger_id": _required(ledger_id, "ledger_id"),
            "sequence_number": sequence,
            "previous_chain_digest": previous,
            "record_id": _required(record_id, "record_id"),
            "record_digest": _required(record_digest, "record_digest"),
            "created_at": _now(created_at),
            "checkpoint_ref": str(checkpoint_ref or ""),
            "schema_version": SCHEMA_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        chain_digest = stable_digest(payload)
        identity_payload = {**payload, "chain_digest": chain_digest}
        return cls(
            receipt_id=stable_id("authority-receipt", identity_payload),
            chain_digest=chain_digest,
            **payload,
        )

    def validate_integrity(self) -> None:
        payload = _canonical_payload(
            self, exclude=("receipt_id", "chain_digest")
        )
        expected_chain = stable_digest(payload)
        identity_payload = {**payload, "chain_digest": expected_chain}
        if self.chain_digest != expected_chain:
            raise ValueError("authority receipt chain digest does not match")
        if self.receipt_id != stable_id("authority-receipt", identity_payload):
            raise ValueError("authority receipt ID does not match")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported authority receipt schema version")
        if self.proposal_only is not True:
            raise ValueError("authority receipts must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("authority receipt patch-authority boundary was modified")

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class ChainVerificationResult:
    valid: bool
    ledger_id: str
    checked_receipt_ids: tuple[str, ...]
    errors: tuple[str, ...]
    final_sequence_number: int
    final_chain_digest: str
    checkpoint_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


def verify_receipt_chain(
    receipts: Iterable[ChainedAuthorityReceipt],
    *,
    record_digests: Mapping[str, str] | None = None,
    trusted_checkpoint: TrustedCheckpoint | None = None,
    verified_checkpoint_refs: Iterable[str] = (),
) -> ChainVerificationResult:
    """Verify continuity, content identity, order, deletion gaps, and checkpoints.

    The chain proves continuity only. Actor authenticity requires an externally
    verified checkpoint or identity system supplied by the caller.
    """
    items = tuple(receipts)
    errors: list[str] = []
    ledger_ids = {item.ledger_id for item in items}
    ledger_id = sorted(ledger_ids)[0] if ledger_ids else ""
    if len(ledger_ids) > 1:
        errors.append("multiple_ledger_ids")

    checkpoint_verified = False
    checkpoint_trusted: frozenset[str] = frozenset(
        str(item).strip()
        for item in verified_checkpoint_refs
        if str(item).strip()
    )
    if trusted_checkpoint is not None:
        try:
            trusted_checkpoint.validate_integrity(
                verified_checkpoint_refs=checkpoint_trusted
            )
        except (TypeError, ValueError) as exc:
            errors.append(f"invalid_trusted_checkpoint:{exc}")
        else:
            checkpoint_verified = True
            if not ledger_id:
                ledger_id = trusted_checkpoint.ledger_id
        if ledger_id and trusted_checkpoint.ledger_id != ledger_id:
            errors.append("checkpoint_ledger_mismatch")
        if items and items[-1].sequence_number < trusted_checkpoint.sequence_number:
            errors.append("truncated_before_trusted_checkpoint")

    seen_sequences: set[int] = set()
    seen_receipts: set[str] = set()
    expected_sequence: int
    expected_previous: str

    if items and trusted_checkpoint is not None:
        first_sequence = items[0].sequence_number
        if first_sequence == trusted_checkpoint.sequence_number + 1:
            expected_sequence = first_sequence
            expected_previous = trusted_checkpoint.chain_digest
        else:
            expected_sequence = 1
            expected_previous = GENESIS_CHAIN_DIGEST
    else:
        expected_sequence = 1
        expected_previous = GENESIS_CHAIN_DIGEST

    checkpoint_seen = False
    for index, receipt in enumerate(items):
        if receipt.sequence_number in seen_sequences:
            errors.append(f"duplicate_sequence:{receipt.sequence_number}")
        seen_sequences.add(receipt.sequence_number)
        if receipt.receipt_id in seen_receipts:
            errors.append(f"duplicate_receipt:{receipt.receipt_id}")
        seen_receipts.add(receipt.receipt_id)

        if receipt.sequence_number != expected_sequence:
            if receipt.sequence_number > expected_sequence:
                errors.append(
                    f"deleted_or_missing_sequence:{expected_sequence}"
                )
            else:
                errors.append(
                    f"reordered_sequence:{receipt.sequence_number}"
                )
            expected_sequence = receipt.sequence_number

        if receipt.previous_chain_digest != expected_previous:
            errors.append(
                f"previous_digest_mismatch:{receipt.sequence_number}"
            )

        try:
            receipt.validate_integrity()
        except ValueError as exc:
            errors.append(
                f"modified_receipt:{receipt.sequence_number}:{exc}"
            )

        if record_digests is not None:
            actual = record_digests.get(receipt.record_id)
            if actual is None:
                errors.append(f"missing_record:{receipt.record_id}")
            elif actual != receipt.record_digest:
                errors.append(f"modified_record:{receipt.record_id}")

        if (
            trusted_checkpoint is not None
            and receipt.sequence_number == trusted_checkpoint.sequence_number
        ):
            checkpoint_seen = True
            if receipt.chain_digest != trusted_checkpoint.chain_digest:
                errors.append("trusted_checkpoint_digest_mismatch")

        expected_sequence = receipt.sequence_number + 1
        expected_previous = receipt.chain_digest

    if trusted_checkpoint is not None and items:
        first_sequence = items[0].sequence_number
        if (
            first_sequence <= trusted_checkpoint.sequence_number
            and not checkpoint_seen
            and items[-1].sequence_number >= trusted_checkpoint.sequence_number
        ):
            errors.append("trusted_checkpoint_sequence_missing")

    final_sequence = (
        items[-1].sequence_number
        if items
        else (
            trusted_checkpoint.sequence_number
            if trusted_checkpoint is not None and checkpoint_verified
            else 0
        )
    )
    final_digest = (
        items[-1].chain_digest
        if items
        else (
            trusted_checkpoint.chain_digest
            if trusted_checkpoint is not None and checkpoint_verified
            else GENESIS_CHAIN_DIGEST
        )
    )
    return ChainVerificationResult(
        valid=not errors,
        ledger_id=ledger_id,
        checked_receipt_ids=tuple(item.receipt_id for item in items),
        errors=tuple(errors),
        final_sequence_number=final_sequence,
        final_chain_digest=final_digest,
        checkpoint_verified=checkpoint_verified,
    )


__all__ = [
    "AUTHORITY_CONTRACTS_VERSION",
    "SCHEMA_VERSION",
    "PATCH_AUTHORITY",
    "VSA_PATCH_AUTHORITY",
    "PROPOSAL_ONLY",
    "GENESIS_CHAIN_DIGEST",
    "AttestationDecision",
    "RiskClass",
    "GovernanceFunction",
    "AuthorityGrant",
    "ApprovalAttestation",
    "QuorumPolicy",
    "GovernanceDecision",
    "SovereignGovernanceProfile",
    "TrustedCheckpoint",
    "ChainedAuthorityReceipt",
    "ChainVerificationResult",
    "evaluate_governance",
    "verify_receipt_chain",
    "canonical_json",
    "stable_digest",
    "stable_id",
]
