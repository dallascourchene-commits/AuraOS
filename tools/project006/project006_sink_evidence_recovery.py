from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import hmac, json
SCHEMA='AURA-PROJECT006-SINK-EVIDENCE-RECOVERY-v2'; D0='D0_NONPROMOTING'
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
class NativeState(str,Enum):
    ACK_WRITTEN_PRE_EFFECT='ACK_WRITTEN_PRE_EFFECT'; EXECUTION_STARTED='EXECUTION_STARTED'; RESULT_OBSERVED='RESULT_OBSERVED'; ERROR_TERMINAL='ERROR_TERMINAL'; COMPLETION_AMBIGUOUS='COMPLETION_AMBIGUOUS'; RETURN_WRITTEN='RETURN_WRITTEN'
class RecoveryCapability(str,Enum): IDEMPOTENT_RETRY='IDEMPOTENT_RETRY'; QUERY_RECONCILE='QUERY_RECONCILE'; NON_RETRYABLE='NON_RETRYABLE'
class SinkDisposition(str,Enum): ACCEPTED='ACCEPTED'; NOT_ACCEPTED='NOT_ACCEPTED'; UNKNOWN='UNKNOWN'
class RecoveryAction(str,Enum):
    START_PROVIDER_ONCE='START_PROVIDER_ONCE'; RETRY_PROVIDER_SAME_OPERATION_ID='RETRY_PROVIDER_SAME_OPERATION_ID'; QUERY_RECONCILE='QUERY_RECONCILE'; CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY='CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY'; RETRY_RETURN_WRITER_ONLY='RETRY_RETURN_WRITER_ONLY'; DONE='DONE'; HOLD_AMBIGUOUS_NO_REPLAY='HOLD_AMBIGUOUS_NO_REPLAY'; HOLD_INVALID_SINK_EVIDENCE='HOLD_INVALID_SINK_EVIDENCE'; HOLD_CURRENTNESS_MOVED='HOLD_CURRENTNESS_MOVED'; HOLD_UNSUPPORTED_STATE='HOLD_UNSUPPORTED_STATE'
@dataclass(frozen=True)
class OperationIdentity:
    command_id:str; operation_id:str; idempotency_key:str; payload_digest:str; source_file_id:str; source_revision:str; source_digest:str; authorization_root:str; proof_semantics_root:str; fence_root:str
    def __post_init__(self):
        for n in ('command_id','operation_id','idempotency_key','source_file_id','source_revision'): _id(getattr(self,n),n)
        for n in ('payload_digest','source_digest','authorization_root','proof_semantics_root','fence_root'): _root(getattr(self,n),n)
    @property
    def root(self): return digest({'schema':SCHEMA,'kind':'operation_identity',**self.__dict__})
@dataclass(frozen=True)
class CurrentOwnerContext:
    operation:OperationIdentity; authorization_root:str; proof_semantics_root:str; fence_root:str
    def __post_init__(self):
        for n in ('authorization_root','proof_semantics_root','fence_root'): _root(getattr(self,n),n)
@dataclass(frozen=True)
class SinkFenceContext:
    generation:int; installed_generation:int; receipt_root:str
    def __post_init__(self): _nn(self.generation,'generation'); _nn(self.installed_generation,'installed_generation'); _root(self.receipt_root,'receipt_root')
@dataclass(frozen=True)
class SinkEvidence:
    operation_id:str; disposition:SinkDisposition; sink_result_digest:str; result_locator_root:str|None; issuer_root:str; verifier_root:str; observed_at:int; expires_at:int; sink_fence_generation:int; mac:str
    def __post_init__(self):
        _id(self.operation_id,'operation_id'); _root(self.sink_result_digest,'sink_result_digest');
        if self.result_locator_root is not None: _root(self.result_locator_root,'result_locator_root')
        _root(self.issuer_root,'issuer_root'); _root(self.verifier_root,'verifier_root'); _nn(self.observed_at,'observed_at'); _nn(self.expires_at,'expires_at'); _nn(self.sink_fence_generation,'sink_fence_generation'); _root(self.mac,'mac')
        if self.expires_at<self.observed_at: raise ValueError('expires_at before observed_at')
    def unsigned_payload(self): return {'schema':SCHEMA,'kind':'sink_evidence','operation_id':self.operation_id,'disposition':self.disposition.value,'sink_result_digest':self.sink_result_digest,'result_locator_root':self.result_locator_root,'issuer_root':self.issuer_root,'verifier_root':self.verifier_root,'observed_at':self.observed_at,'expires_at':self.expires_at,'sink_fence_generation':self.sink_fence_generation}
