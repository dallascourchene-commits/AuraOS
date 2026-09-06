from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from typing import Sequence
from clock_admission_r42 import CommitTimeWitness, ClockAdmission, ClockGuardReceipt, CLOCK_SCOPE, guarded_resource_commit, digest

D0='D0'
HEX=set('0123456789abcdef')

def _hex64(v): return type(v) is str and len(v)==64 and all(c in HEX for c in v)
def _text(v): return type(v) is str and bool(v) and all(ord(c)>=32 for c in v)

@dataclass(frozen=True)
class TrustedClockAdmission:
    admission_root:str
    witness_root:str
    producer_id:str
    clock_generation:str
    scope:str
    observed_s:int
    consumed:bool=False

@dataclass(frozen=True)
class ClockAdmissionRegistrySnapshot:
    generation:int
    entries:tuple[TrustedClockAdmission,...]
    authority_ceiling:str=D0
    gate10:bool=False
    @property
    def root(self):
        return digest({'schema':'AURA-CLOCK-ADMISSION-REGISTRY-R4.3','generation':self.generation,
                       'entries':[asdict(e) for e in sorted(self.entries,key=lambda e:e.admission_root)],
                       'authority_ceiling':self.authority_ceiling,'gate10':self.gate10})

@dataclass(frozen=True)
class ClockRegistryGuardReceipt:
    admitted:bool
    reasons:tuple[str,...]
    prior_registry_root:str
    next_registry_root:str
    admission_root:str|None
    witness_root:str|None
    downstream:ClockGuardReceipt|None
    next_registry:ClockAdmissionRegistrySnapshot|None
    effect_authority:bool=False
    gate10:bool=False


def trusted_entry(w:CommitTimeWitness,a:ClockAdmission)->TrustedClockAdmission:
    return TrustedClockAdmission(a.currentness_root,w.witness_root,w.producer_id,w.clock_generation,w.scope,w.observed_s,False)

def make_registry(entries:Sequence[TrustedClockAdmission],generation:int=1):
    return ClockAdmissionRegistrySnapshot(generation,tuple(entries))

def _validate_registry(s:ClockAdmissionRegistrySnapshot):
    reasons=[]
    if type(s.generation) is not int or isinstance(s.generation,bool) or s.generation<0: reasons.append('CLOCK_REGISTRY_GENERATION_INVALID')
    if s.authority_ceiling!=D0 or s.gate10: reasons.append('CLOCK_REGISTRY_AUTHORITY_WIDENING')
    roots=[]
    for e in s.entries:
        roots.append(e.admission_root)
        if not _hex64(e.admission_root) or not _hex64(e.witness_root): reasons.append('CLOCK_REGISTRY_ENTRY_ROOT_INVALID')
        if not all(_text(x) for x in (e.producer_id,e.clock_generation,e.scope)): reasons.append('CLOCK_REGISTRY_ENTRY_IDENTITY_INVALID')
        if type(e.observed_s) is not int or isinstance(e.observed_s,bool) or e.observed_s<0: reasons.append('CLOCK_REGISTRY_ENTRY_TIME_INVALID')
        if type(e.consumed) is not bool: reasons.append('CLOCK_REGISTRY_ENTRY_CONSUMED_INVALID')
    if len(roots)!=len(set(roots)): reasons.append('CLOCK_REGISTRY_DUPLICATE_ADMISSION_ROOT')
    return tuple(sorted(set(reasons)))

def guarded_resource_commit_r43(submitted,*,observed_owner_head,observed_lease_root,
    clock_witness:CommitTimeWitness|None,clock_admission:ClockAdmission|None,
    clock_registry:ClockAdmissionRegistrySnapshot|None,observed_clock_registry_root:str|None,
    owner,registry,proposals):
    reasons=[]
    if clock_registry is None: reasons.append('CLOCK_REGISTRY_REQUIRED')
    if observed_clock_registry_root is None or not _hex64(observed_clock_registry_root): reasons.append('OBSERVED_CLOCK_REGISTRY_ROOT_REQUIRED')
    if clock_witness is None: reasons.append('COMMIT_TIME_WITNESS_REQUIRED')
    if clock_admission is None: reasons.append('CLOCK_ADMISSION_REQUIRED')
    if clock_registry is not None:
        reasons.extend(_validate_registry(clock_registry))
        if observed_clock_registry_root is not None and observed_clock_registry_root!=clock_registry.root:
            reasons.append('CLOCK_REGISTRY_MOVED')
    match=None
    if clock_registry is not None and clock_admission is not None:
        matches=[e for e in clock_registry.entries if e.admission_root==clock_admission.currentness_root]
        if not matches: reasons.append('CLOCK_ADMISSION_NOT_PRETRUSTED')
        elif len(matches)==1:
            match=matches[0]
            if match.consumed: reasons.append('CLOCK_ADMISSION_ALREADY_CONSUMED')
    if match is not None and clock_witness is not None and clock_admission is not None:
        if match.witness_root!=clock_witness.witness_root: reasons.append('CLOCK_REGISTRY_WITNESS_MISMATCH')
        if (match.producer_id,match.clock_generation,match.scope)!=(clock_witness.producer_id,clock_witness.clock_generation,clock_witness.scope):
            reasons.append('CLOCK_REGISTRY_IDENTITY_MISMATCH')
        if match.observed_s!=clock_witness.observed_s: reasons.append('CLOCK_REGISTRY_TIME_MISMATCH')
        if clock_admission.exact_witness_root!=clock_witness.witness_root: reasons.append('CLOCK_WITNESS_ADMISSION_MISMATCH')
        if clock_admission.scope!=CLOCK_SCOPE: reasons.append('CLOCK_SCOPE_MISMATCH')
    prior=clock_registry.root if clock_registry is not None else '0'*64
    if reasons:
        return ClockRegistryGuardReceipt(False,tuple(sorted(set(reasons))),prior,prior,getattr(clock_admission,'currentness_root',None),getattr(clock_witness,'witness_root',None),None,clock_registry)
    downstream=guarded_resource_commit(submitted,observed_owner_head=observed_owner_head,observed_lease_root=observed_lease_root,
        clock_witness=clock_witness,clock_admission=clock_admission,expected_clock_admission_root=match.admission_root,
        owner=owner,registry=registry,proposals=proposals)
    if not downstream.admitted:
        return ClockRegistryGuardReceipt(False,('DOWNSTREAM_RESOURCE_COMMIT_HOLD',),prior,prior,match.admission_root,match.witness_root,downstream,clock_registry)
    nxt_entries=tuple(replace(e,consumed=True) if e.admission_root==match.admission_root else e for e in clock_registry.entries)
    nxt=ClockAdmissionRegistrySnapshot(clock_registry.generation+1,nxt_entries,clock_registry.authority_ceiling,clock_registry.gate10)
    return ClockRegistryGuardReceipt(True,(),prior,nxt.root,match.admission_root,match.witness_root,downstream,nxt)

def omega8_r43_keeper(axes): return len(axes)==8 and tuple(axes)==(2,2,2,2,2,2,2,2)
def collapse13_r43(core8,tail5):
    if len(tail5)!=5 or any(type(x) is not int or x not in (0,1,2) for x in tail5): raise ValueError('BAD_13D_TAIL')
    return omega8_r43_keeper(core8)
