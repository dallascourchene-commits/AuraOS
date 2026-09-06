from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from atomic_absorption import OwnerSnapshot, digest
from resource_absorption import (
    LeaseRegistrySnapshot,
    ResourceProposal,
    ResourcePublicationPlan,
    ResourcePublicationReceipt,
    commit_resource_absorption,
)

CLOCK_SCOPE = 'AURA_RESOURCE_COMMIT_TIME_V2'
HEX64 = set('0123456789abcdef')


@dataclass(frozen=True)
class CommitTimeWitness:
    producer_id: str
    clock_generation: str
    scope: str
    observed_s: int
    nonce: str
    witness_root: str


@dataclass(frozen=True)
class ClockAdmission:
    producer_id: str
    clock_generation: str
    scope: str
    exact_witness_root: str
    admission_generation: str
    currentness_root: str
    authority_ceiling: str = 'D0'
    gate10: bool = False


@dataclass(frozen=True)
class ClockGuardReceipt:
    admitted: bool
    reasons: tuple[str, ...]
    witness_root: str | None
    admission_root: str | None
    observed_s: int | None
    downstream: ResourcePublicationReceipt | None
    effect_authority: bool = False
    gate10: bool = False


def _text(v: object) -> bool:
    return type(v) is str and bool(v) and all(ord(c) >= 32 for c in v)


def _hex64(v: object) -> bool:
    return type(v) is str and len(v) == 64 and all(c in HEX64 for c in v)


def witness_payload(producer_id: str, clock_generation: str, scope: str, observed_s: int, nonce: str):
    return {
        'schema': 'AURA-COMMIT-TIME-WITNESS-v2',
        'producer_id': producer_id,
        'clock_generation': clock_generation,
        'scope': scope,
        'observed_s': observed_s,
        'nonce': nonce,
    }


def make_witness(producer_id: str, clock_generation: str, observed_s: int, nonce: str, scope: str = CLOCK_SCOPE):
    payload = witness_payload(producer_id, clock_generation, scope, observed_s, nonce)
    return CommitTimeWitness(producer_id, clock_generation, scope, observed_s, nonce, digest(payload))


def admission_payload(
    producer_id: str,
    clock_generation: str,
    scope: str,
    exact_witness_root: str,
    admission_generation: str,
    authority_ceiling: str = 'D0',
    gate10: bool = False,
):
    return {
        'schema': 'AURA-COMMIT-TIME-ADMISSION-v1',
        'producer_id': producer_id,
        'clock_generation': clock_generation,
        'scope': scope,
        'exact_witness_root': exact_witness_root,
        'admission_generation': admission_generation,
        'authority_ceiling': authority_ceiling,
        'gate10': gate10,
    }


def make_admission(
    witness: CommitTimeWitness,
    admission_generation: str,
    *,
    authority_ceiling: str = 'D0',
    gate10: bool = False,
):
    payload = admission_payload(
        witness.producer_id,
        witness.clock_generation,
        witness.scope,
        witness.witness_root,
        admission_generation,
        authority_ceiling,
        gate10,
    )
    return ClockAdmission(
        witness.producer_id,
        witness.clock_generation,
        witness.scope,
        witness.witness_root,
        admission_generation,
        digest(payload),
        authority_ceiling,
        gate10,
    )


def _validate_witness(witness: CommitTimeWitness) -> list[str]:
    reasons: list[str] = []
    if not all(_text(v) for v in (witness.producer_id, witness.clock_generation, witness.scope, witness.nonce)):
        reasons.append('CLOCK_WITNESS_MALFORMED')
    if type(witness.observed_s) is not int or witness.observed_s < 0:
        reasons.append('CLOCK_WITNESS_MALFORMED')
    if not _hex64(witness.witness_root):
        reasons.append('CLOCK_WITNESS_MALFORMED')
    if reasons:
        return reasons
    expected = digest(witness_payload(witness.producer_id, witness.clock_generation, witness.scope, witness.observed_s, witness.nonce))
    if expected != witness.witness_root:
        reasons.append('CLOCK_WITNESS_DIGEST_MISMATCH')
    return reasons


