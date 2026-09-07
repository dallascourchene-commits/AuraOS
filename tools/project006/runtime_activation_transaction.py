from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib,hmac,json,sqlite3
from pathlib import Path

HEX=set('0123456789abcdef')
LOADED_SCHEMA='AURA-O20R-EFFECT-TIME-LOADED-PROCESS-CURRENTNESS-v1'
class ActivationError(ValueError): pass
class ActivationState(str,Enum):
    PREPARED='PREPARED'
    OLD_GENERATION_RETIRED='OLD_GENERATION_RETIRED'
    NEW_PROCESS_CURRENT='NEW_PROCESS_CURRENT'
    READY_FOR_O21_ACCEPTANCE='READY_FOR_O21_ACCEPTANCE'
    ACTIVATED='ACTIVATED'

def _hex64(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX
def _root(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),default=lambda x:x.value if isinstance(x,Enum) else x.__dict__).encode()).hexdigest()
def _mac(key,payload): return hmac.new(key,json.dumps(payload,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()

@dataclass(frozen=True)
class ActivationPlan:
    activation_id:str; deployment_capsule_root:str; o22_prepare_root:str; target_release_root:str; expected_host_id:str; prior_process_binding_root:str; prior_serving_population_root:str
    def validate(self):
        if not self.activation_id or not self.expected_host_id: raise ActivationError('PLAN_IDENTITY_INVALID')
        for x in (self.deployment_capsule_root,self.o22_prepare_root,self.target_release_root,self.prior_process_binding_root,self.prior_serving_population_root):
            if not _hex64(x): raise ActivationError('PLAN_ROOT_INVALID')
    @property
    def plan_root(self): self.validate(); return _root(self)

@dataclass(frozen=True)
class RetirementEvidence:
    plan_root:str; host_id:str; retired_process_binding_root:str; retired_population_root:str; remaining_old_workers:int; observed_at_ms:int; valid_until_ms:int; verifier_id:str; observer_id:str; mac_hex:str
    def unsigned(self): return {'plan_root':self.plan_root,'host_id':self.host_id,'retired_process_binding_root':self.retired_process_binding_root,'retired_population_root':self.retired_population_root,'remaining_old_workers':self.remaining_old_workers,'observed_at_ms':self.observed_at_ms,'valid_until_ms':self.valid_until_ms,'verifier_id':self.verifier_id,'observer_id':self.observer_id}
    def validate(self):
        for x in (self.plan_root,self.retired_process_binding_root,self.retired_population_root,self.mac_hex):
            if not _hex64(x): raise ActivationError('RETIREMENT_ROOT_INVALID')
        if not self.host_id or not self.verifier_id or not self.observer_id or self.verifier_id==self.observer_id: raise ActivationError('RETIREMENT_ACTOR_INVALID')
        if not isinstance(self.remaining_old_workers,int) or self.remaining_old_workers<0: raise ActivationError('RETIREMENT_COUNT_INVALID')
        if min(self.observed_at_ms,self.valid_until_ms)<0 or self.valid_until_ms<self.observed_at_ms: raise ActivationError('RETIREMENT_TIME_INVALID')

def sign_retirement(key:bytes,plan:ActivationPlan,*,remaining_old_workers=0,observed_at_ms=1000,valid_until_ms=2000,verifier_id='retire-verifier',observer_id='retire-observer'):
    p={'plan_root':plan.plan_root,'host_id':plan.expected_host_id,'retired_process_binding_root':plan.prior_process_binding_root,'retired_population_root':plan.prior_serving_population_root,'remaining_old_workers':remaining_old_workers,'observed_at_ms':observed_at_ms,'valid_until_ms':valid_until_ms,'verifier_id':verifier_id,'observer_id':observer_id}
    return RetirementEvidence(**p,mac_hex=_mac(key,p))

@dataclass(frozen=True)
class LoadedProcessAdmission:
    schema:str; plan_root:str; host_id:str; installed_runtime_root:str; disposition:str; process_binding_root:str; effect_time_witness_root:str; process_generation:int; load_generation:int; serving_population_root:str; selected_worker_id:str; observed_at_ms:int; valid_until_ms:int; verifier_id:str; observer_id:str; mac_hex:str
    def unsigned(self): return {'schema':self.schema,'plan_root':self.plan_root,'host_id':self.host_id,'installed_runtime_root':self.installed_runtime_root,'disposition':self.disposition,'process_binding_root':self.process_binding_root,'effect_time_witness_root':self.effect_time_witness_root,'process_generation':self.process_generation,'load_generation':self.load_generation,'serving_population_root':self.serving_population_root,'selected_worker_id':self.selected_worker_id,'observed_at_ms':self.observed_at_ms,'valid_until_ms':self.valid_until_ms,'verifier_id':self.verifier_id,'observer_id':self.observer_id}
    def validate(self):
        if self.schema!=LOADED_SCHEMA: raise ActivationError('LOADED_SCHEMA_INVALID')
        for x in (self.plan_root,self.installed_runtime_root,self.process_binding_root,self.effect_time_witness_root,self.serving_population_root,self.mac_hex):
            if not _hex64(x): raise ActivationError('LOADED_ROOT_INVALID')
        if not self.host_id or not self.selected_worker_id or not self.verifier_id or not self.observer_id or self.verifier_id==self.observer_id: raise ActivationError('LOADED_ACTOR_INVALID')
        if not isinstance(self.process_generation,int) or self.process_generation<0 or not isinstance(self.load_generation,int) or self.load_generation<0: raise ActivationError('LOADED_GENERATION_INVALID')
        if min(self.observed_at_ms,self.valid_until_ms)<0 or self.valid_until_ms<self.observed_at_ms: raise ActivationError('LOADED_TIME_INVALID')

def sign_loaded(key:bytes,plan:ActivationPlan,*,process_binding_root:str,effect_time_witness_root:str,serving_population_root:str,selected_worker_id='worker-new',process_generation=2,load_generation=1,disposition='ADMIT_EFFECT_TIME_PROCESS_D0',observed_at_ms=1100,valid_until_ms=2000,verifier_id='process-verifier',observer_id='process-observer'):
    p={'schema':LOADED_SCHEMA,'plan_root':plan.plan_root,'host_id':plan.expected_host_id,'installed_runtime_root':plan.target_release_root,'disposition':disposition,'process_binding_root':process_binding_root,'effect_time_witness_root':effect_time_witness_root,'process_generation':process_generation,'load_generation':load_generation,'serving_population_root':serving_population_root,'selected_worker_id':selected_worker_id,'observed_at_ms':observed_at_ms,'valid_until_ms':valid_until_ms,'verifier_id':verifier_id,'observer_id':observer_id}
    return LoadedProcessAdmission(**p,mac_hex=_mac(key,p))

@dataclass(frozen=True)
class PostInstallProofSet:
    plan_root:str; o20_receipt_root:str; o19_receipt_root:str; o20_current_exact:bool; o19_physical_wake_accepted:bool; loaded_process_receipt_root:str; verifier_id:str; observer_id:str; issued_at_ms:int; expires_at_ms:int; mac_hex:str
    def unsigned(self): return {'plan_root':self.plan_root,'o20_receipt_root':self.o20_receipt_root,'o19_receipt_root':self.o19_receipt_root,'o20_current_exact':self.o20_current_exact,'o19_physical_wake_accepted':self.o19_physical_wake_accepted,'loaded_process_receipt_root':self.loaded_process_receipt_root,'verifier_id':self.verifier_id,'observer_id':self.observer_id,'issued_at_ms':self.issued_at_ms,'expires_at_ms':self.expires_at_ms}
    def validate(self):
        for x in (self.plan_root,self.o20_receipt_root,self.o19_receipt_root,self.loaded_process_receipt_root,self.mac_hex):
            if not _hex64(x): raise ActivationError('POSTINSTALL_ROOT_INVALID')
        if not self.verifier_id or not self.observer_id or self.verifier_id==self.observer_id: raise ActivationError('POSTINSTALL_ACTOR_INVALID')
        if min(self.issued_at_ms,self.expires_at_ms)<0 or self.expires_at_ms<self.issued_at_ms: raise ActivationError('POSTINSTALL_TIME_INVALID')

def sign_postinstall(key:bytes,plan:ActivationPlan,loaded:LoadedProcessAdmission,*,o20_receipt_root:str,o19_receipt_root:str,o20_current_exact=True,o19_physical_wake_accepted=True,issued_at_ms=1200,expires_at_ms=2000,verifier_id='post-verifier',observer_id='post-observer'):
    p={'plan_root':plan.plan_root,'o20_receipt_root':o20_receipt_root,'o19_receipt_root':o19_receipt_root,'o20_current_exact':bool(o20_current_exact),'o19_physical_wake_accepted':bool(o19_physical_wake_accepted),'loaded_process_receipt_root':_root(loaded.unsigned()),'verifier_id':verifier_id,'observer_id':observer_id,'issued_at_ms':issued_at_ms,'expires_at_ms':expires_at_ms}
    return PostInstallProofSet(**p,mac_hex=_mac(key,p))

class ActivationJournal:
    def __init__(self,path:str):
        self.path=path; Path(path).parent.mkdir(parents=True,exist_ok=True)
        c=sqlite3.connect(path)
        try:
            c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL')
            c.execute('CREATE TABLE IF NOT EXISTS act(activation_id TEXT PRIMARY KEY,state TEXT NOT NULL,plan_root TEXT NOT NULL,target_release_root TEXT NOT NULL,o21_commit_receipt_root TEXT NOT NULL,retirement_root TEXT,loaded_root TEXT,postinstall_root TEXT,activation_receipt_root TEXT,last_receipt_root TEXT NOT NULL)')
            c.commit()
        finally:c.close()
    def _read(self,aid):
        c=sqlite3.connect(self.path)
        try:return c.execute('SELECT state,plan_root,target_release_root,o21_commit_receipt_root,retirement_root,loaded_root,postinstall_root,activation_receipt_root,last_receipt_root FROM act WHERE activation_id=?',(aid,)).fetchone()
        finally:c.close()
    def status(self,aid):
        row=self._read(aid)
        if not row:return None
        return {'activation_id':aid,'state':row[0],'plan_root':row[1],'target_release_root':row[2],'o21_commit_receipt_root':row[3],'retirement_root':row[4],'loaded_root':row[5],'postinstall_root':row[6],'activation_receipt_root':row[7],'last_receipt_root':row[8],'effect_authority':False,'gate10':False}
    def prepare(self,plan:ActivationPlan,*,o21_state:str,o21_target_release_root:str,o21_commit_receipt_root:str):
        plan.validate()
        if o21_state!='COMMITTED': raise ActivationError('O21_NOT_COMMITTED')
        if o21_target_release_root!=plan.target_release_root or not _hex64(o21_commit_receipt_root): raise ActivationError('O21_COMMIT_BINDING_MISMATCH')
        row=self._read(plan.activation_id)
        if row:
            if row[1]!=plan.plan_root or row[2]!=plan.target_release_root or row[3]!=o21_commit_receipt_root: raise ActivationError('ACTIVATION_IDENTITY_CONFLICT')
            return self.status(plan.activation_id)
        rr=_root({'activation_id':plan.activation_id,'state':ActivationState.PREPARED.value,'plan_root':plan.plan_root,'o21_commit_receipt_root':o21_commit_receipt_root})
        c=sqlite3.connect(self.path)
        try:c.execute('INSERT INTO act VALUES(?,?,?,?,?,?,?,?,?,?)',(plan.activation_id,ActivationState.PREPARED.value,plan.plan_root,plan.target_release_root,o21_commit_receipt_root,None,None,None,None,rr));c.commit()
        finally:c.close()
        return self.status(plan.activation_id)
    def retire_old(self,plan:ActivationPlan,e:RetirementEvidence,*,key:bytes,now_ms:int):
        row=self._read(plan.activation_id)
        if not row or row[0]!=ActivationState.PREPARED.value: raise ActivationError('RETIREMENT_STATE_INVALID')
        e.validate()
        if not hmac.compare_digest(_mac(key,e.unsigned()),e.mac_hex): raise ActivationError('RETIREMENT_UNAUTHENTICATED')
        if e.plan_root!=plan.plan_root or e.host_id!=plan.expected_host_id or e.retired_process_binding_root!=plan.prior_process_binding_root or e.retired_population_root!=plan.prior_serving_population_root: raise ActivationError('RETIREMENT_BINDING_MISMATCH')
        if now_ms<e.observed_at_ms or now_ms>e.valid_until_ms: raise ActivationError('RETIREMENT_STALE')
        if e.remaining_old_workers!=0: raise ActivationError('OLD_SERVING_GENERATION_REMAINS')
        er=_root(e.unsigned()); rr=_root({'activation_id':plan.activation_id,'state':ActivationState.OLD_GENERATION_RETIRED.value,'retirement_root':er})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE act SET state=?,retirement_root=?,last_receipt_root=? WHERE activation_id=?',(ActivationState.OLD_GENERATION_RETIRED.value,er,rr,plan.activation_id));c.commit()
        finally:c.close()
        return self.status(plan.activation_id)
    def bind_loaded(self,plan:ActivationPlan,e:LoadedProcessAdmission,*,key:bytes,now_ms:int):
        row=self._read(plan.activation_id)
        if not row or row[0]!=ActivationState.OLD_GENERATION_RETIRED.value: raise ActivationError('LOADED_STATE_INVALID')
        e.validate()
        if not hmac.compare_digest(_mac(key,e.unsigned()),e.mac_hex): raise ActivationError('LOADED_ADMISSION_UNAUTHENTICATED')
        if e.plan_root!=plan.plan_root or e.host_id!=plan.expected_host_id or e.installed_runtime_root!=plan.target_release_root: raise ActivationError('LOADED_BINDING_MISMATCH')
        if e.disposition!='ADMIT_EFFECT_TIME_PROCESS_D0': raise ActivationError('LOADED_PROCESS_NOT_CURRENT')
        if now_ms<e.observed_at_ms or now_ms>e.valid_until_ms: raise ActivationError('LOADED_ADMISSION_STALE')
        if e.process_binding_root==plan.prior_process_binding_root or e.serving_population_root==plan.prior_serving_population_root: raise ActivationError('OLD_GENERATION_ALIAS')
        lr=_root(e.unsigned()); rr=_root({'activation_id':plan.activation_id,'state':ActivationState.NEW_PROCESS_CURRENT.value,'loaded_root':lr})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE act SET state=?,loaded_root=?,last_receipt_root=? WHERE activation_id=?',(ActivationState.NEW_PROCESS_CURRENT.value,lr,rr,plan.activation_id));c.commit()
        finally:c.close()
        return self.status(plan.activation_id)
    def bind_postinstall(self,plan:ActivationPlan,p:PostInstallProofSet,loaded:LoadedProcessAdmission,*,key:bytes,now_ms:int):
        row=self._read(plan.activation_id)
        if not row or row[0]!=ActivationState.NEW_PROCESS_CURRENT.value: raise ActivationError('POSTINSTALL_STATE_INVALID')
        p.validate()
        if not hmac.compare_digest(_mac(key,p.unsigned()),p.mac_hex): raise ActivationError('POSTINSTALL_UNAUTHENTICATED')
        lr=_root(loaded.unsigned())
        if p.plan_root!=plan.plan_root or p.loaded_process_receipt_root!=lr or row[5]!=lr: raise ActivationError('POSTINSTALL_LOADED_BINDING_MISMATCH')
        if now_ms<p.issued_at_ms or now_ms>p.expires_at_ms: raise ActivationError('POSTINSTALL_STALE')
        if not p.o20_current_exact or not p.o19_physical_wake_accepted: raise ActivationError('POSTINSTALL_OWNER_PROOF_NOT_ACCEPTED')
        pr=_root(p.unsigned()); rr=_root({'activation_id':plan.activation_id,'state':ActivationState.READY_FOR_O21_ACCEPTANCE.value,'postinstall_root':pr,'loaded_root':lr})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE act SET state=?,postinstall_root=?,last_receipt_root=? WHERE activation_id=?',(ActivationState.READY_FOR_O21_ACCEPTANCE.value,pr,rr,plan.activation_id));c.commit()
        finally:c.close()
        return self.status(plan.activation_id)
    def mark_activated(self,plan:ActivationPlan,*,o21_state:str,o21_acceptance_receipt_root:str):
        row=self._read(plan.activation_id)
        if not row or row[0]!=ActivationState.READY_FOR_O21_ACCEPTANCE.value: raise ActivationError('ACTIVATE_STATE_INVALID')
        if o21_state!='ACCEPTED' or not _hex64(o21_acceptance_receipt_root): raise ActivationError('O21_ACCEPTANCE_NOT_PROVEN')
        ar=_root({'activation_id':plan.activation_id,'plan_root':plan.plan_root,'o21_acceptance_receipt_root':o21_acceptance_receipt_root,'loaded_root':row[5],'postinstall_root':row[6]})
        rr=_root({'activation_id':plan.activation_id,'state':ActivationState.ACTIVATED.value,'activation_receipt_root':ar})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE act SET state=?,activation_receipt_root=?,last_receipt_root=? WHERE activation_id=?',(ActivationState.ACTIVATED.value,ar,rr,plan.activation_id));c.commit()
        finally:c.close()
        return self.status(plan.activation_id)
