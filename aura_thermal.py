"""
Cross-platform thermal-sensor helpers for Aura runtime gates.

Linux laptops, containers, Windows systems, and some Termux/mobile installs
expose temperature through different sources and scales. Aura normalizes
bounded Celsius, Kelvin, deci-Kelvin, milli-Celsius, and milli-Kelvin readings
to Celsius before applying runtime thermal gates.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable


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
_WINDOWS_ACPI_THERMAL_COMMAND = (
    "powershell.exe",
    "-NoProfile",
    "-NonInteractive",
    "-Command",
    "$ErrorActionPreference = 'Stop'; "
    "Get-CimInstance -Namespace root/wmi "
    "-ClassName MSAcpi_ThermalZoneTemperature | "
    "ForEach-Object { $_.CurrentTemperature }",
)


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
    text = str(raw or "").strip()
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

    # Order keeps ordinary Celsius exact, recognizes Windows ACPI deci-Kelvin,
    # and still preserves Linux/Android milli-Celsius readings.
    candidates = (
        value,
        value - KELVIN_OFFSET_C,
        value / 10.0 - KELVIN_OFFSET_C,
        value / 1000.0 - KELVIN_OFFSET_C,
        value / 1000.0,
    )
    for candidate in candidates:
        parsed = _bounded_celsius(candidate)
        if parsed is not None:
            return parsed
    return None


def _discover_thermal_paths() -> tuple[Path, ...]:
    """Discover Linux/Android thermal-zone and laptop hwmon sensor files."""
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
    return tuple(discovered) if discovered else DEFAULT_THERMAL_PATHS


def _read_psutil_temp_c() -> float | None:
    """Read an optional psutil temperature source without requiring psutil."""
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
    for entries in groups.values():
        for entry in entries or ():
            parsed = _parse_temp_c(getattr(entry, "current", None), unit_hint="celsius")
            if parsed is not None:
                return parsed
    return None


def _read_windows_acpi_temp_c() -> float | None:
    """Read Windows ACPI thermal-zone values, reported in tenths Kelvin."""
    if os.name != "nt":
        return None
    try:
        completed = subprocess.run(
            _WINDOWS_ACPI_THERMAL_COMMAND,
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    for line in completed.stdout.splitlines():
        parsed = _parse_temp_c(line, unit_hint="decikelvin")
        if parsed is not None:
            return parsed
    return None


def read_cpu_temp_c(
    *,
    fallback: float | None = None,
    paths: Iterable[str | os.PathLike[str]] | None = None,
) -> float:
    """Read the first usable device temperature and normalize it to Celsius."""
    fallback_value = thermal_fallback_c() if fallback is None else float(fallback)
    source_paths = _discover_thermal_paths() if paths is None else paths
    for path_value in source_paths:
        path = Path(path_value)
        try:
            parsed = _parse_temp_c(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if parsed is not None:
            return parsed

    if paths is None:
        for provider in (_read_psutil_temp_c, _read_windows_acpi_temp_c):
            parsed = provider()
            if parsed is not None:
                return parsed
    return fallback_value
