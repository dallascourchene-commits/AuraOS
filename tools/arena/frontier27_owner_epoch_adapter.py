"""D0 owner-epoch adapter for the canonical Frontier-27 residency owner.

This module adds a monotone mutation epoch to every governed residency write
without changing ExpertResidencyLRU's visible behavior. It deliberately does
not claim that direct mutation of the inherited public ``r`` mapping is fenced;
that compatibility surface remains an explicit raw-bypass negative control.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

from frontier27_runtime import ExpertResidencyLRU, FrontierOffload


class EpochExpertResidencyLRU(ExpertResidencyLRU):
    def __init__(self, capacity: int):
        super().__init__(capacity)
        self._mutation_epoch = 0

    @property
    def mutation_epoch(self) -> int:
        return self._mutation_epoch

    def _advance_epoch(self) -> None:
        self._mutation_epoch += 1

    def access(self, x: int) -> bool:
        result = super().access(x)
        self._advance_epoch()
        return result

    def prefetch(self, x: int) -> None:
        super().prefetch(x)
        self._advance_epoch()


class EpochFrontierOffload(FrontierOffload):
    """FrontierOffload using the epoch-governed residency owner."""
    def __init__(self, size, capacity, tier, window_s, budget_j):
        super().__init__(size, capacity, tier, window_s, budget_j)
        self.r = EpochExpertResidencyLRU(capacity)


@dataclass(frozen=True)
class ResidencyEpochSnapshot:
    mutation_epoch: int
    order: Tuple[int, ...]
    hits: int
    misses: int


def snapshot(owner: EpochExpertResidencyLRU) -> ResidencyEpochSnapshot:
    return ResidencyEpochSnapshot(
        owner.mutation_epoch,
        tuple(owner.r.keys()),
        owner.hits,
        owner.misses,
    )


def unchanged(owner: EpochExpertResidencyLRU, before: ResidencyEpochSnapshot) -> bool:
    return (
        owner.mutation_epoch == before.mutation_epoch
        and tuple(owner.r.keys()) == before.order
        and owner.hits == before.hits
        and owner.misses == before.misses
    )
