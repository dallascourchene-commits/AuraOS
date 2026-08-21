"""AuraOS V9 WO-D D-02 secure-store adapter contract.

This module deliberately does *not* implement cryptography or invent a key store.
It binds Aura World/device context to an injected, externally trusted platform
secure-store backend and fails closed when that backend is absent, degraded,
untrusted, stale, or otherwise unusable.

Hard boundaries:
- SECURE STORAGE != AUTHORIZATION, CURRENTNESS, TRUTH, OR HUMAN AUTHORITY.
- DEVICE KEY != HUMAN/COMMUNITY AUTHORITY.
- Backend metadata is an externally supplied capability claim; the adapter does
  not attest that a backend is genuinely hardware-backed or otherwise secure.
- No plaintext secret, secret hash, secret-derived identifier, exception text,
  or backend-returned secret is included in receipts or canonical references.
- No file/in-memory/plaintext fallback is treated as a secure store.
- Secret zeroization in Python is best-effort only and is not a memory-security
  guarantee.

D-02 is a narrow adapter/receipt layer only. Join/revoke/rotate receipts, sync,
handoff, recovery, networking, signing, attestation, and effect authorization
remain outside this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Protocol, runtime_checkable

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest
from aura_world_device_contracts import (
    DeviceBindingV1,
    WorldIdentityRefV1,
    assess_device_binding,
)


SECURE_STORE_BACKEND_DESCRIPTOR_VERSION = "AURA_SECURE_STORE_BACKEND_DESCRIPTOR_V1"
SECURE_STORE_REF_VERSION = "AURA_SECURE_STORE_REF_V1"
SECURE_STORE_RECEIPT_VERSION = "AURA_SECURE_STORE_RECEIPT_V1"
SECURE_STORE_REQUIRED_SCOPE = "SECURE_STORE"

_MAX_TEXT_CHARS = 512
_MAX_SECRET_BYTES = 1024 * 1024


class SecureStoreCapabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNSUPPORTED = "UNSUPPORTED"


class SecureStoreSecurityProfile(str, Enum):
    PLATFORM_SECURE_STORE = "PLATFORM_SECURE_STORE"
    UNSUPPORTED = "UNSUPPORTED"


class SecureStoreOperation(str, Enum):
    STORE = "STORE"
    LOAD = "LOAD"
    DELETE = "DELETE"


class SecureStoreOperationStatus(str, Enum):
    STORED = "STORED"
    LOADED = "LOADED"
    DELETED = "DELETED"
    NOT_FOUND = "NOT_FOUND"
    BINDING_BLOCKED = "BINDING_BLOCKED"
    BACKEND_UNTRUSTED = "BACKEND_UNTRUSTED"
    BACKEND_UNSUPPORTED = "BACKEND_UNSUPPORTED"
    BACKEND_DEGRADED = "BACKEND_DEGRADED"
    BACKEND_PROFILE_BLOCKED = "BACKEND_PROFILE_BLOCKED"
    BACKEND_ERROR = "BACKEND_ERROR"


def _required_text(value: Any, field_name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty canonical string")
    if len(value) > _MAX_TEXT_CHARS:
        raise ValueError(f"{field_name} exceeds {_MAX_TEXT_CHARS} characters")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def _enum_value(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:
    if isinstance(value, enum_type):
        raw = value.value
    elif type(value) is str:
        raw = value
    else:
        raise ValueError(f"{field_name} must be a canonical string or {enum_type.__name__}")
    allowed = {item.value for item in enum_type}
    if raw not in allowed:
        raise ValueError(f"unsupported {field_name}: {raw}")
    return raw


def _trusted_refs(values: Iterable[Any]) -> frozenset[str]:
    if type(values) not in (list, tuple, set, frozenset):
        raise ValueError("trusted_backend_refs must be an explicit collection")
    refs = frozenset(_required_text(item, "trusted_backend_ref") for item in values)
    if not refs:
        raise ValueError("trusted_backend_refs must not be empty")
    return refs


def _secret_bytes(value: Any) -> bytes:
    if type(value) not in (bytes, bytearray):
        raise ValueError("secret must be bytes or bytearray")
    data = bytes(value)
    if not data:
        raise ValueError("secret must not be empty")
    if len(data) > _MAX_SECRET_BYTES:
        raise ValueError(f"secret exceeds {_MAX_SECRET_BYTES} bytes")
    return data


@dataclass(frozen=True)
class SecureStoreBackendDescriptorV1:
    """Non-secret externally asserted backend capability metadata.

    Trust in this descriptor comes from the caller's trusted-backend reference
    set and platform/provider verification. The digest proves descriptor content
    identity only; it does not prove the backend's security properties.
    """

    backend_ref: str
    backend_generation: str
    security_profile: str
    capability_state: str
    digest: str
    version: str = SECURE_STORE_BACKEND_DESCRIPTOR_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        _required_text(self.backend_ref, "backend_ref")
        _required_text(self.backend_generation, "backend_generation")
        _enum_value(self.security_profile, SecureStoreSecurityProfile, "security_profile")
        _enum_value(self.capability_state, SecureStoreCapabilityState, "capability_state")
        if self.version != SECURE_STORE_BACKEND_DESCRIPTOR_VERSION:
            raise ValueError("unsupported SecureStoreBackendDescriptorV1 version")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("SecureStoreBackendDescriptorV1 authority boundary changed")
        expected = stable_digest(self._payload())
        if self.digest != expected:
            raise ValueError("SecureStoreBackendDescriptorV1 digest mismatch")

    @classmethod
    def create(
        cls,
        *,
        backend_ref: str,
        backend_generation: str,
        security_profile: str | SecureStoreSecurityProfile,
        capability_state: str | SecureStoreCapabilityState,
    ) -> "SecureStoreBackendDescriptorV1":
        raw = {
            "version": SECURE_STORE_BACKEND_DESCRIPTOR_VERSION,
            "backend_ref": _required_text(backend_ref, "backend_ref"),
            "backend_generation": _required_text(backend_generation, "backend_generation"),
            "security_profile": _enum_value(
                security_profile, SecureStoreSecurityProfile, "security_profile"
            ),
            "capability_state": _enum_value(
                capability_state, SecureStoreCapabilityState, "capability_state"
            ),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return cls(
            backend_ref=raw["backend_ref"],
            backend_generation=raw["backend_generation"],
            security_profile=raw["security_profile"],
            capability_state=raw["capability_state"],
            digest=stable_digest(raw),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "backend_ref": self.backend_ref,
            "backend_generation": self.backend_generation,
            "security_profile": self.security_profile,
            "capability_state": self.capability_state,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SecureStoreRefV1:
    """Non-secret reference binding one secret slot to exact World/device/backend context."""

    secret_id: str
    purpose: str
    world_digest: str
    device_binding_digest: str
    backend_ref: str
    backend_generation: str
    digest: str
    version: str = SECURE_STORE_REF_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        for field_name in (
            "secret_id",
            "purpose",
            "world_digest",
            "device_binding_digest",
            "backend_ref",
            "backend_generation",
        ):
            _required_text(getattr(self, field_name), field_name)
        if self.version != SECURE_STORE_REF_VERSION:
            raise ValueError("unsupported SecureStoreRefV1 version")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("SecureStoreRefV1 authority boundary changed")
        expected = stable_digest(self._payload())
        if self.digest != expected:
            raise ValueError("SecureStoreRefV1 digest mismatch")

    @classmethod
    def create(
        cls,
        *,
        secret_id: str,
        purpose: str,
        world: WorldIdentityRefV1,
        binding: DeviceBindingV1,
        backend: SecureStoreBackendDescriptorV1,
    ) -> "SecureStoreRefV1":
        if not isinstance(world, WorldIdentityRefV1):
            raise ValueError("world must be a WorldIdentityRefV1")
        if not isinstance(binding, DeviceBindingV1):
            raise ValueError("binding must be a DeviceBindingV1")
        if not isinstance(backend, SecureStoreBackendDescriptorV1):
            raise ValueError("backend must be a SecureStoreBackendDescriptorV1")
        if binding.world_identity.digest != world.digest:
            raise ValueError("binding World does not match expected World")
        raw = {
            "version": SECURE_STORE_REF_VERSION,
            "secret_id": _required_text(secret_id, "secret_id"),
            "purpose": _required_text(purpose, "purpose"),
            "world_digest": world.digest,
            "device_binding_digest": binding.digest,
            "backend_ref": backend.backend_ref,
            "backend_generation": backend.backend_generation,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return cls(
            secret_id=raw["secret_id"],
            purpose=raw["purpose"],
            world_digest=raw["world_digest"],
            device_binding_digest=raw["device_binding_digest"],
            backend_ref=raw["backend_ref"],
            backend_generation=raw["backend_generation"],
            digest=stable_digest(raw),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "secret_id": self.secret_id,
            "purpose": self.purpose,
            "world_digest": self.world_digest,
            "device_binding_digest": self.device_binding_digest,
            "backend_ref": self.backend_ref,
            "backend_generation": self.backend_generation,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SecureStoreReceiptV1:
    """Non-secret operation receipt. Backend exception text is never retained."""

    operation_id: str
    operation: str
    status: str
    secret_ref_digest: str
    backend_descriptor_digest: str
    world_digest: str
    device_binding_digest: str
    detail_code: str
    digest: str
    version: str = SECURE_STORE_RECEIPT_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        for field_name in (
            "operation_id",
            "secret_ref_digest",
            "backend_descriptor_digest",
            "world_digest",
            "device_binding_digest",
            "detail_code",
        ):
            _required_text(getattr(self, field_name), field_name)
        _enum_value(self.operation, SecureStoreOperation, "operation")
        _enum_value(self.status, SecureStoreOperationStatus, "status")
        if self.version != SECURE_STORE_RECEIPT_VERSION:
            raise ValueError("unsupported SecureStoreReceiptV1 version")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("SecureStoreReceiptV1 authority boundary changed")
        expected = stable_digest(self._payload())
        if self.digest != expected:
            raise ValueError("SecureStoreReceiptV1 digest mismatch")

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        operation: str | SecureStoreOperation,
        status: str | SecureStoreOperationStatus,
        secret_ref: SecureStoreRefV1,
        backend: SecureStoreBackendDescriptorV1,
        world: WorldIdentityRefV1,
        binding: DeviceBindingV1,
        detail_code: str,
    ) -> "SecureStoreReceiptV1":
        if not isinstance(secret_ref, SecureStoreRefV1):
            raise ValueError("secret_ref must be a SecureStoreRefV1")
        raw = {
            "version": SECURE_STORE_RECEIPT_VERSION,
            "operation_id": _required_text(operation_id, "operation_id"),
            "operation": _enum_value(operation, SecureStoreOperation, "operation"),
            "status": _enum_value(status, SecureStoreOperationStatus, "status"),
            "secret_ref_digest": secret_ref.digest,
            "backend_descriptor_digest": backend.digest,
            "world_digest": world.digest,
            "device_binding_digest": binding.digest,
            "detail_code": _required_text(detail_code, "detail_code"),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return cls(
            operation_id=raw["operation_id"],
            operation=raw["operation"],
            status=raw["status"],
            secret_ref_digest=raw["secret_ref_digest"],
            backend_descriptor_digest=raw["backend_descriptor_digest"],
            world_digest=raw["world_digest"],
            device_binding_digest=raw["device_binding_digest"],
            detail_code=raw["detail_code"],
            digest=stable_digest(raw),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "operation_id": self.operation_id,
            "operation": self.operation,
            "status": self.status,
            "secret_ref_digest": self.secret_ref_digest,
            "backend_descriptor_digest": self.backend_descriptor_digest,
            "world_digest": self.world_digest,
            "device_binding_digest": self.device_binding_digest,
            "detail_code": self.detail_code,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OpaqueSecretV1:
    """Best-effort redacted secret wrapper for transient runtime use.

    ``reveal_bytes`` is an explicit trust-boundary crossing. Python cannot
    guarantee complete memory zeroization; ``destroy`` only overwrites this
    wrapper's mutable buffer on a best-effort basis.
    """

    __slots__ = ("_buffer", "_destroyed")

    def __init__(self, value: bytes | bytearray) -> None:
        self._buffer = bytearray(_secret_bytes(value))
        self._destroyed = False

    def __repr__(self) -> str:
        return "OpaqueSecretV1(<redacted>)"

    __str__ = __repr__

    @property
    def destroyed(self) -> bool:
        return self._destroyed

    def reveal_bytes(self) -> bytes:
        if self._destroyed:
            raise ValueError("secret has been destroyed")
        return bytes(self._buffer)

    def destroy(self) -> None:
        for index in range(len(self._buffer)):
            self._buffer[index] = 0
        self._destroyed = True

    def __del__(self) -> None:  # pragma: no cover - best-effort only
        try:
            self.destroy()
        except Exception:
            pass


@runtime_checkable
class SecureStoreBackend(Protocol):
    descriptor: SecureStoreBackendDescriptorV1

    def store(self, key: str, secret: bytes) -> None: ...

    def load(self, key: str) -> bytes | None: ...

    def delete(self, key: str) -> bool: ...


class UnsupportedSecureStoreBackend:
    """Explicit fail-closed backend used when no platform secure store exists."""

    descriptor = SecureStoreBackendDescriptorV1.create(
        backend_ref="builtin:unsupported-secure-store",
        backend_generation="1",
        security_profile=SecureStoreSecurityProfile.UNSUPPORTED,
        capability_state=SecureStoreCapabilityState.UNSUPPORTED,
    )

    def store(self, key: str, secret: bytes) -> None:
        raise RuntimeError("secure store unsupported")

    def load(self, key: str) -> bytes | None:
        raise RuntimeError("secure store unsupported")

    def delete(self, key: str) -> bool:
        raise RuntimeError("secure store unsupported")


class SecureStoreAdapterV1:
    """Fail-closed bridge from a current DeviceBinding to a trusted backend."""

    def __init__(
        self,
        *,
        world: WorldIdentityRefV1,
        binding: DeviceBindingV1,
        trusted_backend_refs: Iterable[str],
        backend: SecureStoreBackend | None = None,
    ) -> None:
        if not isinstance(world, WorldIdentityRefV1):
            raise ValueError("world must be a WorldIdentityRefV1")
        if not isinstance(binding, DeviceBindingV1):
            raise ValueError("binding must be a DeviceBindingV1")
        if binding.world_identity.digest != world.digest:
            raise ValueError("binding World does not match expected World")
        self._world = world
        self._binding = binding
        self._trusted_backend_refs = _trusted_refs(trusted_backend_refs)
        self._backend: SecureStoreBackend = backend or UnsupportedSecureStoreBackend()
        descriptor = getattr(self._backend, "descriptor", None)
        if not isinstance(descriptor, SecureStoreBackendDescriptorV1):
            raise ValueError("backend must expose SecureStoreBackendDescriptorV1 descriptor")
        self._descriptor = descriptor

    @property
    def descriptor(self) -> SecureStoreBackendDescriptorV1:
        return self._descriptor

    def make_ref(self, *, secret_id: str, purpose: str) -> SecureStoreRefV1:
        return SecureStoreRefV1.create(
            secret_id=secret_id,
            purpose=purpose,
            world=self._world,
            binding=self._binding,
            backend=self._descriptor,
        )

    def _context_status(self, *, now: float) -> tuple[SecureStoreOperationStatus | None, str]:
        if self._descriptor.backend_ref not in self._trusted_backend_refs:
            return SecureStoreOperationStatus.BACKEND_UNTRUSTED, "BACKEND_REF_NOT_TRUSTED"
        assessment = assess_device_binding(
            self._binding,
            now=now,
            required_scope=(SECURE_STORE_REQUIRED_SCOPE,),
            expected_world=self._world,
        )
        if not assessment.usable:
            return SecureStoreOperationStatus.BINDING_BLOCKED, assessment.status
        if self._descriptor.capability_state == SecureStoreCapabilityState.UNSUPPORTED.value:
            return SecureStoreOperationStatus.BACKEND_UNSUPPORTED, "BACKEND_UNSUPPORTED"
        if self._descriptor.capability_state == SecureStoreCapabilityState.DEGRADED.value:
            return SecureStoreOperationStatus.BACKEND_DEGRADED, "DEGRADED_FAIL_CLOSED"
        if self._descriptor.security_profile != SecureStoreSecurityProfile.PLATFORM_SECURE_STORE.value:
            return SecureStoreOperationStatus.BACKEND_PROFILE_BLOCKED, "SECURITY_PROFILE_NOT_ADMITTED"
        return None, "READY"

    def _validate_ref(self, secret_ref: SecureStoreRefV1) -> None:
        if not isinstance(secret_ref, SecureStoreRefV1):
            raise ValueError("secret_ref must be a SecureStoreRefV1")
        if secret_ref.world_digest != self._world.digest:
            raise ValueError("secret_ref World mismatch")
        if secret_ref.device_binding_digest != self._binding.digest:
            raise ValueError("secret_ref device binding mismatch")
        if secret_ref.backend_ref != self._descriptor.backend_ref:
            raise ValueError("secret_ref backend mismatch")
        if secret_ref.backend_generation != self._descriptor.backend_generation:
            raise ValueError("secret_ref backend generation mismatch")

    def _receipt(
        self,
        *,
        operation_id: str,
        operation: SecureStoreOperation,
        status: SecureStoreOperationStatus,
        secret_ref: SecureStoreRefV1,
        detail_code: str,
    ) -> SecureStoreReceiptV1:
        return SecureStoreReceiptV1.create(
            operation_id=operation_id,
            operation=operation,
            status=status,
            secret_ref=secret_ref,
            backend=self._descriptor,
            world=self._world,
            binding=self._binding,
            detail_code=detail_code,
        )

    def store_secret(
        self,
        *,
        operation_id: str,
        secret_id: str,
        purpose: str,
        secret: bytes | bytearray,
        now: float,
    ) -> tuple[SecureStoreRefV1, SecureStoreReceiptV1]:
        value = _secret_bytes(secret)
        secret_ref = self.make_ref(secret_id=secret_id, purpose=purpose)
        blocked, detail = self._context_status(now=now)
        if blocked is not None:
            return secret_ref, self._receipt(
                operation_id=operation_id,
                operation=SecureStoreOperation.STORE,
                status=blocked,
                secret_ref=secret_ref,
                detail_code=detail,
            )
        try:
            self._backend.store(secret_ref.digest, value)
        except Exception:
            return secret_ref, self._receipt(
                operation_id=operation_id,
                operation=SecureStoreOperation.STORE,
                status=SecureStoreOperationStatus.BACKEND_ERROR,
                secret_ref=secret_ref,
                detail_code="BACKEND_EXCEPTION_REDACTED",
            )
        return secret_ref, self._receipt(
            operation_id=operation_id,
            operation=SecureStoreOperation.STORE,
            status=SecureStoreOperationStatus.STORED,
            secret_ref=secret_ref,
            detail_code="STORED_BY_ADMITTED_BACKEND",
        )

    def load_secret(
        self,
        *,
        operation_id: str,
        secret_ref: SecureStoreRefV1,
        now: float,
    ) -> tuple[OpaqueSecretV1 | None, SecureStoreReceiptV1]:
        self._validate_ref(secret_ref)
        blocked, detail = self._context_status(now=now)
        if blocked is not None:
            return None, self._receipt(
                operation_id=operation_id,
                operation=SecureStoreOperation.LOAD,
                status=blocked,
                secret_ref=secret_ref,
                detail_code=detail,
            )
        try:
            value = self._backend.load(secret_ref.digest)
        except Exception:
            return None, self._receipt(
                operation_id=operation_id,
                operation=SecureStoreOperation.LOAD,
                status=SecureStoreOperationStatus.BACKEND_ERROR,
                secret_ref=secret_ref,
                detail_code="BACKEND_EXCEPTION_REDACTED",
            )
        if value is None:
            return None, self._receipt(
                operation_id=operation_id,
                operation=SecureStoreOperation.LOAD,
                status=SecureStoreOperationStatus.NOT_FOUND,
                secret_ref=secret_ref,
                detail_code="SECRET_NOT_FOUND",
            )
        try:
            wrapped = OpaqueSecretV1(value)
        except ValueError:
            return None, self._receipt(
                operation_id=operation_id,
                operation=SecureStoreOperation.LOAD,
                status=SecureStoreOperationStatus.BACKEND_ERROR,
                secret_ref=secret_ref,
                detail_code="BACKEND_RETURNED_INVALID_SECRET",
            )
        return wrapped, self._receipt(
            operation_id=operation_id,
            operation=SecureStoreOperation.LOAD,
            status=SecureStoreOperationStatus.LOADED,
            secret_ref=secret_ref,
            detail_code="LOADED_FROM_ADMITTED_BACKEND",
        )

    def delete_secret(
        self,
        *,
        operation_id: str,
        secret_ref: SecureStoreRefV1,
        now: float,
    ) -> SecureStoreReceiptV1:
        self._validate_ref(secret_ref)
        blocked, detail = self._context_status(now=now)
        if blocked is not None:
            return self._receipt(
                operation_id=operation_id,
                operation=SecureStoreOperation.DELETE,
                status=blocked,
                secret_ref=secret_ref,
                detail_code=detail,
            )
        try:
            deleted = self._backend.delete(secret_ref.digest)
        except Exception:
            return self._receipt(
                operation_id=operation_id,
                operation=SecureStoreOperation.DELETE,
                status=SecureStoreOperationStatus.BACKEND_ERROR,
                secret_ref=secret_ref,
                detail_code="BACKEND_EXCEPTION_REDACTED",
            )
        return self._receipt(
            operation_id=operation_id,
            operation=SecureStoreOperation.DELETE,
            status=(
                SecureStoreOperationStatus.DELETED
                if deleted
                else SecureStoreOperationStatus.NOT_FOUND
            ),
            secret_ref=secret_ref,
            detail_code="SECRET_DELETED" if deleted else "SECRET_NOT_FOUND",
        )


__all__ = [
    "OpaqueSecretV1",
    "SECURE_STORE_BACKEND_DESCRIPTOR_VERSION",
    "SECURE_STORE_RECEIPT_VERSION",
    "SECURE_STORE_REF_VERSION",
    "SECURE_STORE_REQUIRED_SCOPE",
    "SecureStoreAdapterV1",
    "SecureStoreBackend",
    "SecureStoreBackendDescriptorV1",
    "SecureStoreCapabilityState",
    "SecureStoreOperation",
    "SecureStoreOperationStatus",
    "SecureStoreReceiptV1",
    "SecureStoreRefV1",
    "SecureStoreSecurityProfile",
    "UnsupportedSecureStoreBackend",
]
