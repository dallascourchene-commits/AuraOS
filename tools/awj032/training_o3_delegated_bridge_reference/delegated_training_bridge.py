from __future__ import annotations
from dataclasses import dataclass,asdict
from hashlib import sha256
import hmac,json
from tools.awj032.training_r1_resolver_reference.training_admission_resolver import AdmissionReceipt,OwnerResolver,AIRLLM_COMMIT
SCHEMA='AURA-AWJ032-DELEGATED-TRAINING-BRIDGE-v2'; HEX=set('0123456789abcdef')
SUPPORTED={('qwen3_5','AirLLMLoRA'),('qwen3_8_dense','AirLLMLoRA'),('qwen4_exp','AirLLMLoRAQwen4Exp')}
PROHIBITED_DELEGATE_FIELDS={'bootstrap_path','filesystem_path','credential','credentials','secret','token','host_private_key','runtime_package_path','currentness_internals','k27_authority'}
def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def jhash(v): return sha256(canon(v)).hexdigest()
def isroot(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX
def needroot(x,n):
    if not isroot(x): raise ValueError(f'{n}: sha256 required')
def valid_int(x): return type(x) is int
def _valid_keyring(keys,active,generation): return bool(active and active in keys and valid_int(generation) and generation>=1 and isinstance(keys[active],(bytes,bytearray)) and keys[active])
@dataclass(frozen=True)
class TrainingOperation:
    mission_root:str; source_identity_root:str; intent_root:str; contract_root:str; payload_root:str; base_checkpoint_root:str; base_config_root:str; tokenizer_root:str; runtime_root:str; adapter_spec_root:str; target_topology_root:str; airllm_commit:str; model_family:str; trainer_class:str
    def __post_init__(self):
        for n in ('mission_root','source_identity_root','intent_root','contract_root','payload_root','base_checkpoint_root','base_config_root','tokenizer_root','runtime_root','adapter_spec_root','target_topology_root'): needroot(getattr(self,n),n)
        if self.airllm_commit!=AIRLLM_COMMIT or (self.model_family,self.trainer_class) not in SUPPORTED: raise ValueError('unsupported training source/family')
    @property
    def operation_root(self): return jhash({'schema':SCHEMA,'kind':'training_operation',**asdict(self)})
def capsule_subject_root(*,operation_root,opaque_work_handle,source_identity_root,adapter_spec_root,admission_semantic_root,admission_receipt_root,test_plan_root,worker_class,max_steps):
    for n,v in [('operation_root',operation_root),('source_identity_root',source_identity_root),('adapter_spec_root',adapter_spec_root),('admission_semantic_root',admission_semantic_root),('admission_receipt_root',admission_receipt_root),('test_plan_root',test_plan_root)]: needroot(v,n)
    if not opaque_work_handle or len(opaque_work_handle)>96 or worker_class not in {'non_sol_worker','isolated_training_worker'} or not valid_int(max_steps) or not 1<=max_steps<=100000: raise ValueError('capsule subject')
    return jhash({'schema':SCHEMA,'kind':'delegated_capsule_subject','operation_root':operation_root,'opaque_work_handle':opaque_work_handle,'source_identity_root':source_identity_root,'adapter_spec_root':adapter_spec_root,'admission_semantic_root':admission_semantic_root,'admission_receipt_root':admission_receipt_root,'test_plan_root':test_plan_root,'worker_class':worker_class,'max_steps':max_steps})
@dataclass(frozen=True)
class WorkcellLease:
    operation_root:str; capsule_subject_root:str; admission_semantic_root:str; admission_receipt_root:str; host_generation:int; issued_at:int; expires_at:int; key_id:str; mac:str
    def __post_init__(self):
        for n in ('operation_root','capsule_subject_root','admission_semantic_root','admission_receipt_root','mac'): needroot(getattr(self,n),n)
        if not valid_int(self.host_generation) or self.host_generation<1 or not valid_int(self.issued_at) or not valid_int(self.expires_at) or self.issued_at<0 or self.expires_at<=self.issued_at or not self.key_id: raise ValueError('invalid workcell lease')
    @property
    def signed_payload(self): return {'schema':SCHEMA,'kind':'workcell_lease','operation_root':self.operation_root,'capsule_subject_root':self.capsule_subject_root,'admission_semantic_root':self.admission_semantic_root,'admission_receipt_root':self.admission_receipt_root,'host_generation':self.host_generation,'issued_at':self.issued_at,'expires_at':self.expires_at,'key_id':self.key_id}
    @property
    def lease_root(self): return jhash({**self.signed_payload,'mac':self.mac})
class HostWorkcellAuthority:
    def __init__(self,keys,active_key_id,generation):
        if not _valid_keyring(keys,active_key_id,generation): raise ValueError('invalid host authority')
        self.keys={k:bytes(v) for k,v in keys.items()}; self.active_key_id=active_key_id; self.generation=generation
    @staticmethod
    def _mac(key,p): return hmac.new(key,canon(p),sha256).hexdigest()
    def issue(self,*,operation_root,capsule_subject_root,admission_semantic_root,admission_receipt_root,now,ttl):
        if not valid_int(now) or now<0 or not valid_int(ttl) or ttl<=0: raise ValueError('finite integer lease time required')
        p={'schema':SCHEMA,'kind':'workcell_lease','operation_root':operation_root,'capsule_subject_root':capsule_subject_root,'admission_semantic_root':admission_semantic_root,'admission_receipt_root':admission_receipt_root,'host_generation':self.generation,'issued_at':now,'expires_at':now+ttl,'key_id':self.active_key_id}
        return WorkcellLease(operation_root,capsule_subject_root,admission_semantic_root,admission_receipt_root,self.generation,now,now+ttl,self.active_key_id,self._mac(self.keys[self.active_key_id],p))
    def verify(self,lease,*,now,expected_operation_root,expected_capsule_subject_root,expected_admission_semantic_root,expected_admission_receipt_root):
        if not valid_int(now) or now<0: return 'HOLD_WORKCELL_INVALID_TIME'
        if lease.key_id!=self.active_key_id or lease.key_id not in self.keys: return 'HOLD_WORKCELL_KEY'
        if lease.host_generation!=self.generation: return 'HOLD_WORKCELL_GENERATION'
        if now<lease.issued_at: return 'HOLD_WORKCELL_NOT_YET_VALID'
        if now>=lease.expires_at: return 'HOLD_WORKCELL_EXPIRED'
        if not hmac.compare_digest(self._mac(self.keys[lease.key_id],lease.signed_payload),lease.mac): return 'HOLD_WORKCELL_SIGNATURE'
        if (lease.operation_root,lease.capsule_subject_root,lease.admission_semantic_root,lease.admission_receipt_root)!=(expected_operation_root,expected_capsule_subject_root,expected_admission_semantic_root,expected_admission_receipt_root): return 'HOLD_WORKCELL_BINDING'
        return 'VERIFIED_D0_WORKCELL'
@dataclass(frozen=True)
class DelegatedTrainingCapsule:
    operation_root:str; opaque_work_handle:str; source_identity_root:str; adapter_spec_root:str; admission_semantic_root:str; admission_receipt_root:str; workcell_lease_root:str; test_plan_root:str; worker_class:str; max_steps:int
    def __post_init__(self):
        for n in ('operation_root','source_identity_root','adapter_spec_root','admission_semantic_root','admission_receipt_root','workcell_lease_root','test_plan_root'): needroot(getattr(self,n),n)
        capsule_subject_root(operation_root=self.operation_root,opaque_work_handle=self.opaque_work_handle,source_identity_root=self.source_identity_root,adapter_spec_root=self.adapter_spec_root,admission_semantic_root=self.admission_semantic_root,admission_receipt_root=self.admission_receipt_root,test_plan_root=self.test_plan_root,worker_class=self.worker_class,max_steps=self.max_steps)
    @property
    def subject_root(self): return capsule_subject_root(operation_root=self.operation_root,opaque_work_handle=self.opaque_work_handle,source_identity_root=self.source_identity_root,adapter_spec_root=self.adapter_spec_root,admission_semantic_root=self.admission_semantic_root,admission_receipt_root=self.admission_receipt_root,test_plan_root=self.test_plan_root,worker_class=self.worker_class,max_steps=self.max_steps)
    @property
    def capsule_root(self): return jhash({'schema':SCHEMA,'kind':'delegated_capsule',**asdict(self)})
    def public_payload(self): return asdict(self)
@dataclass(frozen=True)
class DurableTrainingAttempt:
    operation_root:str; capsule_root:str; attempt_id:str; idempotency_key:str; recovery_policy_root:str
    def __post_init__(self):
        for n in ('operation_root','capsule_root','attempt_id','idempotency_key','recovery_policy_root'): needroot(getattr(self,n),n)
    @property
    def attempt_root(self): return jhash({'schema':SCHEMA,'kind':'attempt',**asdict(self)})
@dataclass(frozen=True)
class WorkerProposal:
    capsule_root:str; attempt_root:str; proposal_adapter_root:str; metrics_root:str; test_receipt_root:str; worker_class:str; output_digest:str; authority:str='PROPOSAL_ONLY'
    def __post_init__(self):
        for n in ('capsule_root','attempt_root','proposal_adapter_root','metrics_root','test_receipt_root','output_digest'): needroot(getattr(self,n),n)
        if self.worker_class not in {'non_sol_worker','isolated_training_worker'} or self.authority!='PROPOSAL_ONLY': raise ValueError('worker authority')
@dataclass(frozen=True)
class RecoveryVerdict:
    attempt_root:str; verdict:str; key_id:str; generation:int; issued_at:int; mac:str
    def __post_init__(self):
        needroot(self.attempt_root,'attempt_root'); needroot(self.mac,'mac')
        if self.verdict not in {'NOT_STARTED','UNKNOWN','COMPLETED'} or not self.key_id or not valid_int(self.generation) or self.generation<1 or not valid_int(self.issued_at) or self.issued_at<0: raise ValueError('recovery metadata')
    @property
    def signed_payload(self): return {'schema':SCHEMA,'kind':'recovery_verdict','attempt_root':self.attempt_root,'verdict':self.verdict,'key_id':self.key_id,'generation':self.generation,'issued_at':self.issued_at}
    @property
    def verdict_root(self): return jhash({**self.signed_payload,'mac':self.mac})
class RecoveryAuthority:
    def __init__(self,keys,active_key_id,generation):
        if not _valid_keyring(keys,active_key_id,generation): raise ValueError('recovery authority')
        self.keys={k:bytes(v) for k,v in keys.items()}; self.active_key_id=active_key_id; self.generation=generation; self._current={}
    def issue(self,attempt_root,verdict,now):
        if not valid_int(now) or now<0: raise ValueError('recovery time')
        prev=self._current.get(attempt_root)
        if prev is not None:
            if now<=prev.issued_at: raise ValueError('recovery verdict time must increase monotonically')
            if prev.verdict=='COMPLETED' and verdict!='COMPLETED': raise ValueError('completed recovery verdict is terminal')
        p={'schema':SCHEMA,'kind':'recovery_verdict','attempt_root':attempt_root,'verdict':verdict,'key_id':self.active_key_id,'generation':self.generation,'issued_at':now}
        v=RecoveryVerdict(attempt_root,verdict,self.active_key_id,self.generation,now,hmac.new(self.keys[self.active_key_id],canon(p),sha256).hexdigest()); self._current[attempt_root]=v; return v
    def verify(self,v,expected_attempt_root,current_required=False):
        if v.key_id!=self.active_key_id or v.key_id not in self.keys: return 'HOLD_RECOVERY_KEY'
        if v.generation!=self.generation: return 'HOLD_RECOVERY_GENERATION'
        if v.attempt_root!=expected_attempt_root: return 'HOLD_RECOVERY_ATTEMPT'
        if not hmac.compare_digest(hmac.new(self.keys[v.key_id],canon(v.signed_payload),sha256).hexdigest(),v.mac): return 'HOLD_RECOVERY_SIGNATURE'
        if current_required:
            cur=self._current.get(expected_attempt_root)
            if cur is None or cur.verdict_root!=v.verdict_root: return 'HOLD_RECOVERY_SUPERSEDED'
        return 'VERIFIED_RECOVERY'
def validate_delegate_payload(c): return not bool(set(c.public_payload())&PROHIBITED_DELEGATE_FIELDS)
def admit_delegation(*,operation,admission_receipt,admission_resolver,lease,workcell_authority,capsule,now):
    if operation.operation_root!=capsule.operation_root: return 'HOLD_OPERATION_BINDING'
    if operation.source_identity_root!=capsule.source_identity_root: return 'HOLD_SOURCE_IDENTITY'
    if operation.adapter_spec_root!=capsule.adapter_spec_root: return 'HOLD_ADAPTER_SPEC'
    if capsule.admission_semantic_root!=admission_receipt.semantic.semantic_root: return 'HOLD_ADMISSION_SEMANTIC'
    if capsule.admission_receipt_root!=admission_receipt.receipt_root: return 'HOLD_ADMISSION_RECEIPT'
    if capsule.workcell_lease_root!=lease.lease_root: return 'HOLD_WORKCELL_LEASE_ROOT'
    if not validate_delegate_payload(capsule): return 'HOLD_PRIVATE_FIELD_LEAK'
    a=admission_resolver.verify(admission_receipt,now=now,expected_source_root=operation.source_identity_root,expected_adapter_root=operation.adapter_spec_root,expected_runtime_root=operation.runtime_root,expected_target_topology_root=operation.target_topology_root)
    if a!='VERIFIED_D0_ADMISSION': return 'HOLD_ADMISSION_CURRENTNESS:'+a
    w=workcell_authority.verify(lease,now=now,expected_operation_root=operation.operation_root,expected_capsule_subject_root=capsule.subject_root,expected_admission_semantic_root=admission_receipt.semantic.semantic_root,expected_admission_receipt_root=admission_receipt.receipt_root)
    if w!='VERIFIED_D0_WORKCELL': return 'HOLD_WORKCELL_CURRENTNESS:'+w
    return 'ADMIT_D0_DELEGATED_TRAINING_PROPOSAL_ONLY'
def validate_worker_proposal(*,operation,admission_receipt,admission_resolver,lease,workcell_authority,capsule,attempt,proposal,now):
    pre=admit_delegation(operation=operation,admission_receipt=admission_receipt,admission_resolver=admission_resolver,lease=lease,workcell_authority=workcell_authority,capsule=capsule,now=now)
    if pre!='ADMIT_D0_DELEGATED_TRAINING_PROPOSAL_ONLY': return pre
    if attempt.operation_root!=operation.operation_root or attempt.capsule_root!=capsule.capsule_root: return 'HOLD_DURABLE_ATTEMPT_BINDING'
    if proposal.capsule_root!=capsule.capsule_root: return 'HOLD_PROPOSAL_CAPSULE'
    if proposal.attempt_root!=attempt.attempt_root: return 'HOLD_PROPOSAL_ATTEMPT'
    if proposal.worker_class!=capsule.worker_class: return 'HOLD_PROPOSAL_WORKER_CLASS'
    if proposal.authority!='PROPOSAL_ONLY': return 'HOLD_WORKER_AUTHORITY'
    return 'ADMIT_D0_ADAPTER_PROPOSAL_FOR_HOST_REVIEW'
def retry_decision(attempt,verdict,authority):
    v=authority.verify(verdict,attempt.attempt_root,current_required=True)
    if v!='VERIFIED_RECOVERY': return v
    if verdict.verdict=='NOT_STARTED': return 'RETRY_CANDIDATE_D0'
    if verdict.verdict=='UNKNOWN': return 'HOLD_RECONCILE_UNKNOWN'
    return 'RETURN_ONLY_COMPLETED'
def semantic_operation_reopen(old,new): return 'PRESERVE_OPERATION' if old.operation_root==new.operation_root else 'NEW_SEMANTIC_OPERATION'
def minimum_reopen_cone(changed_root,capsules): return tuple(i for i,c in enumerate(capsules) if changed_root in {c.operation_root,c.source_identity_root,c.adapter_spec_root,c.admission_semantic_root,c.admission_receipt_root,c.workcell_lease_root,c.test_plan_root})
def omega8(state):
    if len(state)!=8 or any(v not in (0,1,2) for v in state): raise ValueError
    return 'KEEPER' if all(v==2 for v in state) else 'HOLD'
def factored13d(state):
    if len(state)!=13 or any(v not in (0,1,2) for v in state): raise ValueError
    return 'KEEPER' if all(v==2 for v in state) else 'HOLD'
