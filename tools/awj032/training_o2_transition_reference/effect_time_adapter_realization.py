from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Callable

from tools.awj032.training_o2_transition_reference.transition_envelope import AdapterCore, TransitionEnvelope, verify_transition

SCHEMA = 'AURA-AWJ032-O4-EFFECT-TIME-ADAPTER-REALIZATION-v1'
D0_TRANSITION = 'ADMIT_D0_PROOF_CARRYING_TRANSITION'
D0_EFFECT_TIME = 'ADMIT_D0_EFFECT_TIME_ADAPTER_REALIZATION'
HEX = set('0123456789abcdef')


def _canon(v): return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
def _root(v): return sha256(_canon(v)).hexdigest()
def _isroot(v): return isinstance(v, str) and len(v) == 64 and set(v) <= HEX
def _needroot(v, name):
    if not _isroot(v): raise ValueError(f'{name}: sha256 required')
def _valid_int(v): return type(v) is int


@dataclass(frozen=True)
class StableAdapterRealization:
    transition_root: str
    adapter_core_root: str
    runtime_root: str
    loader_root: str
    cache_schema_root: str
    output_kind: str = 'runtime_adapter'
    def __post_init__(self):
        for n in ('transition_root','adapter_core_root','runtime_root','loader_root','cache_schema_root'):
            _needroot(getattr(self, n), n)
        if self.output_kind not in {'runtime_adapter','merged_checkpoint'}: raise ValueError('unsupported output_kind')
    @property
    def realization_root(self):
        return _root({'schema':SCHEMA,'kind':'stable_adapter_realization',**asdict(self)})
    @property
    def cache_root(self):
        return _root({'schema':SCHEMA,'kind':'immutable_adapter_cache','realization_root':self.realization_root})


@dataclass(frozen=True)
class AtUseAdapterObservation:
    now: int
    realization_root: str
    cache_root: str
    process_witness_root: str
    process_generation: int
    load_generation: int
    loaded_units_root: str
    loaded_adapter_unit_root: str
    dispatch_root: str
    mutation_generation: int
    serving_population_root: str
    selected_worker_id: str
    def __post_init__(self):
        if not _valid_int(self.now) or self.now < 0: raise ValueError('now')
        for n in ('realization_root','cache_root','process_witness_root','loaded_units_root','loaded_adapter_unit_root','dispatch_root','serving_population_root'):
            _needroot(getattr(self,n),n)
        if not _valid_int(self.process_generation) or self.process_generation < 1: raise ValueError('process_generation')
        if not _valid_int(self.load_generation) or self.load_generation < 1: raise ValueError('load_generation')
        if not _valid_int(self.mutation_generation) or self.mutation_generation < 0: raise ValueError('mutation_generation')
        if not self.selected_worker_id: raise ValueError('selected_worker_id')


@dataclass(frozen=True)
class VerifiedProcessProjection:
    process_witness_root: str
    valid_until: int
    process_generation: int
    load_generation: int
    loaded_units_root: str
    loaded_adapter_unit_root: str
    dispatch_root: str
    mutation_generation: int
    serving_population_root: str
    selected_worker_id: str
    current_d0: bool
    effect_authority: bool = False
    checkpoint_authority: bool = False
    gate10: bool = False
    def __post_init__(self):
        _needroot(self.process_witness_root,'process_witness_root')
        for n in ('loaded_units_root','loaded_adapter_unit_root','dispatch_root','serving_population_root'):
            _needroot(getattr(self,n),n)
        if not _valid_int(self.valid_until) or self.valid_until < 0: raise ValueError('valid_until')
        if not _valid_int(self.process_generation) or self.process_generation < 1: raise ValueError('process_generation')
        if not _valid_int(self.load_generation) or self.load_generation < 1: raise ValueError('load_generation')
        if not _valid_int(self.mutation_generation) or self.mutation_generation < 0: raise ValueError('mutation_generation')
        if not self.selected_worker_id: raise ValueError('selected_worker_id')
        if type(self.current_d0) is not bool: raise ValueError('current_d0')


@dataclass(frozen=True)
class EffectTimeRealizationDecision:
    admitted: bool
    reason: str
    realization_root: str
    cache_root: str
    process_witness_root: str | None
    effect_time_root: str | None
    effect_authority: bool = False
    checkpoint_authority: bool = False
    gate10: bool = False


