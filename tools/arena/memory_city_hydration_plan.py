from __future__ import annotations

"""Deterministic exact-span hydration planning for Memory City Navigator.

D0/non-promoting. This module schedules already-bound SourceSpanLocator handles;
it does not fetch sources, change K27 storage, or mint source/truth/effect authority.
"""
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any
from memory_city_navigator import SourceSpanLocator, NavigatorError, digest


class HydrationPlanDisposition(str, Enum):
    READY = "READY"
    HOLD_BUDGET = "HOLD_BUDGET"
    HOLD_COLLISION = "HOLD_COLLISION"


@dataclass(frozen=True)
class HydrationPlan:
    disposition: HydrationPlanDisposition
    required_spans: tuple[SourceSpanLocator, ...]
    selected_bytes: int
    max_hydration_bytes: int
    reasons: tuple[str, ...]
    receipt_root: str
    authority_minted: bool = False


def compile_hydration_plan(locators: tuple[SourceSpanLocator, ...], *, max_hydration_bytes: int) -> HydrationPlan:
    if type(max_hydration_bytes) is not int or max_hydration_bytes < 0:
        raise NavigatorError("max_hydration_bytes must be nonnegative")
    if not locators:
        raise NavigatorError("at least one source span is required")

    exact: dict[tuple[Any, ...], SourceSpanLocator] = {}
    logical: dict[tuple[str, int, int], tuple[str, str]] = {}
    reasons: list[str] = []
    for locator in locators:
        logical_key = (locator.source_id, locator.start_line, locator.end_line)
        identity = (locator.parent_export_sha256, locator.span_sha256)
        prior = logical.get(logical_key)
        if prior is not None and prior != identity:
            reasons.append("CONSEQUENCE_DISTINCT_SOURCE_SPAN_COLLISION")
        logical[logical_key] = identity
        exact_key = (locator.source_id, locator.parent_export_sha256, locator.start_line,
                     locator.end_line, locator.span_sha256, locator.span_bytes, locator.k27_hint)
        exact[exact_key] = locator

    required = tuple(sorted(exact.values(), key=lambda x: (x.source_id, x.start_line, x.end_line, x.span_sha256)))
    selected = sum(x.span_bytes for x in required)
    if reasons:
        disposition = HydrationPlanDisposition.HOLD_COLLISION
    elif selected > max_hydration_bytes:
        disposition = HydrationPlanDisposition.HOLD_BUDGET
        reasons.append("HYDRATION_BUDGET_EXCEEDED")
    else:
        disposition = HydrationPlanDisposition.READY

    payload = {
        "schema": "AURA-MEMORY-CITY-HYDRATION-PLAN-v1",
        "disposition": disposition.value,
        "selected_bytes": selected,
        "max_hydration_bytes": max_hydration_bytes,
        "reasons": sorted(set(reasons)),
        "required_spans": [asdict(x) for x in required],
        "authority_minted": False,
    }
    return HydrationPlan(disposition, required, selected, max_hydration_bytes,
                         tuple(sorted(set(reasons))), digest(payload))