def _validate_admission(admission: ClockAdmission) -> list[str]:
    reasons: list[str] = []
    if not all(_text(v) for v in (admission.producer_id, admission.clock_generation, admission.scope, admission.admission_generation)):
        reasons.append('CLOCK_ADMISSION_MALFORMED')
    if not _hex64(admission.exact_witness_root) or not _hex64(admission.currentness_root):
        reasons.append('CLOCK_ADMISSION_MALFORMED')
    if type(admission.gate10) is not bool or admission.authority_ceiling != 'D0' or admission.gate10:
        reasons.append('CLOCK_ADMISSION_AUTHORITY_WIDENING')
    if reasons:
        return reasons
    expected = digest(admission_payload(
        admission.producer_id,
        admission.clock_generation,
        admission.scope,
        admission.exact_witness_root,
        admission.admission_generation,
        admission.authority_ceiling,
        admission.gate10,
    ))
    if expected != admission.currentness_root:
        reasons.append('CLOCK_ADMISSION_ROOT_MISMATCH')
    return reasons


def guarded_resource_commit(
    submitted: ResourcePublicationPlan,
    *,
    observed_owner_head: str,
    observed_lease_root: str,
    clock_witness: CommitTimeWitness | None,
    clock_admission: ClockAdmission | None,
    expected_clock_admission_root: str | None,
    owner: OwnerSnapshot | None,
    registry: LeaseRegistrySnapshot | None,
    proposals: Sequence[ResourceProposal] | None,
) -> ClockGuardReceipt:
    """D0 composition guard: no raw caller-selected commit timestamp enters downstream.

    The admission object is opaque upstream evidence. Structural equality here does not
    authenticate a provider clock or prove physical time; it creates an explicit owner
    boundary where a current clock-source admission must be supplied.
    """
    reasons: list[str] = []
    if clock_witness is None:
        reasons.append('COMMIT_TIME_WITNESS_REQUIRED')
    if clock_admission is None:
        reasons.append('CLOCK_ADMISSION_REQUIRED')
    if expected_clock_admission_root is None or not _hex64(expected_clock_admission_root):
        reasons.append('EXPECTED_CLOCK_ADMISSION_ROOT_REQUIRED')

    if clock_witness is not None:
        reasons.extend(_validate_witness(clock_witness))
    if clock_admission is not None:
        reasons.extend(_validate_admission(clock_admission))

    if clock_witness is not None and clock_admission is not None:
        if clock_witness.producer_id != clock_admission.producer_id:
            reasons.append('CLOCK_PRODUCER_MISMATCH')
        if clock_witness.clock_generation != clock_admission.clock_generation:
            reasons.append('CLOCK_GENERATION_MISMATCH')
        if clock_witness.scope != CLOCK_SCOPE or clock_admission.scope != CLOCK_SCOPE:
            reasons.append('CLOCK_SCOPE_MISMATCH')
        if clock_witness.witness_root != clock_admission.exact_witness_root:
            reasons.append('CLOCK_WITNESS_ADMISSION_MISMATCH')
        if expected_clock_admission_root is not None and clock_admission.currentness_root != expected_clock_admission_root:
            reasons.append('CLOCK_ADMISSION_CURRENTNESS_MISMATCH')
        if clock_witness.observed_s < submitted.evaluated_at_s:
            reasons.append('CLOCK_BEFORE_PLAN')

    reasons = sorted(set(reasons))
    if reasons:
        return ClockGuardReceipt(
            False,
            tuple(reasons),
            getattr(clock_witness, 'witness_root', None),
            getattr(clock_admission, 'currentness_root', None),
            getattr(clock_witness, 'observed_s', None),
            None,
        )

    downstream = commit_resource_absorption(
        submitted,
        observed_owner_head=observed_owner_head,
        observed_lease_root=observed_lease_root,
        owner=owner,
        registry=registry,
        proposals=proposals,
        now_s=clock_witness.observed_s,
    )
    return ClockGuardReceipt(
        downstream.committed,
        () if downstream.committed else ('DOWNSTREAM_RESOURCE_COMMIT_HOLD',),
        clock_witness.witness_root,
        clock_admission.currentness_root,
        clock_witness.observed_s,
        downstream,
    )


def omega8_clock_admission_keeper(axes):
    return len(axes) == 8 and all(type(x) is int and x == 2 for x in axes)


def context13_clock_admission_preserves_invalid(core8, tail5):
    if len(tail5) != 5 or any(type(x) is not int or x not in (0, 1, 2) for x in tail5):
        raise ValueError('BAD_13D_TAIL')
    return omega8_clock_admission_keeper(core8)
