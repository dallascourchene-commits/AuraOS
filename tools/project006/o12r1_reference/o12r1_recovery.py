from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import hmac, json

SCHEMA='AURA-PROJECT006-O12R1-OWNER-AUTH-RECOVERY-v1'
D0='D0_NONPROMOTING'

def digest(v): return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def _root(v,f):
    if not isinstance(v,str) or len(v)!=64 or v.lower()!=v or any(c not in '0123456789abcdef' for c in v): raise ValueError(f'{f} must be lowercase sha256 hex')
    return v
def _id(v,f):
    if not isinstance(v,str) or not v or len(v)>2048: raise ValueError(f'{f} required')
    return v
def _nn(v,f):
    if type(v) is not int or v<0: raise ValueError(f'{f} must be nonnegative exact int')
    return v
def _sign(secret,p): return hmac.new(secret,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sha256).hexdigest()

class RecoveryMode(str,Enum): IDEMPOTENT_RETRY='IDEMPOTENT_RETRY'; QUERY_RECONCILE='QUERY_RECONCILE'; NON_RETRYABLE='NON_RETRYABLE'
class SinkDisposition(str,Enum): ACCEPTED='ACCEPTED'; NOT_ACCEPTED='NOT_ACCEPTED'; UNKNOWN='UNKNOWN'
class Action(str,Enum):
    RETRY_EXACT_SAME_EFFECT='RETRY_EXACT_SAME_EFFECT'; QUERY_PROVIDER_STATUS='QUERY_PROVIDER_STATUS'; CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY='CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY'; RETRY_RETURN_WRITER_ONLY='RETRY_RETURN_WRITER_ONLY'; DONE='DONE'; HOLD_INVALID_EVIDENCE='HOLD_INVALID_EVIDENCE'; HOLD_REBIND_REQUIRED='HOLD_REBIND_REQUIRED'; HOLD_AMBIGUOUS='HOLD_AMBIGUOUS'; HOLD_UNSUPPORTED='HOLD_UNSUPPORTED'
class FinalAction(str,Enum): STAGE_FINAL_RETURN='STAGE_FINAL_RETURN'; HOLD_RECOVERY_REQUIRED='HOLD_RECOVERY_REQUIRED'; HOLD_UNSUPPORTED='HOLD_UNSUPPORTED'

@dataclass(frozen=True)
class AtUseOwnerReceipt:
    operation_id:str; resource_root:str; intent_root:str; contract_root:str; source_digest:str; idempotency_key:str; effect_payload_root:str; authorization_root:str; proof_semantics_root:str; owner_generation:int; owner_root:str; verifier_root:str; observed_at:int; expires_at:int; mac:str
    def __post_init__(self):
        _id(self.operation_id,'operation_id'); _id(self.idempotency_key,'idempotency_key')
        for f in ('resource_root','intent_root','contract_root','source_digest','effect_payload_root','authorization_root','proof_semantics_root','owner_root','verifier_root','mac'): _root(getattr(self,f),f)
        for f in ('owner_generation','observed_at','expires_at'): _nn(getattr(self,f),f)
        if self.expires_at<self.observed_at: raise ValueError('expires_at before observed_at')
    def unsigned(self):
        return {'schema':SCHEMA,'kind':'at_use_owner_receipt','operation_id':self.operation_id,'resource_root':self.resource_root,'intent_root':self.intent_root,'contract_root':self.contract_root,'source_digest':self.source_digest,'idempotency_key':self.idempotency_key,'effect_payload_root':self.effect_payload_root,'authorization_root':self.authorization_root,'proof_semantics_root':self.proof_semantics_root,'owner_generation':self.owner_generation,'owner_root':self.owner_root,'verifier_root':self.verifier_root,'observed_at':self.observed_at,'expires_at':self.expires_at}

