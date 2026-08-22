from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
import hashlib, json, re, unicodedata
from typing import Any, Mapping, Sequence

WORKER_PRESENCE_SCHEMA = "AURAOS_V9_WORKER_PRESENCE_V1"
WORKER_CENSUS_SCHEMA = "AURAOS_V9_WORKER_CENSUS_V1"
ACTIVITY_OBSERVATION_SCHEMA = "AURAOS_V9_ACTIVITY_OBSERVATION_V1"
SCHEDULER_WORKER_PROJECTION_SCHEMA = "AURAOS_V9_SCHEDULER_WORKER_PROJECTION_V1"
DEFAULT_HEARTBEAT_INTERVAL_MS = 15_000
DEFAULT_LEASE_TTL_MS = 45_000
DEFAULT_RECOVERY_GRACE_MS = 90_000
_MAX = (1 << 53) - 1
_HEX = re.compile(r"^[0-9a-f]{64}$")

class ContractViolation(ValueError): pass

class RuntimePresenceState(str, Enum):
    JOINING="JOINING"; READY="READY"; WORKING="WORKING"; REVIEWING="REVIEWING"
    WAITING="WAITING"; DRAINING="DRAINING"; STALE="STALE"; OFFLINE="OFFLINE"

LIVE_STATES=frozenset({RuntimePresenceState.JOINING,RuntimePresenceState.READY,
 RuntimePresenceState.WORKING,RuntimePresenceState.REVIEWING,
 RuntimePresenceState.WAITING,RuntimePresenceState.DRAINING})

def _s(v: str, f: str) -> str:
    if not isinstance(v,str): raise ContractViolation(f"{f} must be a string")
    v=unicodedata.normalize("NFC",v)
    if not v: raise ContractViolation(f"{f} must be non-empty")
    if any(ord(c)<32 for c in v): raise ContractViolation(f"{f} may not contain control characters")
    return v

def _o(v: str|None, f: str) -> str|None: return None if v is None else _s(v,f)
def _d(v: str,f: str)->str:
    v=_s(v,f)
    if not _HEX.fullmatch(v): raise ContractViolation(f"{f} must be lowercase 64-hex")
    return v
def _n(v:int,f:str,positive=False)->int:
    if isinstance(v,bool) or not isinstance(v,int) or v<0 or v>_MAX or (positive and v==0):
        raise ContractViolation(f"{f} must be {'positive ' if positive else ''}JCS-safe integer")
    return v

def _canon(v:Any)->Any:
    if isinstance(v,str): return unicodedata.normalize("NFC",v)
    if isinstance(v,bool): return v
    if isinstance(v,int): return _n(v,"json integer")
    if isinstance(v,(list,tuple)): return [_canon(x) for x in v]
    if isinstance(v,Mapping):
        out={}
        for k,x in v.items():
            k=_s(k,"json key")
            if k in out: raise ContractViolation("duplicate canonical key")
            out[k]=_canon(x)
        return out
    raise ContractViolation("unsupported canonical JSON value")

