"""Public B11-B15 bilateral live-repair and Spatial Foundry adapter API.

Implementation is split into contracts, bounded capture, and canonical-owner
orchestration modules to keep each exact source slice reviewable.
"""
from aura_bilateral_live_repair_foundry_capture import BoundedIncidentCapture
from aura_bilateral_live_repair_foundry_contracts import (
    BilateralIdentity,
    BilateralLiveRepairError,
    CaptureDissolutionReceipt,
    IncidentEvent,
    IncidentReplayPacket,
    PreviewRollbackReceipt,
    RepairCandidateResult,
    RequiredAssetIdentity,
    canonical_bytes,
    canonical_sanitize,
    classify_repair_route,
    derive_repair_failure_class,
    digest,
)
from aura_bilateral_live_repair_foundry_service import BilateralLiveRepairService

__all__ = [
    "BilateralIdentity",
    "BilateralLiveRepairError",
    "BilateralLiveRepairService",
    "BoundedIncidentCapture",
    "CaptureDissolutionReceipt",
    "IncidentEvent",
    "IncidentReplayPacket",
    "PreviewRollbackReceipt",
    "RepairCandidateResult",
    "RequiredAssetIdentity",
    "canonical_bytes",
    "canonical_sanitize",
    "classify_repair_route",
    "derive_repair_failure_class",
    "digest",
]