@dataclass(frozen=True)
class SinkEvidence:
    operation_id:str; effect_attempt_root:str; provider_operation_root:str; disposition:SinkDisposition; sink_result_digest:str; result_locator_root:str|None; fence_generation:int; issuer_root:str; verifier_root:str; observed_at:int; expires_at:int; mac:str
    def __post_init__(self):
        _id(self.operation_id,'operation_id')
        for f in ('effect_attempt_root','provider_operation_root','sink_result_digest','issuer_root','verifier_root','mac'): _root(getattr(self,f),f)
        if self.result_locator_root is not None: _root(self.result_locator_root,'result_locator_root')
        for f in ('fence_generation','observed_at','expires_at'): _nn(getattr(self,f),f)
        if self.expires_at<self.observed_at: raise ValueError('expires_at before observed_at')
    def unsigned(self):
        return {'schema':SCHEMA,'kind':'sink_evidence','operation_id':self.operation_id,'effect_attempt_root':self.effect_attempt_root,'provider_operation_root':self.provider_operation_root,'disposition':self.disposition.value,'sink_result_digest':self.sink_result_digest,'result_locator_root':self.result_locator_root,'fence_generation':self.fence_generation,'issuer_root':self.issuer_root,'verifier_root':self.verifier_root,'observed_at':self.observed_at,'expires_at':self.expires_at}

@dataclass(frozen=True)
class SinkFenceReceipt:
    operation_id:str; resource_root:str; fenced_attempt_root:str; previous_generation:int; generation:int; installed_generation:int; owner_root:str; verifier_root:str; owner_generation:int; observed_at:int; expires_at:int; mac:str
    def __post_init__(self):
        _id(self.operation_id,'operation_id')
        for f in ('resource_root','fenced_attempt_root','owner_root','verifier_root','mac'): _root(getattr(self,f),f)
        for f in ('previous_generation','generation','installed_generation','owner_generation','observed_at','expires_at'): _nn(getattr(self,f),f)
        if self.expires_at<self.observed_at: raise ValueError('expires_at before observed_at')
    def unsigned(self):
        return {'schema':SCHEMA,'kind':'sink_fence_receipt','operation_id':self.operation_id,'resource_root':self.resource_root,'fenced_attempt_root':self.fenced_attempt_root,'previous_generation':self.previous_generation,'generation':self.generation,'installed_generation':self.installed_generation,'owner_root':self.owner_root,'verifier_root':self.verifier_root,'owner_generation':self.owner_generation,'observed_at':self.observed_at,'expires_at':self.expires_at}

def sign_owner(*,secret,operation_id,resource_root,intent_root,contract_root,source_digest,idempotency_key,effect_payload_root,authorization_root,proof_semantics_root,owner_generation,owner_root,verifier_root,observed_at,expires_at):
    p={'schema':SCHEMA,'kind':'at_use_owner_receipt','operation_id':operation_id,'resource_root':resource_root,'intent_root':intent_root,'contract_root':contract_root,'source_digest':source_digest,'idempotency_key':idempotency_key,'effect_payload_root':effect_payload_root,'authorization_root':authorization_root,'proof_semantics_root':proof_semantics_root,'owner_generation':owner_generation,'owner_root':owner_root,'verifier_root':verifier_root,'observed_at':observed_at,'expires_at':expires_at}
    return AtUseOwnerReceipt(operation_id,resource_root,intent_root,contract_root,source_digest,idempotency_key,effect_payload_root,authorization_root,proof_semantics_root,owner_generation,owner_root,verifier_root,observed_at,expires_at,_sign(secret,p))
def sign_sink(*,secret,operation_id,effect_attempt_root,provider_operation_root,disposition,sink_result_digest,result_locator_root,fence_generation,issuer_root,verifier_root,observed_at,expires_at):
    p={'schema':SCHEMA,'kind':'sink_evidence','operation_id':operation_id,'effect_attempt_root':effect_attempt_root,'provider_operation_root':provider_operation_root,'disposition':disposition.value,'sink_result_digest':sink_result_digest,'result_locator_root':result_locator_root,'fence_generation':fence_generation,'issuer_root':issuer_root,'verifier_root':verifier_root,'observed_at':observed_at,'expires_at':expires_at}
    return SinkEvidence(operation_id,effect_attempt_root,provider_operation_root,disposition,sink_result_digest,result_locator_root,fence_generation,issuer_root,verifier_root,observed_at,expires_at,_sign(secret,p))
