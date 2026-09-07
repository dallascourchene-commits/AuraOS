from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json

HEX=set('0123456789abcdef')
O1_RECEIPT_ROOT='ed8975dead9f66ebbf559c41865a757cdc437a5d99102d755d47fceffa3209ed'
AIRLLM_COMMIT='55e435087d951da8c25ab3672e969025241a398e'
PARENT_BOUNDARY='1Y4R5iX5yU2G4-AcXvfVDE9ohYnk1QEwM'
PARENT_PHYSICAL='18ZsY5e2KLzQLBr8ConI1qp7PxL-giOFRzashya6-nvM'
SUPPORTED={('qwen3_5','AirLLMLoRA'),('qwen3_8','AirLLMLoRA'),('qwen4_exp','AirLLMLoRAQwen4Exp')}

def h(obj):
    if not isinstance(obj,(str,bytes)):
        obj=json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True)
    if isinstance(obj,str): obj=obj.encode()
    return sha256(obj).hexdigest()

def isroot(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX

def _roots(*xs):
    if not all(isroot(x) for x in xs): raise ValueError('all roots must be lowercase sha256 hex')

@dataclass(frozen=True)
class AdapterCore:
    base_checkpoint_root:str; adapter_values_root:str; config_root:str; tokenizer_root:str
    airllm_commit:str; model_family:str; trainer_class:str; target_topology_root:str
    def __post_init__(self):
        _roots(self.base_checkpoint_root,self.adapter_values_root,self.config_root,self.tokenizer_root,self.target_topology_root)
        if self.airllm_commit != AIRLLM_COMMIT: raise ValueError('airllm source generation drift')
        if (self.model_family,self.trainer_class) not in SUPPORTED: raise ValueError('unsupported training family')
    @property
    def identity_root(self): return h({'schema':'AdapterCore/v1',**asdict(self)})

@dataclass(frozen=True)
class TransitionEnvelope:
    training_admission_root:str; base_core_root:str; from_adapter_root:str; to_adapter_root:str
    inference_runtime_root:str; cache_policy_root:str; deployment_generation:str; activation_mode:str='runtime_adapter'
    merge_grid_root:str|None=None
    def __post_init__(self):
        _roots(self.training_admission_root,self.base_core_root,self.from_adapter_root,self.to_adapter_root,self.inference_runtime_root,self.cache_policy_root)
        if self.training_admission_root != O1_RECEIPT_ROOT: raise ValueError('training admission root not O1-bound')
        if self.activation_mode not in {'runtime_adapter','merged_checkpoint'}: raise ValueError('bad activation mode')
        if self.activation_mode=='merged_checkpoint':
            if self.merge_grid_root is None or not isroot(self.merge_grid_root): raise ValueError('merged checkpoint requires exact grid root')
        elif self.merge_grid_root is not None: raise ValueError('runtime adapter must not carry merge grid')
        if not self.deployment_generation: raise ValueError('deployment generation required')
    @property
    def transition_root(self): return h({'schema':'AdapterTransition/v1',**asdict(self)})
    @property
    def source_envelope_digest(self):
        return h({'schema':'AdapterTransitionSourceEnvelope/v1','transition_root':self.transition_root,'training_admission_root':self.training_admission_root,'base_core_root':self.base_core_root,'to_adapter_root':self.to_adapter_root,'runtime_root':self.inference_runtime_root,'deployment_generation':self.deployment_generation})

@dataclass(frozen=True)
class Ack:
    command_id:str; attempt_id:str; idempotency_key:str; source_envelope_digest:str
    transition_root:str; training_admission_root:str; adapter_core_root:str; runtime_root:str; ordinal:int

@dataclass(frozen=True)
class Result:
    command_id:str; attempt_id:str; idempotency_key:str; source_envelope_digest:str
    transition_root:str; training_admission_root:str; adapter_core_root:str; runtime_root:str; ordinal:int
    provider_success:bool=True

def verify_transition(core:AdapterCore, env:TransitionEnvelope, ack:Ack|None, result:Result|None, independently_recomputed_source_digest:str|None):
    if core.identity_root != env.to_adapter_root: return 'HOLD_ADAPTER_CORE_MISMATCH'
    if ack is None or result is None: return 'HOLD_UNBOUND_PHYSICAL_SUCCESS'
    if independently_recomputed_source_digest != env.source_envelope_digest: return 'HOLD_SOURCE_RECOMPUTE_MISMATCH'
    expected=(env.source_envelope_digest,env.transition_root,env.training_admission_root,core.identity_root,env.inference_runtime_root)
    for obj in (ack,result):
        got=(obj.source_envelope_digest,obj.transition_root,obj.training_admission_root,obj.adapter_core_root,obj.runtime_root)
        if got != expected: return 'HOLD_TRANSITION_IDENTITY_MISMATCH'
    if (ack.command_id,ack.attempt_id,ack.idempotency_key)!=(result.command_id,result.attempt_id,result.idempotency_key): return 'HOLD_COMMAND_BINDING_MISMATCH'
    if ack.ordinal >= result.ordinal: return 'HOLD_TEMPORAL_ORDER'
    if not result.provider_success: return 'HOLD_PROVIDER_RESULT'
    return 'ADMIT_D0_PROOF_CARRYING_TRANSITION'

def minimum_reopen_cone(changed_root:str, transitions:list[TransitionEnvelope]):
    out=[]
    for i,t in enumerate(transitions):
        if changed_root in {t.base_core_root,t.from_adapter_root,t.to_adapter_root,t.inference_runtime_root,t.cache_policy_root,t.training_admission_root,t.merge_grid_root}:
            out.append(i)
    return tuple(out)

def omega8(state):
    if len(state)!=8 or any(v not in (0,1,2) for v in state): raise ValueError
    return 'KEEPER' if all(v==2 for v in state) else 'HOLD'

def factored13d(state):
    if len(state)!=13 or any(v not in (0,1,2) for v in state): raise ValueError
    return 'KEEPER' if all(v==2 for v in state) else 'HOLD'
