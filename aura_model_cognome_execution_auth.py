"""Content-bound authorization for approved Model Cognome live experiments.

This record grants no policy-promotion or source-mutation authority.  It only
admits one bounded PAIRED_LIVE experiment when purpose, current Connectome graph,
policy mode, selected profiles, verifier, expiry, and call count all match.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import time
from typing import Any, Mapping, Sequence

from aura_model_cognome import stable_id

PAIRED_LIVE = "PAIRED_LIVE"
AUTHORIZATION_VERSION = "AURA_ADAPTIVE_EXECUTION_AUTHORIZATION_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_ALLOWED_POLICIES = frozenset({"ZERO_MODEL", "DIRECT", "CASCADE", "PANEL"})
_MODEL_POLICIES = frozenset({"DIRECT", "CASCADE", "PANEL"})


@dataclass(frozen=True)
class ExecutionAuthorization:
    authorization_id: str
    approved_by: str
    verifier_id: str
    purpose_digest: str
    capability_graph_digest: str
    allowed_policy_modes: tuple[str, ...]
    allowed_profile_ids: tuple[str, ...]
    nonce: str
    issued_at: float
    expires_at: float
    max_calls: int
    allow_forced_override: bool = False
    measurement_mode: str = PAIRED_LIVE
    version: str = AUTHORIZATION_VERSION

    def __post_init__(self) -> None:
        for name in (
            "authorization_id", "approved_by", "verifier_id", "purpose_digest",
            "capability_graph_digest", "nonce",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.measurement_mode != PAIRED_LIVE:
            raise ValueError("execution authorization is valid only for PAIRED_LIVE")
        if self.version != AUTHORIZATION_VERSION:
            raise ValueError("unsupported execution authorization version")
        if not math.isfinite(float(self.issued_at)) or not math.isfinite(float(self.expires_at)):
            raise ValueError("authorization timestamps must be finite")
        if self.issued_at < 0 or self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must be greater than issue time")
        if self.max_calls < 0:
            raise ValueError("max_calls must be non-negative")
        if not isinstance(self.allowed_policy_modes, tuple):
            raise ValueError("allowed_policy_modes must be a tuple")
        if not isinstance(self.allowed_profile_ids, tuple):
            raise ValueError("allowed_profile_ids must be a tuple")
        if not self.allowed_policy_modes:
            raise ValueError("allowed_policy_modes must not be empty")
        if len(self.allowed_policy_modes) != len(set(self.allowed_policy_modes)):
            raise ValueError("allowed_policy_modes cannot contain duplicates")
        unknown = sorted(set(self.allowed_policy_modes) - _ALLOWED_POLICIES)
        if unknown:
            raise ValueError("unknown authorized policy modes: " + ", ".join(unknown))
        if any(not str(item).strip() for item in self.allowed_profile_ids):
            raise ValueError("allowed_profile_ids cannot contain empty values")
        if len(self.allowed_profile_ids) != len(set(self.allowed_profile_ids)):
            raise ValueError("allowed_profile_ids cannot contain duplicates")
        if set(self.allowed_policy_modes) & _MODEL_POLICIES and not self.allowed_profile_ids:
            raise ValueError("model-executing policy modes require an explicit profile allowlist")
        if type(self.allow_forced_override) is not bool:
            raise ValueError("allow_forced_override must be a boolean")
        expected = stable_id("execution-authorization", self.identity_basis())
        if self.authorization_id != expected:
            raise ValueError("authorization_id does not match authorization content")

    def identity_basis(self) -> dict[str, Any]:
        return {
            "approved_by": self.approved_by,
            "verifier_id": self.verifier_id,
            "purpose_digest": self.purpose_digest,
            "capability_graph_digest": self.capability_graph_digest,
            "allowed_policy_modes": self.allowed_policy_modes,
            "allowed_profile_ids": self.allowed_profile_ids,
            "nonce": self.nonce,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "max_calls": self.max_calls,
            "allow_forced_override": self.allow_forced_override,
            "measurement_mode": self.measurement_mode,
            "version": self.version,
        }

    @classmethod
    def create(
        cls,
        *,
        approved_by: str,
        verifier_id: str,
        purpose_digest: str,
        capability_graph_digest: str,
        allowed_policy_modes: Sequence[str],
        nonce: str,
        allowed_profile_ids: Sequence[str] = (),
        issued_at: float | None = None,
        expires_at: float | None = None,
        ttl_seconds: float = 900.0,
        max_calls: int = 4,
        allow_forced_override: bool = False,
    ) -> "ExecutionAuthorization":
        issued = time.time() if issued_at is None else float(issued_at)
        expiry = issued + float(ttl_seconds) if expires_at is None else float(expires_at)
        basis = {
            "approved_by": str(approved_by).strip(),
            "verifier_id": str(verifier_id).strip(),
            "purpose_digest": str(purpose_digest).strip(),
            "capability_graph_digest": str(capability_graph_digest).strip(),
            "allowed_policy_modes": tuple(str(item) for item in allowed_policy_modes),
            "allowed_profile_ids": tuple(str(item) for item in allowed_profile_ids),
            "nonce": str(nonce).strip(),
            "issued_at": issued,
            "expires_at": expiry,
            "max_calls": int(max_calls),
            "allow_forced_override": allow_forced_override,
            "measurement_mode": PAIRED_LIVE,
            "version": AUTHORIZATION_VERSION,
        }
        return cls(authorization_id=stable_id("execution-authorization", basis), **basis)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExecutionAuthorization":
        policy_modes = value.get("allowed_policy_modes", ())
        profile_ids = value.get("allowed_profile_ids", ())
        if not isinstance(policy_modes, (list, tuple)):
            raise ValueError("allowed_policy_modes must be a list or tuple")
        if not isinstance(profile_ids, (list, tuple)):
            raise ValueError("allowed_profile_ids must be a list or tuple")
        if type(value.get("allow_forced_override", False)) is not bool:
            raise ValueError("allow_forced_override must be a boolean")
        return cls(
            authorization_id=str(value.get("authorization_id") or ""),
            approved_by=str(value.get("approved_by") or ""),
            verifier_id=str(value.get("verifier_id") or ""),
            purpose_digest=str(value.get("purpose_digest") or ""),
            capability_graph_digest=str(value.get("capability_graph_digest") or ""),
            allowed_policy_modes=tuple(str(item) for item in policy_modes),
            allowed_profile_ids=tuple(str(item) for item in profile_ids),
            nonce=str(value.get("nonce") or ""),
            issued_at=float(value.get("issued_at")),
            expires_at=float(value.get("expires_at")),
            max_calls=int(value.get("max_calls", 0)),
            allow_forced_override=value.get("allow_forced_override", False),
            measurement_mode=str(value.get("measurement_mode") or PAIRED_LIVE),
            version=str(value.get("version") or AUTHORIZATION_VERSION),
        )

    def validate_for(
        self,
        *,
        purpose_digest: str,
        graph_digest: str,
        policy_mode: str,
        profile_ids: Sequence[str],
        call_count: int,
        forced_override: bool,
        verifier_id: str,
        now: float,
    ) -> list[str]:
        errors: list[str] = []
        if not math.isfinite(float(now)):
            errors.append("authorization evaluation time must be finite")
            return errors
        if type(call_count) is not int or call_count < 0:
            errors.append("call_count must be a non-negative integer")
        if len(tuple(profile_ids)) != len(set(str(item) for item in profile_ids)):
            errors.append("selected profile IDs cannot contain duplicates")
        if now < self.issued_at:
            errors.append("authorization is not active yet")
        if now >= self.expires_at:
            errors.append("authorization has expired")
        if self.purpose_digest != purpose_digest:
            errors.append("authorization purpose digest mismatch")
        if self.capability_graph_digest != graph_digest:
            errors.append("authorization capability graph digest mismatch")
        if self.verifier_id != verifier_id:
            errors.append("authorization verifier mismatch")
        if policy_mode not in self.allowed_policy_modes:
            errors.append("policy mode is not authorized")
        selected = tuple(str(item) for item in profile_ids)
        if not set(selected).issubset(set(self.allowed_profile_ids)):
            errors.append("selected profile is outside the authorization allowlist")
        if call_count > self.max_calls:
            errors.append("route exceeds authorization call limit")
        if forced_override and not self.allow_forced_override:
            errors.append("forced-model override is not authorized")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
