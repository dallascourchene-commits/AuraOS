"""Pure host-observation contract for AuraOS V9 WO-B H1.

HostDiscoveryV1 describes what a host can safely observe about itself without
turning hardware facts into permission, authority, correctness, or runtime
profile selection.

Hard boundaries:
- PLATFORM_API != AURA_SEMANTICS.
- DEVICE != WORLD.
- HARDWARE_CAPABILITY != AUTHORITY.
- DISCOVERY != PERMISSION.
- OPTIMIZATION != CORRECTNESS.
- Missing evidence stays UNKNOWN/UNAVAILABLE/ERROR; no fallback value is
  relabelled as an observation.
- No provider call, network reachability probe, credential read, device ID,
  hostname, username, IP address, or privileged mutation belongs here.

H2 normalization, H3 runtime-profile selection, H4 platform adapters and H5
acceptance/benchmark work are deliberately out of scope.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
import math
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import sys
import time
from typing import Any

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest


HOST_DISCOVERY_VERSION = "AURA_HOST_DISCOVERY_V1"
HOST_OBSERVATION_VERSION = "AURA_HOST_OBSERVATION_V1"
_MAX_TEXT = 512
_MAX_COLLECTION = 64
_DIGEST_RE = re.compile(r"^[0-9a-f]{32}$")
_BINARY_NAME_RE = re.compile(r"^[A-Za-z0-9_.+-]{1,128}$")

REQUIRED_OBSERVATIONS = (
    "platform_family",
    "os_release",
    "architecture",
    "cpu_logical",
    "cpu_physical",
    "ram_bytes",
    "storage_total_bytes",
    "storage_free_bytes",
    "thermal_c",
    "accelerators",
    "battery_percent",
    "power_source",
    "network_class",
    "python_runtime",
    "runtime_binaries",
)
_REQUIRED_OBSERVATION_SET = frozenset(REQUIRED_OBSERVATIONS)


class ObservationState(str, Enum):
    OBSERVED = "OBSERVED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


def _text(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    if value != value.strip():
        raise ValueError(f"{field_name} must use canonical surrounding whitespace")
    if not value and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > _MAX_TEXT:
        raise ValueError(f"{field_name} exceeds {_MAX_TEXT} characters")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def _state(value: str | ObservationState) -> str:
    raw = value.value if isinstance(value, ObservationState) else value
    if type(raw) is not str or raw not in {item.value for item in ObservationState}:
        raise ValueError(f"unsupported observation state: {raw!r}")
    return raw


def _canonical_value(value: Any, field_name: str = "value", *, depth: int = 0) -> Any:
    if depth > 4:
        raise ValueError(f"{field_name} exceeds maximum nesting depth")
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{field_name} must not contain non-finite floats")
        return value
    if type(value) is str:
        return _text(value, field_name, allow_empty=True)
    if isinstance(value, Mapping):
        if len(value) > _MAX_COLLECTION:
            raise ValueError(f"{field_name} has too many members")
        result: dict[str, Any] = {}
        for key in sorted(value):
            if type(key) is not str:
                raise ValueError(f"{field_name} mapping keys must be strings")
            canonical_key = _text(key, f"{field_name}.key")
            result[canonical_key] = _canonical_value(
                value[key], f"{field_name}.{canonical_key}", depth=depth + 1
            )
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_COLLECTION:
            raise ValueError(f"{field_name} has too many members")
        return [
            _canonical_value(item, f"{field_name}[{index}]", depth=depth + 1)
            for index, item in enumerate(value)
        ]
    raise ValueError(f"{field_name} contains unsupported value type {type(value).__name__}")


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], name: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{name} schema mismatch; missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _digest(value: Any, field_name: str = "digest") -> str:
    text = _text(value, field_name)
    if not _DIGEST_RE.fullmatch(text):
        raise ValueError(f"{field_name} must be a 32-character lowercase hex digest")
    return text


def _timestamp(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("observed_at must be a finite non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("observed_at must be a finite non-negative number")
    return result


@dataclass(frozen=True)
class HostObservationV1:
    state: str
    value: Any
    source: str
    detail: str = ""
    version: str = HOST_OBSERVATION_VERSION

    def __post_init__(self) -> None:
        state = _state(self.state)
        if state != self.state:
            raise ValueError("observation state must be a canonical string")
        _text(self.source, "source")
        _text(self.detail, "detail", allow_empty=True)
        canonical = _canonical_value(self.value)
        if state == ObservationState.OBSERVED.value:
            if canonical is None:
                raise ValueError("OBSERVED requires a value")
        elif canonical is not None:
            raise ValueError(f"{state} observations must not carry a value")
        if self.version != HOST_OBSERVATION_VERSION:
            raise ValueError("unsupported HostObservationV1 version")

    @classmethod
    def observed(cls, value: Any, *, source: str, detail: str = "") -> "HostObservationV1":
        return cls(
            state=ObservationState.OBSERVED.value,
            value=_canonical_value(value),
            source=_text(source, "source"),
            detail=_text(detail, "detail", allow_empty=True),
        )

    @classmethod
    def missing(
        cls,
        state: str | ObservationState,
        *,
        source: str,
        detail: str = "",
    ) -> "HostObservationV1":
        canonical_state = _state(state)
        if canonical_state == ObservationState.OBSERVED.value:
            raise ValueError("use HostObservationV1.observed for OBSERVED state")
        return cls(
            state=canonical_state,
            value=None,
            source=_text(source, "source"),
            detail=_text(detail, "detail", allow_empty=True),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["value"] = _canonical_value(self.value)
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HostObservationV1":
        expected = frozenset({"state", "value", "source", "detail", "version"})
        _exact_keys(value, expected, "HostObservationV1")
        return cls(
            state=value["state"],
            value=_canonical_value(value["value"]),
            source=value["source"],
            detail=value["detail"],
            version=value["version"],
        )


def _discovery_payload(
    *,
    source_generation: str,
    observed_at: float,
    observations: Mapping[str, HostObservationV1],
) -> dict[str, Any]:
    return {
        "version": HOST_DISCOVERY_VERSION,
        "source_generation": source_generation,
        "observed_at": observed_at,
        "observations": {
            key: observations[key].to_dict() for key in REQUIRED_OBSERVATIONS
        },
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


@dataclass(frozen=True)
class HostDiscoveryV1:
    source_generation: str
    observed_at: float
    observations: dict[str, HostObservationV1]
    digest: str
    version: str = HOST_DISCOVERY_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        _text(self.source_generation, "source_generation")
        observed_at = _timestamp(self.observed_at)
        if observed_at != self.observed_at:
            object.__setattr__(self, "observed_at", observed_at)
        if not isinstance(self.observations, Mapping):
            raise ValueError("observations must be a mapping")
        if set(self.observations) != _REQUIRED_OBSERVATION_SET:
            raise ValueError(
                "HostDiscoveryV1 requires exactly the declared H1 observation fields"
            )
        for key in REQUIRED_OBSERVATIONS:
            if not isinstance(self.observations[key], HostObservationV1):
                raise ValueError(f"observation {key} must be HostObservationV1")
        if self.version != HOST_DISCOVERY_VERSION:
            raise ValueError("unsupported HostDiscoveryV1 version")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("HostDiscoveryV1 authority boundary changed")
        _digest(self.digest)
        expected = stable_digest(
            _discovery_payload(
                source_generation=self.source_generation,
                observed_at=float(self.observed_at),
                observations=self.observations,
            )
        )
        if self.digest != expected:
            raise ValueError("HostDiscoveryV1 digest mismatch")

    @classmethod
    def create(
        cls,
        *,
        source_generation: str,
        observed_at: float,
        observations: Mapping[str, HostObservationV1],
    ) -> "HostDiscoveryV1":
        source = _text(source_generation, "source_generation")
        when = _timestamp(observed_at)
        copied = dict(observations)
        if set(copied) != _REQUIRED_OBSERVATION_SET:
            raise ValueError(
                "HostDiscoveryV1 requires exactly the declared H1 observation fields"
            )
        payload = _discovery_payload(
            source_generation=source,
            observed_at=when,
            observations=copied,
        )
        return cls(
            source_generation=source,
            observed_at=when,
            observations=copied,
            digest=stable_digest(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        result = _discovery_payload(
            source_generation=self.source_generation,
            observed_at=float(self.observed_at),
            observations=self.observations,
        )
        result["digest"] = self.digest
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HostDiscoveryV1":
        expected = frozenset(
            {
                "source_generation",
                "observed_at",
                "observations",
                "digest",
                "version",
                "patch_authority",
                "vsa_patch_authority",
            }
        )
        _exact_keys(value, expected, "HostDiscoveryV1")
        raw_observations = value["observations"]
        if not isinstance(raw_observations, Mapping):
            raise ValueError("observations must be a mapping")
        if set(raw_observations) != _REQUIRED_OBSERVATION_SET:
            raise ValueError("serialized observations do not match H1 schema")
        observations = {
            key: HostObservationV1.from_dict(raw_observations[key])
            for key in REQUIRED_OBSERVATIONS
        }
        return cls(
            source_generation=value["source_generation"],
            observed_at=value["observed_at"],
            observations=observations,
            digest=value["digest"],
            version=value["version"],
            patch_authority=value["patch_authority"],
            vsa_patch_authority=value["vsa_patch_authority"],
        )


def _observe_text(value: Any, source: str, detail: str = "") -> HostObservationV1:
    if type(value) is str and value.strip():
        return HostObservationV1.observed(value.strip(), source=source, detail=detail)
    return HostObservationV1.missing(
        ObservationState.UNKNOWN,
        source=source,
        detail=detail or "probe returned no usable value",
    )


def _observe_cpu_logical() -> HostObservationV1:
    try:
        value = os.cpu_count()
    except Exception as exc:  # defensive boundary around host API
        return HostObservationV1.missing(
            ObservationState.ERROR,
            source="os.cpu_count",
            detail=f"{type(exc).__name__}: host API failed",
        )
    if type(value) is int and value > 0:
        return HostObservationV1.observed(value, source="os.cpu_count")
    return HostObservationV1.missing(
        ObservationState.UNKNOWN,
        source="os.cpu_count",
        detail="logical CPU count unavailable",
    )


def _observe_cpu_physical() -> HostObservationV1:
    return HostObservationV1.missing(
        ObservationState.UNKNOWN,
        source="stdlib:no_portable_physical_core_probe",
        detail="H1 does not infer physical cores from logical cores",
    )


def _observe_ram_bytes() -> HostObservationV1:
    if not hasattr(os, "sysconf"):
        return HostObservationV1.missing(
            ObservationState.UNKNOWN,
            source="os.sysconf",
            detail="portable RAM probe unavailable on this host",
        )
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
        if type(page_size) is int and type(pages) is int and page_size > 0 and pages > 0:
            return HostObservationV1.observed(
                page_size * pages,
                source="os.sysconf:SC_PAGE_SIZE*SC_PHYS_PAGES",
            )
    except (OSError, ValueError, TypeError):
        pass
    return HostObservationV1.missing(
        ObservationState.UNKNOWN,
        source="os.sysconf:SC_PAGE_SIZE*SC_PHYS_PAGES",
        detail="RAM total unavailable",
    )


def _observe_storage(root_path: str | os.PathLike[str] | None) -> tuple[HostObservationV1, HostObservationV1]:
    if root_path is None:
        anchor = Path.home().anchor or os.sep
        target = Path(anchor)
    else:
        target = Path(root_path)
    try:
        usage = shutil.disk_usage(target)
    except (OSError, ValueError):
        missing = HostObservationV1.missing(
            ObservationState.ERROR,
            source="shutil.disk_usage",
            detail="storage probe failed",
        )
        return missing, missing
    return (
        HostObservationV1.observed(usage.total, source="shutil.disk_usage"),
        HostObservationV1.observed(usage.free, source="shutil.disk_usage"),
    )


def _observe_thermal() -> HostObservationV1:
    try:
        from aura_thermal import read_cpu_temp_c

        # NaN is intentionally used as a sentinel only at the owner boundary.
        # aura_thermal returns its fallback iff no source is usable; replacing the
        # fallback with NaN lets H1 distinguish "no observation" from a real,
        # finite thermal reading without changing aura_thermal's runtime-gate API.
        value = read_cpu_temp_c(fallback=float("nan"))
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        return HostObservationV1.missing(
            ObservationState.ERROR,
            source="aura_thermal.read_cpu_temp_c",
            detail=f"{type(exc).__name__}: thermal observation failed",
        )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            return HostObservationV1.observed(
                number,
                source="aura_thermal.read_cpu_temp_c(fallback=nan)",
                detail="finite value came from an aura_thermal observation source; fallback is NaN",
            )
    return HostObservationV1.missing(
        ObservationState.UNKNOWN,
        source="aura_thermal.read_cpu_temp_c(fallback=nan)",
        detail="no finite thermal observation; runtime fallback is not treated as evidence",
    )


def _observe_accelerators() -> HostObservationV1:
    hints: list[str] = []
    try:
        if Path("/dev/kfd").exists() or Path("/opt/rocm").exists():
            hints.append("ROCM_RUNTIME_HINT")
        if Path("/dev/amdxdna").exists() or Path("/sys/class/accel").exists():
            hints.append("XDNA_RUNTIME_HINT")
        if shutil.which("nvidia-smi") or shutil.which("nvidia-smi.exe"):
            hints.append("NVIDIA_CLI_HINT")
    except OSError:
        return HostObservationV1.missing(
            ObservationState.ERROR,
            source="local_accelerator_presence_hints",
            detail="accelerator presence probe failed",
        )
    if hints:
        return HostObservationV1.observed(
            sorted(set(hints)),
            source="local_accelerator_presence_hints",
            detail="presence hints only; not performance, permission, or execution authority",
        )
    return HostObservationV1.missing(
        ObservationState.UNKNOWN,
        source="local_accelerator_presence_hints",
        detail="absence of known hints does not prove accelerator absence",
    )


def _observe_linux_power_supply(
    power_supply_root: str | os.PathLike[str] = "/sys/class/power_supply",
) -> tuple[HostObservationV1, HostObservationV1]:
    system = platform.system().lower()
    if system not in {"linux", "android"}:
        missing = HostObservationV1.missing(
            ObservationState.UNKNOWN,
            source="linux_power_supply_sysfs",
            detail="H1 has no source-bound portable battery probe for this platform",
        )
        return missing, missing
    root = Path(power_supply_root)
    try:
        entries = sorted(root.iterdir()) if root.exists() else []
    except OSError:
        error = HostObservationV1.missing(
            ObservationState.ERROR,
            source="linux_power_supply_sysfs",
            detail="power-supply enumeration failed",
        )
        return error, error

    battery_capacity: float | None = None
    external_online: bool | None = None
    for entry in entries[:_MAX_COLLECTION]:
        try:
            supply_type = (entry / "type").read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if supply_type == "Battery":
            try:
                capacity_text = (entry / "capacity").read_text(encoding="utf-8", errors="replace").strip()
                capacity = float(capacity_text)
                if math.isfinite(capacity) and 0.0 <= capacity <= 100.0:
                    battery_capacity = capacity
            except (OSError, ValueError):
                pass
        elif supply_type in {"Mains", "USB", "USB_C"}:
            try:
                online = (entry / "online").read_text(encoding="utf-8", errors="replace").strip()
                if online in {"0", "1"}:
                    external_online = external_online is True or online == "1"
            except OSError:
                pass

    if battery_capacity is None:
        battery = HostObservationV1.missing(
            ObservationState.UNAVAILABLE if entries else ObservationState.UNKNOWN,
            source="linux_power_supply_sysfs",
            detail="no observed battery percentage",
        )
    else:
        battery = HostObservationV1.observed(
            battery_capacity, source="linux_power_supply_sysfs:capacity"
        )

    if external_online is None:
        power = HostObservationV1.missing(
            ObservationState.UNKNOWN,
            source="linux_power_supply_sysfs",
            detail="external-power state unavailable",
        )
    else:
        power = HostObservationV1.observed(
            "EXTERNAL_POWER" if external_online else "NO_EXTERNAL_POWER_OBSERVED",
            source="linux_power_supply_sysfs:online",
            detail="observation only; not battery-health or runtime-permission evidence",
        )
    return battery, power


def _observe_network_class() -> HostObservationV1:
    try:
        interfaces = socket.if_nameindex()
    except (AttributeError, OSError):
        return HostObservationV1.missing(
            ObservationState.UNKNOWN,
            source="socket.if_nameindex",
            detail="local interface inventory unavailable",
        )
    return HostObservationV1.observed(
        "LOCAL_INTERFACES_PRESENT" if interfaces else "NO_LOCAL_INTERFACES_OBSERVED",
        source="socket.if_nameindex",
        detail="does not probe internet/provider reachability and stores no interface names or addresses",
    )


def _observe_python_runtime() -> HostObservationV1:
    return HostObservationV1.observed(
        {
            "implementation": platform.python_implementation(),
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
        },
        source="sys.version_info+platform.python_implementation",
    )


def _observe_runtime_binaries(required_binaries: Iterable[str]) -> HostObservationV1:
    if isinstance(required_binaries, (str, bytes, bytearray)):
        raise ValueError("required_binaries must be an iterable of binary names")
    names = tuple(required_binaries)
    if len(names) > _MAX_COLLECTION:
        raise ValueError("too many required_binaries")
    canonical: list[str] = []
    for value in names:
        if type(value) is not str or not _BINARY_NAME_RE.fullmatch(value):
            raise ValueError("required_binaries must contain simple binary names, not paths")
        canonical.append(value)
    if len(set(canonical)) != len(canonical):
        raise ValueError("required_binaries must not contain duplicates")
    result = {name: shutil.which(name) is not None for name in sorted(canonical)}
    return HostObservationV1.observed(
        result,
        source="shutil.which",
        detail="boolean presence only; resolved executable paths are not retained",
    )


def discover_host_v1(
    *,
    source_generation: str,
    observed_at: float | None = None,
    required_binaries: Iterable[str] = (),
    storage_root: str | os.PathLike[str] | None = None,
    power_supply_root: str | os.PathLike[str] = "/sys/class/power_supply",
) -> HostDiscoveryV1:
    """Perform bounded, local, read-only H1 discovery and return HostDiscoveryV1.

    This function does not request permission, contact a provider, test internet
    reachability, select a runtime profile, or authorize an effect.
    """

    when = time.time() if observed_at is None else _timestamp(observed_at)
    storage_total, storage_free = _observe_storage(storage_root)
    battery, power = _observe_linux_power_supply(power_supply_root)
    observations = {
        "platform_family": _observe_text(platform.system(), "platform.system"),
        "os_release": _observe_text(platform.release(), "platform.release"),
        "architecture": _observe_text(platform.machine(), "platform.machine"),
        "cpu_logical": _observe_cpu_logical(),
        "cpu_physical": _observe_cpu_physical(),
        "ram_bytes": _observe_ram_bytes(),
        "storage_total_bytes": storage_total,
        "storage_free_bytes": storage_free,
        "thermal_c": _observe_thermal(),
        "accelerators": _observe_accelerators(),
        "battery_percent": battery,
        "power_source": power,
        "network_class": _observe_network_class(),
        "python_runtime": _observe_python_runtime(),
        "runtime_binaries": _observe_runtime_binaries(required_binaries),
    }
    return HostDiscoveryV1.create(
        source_generation=_text(source_generation, "source_generation"),
        observed_at=when,
        observations=observations,
    )
