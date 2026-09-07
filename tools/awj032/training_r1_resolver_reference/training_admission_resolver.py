from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import hmac, json

SCHEMA='AURA-AWJ032-TRAINING-ADMISSION-RESOLVER-v1'
AIRLLM_COMMIT='55e435087d951da8c25ab3672e969025241a398e'
HEX=set('0123456789abcdef')
SUPPORTED={('qwen3_5','AirLLMLoRA'),('qwen3_8','AirLLMLoRA'),('qwen4_exp','AirLLMLoRAQwen4Exp')}

def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def jhash(v): return sha256(canon(v)).hexdigest()
def isroot(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX

def needroot(x,name):
    if not isroot(x): raise ValueError(f'{name}: sha256 required')
    return x

@dataclass(frozen=True)
class AdmissionSemantic:
    source_root:str
    adapter_root:str
    runtime_root:str
    target_topology_root:str
    airllm_commit:str
    model_family:str
    trainer_class:str
    action:str='ADMIT_D0_ADAPTER_LOAD'
    authority:str='D0_NONPROMOTING'
    gate10:bool=False
    def __post_init__(self):
        for n in ('source_root','adapter_root','runtime_root','target_topology_root'):
            needroot(getattr(self,n),n)
        if self.airllm_commit != AIRLLM_COMMIT: raise ValueError('AirLLM generation drift')
        if (self.model_family,self.trainer_class) not in SUPPORTED: raise ValueError('unsupported family/trainer')
        if self.action!='ADMIT_D0_ADAPTER_LOAD' or self.authority!='D0_NONPROMOTING' or self.gate10:
            raise ValueError('authority widening forbidden')
    @property
    def semantic_root(self): return jhash({'schema':SCHEMA,'kind':'semantic',**asdict(self)})

@dataclass(frozen=True)
class AdmissionReceipt:
    semantic:AdmissionSemantic
    key_id:str
    generation:int
    issued_at:int
    expires_at:int
    mac:str
    def __post_init__(self):
        if not self.key_id: raise ValueError('key_id required')
        if self.generation < 1: raise ValueError('generation must be positive')
        if self.issued_at < 0 or self.expires_at <= self.issued_at: raise ValueError('bad validity interval')
        if not isroot(self.mac): raise ValueError('mac must be sha256 hex')
    @property
    def signed_payload(self):
        return {'schema':SCHEMA,'kind':'receipt','semantic_root':self.semantic.semantic_root,'key_id':self.key_id,
                'generation':self.generation,'issued_at':self.issued_at,'expires_at':self.expires_at}
    @property
    def receipt_root(self): return jhash({**self.signed_payload,'mac':self.mac})

class OwnerResolver:
    def __init__(self, keys:dict[str,bytes], active_key_id:str, active_generation:int):
        if active_key_id not in keys: raise ValueError('active key missing')
        if active_generation < 1: raise ValueError('active generation')
        self._keys=dict(keys); self.active_key_id=active_key_id; self.active_generation=active_generation
    @staticmethod
    def _mac(key:bytes,payload:dict): return hmac.new(key,canon(payload),sha256).hexdigest()
    def issue(self, semantic:AdmissionSemantic, *, now:int, ttl:int) -> AdmissionReceipt:
        if ttl <= 0: raise ValueError('ttl must be positive')
        payload={'schema':SCHEMA,'kind':'receipt','semantic_root':semantic.semantic_root,'key_id':self.active_key_id,
                 'generation':self.active_generation,'issued_at':now,'expires_at':now+ttl}
        mac=self._mac(self._keys[self.active_key_id],payload)
        return AdmissionReceipt(semantic,self.active_key_id,self.active_generation,now,now+ttl,mac)
    def verify(self, receipt:AdmissionReceipt, *, now:int, expected_source_root:str, expected_adapter_root:str,
               expected_runtime_root:str, expected_target_topology_root:str) -> str:
        if receipt.key_id != self.active_key_id or receipt.key_id not in self._keys: return 'HOLD_KEY_CURRENTNESS'
        if receipt.generation != self.active_generation: return 'HOLD_GENERATION_CURRENTNESS'
        if now < receipt.issued_at: return 'HOLD_NOT_YET_VALID'
        if now >= receipt.expires_at: return 'HOLD_EXPIRED'
        want=self._mac(self._keys[receipt.key_id],receipt.signed_payload)
        if not hmac.compare_digest(want,receipt.mac): return 'HOLD_BAD_SIGNATURE'
        s=receipt.semantic
        if s.source_root != expected_source_root: return 'HOLD_SOURCE_MISMATCH'
        if s.adapter_root != expected_adapter_root: return 'HOLD_ADAPTER_MISMATCH'
        if s.runtime_root != expected_runtime_root: return 'HOLD_RUNTIME_MISMATCH'
        if s.target_topology_root != expected_target_topology_root: return 'HOLD_TARGET_TOPOLOGY_MISMATCH'
        if s.action!='ADMIT_D0_ADAPTER_LOAD' or s.authority!='D0_NONPROMOTING' or s.gate10:
            return 'HOLD_AUTHORITY_WIDENING'
        return 'VERIFIED_D0_ADMISSION'

@dataclass(frozen=True)
class TransitionAdmissionBinding:
    transition_root:str
    admission_semantic_root:str
    admission_receipt_root:str
    adapter_root:str
    runtime_root:str
    deployment_generation:str
    def __post_init__(self):
        for n in ('transition_root','admission_semantic_root','admission_receipt_root','adapter_root','runtime_root'):
            needroot(getattr(self,n),n)
        if not self.deployment_generation: raise ValueError('deployment generation required')
    @property
    def binding_root(self): return jhash({'schema':SCHEMA,'kind':'transition_binding',**asdict(self)})

def verify_transition_admission(binding:TransitionAdmissionBinding, receipt:AdmissionReceipt, resolver:OwnerResolver, *, now:int) -> str:
    if binding.admission_semantic_root != receipt.semantic.semantic_root: return 'HOLD_SEMANTIC_BINDING_MISMATCH'
    if binding.admission_receipt_root != receipt.receipt_root: return 'HOLD_RECEIPT_BINDING_MISMATCH'
    if binding.adapter_root != receipt.semantic.adapter_root: return 'HOLD_ADAPTER_BINDING_MISMATCH'
    if binding.runtime_root != receipt.semantic.runtime_root: return 'HOLD_RUNTIME_BINDING_MISMATCH'
    return resolver.verify(receipt, now=now, expected_source_root=receipt.semantic.source_root,
        expected_adapter_root=binding.adapter_root, expected_runtime_root=binding.runtime_root,
        expected_target_topology_root=receipt.semantic.target_topology_root)

def minimum_reopen_cone(changed_root:str, bindings:list[TransitionAdmissionBinding]):
    return tuple(i for i,b in enumerate(bindings) if changed_root in {
        b.transition_root,b.admission_semantic_root,b.admission_receipt_root,b.adapter_root,b.runtime_root})

def omega8(state):
    if len(state)!=8 or any(v not in (0,1,2) for v in state): raise ValueError
    return 'KEEPER' if all(v==2 for v in state) else 'HOLD'

def factored13d(state):
    if len(state)!=13 or any(v not in (0,1,2) for v in state): raise ValueError
    return 'KEEPER' if all(v==2 for v in state) else 'HOLD'
