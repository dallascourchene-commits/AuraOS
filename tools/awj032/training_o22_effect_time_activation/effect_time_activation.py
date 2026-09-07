from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

from tools.awj032.training_o2_transition_reference.transition_envelope import (
    AdapterCore,
    OwnerResolver,
    PhysicalTraceAuthority,
    SignedAck,
    SignedResult,
    TransitionEnvelope,
    TransitionPermit,
    verify_transition,
)
from tools.arena.effect_time_loaded_process_currentness import (
    AtUseObservation,
    Disposition as ProcessDisposition,
    InstalledRuntimeAttestation,
    LoadedProcessWitness,
    decide as decide_process,
)

SCHEMA = "AURA-AWJ032-O22-EFFECT-TIME-LOADED-ADAPTER-TRANSITION-v1"


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Disposition(str, Enum):
    ADMIT_D0 = "ADMIT_EFFECT_TIME_LOADED_ADAPTER_TRANSITION_D0"
    HOLD = "HOLD"


@dataclass(frozen=True)
class ActivationDecision:
    disposition: Disposition
    reason: str
    transition_root: str
    adapter_core_root: str
    process_binding_root: str | None
    effect_time_process_root: str | None
    activation_witness_root: str | None = None
    effect_authority: bool = False
    training_authority: bool = False
    checkpoint_authority: bool = False
    project_write_authority: bool = False
    gate10: bool = False


def activation_dispatch_root(core: AdapterCore, env: TransitionEnvelope) -> str:
    return _digest({
        "schema": SCHEMA,
        "kind": "activation_dispatch",
        "transition_root": env.transition_root,
        "adapter_core_root": core.identity_root,
        "source_root": core.source_root,
        "target_topology_root": core.target_topology_root,
        "inference_runtime_root": env.intent.inference_runtime_root,
    })


def required_loaded_units(core: AdapterCore, env: TransitionEnvelope) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((
        ("awj032.adapter_core_root", core.identity_root),
        ("awj032.adapter_source_root", core.source_root),
        ("awj032.adapter_target_topology_root", core.target_topology_root),
        ("awj032.inference_runtime_root", env.intent.inference_runtime_root),
    )))


def bind_effect_time_activation(
    *,
    core: AdapterCore,
    env: TransitionEnvelope,
    permit: TransitionPermit,
    admission_resolver: OwnerResolver,
    trace_authority: PhysicalTraceAuthority,
    ack: SignedAck | None,
    result: SignedResult | None,
    independently_recomputed_source_digest: str | None,
    now: int,
    observed_source_root: str,
    observed_target_topology_root: str,
    installed: InstalledRuntimeAttestation,
    process: LoadedProcessWitness,
    at_use: AtUseObservation,
) -> ActivationDecision:
    transition_verdict = verify_transition(
        core=core,
        env=env,
        permit=permit,
        admission_resolver=admission_resolver,
        trace_authority=trace_authority,
        ack=ack,
        result=result,
        independently_recomputed_source_digest=independently_recomputed_source_digest,
        now=now,
        observed_source_root=observed_source_root,
        observed_target_topology_root=observed_target_topology_root,
    )
    process_decision = decide_process(installed, process, at_use)

    def hold(reason: str) -> ActivationDecision:
        return ActivationDecision(
            Disposition.HOLD,
            reason,
            env.transition_root,
            core.identity_root,
            process_decision.process_binding_root,
            process_decision.effect_time_witness_root,
        )

    if transition_verdict != "ADMIT_D0_PROOF_CARRYING_TRANSITION":
        return hold("HOLD_TRANSITION:" + transition_verdict)
    if process_decision.disposition is not ProcessDisposition.ADMIT_D0:
        return hold("HOLD_PROCESS:" + process_decision.reason)

    # The AWJ032 transition's exact inference runtime must be the runtime whose
    # loaded process was independently shown current at use.
    if installed.installed_runtime_root != env.intent.inference_runtime_root:
        return hold("HOLD_INFERENCE_RUNTIME_NOT_INSTALLED_RUNTIME")

    names = [name for name, _ in process.loaded_units]
    if len(names) != len(set(names)):
        return hold("HOLD_DUPLICATE_LOADED_UNIT_NAME")
    loaded = dict(process.loaded_units)
    required = dict(required_loaded_units(core, env))
    missing = tuple(sorted(set(required) - set(loaded)))
    if missing:
        return hold("HOLD_REQUIRED_LOADED_UNIT_MISSING:" + ",".join(missing))
    if loaded["awj032.adapter_core_root"] != core.identity_root:
        return hold("HOLD_LOADED_ADAPTER_CORE_MISMATCH")
    if loaded["awj032.adapter_source_root"] != core.source_root:
        return hold("HOLD_LOADED_SOURCE_MISMATCH")
    if loaded["awj032.adapter_target_topology_root"] != core.target_topology_root:
        return hold("HOLD_LOADED_TOPOLOGY_MISMATCH")
    if loaded["awj032.inference_runtime_root"] != env.intent.inference_runtime_root:
        return hold("HOLD_LOADED_RUNTIME_MISMATCH")

    expected_dispatch = activation_dispatch_root(core, env)
    if process.dispatch_root != expected_dispatch:
        return hold("HOLD_ACTIVATION_DISPATCH_MISMATCH")

    witness = _digest({
        "schema": SCHEMA,
        "transition_root": env.transition_root,
        "admission_permit_root": env.admission_permit_root,
        "adapter_core_root": core.identity_root,
        "adapter_source_root": core.source_root,
        "adapter_target_topology_root": core.target_topology_root,
        "inference_runtime_root": env.intent.inference_runtime_root,
        "process_binding_root": process_decision.process_binding_root,
        "effect_time_process_root": process_decision.effect_time_witness_root,
        "process_id": process.process_id,
        "process_start_nonce": process.process_start_nonce,
        "process_generation": process.process_generation,
        "load_generation": process.load_generation,
        "loaded_units_root": process.loaded_units_root(),
        "dispatch_root": process.dispatch_root,
        "serving_population_root": process.serving_population_root,
        "worker_id": process.worker_id,
    })
    return ActivationDecision(
        Disposition.ADMIT_D0,
        "CURRENT_LOADED_ADAPTER_TRANSITION_D0",
        env.transition_root,
        core.identity_root,
        process_decision.process_binding_root,
        process_decision.effect_time_witness_root,
        witness,
    )
