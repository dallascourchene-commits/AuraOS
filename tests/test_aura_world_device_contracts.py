from __future__ import annotations

from copy import deepcopy

import pytest

from aura_world_device_contracts import (
    DeviceBindingUseStatus,
    DeviceBindingV1,
    DeviceCurrentness,
    DeviceRevocationState,
    WorldIdentityRefV1,
    assess_device_binding,
)


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
        "granted_scope": ("READ_WORLD", "PROPOSE_WORK"),
        "expires_at": 2_000_000_000.0,
        "currentness": DeviceCurrentness.CURRENT,
        "owner_ref": world.owner_ref,
        "root_ref": world.root_ref,
        "revocation_state": DeviceRevocationState.ACTIVE,
    }
    values.update(overrides)
    return DeviceBindingV1.create(**values)  # type: ignore[arg-type]


def test_world_identity_is_deterministic_and_round_trips_exactly() -> None:
    first = _world()
    second = _world()

    assert first == second
    assert len(first.digest) == 32
    assert WorldIdentityRefV1.from_dict(first.to_dict()) == first


def test_world_identity_schema_rejects_device_or_unknown_fields() -> None:
    payload = _world().to_dict()
    payload["device_id"] = "must-not-live-on-world-identity"

    with pytest.raises(ValueError, match="schema mismatch"):
        WorldIdentityRefV1.from_dict(payload)


def test_two_devices_share_one_world_without_sharing_device_identity() -> None:
    world = _world()
    phone = _binding(world, device_id="device-phone-01")
    laptop = _binding(
        world,
        device_id="device-laptop-01",
        host_capability_ref="host-profile://laptop-01/v1",
        key_cert_ref="keystore://laptop-01/key-2",
    )

    assert phone.world_identity.digest == laptop.world_identity.digest == world.digest
    assert phone.device_id != laptop.device_id
    assert phone.digest != laptop.digest


def test_binding_scope_is_canonicalized_at_creation_and_round_trips() -> None:
    binding = _binding(granted_scope=("PROPOSE_WORK", "READ_WORLD"))

    assert binding.granted_scope == ("PROPOSE_WORK", "READ_WORLD")
    assert DeviceBindingV1.from_dict(binding.to_dict()) == binding


def test_untrusted_noncanonical_scope_order_and_duplicates_fail_closed() -> None:
    binding = _binding()

    wrong_order = binding.to_dict()
    wrong_order["granted_scope"] = ["READ_WORLD", "PROPOSE_WORK"]
    with pytest.raises(ValueError, match="canonical sorted order"):
        DeviceBindingV1.from_dict(wrong_order)

    duplicate = binding.to_dict()
    duplicate["granted_scope"] = ["PROPOSE_WORK", "PROPOSE_WORK"]
    with pytest.raises(ValueError, match="duplicates"):
        DeviceBindingV1.from_dict(duplicate)


def test_binding_digest_detects_tampering() -> None:
    binding = _binding()
    payload = binding.to_dict()
    payload["host_capability_ref"] = "host-profile://attacker/v9"

    with pytest.raises(ValueError, match="digest mismatch"):
        DeviceBindingV1.from_dict(payload)


def test_binding_rejects_missing_extra_and_nonsequence_scope() -> None:
    binding = _binding()

    missing = binding.to_dict()
    del missing["root_ref"]
    with pytest.raises(ValueError, match="schema mismatch"):
        DeviceBindingV1.from_dict(missing)

    extra = binding.to_dict()
    extra["ambient_authority"] = True
    with pytest.raises(ValueError, match="schema mismatch"):
        DeviceBindingV1.from_dict(extra)

    bad_scope = binding.to_dict()
    bad_scope["granted_scope"] = "READ_WORLD"
    with pytest.raises(ValueError, match="ordered sequence"):
        DeviceBindingV1.from_dict(bad_scope)


def test_device_binding_cannot_change_world_owner_or_root() -> None:
    world = _world()

    with pytest.raises(ValueError, match="owner_ref must equal World owner_ref"):
        _binding(world, owner_ref="authority://different-owner")

    with pytest.raises(ValueError, match="root_ref must equal World root_ref"):
        _binding(world, root_ref="root://different-world")


def test_revoked_stale_unknown_and_expired_bindings_are_not_usable() -> None:
    now = 1_900_000_000.0

    revoked = assess_device_binding(
        _binding(revocation_state=DeviceRevocationState.REVOKED), now=now
    )
    assert revoked.status == DeviceBindingUseStatus.REVOKED.value
    assert revoked.usable is False

    stale = assess_device_binding(
        _binding(currentness=DeviceCurrentness.STALE), now=now
    )
    assert stale.status == DeviceBindingUseStatus.STALE.value
    assert stale.usable is False

    unknown = assess_device_binding(
        _binding(currentness=DeviceCurrentness.UNKNOWN), now=now
    )
    assert unknown.status == DeviceBindingUseStatus.UNKNOWN_CURRENTNESS.value
    assert unknown.usable is False

    expired = assess_device_binding(
        _binding(expires_at=now), now=now
    )
    assert expired.status == DeviceBindingUseStatus.EXPIRED.value
    assert expired.usable is False


def test_scope_widening_is_denied_at_use_time() -> None:
    assessment = assess_device_binding(
        _binding(),
        now=1_900_000_000.0,
        required_scope=("READ_WORLD", "COMMIT_EFFECT"),
    )

    assert assessment.status == DeviceBindingUseStatus.SCOPE_DENIED.value
    assert assessment.usable is False


def test_expected_world_mismatch_is_denied_even_for_current_binding() -> None:
    binding = _binding(_world())
    different_world = _world(
        world_id="world-beta",
        provenance_ref="prov://world-beta/gen-1",
        root_ref="root://world-beta",
        source_generation="gen-1",
    )

    assessment = assess_device_binding(
        binding,
        now=1_900_000_000.0,
        expected_world=different_world,
    )

    assert assessment.status == DeviceBindingUseStatus.WORLD_MISMATCH.value
    assert assessment.usable is False


def test_current_scoped_binding_can_be_assessed_usable_without_authority_claim() -> None:
    binding = _binding()
    assessment = assess_device_binding(
        binding,
        now=1_900_000_000.0,
        required_scope=("READ_WORLD",),
        expected_world=binding.world_identity,
    )

    assert assessment.status == DeviceBindingUseStatus.USABLE.value
    assert assessment.usable is True
    assert assessment.binding_digest == binding.digest
    assert assessment.world_digest == binding.world_identity.digest


def test_tampering_nested_world_identity_is_detected() -> None:
    binding = _binding()
    payload = deepcopy(binding.to_dict())
    payload["world_identity"]["source_generation"] = "gen-attacker"

    with pytest.raises(ValueError, match="WorldIdentityRefV1 digest mismatch"):
        DeviceBindingV1.from_dict(payload)


def test_records_expose_references_not_secret_key_fields() -> None:
    payload = _binding().to_dict()

    assert payload["key_cert_ref"].startswith("keystore://")
    assert "private_key" not in payload
    assert "secret" not in payload
    assert "token" not in payload
