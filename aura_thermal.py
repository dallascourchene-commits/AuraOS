"""
Small thermal-sensor helpers for Aura runtime gates.

Laptops, containers, and some Termux installs do not expose Linux thermal
zones. Treating that absence as 42 C makes Aura falsely skip cool-state work,
so the shared fallback is an operator-safe idle value.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


DEFAULT_THERMAL_FALLBACK_C = 39.0
DEFAULT_THERMAL_PATHS = tuple(
    Path(f"/sys/class/thermal/thermal_zone{idx}/temp")
    for idx in range(8)
)


def thermal_fallback_c() -> float:
    """Return the configured cool fallback when no sensor is available."""
    try:
        return float(os.environ.get("AURA_THERMAL_FALLBACK_C", DEFAULT_THERMAL_FALLBACK_C))
    except (TypeError, ValueError):
        return DEFAULT_THERMAL_FALLBACK_C


def _parse_temp_c(raw: str) -> float | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value > 1000.0:
        value /= 1000.0
    if -40.0 <= value <= 125.0:
        return value
    return None


def read_cpu_temp_c(
    *,
    fallback: float | None = None,
    paths: Iterable[str | os.PathLike[str]] | None = None,
) -> float:
    """Read the first usable CPU thermal-zone value, else return fallback."""
    fallback_value = thermal_fallback_c() if fallback is None else float(fallback)
    for path_value in paths or DEFAULT_THERMAL_PATHS:
        path = Path(path_value)
        try:
            parsed = _parse_temp_c(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if parsed is not None:
            return parsed
    return fallback_value
