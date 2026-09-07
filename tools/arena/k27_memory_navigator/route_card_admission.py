from __future__ import annotations

"""D0 owner-consumable Memory City Navigator RouteCard admission donor.

This module composes existing Aura frontier laws without owning source memory,
K27 truth/currentness, or effect authority. It is deliberately stdlib-only so
it can be falsified in isolation before any owner absorption.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

SCHEMA = "AURA-MEMORY-CITY-NAVIGATOR-ROUTE-ADMISSION-v1"


class Polarity(str, Enum):
    NEGATIVE = "NEGATIVE"
    POSITIVE = "POSITIVE"


class TimingMode(str, Enum):
    CAUSAL = "CAUSAL"
    BOUNDED_PHASE = "BOUNDED_PHASE"
    EXACT_WINDOW = "EXACT_WINDOW"


class Disposition(str, Enum):
    READY_D0 = "READY_D0"
    REUSE_NEGATIVE_D0 = "REUSE_NEGATIVE_D0"
    REBIND_NEGATIVE_CURRENTNESS_D0 = "REBIND_NEGATIVE_CURRENTNESS_D0"
    REPROVE = "REPROVE"
    HOLD = "HOLD"


def _hex64(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be 64 hex chars")
    if value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase SHA-256 hex")
    return value


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


@dataclass(frozen=True)
class CapacityEnvelope:
    hydration: int
    route_cost: int
    lawfield_crossings: int
    disclosure: int

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative exact int")

    def no_wider_than(self, other: "CapacityEnvelope") -> bool:
        return all(getattr(self, k) <= getattr(other, k) for k in self.__dict__)


@dataclass(frozen=True)
class RouteIdentity:
    objective_root: str
    target_id: str
    source_root: str
    dependency_root: str
    map_generation: str
    lifecycle_epoch: int
    owner_incarnation: str
    currentness_generation: int
    k27: tuple[int, ...]
    runtime_state_root: str | None = None
    revision_id: str | None = None

    def __post_init__(self) -> None:
        _hex64(self.objective_root, "objective_root")
        _id(self.target_id, "target_id")
        _hex64(self.source_root, "source_root")
        _hex64(self.dependency_root, "dependency_root")
        _id(self.map_generation, "map_generation")
        _id(self.owner_incarnation, "owner_incarnation")
        if type(self.lifecycle_epoch) is not int or self.lifecycle_epoch < 0:
            raise ValueError("lifecycle_epoch must be non-negative exact int")
        if type(self.currentness_generation) is not int or self.currentness_generation < 0:
            raise ValueError("currentness_generation must be non-negative exact int")
        if not isinstance(self.k27, tuple) or len(self.k27) > 13:
            raise ValueError("k27 must be a tuple with depth <= 13")
        if any(type(x) is not int or x not in (0, 1, 2) for x in self.k27):
            raise ValueError("k27 digits must be exact ints in {0,1,2}")
        if (self.runtime_state_root is None) != (self.revision_id is None):
            raise ValueError("runtime_state_root and revision_id must be bound together")
        if self.runtime_state_root is not None:
            _hex64(self.runtime_state_root, "runtime_state_root")
            _id(self.revision_id, "revision_id")

    def hard_roots(self) -> tuple[object, ...]:
        return (
            self.objective_root, self.target_id, self.source_root,
            self.dependency_root, self.map_generation,
            self.lifecycle_epoch, self.owner_incarnation,
            self.runtime_state_root, self.revision_id,
        )


@dataclass(frozen=True)
class TemporalRequirement:
    event_time: int
    deadline: int | None = None
    worst_case_finish: int | None = None
    phase_tolerance: int | None = None
    lawfield_transition: bool = False
    irreversible_or_external: bool = False

    def __post_init__(self) -> None:
        if type(self.event_time) is not int:
            raise ValueError("event_time must be exact int")
        for field in ("deadline", "worst_case_finish", "phase_tolerance"):
            value = getattr(self, field)
            if value is not None and type(value) is not int:
                raise ValueError(f"{field} must be exact int or None")
        if self.phase_tolerance is not None and self.phase_tolerance < 0:
            raise ValueError("phase_tolerance must be >= 0")
        if type(self.lawfield_transition) is not bool or type(self.irreversible_or_external) is not bool:
            raise ValueError("temporal flags must be exact bools")

    @property
    def mode(self) -> TimingMode:
        if self.irreversible_or_external:
            return TimingMode.EXACT_WINDOW
        if self.lawfield_transition or self.phase_tolerance is not None:
            return TimingMode.BOUNDED_PHASE
        return TimingMode.CAUSAL

    @property
    def deadline_safe(self) -> bool:
        if self.deadline is None:
            return True
        if self.worst_case_finish is None:
            return False
        return self.worst_case_finish <= self.deadline


@dataclass(frozen=True)
class ProofReceipt:
    polarity: Polarity
    route_identity: RouteIdentity
    certified_envelope: CapacityEnvelope
    temporal_mode: TimingMode
    event_time: int
    state_independent_negative: bool = False
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.polarity, Polarity):
            raise ValueError("polarity must be an exact Polarity enum")
        if not isinstance(self.route_identity, RouteIdentity):
            raise ValueError("route_identity must be RouteIdentity")
        if not isinstance(self.certified_envelope, CapacityEnvelope):
            raise ValueError("certified_envelope must be CapacityEnvelope")
        if not isinstance(self.temporal_mode, TimingMode):
            raise ValueError("temporal_mode must be an exact TimingMode enum")
        if type(self.event_time) is not int:
            raise ValueError("event_time must be exact int")
        for name in ("state_independent_negative", "authority_minted", "effect_authority", "gate10"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be exact bool")
        if self.polarity is Polarity.POSITIVE and self.state_independent_negative:
            raise ValueError("positive receipt cannot be state-independent negative")
        if self.authority_minted or self.effect_authority or self.gate10:
            raise ValueError("D0 Navigator receipt cannot carry authority")


@dataclass(frozen=True)
class UseContext:
    identity: RouteIdentity
    envelope: CapacityEnvelope
    temporal: TemporalRequirement
    current_source: bool = True
    capability_current: bool = True
    local_knowledge_sufficient: bool = True
    disclosure_budget_ok: bool = True
    irreversible_effect_already_committed: bool = False


@dataclass(frozen=True)
class Admission:
    disposition: Disposition
    timing_mode: TimingMode
    reasons: tuple[str, ...]
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def _hard_root_movement(old: RouteIdentity, new: RouteIdentity) -> bool:
    return old.hard_roots() != new.hard_roots()


def admit(receipt: ProofReceipt, use: UseContext) -> Admission:
    """Classify one current route-use request.

    Positive readiness requires exact at-use identity, timing, envelope and
    capability/knowledge discharge. A state-independent negative impossibility
    may survive a pure currentness/event-time rebind and any envelope shrink,
    but never a hard-root move or envelope widening. Runtime state/revision are
    hard identity when present. K27 is intentionally absent from authority decisions.
    """
    mode = use.temporal.mode

    if use.irreversible_effect_already_committed:
        return Admission(Disposition.HOLD, mode, ("irreversible_effect_already_committed",))
    if not use.current_source:
        return Admission(Disposition.HOLD, mode, ("source_not_current",))
    if not use.local_knowledge_sufficient:
        return Admission(Disposition.HOLD, mode, ("local_knowledge_insufficient",))
    if not use.capability_current:
        return Admission(Disposition.HOLD, mode, ("capability_not_current_at_use",))
    if not use.disclosure_budget_ok:
        return Admission(Disposition.HOLD, mode, ("capability_attestation_disclosure_budget_exceeded",))
    if not use.temporal.deadline_safe:
        return Admission(Disposition.HOLD, mode, ("worst_case_deadline_miss_or_unknown",))

    hard_move = _hard_root_movement(receipt.route_identity, use.identity)

    if receipt.polarity is Polarity.NEGATIVE:
        if hard_move:
            return Admission(Disposition.REPROVE, mode, ("negative_hard_root_movement",))
        if not use.envelope.no_wider_than(receipt.certified_envelope):
            return Admission(Disposition.REPROVE, mode, ("negative_envelope_widened",))
        if mode is not receipt.temporal_mode:
            return Admission(Disposition.REPROVE, mode, ("negative_temporal_mode_changed",))
        currentness_moved = (
            use.identity.currentness_generation != receipt.route_identity.currentness_generation
            or use.temporal.event_time != receipt.event_time
        )
        if currentness_moved:
            if not receipt.state_independent_negative:
                return Admission(Disposition.REPROVE, mode, ("negative_currentness_moved_but_state_dependent",))
            return Admission(
                Disposition.REBIND_NEGATIVE_CURRENTNESS_D0, mode,
                ("state_independent_negative_rebound_under_same_hard_roots",),
            )
        return Admission(Disposition.REUSE_NEGATIVE_D0, mode, ("negative_certificate_still_dominates",))

    if hard_move:
        return Admission(Disposition.REPROVE, mode, ("positive_hard_root_movement",))
    if use.identity.currentness_generation != receipt.route_identity.currentness_generation:
        return Admission(Disposition.REPROVE, mode, ("positive_currentness_generation_moved",))
    if use.temporal.event_time != receipt.event_time:
        return Admission(Disposition.REPROVE, mode, ("positive_event_time_moved",))
    if use.envelope != receipt.certified_envelope:
        return Admission(Disposition.REPROVE, mode, ("positive_envelope_not_exact",))
    if mode is not receipt.temporal_mode:
        return Admission(Disposition.REPROVE, mode, ("positive_temporal_mode_changed",))
    return Admission(Disposition.READY_D0, mode, ("positive_exact_at_use_discharge",))


def canonical_receipt_root(receipt: ProofReceipt) -> str:
    payload = {
        "schema": SCHEMA,
        "polarity": receipt.polarity.value,
        "identity": {
            "objective_root": receipt.route_identity.objective_root,
            "target_id": receipt.route_identity.target_id,
            "source_root": receipt.route_identity.source_root,
            "dependency_root": receipt.route_identity.dependency_root,
            "map_generation": receipt.route_identity.map_generation,
            "lifecycle_epoch": receipt.route_identity.lifecycle_epoch,
            "owner_incarnation": receipt.route_identity.owner_incarnation,
            "currentness_generation": receipt.route_identity.currentness_generation,
            "k27": list(receipt.route_identity.k27),
            "runtime_state_root": receipt.route_identity.runtime_state_root,
            "revision_id": receipt.route_identity.revision_id,
        },
        "envelope": receipt.certified_envelope.__dict__,
        "temporal_mode": receipt.temporal_mode.value,
        "event_time": receipt.event_time,
        "state_independent_negative": receipt.state_independent_negative,
        "authority_minted": False,
        "effect_authority": False,
        "gate10": False,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(raw).hexdigest()