def sign_fence(*,secret,operation_id,resource_root,fenced_attempt_root,previous_generation,generation,installed_generation,owner_root,verifier_root,owner_generation,observed_at,expires_at):
    p={'schema':SCHEMA,'kind':'sink_fence_receipt','operation_id':operation_id,'resource_root':resource_root,'fenced_attempt_root':fenced_attempt_root,'previous_generation':previous_generation,'generation':generation,'installed_generation':installed_generation,'owner_root':owner_root,'verifier_root':verifier_root,'owner_generation':owner_generation,'observed_at':observed_at,'expires_at':expires_at}
    return SinkFenceReceipt(operation_id,resource_root,fenced_attempt_root,previous_generation,generation,installed_generation,owner_root,verifier_root,owner_generation,observed_at,expires_at,_sign(secret,p))

@dataclass(frozen=True)
class Decision:
    action:Action; reason:str; owner_row_root:str; currentness_root:str|None=None; evidence_root:str|None=None; fence_root:str|None=None; authority:str=D0; effect_authority:bool=False; gate10:bool=False
    def __post_init__(self):
        _root(self.owner_row_root,'owner_row_root')
        for f in ('currentness_root','evidence_root','fence_root'):
            v=getattr(self,f)
            if v is not None:_root(v,f)
        if self.authority!=D0 or self.effect_authority or self.gate10: raise ValueError('O12R1 cannot mint authority')
@dataclass(frozen=True)
class FinalDecision:
    action:FinalAction; reason:str; owner_row_root:str; authority:str=D0; effect_authority:bool=False; gate10:bool=False
    def __post_init__(self):
        _root(self.owner_row_root,'owner_row_root')
        if self.authority!=D0 or self.effect_authority or self.gate10: raise ValueError('O12R1 cannot mint authority')

def owner_row_root(row):
    keys=('command_id','idempotency_key','source_digest','intent_root','contract_root','effect_payload_root','phase','provider_request_count','effect_attempt_root','provider_operation_root','result_root')
    return digest({'schema':SCHEMA,'kind':'effect_attempt_owner_read',**{k:row.get(k) for k in keys}})

def _verify_owner(r,*,secret,row,expected_operation_id,expected_resource_root,expected_owner_root,expected_verifier_root,expected_owner_generation,now):
    cr=digest(r.unsigned())
    if r.operation_id!=expected_operation_id or r.resource_root!=expected_resource_root:return False,'CURRENT_OWNER_OPERATION_OR_RESOURCE_MISMATCH',cr
    if r.owner_root!=expected_owner_root or r.verifier_root!=expected_verifier_root:return False,'CURRENT_OWNER_TRUST_ROOT_MISMATCH',cr
    if r.owner_generation!=expected_owner_generation:return False,'CURRENT_OWNER_GENERATION_MOVED',cr
    if now>r.expires_at:return False,'CURRENT_OWNER_RECEIPT_EXPIRED',cr
    if not hmac.compare_digest(_sign(secret,r.unsigned()),r.mac):return False,'CURRENT_OWNER_RECEIPT_MAC_INVALID',cr
    if row.get('intent_root')!=r.intent_root or row.get('contract_root')!=r.contract_root:return False,'INTENT_OR_CONTRACT_MOVED',cr
    if row.get('source_digest')!=r.source_digest:return False,'SOURCE_CURRENTNESS_MOVED',cr
    if row.get('idempotency_key')!=r.idempotency_key or row.get('effect_payload_root')!=r.effect_payload_root:return False,'IDEMPOTENCY_OR_PAYLOAD_MOVED',cr
    return True,'CURRENT_OWNER_VERIFIED_AT_USE',cr

