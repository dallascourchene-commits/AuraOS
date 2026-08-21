from __future__ import annotations

from copy import deepcopy

import pytest

from aura_secure_store_adapter import (
    OpaqueSecretV1,
    SECURE_STORE_REQUIRED_SCOPE,
    SecureStoreAdapterV1,
    SecureStoreBackendDescriptorV1,
    SecureStoreCapabilityState,
    SecureStoreOperationStatus,
    SecureStoreReceiptV1,
    SecureStoreRefV1,
    SecureStoreSecurityProfile,
    UnsupportedSecureStoreBackend,
)
from aura_world_device_contracts import (
    DeviceBindingV1,
    DeviceCurrentness,
    DeviceRevocationState,
    WorldIdentityRefV1,
)


NOW = 1_900_000_000.0


def _world(**overrides: object) -> WorldIdentityRefV1:
    values = {
        "world_id": "world-alpha",
        "provenance_ref": "prov://world-alpha/gen-7",
        "owner_ref": "authority://owner/alice",
        "root_ref": "root://world-alpha",
        "source_generation": "gen-7",
    }
    values.update(overrides)
    return WorldIdentityRefV1.create(**values)  # type: ignore[arg-type]


def _binding(world: WorldIdentityRefV1 | None = None, **overrides: object) -> DeviceBindingV1:
    world = world or _world()
    values = {
        "world_identity": world,
        "device_id": "device-phone-01",
        "host_capability_ref": "host-profile://phone-01/v1",
        "key_cert_ref": "keystore://phone-01/key-7",
        "granted_scope": ("READ_WORLD", SECURE_STORE_REQUIRED_SCOPE),
        "expires_at": 2_000_000_000.0,
        "currentness": DeviceCurrentness.CURRENT,
        "owner_ref": world.owner_ref,
        "root_ref": world.root_ref,
        "revocation_state": DeviceRevocationState.ACTIVE,
    }
    values.update(overrides)
    return DeviceBindingV1.create(**values)  # type: ignore[arg-type]


class FakePlatformBackend:
    """Contract fixture only; this is not evidence of a real platform keystore."""

    def __init__(
        self,
        *,
        backend_ref: str = "platform-keystore://fixture/device-phone-01",
        generation: str = "gen-1",
        capability_state: SecureStoreCapabilityState = SecureStoreCapabilityState.AVAILABLE,
        profile: SecureStoreSecurityProfile = SecureStoreSecurityProfile.PLATFORM_SECURE_STORE,
        fail: bool = False,
        invalid_load: bool = False,
        invalid_store_result: bool = False,
    ) -> None:
        self.descriptor = SecureStoreBackendDescriptorV1.create(
            backend_ref=backend_ref,
            backend_generation=generation,
            security_profile=profile,
            capability_state=capability_state,
        )
        self.values: dict[str, bytes] = {}
        self.calls: list[tuple[str, str]] = []
        self.fail = fail
        self.invalid_load = invalid_load
        self.invalid_store_result = invalid_store_result

    def store_new(self, key: str, secret: bytes) -> bool:
        self.calls.append(("store_new", key))
        if self.fail:
            raise RuntimeError(f"backend failure containing secret={secret!r}")
        if self.invalid_store_result:
            return "created"  # type: ignore[return-value]
        if key in self.values:
            return False
        self.values[key] = bytes(secret)
        return True

    def load(self, key: str) -> bytes | None:
        self.calls.append(("load", key))
        if self.fail:
            raise RuntimeError("backend failure")
        if self.invalid_load:
            return "plaintext-string-is-not-an-admitted-secret"  # type: ignore[return-value]
        return self.values.get(key)

    def delete(self, key: str) -> bool:
        self.calls.append(("delete", key))
        if self.fail:
            raise RuntimeError("backend failure")
        return self.values.pop(key, None) is not None


def _adapter(
    *,
    world: WorldIdentityRefV1 | None = None,
    binding: DeviceBindingV1 | None = None,
    backend: FakePlatformBackend | None = None,
    trusted_digests: tuple[str, ...] | None = None,
) -> tuple[SecureStoreAdapterV1, FakePlatformBackend, WorldIdentityRefV1, DeviceBindingV1]:
    world = world or _world()
    binding = binding or _binding(world)
    backend = backend or FakePlatformBackend()
    trusted_digests = trusted_digests or (backend.descriptor.digest,)
    return (
        SecureStoreAdapterV1(
            world=world,
            binding=binding,
            backend=backend,
            trusted_backend_descriptor_digests=trusted_digests,
        ),
        backend,
        world,
        binding,
    )


