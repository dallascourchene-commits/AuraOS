from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

from tools.arena.attenuated_stable_operation_delegation import StableOperation, DelegationHop, DomainAdmission, AttemptContext
from tools.arena.installed_runtime_bound_delegation import RuntimeTarget, PermitDisposition, bind_at_use
from tools.project006.installed_runtime_attestation import RuntimeReleaseManifest, HostMeasurement, MeasurementEvidence
from tools.arena.effect_time_loaded_process_currentness import (
    InstalledRuntimeAttestation, LoadedProcessWitness, AtUseObservation,
    Disposition as ProcessDisposition, decide as decide_process,
)

SCHEMA = "AURA-O7-EFFECT-TIME-RELEASE-BOUND-EXECUTION-v1"

def _root(obj):
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class ExecutionDisposition(str, Enum):
    ADMIT_D0 = "ADMIT_EFFECT_TIME_RELEASE_BOUND_EXECUTION_D0"
    HOLD_RUNTIME_BOUND = "HOLD_RUNTIME_BOUND"
    HOLD_TIME_CUT_MISMATCH = "HOLD_TIME_CUT_MISMATCH"
    HOLD_PROCESS_FUTURE_OBSERVATION = "HOLD_PROCESS_FUTURE_OBSERVATION"
    HOLD_EFFECT_TIME_PROCESS = "HOLD_EFFECT_TIME_PROCESS"
    HOLD_EXECUTABLE_SCOPE_INVALID = "HOLD_EXECUTABLE_SCOPE_INVALID"
    HOLD_LOADED_UNIT_SET_MISMATCH = "HOLD_LOADED_UNIT_SET_MISMATCH"
    HOLD_LOADED_UNIT_HASH_MISMATCH = "HOLD_LOADED_UNIT_HASH_MISMATCH"

@dataclass(frozen=True)
class ExecutableScope:
    required_units: tuple[str, ...]
    def validate(self, manifest: RuntimeReleaseManifest):
        if not self.required_units or any(not isinstance(x, str) or not x for x in self.required_units):
            return False
        if len(set(self.required_units)) != len(self.required_units):
            return False
        return set(self.required_units).issubset(set(manifest.components))
    def root(self, manifest: RuntimeReleaseManifest):
        expected = tuple(sorted((name, manifest.components[name]) for name in self.required_units))
        return _root({"schema": SCHEMA, "required_units": expected})

@dataclass(frozen=True)
class EffectTimeExecutionPermit:
    disposition: ExecutionDisposition
    reason: str
    operation_root: str
    attempt_root: str | None
    release_root: str
    runtime_bound_permit_root: str | None
    effect_time_witness_root: str | None
    executable_scope_root: str | None
    execution_permit_root: str | None
    effect_authority: bool = False
    training_authority: bool = False
    checkpoint_authority: bool = False
    project_write_authority: bool = False
    gate10: bool = False

def bind_effect_time(
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
    process: LoadedProcessWitness,
    at_use: AtUseObservation,
    executable_scope: ExecutableScope,
    now_ms: int,
    max_age_ms: int = 300_000,
) -> EffectTimeExecutionPermit:
    op_root = operation.root()
    release_root = manifest.release_root

    def hold(disposition, reason, parent=None, proc=None, scope_root=None):
        return EffectTimeExecutionPermit(
            disposition, reason, op_root,
            None if parent is None else parent.attempt_root,
            release_root,
            None if parent is None else parent.permit_root,
            None if proc is None else proc.effect_time_witness_root,
            scope_root, None,
        )

    if at_use.now != now_ms:
        return hold(ExecutionDisposition.HOLD_TIME_CUT_MISMATCH, "PARENTS_NOT_REVALIDATED_AT_SAME_CUT")

    parent = bind_at_use(
        operation, hops, admission, ctx, manifest, target,
        owner_reported_updated=owner_reported_updated,
        measurement=measurement, evidence=evidence,
        now_ms=now_ms, max_age_ms=max_age_ms,
    )
    if parent.disposition is not PermitDisposition.ADMIT_D0 or parent.permit_root is None:
        return hold(ExecutionDisposition.HOLD_RUNTIME_BOUND, f"O21:{parent.reason}", parent=parent)
    if measurement is None or evidence is None:
        return hold(ExecutionDisposition.HOLD_RUNTIME_BOUND, "O21:CURRENT_MEASUREMENT_REQUIRED", parent=parent)
    if process.observed_at > now_ms:
        return hold(ExecutionDisposition.HOLD_PROCESS_FUTURE_OBSERVATION, "PROCESS_WITNESS_AFTER_AT_USE_CUT", parent=parent)

    derived_installed = InstalledRuntimeAttestation(
        host_id=measurement.host_id,
        installed_runtime_root=release_root,
        generation=manifest.owner_generation,
        observed_at=measurement.observed_at_ms,
        valid_until=evidence.expires_at_ms,
        authenticated=True,
        current=True,
    )
    proc = decide_process(derived_installed, process, at_use)
    if proc.disposition is not ProcessDisposition.ADMIT_D0 or proc.effect_time_witness_root is None:
        return hold(ExecutionDisposition.HOLD_EFFECT_TIME_PROCESS, f"O20R:{proc.reason}", parent=parent, proc=proc)

    if not executable_scope.validate(manifest):
        return hold(ExecutionDisposition.HOLD_EXECUTABLE_SCOPE_INVALID, "EXECUTABLE_SCOPE_NOT_MANIFEST_BOUND", parent=parent, proc=proc)
    scope_root = executable_scope.root(manifest)
    loaded = process.loaded_units
    if len({name for name, _ in loaded}) != len(loaded):
        return hold(ExecutionDisposition.HOLD_LOADED_UNIT_SET_MISMATCH, "DUPLICATE_LOADED_UNIT_NAME", parent=parent, proc=proc, scope_root=scope_root)
    loaded_map = dict(loaded)
    required = set(executable_scope.required_units)
    if set(loaded_map) != required:
        return hold(ExecutionDisposition.HOLD_LOADED_UNIT_SET_MISMATCH, "LOADED_ANSWER_BEARING_UNIT_SET_DIFFERS_FROM_AUTHORIZED_SCOPE", parent=parent, proc=proc, scope_root=scope_root)
    if any(loaded_map[name] != manifest.components[name] for name in required):
        return hold(ExecutionDisposition.HOLD_LOADED_UNIT_HASH_MISMATCH, "LOADED_ANSWER_BEARING_BYTES_DIFFER_FROM_AUTHORIZED_RELEASE", parent=parent, proc=proc, scope_root=scope_root)

    permit_root = _root({
        "schema": SCHEMA,
        "runtime_bound_permit_root": parent.permit_root,
        "effect_time_witness_root": proc.effect_time_witness_root,
        "executable_scope_root": scope_root,
        "operation_root": parent.operation_root,
        "attempt_root": parent.attempt_root,
        "release_root": parent.release_root,
        "measurement_root": parent.measurement_root,
        "target_host_id": parent.target_host_id,
        "target_host_incarnation": parent.target_host_incarnation,
        "source_incarnation_root": parent.source_incarnation_root,
        "loaded_units_root": process.loaded_units_root(),
        "process_binding_root": process.binding_root(),
        "at_use_ms": now_ms,
    })
    return EffectTimeExecutionPermit(
        ExecutionDisposition.ADMIT_D0, "OK_EFFECT_TIME_RELEASE_BOUND_D0",
        parent.operation_root, parent.attempt_root, parent.release_root,
        parent.permit_root, proc.effect_time_witness_root, scope_root, permit_root,
    )
