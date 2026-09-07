from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import hmac, json
from tools.awj032.training_o1_reference.training_admission import Admission as O1Admission, SourceAuditVerifier, AIRLLM_COMMIT
SCHEMA='AURA-AWJ032-TRAINING-ADMISSION-RESOLVER-v5'; HEX=set('0123456789abcdef')
SUPPORTED={('qwen3_5','AirLLMLoRA'),('qwen3_8_dense','AirLLMLoRA'),('qwen4_exp','AirLLMLoRAQwen4Exp')}
def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def jhash(v): return sha256(canon(v)).hexdigest()
def isroot(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX
def needroot(x,n):
    if not isroot(x): raise ValueError(f'{n}: sha256 required')
def valid_int(x): return type(x) is int
def _validate_keyring(keys,active,generation,label):
    if not active or active not in keys or not valid_int(generation) or generation<1: raise ValueError(label)
    if not isinstance(keys[active],(bytes,bytearray)) or not keys[active]: raise ValueError(label)

@dataclass(frozen=True)
class AdmissionSemantic:
    o1_admission_root:str; source_root:str; adapter_root:str; runtime_root:str; target_topology_root:str
    base_checkpoint_root:str; base_config_root:str; tokenizer_root:str; adapter_values_root:str
    airllm_commit:str; model_family:str; trainer_class:str
    action:str='ADMIT_D0_ADAPTER_LOAD'; authority:str='D0_NONPROMOTING'; gate10:bool=False
    def __post_init__(self):
        for n in ('o1_admission_root','source_root','adapter_root','runtime_root','target_topology_root','base_checkpoint_root','base_config_root','tokenizer_root','adapter_values_root'): needroot(getattr(self,n),n)
        if self.airllm_commit!=AIRLLM_COMMIT or (self.model_family,self.trainer_class) not in SUPPORTED: raise ValueError('unsupported source/family')
        if self.action!='ADMIT_D0_ADAPTER_LOAD' or self.authority!='D0_NONPROMOTING' or self.gate10: raise ValueError('authority widening forbidden')
    @property
    def semantic_root(self): return jhash({'schema':SCHEMA,'kind':'semantic',**asdict(self)})

@dataclass(frozen=True)
class AdmissionReceipt:
    semantic:AdmissionSemantic; key_id:str; generation:int; issued_at:int; expires_at:int; mac:str
    def __post_init__(self):
        if not self.key_id or not valid_int(self.generation) or self.generation<1 or not valid_int(self.issued_at) or not valid_int(self.expires_at) or self.issued_at<0 or self.expires_at<=self.issued_at: raise ValueError('receipt metadata')
        needroot(self.mac,'mac')
    @property
    def signed_payload(self): return {'schema':SCHEMA,'kind':'admission_receipt','semantic_root':self.semantic.semantic_root,'key_id':self.key_id,'generation':self.generation,'issued_at':self.issued_at,'expires_at':self.expires_at}
    @property
    def receipt_root(self): return jhash({**self.signed_payload,'mac':self.mac})

@dataclass(frozen=True)
class TransitionPermit:
    transition_root:str; transition_subject_root:str; deployment_generation:str; admission_semantic_root:str; admission_receipt_root:str; o1_admission_root:str
    source_root:str; adapter_root:str; runtime_root:str; target_topology_root:str
    base_checkpoint_root:str; base_config_root:str; tokenizer_root:str; adapter_values_root:str; model_family:str; trainer_class:str
    key_id:str; generation:int; issued_at:int; expires_at:int; mac:str
    def __post_init__(self):
        for n in ('transition_root','transition_subject_root','admission_semantic_root','admission_receipt_root','o1_admission_root','source_root','adapter_root','runtime_root','target_topology_root','base_checkpoint_root','base_config_root','tokenizer_root','adapter_values_root','mac'): needroot(getattr(self,n),n)
        if not self.deployment_generation or not self.model_family or not self.trainer_class or not self.key_id: raise ValueError('permit identity')
        if not valid_int(self.generation) or self.generation<1 or not valid_int(self.issued_at) or not valid_int(self.expires_at) or self.issued_at<0 or self.expires_at<=self.issued_at: raise ValueError('permit validity interval')
    @property
    def signed_payload(self): return {'schema':SCHEMA,'kind':'transition_permit','transition_root':self.transition_root,'transition_subject_root':self.transition_subject_root,'deployment_generation':self.deployment_generation,'admission_semantic_root':self.admission_semantic_root,'admission_receipt_root':self.admission_receipt_root,'o1_admission_root':self.o1_admission_root,'source_root':self.source_root,'adapter_root':self.adapter_root,'runtime_root':self.runtime_root,'target_topology_root':self.target_topology_root,'base_checkpoint_root':self.base_checkpoint_root,'base_config_root':self.base_config_root,'tokenizer_root':self.tokenizer_root,'adapter_values_root':self.adapter_values_root,'model_family':self.model_family,'trainer_class':self.trainer_class,'key_id':self.key_id,'generation':self.generation,'issued_at':self.issued_at,'expires_at':self.expires_at}
    @property
    def permit_root(self): return jhash({**self.signed_payload,'mac':self.mac})

class OwnerResolver:
    def __init__(self,keys:dict[str,bytes],active_key_id:str,active_generation:int):
        _validate_keyring(keys,active_key_id,active_generation,'resolver config'); self._keys={k:bytes(v) for k,v in keys.items()}; self.active_key_id=active_key_id; self.active_generation=active_generation
    @staticmethod
    def _mac(key,payload): return hmac.new(key,canon(payload),sha256).hexdigest()
    def issue(self,semantic:AdmissionSemantic,*,o1_admission:O1Admission,source_verifier:SourceAuditVerifier,now:int,ttl:int):
        if not source_verifier.verify_admission(o1_admission): raise ValueError('O1 admission signature invalid')
        if o1_admission.action!='ADMIT_D0_ADAPTER_LOAD': raise ValueError('O1 outcome is not admission')
        if semantic.o1_admission_root!=o1_admission.admission_root: raise ValueError('O1 admission root mismatch')
        expected=(o1_admission.source_root,o1_admission.adapter_root,o1_admission.runtime_root,o1_admission.target_topology_root,o1_admission.base_checkpoint_root,o1_admission.base_config_root,o1_admission.tokenizer_root,o1_admission.adapter_values_root,o1_admission.model_family,o1_admission.trainer_class)
        got=(semantic.source_root,semantic.adapter_root,semantic.runtime_root,semantic.target_topology_root,semantic.base_checkpoint_root,semantic.base_config_root,semantic.tokenizer_root,semantic.adapter_values_root,semantic.model_family,semantic.trainer_class)
        if got!=expected: raise ValueError('O1 semantic/preimage mismatch')
        if not valid_int(now) or not valid_int(ttl) or now<0 or ttl<=0: raise ValueError('finite integer time required')
        p={'schema':SCHEMA,'kind':'admission_receipt','semantic_root':semantic.semantic_root,'key_id':self.active_key_id,'generation':self.active_generation,'issued_at':now,'expires_at':now+ttl}
        return AdmissionReceipt(semantic,self.active_key_id,self.active_generation,now,now+ttl,self._mac(self._keys[self.active_key_id],p))
    def verify(self,receipt:AdmissionReceipt,*,now:int,expected_source_root:str,expected_adapter_root:str,expected_runtime_root:str,expected_target_topology_root:str,expected_o1_admission_root:str|None=None):
        if not valid_int(now) or now<0: return 'HOLD_INVALID_TIME'
        if receipt.key_id!=self.active_key_id or receipt.key_id not in self._keys: return 'HOLD_KEY_CURRENTNESS'
        if receipt.generation!=self.active_generation: return 'HOLD_GENERATION_CURRENTNESS'
        if now<receipt.issued_at: return 'HOLD_NOT_YET_VALID'
        if now>=receipt.expires_at: return 'HOLD_EXPIRED'
        if not hmac.compare_digest(self._mac(self._keys[receipt.key_id],receipt.signed_payload),receipt.mac): return 'HOLD_BAD_SIGNATURE'
        s=receipt.semantic
        if expected_o1_admission_root is not None and s.o1_admission_root!=expected_o1_admission_root: return 'HOLD_O1_ADMISSION_MISMATCH'
        if s.source_root!=expected_source_root: return 'HOLD_SOURCE_MISMATCH'
        if s.adapter_root!=expected_adapter_root: return 'HOLD_ADAPTER_MISMATCH'
        if s.runtime_root!=expected_runtime_root: return 'HOLD_RUNTIME_MISMATCH'
        if s.target_topology_root!=expected_target_topology_root: return 'HOLD_TARGET_TOPOLOGY_MISMATCH'
        return 'VERIFIED_D0_ADMISSION'
    def issue_transition_permit(self,receipt:AdmissionReceipt,*,transition_root:str,transition_subject_root:str,deployment_generation:str,now:int,ttl:int,observed_source_root:str,observed_adapter_root:str,observed_runtime_root:str,observed_target_topology_root:str):
        needroot(transition_root,'transition_root'); needroot(transition_subject_root,'transition_subject_root')
        if not deployment_generation: raise ValueError('deployment generation required')
        verdict=self.verify(receipt,now=now,expected_source_root=observed_source_root,expected_adapter_root=observed_adapter_root,expected_runtime_root=observed_runtime_root,expected_target_topology_root=observed_target_topology_root)
        if verdict!='VERIFIED_D0_ADMISSION': raise ValueError('cannot issue transition permit: '+verdict)
        if not valid_int(ttl) or ttl<=0: raise ValueError('ttl')
        exp=min(now+ttl,receipt.expires_at)
        if exp<=now: raise ValueError('permit cannot outlive admission')
        s=receipt.semantic
        p={'schema':SCHEMA,'kind':'transition_permit','transition_root':transition_root,'transition_subject_root':transition_subject_root,'deployment_generation':deployment_generation,'admission_semantic_root':s.semantic_root,'admission_receipt_root':receipt.receipt_root,'o1_admission_root':s.o1_admission_root,'source_root':observed_source_root,'adapter_root':observed_adapter_root,'runtime_root':observed_runtime_root,'target_topology_root':observed_target_topology_root,'base_checkpoint_root':s.base_checkpoint_root,'base_config_root':s.base_config_root,'tokenizer_root':s.tokenizer_root,'adapter_values_root':s.adapter_values_root,'model_family':s.model_family,'trainer_class':s.trainer_class,'key_id':self.active_key_id,'generation':self.active_generation,'issued_at':now,'expires_at':exp}
        return TransitionPermit(transition_root,transition_subject_root,deployment_generation,s.semantic_root,receipt.receipt_root,s.o1_admission_root,observed_source_root,observed_adapter_root,observed_runtime_root,observed_target_topology_root,s.base_checkpoint_root,s.base_config_root,s.tokenizer_root,s.adapter_values_root,s.model_family,s.trainer_class,self.active_key_id,self.active_generation,now,exp,self._mac(self._keys[self.active_key_id],p))
    def verify_transition_permit(self,permit:TransitionPermit,*,now:int,expected_transition_root:str,expected_transition_subject_root:str,expected_deployment_generation:str,observed_source_root:str,observed_adapter_root:str,observed_runtime_root:str,observed_target_topology_root:str):
        if not valid_int(now) or now<0: return 'HOLD_INVALID_TIME'
        if permit.key_id!=self.active_key_id or permit.key_id not in self._keys: return 'HOLD_KEY_CURRENTNESS'
        if permit.generation!=self.active_generation: return 'HOLD_GENERATION_CURRENTNESS'
        if now<permit.issued_at: return 'HOLD_NOT_YET_VALID'
        if now>=permit.expires_at: return 'HOLD_EXPIRED'
        if not hmac.compare_digest(self._mac(self._keys[permit.key_id],permit.signed_payload),permit.mac): return 'HOLD_BAD_SIGNATURE'
        if permit.transition_root!=expected_transition_root: return 'HOLD_TRANSITION_CONTEXT'
        if permit.transition_subject_root!=expected_transition_subject_root: return 'HOLD_TRANSITION_SUBJECT'
        if permit.deployment_generation!=expected_deployment_generation: return 'HOLD_DEPLOYMENT_CONTEXT'
        if permit.source_root!=observed_source_root: return 'HOLD_SOURCE_MISMATCH'
        if permit.adapter_root!=observed_adapter_root: return 'HOLD_ADAPTER_MISMATCH'
        if permit.runtime_root!=observed_runtime_root: return 'HOLD_RUNTIME_MISMATCH'
        if permit.target_topology_root!=observed_target_topology_root: return 'HOLD_TARGET_TOPOLOGY_MISMATCH'
        return 'VERIFIED_D0_TRANSITION_PERMIT'

def omega8(s): return 'KEEPER' if len(s)==8 and all(v==2 for v in s) else 'HOLD'
def factored13d(s): return 'KEEPER' if len(s)==13 and all(v==2 for v in s) else 'HOLD'
