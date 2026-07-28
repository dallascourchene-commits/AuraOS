"""Canonical-owner orchestration for B11-B15 bilateral live repair."""
from __future__ import annotations

from aura_bilateral_live_repair_foundry_service_capture import _CapturePersistenceMixin
from aura_bilateral_live_repair_foundry_service_preview import _PreviewLearningProjectionMixin
from aura_bilateral_live_repair_foundry_service_runtime import _RuntimeRepairMixin


class BilateralLiveRepairService(
    _PreviewLearningProjectionMixin,
    _RuntimeRepairMixin,
    _CapturePersistenceMixin,
):
    """Stateful adapter over canonical Aura owners; no new authority plane."""


__all__ = ["BilateralLiveRepairService"]
