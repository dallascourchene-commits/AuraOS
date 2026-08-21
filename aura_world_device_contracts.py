"""World/device identity contracts for AuraOS V9 WO-D.

This module implements the minimum D-01 contract kernel only. It keeps a stable
World-level identity/provenance reference separate from device identity and binds
an individual device to that World through opaque capability/key/authority
references.

Hard boundaries:
- DEVICE != WORLD and NEW DEVICE != NEW AURA.
- DEVICE KEY != HUMAN/COMMUNITY AUTHORITY.
- A canonical digest proves content identity only; it does not authenticate an
  actor/device, authorize an effect, prove evidence completeness, or establish
  currentness.
- Key/certificate values are opaque references. Secret key material does not
  belong in these records.

Secure-store adapters, join/revoke/rotate receipts, sync, handoff, recovery,
networking, signing, attestation, and effect authorization are deliberately out
of scope for D-01.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
import math
import re
from typing import Any

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest


WORLD_IDENTITY_REF_VERSION = "AURA_WORLD_IDENTITY_REF_V1"
DEVICE_BINDING_VERSION = "AURA_DEVICE_BINDING_V1"
DEVICE_BINDING_ASSESSMENT_VERSION = "AURA_DEVICE_BINDING_ASSESSMENT_V1"

_MAX_TEXT_CHARS = 512
_DIGEST_RE = re.compile(r"^[0-9a-f]{32}$")


class DeviceCurrentness(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class DeviceRevocationState(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class DeviceBindingUseStatus(str, Enum):
    USABLE = "USABLE"
    WORLD_CONTEXT_REQUIRED = "WORLD_CONTEXT_REQUIRED"
    WORLD_MISMATCH = "WORLD_MISMATCH"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    STALE = "STALE"
    UNKNOWN_CURRENTNESS = "UNKNOWN_CURRENTNESS"
    SCOPE_DENIED = "SCOPE_DENIED"


def _required_text(value: Any, name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    if value != value.strip() or not value:
        raise ValueError(f"{name} must be a non-empty canonical string")
    if len(value) > _MAX_TEXT_CHARS:
        raise ValueError(f"{name} exceeds {_MAX_TEXT_CHARS} characters")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValueError(f"{name} contains control characters")
    return value


def _digest(value: Any, name: str) -> str:
    text = _required_text(value, name)
    if not _DIGEST_RE.fullmatch(text):
        raise ValueError(f"{name} must be a 32-character lowercase hex digest")
    return text


def _enum_value(value: str | Enum, enum_type: type[Enum], name: str) -> str:
    raw = value.value if isinstance(value, Enum) else str(value)
    allowed = {item.value for item in enum_type}
    if raw not in allowed:
        raise ValueError(f"unsupported {name}: {raw}")
    return raw


def _finite_timestamp(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _canonical_scope(
    values: Sequence[Any],
    name: str,
    *,
    normalize: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValueError(f"{name} must be a list or tuple")
    raw = tuple(_required_text(item, name) for item in values)
    if not raw:
        raise ValueError(f"{name} must not be empty")
    canonical = tuple(sorted(set(raw)))
    if len(canonical) != len(raw):
        raise ValueError(f"{name} must not contain duplicates")
    if normalize:
        return canonical
    if raw != canonical:
        raise ValueError(f"{name} must use canonical sorted order")
    return raw


def _requested_scope(values: Sequence[Any]) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValueError("required_scope must be a list or tuple")
    raw = tuple(_required_text(item, "required_scope") for item in values)
    return tuple(sorted(set(raw)))


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], name: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{name} schema mismatch; missing={missing}, extra={extra}")


def _world_payload(
    *,
    world_id: str,
    provenance_ref: str,
    owner_ref: str,
    root_ref: str,
    source_generation: str,
) -> dict[str, Any]:
    return {
        "version": WORLD_IDENTITY_REF_VERSION,
        "world_id": world_id,
        "provenance_ref": provenance_ref,
        "owner_ref": owner_ref,
        "root_ref": root_ref,
        "source_generation": source_generation,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


@dataclass(frozen=True)
class WorldIdentityRefV1:
    """Stable World identity/provenance reference, never a device identity."""

    world_id: str
    provenance_ref: str
    owner_ref: str
    root_ref: str
    source_generation: str
    digest: str
    version: str = WORLD_IDENTITY_REF_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        for field_name in (
            "world_id",
            "provenance_ref",
            "owner_ref",
            "root_ref",
            "source_generation",
        ):
            _required_text(getattr(self, field_name), field_name)
        if self.version != WORLD_IDENTITY_REF_VERSION:
            raise ValueError("unsupported WorldIdentityRefV1 version")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("WorldIdentityRefV1 authority boundary changed")
        _digest(self.digest, "digest")
        expected = stable_digest(
            _world_payload(
                world_id=self.world_id,
                provenance_ref=self.provenance_ref,
                owner_ref=self.owner_ref,
                root_ref=self.root_ref,
                source_generation=self.source_generation,
            )
        )
        if self.digest != expected:
            raise ValueError("WorldIdentityRefV1 digest mismatch")

    @classmethod
    def create(
        cls,
        *,
        world_id: str,
        provenance_ref: str,
        owner_ref: str,
        root_ref: str,
        source_generation: str,
    ) -> "WorldIdentityRefV1":
        payload = _world_payload(
            world_id=_required_text(world_id, "world_id"),
            provenance_ref=_required_text(provenance_ref, "provenance_ref"),
            owner_ref=_required_text(owner_ref, "owner_ref"),
            root_ref=_required_text(root_ref, "root_ref"),
            source_generation=_required_text(source_generation, "source_generation"),
        )
        return cls(
            world_id=payload["world_id"],
            provenance_ref=payload["provenance_ref"],
            owner_ref=payload["owner_ref"],
            root_ref=payload["root_ref"],
            source_generation=payload["source_generation"],
            digest=stable_digest(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorldIdentityRefV1":
        if not isinstance(value, Mapping):
            raise ValueError("WorldIdentityRefV1 must be a mapping")
        data = dict(value)
        expected = frozenset(
            {
                "world_id",
                "provenance_ref",
                "owner_ref",
                "root_ref",
                "source_generation",
                "digest",
                "version",
                "patch_authority",
                "vsa_patch_authority",
            }
        )
        _exact_keys(data, expected, "WorldIdentityRefV1")
        return cls(
            world_id=data["world_id"],
            provenance_ref=data["provenance_ref"],
            owner_ref=data["owner_ref"],
            root_ref=data["root_ref"],
            source_generation=data["source_generation"],
            digest=data["digest"],
            version=data["version"],
            patch_authority=data["patch_authority"],
            vsa_patch_authority=data["vsa_patch_authority"],
        )


def _binding_payload(
    *,
    world_identity: WorldIdentityRefV1,
    device_id: str,
    host_capability_ref: str,
    key_cert_ref: str,
    granted_scope: tuple[str, ...],
    expires_at: float,
    currentness: str,
    owner_ref: str,
    root_ref: str,
    revocation_state: str,
) -> dict[str, Any]:
    return {
        "version": DEVICE_BINDING_VERSION,
        "world_identity": world_identity.to_dict(),
        "device_id": device_id,
        "host_capability_ref": host_capability_ref,
        "key_cert_ref": key_cert_ref,
        "granted_scope": list(granted_scope),
        "expires_at": expires_at,
        "currentness": currentness,
        "owner_ref": owner_ref,
        "root_ref": root_ref,
        "revocation_state": revocation_state,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


@dataclass(frozen=True)
class DeviceBindingV1:
    """Scoped binding of one device aperture to an existing Aura World."""

    world_identity: WorldIdentityRefV1
    device_id: str
    host_capability_ref: str
    key_cert_ref: str
    granted_scope: tuple[str, ...]
    expires_at: float
    currentness: str
    owner_ref: str
    root_ref: str
    revocation_state: str
    digest: str
    version: str = DEVICE_BINDING_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if not isinstance(self.world_identity, WorldIdentityRefV1):
            raise ValueError("world_identity must be a WorldIdentityRefV1")
        for field_name in (
            "device_id",
            "host_capability_ref",
            "key_cert_ref",
            "owner_ref",
            "root_ref",
        ):
            _required_text(getattr(self, field_name), field_name)
        canonical_scope = _canonical_scope(
            self.granted_scope, "granted_scope", normalize=False
        )
        if canonical_scope != self.granted_scope:
            raise ValueError("granted_scope is not canonical")
        expiry = _finite_timestamp(self.expires_at, "expires_at")
        if expiry != self.expires_at:
            object.__setattr__(self, "expires_at", expiry)
        currentness = _enum_value(
            self.currentness, DeviceCurrentness, "currentness"
        )
        revocation = _enum_value(
            self.revocation_state, DeviceRevocationState, "revocation_state"
        )
        if currentness != self.currentness or revocation != self.revocation_state:
            raise ValueError("binding enum values must be canonical strings")
        if self.owner_ref != self.world_identity.owner_ref:
            raise ValueError("device owner_ref must equal World owner_ref")
        if self.root_ref != self.world_identity.root_ref:
            raise ValueError("device root_ref must equal World root_ref")
        if self.version != DEVICE_BINDING_VERSION:
            raise ValueError("unsupported DeviceBindingV1 version")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("DeviceBindingV1 authority boundary changed")
        _digest(self.digest, "digest")
        expected = stable_digest(
            _binding_payload(
                world_identity=self.world_identity,
                device_id=self.device_id,
                host_capability_ref=self.host_capability_ref,
                key_cert_ref=self.key_cert_ref,
                granted_scope=self.granted_scope,
                expires_at=float(self.expires_at),
                currentness=self.currentness,
                owner_ref=self.owner_ref,
                root_ref=self.root_ref,
                revocation_state=self.revocation_state,
            )
        )
        if self.digest != expected:
            raise ValueError("DeviceBindingV1 digest mismatch")

    @classmethod
    def create(
        cls,
        *,
        world_identity: WorldIdentityRefV1,
        device_id: str,
        host_capability_ref: str,
        key_cert_ref: str,
        granted_scope: Sequence[str],
        expires_at: float,
        currentness: str | DeviceCurrentness,
        owner_ref: str,
        root_ref: str,
        revocation_state: str | DeviceRevocationState = DeviceRevocationState.ACTIVE,
    ) -> "DeviceBindingV1":
        if not isinstance(world_identity, WorldIdentityRefV1):
            raise ValueError("world_identity must be a WorldIdentityRefV1")
        scope = _canonical_scope(granted_scope, "granted_scope", normalize=True)
        current = _enum_value(currentness, DeviceCurrentness, "currentness")
        revocation = _enum_value(
            revocation_state, DeviceRevocationState, "revocation_state"
        )
        payload = _binding_payload(
            world_identity=world_identity,
            device_id=_required_text(device_id, "device_id"),
            host_capability_ref=_required_text(
                host_capability_ref, "host_capability_ref"
            ),
            key_cert_ref=_required_text(key_cert_ref, "key_cert_ref"),
            granted_scope=scope,
            expires_at=_finite_timestamp(expires_at, "expires_at"),
            currentness=current,
            owner_ref=_required_text(owner_ref, "owner_ref"),
            root_ref=_required_text(root_ref, "root_ref"),
            revocation_state=revocation,
        )
        return cls(
            world_identity=world_identity,
            device_id=payload["device_id"],
            host_capability_ref=payload["host_capability_ref"],
            key_cert_ref=payload["key_cert_ref"],
            granted_scope=scope,
            expires_at=payload["expires_at"],
            currentness=current,
            owner_ref=payload["owner_ref"],
            root_ref=payload["root_ref"],
            revocation_state=revocation,
            digest=stable_digest(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["granted_scope"] = list(self.granted_scope)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DeviceBindingV1":
        if not isinstance(value, Mapping):
            raise ValueError("DeviceBindingV1 must be a mapping")
        data = dict(value)
        expected = frozenset(
            {
                "world_identity",
                "device_id",
                "host_capability_ref",
                "key_cert_ref",
                "granted_scope",
                "expires_at",
                "currentness",
                "owner_ref",
                "root_ref",
                "revocation_state",
                "digest",
                "version",
                "patch_authority",
                "vsa_patch_authority",
            }
        )
        _exact_keys(data, expected, "DeviceBindingV1")
        raw_scope = data["granted_scope"]
        if type(raw_scope) is not list:
            raise ValueError("granted_scope must be a JSON list")
        raw_world = data["world_identity"]
        if not isinstance(raw_world, Mapping):
            raise ValueError("world_identity must be a mapping")
        return cls(
            world_identity=WorldIdentityRefV1.from_dict(raw_world),
            device_id=data["device_id"],
            host_capability_ref=data["host_capability_ref"],
            key_cert_ref=data["key_cert_ref"],
            granted_scope=tuple(raw_scope),
            expires_at=data["expires_at"],
            currentness=data["currentness"],
            owner_ref=data["owner_ref"],
            root_ref=data["root_ref"],
            revocation_state=data["revocation_state"],
            digest=data["digest"],
            version=data["version"],
            patch_authority=data["patch_authority"],
            vsa_patch_authority=data["vsa_patch_authority"],
        )


@dataclass(frozen=True)
class DeviceBindingAssessmentV1:
    """Read-only use-time assessment; this is not effect authorization."""

    status: str
    usable: bool
    binding_digest: str
    world_digest: str
    version: str = DEVICE_BINDING_ASSESSMENT_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        _enum_value(self.status, DeviceBindingUseStatus, "status")
        if type(self.usable) is not bool:
            raise ValueError("usable must be a boolean")
        _digest(self.binding_digest, "binding_digest")
        _digest(self.world_digest, "world_digest")
        if self.version != DEVICE_BINDING_ASSESSMENT_VERSION:
            raise ValueError("unsupported DeviceBindingAssessmentV1 version")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("DeviceBindingAssessmentV1 authority boundary changed")
        if self.usable is not (self.status == DeviceBindingUseStatus.USABLE.value):
            raise ValueError("usable must match status")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_device_binding(
    binding: DeviceBindingV1,
    *,
    now: float,
    required_scope: Sequence[str] = (),
    expected_world: WorldIdentityRefV1 | None = None,
) -> DeviceBindingAssessmentV1:
    """Fail-closed read-only assessment of a DeviceBindingV1.

    This checks only the information already carried by the binding and caller.
    It does not authenticate the key/certificate reference, refresh currentness,
    verify evidence completeness, or authorize an effect. Positive USABLE also
    requires an exact expected World context supplied by the caller.
    """

    if not isinstance(binding, DeviceBindingV1):
        raise ValueError("binding must be a DeviceBindingV1")
    current_time = _finite_timestamp(now, "now")
    requested = _requested_scope(required_scope)

    if expected_world is not None:
        if not isinstance(expected_world, WorldIdentityRefV1):
            raise ValueError("expected_world must be a WorldIdentityRefV1")
        if binding.world_identity.digest != expected_world.digest:
            status = DeviceBindingUseStatus.WORLD_MISMATCH
        else:
            status = None
    else:
        status = None

    if status is None and binding.revocation_state == DeviceRevocationState.REVOKED.value:
        status = DeviceBindingUseStatus.REVOKED
    if status is None and binding.expires_at <= current_time:
        status = DeviceBindingUseStatus.EXPIRED
    if status is None and binding.currentness == DeviceCurrentness.STALE.value:
        status = DeviceBindingUseStatus.STALE
    if status is None and binding.currentness == DeviceCurrentness.UNKNOWN.value:
        status = DeviceBindingUseStatus.UNKNOWN_CURRENTNESS
    if status is None and not set(requested).issubset(binding.granted_scope):
        status = DeviceBindingUseStatus.SCOPE_DENIED
    if status is None and expected_world is None:
        status = DeviceBindingUseStatus.WORLD_CONTEXT_REQUIRED
    if status is None:
        status = DeviceBindingUseStatus.USABLE

    return DeviceBindingAssessmentV1(
        status=status.value,
        usable=status is DeviceBindingUseStatus.USABLE,
        binding_digest=binding.digest,
        world_digest=binding.world_identity.digest,
    )


__all__ = [
    "DEVICE_BINDING_ASSESSMENT_VERSION",
    "DEVICE_BINDING_VERSION",
    "WORLD_IDENTITY_REF_VERSION",
    "DeviceBindingAssessmentV1",
    "DeviceBindingUseStatus",
    "DeviceBindingV1",
    "DeviceCurrentness",
    "DeviceRevocationState",
    "WorldIdentityRefV1",
    "assess_device_binding",
]
