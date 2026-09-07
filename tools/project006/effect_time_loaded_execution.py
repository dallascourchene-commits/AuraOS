from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib,json
from typing import Optional
HEX=set('0123456789abcdef')
class LoadedExecutionError(ValueError): pass
class Disposition(str,Enum):
    HOLD_INSTALLED_RELEASE='HOLD_INSTALLED_RELEASE'
    HOLD_SOURCE_TOPOLOGY='HOLD_SOURCE_TOPOLOGY'
    HOLD_UNAUTHENTICATED_PROCESS='HOLD_UNAUTHENTICATED_PROCESS'
    HOLD_PROCESS_IDENTITY='HOLD_PROCESS_IDENTITY'
    HOLD_PROCESS_GENERATION='HOLD_PROCESS_GENERATION'
    HOLD_LOAD_GENERATION='HOLD_LOAD_GENERATION'
    HOLD_MUTATION_GENERATION='HOLD_MUTATION_GENERATION'
    HOLD_ANSWER_UNIT='HOLD_ANSWER_UNIT'
    HOLD_DISPATCH='HOLD_DISPATCH'
    HOLD_UNRESOLVED_UNIT='HOLD_UNRESOLVED_UNIT'
    HOLD_WORKER_SELECTION='HOLD_WORKER_SELECTION'
    HOLD_STALE_EFFECT_TIME='HOLD_STALE_EFFECT_TIME'
    CURRENT_EFFECT_EXECUTABLE='CURRENT_EFFECT_EXECUTABLE'

def _hex(v):return isinstance(v,str) and len(v)==64 and set(v)<=HEX
def _root(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),default=lambda x:x.value if isinstance(x,Enum) else x.__dict__).encode()).hexdigest()

@dataclass(frozen=True)
class ExecutionTopologyManifest:
    release_root:str
    source_root:str
    target_topology_root:str
    answer_unit_root:str
    dispatch_root:str
    def validate(self):
        if any(not _hex(v) for v in (self.release_root,self.source_root,self.target_topology_root,self.answer_unit_root,self.dispatch_root)): raise LoadedExecutionError('MANIFEST_ROOT_INVALID')
    @property
    def manifest_root(self): self.validate(); return _root(self)

@dataclass(frozen=True)
class LoadedProcessMeasurement:
    installed_release_root:str
    source_root:str
    target_topology_root:str
    process_identity_root:str
    process_generation:int
    load_generation:int
    mutation_generation:int
    loaded_answer_unit_root:str
    dispatch_root:str
    unresolved_units:tuple[str,...]
    serving_population_root:str
    serving_population_size:int
    selected_worker_root:Optional[str]
    observed_at_ms:int
    def validate(self):
        roots=(self.installed_release_root,self.source_root,self.target_topology_root,self.process_identity_root,self.loaded_answer_unit_root,self.dispatch_root,self.serving_population_root)
        if any(not _hex(v) for v in roots): raise LoadedExecutionError('MEASUREMENT_ROOT_INVALID')
        if any(not isinstance(x,int) or x<0 for x in (self.process_generation,self.load_generation,self.mutation_generation,self.observed_at_ms)): raise LoadedExecutionError('MEASUREMENT_GENERATION_INVALID')
        if not isinstance(self.serving_population_size,int) or self.serving_population_size<1: raise LoadedExecutionError('POPULATION_INVALID')
        if self.selected_worker_root is not None and not _hex(self.selected_worker_root): raise LoadedExecutionError('SELECTED_WORKER_ROOT_INVALID')
        if any(not isinstance(x,str) or not x for x in self.unresolved_units): raise LoadedExecutionError('UNRESOLVED_UNIT_INVALID')
    @property
    def measurement_root(self): self.validate(); return _root(self)

@dataclass(frozen=True)
class ProcessEvidence:
    measurement_root:str
    manifest_root:str
    verifier_id:str
    observer_id:str
    authenticated:bool
    independent:bool
    issued_at_ms:int
    expires_at_ms:int
    def validate(self):
        if not _hex(self.measurement_root) or not _hex(self.manifest_root): raise LoadedExecutionError('EVIDENCE_ROOT_INVALID')
        if not self.verifier_id or not self.observer_id or self.verifier_id==self.observer_id: raise LoadedExecutionError('EVIDENCE_ACTOR_INVALID')
        if not isinstance(self.authenticated,bool) or not isinstance(self.independent,bool): raise LoadedExecutionError('EVIDENCE_BOOL_INVALID')
        if any(not isinstance(x,int) or x<0 for x in (self.issued_at_ms,self.expires_at_ms)) or self.expires_at_ms<self.issued_at_ms: raise LoadedExecutionError('EVIDENCE_TIME_INVALID')

