from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from enum import Enum
from hashlib import sha256
import json, math, re
from typing import Any, Iterable, Sequence

SCHEMA = 'AURA-SEMANTIC-AUTH-K27-ADMISSION-v1'
AGENT01_O18_SEMANTIC_ROOT = 'd23f330e80611004782aa70e61d3f6226812b2c2695abffbcfa13597af6380e6'
AGENT14_O5_GENERATION = '12ad0671bebef7f036e23bd54dcaea5630cc92da'
HEX40 = re.compile(r'^[0-9a-f]{40}$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
ID = re.compile(r'^[A-Za-z0-9_.:/@+-]{1,160}$')

class AdmissionError(ValueError): pass
class SemanticDecision(str, Enum):
    EXACT_CURRENT='EXACT_CURRENT'
    REBIND_ADMISSION='REBIND_ADMISSION'
    REPROVE_SECURITY='REPROVE_SECURITY'
class ReadjudicationDecision(str, Enum):
    REPROVE_LOCAL_FIRST='REPROVE_LOCAL_FIRST'
    HOLD_AUTHENTICATION_CUTSET='HOLD_AUTHENTICATION_CUTSET'
    ELIGIBLE_FOR_FRESH_READJUDICATION='ELIGIBLE_FOR_FRESH_READJUDICATION'
class Decision(str, Enum):
    ADMIT_RUNTIME_REUSE='ADMIT_RUNTIME_REUSE'
    REPROVE_SEMANTIC='REPROVE_SEMANTIC'
    READJUDICATE_EXTERNAL_AUTH='READJUDICATE_EXTERNAL_AUTH'
    HOLD='HOLD'

def canon(v: Any) -> bytes:
    try: return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    except (TypeError, ValueError) as exc: raise AdmissionError('NON_CANONICAL') from exc

def digest(v: Any) -> str: return sha256(canon(v)).hexdigest()
def _h40(x: Any, label: str) -> str:
    if not isinstance(x,str) or HEX40.fullmatch(x) is None: raise AdmissionError('INVALID_'+label.upper())
    return x
def _h64(x: Any, label: str) -> str:
    if not isinstance(x,str) or HEX64.fullmatch(x) is None: raise AdmissionError('INVALID_'+label.upper())
    return x
def _id(x: Any, label: str) -> str:
    if not isinstance(x,str) or ID.fullmatch(x) is None: raise AdmissionError('INVALID_'+label.upper())
    return x

def coordinate_for(identity_root: str) -> tuple[int,int,int]:
    raw=bytes.fromhex(_h64(identity_root,'identity_root')); return (raw[0]%27, raw[1]%27, raw[2]%27)

@dataclass(frozen=True)
class SemanticTransition:
    owner_proof_root: str
    decision: SemanticDecision
    semantic_domain_root: str
    semantic_projection_root: str
    dependency_root: str
    receipt_root: str
    d0: bool=True
    effect_authority: bool=False
    gate10: bool=False
    def body(self):
        return {'schema':SCHEMA+'-SEMANTIC','owner_proof_root':self.owner_proof_root,
                'decision':self.decision.value if isinstance(self.decision,SemanticDecision) else self.decision,
                'semantic_domain_root':self.semantic_domain_root,'semantic_projection_root':self.semantic_projection_root,
                'dependency_root':self.dependency_root,'d0':self.d0,'effect_authority':self.effect_authority,'gate10':self.gate10}

def make_semantic_transition(*, decision: SemanticDecision, semantic_domain_root: str, semantic_projection_root: str,
                             dependency_root: str, owner_proof_root: str=AGENT01_O18_SEMANTIC_ROOT) -> SemanticTransition:
    _h64(owner_proof_root,'semantic_owner_proof_root')
    for n,v in (('semantic_domain_root',semantic_domain_root),('semantic_projection_root',semantic_projection_root),('dependency_root',dependency_root)): _h64(v,n)
    if not isinstance(decision,SemanticDecision): raise AdmissionError('INVALID_SEMANTIC_DECISION')
    x=SemanticTransition(owner_proof_root,decision,semantic_domain_root,semantic_projection_root,dependency_root,'')
    return replace(x,receipt_root=digest(x.body()))

def verify_semantic(x: SemanticTransition) -> bool:
    if type(x) is not SemanticTransition or not isinstance(x.decision,SemanticDecision): return False
    if any(type(v) is not bool for v in (x.d0,x.effect_authority,x.gate10)): return False
    try:
        _h64(x.owner_proof_root,'semantic_owner_proof_root'); _h64(x.semantic_domain_root,'semantic_domain_root'); _h64(x.semantic_projection_root,'semantic_projection_root'); _h64(x.dependency_root,'dependency_root'); _h64(x.receipt_root,'semantic_receipt_root')
    except AdmissionError: return False
    return x.d0 and not x.effect_authority and not x.gate10 and x.receipt_root==digest(x.body())

@dataclass(frozen=True)
class ReadjudicationReceipt:
    owner_generation: str
    decision: ReadjudicationDecision
    local_surface_root: str
    auth_surface_root: str
    receipt_root: str
    d0: bool=True
    effect_authority: bool=False
    gate10: bool=False
    def body(self):
        return {'schema':SCHEMA+'-READJUDICATION','owner_generation':self.owner_generation,
                'decision':self.decision.value if isinstance(self.decision,ReadjudicationDecision) else self.decision,
                'local_surface_root':self.local_surface_root,'auth_surface_root':self.auth_surface_root,
                'd0':self.d0,'effect_authority':self.effect_authority,'gate10':self.gate10}

def make_readjudication(*, decision: ReadjudicationDecision, local_surface_root: str, auth_surface_root: str,
                        owner_generation: str=AGENT14_O5_GENERATION) -> ReadjudicationReceipt:
    _h40(owner_generation,'readjudication_owner_generation'); _h64(local_surface_root,'local_surface_root'); _h64(auth_surface_root,'auth_surface_root')
    if not isinstance(decision,ReadjudicationDecision): raise AdmissionError('INVALID_READJUDICATION_DECISION')
    x=ReadjudicationReceipt(owner_generation,decision,local_surface_root,auth_surface_root,'')
    return replace(x,receipt_root=digest(x.body()))

def verify_readjudication(x: ReadjudicationReceipt) -> bool:
    if type(x) is not ReadjudicationReceipt or not isinstance(x.decision,ReadjudicationDecision): return False
    if any(type(v) is not bool for v in (x.d0,x.effect_authority,x.gate10)): return False
    try:
        _h40(x.owner_generation,'readjudication_owner_generation'); _h64(x.local_surface_root,'local_surface_root'); _h64(x.auth_surface_root,'auth_surface_root'); _h64(x.receipt_root,'readjudication_receipt_root')
    except AdmissionError: return False
    return x.d0 and not x.effect_authority and not x.gate10 and x.receipt_root==digest(x.body())

@dataclass(frozen=True)
class CrossPlaneBinding:
    semantic_owner_proof_root: str
    readjudication_owner_generation: str
    semantic_receipt_root: str
    readjudication_receipt_root: str
    semantic_domain_root: str
    semantic_projection_root: str
    local_surface_root: str
    auth_surface_root: str
    binding_root: str
    def body(self):
        return {'schema':SCHEMA+'-CROSS-PLANE-BINDING','semantic_owner_proof_root':self.semantic_owner_proof_root,
                'readjudication_owner_generation':self.readjudication_owner_generation,'semantic_receipt_root':self.semantic_receipt_root,
                'readjudication_receipt_root':self.readjudication_receipt_root,'semantic_domain_root':self.semantic_domain_root,
                'semantic_projection_root':self.semantic_projection_root,'local_surface_root':self.local_surface_root,'auth_surface_root':self.auth_surface_root}

def make_cross_plane_binding(s: SemanticTransition, r: ReadjudicationReceipt) -> CrossPlaneBinding:
    if not verify_semantic(s) or not verify_readjudication(r): raise AdmissionError('INVALID_PARENT_RECEIPT')
    x=CrossPlaneBinding(s.owner_proof_root,r.owner_generation,s.receipt_root,r.receipt_root,s.semantic_domain_root,s.semantic_projection_root,r.local_surface_root,r.auth_surface_root,'')
    return replace(x,binding_root=digest(x.body()))

def verify_cross_plane_binding(x: CrossPlaneBinding)->bool:
    if type(x) is not CrossPlaneBinding:return False
    try:
        _h64(x.semantic_owner_proof_root,'semantic_owner_proof_root');_h40(x.readjudication_owner_generation,'readjudication_owner_generation')
        for n in ('semantic_receipt_root','readjudication_receipt_root','semantic_domain_root','semantic_projection_root','local_surface_root','auth_surface_root','binding_root'):_h64(getattr(x,n),n)
    except AdmissionError:return False
    return x.binding_root==digest(x.body())

@dataclass(frozen=True)
class UpstreamAdmissionSet:
    semantic_owner_proof_root: str
    readjudication_owner_generation: str
    accepted_binding_roots: tuple[str,...]
    external_receipt_root: str
    surface_root: str
    def body(self):
        return {'schema':SCHEMA+'-UPSTREAM-ADMISSION','semantic_owner_proof_root':self.semantic_owner_proof_root,
                'readjudication_owner_generation':self.readjudication_owner_generation,
                'accepted_binding_roots':list(self.accepted_binding_roots),'external_receipt_root':self.external_receipt_root}

def _roots(xs: Iterable[str], label: str) -> tuple[str,...]:
    if isinstance(xs,(str,bytes)): raise AdmissionError('INVALID_'+label.upper())
    out=tuple(sorted(xs))
    if not out or len(out)!=len(set(out)): raise AdmissionError('INVALID_'+label.upper())
    for x in out: _h64(x,label)
    return out

def make_admission_set(*, binding_roots: Sequence[str], external_receipt_root: str,
                       semantic_owner_proof_root: str=AGENT01_O18_SEMANTIC_ROOT,
                       readjudication_owner_generation: str=AGENT14_O5_GENERATION) -> UpstreamAdmissionSet:
    _h64(semantic_owner_proof_root,'semantic_owner_proof_root'); _h40(readjudication_owner_generation,'readjudication_owner_generation'); _h64(external_receipt_root,'external_receipt_root')
    x=UpstreamAdmissionSet(semantic_owner_proof_root,readjudication_owner_generation,_roots(binding_roots,'binding_root'),external_receipt_root,'')
    return replace(x,surface_root=digest(x.body()))

def verify_admission_set(x: UpstreamAdmissionSet)->bool:
    if type(x) is not UpstreamAdmissionSet: return False
    try:
        _h64(x.semantic_owner_proof_root,'semantic_owner_proof_root'); _h40(x.readjudication_owner_generation,'readjudication_owner_generation'); _roots(x.accepted_binding_roots,'binding_root'); _h64(x.external_receipt_root,'external_receipt_root'); _h64(x.surface_root,'surface_root')
    except AdmissionError: return False
    return x.surface_root==digest(x.body())

@dataclass(frozen=True)
class K27Entry:
    subject_id:str; identity_root:str; coordinate:tuple[int,int,int]
    semantic_root:str; semantic_domain_root:str; semantic_projection_root:str
    provider_anchor_root:str; dependency_root:str
    runtime_owner:str; runtime_generation:str; compatibility_profile:str; benchmark_generation:str
    payload_hash:str; cache_handle:str; entry_root:str
    def body(self):
        d=asdict(self); d['schema']=SCHEMA+'-ENTRY'; d.pop('entry_root'); d['coordinate']=list(self.coordinate); return d

def make_entry(*,subject_id:str,semantic_root:str,semantic_domain_root:str,semantic_projection_root:str,provider_anchor_root:str,dependency_root:str,
               runtime_owner:str,runtime_generation:str,compatibility_profile:str,benchmark_generation:str,payload_hash:str,cache_handle:str)->K27Entry:
    subject_id=_id(subject_id,'subject_id'); identity_root=digest({'schema':SCHEMA+'-IDENTITY','subject_id':subject_id})
    for n,v in (('semantic_root',semantic_root),('semantic_domain_root',semantic_domain_root),('semantic_projection_root',semantic_projection_root),('provider_anchor_root',provider_anchor_root),('dependency_root',dependency_root),('payload_hash',payload_hash)): _h64(v,n)
    _id(runtime_owner,'runtime_owner'); _h40(runtime_generation,'runtime_generation'); _id(compatibility_profile,'compatibility_profile'); _h40(benchmark_generation,'benchmark_generation'); _id(cache_handle,'cache_handle')
    x=K27Entry(subject_id,identity_root,coordinate_for(identity_root),semantic_root,semantic_domain_root,semantic_projection_root,provider_anchor_root,dependency_root,runtime_owner,runtime_generation,compatibility_profile,benchmark_generation,payload_hash,cache_handle,'')
    return replace(x,entry_root=digest(x.body()))

def verify_entry(x:K27Entry)->bool:
    if type(x) is not K27Entry: return False
    try:
        _id(x.subject_id,'subject_id'); ident=digest({'schema':SCHEMA+'-IDENTITY','subject_id':x.subject_id})
        if x.identity_root!=ident or x.coordinate!=coordinate_for(ident): return False
        for n,v in (('semantic_root',x.semantic_root),('semantic_domain_root',x.semantic_domain_root),('semantic_projection_root',x.semantic_projection_root),('provider_anchor_root',x.provider_anchor_root),('dependency_root',x.dependency_root),('payload_hash',x.payload_hash),('entry_root',x.entry_root)): _h64(v,n)
        _id(x.runtime_owner,'runtime_owner'); _h40(x.runtime_generation,'runtime_generation'); _id(x.compatibility_profile,'compatibility_profile'); _h40(x.benchmark_generation,'benchmark_generation'); _id(x.cache_handle,'cache_handle')
    except AdmissionError:return False
    return x.entry_root==digest(x.body())

@dataclass(frozen=True)
class CurrentContext:
    subject_id:str;semantic_root:str;semantic_domain_root:str;semantic_projection_root:str;provider_anchor_root:str;dependency_root:str
    runtime_owner:str;runtime_generation:str;compatibility_profile:str;benchmark_generation:str;payload_hash:str
    expected_local_surface_root:str;expected_auth_surface_root:str

@dataclass(frozen=True)
class RoutingSignals:
    recompute_cost:float;dependency_fanout:int;invocation_frequency:float;locality:float;queue_depth:int

def validate_context(c:CurrentContext):
    if type(c) is not CurrentContext: raise AdmissionError('CURRENT_CONTEXT_REQUIRED')
    _id(c.subject_id,'subject_id')
    for n in ('semantic_root','semantic_domain_root','semantic_projection_root','provider_anchor_root','dependency_root','payload_hash','expected_local_surface_root','expected_auth_surface_root'): _h64(getattr(c,n),n)
    _id(c.runtime_owner,'runtime_owner');_h40(c.runtime_generation,'runtime_generation');_id(c.compatibility_profile,'compatibility_profile');_h40(c.benchmark_generation,'benchmark_generation')

def route_score(s:RoutingSignals)->float:
    if type(s) is not RoutingSignals: raise AdmissionError('ROUTING_SIGNALS_REQUIRED')
    vals=(s.recompute_cost,s.invocation_frequency,s.locality)
    if any(type(v) not in (int,float) or isinstance(v,bool) or not math.isfinite(float(v)) or float(v)<0 for v in vals): raise AdmissionError('INVALID_ROUTING_FLOAT')
    if type(s.dependency_fanout) is not int or isinstance(s.dependency_fanout,bool) or s.dependency_fanout<0: raise AdmissionError('INVALID_FANOUT')
    if type(s.queue_depth) is not int or isinstance(s.queue_depth,bool) or s.queue_depth<0: raise AdmissionError('INVALID_QUEUE_DEPTH')
    score=(float(s.recompute_cost)*(1+s.dependency_fanout)*(1+float(s.invocation_frequency))*(1+float(s.locality)))/(1+s.queue_depth)
    if not math.isfinite(score): raise AdmissionError('ROUTING_SCORE_OVERFLOW')
    return round(score,12)

@dataclass(frozen=True)
class Receipt:
    decision:Decision;reasons:tuple[str,...];coordinate:tuple[int,int,int];route_score:float|None
    semantic_receipt_root:str;readjudication_receipt_root:str;cross_plane_binding_root:str;admission_surface_root:str;entry_root:str
    semantic_domain_root:str;semantic_projection_root:str;local_surface_root:str;auth_surface_root:str
    d0:bool=True;truth_authority:bool=False;effect_authority:bool=False;gate10:bool=False;receipt_root:str=''
    def body(self):
        d=asdict(self);d['schema']=SCHEMA+'-RECEIPT';d['decision']=self.decision.value;d.pop('receipt_root');d['coordinate']=list(self.coordinate);return d
    def verify(self):
        if not self.d0 or self.truth_authority or self.effect_authority or self.gate10:return False
        try:_h64(self.receipt_root,'receipt_root')
        except AdmissionError:return False
        return self.receipt_root==digest(self.body())

def decide(s:SemanticTransition,r:ReadjudicationReceipt,b:CrossPlaneBinding,a:UpstreamAdmissionSet,e:K27Entry,c:CurrentContext,signals:RoutingSignals)->Receipt:
    reasons=[];decision=Decision.HOLD;score=None
    if not verify_semantic(s): reasons.append('INVALID_SEMANTIC_RECEIPT')
    if not verify_readjudication(r): reasons.append('INVALID_READJUDICATION_RECEIPT')
    if not verify_cross_plane_binding(b): reasons.append('INVALID_CROSS_PLANE_BINDING')
    if not verify_admission_set(a): reasons.append('INVALID_UPSTREAM_ADMISSION_SET')
    if not verify_entry(e): reasons.append('INVALID_K27_ENTRY')
    try:validate_context(c)
    except AdmissionError as ex: reasons.append(str(ex))
    if not reasons:
        if s.owner_proof_root!=a.semantic_owner_proof_root: reasons.append('SEMANTIC_OWNER_PROOF_MISMATCH')
        if r.owner_generation!=a.readjudication_owner_generation: reasons.append('READJUDICATION_OWNER_GENERATION_MISMATCH')
        if b.binding_root not in a.accepted_binding_roots: reasons.append('CROSS_PLANE_BINDING_NOT_ADMITTED')
        if b.semantic_owner_proof_root!=s.owner_proof_root or b.readjudication_owner_generation!=r.owner_generation: reasons.append('CROSS_PLANE_OWNER_MISMATCH')
        if b.semantic_receipt_root!=s.receipt_root or b.readjudication_receipt_root!=r.receipt_root: reasons.append('CROSS_PLANE_RECEIPT_MISMATCH')
        if b.semantic_domain_root!=s.semantic_domain_root or b.semantic_projection_root!=s.semantic_projection_root: reasons.append('CROSS_PLANE_SEMANTIC_MISMATCH')
        if b.local_surface_root!=r.local_surface_root or b.auth_surface_root!=r.auth_surface_root: reasons.append('CROSS_PLANE_READJUDICATION_MISMATCH')
        if s.semantic_domain_root!=c.semantic_domain_root or e.semantic_domain_root!=c.semantic_domain_root: reasons.append('SEMANTIC_DOMAIN_MISMATCH')
        if s.semantic_projection_root!=c.semantic_projection_root or e.semantic_projection_root!=c.semantic_projection_root: reasons.append('SEMANTIC_PROJECTION_MISMATCH')
        if s.dependency_root!=c.dependency_root or e.dependency_root!=c.dependency_root: reasons.append('DEPENDENCY_ROOT_MISMATCH')
        if r.local_surface_root!=c.expected_local_surface_root: reasons.append('LOCAL_SURFACE_MISMATCH')
        if r.auth_surface_root!=c.expected_auth_surface_root: reasons.append('AUTH_SURFACE_MISMATCH')
        if e.subject_id!=c.subject_id: reasons.append('SUBJECT_MISMATCH')
        if e.semantic_root!=c.semantic_root: reasons.append('SEMANTIC_ROOT_MISMATCH')
        if e.provider_anchor_root!=c.provider_anchor_root: reasons.append('PROVIDER_ANCHOR_MISMATCH')
        if e.runtime_owner!=c.runtime_owner: reasons.append('RUNTIME_OWNER_MISMATCH')
        if e.runtime_generation!=c.runtime_generation: reasons.append('RUNTIME_GENERATION_MISMATCH')
        if e.compatibility_profile!=c.compatibility_profile: reasons.append('COMPATIBILITY_PROFILE_MISMATCH')
        if e.benchmark_generation!=c.benchmark_generation: reasons.append('BENCHMARK_GENERATION_MISMATCH')
        if e.payload_hash!=c.payload_hash: reasons.append('PAYLOAD_HASH_MISMATCH')
    if reasons:
        if any(x in reasons for x in ('SEMANTIC_DOMAIN_MISMATCH','SEMANTIC_PROJECTION_MISMATCH','SEMANTIC_OWNER_PROOF_MISMATCH','DEPENDENCY_ROOT_MISMATCH')) or (verify_semantic(s) and s.decision is SemanticDecision.REPROVE_SECURITY): decision=Decision.REPROVE_SEMANTIC
        else: decision=Decision.HOLD
    elif s.decision is SemanticDecision.REPROVE_SECURITY or r.decision is ReadjudicationDecision.REPROVE_LOCAL_FIRST:
        decision=Decision.REPROVE_SEMANTIC;reasons=['LOCAL_SEMANTIC_REPROOF_REQUIRED']
    elif r.decision is ReadjudicationDecision.HOLD_AUTHENTICATION_CUTSET:
        decision=Decision.READJUDICATE_EXTERNAL_AUTH;reasons=['EXTERNAL_AUTHENTICATION_INCOMPLETE']
    else:
        try:score=route_score(signals);decision=Decision.ADMIT_RUNTIME_REUSE;reasons=['OK']
        except AdmissionError as ex:decision=Decision.HOLD;reasons=[str(ex)]
    rr=Receipt(decision,tuple(reasons),e.coordinate if type(e) is K27Entry else (-1,-1,-1),score,
               s.receipt_root if type(s) is SemanticTransition else '0'*64,r.receipt_root if type(r) is ReadjudicationReceipt else '0'*64,
               b.binding_root if type(b) is CrossPlaneBinding else '0'*64,a.surface_root if type(a) is UpstreamAdmissionSet else '0'*64,e.entry_root if type(e) is K27Entry else '0'*64,
               c.semantic_domain_root if type(c) is CurrentContext else '0'*64,c.semantic_projection_root if type(c) is CurrentContext else '0'*64,
               c.expected_local_surface_root if type(c) is CurrentContext else '0'*64,c.expected_auth_surface_root if type(c) is CurrentContext else '0'*64)
    return replace(rr,receipt_root=digest(rr.body()))

def crystalline(state8:Sequence[int])->bool:return len(state8)==8 and all(type(x)is int and x==2 for x in state8)
def admission13(state13:Sequence[int])->bool:return len(state13)==13 and all(type(x)is int and x in (0,1,2) for x in state13) and crystalline(state13[:8])
