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


class SupportUseDisposition(str, Enum):
    READY_D0 = "READY_D0"
    REPROVE_SUPPORT_WORLD = "REPROVE_SUPPORT_WORLD"
    HOLD_SUPPORT_UNCERTAINTY = "HOLD_SUPPORT_UNCERTAINTY"
    HOLD_UNBOUND_SUPPORT_IDENTITY = "HOLD_UNBOUND_SUPPORT_IDENTITY"


def _hex64(value: str, field: str) -> str:
    if (not isinstance(value, str) or len(value) != 64 or value.lower() != value
            or any(c not in "0123456789abcdef" for c in value)):
        raise ValueError(f"{field} must be lowercase SHA-256 hex")
    return value


@dataclass(frozen=True)
class SupportWorldIdentity:
    configuration_root: str
    support_generation: int
    owner_incarnation: str

    def __post_init__(self) -> None:
        _hex64(self.configuration_root, "configuration_root")
        if type(self.support_generation) is not int or self.support_generation < 0:
            raise ValueError("support_generation must be non-negative exact int")
        if not isinstance(self.owner_incarnation, str) or not self.owner_incarnation:
            raise ValueError("owner_incarnation required")


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
    support_identity_root: str | None
    support_refresh_required: bool
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


@dataclass(frozen=True)
class SupportUseDecision:
    disposition: SupportUseDisposition
    current_support_root: str
    current_support_identity_root: str
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


def _support_identity_root(support_root: str, identity: SupportWorldIdentity) -> str:
    _hex64(support_root, "support_root")
    if not isinstance(identity, SupportWorldIdentity):
        raise ValueError("support_identity must be SupportWorldIdentity")
    payload = {
        "support_root": support_root,
        "configuration_root": identity.configuration_root,
        "support_generation": identity.support_generation,
        "owner_incarnation": identity.owner_incarnation,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(raw).hexdigest()


def compile_invariant_support(
    segment_ids: Iterable[str],
    geometry_seed_segment_ids: Iterable[str],
    supports: Sequence[HardInvariantSupport],
    *,
    changed_invariant_ids: Iterable[str] = (),
    eager_threshold: float = 0.5,
    support_identity: SupportWorldIdentity | None = None,
) -> InvariantSupportPlan:
    """Expand a geometric route seed through CURRENT hard-invariant support.

    Geometry and logical reproof remain separate. When support_identity is
    supplied, the plan is bound to exact support membership/state plus current
    configuration generation and owner incarnation. An unbound plan remains a
    D0 planning hint and cannot later pass validate_support_use().
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
    if support_identity is not None and not isinstance(support_identity, SupportWorldIdentity):
        raise ValueError("support_identity must be SupportWorldIdentity or None")

    root = _support_root(supports)
    identity_root = None if support_identity is None else _support_identity_root(root, support_identity)
    if any(s.state is not SupportState.CURRENT for s in supports):
        return InvariantSupportPlan(
            disposition=SupportDisposition.HOLD_SUPPORT_UNCERTAINTY,
            reproof_segment_ids=tuple(sorted(segments)),
            coordination_components=(tuple(sorted(segments)),),
            support_root=root,
            support_identity_root=identity_root,
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
        support_identity_root=identity_root,
        support_refresh_required=False,
    )


def validate_support_use(
    plan: InvariantSupportPlan,
    current_supports: Sequence[HardInvariantSupport],
    current_identity: SupportWorldIdentity,
) -> SupportUseDecision:
    """Require exact support/configuration identity at the plan use site."""
    if not isinstance(plan, InvariantSupportPlan):
        raise ValueError("plan must be InvariantSupportPlan")
    if not isinstance(current_identity, SupportWorldIdentity):
        raise ValueError("current_identity must be SupportWorldIdentity")
    current_root = _support_root(current_supports)
    current_identity_root = _support_identity_root(current_root, current_identity)

    if plan.support_identity_root is None:
        disposition = SupportUseDisposition.HOLD_UNBOUND_SUPPORT_IDENTITY
    elif any(s.state is not SupportState.CURRENT for s in current_supports):
        disposition = SupportUseDisposition.HOLD_SUPPORT_UNCERTAINTY
    elif plan.support_identity_root != current_identity_root:
        disposition = SupportUseDisposition.REPROVE_SUPPORT_WORLD
    elif plan.disposition is SupportDisposition.HOLD_SUPPORT_UNCERTAINTY:
        disposition = SupportUseDisposition.HOLD_SUPPORT_UNCERTAINTY
    else:
        disposition = SupportUseDisposition.READY_D0

    return SupportUseDecision(
        disposition=disposition,
        current_support_root=current_root,
        current_support_identity_root=current_identity_root,
    )
