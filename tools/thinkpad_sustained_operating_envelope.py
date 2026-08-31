"""Read-only ThinkPad/Linux sustained operating-envelope observer.

The observer records what the supplied proc/sys filesystem roots expose about
memory/swap pressure, power supplies, thermal zones, and CPU frequency state.
It never writes those files and never infers thermal throttling, battery safety,
performance superiority, or model execution from the observations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "AuraThinkPadSustainedOperatingEnvelopeV1"
CURRENTNESS_DOMAIN = "owner-host-operating-envelope-observation-generation"
MAX_SENSOR_FILES = 4096


class OperatingEnvelopeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise OperatingEnvelopeError("NONCANONICAL_ENVELOPE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _read_text(path: Path, limit: int = 64 * 1024) -> str | None:
    try:
        if not path.is_file() or path.is_symlink():
            return None
        data = path.read_bytes()
    except (OSError, PermissionError):
        return None
    if len(data) > limit:
        return None
    try:
        return data.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError:
        return None


def _int_text(path: Path) -> int | None:
    text = _read_text(path, 256)
    if text is None:
        return None
    try:
        return int(text, 10)
    except ValueError:
        return None


def _parse_meminfo(text: str | None) -> dict[str, int | None]:
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    out: dict[str, int | None] = {key: None for key in wanted}
    if text is None:
        return out
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        if key not in wanted:
            continue
        parts = raw.strip().split()
        if not parts:
            continue
        try:
            value = int(parts[0])
        except ValueError:
            continue
        unit = parts[1] if len(parts) > 1 else ""
        if unit not in ("", "kB"):
            continue
        out[key] = value * 1024 if unit == "kB" else value
    return out


def _parse_psi(text: str | None) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    if text is None:
        return result
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0] not in ("some", "full"):
            continue
        metrics: dict[str, float | int] = {}
        for token in parts[1:]:
            if "=" not in token:
                continue
            key, raw = token.split("=", 1)
            try:
                if key == "total":
                    metrics[key] = int(raw)
                else:
                    value = float(raw)
                    if math.isfinite(value) and value >= 0:
                        metrics[key] = value
            except ValueError:
                continue
        result[parts[0]] = metrics
    return result


def _bounded_dirs(root: Path, pattern: str) -> list[Path]:
    try:
        dirs = sorted(path for path in root.glob(pattern) if path.is_dir() and not path.is_symlink())
    except OSError:
        return []
    if len(dirs) > MAX_SENSOR_FILES:
        raise OperatingEnvelopeError("SENSOR_CARDINALITY_EXCEEDED")
    return dirs


@dataclass(frozen=True)
class PowerSupplyObservation:
    name: str
    kind: str | None
    online: int | None
    capacity_percent: int | None
    status: str | None
    energy_now_uwh: int | None
    power_now_uw: int | None


@dataclass(frozen=True)
class ThermalObservation:
    zone: str
    sensor_type: str | None
    temperature_millicelsius: int | None


@dataclass(frozen=True)
class CpuFrequencyObservation:
    policy: str
    current_khz: int | None
    min_khz: int | None
    max_khz: int | None


@dataclass(frozen=True)
class SustainedOperatingEnvelope:
    observed_at_utc: str
    proc_root: str
    sys_root: str
    os_release: str | None
    kernel_version: str | None
    mem_total_bytes: int | None
    mem_available_bytes: int | None
    swap_total_bytes: int | None
    swap_free_bytes: int | None
    memory_available_ratio: float | None
    swap_free_ratio: float | None
    memory_psi: dict[str, dict[str, float | int]]
    power_supplies: tuple[PowerSupplyObservation, ...]
    thermal_zones: tuple[ThermalObservation, ...]
    cpu_frequency_policies: tuple[CpuFrequencyObservation, ...]
    currentness_domain: str = CURRENTNESS_DOMAIN
    current_at_observation_time_only: bool = True
    thinkpad_identity_proven: bool = False
    thermal_throttling_proven: bool = False
    battery_power_limit_proven: bool = False
    memory_pressure_safe_for_model: bool = False
    performance_effect_proven: bool = False
    model_execution_observed: bool = False
    producer_authenticated: bool = False
    effect_authority_proven: bool = False
    g2_admitted: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def observation_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def evidence_ref(self) -> str:
        return f"thinkpad-operating-envelope-sha256:{self.observation_digest}"


def _power_supplies(sys_root: Path) -> tuple[PowerSupplyObservation, ...]:
    out: list[PowerSupplyObservation] = []
    for path in _bounded_dirs(sys_root / "class" / "power_supply", "*"):
        out.append(
            PowerSupplyObservation(
                name=path.name,
                kind=_read_text(path / "type", 256),
                online=_int_text(path / "online"),
                capacity_percent=_int_text(path / "capacity"),
                status=_read_text(path / "status", 256),
                energy_now_uwh=_int_text(path / "energy_now"),
                power_now_uw=_int_text(path / "power_now"),
            )
        )
    return tuple(out)


def _thermal_zones(sys_root: Path) -> tuple[ThermalObservation, ...]:
    out: list[ThermalObservation] = []
    for path in _bounded_dirs(sys_root / "class" / "thermal", "thermal_zone*"):
        out.append(
            ThermalObservation(
                zone=path.name,
                sensor_type=_read_text(path / "type", 256),
                temperature_millicelsius=_int_text(path / "temp"),
            )
        )
    return tuple(out)


def _cpu_frequencies(sys_root: Path) -> tuple[CpuFrequencyObservation, ...]:
    cpufreq_root = sys_root / "devices" / "system" / "cpu" / "cpufreq"
    out: list[CpuFrequencyObservation] = []
    for path in _bounded_dirs(cpufreq_root, "policy*"):
        out.append(
            CpuFrequencyObservation(
                policy=path.name,
                current_khz=_int_text(path / "scaling_cur_freq"),
                min_khz=_int_text(path / "scaling_min_freq"),
                max_khz=_int_text(path / "scaling_max_freq"),
            )
        )
    return tuple(out)


def observe_sustained_operating_envelope(
    *,
    proc_root: str = "/proc",
    sys_root: str = "/sys",
    observed_at_utc: str | None = None,
) -> SustainedOperatingEnvelope:
    """Observe one read-only operating-envelope generation.

    Custom roots exist so the observer can be falsified with synthetic fixture
    trees. Their values are carried into the receipt; using fixture roots never
    proves that a ThinkPad was observed.
    """
    proc = Path(proc_root)
    sys = Path(sys_root)
    if not proc.is_absolute() or not sys.is_absolute():
        raise OperatingEnvelopeError("OBSERVATION_ROOT_MUST_BE_ABSOLUTE")
    timestamp = observed_at_utc or datetime.now(timezone.utc).isoformat()
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise OperatingEnvelopeError("OBSERVATION_TIME_REQUIRED")

    mem = _parse_meminfo(_read_text(proc / "meminfo"))
    mem_total = mem["MemTotal"]
    mem_available = mem["MemAvailable"]
    swap_total = mem["SwapTotal"]
    swap_free = mem["SwapFree"]
    mem_ratio = (
        mem_available / mem_total
        if isinstance(mem_available, int) and isinstance(mem_total, int) and mem_total > 0
        else None
    )
    swap_ratio = (
        swap_free / swap_total
        if isinstance(swap_free, int) and isinstance(swap_total, int) and swap_total > 0
        else None
    )

    return SustainedOperatingEnvelope(
        observed_at_utc=timestamp.strip(),
        proc_root=str(proc),
        sys_root=str(sys),
        os_release=_read_text(proc / "sys" / "kernel" / "osrelease", 4096),
        kernel_version=_read_text(proc / "version", 4096),
        mem_total_bytes=mem_total,
        mem_available_bytes=mem_available,
        swap_total_bytes=swap_total,
        swap_free_bytes=swap_free,
        memory_available_ratio=mem_ratio,
        swap_free_ratio=swap_ratio,
        memory_psi=_parse_psi(_read_text(proc / "pressure" / "memory", 16 * 1024)),
        power_supplies=_power_supplies(sys),
        thermal_zones=_thermal_zones(sys),
        cpu_frequency_policies=_cpu_frequencies(sys),
    )
