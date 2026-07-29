"""
Cross-platform thermal-sensor helpers for Aura runtime gates.

Linux laptops, containers, Windows systems, and some Termux/mobile installs
expose temperature through different sources and scales. Aura normalizes
bounded Celsius, Kelvin, milli-Celsius, and milli-Kelvin readings to Celsius
before applying runtime thermal gates.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import os
from pathlib import Path
import shutil

# Only a resolved PowerShell executable is invoked, with shell expansion disabled.
import subprocess  # nosec B404
from threading import Lock, Thread
from time import monotonic

DEFAULT_THERMAL_FALLBACK_C = 39.0
MIN_VALID_TEMP_C = -40.0
MAX_VALID_TEMP_C = 125.0
KELVIN_OFFSET_C = 273.15
DEFAULT_THERMAL_PATHS = tuple(
    Path(f"/sys/class/thermal/thermal_zone{idx}/temp")
    for idx in range(8)
)
_THERMAL_DISCOVERY_PATTERNS = (
    (Path("/sys/class/thermal"), "thermal_zone*/temp"),
    (Path("/sys/class/hwmon"), "hwmon*/temp*_input"),
)
_THERMAL_PATHS_CACHE_TTL_SECONDS = 30.0
_WINDOWS_ACPI_CACHE_TTL_SECONDS = 30.0
_WINDOWS_ACPI_FAILURE_CACHE_TTL_SECONDS = 60.0

_THERMAL_PATHS_CACHE: tuple[Path, ...] | None = None
_THERMAL_PATHS_CACHE_EXPIRES_AT = 0.0
_THERMAL_PATHS_CACHE_LOCK = Lock()

_WINDOWS_ACPI_CACHE_C: float | None = None
_WINDOWS_ACPI_CACHE_READY = False
_WINDOWS_ACPI_CACHE_EXPIRES_AT = 0.0
_WINDOWS_ACPI_PROBE_IN_FLIGHT = False
_WINDOWS_ACPI_CACHE_LOCK = Lock()


def thermal_fallback_c() -> float:
    """Return the configured cool fallback when no sensor is available."""
    try:
        return float(os.environ.get("AURA_THERMAL_FALLBACK_C", DEFAULT_THERMAL_FALLBACK_C))
    except (TypeError, ValueError):
        return DEFAULT_THERMAL_FALLBACK_C


def _bounded_celsius(value: float) -> float | None:
    return value if MIN_VALID_TEMP_C <= value <= MAX_VALID_TEMP_C else None


def _parse_temp_c(raw: object, *, unit_hint: str = "auto") -> float | None:
    """Normalize a bounded sensor reading to Celsius."""
    text = str(raw if raw is not None else "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None

    converters = {
        "celsius": lambda item: item,
        "millicelsius": lambda item: item / 1000.0,
        "kelvin": lambda item: item - KELVIN_OFFSET_C,
        "decikelvin": lambda item: item / 10.0 - KELVIN_OFFSET_C,
        "millikelvin": lambda item: item / 1000.0 - KELVIN_OFFSET_C,
    }
    if unit_hint != "auto":
        converter = converters.get(unit_hint)
        return _bounded_celsius(converter(value)) if converter is not None else None

    # Deci-Kelvin is intentionally excluded from inference because values overlap
    # with cold milli-Celsius readings. Platform providers pass an explicit hint.
    candidates = (
        value,
        value - KELVIN_OFFSET_C,
        value / 1000.0 - KELVIN_OFFSET_C,
        value / 1000.0,
    )
    for candidate in candidates:
        parsed = _bounded_celsius(candidate)
        if parsed is not None:
            return parsed
    return None


def _discover_thermal_paths() -> tuple[Path, ...]:
    """Discover and briefly cache Linux/Android thermal and laptop hwmon paths."""
    global _THERMAL_PATHS_CACHE, _THERMAL_PATHS_CACHE_EXPIRES_AT  # noqa: PLW0603

    now = monotonic()
    with _THERMAL_PATHS_CACHE_LOCK:
        if (
            _THERMAL_PATHS_CACHE is not None
            and now < _THERMAL_PATHS_CACHE_EXPIRES_AT
        ):
            return _THERMAL_PATHS_CACHE

    discovered: list[Path] = []
    seen: set[Path] = set()
    for root, pattern in _THERMAL_DISCOVERY_PATTERNS:
        try:
            matches = sorted(root.glob(pattern))
        except OSError:
            continue
        for path in matches:
            if path not in seen:
                seen.add(path)
                discovered.append(path)

    if discovered:
        resolved = tuple(discovered)
    elif os.name == "nt":
        resolved = ()
    else:
        resolved = DEFAULT_THERMAL_PATHS

    with _THERMAL_PATHS_CACHE_LOCK:
        _THERMAL_PATHS_CACHE = resolved
        _THERMAL_PATHS_CACHE_EXPIRES_AT = now + _THERMAL_PATHS_CACHE_TTL_SECONDS
    return resolved


def _read_psutil_temp_c() -> float | None:
    """Read the hottest optional psutil source without requiring psutil."""
    try:
        import psutil  # type: ignore[import-not-found]
    except ImportError:
        return None
    reader = getattr(psutil, "sensors_temperatures", None)
    if not callable(reader):
        return None
    try:
        groups = reader(fahrenheit=False)
    except (OSError, RuntimeError, NotImplementedError):
        return None
    if not isinstance(groups, dict):
        return None

    candidates: list[float] = []
    for entries in groups.values():
        for entry in entries or ():
            parsed = _parse_temp_c(getattr(entry, "current", None), unit_hint="celsius")
            if parsed is not None:
                candidates.append(parsed)
    return max(candidates) if candidates else None


def _run_windows_acpi_probe() -> float | None:
    """Perform one bounded Windows ACPI query and return Celsius."""
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        return None
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "Get-CimInstance -Namespace root/wmi "
        "-ClassName MSAcpi_ThermalZoneTemperature | "
        "ForEach-Object { $_.CurrentTemperature }"
    )
    try:
        # The executable and arguments are fixed; caller data never enters the command.
        completed = subprocess.run(  # nosec B603
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None

    candidates = [
        parsed
        for line in completed.stdout.splitlines()
        if (parsed := _parse_temp_c(line, unit_hint="decikelvin")) is not None
    ]
    return max(candidates) if candidates else None


def _store_windows_acpi_probe_result(value: float | None) -> None:
    global _WINDOWS_ACPI_CACHE_C, _WINDOWS_ACPI_CACHE_READY  # noqa: PLW0603
    global _WINDOWS_ACPI_CACHE_EXPIRES_AT, _WINDOWS_ACPI_PROBE_IN_FLIGHT  # noqa: PLW0603

    ttl = (
        _WINDOWS_ACPI_CACHE_TTL_SECONDS
        if value is not None
        else _WINDOWS_ACPI_FAILURE_CACHE_TTL_SECONDS
    )
    with _WINDOWS_ACPI_CACHE_LOCK:
        _WINDOWS_ACPI_CACHE_C = value
        _WINDOWS_ACPI_CACHE_READY = True
        _WINDOWS_ACPI_CACHE_EXPIRES_AT = monotonic() + ttl
        _WINDOWS_ACPI_PROBE_IN_FLIGHT = False


def _windows_acpi_probe_worker() -> None:
    _store_windows_acpi_probe_result(_run_windows_acpi_probe())


def _read_windows_acpi_temp_c() -> float | None:
    """Return cached Windows ACPI data and avoid blocking active event loops."""
    global _WINDOWS_ACPI_PROBE_IN_FLIGHT  # noqa: PLW0603

    if os.name != "nt":
        return None

    now = monotonic()
    with _WINDOWS_ACPI_CACHE_LOCK:
        cached = _WINDOWS_ACPI_CACHE_C
        if _WINDOWS_ACPI_CACHE_READY and now < _WINDOWS_ACPI_CACHE_EXPIRES_AT:
            return cached
        if _WINDOWS_ACPI_PROBE_IN_FLIGHT:
            return cached
        _WINDOWS_ACPI_PROBE_IN_FLIGHT = True

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        value = _run_windows_acpi_probe()
        _store_windows_acpi_probe_result(value)
        return value

    Thread(
        target=_windows_acpi_probe_worker,
        name="aura-windows-acpi-thermal",
        daemon=True,
    ).start()
    return cached


def read_cpu_temp_c(
    *,
    fallback: float | None = None,
    paths: Iterable[str | os.PathLike[str]] | None = None,
) -> float:
    """Read the hottest usable device temperature and normalize it to Celsius."""
    fallback_value = thermal_fallback_c() if fallback is None else float(fallback)
    source_paths = _discover_thermal_paths() if paths is None else paths
    unit_hint = "millicelsius" if paths is None else "auto"

    path_candidates: list[float] = []
    for path_value in source_paths:
        path = Path(path_value)
        try:
            parsed = _parse_temp_c(
                path.read_text(encoding="utf-8", errors="replace"),
                unit_hint=unit_hint,
            )
        except OSError:
            continue
        if parsed is not None:
            path_candidates.append(parsed)
    if path_candidates:
        return max(path_candidates)

    if paths is None:
        psutil_temp = _read_psutil_temp_c()
        if psutil_temp is not None:
            return psutil_temp
        windows_temp = _read_windows_acpi_temp_c()
        if windows_temp is not None:
            return windows_temp
    return fallback_value