def _stored_ref(adapter: SecureStoreAdapterV1, *, secret: bytes = b"fixture-secret") -> SecureStoreRefV1:
    secret_ref, receipt = adapter.store_secret(
        operation_id="op-store-fixture",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=secret,
        now=NOW,
    )
    assert receipt.status == SecureStoreOperationStatus.STORED.value
    assert secret_ref is not None
    return secret_ref


def test_success_path_keeps_secret_out_of_refs_and_receipts() -> None:
    adapter, backend, _, _ = _adapter()
    secret = b"correct horse battery staple"

    secret_ref, store_receipt = adapter.store_secret(
        operation_id="op-store-1",
        secret_id="device-key-slot",
        purpose="device-key-material",
        secret=secret,
        now=NOW,
    )

    assert secret_ref is not None
    assert store_receipt.status == SecureStoreOperationStatus.STORED.value
    assert backend.values[secret_ref.digest] == secret
    assert secret not in repr(secret_ref.to_dict()).encode()
    assert secret not in repr(store_receipt.to_dict()).encode()
    assert "correct horse" not in repr(secret_ref.to_dict())
    assert "correct horse" not in repr(store_receipt.to_dict())

    loaded, load_receipt = adapter.load_secret(
        operation_id="op-load-1", secret_ref=secret_ref, now=NOW
    )
    assert isinstance(loaded, OpaqueSecretV1)
    assert load_receipt.status == SecureStoreOperationStatus.LOADED.value
    assert repr(loaded) == "OpaqueSecretV1(<redacted>)"
    assert str(loaded) == "OpaqueSecretV1(<redacted>)"
    assert loaded.reveal_bytes() == secret

    loaded.destroy()
    assert loaded.destroyed is True
    with pytest.raises(ValueError, match="destroyed"):
        loaded.reveal_bytes()


def test_second_store_cannot_overwrite_without_rotation_lifecycle() -> None:
    adapter, backend, _, _ = _adapter()
    first_secret = b"first-secret-value"
    replacement = b"different-secret-value"

    first_ref, first_receipt = adapter.store_secret(
        operation_id="op-store-a",
        secret_id="same-slot",
        purpose="same-purpose",
        secret=first_secret,
        now=NOW,
    )
    second_ref, second_receipt = adapter.store_secret(
        operation_id="op-store-b",
        secret_id="same-slot",
        purpose="same-purpose",
        secret=replacement,
        now=NOW,
    )

    assert first_ref is not None
    assert first_receipt.status == SecureStoreOperationStatus.STORED.value
    assert second_ref is None
    assert second_receipt.status == SecureStoreOperationStatus.ALREADY_EXISTS.value
    assert second_receipt.detail_code == "SECRET_ALREADY_EXISTS"
    assert backend.values[first_ref.digest] == first_secret
    assert replacement not in backend.values.values()


def test_failed_store_does_not_return_a_usable_looking_reference() -> None:
    backend = FakePlatformBackend(fail=True)
    adapter, _, _, _ = _adapter(backend=backend)

    secret_ref, receipt = adapter.store_secret(
        operation_id="op-store-fail-ref",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=b"secret",
        now=NOW,
    )

    assert secret_ref is None
    assert receipt.status == SecureStoreOperationStatus.BACKEND_ERROR.value
    assert receipt.secret_ref_digest


def test_invalid_backend_store_result_fails_closed_without_reference() -> None:
    backend = FakePlatformBackend(invalid_store_result=True)
    adapter, _, _, _ = _adapter(backend=backend)

    secret_ref, receipt = adapter.store_secret(
        operation_id="op-invalid-store-result",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=b"secret",
        now=NOW,
    )

    assert secret_ref is None
    assert receipt.status == SecureStoreOperationStatus.BACKEND_ERROR.value
    assert receipt.detail_code == "BACKEND_RETURNED_INVALID_STORE_RESULT"
    assert backend.values == {}


def test_backend_exception_text_and_secret_are_not_copied_into_receipt() -> None:
    backend = FakePlatformBackend(fail=True)
    adapter, _, _, _ = _adapter(backend=backend)
    secret = b"do-not-copy-me"

    _, receipt = adapter.store_secret(
        operation_id="op-store-fail",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=secret,
        now=NOW,
    )

    assert receipt.status == SecureStoreOperationStatus.BACKEND_ERROR.value
    assert receipt.detail_code == "BACKEND_EXCEPTION_REDACTED"
    rendered = repr(receipt.to_dict())
    assert "do-not-copy-me" not in rendered
    assert "backend failure containing secret" not in rendered


