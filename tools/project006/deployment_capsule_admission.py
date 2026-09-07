from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, hmac, json
from typing import Optional, Tuple

HEX=set('0123456789abcdef')
class CapsuleError(ValueError): pass
class Disposition(str,Enum):
    HOST_OBSERVATION_REQUIRED='HOST_OBSERVATION_REQUIRED'
    HOLD_EVIDENCE_UNAUTHENTICATED='HOLD_EVIDENCE_UNAUTHENTICATED'
    HOLD_HOST_INCARNATION_MOVED='HOLD_HOST_INCARNATION_MOVED'
    HOLD_BASE_MOVED='HOLD_BASE_MOVED'
    HOLD_COMPONENT_SET_MOVED='HOLD_COMPONENT_SET_MOVED'
    HOLD_COMPONENT_VALUE_MOVED='HOLD_COMPONENT_VALUE_MOVED'
    HOLD_PROOF_SET_INCOMPLETE='HOLD_PROOF_SET_INCOMPLETE'
    HOLD_PROOF_VACUOUS='HOLD_PROOF_VACUOUS'
    HOLD_PROOF_NOT_EXACT_HEAD='HOLD_PROOF_NOT_EXACT_HEAD'
    HOLD_PROOF_FAILED='HOLD_PROOF_FAILED'
    HOLD_STALE_OBSERVATION='HOLD_STALE_OBSERVATION'
    READY_O21_PREPARE='READY_O21_PREPARE'

def _hex64(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX
def _root(o):
    return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),default=lambda x:x.value if isinstance(x,Enum) else x.__dict__).encode()).hexdigest()
def _pairs(xs:Tuple[Tuple[str,str],...])->Tuple[Tuple[str,str],...]:
    if not isinstance(xs,tuple) or any(not isinstance(p,tuple) or len(p)!=2 for p in xs): raise CapsuleError('PAIRS_NOT_DEEP_IMMUTABLE')
    if any(not k or not _hex64(v) for k,v in xs) or len({k for k,_ in xs})!=len(xs): raise CapsuleError('PAIR_SET_INVALID')
    if tuple(sorted(xs))!=xs: raise CapsuleError('PAIRS_NOT_CANONICAL')
    return xs

@dataclass(frozen=True)
class ProofClaim:
    name:str
    proof_root:str
    exact_head:str
    status:str
    executed_cases:int
    skipped_required_cases:int
    verifier_id:str
    observer_id:str
    def validate(self):
        if not self.name or not _hex64(self.proof_root) or not self.exact_head: raise CapsuleError('PROOF_IDENTITY_INVALID')
        if self.status not in ('PASS','FAIL'): raise CapsuleError('PROOF_STATUS_INVALID')
        if not isinstance(self.executed_cases,int) or self.executed_cases<0: raise CapsuleError('PROOF_CASE_COUNT_INVALID')
        if not isinstance(self.skipped_required_cases,int) or self.skipped_required_cases<0: raise CapsuleError('PROOF_SKIP_COUNT_INVALID')
        if not self.verifier_id or not self.observer_id or self.verifier_id==self.observer_id: raise CapsuleError('PROOF_INDEPENDENCE_INVALID')
    @property
    def root(self): self.validate(); return _root(self)

@dataclass(frozen=True)
class DeploymentCapsule:
    capsule_id:str
    repository:str
    target_head:str
    target_release_root:str
    expected_source_release_root:str
    expected_host_incarnation:str
    expected_components:Tuple[Tuple[str,str],...]
    required_proof_names:Tuple[str,...]
    canonical_repair_commit_root:str
    o21_contract_root:str
    def validate(self):
        if not self.capsule_id or not self.repository or not self.target_head or not self.expected_host_incarnation: raise CapsuleError('CAPSULE_IDENTITY_INVALID')
        for x in (self.target_release_root,self.expected_source_release_root,self.canonical_repair_commit_root,self.o21_contract_root):
            if not _hex64(x): raise CapsuleError('CAPSULE_ROOT_INVALID')
        _pairs(self.expected_components)
        if not isinstance(self.required_proof_names,tuple) or not self.required_proof_names or len(set(self.required_proof_names))!=len(self.required_proof_names) or tuple(sorted(self.required_proof_names))!=self.required_proof_names: raise CapsuleError('REQUIRED_PROOF_SET_INVALID')
    @property
    def capsule_root(self): self.validate(); return _root(self)