def canonical_json_bytes(v:Mapping[str,Any])->bytes:
    return json.dumps(_canon(v),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _hash(domain:str,body:Mapping[str,Any])->str:
    return hashlib.sha256(canonical_json_bytes({"domain_separator":domain,**dict(body)})).hexdigest()

@dataclass(frozen=True)
class WorkerPresenceV1:
    worker_instance_id:str; session_id:str; model:str; provider:str; device_ref:str; runtime_ref:str
    evidence_independence_group:str; state:RuntimePresenceState
    current_work_order_id:str|None; current_claim_id:str|None; logical_position_ref:str|None; topology_profile:str|None
    lease_generation:int; fencing_token_digest:str; heartbeat_seq:int
    joined_at_ms:int; last_seen_at_ms:int; lease_expires_at_ms:int
    capability_profile_digest:str; authority_ceiling_digest:str; currentness_digest:str
    heartbeat_interval_ms:int=DEFAULT_HEARTBEAT_INTERVAL_MS
    lease_ttl_ms:int=DEFAULT_LEASE_TTL_MS
    recovery_grace_ms:int=DEFAULT_RECOVERY_GRACE_MS
    def protected_body(self):
        if not isinstance(self.state,RuntimePresenceState): raise ContractViolation("invalid state")
        joined,last,exp=_n(self.joined_at_ms,"joined"),_n(self.last_seen_at_ms,"last"),_n(self.lease_expires_at_ms,"expiry")
        ttl=_n(self.lease_ttl_ms,"ttl",True)
        if last<joined: raise ContractViolation("last seen precedes join")
        if exp!=last+ttl: raise ContractViolation("lease expiry must equal last_seen + ttl")
        body={"schema":WORKER_PRESENCE_SCHEMA,"worker_instance_id":_s(self.worker_instance_id,"worker"),
          "session_id":_s(self.session_id,"session"),"model":_s(self.model,"model"),"provider":_s(self.provider,"provider"),
          "device_ref":_s(self.device_ref,"device"),"runtime_ref":_s(self.runtime_ref,"runtime"),
          "evidence_independence_group":_s(self.evidence_independence_group,"evidence group"),"state":self.state.value,
          "lease_generation":_n(self.lease_generation,"lease generation",True),"fencing_token_digest":_d(self.fencing_token_digest,"fence"),
          "heartbeat_seq":_n(self.heartbeat_seq,"heartbeat seq"),"joined_at_ms":joined,"last_seen_at_ms":last,"lease_expires_at_ms":exp,
          "heartbeat_interval_ms":_n(self.heartbeat_interval_ms,"heartbeat interval",True),"lease_ttl_ms":ttl,
          "recovery_grace_ms":_n(self.recovery_grace_ms,"recovery grace",True),
          "capability_profile_digest":_d(self.capability_profile_digest,"capability"),"authority_ceiling_digest":_d(self.authority_ceiling_digest,"authority"),
          "currentness_digest":_d(self.currentness_digest,"currentness")}
        for k,v in (("current_work_order_id",self.current_work_order_id),("current_claim_id",self.current_claim_id),
                    ("logical_position_ref",self.logical_position_ref),("topology_profile",self.topology_profile)):
            v=_o(v,k)
            if v is not None: body[k]=v
        return body
    def digest(self): return _hash("AURA::V9::WORKER-PRESENCE::V1",self.protected_body())

@dataclass(frozen=True)
class HeartbeatV1:
    worker_instance_id:str; session_id:str; lease_generation:int; fencing_token_digest:str; heartbeat_seq:int
    requested_state:RuntimePresenceState; current_work_order_id:str|None; current_claim_id:str|None
    logical_position_ref:str|None; topology_profile:str|None
    currentness_digest:str; authority_ceiling_digest:str; worker_reported_at_ms:int
    def validate(self):
        if self.requested_state in (RuntimePresenceState.STALE,RuntimePresenceState.OFFLINE):
            raise ContractViolation("heartbeat cannot self-assert stale/offline")
        _s(self.worker_instance_id,"worker"); _s(self.session_id,"session"); _n(self.lease_generation,"generation",True)
        _d(self.fencing_token_digest,"fence"); _n(self.heartbeat_seq,"sequence",True); _n(self.worker_reported_at_ms,"reported time")
        _d(self.currentness_digest,"currentness"); _d(self.authority_ceiling_digest,"authority")
        _o(self.current_claim_id,"claim"); _o(self.current_work_order_id,"work order")
        return self

@dataclass(frozen=True)
class ActivityObservationV1:
    worker_instance_id:str; session_id:str; observed_at_ms:int; evidence_ref:str
    def protected_body(self):
        return {"schema":ACTIVITY_OBSERVATION_SCHEMA,"observation_kind":"ACTIVITY_OBSERVED",
                "worker_instance_id":_s(self.worker_instance_id,"worker"),"session_id":_s(self.session_id,"session"),
                "observed_at_ms":_n(self.observed_at_ms,"observed"),"evidence_ref":_s(self.evidence_ref,"evidence")}

@dataclass(frozen=True)
class ReapDecisionV1:
    state:RuntimePresenceState; retire_fence:bool; release_claim:bool; requires_rejoin:bool

@dataclass(frozen=True)
class WorkerCensusV1:
    observed_at_ms:int; total_registered:int; live_count:int; working_count:int; reviewing_count:int
    waiting_count:int; ready_count:int; stale_count:int; offline_count:int; utilization_basis_points:int
    live_by_provider:tuple[tuple[str,int],...]; live_by_model:tuple[tuple[str,int],...]
    working_by_work_order:tuple[tuple[str,int],...]; live_by_topology:tuple[tuple[str,int],...]
    worker_presence_digests:tuple[str,...]
    def protected_body(self):
        return {"schema":WORKER_CENSUS_SCHEMA,"observed_at_ms":self.observed_at_ms,"total_registered":self.total_registered,
          "live_count":self.live_count,"working_count":self.working_count,"reviewing_count":self.reviewing_count,
          "waiting_count":self.waiting_count,"ready_count":self.ready_count,"stale_count":self.stale_count,
          "offline_count":self.offline_count,"utilization_basis_points":self.utilization_basis_points,
          "live_by_provider":[list(x) for x in self.live_by_provider],"live_by_model":[list(x) for x in self.live_by_model],
          "working_by_work_order":[list(x) for x in self.working_by_work_order],"live_by_topology":[list(x) for x in self.live_by_topology],
          "worker_presence_digests":list(self.worker_presence_digests)}
    def digest(self): return _hash("AURA::V9::WORKER-CENSUS::V1",self.protected_body())

def join_runtime_worker(*,worker_instance_id,session_id,model,provider,device_ref,runtime_ref,evidence_independence_group,
    lease_generation,fencing_token_digest,received_at_ms,capability_profile_digest,authority_ceiling_digest,currentness_digest,
    heartbeat_interval_ms=DEFAULT_HEARTBEAT_INTERVAL_MS,lease_ttl_ms=DEFAULT_LEASE_TTL_MS,recovery_grace_ms=DEFAULT_RECOVERY_GRACE_MS):
    t=_n(received_at_ms,"received"); ttl=_n(lease_ttl_ms,"ttl",True)
    p=WorkerPresenceV1(worker_instance_id,session_id,model,provider,device_ref,runtime_ref,evidence_independence_group,
      RuntimePresenceState.READY,None,None,None,None,lease_generation,fencing_token_digest,0,t,t,t+ttl,
      capability_profile_digest,authority_ceiling_digest,currentness_digest,heartbeat_interval_ms,ttl,recovery_grace_ms)
    p.protected_body(); return p

def effective_state(p:WorkerPresenceV1,*,now_ms:int):
    p.protected_body(); now=_n(now_ms,"now")
    if p.state is RuntimePresenceState.OFFLINE:return p.state
    if now<=p.lease_expires_at_ms:return p.state
    if now<=p.lease_expires_at_ms+p.recovery_grace_ms:return RuntimePresenceState.STALE
    return RuntimePresenceState.OFFLINE

def runtime_live(record:WorkerPresenceV1|ActivityObservationV1,*,now_ms:int)->bool:
    return isinstance(record,WorkerPresenceV1) and effective_state(record,now_ms=now_ms) in LIVE_STATES

def accept_heartbeat(current:WorkerPresenceV1,hb:HeartbeatV1,*,received_at_ms:int,expected_claim_id:str|None,
                     expected_currentness_digest:str,expected_authority_ceiling_digest:str):
    current.protected_body(); hb.validate(); t=_n(received_at_ms,"received")
    if t>current.lease_expires_at_ms: raise ContractViolation("lease expired; rejoin required")
    if t<current.last_seen_at_ms: raise ContractViolation("receive time regressed")
    checks=((hb.worker_instance_id,current.worker_instance_id,"worker mismatch"),(hb.session_id,current.session_id,"session mismatch"),
            (hb.lease_generation,current.lease_generation,"lease generation mismatch"),(hb.fencing_token_digest,current.fencing_token_digest,"fence mismatch"))
    for a,b,msg in checks:
        if a!=b: raise ContractViolation(msg)
    if hb.heartbeat_seq<=current.heartbeat_seq: raise ContractViolation("heartbeat sequence must strictly increase")
    if _o(hb.current_claim_id,"claim")!=_o(expected_claim_id,"expected claim"): raise ContractViolation("claim mismatch")
    if hb.currentness_digest!=_d(expected_currentness_digest,"expected currentness"): raise ContractViolation("currentness mismatch")
    if hb.authority_ceiling_digest!=_d(expected_authority_ceiling_digest,"expected authority"): raise ContractViolation("authority mismatch")
    out=replace(current,state=hb.requested_state,current_work_order_id=hb.current_work_order_id,current_claim_id=hb.current_claim_id,
      logical_position_ref=hb.logical_position_ref,topology_profile=hb.topology_profile,heartbeat_seq=hb.heartbeat_seq,
      last_seen_at_ms=t,lease_expires_at_ms=t+current.lease_ttl_ms,currentness_digest=hb.currentness_digest,
      authority_ceiling_digest=hb.authority_ceiling_digest)
    out.protected_body(); return out

def reap_presence(p:WorkerPresenceV1,*,now_ms:int):
    s=effective_state(p,now_ms=now_ms)
    if s is RuntimePresenceState.OFFLINE:return ReapDecisionV1(s,True,p.current_claim_id is not None,True)
    return ReapDecisionV1(s,False,False,False)

def rejoin_runtime_worker(previous:WorkerPresenceV1,*,session_id,lease_generation,fencing_token_digest,received_at_ms,
                          authority_ceiling_digest,currentness_digest):
    if not reap_presence(previous,now_ms=received_at_ms).requires_rejoin: raise ContractViolation("prior lease is not offline")
    if _n(lease_generation,"generation",True)<=previous.lease_generation: raise ContractViolation("generation must strictly increase")
    if _d(fencing_token_digest,"fence")==previous.fencing_token_digest: raise ContractViolation("new fencing token required")
    return join_runtime_worker(worker_instance_id=previous.worker_instance_id,session_id=session_id,model=previous.model,
      provider=previous.provider,device_ref=previous.device_ref,runtime_ref=previous.runtime_ref,
      evidence_independence_group=previous.evidence_independence_group,lease_generation=lease_generation,
      fencing_token_digest=fencing_token_digest,received_at_ms=received_at_ms,
      capability_profile_digest=previous.capability_profile_digest,authority_ceiling_digest=authority_ceiling_digest,
      currentness_digest=currentness_digest,heartbeat_interval_ms=previous.heartbeat_interval_ms,
      lease_ttl_ms=previous.lease_ttl_ms,recovery_grace_ms=previous.recovery_grace_ms)

def _pairs(d): return tuple(sorted(d.items(),key=lambda x:x[0].encode()))
def build_worker_census(presences:Sequence[WorkerPresenceV1],*,now_ms:int):
    seen=set(); c={s:0 for s in RuntimePresenceState}; prov={}; models={}; wo={}; topo={}; digs=[]
    def inc(d,k):
        if k is not None:d[k]=d.get(k,0)+1
    for p in presences:
        if p.worker_instance_id in seen: raise ContractViolation("duplicate worker_instance_id")
        seen.add(p.worker_instance_id); digs.append(p.digest()); s=effective_state(p,now_ms=now_ms); c[s]+=1
        if s in LIVE_STATES:inc(prov,p.provider);inc(models,p.model);inc(topo,p.topology_profile)
        if s is RuntimePresenceState.WORKING:inc(wo,p.current_work_order_id)
    live=sum(c[s] for s in LIVE_STATES); work=c[RuntimePresenceState.WORKING]
    return WorkerCensusV1(_n(now_ms,"now"),len(presences),live,work,c[RuntimePresenceState.REVIEWING],
      c[RuntimePresenceState.WAITING],c[RuntimePresenceState.READY],c[RuntimePresenceState.STALE],
      c[RuntimePresenceState.OFFLINE],0 if not live else work*10000//live,_pairs(prov),_pairs(models),_pairs(wo),_pairs(topo),tuple(sorted(digs)))

def scheduler_worker_projection(presences:Sequence[WorkerPresenceV1],*,now_ms:int):
    live=[p for p in presences if runtime_live(p,now_ms=now_ms)]
    return {"schema":SCHEDULER_WORKER_PROJECTION_SCHEMA,"active_worker_count":len(live),
      "logical_position_refs":sorted({p.logical_position_ref for p in live if p.logical_position_ref}),
      "capability_profile_refs":sorted({p.capability_profile_digest for p in live}),
      "evidence_independence_groups":sorted({p.evidence_independence_group for p in live})}