@dataclass(frozen=True)
class AtUseExpectation:
    process_identity_root:str
    process_generation:int
    load_generation:int
    mutation_generation:int
    selected_worker_root:Optional[str]
    now_ms:int
    max_age_ms:int=30_000
    def validate(self):
        if not _hex(self.process_identity_root): raise LoadedExecutionError('EXPECTED_PROCESS_ROOT_INVALID')
        if any(not isinstance(x,int) or x<0 for x in (self.process_generation,self.load_generation,self.mutation_generation,self.now_ms,self.max_age_ms)): raise LoadedExecutionError('EXPECTED_GENERATION_INVALID')
        if self.selected_worker_root is not None and not _hex(self.selected_worker_root): raise LoadedExecutionError('EXPECTED_WORKER_INVALID')

@dataclass(frozen=True)
class ExecutionAttestation:
    disposition:Disposition
    current:bool
    reasons:tuple[str,...]
    manifest_root:str
    measurement_root:str
    process_identity_root:str
    def to_dict(self):return {'disposition':self.disposition.value,'current':self.current,'reasons':list(self.reasons),'manifest_root':self.manifest_root,'measurement_root':self.measurement_root,'process_identity_root':self.process_identity_root}

def attest_loaded_execution(manifest:ExecutionTopologyManifest, measurement:LoadedProcessMeasurement, evidence:ProcessEvidence, expected:AtUseExpectation)->ExecutionAttestation:
    manifest.validate(); measurement.validate(); evidence.validate(); expected.validate()
    mr=measurement.measurement_root; mm=manifest.manifest_root
    def hold(d,r): return ExecutionAttestation(d,False,(r,),mm,mr,measurement.process_identity_root)
    if measurement.installed_release_root!=manifest.release_root: return hold(Disposition.HOLD_INSTALLED_RELEASE,'INSTALLED_RELEASE_MOVED')
    if measurement.source_root!=manifest.source_root or measurement.target_topology_root!=manifest.target_topology_root: return hold(Disposition.HOLD_SOURCE_TOPOLOGY,'CORE_SOURCE_OR_TOPOLOGY_DETACHED')
    if evidence.measurement_root!=mr or evidence.manifest_root!=mm or not evidence.authenticated or not evidence.independent: return hold(Disposition.HOLD_UNAUTHENTICATED_PROCESS,'PROCESS_MEASUREMENT_UNAUTHENTICATED')
    if measurement.process_identity_root!=expected.process_identity_root: return hold(Disposition.HOLD_PROCESS_IDENTITY,'PROCESS_IDENTITY_MOVED')
    if measurement.process_generation!=expected.process_generation: return hold(Disposition.HOLD_PROCESS_GENERATION,'PROCESS_GENERATION_MOVED')
    if measurement.load_generation!=expected.load_generation: return hold(Disposition.HOLD_LOAD_GENERATION,'LOAD_GENERATION_MOVED')
    if measurement.mutation_generation!=expected.mutation_generation: return hold(Disposition.HOLD_MUTATION_GENERATION,'MUTATION_GENERATION_MOVED')
    if measurement.loaded_answer_unit_root!=manifest.answer_unit_root: return hold(Disposition.HOLD_ANSWER_UNIT,'ANSWER_BEARING_UNIT_MOVED')
    if measurement.dispatch_root!=manifest.dispatch_root: return hold(Disposition.HOLD_DISPATCH,'DISPATCH_MOVED')
    if measurement.unresolved_units: return hold(Disposition.HOLD_UNRESOLVED_UNIT,'UNRESOLVED_ANSWER_BEARING_UNIT')
    if measurement.serving_population_size>1:
        if expected.selected_worker_root is None or measurement.selected_worker_root!=expected.selected_worker_root: return hold(Disposition.HOLD_WORKER_SELECTION,'HETEROGENEOUS_WORKER_NOT_EXACTLY_SELECTED')
    if expected.now_ms<evidence.issued_at_ms or expected.now_ms>evidence.expires_at_ms or expected.now_ms-measurement.observed_at_ms>expected.max_age_ms: return hold(Disposition.HOLD_STALE_EFFECT_TIME,'PROCESS_MEASUREMENT_STALE_AT_EFFECT_TIME')
    return ExecutionAttestation(Disposition.CURRENT_EFFECT_EXECUTABLE,True,(),mm,mr,measurement.process_identity_root)
