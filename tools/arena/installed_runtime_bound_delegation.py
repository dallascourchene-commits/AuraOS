from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

from tools.arena.attenuated_stable_operation_delegation import StableOperation, DelegationHop, DomainAdmission, AttemptContext, Disposition as DelegationDisposition, decide
from tools.project006.installed_runtime_attestation import RuntimeReleaseManifest, HostMeasurement, MeasurementEvidence, RuntimeDisposition, attest_runtime

SCHEMA = 'AURA-O21-INSTALLED-RUNTIME-BOUND-DELEGATED-EXECUTION-v1'

def _root(obj):
    return sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

class PermitDisposition(str, Enum):
    ADMIT_D0 = 'ADMIT_RUNTIME_BOUND_DELEGATED_ATTEMPT_D0'
    HOLD_DELEGATION = 'HOLD_DELEGATION'
    HOLD_RUNTIME = 'HOLD_RUNTIME'
    HOLD_RELEASE_OPERATION_MISMATCH = 'HOLD_RELEASE_OPERATION_MISMATCH'
    HOLD_SOURCE_CROSS_BINDING = 'HOLD_SOURCE_CROSS_BINDING'
    HOLD_TARGET_RELEASE_MISMATCH = 'HOLD_TARGET_RELEASE_MISMATCH'
    HOLD_TARGET_HOST_MISMATCH = 'HOLD_TARGET_HOST_MISMATCH'
    HOLD_TARGET_INCARNATION_MISMATCH = 'HOLD_TARGET_INCARNATION_MISMATCH'
    HOLD_RUNTIME_RECEIPT_INCOMPLETE = 'HOLD_RUNTIME_RECEIPT_INCOMPLETE'

@dataclass(frozen=True)
class RuntimeTarget:
    host_id: str
    host_incarnation: str
    release_root: str

@dataclass(frozen=True)
class RuntimeBoundPermit:
    disposition: PermitDisposition
    reason: str
    operation_root: str
    attempt_root: str | None
    delegation_chain_root: str
    release_root: str
    measurement_root: str | None
    target_host_id: str
    target_host_incarnation: str
    source_incarnation_root: str
    permit_root: str | None
    effect_authority: bool = False
    training_authority: bool = False
    checkpoint_authority: bool = False
    gate10: bool = False


def bind_at_use(
    operation: StableOperation,
    hops: tuple[DelegationHop, ...],
    admission: DomainAdmission,
    ctx: AttemptContext,
    manifest: RuntimeReleaseManifest,
    target: RuntimeTarget,
    *,
    owner_reported_updated: bool | None,
    measurement: HostMeasurement | None,
    evidence: MeasurementEvidence | None,
    now_ms: int,
    max_age_ms: int = 300_000,
) -> RuntimeBoundPermit:
    delegation = decide(operation, hops, admission, ctx)
    runtime = attest_runtime(
        manifest,
        owner_reported_updated=owner_reported_updated,
        measurement=measurement,
        evidence=evidence,
        now_ms=now_ms,
        max_age_ms=max_age_ms,
    )
    op_root = operation.root()
    release_root = manifest.release_root

    def hold(disposition: PermitDisposition, reason: str) -> RuntimeBoundPermit:
        return RuntimeBoundPermit(
            disposition=disposition,
            reason=reason,
            operation_root=op_root,
            attempt_root=delegation.attempt_root,
            delegation_chain_root=delegation.delegation_chain_root,
            release_root=release_root,
            measurement_root=runtime.measurement_root,
            target_host_id=target.host_id,
            target_host_incarnation=target.host_incarnation,
            source_incarnation_root=operation.source_incarnation_root,
            permit_root=None,
        )

    if delegation.disposition is not DelegationDisposition.ADMIT_D0 or delegation.attempt_root is None:
        return hold(PermitDisposition.HOLD_DELEGATION, f'DELEGATION:{delegation.reason}')
    if runtime.disposition is not RuntimeDisposition.CURRENT_EXACT_HOST_OBSERVED or not runtime.current:
        return hold(PermitDisposition.HOLD_RUNTIME, f'RUNTIME:{runtime.disposition.value}')
    if runtime.measurement_root is None or runtime.exact_installed_head is None or measurement is None or evidence is None:
        return hold(PermitDisposition.HOLD_RUNTIME_RECEIPT_INCOMPLETE, 'RUNTIME_RECEIPT_INCOMPLETE')
    if manifest.canonical_operation_root != op_root:
        return hold(PermitDisposition.HOLD_RELEASE_OPERATION_MISMATCH, 'RELEASE_OPERATION_ROOT_MISMATCH')
    if measurement.source_incarnation_root != operation.source_incarnation_root or ctx.source_incarnation_root != operation.source_incarnation_root:
        return hold(PermitDisposition.HOLD_SOURCE_CROSS_BINDING, 'SOURCE_INCARNATION_CROSS_BINDING_FAILED')
    if target.release_root != release_root:
        return hold(PermitDisposition.HOLD_TARGET_RELEASE_MISMATCH, 'TARGET_RELEASE_ROOT_MISMATCH')
    if target.host_id != measurement.host_id:
        return hold(PermitDisposition.HOLD_TARGET_HOST_MISMATCH, 'TARGET_HOST_ID_MISMATCH')
    if target.host_incarnation != measurement.host_incarnation:
        return hold(PermitDisposition.HOLD_TARGET_INCARNATION_MISMATCH, 'TARGET_HOST_INCARNATION_MISMATCH')

    permit_root = _root({
        'schema': SCHEMA,
        'operation_root': op_root,
        'attempt_root': delegation.attempt_root,
        'delegation_chain_root': delegation.delegation_chain_root,
        'release_root': release_root,
        'measurement_root': runtime.measurement_root,
        'exact_installed_head': runtime.exact_installed_head,
        'target_host_id': target.host_id,
        'target_host_incarnation': target.host_incarnation,
        'source_incarnation_root': operation.source_incarnation_root,
        'evidence_issued_at_ms': evidence.issued_at_ms,
        'evidence_expires_at_ms': evidence.expires_at_ms,
    })
    return RuntimeBoundPermit(
        disposition=PermitDisposition.ADMIT_D0,
        reason='OK_RUNTIME_BOUND_D0',
        operation_root=op_root,
        attempt_root=delegation.attempt_root,
        delegation_chain_root=delegation.delegation_chain_root,
        release_root=release_root,
        measurement_root=runtime.measurement_root,
        target_host_id=target.host_id,
        target_host_incarnation=target.host_incarnation,
        source_incarnation_root=operation.source_incarnation_root,
        permit_root=permit_root,
    )
