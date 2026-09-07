from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import hmac
import json

from tools.awj032.training_r1_resolver_reference.training_admission_resolver import (
    OwnerResolver, TransitionPermit, AIRLLM_COMMIT,
)

SCHEMA='AURA-AWJ032-AIRLLM-ADAPTER-TRANSITION-v3'
HEX=set('0123456789abcdef')
SUPPORTED={('qwen3_5','AirLLMLoRA'),('qwen3_8_dense','AirLLMLoRA'),('qwen4_exp','AirLLMLoRAQwen4Exp')}


def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def jhash(v): return sha256(canon(v)).hexdigest()
def isroot(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX
def needroot(x,n):
    if not isroot(x): raise ValueError(f'{n}: sha256 required')
def valid_int(x): return type(x) is int


@dataclass(frozen=True)
class AdapterCore:
    o1_adapter_root:str
    base_checkpoint_root:str
    adapter_values_root:str
    config_root:str
    tokenizer_root:str
    source_root:str
    airllm_commit:str
    model_family:str
    trainer_class:str
    target_topology_root:str
    def __post_init__(self):
        for n in ('o1_adapter_root','base_checkpoint_root','adapter_values_root','config_root','tokenizer_root','source_root','target_topology_root'):
            needroot(getattr(self,n),n)
        if self.airllm_commit != AIRLLM_COMMIT: raise ValueError('airllm source generation drift')
        if (self.model_family,self.trainer_class) not in SUPPORTED: raise ValueError('unsupported training family')
    @property
    def identity_root(self): return jhash({'schema':SCHEMA,'kind':'adapter_core',**asdict(self)})


@dataclass(frozen=True)
class TransitionIntent:
    o1_adapter_root:str
    base_core_root:str
    from_adapter_root:str
    to_adapter_root:str
    inference_runtime_root:str
    cache_policy_root:str
    deployment_generation:str
    activation_mode:str='runtime_adapter'
    merge_grid_root:str|None=None
    def __post_init__(self):
        for n in ('o1_adapter_root','base_core_root','from_adapter_root','to_adapter_root','inference_runtime_root','cache_policy_root'):
            needroot(getattr(self,n),n)
        if not self.deployment_generation: raise ValueError('deployment generation required')
        if self.activation_mode not in {'runtime_adapter','merged_checkpoint'}: raise ValueError('bad activation mode')
        if self.activation_mode=='merged_checkpoint':
            if self.merge_grid_root is None: raise ValueError('merged checkpoint requires exact grid root')
            needroot(self.merge_grid_root,'merge_grid_root')
        elif self.merge_grid_root is not None:
            raise ValueError('runtime adapter must not carry merge grid')
    @property
    def intent_root(self): return jhash({'schema':SCHEMA,'kind':'transition_intent',**asdict(self)})


@dataclass(frozen=True)
class TransitionEnvelope:
    intent:TransitionIntent
    admission_permit_root:str
    def __post_init__(self): needroot(self.admission_permit_root,'admission_permit_root')
    @property
    def transition_root(self): return jhash({'schema':SCHEMA,'kind':'transition_envelope','intent_root':self.intent.intent_root,'admission_permit_root':self.admission_permit_root})
    @property
    def source_envelope_digest(self):
        return jhash({'schema':SCHEMA,'kind':'source_envelope','transition_root':self.transition_root,
            'intent_root':self.intent.intent_root,'admission_permit_root':self.admission_permit_root,
            'o1_adapter_root':self.intent.o1_adapter_root,'base_core_root':self.intent.base_core_root,
            'to_adapter_root':self.intent.to_adapter_root,'runtime_root':self.intent.inference_runtime_root,
            'deployment_generation':self.intent.deployment_generation})


@dataclass(frozen=True)
class AckPayload:
    command_id:str
    attempt_id:str
    idempotency_key:str
    source_envelope_digest:str
    transition_root:str
    admission_permit_root:str
    adapter_core_root:str
    runtime_root:str
    ordinal:int
    def __post_init__(self):
        if not self.command_id or not self.attempt_id or not self.idempotency_key: raise ValueError('nonempty physical trace identity required')
        for n in ('source_envelope_digest','transition_root','admission_permit_root','adapter_core_root','runtime_root'):
            needroot(getattr(self,n),n)
        if not valid_int(self.ordinal) or self.ordinal < 0: raise ValueError('ordinal')


@dataclass(frozen=True)
class ResultPayload:
    command_id:str
    attempt_id:str
    idempotency_key:str
    source_envelope_digest:str
    transition_root:str
    admission_permit_root:str
    adapter_core_root:str
    runtime_root:str
    ordinal:int
    provider_success:bool
    def __post_init__(self):
        if not self.command_id or not self.attempt_id or not self.idempotency_key: raise ValueError('nonempty physical trace identity required')
        for n in ('source_envelope_digest','transition_root','admission_permit_root','adapter_core_root','runtime_root'):
            needroot(getattr(self,n),n)
        if not valid_int(self.ordinal) or self.ordinal < 0: raise ValueError('ordinal')
        if type(self.provider_success) is not bool: raise ValueError('provider_success must be explicit bool')


@dataclass(frozen=True)
class SignedAck:
    payload:AckPayload
    key_id:str
    generation:int
    mac:str
    def __post_init__(self):
        if not self.key_id or not valid_int(self.generation) or self.generation < 1: raise ValueError('trace generation')
        needroot(self.mac,'mac')
    @property
    def signed_payload(self): return {'schema':SCHEMA,'kind':'ack','payload':asdict(self.payload),'key_id':self.key_id,'generation':self.generation}
    @property
    def ack_root(self): return jhash({**self.signed_payload,'mac':self.mac})


@dataclass(frozen=True)
class SignedResult:
    payload:ResultPayload
    key_id:str
    generation:int
    mac:str
    def __post_init__(self):
        if not self.key_id or not valid_int(self.generation) or self.generation < 1: raise ValueError('trace generation')
        needroot(self.mac,'mac')
    @property
    def signed_payload(self): return {'schema':SCHEMA,'kind':'result','payload':asdict(self.payload),'key_id':self.key_id,'generation':self.generation}
    @property
    def result_root(self): return jhash({**self.signed_payload,'mac':self.mac})


class PhysicalTraceAuthority:
    def __init__(self, keys:dict[str,bytes], active_key_id:str, generation:int):
        if active_key_id not in keys or not valid_int(generation) or generation < 1: raise ValueError('trace authority config')
        self._keys={k:bytes(v) for k,v in keys.items()}; self.active_key_id=active_key_id; self.generation=generation
    @staticmethod
    def _mac(key,payload): return hmac.new(key,canon(payload),sha256).hexdigest()
    def issue_ack(self,payload:AckPayload):
        p={'schema':SCHEMA,'kind':'ack','payload':asdict(payload),'key_id':self.active_key_id,'generation':self.generation}
        return SignedAck(payload,self.active_key_id,self.generation,self._mac(self._keys[self.active_key_id],p))
    def issue_result(self,payload:ResultPayload):
        p={'schema':SCHEMA,'kind':'result','payload':asdict(payload),'key_id':self.active_key_id,'generation':self.generation}
        return SignedResult(payload,self.active_key_id,self.generation,self._mac(self._keys[self.active_key_id],p))
    def verify_ack(self,ack:SignedAck):
        if ack.key_id!=self.active_key_id or ack.key_id not in self._keys: return False
        if ack.generation!=self.generation: return False
        return hmac.compare_digest(self._mac(self._keys[ack.key_id],ack.signed_payload),ack.mac)
    def verify_result(self,result:SignedResult):
        if result.key_id!=self.active_key_id or result.key_id not in self._keys: return False
        if result.generation!=self.generation: return False
        return hmac.compare_digest(self._mac(self._keys[result.key_id],result.signed_payload),result.mac)


def verify_transition(*, core:AdapterCore, env:TransitionEnvelope, permit:TransitionPermit, admission_resolver:OwnerResolver,
                      trace_authority:PhysicalTraceAuthority, ack:SignedAck|None, result:SignedResult|None,
                      independently_recomputed_source_digest:str|None, now:int, observed_source_root:str,
                      observed_target_topology_root:str):
    if core.identity_root != env.intent.to_adapter_root: return 'HOLD_ADAPTER_CORE_MISMATCH'
    if core.o1_adapter_root != env.intent.o1_adapter_root: return 'HOLD_O1_ADAPTER_BINDING'
    if permit.permit_root != env.admission_permit_root: return 'HOLD_ADMISSION_PERMIT_ROOT'
    if permit.adapter_root != core.o1_adapter_root: return 'HOLD_ADMISSION_ADAPTER_BINDING'
    if permit.transition_subject_root != core.identity_root: return 'HOLD_TRANSITION_SUBJECT_BINDING'
    if permit.runtime_root != env.intent.inference_runtime_root: return 'HOLD_ADMISSION_RUNTIME_BINDING'
    p=admission_resolver.verify_transition_permit(permit,now=now,expected_transition_root=env.intent.intent_root,expected_transition_subject_root=core.identity_root,
        expected_deployment_generation=env.intent.deployment_generation,observed_source_root=observed_source_root,
        observed_adapter_root=core.o1_adapter_root,observed_runtime_root=env.intent.inference_runtime_root,
        observed_target_topology_root=observed_target_topology_root)
    if p!='VERIFIED_D0_TRANSITION_PERMIT': return 'HOLD_ADMISSION_PERMIT:'+p
    if ack is None or result is None: return 'HOLD_UNBOUND_PHYSICAL_SUCCESS'
    if not trace_authority.verify_ack(ack): return 'HOLD_ACK_SIGNATURE'
    if not trace_authority.verify_result(result): return 'HOLD_RESULT_SIGNATURE'
    if independently_recomputed_source_digest != env.source_envelope_digest: return 'HOLD_SOURCE_RECOMPUTE_MISMATCH'
    expected=(env.source_envelope_digest,env.transition_root,env.admission_permit_root,core.identity_root,env.intent.inference_runtime_root)
    ag=(ack.payload.source_envelope_digest,ack.payload.transition_root,ack.payload.admission_permit_root,ack.payload.adapter_core_root,ack.payload.runtime_root)
    rg=(result.payload.source_envelope_digest,result.payload.transition_root,result.payload.admission_permit_root,result.payload.adapter_core_root,result.payload.runtime_root)
    if ag != expected or rg != expected: return 'HOLD_TRANSITION_IDENTITY_MISMATCH'
    ids=(ack.payload.command_id,ack.payload.attempt_id,ack.payload.idempotency_key)
    if ids != (result.payload.command_id,result.payload.attempt_id,result.payload.idempotency_key): return 'HOLD_COMMAND_BINDING_MISMATCH'
    if ack.payload.ordinal >= result.payload.ordinal: return 'HOLD_TEMPORAL_ORDER'
    if not result.payload.provider_success: return 'HOLD_PROVIDER_RESULT'
    return 'ADMIT_D0_PROOF_CARRYING_TRANSITION'


def minimum_reopen_cone(changed_root,transitions):
    out=[]
    for i,t in enumerate(transitions):
        x=t.intent
        if changed_root in {t.admission_permit_root,x.o1_adapter_root,x.base_core_root,x.from_adapter_root,x.to_adapter_root,x.inference_runtime_root,x.cache_policy_root,x.merge_grid_root}:
            out.append(i)
    return tuple(out)
def omega8(s): return 'KEEPER' if len(s)==8 and all(v==2 for v in s) else 'HOLD'
def factored13d(s): return 'KEEPER' if len(s)==13 and all(v==2 for v in s) else 'HOLD'