def _verify_sink(e,*,secret,row,operation_id,issuer_root,verifier_root,now):
    er=digest(e.unsigned())
    if e.operation_id!=operation_id:return False,'SINK_OPERATION_MISMATCH',er
    if e.effect_attempt_root!=row.get('effect_attempt_root'):return False,'SINK_ATTEMPT_MISMATCH',er
    if row.get('provider_operation_root') is None:return False,'OWNER_PROVIDER_OPERATION_UNAVAILABLE',er
    if e.provider_operation_root!=row.get('provider_operation_root'):return False,'SINK_PROVIDER_OPERATION_MISMATCH',er
    if e.issuer_root!=issuer_root or e.verifier_root!=verifier_root:return False,'SINK_TRUST_ROOT_MISMATCH',er
    if now>e.expires_at:return False,'SINK_EVIDENCE_EXPIRED',er
    if not hmac.compare_digest(_sign(secret,e.unsigned()),e.mac):return False,'SINK_EVIDENCE_MAC_INVALID',er
    return True,'SINK_VERIFIED',er

def _verify_fence(f,*,secret,row,e,operation_id,resource_root,owner_root,verifier_root,owner_generation,now):
    fr=digest(f.unsigned())
    if f.operation_id!=operation_id or f.resource_root!=resource_root:return False,'FENCE_OPERATION_OR_RESOURCE_MISMATCH',fr
    if f.fenced_attempt_root!=row.get('effect_attempt_root'):return False,'FENCE_ATTEMPT_MISMATCH',fr
    if f.owner_root!=owner_root or f.verifier_root!=verifier_root:return False,'FENCE_OWNER_OR_VERIFIER_MISMATCH',fr
    if f.owner_generation!=owner_generation:return False,'FENCE_OWNER_GENERATION_MOVED',fr
    if now>f.expires_at:return False,'FENCE_RECEIPT_EXPIRED',fr
    if not hmac.compare_digest(_sign(secret,f.unsigned()),f.mac):return False,'FENCE_RECEIPT_MAC_INVALID',fr
    if f.generation!=f.installed_generation:return False,'FENCE_NOT_INSTALLED_CURRENT',fr
    if f.generation<=e.fence_generation or f.previous_generation<e.fence_generation:return False,'FENCE_NOT_NEWER_THAN_OBSERVED_ATTEMPT',fr
    return True,'FENCE_VERIFIED_CURRENT',fr

