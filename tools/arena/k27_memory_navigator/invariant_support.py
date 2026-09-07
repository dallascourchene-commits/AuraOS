from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable, Sequence


class SupportState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class SupportDisposition(str, Enum):
    NO_REPROOF = "NO_REPROOF"
    SELECTIVE_REPROOF = "SELECTIVE_REPROOF"
    EAGER_SHARED_REPROOF = "EAGER_SHARED_REPROOF"
    HOLD_SUPPORT_UNCERTAINTY = "HOLD_SUPPORT_UNCERTAINTY"


@dataclass(frozen=True)
class HardInvariantSupport:
    invariant_id: str
    segment_ids: frozenset[str]
    state: SupportState = SupportState.CURRENT

    def __post_init__(self) -> None:
        if not isinstance(self.invariant_id, str) or not self.invariant_id:
            raise ValueError("invariant_id required")
        if not isinstance(self.segment_ids, frozenset) or not self.segment_ids:
            raise ValueError("segment_ids must be a non-empty frozenset")
        if any(not isinstance(x, str) or not x for x in self.segment_ids):
            raise ValueError("segment ids must be non-empty strings")
        if not isinstance(self.state, SupportState):
            raise ValueError("state must be exact SupportState")


@dataclass(frozen=True)
class InvariantSupportPlan:
    disposition: SupportDisposition
    reproof_segment_ids: tuple[str, ...]
    coordination_components: tuple[tuple[str, ...], ...]
    support_root: str
    support_refresh_required: bool
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def _support_root(supports: Sequence[HardInvariantSupport]) -> str:
    payload = [
        {
            "invariant_id": s.invariant_id,
            "segment_ids": sorted(s.segment_ids),
            "state": s.state.value,
        }
        for s in sorted(supports, key=lambda x: x.invariant_id)
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(raw).hexdigest()


def compile_invariant_support(
    segment_ids: Iterable[str],
    geometry_seed_segment_ids: Iterable[str],
    supports: Sequence[HardInvariantSupport],
    *,
    changed_invariant_ids: Iterable[str] = (),
    eager_threshold: float = 0.5,
) -> InvariantSupportPlan:
    """Expand a geometric route seed through CURRENT hard-invariant support.

    This compiler does not claim that invariant coupling changes route geometry.
    It expands the logical/evidence reproof cone. STALE or UNKNOWN support cannot
    certify independence, so the result holds and requests support refresh.
    """
    if not 0.0 < eager_threshold <= 1.0:
        raise ValueError("eager_threshold must be in (0,1]")
    segments = tuple(segment_ids)
    if not segments or len(segments) != len(set(segments)):
        raise ValueError("segment_ids must be unique and non-empty")
    if any(not isinstance(x, str) or not x for x in segments):
        raise ValueError("segment ids must be non-empty strings")
    segment_set = set(segments)

    seeds = set(geometry_seed_segment_ids)
    if not seeds <= segment_set:
        raise ValueError("geometry seed contains unknown segment")
    changed_ids = set(changed_invariant_ids)
    if any(not isinstance(x, str) or not x for x in changed_ids):
        raise ValueError("changed invariant ids must be non-empty strings")

    invariant_ids = [s.invariant_id for s in supports]
    if len(invariant_ids) != len(set(invariant_ids)):
        raise ValueError("duplicate invariant_id")
    if any(not s.segment_ids <= segment_set for s in supports):
        raise ValueError("support references unknown segment")

    root = _support_root(supports)
    if any(s.state is not SupportState.CURRENT for s in supports):
        return InvariantSupportPlan(
            disposition=SupportDisposition.HOLD_SUPPORT_UNCERTAINTY,
            reproof_segment_ids=tuple(sorted(segments)),
            coordination_components=(tuple(sorted(segments)),),
            support_root=root,
            support_refresh_required=True,
        )

    by_invariant = {s.invariant_id: s for s in supports}
    if not changed_ids <= set(by_invariant):
        raise ValueError("changed invariant missing support declaration")
    for iid in changed_ids:
        seeds.update(by_invariant[iid].segment_ids)

    parent = {s: s for s in segments}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for support in supports:
        ordered = sorted(support.segment_ids)
        for other in ordered[1:]:
            union(ordered[0], other)

    groups: dict[str, list[str]] = {}
    for segment in segments:
        groups.setdefault(find(segment), []).append(segment)
    components = tuple(sorted((tuple(sorted(v)) for v in groups.values()), key=lambda x: x[0]))

    reproof: set[str] = set()
    for component in components:
        if seeds.intersection(component):
            reproof.update(component)

    if not reproof:
        disposition = SupportDisposition.NO_REPROOF
    elif len(reproof) / len(segments) >= eager_threshold:
        disposition = SupportDisposition.EAGER_SHARED_REPROOF
        reproof = set(segments)
    else:
        disposition = SupportDisposition.SELECTIVE_REPROOF

    return InvariantSupportPlan(
        disposition=disposition,
        reproof_segment_ids=tuple(sorted(reproof)),
        coordination_components=components,
        support_root=root,
        support_refresh_required=False,
    )