def sign_sink_evidence(*,secret:bytes,operation_id:str,disposition:SinkDisposition,sink_result_digest:str,result_locator_root:str|None,issuer_root:str,verifier_root:str,observed_at:int,expires_at:int,sink_fence_generation:int):
    p={'schema':SCHEMA,'kind':'sink_evidence','operation_id':operation_id,'disposition':disposition.value,'sink_result_digest':sink_result_digest,'result_locator_root':result_locator_root,'issuer_root':issuer_root,'verifier_root':verifier_root,'observed_at':observed_at,'expires_at':expires_at,'sink_fence_generation':sink_fence_generation}; mac=hmac.new(secret,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sha256).hexdigest(); return SinkEvidence(operation_id=operation_id,disposition=disposition,sink_result_digest=sink_result_digest,result_locator_root=result_locator_root,issuer_root=issuer_root,verifier_root=verifier_root,observed_at=observed_at,expires_at=expires_at,sink_fence_generation=sink_fence_generation,mac=mac)
@dataclass(frozen=True)
class RecoveryDecision:
    action:RecoveryAction; reason:str; operation_root:str; sink_evidence_root:str|None=None; authority:str=D0; authority_minted:bool=False; effect_authority:bool=False; gate10:bool=False
    def __post_init__(self):
        _root(self.operation_root,'operation_root');
        if self.sink_evidence_root is not None: _root(self.sink_evidence_root,'sink_evidence_root')
        if self.authority_minted or self.effect_authority or self.gate10: raise ValueError('D0 recovery cannot mint authority')
def _owner_current(op,cur):
    if cur.operation.command_id!=op.command_id or cur.operation.operation_id!=op.operation_id: return False,'OPERATION_IDENTITY_MOVED'
    if cur.operation.idempotency_key!=op.idempotency_key or cur.operation.payload_digest!=op.payload_digest: return False,'IDEMPOTENCY_OR_PAYLOAD_MOVED'
    if (cur.operation.source_file_id,cur.operation.source_revision,cur.operation.source_digest)!=(op.source_file_id,op.source_revision,op.source_digest): return False,'SOURCE_CURRENTNESS_MOVED'
    if cur.authorization_root!=op.authorization_root or cur.operation.authorization_root!=op.authorization_root: return False,'AUTHORIZATION_MOVED'
    if cur.proof_semantics_root!=op.proof_semantics_root or cur.operation.proof_semantics_root!=op.proof_semantics_root: return False,'PROOF_SEMANTICS_MOVED'
    if cur.fence_root!=op.fence_root or cur.operation.fence_root!=op.fence_root: return False,'FENCE_MOVED'
    return True,'CURRENT'
def _verify_sink(e,*,secret,expected_operation_id,expected_issuer_root,expected_verifier_root,now):
    _nn(now,'now'); root=digest(e.unsigned_payload())
    if e.operation_id!=expected_operation_id: return False,'SINK_OPERATION_MISMATCH',root
    if e.issuer_root!=expected_issuer_root or e.verifier_root!=expected_verifier_root: return False,'SINK_TRUST_ROOT_MISMATCH',root
    if now>e.expires_at: return False,'SINK_EVIDENCE_EXPIRED',root
    expected=hmac.new(secret,json.dumps(e.unsigned_payload(),sort_keys=True,separators=(',',':')).encode(),sha256).hexdigest()
    if not hmac.compare_digest(expected,e.mac): return False,'SINK_EVIDENCE_MAC_INVALID',root
    return True,'SINK_EVIDENCE_VERIFIED',root