def decide_from_owner(*,journal,command_id,recovery_mode,current_receipt,current_secret,current_operation_id,current_resource_root,current_owner_root,current_verifier_root,current_owner_generation,sink_evidence,sink_secret,sink_issuer_root,sink_verifier_root,fence_receipt,fence_secret,fence_owner_root,fence_verifier_root,fence_owner_generation,now):
    row=journal.status(command_id); rr=owner_row_root(row); phase=row.get('phase')
    if phase=='RETURN_WRITTEN':return Decision(Action.DONE,'RETURN_ALREADY_DURABLE',rr)
    if phase in ('RESULT_OBSERVED','ERROR_TERMINAL'):return Decision(Action.RETRY_RETURN_WRITER_ONLY,'TERMINAL_OUTCOME_ALREADY_OBSERVED',rr)
    if phase!='COMPLETION_AMBIGUOUS':return Decision(Action.HOLD_UNSUPPORTED,'O12R1_ONLY_OWNS_POST_ATTEMPT_AMBIGUITY',rr)
    if not isinstance(current_receipt,AtUseOwnerReceipt):return Decision(Action.HOLD_REBIND_REQUIRED,'AUTHENTICATED_CURRENT_OWNER_RECEIPT_REQUIRED',rr)
    cok,cwhy,cr=_verify_owner(current_receipt,secret=current_secret,row=row,expected_operation_id=current_operation_id,expected_resource_root=current_resource_root,expected_owner_root=current_owner_root,expected_verifier_root=current_verifier_root,expected_owner_generation=current_owner_generation,now=now)
    if not cok:return Decision(Action.HOLD_REBIND_REQUIRED,cwhy,rr,cr)
    if sink_evidence is None:
        if recovery_mode is RecoveryMode.IDEMPOTENT_RETRY:return Decision(Action.RETRY_EXACT_SAME_EFFECT,'AUTHENTICATED_CURRENT_OWNER_PROVIDER_DEDUPED_RETRY',rr,cr)
        if recovery_mode is RecoveryMode.QUERY_RECONCILE:return Decision(Action.QUERY_PROVIDER_STATUS,'QUERY_BEFORE_ANY_RESEND',rr,cr)
        return Decision(Action.HOLD_AMBIGUOUS,'NONRETRYABLE_AMBIGUOUS_EFFECT',rr,cr)
    sok,swhy,er=_verify_sink(sink_evidence,secret=sink_secret,row=row,operation_id=current_operation_id,issuer_root=sink_issuer_root,verifier_root=sink_verifier_root,now=now)
    if not sok:return Decision(Action.HOLD_INVALID_EVIDENCE,swhy,rr,cr,er)
    if sink_evidence.disposition is SinkDisposition.ACCEPTED:
        if sink_evidence.result_locator_root is None:return Decision(Action.HOLD_AMBIGUOUS,'ACCEPTED_RESULT_UNAVAILABLE',rr,cr,er)
        return Decision(Action.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY,'ACCEPTED_EXACT_ATTEMPT_RESULT_RECOVERABLE',rr,cr,er)
    if sink_evidence.disposition is SinkDisposition.UNKNOWN:return Decision(Action.HOLD_AMBIGUOUS,'VERIFIED_STATUS_UNKNOWN',rr,cr,er)
    if recovery_mode is RecoveryMode.NON_RETRYABLE:return Decision(Action.HOLD_AMBIGUOUS,'NOT_ACCEPTED_BUT_CONTRACT_NONRETRYABLE',rr,cr,er)
    if fence_receipt is None:return Decision(Action.HOLD_AMBIGUOUS,'RIGHTFUL_INSTALLED_SINK_FENCE_REQUIRED',rr,cr,er)
    fok,fwhy,fr=_verify_fence(fence_receipt,secret=fence_secret,row=row,e=sink_evidence,operation_id=current_operation_id,resource_root=current_resource_root,owner_root=fence_owner_root,verifier_root=fence_verifier_root,owner_generation=fence_owner_generation,now=now)
    if not fok:return Decision(Action.HOLD_INVALID_EVIDENCE,fwhy,rr,cr,er,fr)
    return Decision(Action.RETRY_EXACT_SAME_EFFECT,'NOT_ACCEPTED_RIGHTFUL_NEW_FENCE_EXCLUDES_OLD_ATTEMPT',rr,cr,er,fr)

def guard_final_projection(*,journal,command_id,recovery_mode):
    row=journal.status(command_id); rr=owner_row_root(row); phase=row.get('phase')
    if phase in ('RESULT_OBSERVED','ERROR_TERMINAL'):return FinalDecision(FinalAction.STAGE_FINAL_RETURN,'TERMINAL_OUTCOME_MAY_PROJECT',rr)
    if phase=='COMPLETION_AMBIGUOUS':
        if recovery_mode is RecoveryMode.NON_RETRYABLE:return FinalDecision(FinalAction.STAGE_FINAL_RETURN,'NONRETRYABLE_AMBIGUITY_MAY_PUBLISH_HOLD_RETURN',rr)
        return FinalDecision(FinalAction.HOLD_RECOVERY_REQUIRED,'RETRYABLE_OR_QUERYABLE_AMBIGUITY_MUST_NOT_FINALIZE',rr)
    return FinalDecision(FinalAction.HOLD_UNSUPPORTED,'NO_FINAL_EFFECT_TERMINAL',rr)