def admit_effect_time_realization(*, realization:StableAdapterRealization, observation:AtUseAdapterObservation,
                                  resolve_process_currentness:Callable[[AtUseAdapterObservation], VerifiedProcessProjection | None]):
    def hold(reason, pw=None):
        return EffectTimeRealizationDecision(False, reason, realization.realization_root, realization.cache_root, pw, None)
    if observation.realization_root != realization.realization_root: return hold('HOLD_REALIZATION_IDENTITY')
    if observation.cache_root != realization.cache_root: return hold('HOLD_CACHE_IDENTITY')
    verified = resolve_process_currentness(observation)
    if verified is None: return hold('HOLD_PROCESS_CURRENTNESS_UNVERIFIED')
    if not verified.current_d0: return hold('HOLD_PROCESS_NOT_CURRENT_D0', verified.process_witness_root)
    if verified.effect_authority or verified.checkpoint_authority or verified.gate10:
        return hold('HOLD_PROCESS_PROJECTION_AUTHORITY_ESCALATION', verified.process_witness_root)
    if observation.now > verified.valid_until: return hold('HOLD_PROCESS_CURRENTNESS_EXPIRED', verified.process_witness_root)
    actual=(observation.process_witness_root,observation.process_generation,observation.load_generation,
            observation.loaded_units_root,observation.loaded_adapter_unit_root,observation.dispatch_root,
            observation.mutation_generation,observation.serving_population_root,observation.selected_worker_id)
    expected=(verified.process_witness_root,verified.process_generation,verified.load_generation,
              verified.loaded_units_root,verified.loaded_adapter_unit_root,verified.dispatch_root,
              verified.mutation_generation,verified.serving_population_root,verified.selected_worker_id)
    if actual != expected: return hold('HOLD_EFFECT_TIME_PROCESS_BINDING', verified.process_witness_root)
    if verified.loaded_adapter_unit_root != realization.cache_root:
        return hold('HOLD_LOADED_ADAPTER_REALIZATION_MOVED', verified.process_witness_root)
    er=_root({'schema':SCHEMA,'kind':'effect_time_adapter_realization','realization_root':realization.realization_root,
              'cache_root':realization.cache_root,'process_witness_root':verified.process_witness_root,
              'process_generation':verified.process_generation,'load_generation':verified.load_generation,
              'loaded_units_root':verified.loaded_units_root,'dispatch_root':verified.dispatch_root,
              'mutation_generation':verified.mutation_generation,'serving_population_root':verified.serving_population_root,
              'selected_worker_id':verified.selected_worker_id,'now':observation.now})
    return EffectTimeRealizationDecision(True,D0_EFFECT_TIME,realization.realization_root,realization.cache_root,verified.process_witness_root,er)


def verify_effect_time_transition(*, core:AdapterCore, env:TransitionEnvelope, realization:StableAdapterRealization,
                                  observation:AtUseAdapterObservation,
                                  resolve_process_currentness:Callable[[AtUseAdapterObservation], VerifiedProcessProjection | None],
                                  transition_kwargs:dict):
    transition = verify_transition(core=core, env=env, **transition_kwargs)
    if transition != D0_TRANSITION:
        return EffectTimeRealizationDecision(False,'HOLD_TRANSITION:'+transition,realization.realization_root,realization.cache_root,None,None)
    if realization.transition_root != env.transition_root:
        return EffectTimeRealizationDecision(False,'HOLD_REALIZATION_TRANSITION_BINDING',realization.realization_root,realization.cache_root,None,None)
    if realization.adapter_core_root != core.identity_root:
        return EffectTimeRealizationDecision(False,'HOLD_REALIZATION_CORE_BINDING',realization.realization_root,realization.cache_root,None,None)
    if realization.runtime_root != env.intent.inference_runtime_root:
        return EffectTimeRealizationDecision(False,'HOLD_REALIZATION_RUNTIME_BINDING',realization.realization_root,realization.cache_root,None,None)
    return admit_effect_time_realization(realization=realization,observation=observation,resolve_process_currentness=resolve_process_currentness)