def test_untrusted_backend_descriptor_fails_before_backend_is_called() -> None:
    backend = FakePlatformBackend()
    adapter, _, _, _ = _adapter(backend=backend, trusted_digests=("different-descriptor-digest",))

    secret_ref, receipt = adapter.store_secret(
        operation_id="op-untrusted",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=b"secret",
        now=NOW,
    )

    assert secret_ref is None
    assert receipt.status == SecureStoreOperationStatus.BACKEND_UNTRUSTED.value
    assert receipt.detail_code == "BACKEND_DESCRIPTOR_NOT_TRUSTED"
    assert backend.calls == []


def test_unsupported_backend_has_no_plaintext_or_memory_fallback() -> None:
    world = _world()
    binding = _binding(world)
    backend = UnsupportedSecureStoreBackend()
    adapter = SecureStoreAdapterV1(
        world=world,
        binding=binding,
        backend=backend,
        trusted_backend_descriptor_digests=(backend.descriptor.digest,),
    )

    secret_ref, receipt = adapter.store_secret(
        operation_id="op-unsupported",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=b"secret",
        now=NOW,
    )

    assert secret_ref is None
    assert receipt.status == SecureStoreOperationStatus.BACKEND_UNSUPPORTED.value
    assert receipt.detail_code == "BACKEND_UNSUPPORTED"


def test_degraded_backend_fails_closed_without_invocation() -> None:
    backend = FakePlatformBackend(capability_state=SecureStoreCapabilityState.DEGRADED)
    adapter, _, _, _ = _adapter(backend=backend)

    secret_ref, receipt = adapter.store_secret(
        operation_id="op-degraded",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=b"secret",
        now=NOW,
    )

    assert secret_ref is None
    assert receipt.status == SecureStoreOperationStatus.BACKEND_DEGRADED.value
    assert backend.calls == []


def test_non_platform_security_profile_is_not_silently_treated_as_secure_store() -> None:
    backend = FakePlatformBackend(
        profile=SecureStoreSecurityProfile.UNSUPPORTED,
        capability_state=SecureStoreCapabilityState.AVAILABLE,
    )
    adapter, _, _, _ = _adapter(backend=backend)

    secret_ref, receipt = adapter.store_secret(
        operation_id="op-profile",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=b"secret",
        now=NOW,
    )

    assert secret_ref is None
    assert receipt.status == SecureStoreOperationStatus.BACKEND_PROFILE_BLOCKED.value
    assert backend.calls == []


@pytest.mark.parametrize(
    ("binding_overrides", "expected_detail"),
    [
        ({"currentness": DeviceCurrentness.STALE}, "STALE"),
        ({"currentness": DeviceCurrentness.UNKNOWN}, "UNKNOWN_CURRENTNESS"),
        ({"revocation_state": DeviceRevocationState.REVOKED}, "REVOKED"),
        ({"expires_at": NOW}, "EXPIRED"),
        ({"granted_scope": ("READ_WORLD",)}, "SCOPE_DENIED"),
    ],
)
def test_unusable_device_binding_blocks_secure_store_before_backend(
    binding_overrides: dict[str, object], expected_detail: str
) -> None:
    world = _world()
    binding = _binding(world, **binding_overrides)
    adapter, backend, _, _ = _adapter(world=world, binding=binding)

    secret_ref, receipt = adapter.store_secret(
        operation_id=f"op-blocked-{expected_detail}",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=b"secret",
        now=NOW,
    )

    assert secret_ref is None
    assert receipt.status == SecureStoreOperationStatus.BINDING_BLOCKED.value
    assert receipt.detail_code == expected_detail
    assert backend.calls == []


def test_secret_reference_cannot_be_transplanted_across_world_or_device_context() -> None:
    adapter_a, _, _, _ = _adapter()
    secret_ref = _stored_ref(adapter_a)

    world_b = _world(
        world_id="world-beta",
        provenance_ref="prov://world-beta/gen-1",
        root_ref="root://world-beta",
        source_generation="gen-1",
    )
    binding_b = _binding(
        world_b,
        device_id="device-laptop-02",
        host_capability_ref="host-profile://laptop-02/v1",
        key_cert_ref="keystore://laptop-02/key-1",
    )
    adapter_b, backend_b, _, _ = _adapter(world=world_b, binding=binding_b)

    with pytest.raises(ValueError, match="World mismatch"):
        adapter_b.load_secret(operation_id="op-transplant", secret_ref=secret_ref, now=NOW)
    assert backend_b.calls == []