@dataclass(frozen=True)
class ObservedHostBasis:
    host_id:str
    host_incarnation:str
    installed_head:str
    installed_release_root:str
    components:Tuple[Tuple[str,str],...]
    source_incarnation_root:str
    observed_at_ms:int
    def validate(self):
        if not self.host_id or not self.host_incarnation or not self.installed_head: raise CapsuleError('HOST_BASIS_IDENTITY_INVALID')
        if not _hex64(self.installed_release_root) or not _hex64(self.source_incarnation_root): raise CapsuleError('HOST_BASIS_ROOT_INVALID')
        _pairs(self.components)
        if not isinstance(self.observed_at_ms,int) or self.observed_at_ms<0: raise CapsuleError('HOST_BASIS_TIME_INVALID')
    @property
    def basis_root(self): self.validate(); return _root(self)

@dataclass(frozen=True)
class AdmissionEvidence:
    capsule_root:str
    host_basis_root:str
    proof_claim_roots:Tuple[str,...]
    verifier_id:str
    observer_id:str
    issued_at_ms:int
    expires_at_ms:int
    mac_hex:str
    def validate(self):
        if not _hex64(self.capsule_root) or not _hex64(self.host_basis_root): raise CapsuleError('EVIDENCE_ROOT_INVALID')
        if not isinstance(self.proof_claim_roots,tuple) or any(not _hex64(x) for x in self.proof_claim_roots): raise CapsuleError('EVIDENCE_PROOF_ROOT_INVALID')
        if not self.verifier_id or not self.observer_id or self.verifier_id==self.observer_id: raise CapsuleError('EVIDENCE_INDEPENDENCE_INVALID')
        if not isinstance(self.issued_at_ms,int) or not isinstance(self.expires_at_ms,int) or self.issued_at_ms<0 or self.expires_at_ms<self.issued_at_ms: raise CapsuleError('EVIDENCE_TIME_INVALID')
        if not _hex64(self.mac_hex): raise CapsuleError('EVIDENCE_MAC_INVALID')
    def unsigned_payload(self):
        return {'capsule_root':self.capsule_root,'host_basis_root':self.host_basis_root,'proof_claim_roots':list(self.proof_claim_roots),'verifier_id':self.verifier_id,'observer_id':self.observer_id,'issued_at_ms':self.issued_at_ms,'expires_at_ms':self.expires_at_ms}

