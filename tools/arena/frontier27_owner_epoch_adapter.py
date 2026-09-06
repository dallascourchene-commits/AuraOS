"""D0 owner-epoch adapter for Frontier-27 with a non-bypassable public state surface.

The canonical owner remains untouched. This adapter demonstrates the owner
migration shape: mutable residency/counters are private; public state is
read-only; every governed mutation advances one monotone epoch.
"""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Tuple

from frontier27_runtime import FrontierOffload


class EpochExpertResidencyLRU:
    __slots__ = ("capacity", "_residency", "_hits", "_misses", "_mutation_epoch")

    def __init__(self, capacity: int):
        if type(capacity) is not int or capacity < 0:
            raise ValueError("capacity must be a non-negative integer")
        self.capacity = capacity
        self._residency = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._mutation_epoch = 0

    @property
    def r(self) -> Mapping[int, None]:
        return MappingProxyType(self._residency)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def mutation_epoch(self) -> int:
        return self._mutation_epoch

    def _advance_epoch(self) -> None:
        self._mutation_epoch += 1

    def access(self, x: int) -> bool:
        hit = x in self._residency
        self._hits += int(hit)
        self._misses += int(not hit)
        if hit:
            self._residency.move_to_end(x)
        else:
            self._residency[x] = None
            if len(self._residency) > self.capacity:
                self._residency.popitem(last=False)
        self._advance_epoch()
        return hit

    def resident(self, x: int) -> bool:
        return x in self._residency

    def prefetch(self, x: int) -> None:
        if x in self._residency:
            self._residency.move_to_end(x)
        else:
            self._residency[x] = None
            if len(self._residency) > self.capacity:
                self._residency.popitem(last=False)
        self._advance_epoch()


class EpochFrontierOffload(FrontierOffload):
    """Canonical FrontierOffload algorithm with the epoch-governed owner."""
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
    return ResidencyEpochSnapshot(owner.mutation_epoch, tuple(owner.r.keys()), owner.hits, owner.misses)


def unchanged(owner: EpochExpertResidencyLRU, before: ResidencyEpochSnapshot) -> bool:
    return (
        owner.mutation_epoch == before.mutation_epoch
        and tuple(owner.r.keys()) == before.order
        and owner.hits == before.hits
        and owner.misses == before.misses
    )


def governed_aba_probe() -> bool:
    """Return True only when a visible-state ABA is detected by the epoch."""
    owner = EpochExpertResidencyLRU(3)
    for value in (1, 2, 3):
        owner.prefetch(value)
    before = snapshot(owner)
    visible = (tuple(owner.r.items()), owner.hits, owner.misses)
    for value in (1, 2, 3):
        owner.prefetch(value)
    return (tuple(owner.r.items()), owner.hits, owner.misses) == visible and not unchanged(owner, before)
