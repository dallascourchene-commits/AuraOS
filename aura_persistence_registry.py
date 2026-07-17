"""Compatibility facade for Aura's canonical temporal checkpoint registry."""
from aura_temporal_persistence import (
    PATCH_AUTHORITY,
    RESTORATION_ASSESSMENT_VERSION,
    TEMPORAL_CHECKPOINT_VERSION,
    TEMPORAL_PERSISTENCE_VERSION,
    TEMPORAL_REGISTRY_VERSION,
    VSA_PATCH_AUTHORITY,
    RestorationAssessment,
    TemporalCheckpoint,
    TemporalCheckpointRegistry,
    checkpoint_refactor_state,
    verify_refactor_checkpoint,
)

__all__ = [
    "PATCH_AUTHORITY",
    "RESTORATION_ASSESSMENT_VERSION",
    "TEMPORAL_CHECKPOINT_VERSION",
    "TEMPORAL_PERSISTENCE_VERSION",
    "TEMPORAL_REGISTRY_VERSION",
    "VSA_PATCH_AUTHORITY",
    "RestorationAssessment",
    "TemporalCheckpoint",
    "TemporalCheckpointRegistry",
    "checkpoint_refactor_state",
    "verify_refactor_checkpoint",
]
