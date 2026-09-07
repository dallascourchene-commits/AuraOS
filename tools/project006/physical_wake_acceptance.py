from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib,json,sqlite3
from pathlib import Path

HEX=set('0123456789abcdef')
class WitnessError(ValueError): pass
class EventKind(str,Enum):
    WINDOWS_GUARDIAN_ALIVE='WINDOWS_GUARDIAN_ALIVE'
    WSL_STOP_OBSERVED='WSL_STOP_OBSERVED'
    WSL_RESTART_OBSERVED='WSL_RESTART_OBSERVED'
    COMMAND_INGESTED='COMMAND_INGESTED'
    COMMAND_CONSUMED='COMMAND_CONSUMED'
    OUTBOUND_RETURN_WRITTEN='OUTBOUND_RETURN_WRITTEN'
    REPLAY_ATTEMPTED='REPLAY_ATTEMPTED'
    REPLAY_NO_DUPLICATE_EFFECT='REPLAY_NO_DUPLICATE_EFFECT'

REQUIRED_KINDS=tuple(EventKind)

def _root(obj)->str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),default=lambda x:x.value if isinstance(x,Enum) else x.__dict__).encode()).hexdigest()
def _hex64(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX

@dataclass(frozen=True)
class AcceptanceContract:
    test_id:str
    command_id:str
    currentness_root:str
    authority_root:str
    expected_provider_request_count:int
    expected_sequence_ids:tuple[str,...]=tuple(str(i) for i in range(8))
    def validate(self):
        if not self.test_id or not self.command_id: raise WitnessError('SCOPE_INVALID')
        if not _hex64(self.currentness_root) or not _hex64(self.authority_root): raise WitnessError('ROOT_INVALID')
        if not isinstance(self.expected_provider_request_count,int) or self.expected_provider_request_count<0: raise WitnessError('PROVIDER_COUNT_INVALID')
        if len(self.expected_sequence_ids)!=8 or len(set(self.expected_sequence_ids))!=8: raise WitnessError('COVERAGE_CONTRACT_INVALID')

@dataclass(frozen=True)
class WakeEvent:
    test_id:str; command_id:str; sequence_id:str; kind:EventKind; evidence_root:str; observed_at_ms:int
    def validate(self):
        if not self.test_id or not self.command_id or not self.sequence_id: raise WitnessError('EVENT_SCOPE_INVALID')
        if not _hex64(self.evidence_root): raise WitnessError('EVIDENCE_ROOT_INVALID')
        if not isinstance(self.observed_at_ms,int) or self.observed_at_ms<0: raise WitnessError('TIME_INVALID')
    @property
    def event_root(self): return _root(self)

class WakeAcceptanceLedger:
    def __init__(self,path:str):
        self.path=path; Path(path).parent.mkdir(parents=True,exist_ok=True)
        c=sqlite3.connect(path)
        try:
            c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL')
            c.execute('CREATE TABLE IF NOT EXISTS events(test_id TEXT, command_id TEXT, sequence_id TEXT, kind TEXT, evidence_root TEXT, observed_at_ms INTEGER, event_root TEXT, PRIMARY KEY(test_id,command_id,sequence_id))')
            c.commit()
        finally:c.close()
    def append(self,e:WakeEvent)->str:
        e.validate(); c=sqlite3.connect(self.path)
        try:
            row=c.execute('SELECT kind,evidence_root,observed_at_ms,event_root FROM events WHERE test_id=? AND command_id=? AND sequence_id=?',(e.test_id,e.command_id,e.sequence_id)).fetchone()
            if row:
                if row==(e.kind.value,e.evidence_root,e.observed_at_ms,e.event_root): return 'DUPLICATE_COLLAPSED'
                raise WitnessError('SEQUENCE_EQUIVOCATION')
            c.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',(e.test_id,e.command_id,e.sequence_id,e.kind.value,e.evidence_root,e.observed_at_ms,e.event_root)); c.commit(); return 'APPENDED'
        finally:c.close()
    def projection(self,contract:AcceptanceContract):
        contract.validate(); c=sqlite3.connect(self.path)
        try:
            rows=c.execute('SELECT sequence_id,kind,evidence_root,observed_at_ms,event_root FROM events WHERE test_id=? AND command_id=?',(contract.test_id,contract.command_id)).fetchall()
        finally:c.close()
        return sorted(rows,key=lambda r:contract.expected_sequence_ids.index(r[0]) if r[0] in contract.expected_sequence_ids else 999)
    def evaluate(self,contract:AcceptanceContract,provider_request_count:int,currentness_root:str,authority_root:str):
        contract.validate(); rows=self.projection(contract)
        seqs={r[0] for r in rows}; expected=set(contract.expected_sequence_ids)
        reasons=[]
        if seqs!=expected: reasons.append('COVERAGE_INCOMPLETE' if seqs<expected else 'COVERAGE_MISMATCH')
        if len(rows)==8:
            kinds=[r[1] for r in rows]
            if kinds!=[k.value for k in REQUIRED_KINDS]: reasons.append('EVENT_KIND_SEQUENCE_MISMATCH')
            times=[r[3] for r in rows]
            if times!=sorted(times): reasons.append('CAUSAL_TIME_ORDER_MISMATCH')
        if provider_request_count!=contract.expected_provider_request_count: reasons.append('PROVIDER_COUNT_MISMATCH')
        if currentness_root!=contract.currentness_root: reasons.append('CURRENTNESS_MOVED')
        if authority_root!=contract.authority_root: reasons.append('AUTHORITY_MOVED')
        return {'accepted':not reasons,'disposition':'PHYSICAL_WAKE_ACCEPTED' if not reasons else 'HOLD_PHYSICAL_WAKE','reasons':reasons,'coverage_complete':seqs==expected,'ledger_root':_root(rows),'observed_sequences':sorted(seqs),'expected_sequences':list(contract.expected_sequence_ids)}