def test_backend_generation_change_invalidates_old_reference_and_requires_new_trust() -> None:
    backend_v1 = FakePlatformBackend(generation="gen-1")
    adapter_v1, _, world, binding = _adapter(backend=backend_v1)
    secret_ref = _stored_ref(adapter_v1)

    backend_v2 = FakePlatformBackend(
        backend_ref=backend_v1.descriptor.backend_ref,
        generation="gen-2",
    )
    adapter_v2, _, _, _ = _adapter(
        world=world,
        binding=binding,
        backend=backend_v2,
        trusted_digests=(backend_v2.descriptor.digest,),
    )

    with pytest.raises(ValueError, match="generation mismatch"):
        adapter_v2.load_secret(operation_id="op-load-v2", secret_ref=secret_ref, now=NOW)


def test_load_rejects_backend_non_byte_secret_without_exposing_value() -> None:
    backend = FakePlatformBackend()
    adapter, _, _, _ = _adapter(backend=backend)
    secret_ref = _stored_ref(adapter)
    backend.invalid_load = True

    loaded, receipt = adapter.load_secret(
        operation_id="op-invalid-load", secret_ref=secret_ref, now=NOW
    )

    assert loaded is None
    assert receipt.status == SecureStoreOperationStatus.BACKEND_ERROR.value
    assert receipt.detail_code == "BACKEND_RETURNED_INVALID_SECRET"
    assert "plaintext-string" not in repr(receipt.to_dict())


def test_store_requires_explicit_bytes_and_never_coerces_text_secret() -> None:
    adapter, backend, _, _ = _adapter()

    with pytest.raises(ValueError, match="bytes or bytearray"):
        adapter.store_secret(
            operation_id="op-bad-secret",
            secret_id="slot-a",
            purpose="device-key-material",
            secret="secret-text",  # type: ignore[arg-type]
            now=NOW,
        )
    assert backend.calls == []


def test_delete_reports_not_found_after_prior_delete_without_secret_material() -> None:
    adapter, _, _, _ = _adapter()
    secret_ref = _stored_ref(adapter)

    first = adapter.delete_secret(
        operation_id="op-delete-1", secret_ref=secret_ref, now=NOW
    )
    second = adapter.delete_secret(
        operation_id="op-delete-2", secret_ref=secret_ref, now=NOW
    )

    assert first.status == SecureStoreOperationStatus.DELETED.value
    assert second.status == SecureStoreOperationStatus.NOT_FOUND.value
    assert second.detail_code == "SECRET_NOT_FOUND"


def test_descriptor_reference_and_receipt_round_trip_exactly_and_reject_schema_tamper() -> None:
    adapter, backend, _, _ = _adapter()
    secret_ref, receipt = adapter.store_secret(
        operation_id="op-round-trip",
        secret_id="slot-a",
        purpose="device-key-material",
        secret=b"secret",
        now=NOW,
    )
    assert secret_ref is not None

    assert SecureStoreBackendDescriptorV1.from_dict(backend.descriptor.to_dict()) == backend.descriptor
    assert SecureStoreRefV1.from_dict(secret_ref.to_dict()) == secret_ref
    assert SecureStoreReceiptV1.from_dict(receipt.to_dict()) == receipt

    for value, loader in (
        (backend.descriptor.to_dict(), SecureStoreBackendDescriptorV1.from_dict),
        (secret_ref.to_dict(), SecureStoreRefV1.from_dict),
        (receipt.to_dict(), SecureStoreReceiptV1.from_dict),
    ):
        tampered = deepcopy(value)
        tampered["ambient_authority"] = True
        with pytest.raises(ValueError, match="schema mismatch"):
            loader(tampered)


def test_receipt_detail_code_is_closed_and_cannot_carry_secret_or_exception_text() -> None:
    adapter, backend, world, binding = _adapter()
    secret_ref = _stored_ref(adapter)

    with pytest.raises(ValueError, match="unsupported detail_code"):
        SecureStoreReceiptV1.create(
            operation_id="op-injected-detail",
            operation="LOAD",
            status="LOADED",
            secret_ref=secret_ref,
            backend=backend.descriptor,
            world=world,
            binding=binding,
            detail_code="secret=please-leak-me",
        )
