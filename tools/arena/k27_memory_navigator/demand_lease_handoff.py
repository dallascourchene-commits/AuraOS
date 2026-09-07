from __future__ import annotations

"""D0 configuration-bound demand-cell lease handoff donor.

Locality and cache residency never authorize mutation. A mutable lease is
valid only for the exact immutable cell revision and support/configuration
state whose proof-carrying transition evidence and protected-resource fence
receipt agree at the mutation boundary.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping, FrozenSet

SCHEMA = "AURA-MEMORY-CITY-DEMAND-LEASE-HANDOFF-v2"


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


def _canonical_root(payload: Mapping[str, object]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
    """Proposed transition values only; this object carries no authentication."""

    cell_id: str
    old_configuration_root: str
    new_configuration_root: str
    old_support_epoch: int
    new_support_epoch: int
    new_fence_generation: int

    def __post_init__(self) -> None:
        _id(self.cell_id, "cell_id")
        _root(self.old_configuration_root, "old_configuration_root")
        _root(self.new_configuration_root, "new_configuration_root")
        _nonnegative_int(self.old_support_epoch, "old_support_epoch")
        _nonnegative_int(self.new_support_epoch, "new_support_epoch")
        _nonnegative_int(self.new_fence_generation, "new_fence_generation")

    def canonical_claim_root(self) -> str:
        return _canonical_root({
            "schema": SCHEMA,
            "kind": "configuration_transition_claim",
            "cell_id": self.cell_id,
            "old_configuration_root": self.old_configuration_root,
            "new_configuration_root": self.new_configuration_root,
            "old_support_epoch": self.old_support_epoch,
            "new_support_epoch": self.new_support_epoch,
            "new_fence_generation": self.new_fence_generation,
        })


@dataclass(frozen=True)
class TransitionAuthorityEvidence:
    """Owner/verifier-produced receipt binding one exact transition claim.

    The handoff compiler does not infer authentication from booleans. It only
    accepts a receipt when its claim root, authority source and verifier receipt
    roots are exact current roots supplied by the owner boundary.
    """

    transition_claim_root: str
    authority_source_root: str
    verifier_receipt_root: str

    def __post_init__(self) -> None:
        _root(self.transition_claim_root, "transition_claim_root")
        _root(self.authority_source_root, "authority_source_root")
        _root(self.verifier_receipt_root, "verifier_receipt_root")


@dataclass(frozen=True)
class ResourceFenceReceipt:
    """Observed protected-resource fence state, separate from transition intent."""

    cell_id: str
    configuration_root: str
    support_epoch: int
    installed_fence_generation: int
    resource_state_root: str
    observer_receipt_root: str

    def __post_init__(self) -> None:
        _id(self.cell_id, "cell_id")
        _root(self.configuration_root, "configuration_root")
        _nonnegative_int(self.support_epoch, "support_epoch")
        _nonnegative_int(self.installed_fence_generation, "installed_fence_generation")
        _root(self.resource_state_root, "resource_state_root")
        _root(self.observer_receipt_root, "observer_receipt_root")

    def canonical_state_root(self) -> str:
        return _canonical_root({
            "schema": SCHEMA,
            "kind": "resource_fence_state",
            "cell_id": self.cell_id,
            "configuration_root": self.configuration_root,
            "support_epoch": self.support_epoch,
            "installed_fence_generation": self.installed_fence_generation,
        })


@dataclass(frozen=True)
class TransitionVerificationContext:
    """Current owner-bound verifier/resource roots used to reject stale receipts."""

    authority_source_root: str
    verifier_receipt_root: str
    resource_state_root: str
    observer_receipt_root: str

    def __post_init__(self) -> None:
        _root(self.authority_source_root, "authority_source_root")
        _root(self.verifier_receipt_root, "verifier_receipt_root")
        _root(self.resource_state_root, "resource_state_root")
        _root(self.observer_receipt_root, "observer_receipt_root")


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
    # highest_accepted_fence is the protected resource's installation witness.
    # An issued/current generation that has not reached that boundary is not READY.
    if lease.fence_generation != cell.highest_accepted_fence:
        return LeaseDecision(LeaseDisposition.HOLD, "FENCE_NOT_INSTALLED_CURRENT")
    if lease.fence_generation != cell.fence_generation:
        return LeaseDecision(LeaseDisposition.REBIND_REQUIRED, "FENCE_GENERATION_MOVED")
    if now >= lease.expires_at:
        return LeaseDecision(LeaseDisposition.HOLD, "LEASE_EXPIRED")
    return LeaseDecision(LeaseDisposition.READY_D0, "EXACT_CONFIGURATION_BOUND_FENCE")


def apply_configuration_transition(
    cell: DemandCellState,
    transition: ConfigurationTransition,
    authority_evidence: TransitionAuthorityEvidence,
    resource_receipt: ResourceFenceReceipt,
    verification: TransitionVerificationContext,
) -> tuple[LeaseDecision, DemandCellState]:
    """Apply a transition only when independent receipts bind the exact claim/state.

    No caller-provided `authenticated=True` or `installed_at_resource=True` flag
    exists. The transition, authority receipt, protected-resource observation,
    and current verifier/resource roots must all agree exactly.
    """
    if not isinstance(cell, DemandCellState) or not isinstance(transition, ConfigurationTransition):
        raise ValueError("typed cell and transition required")
    if not isinstance(authority_evidence, TransitionAuthorityEvidence):
        raise ValueError("typed transition authority evidence required")
    if not isinstance(resource_receipt, ResourceFenceReceipt):
        raise ValueError("typed resource fence receipt required")
    if not isinstance(verification, TransitionVerificationContext):
        raise ValueError("typed transition verification context required")
    if transition.cell_id != cell.cell_id:
        return LeaseDecision(LeaseDisposition.HOLD, "CELL_MISMATCH"), cell
    if (
        transition.old_configuration_root != cell.configuration_root
        or transition.old_support_epoch != cell.support_epoch
    ):
        return LeaseDecision(LeaseDisposition.HOLD, "TRANSITION_BASE_STALE"), cell
    if authority_evidence.transition_claim_root != transition.canonical_claim_root():
        return LeaseDecision(LeaseDisposition.HOLD, "TRANSITION_EVIDENCE_CLAIM_MISMATCH"), cell
    if authority_evidence.authority_source_root != verification.authority_source_root:
        return LeaseDecision(LeaseDisposition.HOLD, "AUTHORITY_SOURCE_ROOT_STALE"), cell
    if authority_evidence.verifier_receipt_root != verification.verifier_receipt_root:
        return LeaseDecision(LeaseDisposition.HOLD, "VERIFIER_RECEIPT_ROOT_STALE"), cell
    if transition.new_configuration_root == cell.configuration_root:
        return LeaseDecision(LeaseDisposition.HOLD, "CONFIGURATION_ROOT_NOT_ADVANCED"), cell
    if transition.new_support_epoch <= cell.support_epoch:
        return LeaseDecision(LeaseDisposition.HOLD, "SUPPORT_EPOCH_NOT_ADVANCED"), cell
    if transition.new_fence_generation <= cell.fence_generation:
        return LeaseDecision(LeaseDisposition.HOLD, "FENCE_NOT_MONOTONIC"), cell
    if transition.new_fence_generation <= cell.highest_accepted_fence:
        return LeaseDecision(LeaseDisposition.HOLD, "FENCE_NOT_ABOVE_ACCEPTED"), cell

    if resource_receipt.cell_id != transition.cell_id:
        return LeaseDecision(LeaseDisposition.HOLD, "RESOURCE_CELL_MISMATCH"), cell
    if resource_receipt.resource_state_root != verification.resource_state_root:
        return LeaseDecision(LeaseDisposition.HOLD, "RESOURCE_STATE_ROOT_STALE"), cell
    if resource_receipt.observer_receipt_root != verification.observer_receipt_root:
        return LeaseDecision(LeaseDisposition.HOLD, "RESOURCE_OBSERVER_ROOT_STALE"), cell
    if resource_receipt.resource_state_root != resource_receipt.canonical_state_root():
        return LeaseDecision(LeaseDisposition.HOLD, "RESOURCE_STATE_RECEIPT_MALFORMED"), cell
    if (
        resource_receipt.configuration_root != transition.new_configuration_root
        or resource_receipt.support_epoch != transition.new_support_epoch
        or resource_receipt.installed_fence_generation != transition.new_fence_generation
    ):
        return LeaseDecision(LeaseDisposition.HOLD, "FENCE_NOT_VERIFIED_AT_RESOURCE"), cell

    next_state = DemandCellState(
        cell_id=cell.cell_id,
        revision=cell.revision,
        configuration_root=transition.new_configuration_root,
        support_epoch=transition.new_support_epoch,
        fence_generation=transition.new_fence_generation,
        highest_accepted_fence=transition.new_fence_generation,
    )
    return LeaseDecision(LeaseDisposition.READY_D0, "PROOF_BOUND_CONFIGURATION_TRANSITION_INSTALLED"), next_state


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
    """Return the smallest consumer-closed invalidation cone.

    Repository convention is dependent -> dependencies. Starting at a changed
    source, invalidate each dependent whose dependency set contains an already
    invalid node, then continue to that dependent's consumers.
    """
    if not isinstance(changed_cells, frozenset) or any(not isinstance(x, str) or not x for x in changed_cells):
        raise ValueError("changed_cells must be a frozenset of non-empty ids")
    normalized: dict[str, FrozenSet[str]] = {}
    for dependent, dependencies in dependency_edges.items():
        if not isinstance(dependent, str) or not dependent:
            raise ValueError("dependency edge keys must be non-empty dependent ids")
        if not isinstance(dependencies, frozenset) or any(not isinstance(x, str) or not x for x in dependencies):
            raise ValueError("dependency edges must map dependents to frozensets of dependency ids")
        normalized[dependent] = dependencies

    seen = set(changed_cells)
    frontier = list(changed_cells)
    while frontier:
        changed = frontier.pop()
        for dependent, dependencies in normalized.items():
            if dependent not in seen and changed in dependencies:
                seen.add(dependent)
                frontier.append(dependent)
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
    return _canonical_root(payload)