def _new_sink_fence(e,f): return f is not None and f.generation==f.installed_generation and f.installed_generation>e.sink_fence_generation
def decide_recovery(*,state,operation,current,capability,sink_evidence,secret,expected_issuer_root,expected_verifier_root,now,sink_fence:SinkFenceContext|None=None):
    op_root=operation.root
    if state is NativeState.RETURN_WRITTEN: return RecoveryDecision(RecoveryAction.DONE,'RETURN_ALREADY_DURABLE',op_root)
    if state in (NativeState.RESULT_OBSERVED,NativeState.ERROR_TERMINAL): return RecoveryDecision(RecoveryAction.RETRY_RETURN_WRITER_ONLY,'TERMINAL_OUTCOME_ALREADY_OBSERVED',op_root)
    current_ok,current_reason=_owner_current(operation,current)
    if state is NativeState.ACK_WRITTEN_PRE_EFFECT:
        return RecoveryDecision(RecoveryAction.START_PROVIDER_ONCE if current_ok else RecoveryAction.HOLD_CURRENTNESS_MOVED,'CURRENT_ACK_ALLOWS_FIRST_PROVIDER_ATTEMPT' if current_ok else current_reason,op_root)
    if state is not NativeState.COMPLETION_AMBIGUOUS: return RecoveryDecision(RecoveryAction.HOLD_UNSUPPORTED_STATE,'UNSUPPORTED_NATIVE_RECOVERY_STATE',op_root)
    evidence_root=None
    if sink_evidence is not None:
        ok,reason,evidence_root=_verify_sink(sink_evidence,secret=secret,expected_operation_id=operation.operation_id,expected_issuer_root=expected_issuer_root,expected_verifier_root=expected_verifier_root,now=now)
        if not ok: return RecoveryDecision(RecoveryAction.HOLD_INVALID_SINK_EVIDENCE,reason,op_root,evidence_root)
        if sink_evidence.disposition is SinkDisposition.ACCEPTED:
            if sink_evidence.result_locator_root is None: return RecoveryDecision(RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY,'ACCEPTED_RESULT_UNAVAILABLE',op_root,evidence_root)
            return RecoveryDecision(RecoveryAction.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY,'SINK_ACCEPTED_RESULT_RECOVERABLE',op_root,evidence_root)
        if sink_evidence.disposition is SinkDisposition.UNKNOWN: return RecoveryDecision(RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY,'SINK_STATUS_UNKNOWN',op_root,evidence_root)
        if sink_evidence.disposition is SinkDisposition.NOT_ACCEPTED:
            if not current_ok: return RecoveryDecision(RecoveryAction.HOLD_CURRENTNESS_MOVED,current_reason,op_root,evidence_root)
            if not _new_sink_fence(sink_evidence,sink_fence): return RecoveryDecision(RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY,'OLD_INFLIGHT_REQUEST_NOT_FENCED',op_root,evidence_root)
            if capability is RecoveryCapability.IDEMPOTENT_RETRY: return RecoveryDecision(RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID,'NOT_ACCEPTED_NEW_FENCE_CURRENT_IDEMPOTENT_CONTRACT',op_root,evidence_root)
            return RecoveryDecision(RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY,'NOT_ACCEPTED_WITHOUT_IDEMPOTENT_RETRY_CONTRACT',op_root,evidence_root)
    if not current_ok: return RecoveryDecision(RecoveryAction.HOLD_CURRENTNESS_MOVED,current_reason,op_root,evidence_root)
    if capability is RecoveryCapability.IDEMPOTENT_RETRY: return RecoveryDecision(RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID,'AMBIGUOUS_BUT_EXACT_IDEMPOTENT_RETRY',op_root,evidence_root)
    if capability is RecoveryCapability.QUERY_RECONCILE: return RecoveryDecision(RecoveryAction.QUERY_RECONCILE,'AMBIGUOUS_REQUIRES_PROVIDER_RECONCILIATION',op_root,evidence_root)
    return RecoveryDecision(RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY,'AMBIGUOUS_NONRETRYABLE_EFFECT',op_root,evidence_root)
