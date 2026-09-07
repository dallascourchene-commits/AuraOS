from __future__ import annotations

"""D0 configuration-bound demand-cell lease handoff donor.

Locality and cache residency never authorize mutation. A mutable lease is
valid only for the exact immutable cell revision and authenticated support /
configuration generation whose fencing generation has been installed at the
mutation boundary.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping, FrozenSet

SCHEMA = "AURA-MEMORY-CITY-DEMAND-LEASE-HANDOFF-v1"


class LeaseDisposition(str, Enum):
    READY_D0 = "READY_D0"
    REBIND_REQUIRED = "REBIND_REQUIRED"
    HOLD = "HOLD"


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be lowercase SHA-256 hex")
    if value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase SHA-256 hex")
    return value


def _nonnegative_int(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative exact int")
    return value


@dataclass(frozen=True)
class DemandCellState:
    cell_id: str
    revision: int
    configuration_root: str
    support_epoch: int
    fence_generation: int
    highest_accepted_fence: int

    def __post_init__(self) -> None:
        _id(self.cell_id, "cell_id")
        _nonnegative_int(self.revision, "revision")
        _root(self.configuration_root, "configuration_root")
        _nonnegative_int(self.support_epoch, "support_epoch")
        _nonnegative_int(self.fence_generation, "fence_generation")
        _nonnegative_int(self.highest_accepted_fence, "highest_accepted_fence")
        if self.highest_accepted_fence > self.fence_generation:
            raise ValueError("highest_accepted_fence cannot exceed current fence_generation")


@dataclass(frozen=True)
class DemandCellLease:
    cell_id: str
    revision: int
    configuration_root: str
    support_epoch: int
    fence_generation: int
    holder: str
    expires_at: int

    def __post_init__(self) -> None:
        _id(self.cell_id, "cell_id")
        _nonnegative_int(self.revision, "revision")
        _root(self.configuration_root, "configuration_root")
        _nonnegative_int(self.support_epoch, "support_epoch")
        _nonnegative_int(self.fence_generation, "fence_generation")
        _id(self.holder, "holder")
        if type(self.expires_at) is not int:
            raise ValueError("expires_at must be an exact int")


@dataclass(frozen=True)
class ConfigurationTransition:
    cell_id: str
    old_configuration_root: str
    new_configuration_root: str
    old_support_epoch: int
    new_support_epoch: int
    new_fence_generation: int
    authenticated: bool
    installed_at_resource: bool

    def __post_init__(self) -> None:
        _id(self.cell_id, "cell_id")
        _root(self.old_configuration_root, "old_configuration_root")
        _root(self.new_configuration_root, "new_configuration_root")
        _nonnegative_int(self.old_support_epoch, "old_support_epoch")
        _nonnegative_int(self.new_support_epoch, "new_support_epoch")
        _nonnegative_int(self.new_fence_generation, "new_fence_generation")
        if type(self.authenticated) is not bool or type(self.installed_at_resource) is not bool:
            raise ValueError("transition flags must be exact bools")


@dataclass(frozen=True)
class LeaseDecision:
    disposition: LeaseDisposition
    reason: str
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, LeaseDisposition):
            raise ValueError("disposition must be LeaseDisposition")
        _id(self.reason, "reason")
        if self.authority_minted or self.effect_authority or self.gate10:
            raise ValueError("D0 lease decision cannot mint authority")


def compile_write(lease: DemandCellLease, cell: DemandCellState, now: int) -> LeaseDecision:
    """Admit a D0 write intent against the exact mutation-boundary state."""
    if not isinstance(lease, DemandCellLease) or not isinstance(cell, DemandCellState):
        raise ValueError("typed lease and cell state required")
    if type(now) is not int:
        raise ValueError("now must be exact int")
    if lease.cell_id != cell.cell_id:
        return LeaseDecision(LeaseDisposition.HOLD, "CELL_MISMATCH")
    if lease.revision != cell.revision:
        return LeaseDecision(LeaseDisposition.REBIND_REQUIRED, "REVISION_MOVED")
    if lease.configuration_root != cell.configuration_root:
        return LeaseDecision(LeaseDisposition.REBIND_REQUIRED, "CONFIGURATION_MOVED")
    if lease.support_epoch != cell.support_epoch:
        return LeaseDecision(LeaseDisposition.REBIND_REQUIRED, "SUPPORT_EPOCH_MOVED")
    if lease.fence_generation < cell.highest_accepted_fence:
        return LeaseDecision(LeaseDisposition.HOLD, "STALE_FENCE")
    if lease.fence_generation != cell.fence_generation:
        return LeaseDecision(LeaseDisposition.REBIND_REQUIRED, "FENCE_GENERATION_MOVED")
    if now >= lease.expires_at:
        return LeaseDecision(LeaseDisposition.HOLD, "LEASE_EXPIRED")
    return LeaseDecision(LeaseDisposition.READY_D0, "EXACT_CONFIGURATION_BOUND_FENCE")


def apply_configuration_transition(
    cell: DemandCellState,
    transition: ConfigurationTransition,
) -> tuple[LeaseDecision, DemandCellState]:
    """Install an authenticated support/configuration handoff at the resource."""
    if not isinstance(cell, DemandCellState) or not isinstance(transition, ConfigurationTransition):
        raise ValueError("typed cell and transition required")
    if transition.cell_id != cell.cell_id:
        return LeaseDecision(LeaseDisposition.HOLD, "CELL_MISMATCH"), cell
    if (
        transition.old_configuration_root != cell.configuration_root
        or transition.old_support_epoch != cell.support_epoch
    ):
        return LeaseDecision(LeaseDisposition.HOLD, "TRANSITION_BASE_STALE"), cell
    if not transition.authenticated:
        return LeaseDecision(LeaseDisposition.HOLD, "TRANSITION_UNAUTHENTICATED"), cell
    if transition.new_configuration_root == cell.configuration_root:
        return LeaseDecision(LeaseDisposition.HOLD, "CONFIGURATION_ROOT_NOT_ADVANCED"), cell
    if transition.new_support_epoch <= cell.support_epoch:
        return LeaseDecision(LeaseDisposition.HOLD, "SUPPORT_EPOCH_NOT_ADVANCED"), cell
    if transition.new_fence_generation <= cell.fence_generation:
        return LeaseDecision(LeaseDisposition.HOLD, "FENCE_NOT_MONOTONIC"), cell
    if transition.new_fence_generation <= cell.highest_accepted_fence:
        return LeaseDecision(LeaseDisposition.HOLD, "FENCE_NOT_ABOVE_ACCEPTED"), cell
    if not transition.installed_at_resource:
        return LeaseDecision(LeaseDisposition.HOLD, "FENCE_NOT_INSTALLED_AT_RESOURCE"), cell

    next_state = DemandCellState(
        cell_id=cell.cell_id,
        revision=cell.revision,
        configuration_root=transition.new_configuration_root,
        support_epoch=transition.new_support_epoch,
        fence_generation=transition.new_fence_generation,
        highest_accepted_fence=transition.new_fence_generation,
    )
    return LeaseDecision(LeaseDisposition.READY_D0, "CONFIGURATION_TRANSITION_INSTALLED"), next_state


def grant_current_lease(
    cell: DemandCellState,
    *,
    holder: str,
    expires_at: int,
) -> DemandCellLease:
    """Bind a successor lease to the exact current state; this grants no effect authority by itself."""
    return DemandCellLease(
        cell_id=cell.cell_id,
        revision=cell.revision,
        configuration_root=cell.configuration_root,
        support_epoch=cell.support_epoch,
        fence_generation=cell.fence_generation,
        holder=holder,
        expires_at=expires_at,
    )


def commit_new_immutable_revision(
    lease: DemandCellLease,
    cell: DemandCellState,
    now: int,
) -> tuple[LeaseDecision, DemandCellState]:
    decision = compile_write(lease, cell, now)
    if decision.disposition is not LeaseDisposition.READY_D0:
        return decision, cell
    next_state = DemandCellState(
        cell_id=cell.cell_id,
        revision=cell.revision + 1,
        configuration_root=cell.configuration_root,
        support_epoch=cell.support_epoch,
        fence_generation=cell.fence_generation,
        highest_accepted_fence=max(cell.highest_accepted_fence, lease.fence_generation),
    )
    return LeaseDecision(LeaseDisposition.READY_D0, "NEW_IMMUTABLE_REVISION_COMMITTED"), next_state


def dependency_closed_invalidation(
    changed_cells: FrozenSet[str],
    dependency_edges: Mapping[str, FrozenSet[str]],
) -> FrozenSet[str]:
    """Return the smallest forward dependency-closed invalidation cone."""
    if not isinstance(changed_cells, frozenset) or any(not isinstance(x, str) or not x for x in changed_cells):
        raise ValueError("changed_cells must be a frozenset of non-empty ids")
    seen = set(changed_cells)
    stack = list(changed_cells)
    while stack:
        current = stack.pop()
        children = dependency_edges.get(current, frozenset())
        if not isinstance(children, frozenset) or any(not isinstance(x, str) or not x for x in children):
            raise ValueError("dependency edges must map to frozensets of non-empty ids")
        for child in children:
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return frozenset(seen)


def canonical_lease_root(lease: DemandCellLease) -> str:
    payload = {
        "schema": SCHEMA,
        "cell_id": lease.cell_id,
        "revision": lease.revision,
        "configuration_root": lease.configuration_root,
        "support_epoch": lease.support_epoch,
        "fence_generation": lease.fence_generation,
        "holder": lease.holder,
        "expires_at": lease.expires_at,
        "authority_minted": False,
        "effect_authority": False,
        "gate10": False,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
