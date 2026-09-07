from __future__ import annotations
import hashlib,hmac,json,sqlite3,time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

SCHEMA='AURA-P006-O15-WORKCELL-STABLE-OP-v1'; D0='D0_NONPROMOTING'
def H(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def R(v,n):
    if not isinstance(v,str) or len(v)!=64 or v.lower()!=v or any(c not in '0123456789abcdef' for c in v): raise ValueError(n)
    return v
def I(v,n):
    if not isinstance(v,str) or not v: raise ValueError(n)
    return v
def NN(v,n):
    if type(v) is not int or v<0: raise ValueError(n)
    return v

def sign(key:bytes,payload:dict)->str:
    if not isinstance(key,bytes) or len(key)<16: raise ValueError('lease_key')
    return hmac.new(key,json.dumps(payload,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()

class Action(str,Enum): CALL='CALL_PROVIDER_FIRST_TIME'; RETRY='RETRY_EXACT_SAME_EFFECT'; HOLD='HOLD'; RETURN='RETURN_WRITER_ONLY'
@dataclass(frozen=True)
class SemanticOperation:
    command_id:str; idempotency_key:str; source_file_id:str; source_revision:str; source_digest:str; intent_root:str; contract_root:str; payload_root:str
    def __post_init__(s):
        for n in ('command_id','idempotency_key','source_file_id','source_revision'): I(getattr(s,n),n)
        for n in ('source_digest','intent_root','contract_root','payload_root'): R(getattr(s,n),n)
    @property
    def root(s): return H({'schema':SCHEMA,'kind':'stable_operation','command_id':s.command_id,'idempotency_key':s.idempotency_key,'source_file_id':s.source_file_id,'source_revision':s.source_revision,'source_digest':s.source_digest,'intent_root':s.intent_root,'contract_root':s.contract_root,'payload_root':s.payload_root})

@dataclass(frozen=True)
class WorkcellLease:
    handle:str; session_id:str; objective_root:str; project:str; card_root:str; progress_root:str; host_generation:int; issued_at:int; expires_at:int; nonce_root:str; mac:str
    def __post_init__(s):
        for n in ('handle','session_id','project'): I(getattr(s,n),n)
        for n in ('objective_root','card_root','progress_root','nonce_root','mac'): R(getattr(s,n),n)
        for n in ('host_generation','issued_at','expires_at'): NN(getattr(s,n),n)
        if s.expires_at<s.issued_at: raise ValueError('lease_time')
    def unsigned(s): return {'schema':SCHEMA,'kind':'workcell_lease','handle':s.handle,'session_id':s.session_id,'objective_root':s.objective_root,'project':s.project,'card_root':s.card_root,'progress_root':s.progress_root,'host_generation':s.host_generation,'issued_at':s.issued_at,'expires_at':s.expires_at,'nonce_root':s.nonce_root}
    @property
    def root(s): return H({'unsigned':s.unsigned(),'mac':s.mac})

@dataclass(frozen=True)
class HostCurrent:
    session_id:str; objective_root:str; project:str; card_root:str; progress_root:str; host_generation:int; now:int
    def __post_init__(s):
        for n in ('session_id','project'): I(getattr(s,n),n)
        for n in ('objective_root','card_root','progress_root'): R(getattr(s,n),n)
        NN(s.host_generation,'host_generation'); NN(s.now,'now')

@dataclass(frozen=True)
class ProofBoundAttempt:
    action:Action; command_id:str; stable_operation_root:str; proof_bound_admission_root:str; parent_attempt_root:str; provider_request_count:int
    def __post_init__(s):
        if s.action not in (Action.CALL,Action.RETRY): raise ValueError('provider_action')
        I(s.command_id,'command_id')
        for n in ('stable_operation_root','proof_bound_admission_root','parent_attempt_root'): R(getattr(s,n),n)
        if type(s.provider_request_count) is not int or s.provider_request_count<1: raise ValueError('provider_request_count')

@dataclass(frozen=True)
class ExecutionPermit:
    action:Action; command_id:str; stable_operation_root:str; workcell_lease_root:str; proof_bound_admission_root:str; parent_attempt_root:str; execution_witness_root:str; provider_request_count:int; authority:str=D0; effect_authority:bool=False; gate10:bool=False
    def __post_init__(s):
        if s.action not in (Action.CALL,Action.RETRY): raise ValueError('action')
        for n in ('stable_operation_root','workcell_lease_root','proof_bound_admission_root','parent_attempt_root','execution_witness_root'): R(getattr(s,n),n)
        if s.authority!=D0 or s.effect_authority or s.gate10: raise ValueError('authority')


def issue_lease(*,key:bytes,handle:str,session_id:str,objective_root:str,project:str,card_root:str,progress_root:str,host_generation:int,issued_at:int,expires_at:int)->WorkcellLease:
    payload={'schema':SCHEMA,'kind':'workcell_lease','handle':handle,'session_id':session_id,'objective_root':objective_root,'project':project,'card_root':card_root,'progress_root':progress_root,'host_generation':host_generation,'issued_at':issued_at,'expires_at':expires_at,'nonce_root':H([handle,session_id,issued_at,host_generation])}
    return WorkcellLease(handle=handle,session_id=session_id,objective_root=objective_root,project=project,card_root=card_root,progress_root=progress_root,host_generation=host_generation,issued_at=issued_at,expires_at=expires_at,nonce_root=payload['nonce_root'],mac=sign(key,payload))

def verify_lease(lease:WorkcellLease,current:HostCurrent,key:bytes)->str:
    if not hmac.compare_digest(sign(key,lease.unsigned()),lease.mac): raise ValueError('WORKCELL_MAC_INVALID')
    if lease.session_id!=current.session_id: raise ValueError('WORKCELL_SESSION_MOVED')
    if lease.objective_root!=current.objective_root or lease.project!=current.project: raise ValueError('WORKCELL_OBJECTIVE_OR_PROJECT_MOVED')
    if lease.card_root!=current.card_root: raise ValueError('WORKCELL_CARD_MOVED')
    if lease.progress_root!=current.progress_root: raise ValueError('WORKCELL_PROGRESS_MOVED')
    if lease.host_generation!=current.host_generation: raise ValueError('HOST_GENERATION_MOVED')
    if current.now>lease.expires_at: raise ValueError('WORKCELL_EXPIRED')
    if current.now<lease.issued_at: raise ValueError('HOST_CLOCK_BEFORE_LEASE')
    return lease.root

def execution_witness(op_root:str,lease_root:str,attempt:ProofBoundAttempt,recovery_verdict_root:str|None=None)->str:
    R(op_root,'op_root'); R(lease_root,'lease_root')
    if recovery_verdict_root is not None: R(recovery_verdict_root,'recovery_verdict_root')
    return H({'schema':SCHEMA,'kind':'workcell_execution_witness','stable_operation_root':op_root,'workcell_lease_root':lease_root,'proof_bound_admission_root':attempt.proof_bound_admission_root,'parent_attempt_root':attempt.parent_attempt_root,'provider_request_count':attempt.provider_request_count,'recovery_verdict_root':recovery_verdict_root,'authority':D0,'effect_authority':False,'gate10':False})

class Gate:
    def __init__(self,path:str|Path,*,lease_key:bytes):
        self.path=str(path); self.lease_key=lease_key
        c=sqlite3.connect(self.path); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL'); c.execute('''CREATE TABLE IF NOT EXISTS o15_op(command_id TEXT PRIMARY KEY,idempotency_key TEXT,source_file_id TEXT,source_revision TEXT,source_digest TEXT,intent_root TEXT,contract_root TEXT,payload_root TEXT,stable_operation_root TEXT,phase TEXT,last_attempt_root TEXT,last_admission_root TEXT,last_workcell_root TEXT,last_execution_root TEXT,provider_request_count INTEGER,result_root TEXT)'''); c.commit(); c.close()
    @contextmanager
    def con(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; c.execute('BEGIN IMMEDIATE')
        try: yield c; c.commit()
        except Exception: c.rollback(); raise
        finally: c.close()
    def status(self,command_id):
        with self.con() as c:
            r=c.execute('SELECT * FROM o15_op WHERE command_id=?',(command_id,)).fetchone()
            if r is None: raise ValueError('OPERATION_NOT_BOUND')
            return dict(r)
    @staticmethod
    def _sem(op:SemanticOperation): return (op.idempotency_key,op.source_file_id,op.source_revision,op.source_digest,op.intent_root,op.contract_root,op.payload_root)
    def _check_attempt(self,op:SemanticOperation,a:ProofBoundAttempt,expected:Action):
        if a.action is not expected: raise ValueError('PARENT_ACTION_MISMATCH')
        if a.command_id!=op.command_id: raise ValueError('PARENT_COMMAND_MOVED')
        if a.stable_operation_root!=op.root: raise ValueError('PARENT_STABLE_OPERATION_MOVED')
    def expose_first(self,op:SemanticOperation,lease:WorkcellLease,current:HostCurrent,a:ProofBoundAttempt)->ExecutionPermit:
        self._check_attempt(op,a,Action.CALL)
        if a.provider_request_count!=1: raise ValueError('FIRST_ATTEMPT_COUNT')
        lr=verify_lease(lease,current,self.lease_key); er=execution_witness(op.root,lr,a)
        with self.con() as c:
            old=c.execute('SELECT * FROM o15_op WHERE command_id=?',(op.command_id,)).fetchone(); sem=self._sem(op)
            if old is None:
                c.execute('INSERT INTO o15_op VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)',(op.command_id,*sem,op.root,'EXPOSED',a.parent_attempt_root,a.proof_bound_admission_root,lr,er,a.provider_request_count))
            else:
                if tuple(old[n] for n in ('idempotency_key','source_file_id','source_revision','source_digest','intent_root','contract_root','payload_root'))!=sem or old['stable_operation_root']!=op.root: raise ValueError('STABLE_OPERATION_MOVED')
                raise ValueError('FIRST_OPERATION_ALREADY_BOUND')
        return ExecutionPermit(Action.CALL,op.command_id,op.root,lr,a.proof_bound_admission_root,a.parent_attempt_root,er,a.provider_request_count)
    def ambiguous(self,command_id:str,op_root:str):
        R(op_root,'op_root')
        with self.con() as c:
            old=c.execute('SELECT * FROM o15_op WHERE command_id=?',(command_id,)).fetchone()
            if old is None or old['stable_operation_root']!=op_root or old['phase']!='EXPOSED': raise ValueError('AMBIGUITY_DIVERGED')
            c.execute('UPDATE o15_op SET phase=? WHERE command_id=?',('AMBIGUOUS',command_id))
    def retry(self,op:SemanticOperation,lease:WorkcellLease,current:HostCurrent,a:ProofBoundAttempt,recovery_verdict_root:str)->ExecutionPermit:
        self._check_attempt(op,a,Action.RETRY); R(recovery_verdict_root,'recovery_verdict_root'); lr=verify_lease(lease,current,self.lease_key)
        with self.con() as c:
            old=c.execute('SELECT * FROM o15_op WHERE command_id=?',(op.command_id,)).fetchone()
            if old is None or old['phase']!='AMBIGUOUS': raise ValueError('RETRY_REQUIRES_AMBIGUOUS')
            if old['stable_operation_root']!=op.root or tuple(old[n] for n in ('idempotency_key','source_file_id','source_revision','source_digest','intent_root','contract_root','payload_root'))!=self._sem(op): raise ValueError('STABLE_OPERATION_MOVED')
            if a.provider_request_count<=old['provider_request_count']: raise ValueError('RETRY_ATTEMPT_NOT_NEW')
            if a.parent_attempt_root==old['last_attempt_root']: raise ValueError('RETRY_ATTEMPT_ROOT_NOT_NEW')
            er=execution_witness(op.root,lr,a,recovery_verdict_root)
            c.execute('UPDATE o15_op SET phase=?,last_attempt_root=?,last_admission_root=?,last_workcell_root=?,last_execution_root=?,provider_request_count=? WHERE command_id=?',('EXPOSED',a.parent_attempt_root,a.proof_bound_admission_root,lr,er,a.provider_request_count,op.command_id))
        return ExecutionPermit(Action.RETRY,op.command_id,op.root,lr,a.proof_bound_admission_root,a.parent_attempt_root,er,a.provider_request_count)
    def record_result(self,command_id:str,result_root:str):
        R(result_root,'result_root')
        with self.con() as c:
            old=c.execute('SELECT * FROM o15_op WHERE command_id=?',(command_id,)).fetchone()
            if old is None or old['phase']!='EXPOSED': raise ValueError('RESULT_WITHOUT_EXPOSED_OPERATION')
            c.execute('UPDATE o15_op SET phase=?,result_root=? WHERE command_id=?',('RESULT_OBSERVED',result_root,command_id))
    def return_writer_only(self,command_id:str)->Action:
        row=self.status(command_id)
        if row['phase']!='RESULT_OBSERVED' or row['result_root'] is None: raise ValueError('RESULT_NOT_OBSERVED')
        return Action.RETURN

def public_work_handle(lease:WorkcellLease)->dict:
    return {'work_handle':'WK:'+lease.handle[:16]+'…','rule':'Opaque locator only; execution proof is host-private.'}
def public_surface_leaks(obj)->bool:
    b=json.dumps(obj,sort_keys=True).lower(); return any(x in b for x in ('stable_operation_root','proof_bound_admission_root','parent_attempt_root','execution_witness_root','consumer_admission','provider_permit','effect_attempt','lease_root'))
