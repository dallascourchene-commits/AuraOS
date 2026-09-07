from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from .route_card_admission import Admission, Disposition, ProofReceipt, UseContext, admit


class DeltaStrategy(str, Enum):
    NO_GEOMETRY_REBUILD = "NO_GEOMETRY_REBUILD"
    SELECTIVE = "SELECTIVE"
    EAGER_SHARED = "EAGER_SHARED"


@dataclass(frozen=True)
class RouteSegment:
    segment_id: str
    corridor_nodes: frozenset[str]
    receipt: ProofReceipt

    def __post_init__(self) -> None:
        if not isinstance(self.segment_id, str) or not self.segment_id:
            raise ValueError("segment_id required")
        if not isinstance(self.corridor_nodes, frozenset) or not self.corridor_nodes:
            raise ValueError("corridor_nodes must be non-empty frozenset")
        if any(not isinstance(n, str) or not n for n in self.corridor_nodes):
            raise ValueError("corridor node ids must be non-empty strings")


@dataclass(frozen=True)
class RouteChange:
    changed_nodes: frozenset[str]
    geometry_changed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.changed_nodes, frozenset):
            raise ValueError("changed_nodes must be frozenset")
        if any(not isinstance(n, str) or not n for n in self.changed_nodes):
            raise ValueError("changed node ids must be non-empty strings")
        if self.geometry_changed and not self.changed_nodes:
            raise ValueError("geometry change requires at least one changed node")


@dataclass(frozen=True)
class SegmentDecision:
    segment_id: str
    admission: Admission
    geometry_recompute: bool
    evidence_query_required: bool


@dataclass(frozen=True)
class DeltaPlan:
    strategy: DeltaStrategy
    selected_segment_ids: tuple[str, ...]
    geometry_recomputations: int
    decisions: tuple[SegmentDecision, ...]
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def _coverage(selected: int, total: int) -> float:
    return 0.0 if total == 0 else selected / total


def plan_route_delta(
    segments: Sequence[RouteSegment],
    use_contexts: Mapping[str, UseContext],
    change: RouteChange,
    *,
    eager_threshold: float = 0.5,
) -> DeltaPlan:
    """Compile the smallest lawful route re-evaluation set.

    Geometry change selects corridor-intersecting segments and switches to an
    eager shared pass when the affected fraction is dense. Pure lifecycle,
    currentness, event-time, capability, or evidence movement does not rebuild
    geometry; every segment still passes its at-use admission gate.
    """
    if not 0.0 < eager_threshold <= 1.0:
        raise ValueError("eager_threshold must be in (0,1]")
    ids = [s.segment_id for s in segments]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate segment_id")
    if set(ids) != set(use_contexts):
        raise ValueError("use_contexts must bind exactly every segment")

    if change.geometry_changed:
        affected = [s.segment_id for s in segments if s.corridor_nodes & change.changed_nodes]
        if _coverage(len(affected), len(segments)) >= eager_threshold:
            selected = tuple(ids)
            strategy = DeltaStrategy.EAGER_SHARED
        else:
            selected = tuple(affected)
            strategy = DeltaStrategy.SELECTIVE
    else:
        selected = ()
        strategy = DeltaStrategy.NO_GEOMETRY_REBUILD

    selected_set = set(selected)
    decisions = []
    for segment in segments:
        admission = admit(segment.receipt, use_contexts[segment.segment_id])
        geometry_recompute = segment.segment_id in selected_set
        evidence_query_required = admission.disposition in (Disposition.REPROVE, Disposition.READY_D0)
        decisions.append(SegmentDecision(
            segment_id=segment.segment_id,
            admission=admission,
            geometry_recompute=geometry_recompute,
            evidence_query_required=evidence_query_required,
        ))

    return DeltaPlan(
        strategy=strategy,
        selected_segment_ids=selected,
        geometry_recomputations=len(selected),
        decisions=tuple(decisions),
    )
