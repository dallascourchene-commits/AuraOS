from __future__ import annotations

import math

import pytest

import aura_host_discovery as hd
from aura_host_discovery import (
    HostDiscoveryV1,
    HostObservationV1,
    ObservationState,
    REQUIRED_OBSERVATIONS,
)


def _observations() -> dict[str, HostObservationV1]:
    return {
        key: HostObservationV1.observed(f"value:{key}", source=f"test:{key}")
        for key in REQUIRED_OBSERVATIONS
    }


def test_observation_state_does_not_launder_missing_evidence_into_a_value() -> None:
    with pytest.raises(ValueError):
        HostObservationV1(
            state=ObservationState.UNKNOWN.value,
            value=39.0,
            source="thermal-fallback",
        )
    with pytest.raises(ValueError):
        HostObservationV1(
            state=ObservationState.OBSERVED.value,
            value=None,
            source="missing",
        )


def test_host_discovery_round_trip_is_exact_and_digest_checked() -> None:
    record = HostDiscoveryV1.create(
        source_generation="main@abc123",
        observed_at=100.0,
        observations=_observations(),
    )
    restored = HostDiscoveryV1.from_dict(record.to_dict())
    assert restored == record

    tampered = record.to_dict()
    tampered["observations"]["architecture"]["value"] = "different"
    with pytest.raises(ValueError, match="digest mismatch"):
        HostDiscoveryV1.from_dict(tampered)


def test_host_discovery_schema_is_closed() -> None:
    record = HostDiscoveryV1.create(
        source_generation="main@abc123",
        observed_at=100.0,
        observations=_observations(),
    ).to_dict()

    extra = dict(record)
    extra["permission_granted"] = True
    with pytest.raises(ValueError, match="schema mismatch"):
        HostDiscoveryV1.from_dict(extra)

    missing = dict(record)
    missing_obs = dict(missing["observations"])
    missing_obs.pop("thermal_c")
    missing["observations"] = missing_obs
    with pytest.raises(ValueError, match="serialized observations"):
        HostDiscoveryV1.from_dict(missing)


def test_source_generation_is_digest_bound() -> None:
    observations = _observations()
    first = HostDiscoveryV1.create(
        source_generation="main@one",
        observed_at=100.0,
        observations=observations,
    )
    second = HostDiscoveryV1.create(
        source_generation="main@two",
        observed_at=100.0,
        observations=observations,
    )
    assert first.digest != second.digest


def test_discover_host_composes_observations_without_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hd.platform, "system", lambda: "Linux")
    monkeypatch.setattr(hd.platform, "release", lambda: "6.0-test")
    monkeypatch.setattr(hd.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(hd, "_observe_cpu_logical", lambda: HostObservationV1.observed(8, source="test"))
    monkeypatch.setattr(hd, "_observe_cpu_physical", lambda: HostObservationV1.missing(ObservationState.UNKNOWN, source="test"))
    monkeypatch.setattr(hd, "_observe_ram_bytes", lambda: HostObservationV1.observed(16_000, source="test"))
    monkeypatch.setattr(
        hd,
        "_observe_storage",
        lambda _root: (
            HostObservationV1.observed(100_000, source="test"),
            HostObservationV1.observed(40_000, source="test"),
        ),
    )
    monkeypatch.setattr(hd, "_observe_thermal", lambda: HostObservationV1.missing(ObservationState.UNKNOWN, source="test"))
    monkeypatch.setattr(hd, "_observe_accelerators", lambda: HostObservationV1.missing(ObservationState.UNKNOWN, source="test"))
    monkeypatch.setattr(
        hd,
        "_observe_linux_power_supply",
        lambda _root: (
            HostObservationV1.missing(ObservationState.UNAVAILABLE, source="test"),
            HostObservationV1.missing(ObservationState.UNKNOWN, source="test"),
        ),
    )
    monkeypatch.setattr(hd, "_observe_network_class", lambda: HostObservationV1.observed("LOCAL_INTERFACES_PRESENT", source="test"))
    monkeypatch.setattr(hd, "_observe_python_runtime", lambda: HostObservationV1.observed({"implementation": "CPython", "major": 3, "minor": 12}, source="test"))
    monkeypatch.setattr(hd.shutil, "which", lambda name: "/hidden/path" if name == "git" else None)

    record = hd.discover_host_v1(
        source_generation="main@abc123",
        observed_at=100.0,
        required_binaries=("git", "missing-tool"),
    )
    payload = record.to_dict()
    assert payload["observations"]["platform_family"]["value"] == "Linux"
    assert payload["observations"]["thermal_c"]["state"] == "UNKNOWN"
    assert payload["observations"]["runtime_binaries"]["value"] == {
        "git": True,
        "missing-tool": False,
    }
    serialized = repr(payload).lower()
    assert "/hidden/path" not in serialized
    assert "permission_granted" not in serialized
    assert "authority_granted" not in serialized
    assert "device_id" not in serialized


def test_thermal_nan_fallback_is_not_observed(monkeypatch: pytest.MonkeyPatch) -> None:
    import aura_thermal

    monkeypatch.setattr(aura_thermal, "read_cpu_temp_c", lambda **_kwargs: float("nan"))
    observation = hd._observe_thermal()
    assert observation.state == ObservationState.UNKNOWN.value
    assert observation.value is None
    assert "fallback" in observation.detail


def test_thermal_finite_value_is_observed(monkeypatch: pytest.MonkeyPatch) -> None:
    import aura_thermal

    monkeypatch.setattr(aura_thermal, "read_cpu_temp_c", lambda **_kwargs: 42.5)
    observation = hd._observe_thermal()
    assert observation.state == ObservationState.OBSERVED.value
    assert observation.value == 42.5


def test_required_binary_probe_accepts_names_only_and_does_not_store_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hd.shutil, "which", lambda _name: "/secret/location/tool")
    observation = hd._observe_runtime_binaries(("python", "git"))
    assert observation.value == {"git": True, "python": True}
    assert "/secret/location" not in repr(observation.to_dict())

    for invalid in (("../tool",), ("/usr/bin/tool",), ("tool", "tool")):
        with pytest.raises(ValueError):
            hd._observe_runtime_binaries(invalid)


def test_accelerator_absence_is_unknown_not_proof_of_no_accelerator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hd.Path, "exists", lambda _self: False)
    monkeypatch.setattr(hd.shutil, "which", lambda _name: None)
    observation = hd._observe_accelerators()
    assert observation.state == ObservationState.UNKNOWN.value
    assert observation.value is None


def test_network_inventory_does_not_claim_reachability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hd.socket, "if_nameindex", lambda: [(1, "lo"), (2, "eth0")])
    observation = hd._observe_network_class()
    assert observation.value == "LOCAL_INTERFACES_PRESENT"
    assert "reachability" in observation.detail
    assert "eth0" not in repr(observation.to_dict())


def test_nonfinite_and_noncanonical_observation_values_fail_closed() -> None:
    with pytest.raises(ValueError):
        HostObservationV1.observed(math.inf, source="test")
    with pytest.raises(ValueError):
        HostObservationV1.observed({" ok": 1}, source="test")


def test_malformed_serialization_fails_with_value_error() -> None:
    with pytest.raises(ValueError):
        HostObservationV1.from_dict([])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        HostDiscoveryV1.from_dict([])  # type: ignore[arg-type]
