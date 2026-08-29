"""AuraOS vNext convergence primitives.

This package is deliberately small. It contains bounded primitives that can be
reviewed independently from the historical AuraOS repository. The historical
repo remains provenance; vNext selects and adapts useful owners rather than
silently deleting them.
"""

from .visitor_capsule import (
    AuraVisitorCapsuleV1,
    ProposedDeltaV1,
    VisitorCapsuleError,
    build_l0_capsule,
    validate_capsule,
    validate_proposed_delta,
)
from .qdkt_guard import QDKTGuardedProjection, QDKTObservation, QDKTState

__all__ = [
    "AuraVisitorCapsuleV1",
    "ProposedDeltaV1",
    "VisitorCapsuleError",
    "build_l0_capsule",
    "validate_capsule",
    "validate_proposed_delta",
    "QDKTGuardedProjection",
    "QDKTObservation",
    "QDKTState",
]
