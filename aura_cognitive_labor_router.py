"""Public compatibility facade for fail-closed Aura cognitive-labor routing."""
from __future__ import annotations

from typing import Any

from aura_cognitive_labor_router_core import (
    COGNITIVE_LABOR_ROUTER_VERSION,
    CognitiveLaborDecision,
    route_failure as _route_failure,
    route_initial_refactor,
)


def route_failure(*, failure_packet: Any, local_repair_attempts: Any = None, **kwargs: Any) -> CognitiveLaborDecision:
    """Preserve the established ``None`` meaning: read repair evidence from the packet."""
    if local_repair_attempts is None:
        return _route_failure(failure_packet=failure_packet, **kwargs)
    return _route_failure(
        failure_packet=failure_packet,
        local_repair_attempts=local_repair_attempts,
        **kwargs,
    )


__all__ = [
    "COGNITIVE_LABOR_ROUTER_VERSION",
    "CognitiveLaborDecision",
    "route_failure",
    "route_initial_refactor",
]