def sign_evidence(key:bytes,capsule:DeploymentCapsule,host:ObservedHostBasis,claims:Tuple[ProofClaim,...],verifier_id='owner-verifier',observer_id='independent-observer',issued_at_ms=1000,expires_at_ms=2000)->AdmissionEvidence:
    roots=tuple(c.root for c in claims)
    p={'capsule_root':capsule.capsule_root,'host_basis_root':host.basis_root,'proof_claim_roots':list(roots),'verifier_id':verifier_id,'observer_id':observer_id,'issued_at_ms':issued_at_ms,'expires_at_ms':expires_at_ms}
    mac=hmac.new(key,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
    return AdmissionEvidence(p['capsule_root'],p['host_basis_root'],roots,verifier_id,observer_id,issued_at_ms,expires_at_ms,mac)

def _verify_evidence(key:bytes,e:AdmissionEvidence)->bool:
    e.validate(); expected=hmac.new(key,json.dumps(e.unsigned_payload(),sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest(); return hmac.compare_digest(expected,e.mac_hex)

def admit_capsule(capsule:DeploymentCapsule, *, host:Optional[ObservedHostBasis], claims:Tuple[ProofClaim,...], evidence:Optional[AdmissionEvidence], key:bytes, now_ms:int, max_host_age_ms:int=300_000):
    capsule.validate()
    if host is None or evidence is None:
        return {'ready':False,'disposition':Disposition.HOST_OBSERVATION_REQUIRED.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':['EXACT_HOST_OBSERVATION_REQUIRED']}
    host.validate()
    for c in claims: c.validate()
    claim_roots=tuple(c.root for c in claims)
    if not _verify_evidence(key,evidence) or evidence.capsule_root!=capsule.capsule_root or evidence.host_basis_root!=host.basis_root or evidence.proof_claim_roots!=claim_roots:
        return {'ready':False,'disposition':Disposition.HOLD_EVIDENCE_UNAUTHENTICATED.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':['FULL_EVIDENCE_BINDING_FAILED']}
    if now_ms<evidence.issued_at_ms or now_ms>evidence.expires_at_ms or now_ms-host.observed_at_ms>max_host_age_ms:
        return {'ready':False,'disposition':Disposition.HOLD_STALE_OBSERVATION.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':['HOST_OR_EVIDENCE_NOT_FRESH_AT_USE']}
    if host.host_incarnation!=capsule.expected_host_incarnation:
        return {'ready':False,'disposition':Disposition.HOLD_HOST_INCARNATION_MOVED.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':['HOST_INCARNATION_MOVED']}
    if host.installed_release_root!=capsule.expected_source_release_root:
        return {'ready':False,'disposition':Disposition.HOLD_BASE_MOVED.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':['INSTALLED_SOURCE_RELEASE_MOVED']}
    ek={k for k,_ in capsule.expected_components}; ok={k for k,_ in host.components}
    if ek!=ok:
        return {'ready':False,'disposition':Disposition.HOLD_COMPONENT_SET_MOVED.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':['OBSERVED_COMPONENT_SET_DIFFERS']}
    if host.components!=capsule.expected_components:
        return {'ready':False,'disposition':Disposition.HOLD_COMPONENT_VALUE_MOVED.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':['OBSERVED_COMPONENT_VALUES_DIFFER']}
    byname={c.name:c for c in claims}
    if set(byname)!=set(capsule.required_proof_names):
        return {'ready':False,'disposition':Disposition.HOLD_PROOF_SET_INCOMPLETE.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':['REQUIRED_PROOF_SET_NOT_EXACT']}
    for n in capsule.required_proof_names:
        c=byname[n]
        if c.status!='PASS': return {'ready':False,'disposition':Disposition.HOLD_PROOF_FAILED.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':[f'{n}:NOT_PASS']}
        if c.executed_cases<=0 or c.skipped_required_cases!=0: return {'ready':False,'disposition':Disposition.HOLD_PROOF_VACUOUS.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':[f'{n}:VACUOUS_OR_SKIPPED']}
        if c.exact_head!=capsule.target_head: return {'ready':False,'disposition':Disposition.HOLD_PROOF_NOT_EXACT_HEAD.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':None,'reasons':[f'{n}:HEAD_MISMATCH']}
    prepare=_root({'capsule_root':capsule.capsule_root,'host_basis_root':host.basis_root,'claims':list(claim_roots),'o21_contract_root':capsule.o21_contract_root,'source_release_root':host.installed_release_root,'target_release_root':capsule.target_release_root})
    return {'ready':True,'disposition':Disposition.READY_O21_PREPARE.value,'capsule_root':capsule.capsule_root,'o21_prepare_root':prepare,'reasons':[]}

def operator_plan(capsule:DeploymentCapsule)->Tuple[str,...]:
    capsule.validate()
    return ('MEASURE_EXACT_HOST_BASIS','AUTHENTICATE_NONVACUOUS_EXACT_HEAD_PROOFS','O21_PREPARE','PERSIST_EXACT_BACKUP','STAGE_AND_HASH_EXACT_TARGET_BYTES','O21_COMMIT_ONCE','O20_POSTINSTALL_EXACT_MEASUREMENT','O19_STOP_WSL_AND_PROVE_8_EVENT_ACCEPTANCE','ACCEPT_OR_EXACT_ROLLBACK')
