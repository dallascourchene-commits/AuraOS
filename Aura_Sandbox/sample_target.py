"""
Small benchmark target used by Aura's proxy benchmark sandbox task.
"""

from __future__ import annotations


def _coerce_values(values: list[float] | tuple[float, ...]) -> list[float]:
    return [float(value) for value in values]


def describe_score(values: list[float] | tuple[float, ...]) -> str:
    data = _coerce_values(values)
    if not data:
        return "empty"
    return f"count={len(data)}"


def compute_score(values: list[float], weight: float = 1.0) -> float:
    data = _coerce_values(values)
    return sum(data) / len(data)
