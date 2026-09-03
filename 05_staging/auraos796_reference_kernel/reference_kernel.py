from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

EVENT_TYPES = {
    "CHECKIN", "CHECKOUT", "WORK_START", "WORK_STATE", "CLAIM", "CHECKPOINT",
    "RESULT", "REVIEW", "WAIT", "STALE", "OFFLINE", "REBIND", "DRIVE_OBSERVATION",
    "GITHUB_OBSERVATION", "EXTERNAL_GROUNDING", "CURRENTNESS_INVALIDATION",
    "ARENA_OPEN", "ARENA_CLOSE", "RECONCILIATION",
}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def semantic_payload_root(payload: Mapping[str, object]) -> str:
    """Meaning fingerprint independent of transport position."""
    explicit = payload.get("semantic_root")
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit:
            raise ValueError("INVALID_SEMANTIC_ROOT")
        return explicit
    semantic = {k: v for k, v in payload.items() if k not in {"source_sequence", "semantic_root"}}
    return digest(semantic)


@dataclass(frozen=True)
class SourceCursor3D:
    source_sequence: int
    provider_generation: str
    semantic_root: str

    def validate(self) -> None:
        if self.source_sequence < 0:
            raise ValueError("INVALID_SOURCE_SEQUENCE")
        if not self.provider_generation or not self.semantic_root:
            raise ValueError("SOURCE_CURSOR_BINDING_REQUIRED")


def classify_source_cursor_transition(prior: SourceCursor3D, observed: SourceCursor3D) -> str:
    prior.validate(); observed.validate()
    if observed.source_sequence < prior.source_sequence:
        return "HISTORICAL_RECEIPT_ONLY"
    if observed.source_sequence == prior.source_sequence:
        if observed.semantic_root != prior.semantic_root:
            return "SOURCE_POSITION_SEMANTIC_CONFLICT"
        if observed.provider_generation != prior.provider_generation:
            return "CURRENTNESS_REBIND_ONLY"
        return "EXACT_REPLAY_NOOP"
    if observed.semantic_root == prior.semantic_root:
        return "CURSOR_ADVANCE_NO_SEMANTIC_WAKE"
    return "SEMANTIC_ADVANCE"


@dataclass(frozen=True)
class OwnerRef:
    provider: str
    repository: str
    object_kind: str
    ordinal: int

    def validate(self) -> None:
        if self.provider != "github": raise ValueError("UNSUPPORTED_PROVIDER")
        if not self.repository or "/" not in self.repository: raise ValueError("REPOSITORY_REQUIRED")
        if self.object_kind not in {"issue", "pull"}: raise ValueError("OBJECT_KIND_REQUIRED")
        if self.ordinal <= 0: raise ValueError("INVALID_ORDINAL")

    @property
    def canonical(self) -> str:
        self.validate()
        return f"github://{self.repository}/{self.object_kind}/{self.ordinal}"


@dataclass(frozen=True)
class EvidenceLease:
    source_ref: str
    provider_revision: str
    semantic_root: str
    producer: str

    def validate(self) -> None:
        if not all((self.source_ref, self.provider_revision, self.semantic_root, self.producer)):
            raise ValueError("LEASE_BINDING_REQUIRED")

    @property
    def identity(self) -> str:
        self.validate(); return digest(asdict(self))


@dataclass(frozen=True)
class JSpaceEvent:
    event_id: str
    event_type: str
    jid: int
    visit_id: str
    source_ref: str
    source_generation: str
    owner_epoch: str
    subject: str
    payload: dict
    recorded_at_ns: int
    effect_authority: bool = False
    gate10: bool = False

    def validate(self) -> None:
        if self.event_type not in EVENT_TYPES: raise ValueError("UNKNOWN_EVENT_TYPE")
        if not all((self.event_id, self.visit_id, self.source_ref, self.source_generation, self.owner_epoch, self.subject)):
            raise ValueError("MISSING_BINDING")
        if self.effect_authority or self.gate10: raise ValueError("AUTHORITY_WIDENING")
        if self.jid <= 0: raise ValueError("INVALID_JID")
        source_sequence = self.payload.get("source_sequence")
        if source_sequence is not None and (not isinstance(source_sequence, int) or source_sequence < 0):
            raise ValueError("INVALID_SOURCE_SEQUENCE")
        current = self.payload.get("current")
        if current is not None and not isinstance(current, bool):
            raise ValueError("INVALID_SOURCE_CURRENTNESS")
        semantic_payload_root(self.payload)

    @property
    def payload_digest(self) -> str: return digest(self.payload)

    @property
    def semantic_root(self) -> str: return semantic_payload_root(self.payload)


class JSpaceStore:
    def __init__(self, path: str | Path): self.path = str(path); self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL"); conn.execute("PRAGMA synchronous=FULL")
        return conn

    def _init(self) -> None:
        conn = self.connect()
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS allocator(id INTEGER PRIMARY KEY CHECK(id=1), next_jid INTEGER NOT NULL, epoch INTEGER NOT NULL);
        INSERT OR IGNORE INTO allocator(id,next_jid,epoch) VALUES(1,1,1);
        CREATE TABLE IF NOT EXISTS events(
          seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,event_type TEXT NOT NULL,
          jid INTEGER NOT NULL,visit_id TEXT NOT NULL,source_ref TEXT NOT NULL,source_generation TEXT NOT NULL,
          owner_epoch TEXT NOT NULL,subject TEXT NOT NULL,payload_json TEXT NOT NULL,payload_digest TEXT NOT NULL,
          recorded_at_ns INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS events_jid_seq ON events(jid,seq);
        CREATE TABLE IF NOT EXISTS deps(src TEXT NOT NULL,dst TEXT NOT NULL,kind TEXT NOT NULL,PRIMARY KEY(src,dst,kind));
        """)
        conn.close()

    def allocate_jid(self) -> tuple[int, int]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            jid, epoch = conn.execute("SELECT next_jid,epoch FROM allocator WHERE id=1").fetchone()
            conn.execute("UPDATE allocator SET next_jid=?,epoch=? WHERE id=1", (jid + 1, epoch + 1))
            conn.execute("COMMIT"); return jid, epoch
        except Exception:
            conn.execute("ROLLBACK"); raise
        finally: conn.close()

    def append(self, event: JSpaceEvent) -> tuple[str, int]:
        event.validate(); conn = self.connect()
        payload_json = json.dumps(event.payload, sort_keys=True, separators=(",", ":"))
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT seq,event_type,jid,visit_id,source_ref,source_generation,owner_epoch,subject,payload_digest FROM events WHERE event_id=?",
                (event.event_id,),).fetchone()
            semantic = (event.event_type,event.jid,event.visit_id,event.source_ref,event.source_generation,event.owner_epoch,event.subject,event.payload_digest)
            if row:
                if tuple(row[1:]) != semantic: raise ValueError("CONFLICTING_EVENT_REPLAY")
                conn.execute("COMMIT"); return "DUPLICATE_COLLAPSED", row[0]
            cur = conn.execute(
                "INSERT INTO events(event_id,event_type,jid,visit_id,source_ref,source_generation,owner_epoch,subject,payload_json,payload_digest,recorded_at_ns) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (event.event_id,event.event_type,event.jid,event.visit_id,event.source_ref,event.source_generation,event.owner_epoch,event.subject,payload_json,event.payload_digest,event.recorded_at_ns),)
            conn.execute("COMMIT"); return "APPENDED", cur.lastrowid
        except Exception:
            conn.execute("ROLLBACK"); raise
        finally: conn.close()

    def add_dep(self, src: str, dst: str, kind: str = "CONSEQUENCE") -> None:
        conn = self.connect(); conn.execute("INSERT OR IGNORE INTO deps(src,dst,kind) VALUES(?,?,?)", (src,dst,kind)); conn.close()

    def affected_cone(self, changed: Iterable[str]) -> set[str]:
        conn = self.connect(); adjacency: dict[str,set[str]] = {}
        for src,dst,_ in conn.execute("SELECT src,dst,kind FROM deps"): adjacency.setdefault(src,set()).add(dst)
        conn.close(); out=set(changed); stack=list(out)
        while stack:
            node=stack.pop()
            for child in adjacency.get(node,()):
                if child not in out: out.add(child); stack.append(child)
        return out

    def events(self) -> list[tuple]:
        conn=self.connect(); rows=conn.execute(
            "SELECT seq,event_id,event_type,jid,visit_id,source_ref,source_generation,owner_epoch,subject,payload_json,recorded_at_ns FROM events ORDER BY seq").fetchall()
        conn.close(); return rows

    def project(self) -> dict[int, dict]:
        projection: dict[int,dict] = {}
        applied: dict[tuple[int,str,str],SourceCursor3D] = {}
        for seq,_,event_type,jid,visit,source,generation,_,subject,payload_json,_ in self.events():
            state=projection.setdefault(jid,{"jid":jid,"visit_id":visit,"status":"UNKNOWN","objective":None,"last_seq":0,
                "sources":{},"authority_effect":False,"runtime_liveness":"UNKNOWN","source_sequences":{},"source_cursors":{},"source_currentness":{}})
            payload=json.loads(payload_json); stream=(jid,source,subject); source_sequence=payload.get("source_sequence")
            apply_semantics=True
            key=f"{source}|{subject}"
            if source_sequence is not None:
                observed=SourceCursor3D(source_sequence,generation,semantic_payload_root(payload)); observed.validate()
                prior=applied.get(stream)
                if prior is not None:
                    transition=classify_source_cursor_transition(prior,observed)
                    if transition=="SOURCE_POSITION_SEMANTIC_CONFLICT": raise ValueError("SOURCE_SEQUENCE_CONFLICT")
                    if transition=="HISTORICAL_RECEIPT_ONLY":
                        state["last_seq"]=max(state["last_seq"],seq); continue
                    if transition in {"EXACT_REPLAY_NOOP","CURRENTNESS_REBIND_ONLY","CURSOR_ADVANCE_NO_SEMANTIC_WAKE"}:
                        apply_semantics=False
                applied[stream]=observed
                state["source_sequences"][key]=source_sequence
                state["source_cursors"][key]={"source_sequence":source_sequence,"provider_generation":generation,"semantic_root":observed.semantic_root}
            if "current" in payload:
                state["source_currentness"][key]=payload["current"]
            state["visit_id"]=visit; state["last_seq"]=max(state["last_seq"],seq); state["sources"][source]=generation
            if apply_semantics:
                if event_type=="CHECKIN": state["status"]="READY"
                elif event_type in {"WORK_START","WORK_STATE"}: state["status"]=payload.get("status","WORKING")
                elif event_type=="WAIT": state["status"]="WAITING"
                elif event_type=="STALE": state["status"]="STALE"
                elif event_type=="OFFLINE": state["status"]="OFFLINE"
                elif event_type=="CHECKOUT": state["status"]="DECOMMISSIONED"
                if "objective" in payload: state["objective"]=payload["objective"]
            state["authority_effect"]=False; state["runtime_liveness"]="UNKNOWN"
        return projection


@dataclass(frozen=True)
class FrontierDecision:
    disposition: str; affected: tuple[str,...]; hydrate: tuple[str,...]; cold_preserved: tuple[str,...]; reason: str; effect_authority: bool=False


class WakeReducer:
    def __init__(self, store:JSpaceStore): self.store=store
    def decide(self,changed:set[str],capability_nodes:set[str],deterministically_closed:set[str],all_nodes:set[str])->FrontierDecision:
        if not changed: return FrontierDecision("NOOP",(),(),tuple(sorted(all_nodes)),"NO_MATERIAL_DELTA")
        cone=self.store.affected_cone(changed); unresolved=cone-deterministically_closed
        hydrate=tuple(sorted(x for x in unresolved if x in capability_nodes or x in changed)); cold=tuple(sorted(all_nodes-cone))
        if not unresolved: return FrontierDecision("CLOSED_DETERMINISTIC",tuple(sorted(cone)),(),cold,"ALL_AFFECTED_CLOSED")
        return FrontierDecision("WAKE_UNRESOLVED_CONSEQUENCE",tuple(sorted(cone)),hydrate,cold,"UNRESOLVED_CONSEQUENCE_REMAINS")


@dataclass(frozen=True)
class LeaseDecision:
    disposition:str; changed_sources:tuple[str,...]; affected:tuple[str,...]; reusable:tuple[str,...]; effect_authority:bool=False


class EvidenceLeaseGate:
    def __init__(self,store:JSpaceStore,bindings:Mapping[str,EvidenceLease]):
        self.store=store; self.bindings=dict(bindings)
        for lease in self.bindings.values(): lease.validate()
    def compare(self,observed:Mapping[str,EvidenceLease],all_nodes:set[str])->LeaseDecision:
        changed:set[str]=set()
        for source,expected in self.bindings.items():
            actual=observed.get(source)
            if actual is None: changed.add(source)
            else:
                actual.validate()
                if actual.identity!=expected.identity: changed.add(source)
        if not changed: return LeaseDecision("CURRENT_PLANNING_CANDIDATE",(),(),tuple(sorted(all_nodes)))
        cone=self.store.affected_cone(changed)
        return LeaseDecision("HOLD_REVALIDATE_SOURCE",tuple(sorted(changed)),tuple(sorted(cone)),tuple(sorted(all_nodes-cone)))


@dataclass(frozen=True)
class SourceState:
    source_ref:str; generation:str; current:bool=True; source_sequence:int|None=None; semantic_root:str|None=None

    def resolved_semantic_root(self)->str:
        if self.semantic_root is not None:
            if not self.semantic_root: raise ValueError("INVALID_SEMANTIC_ROOT")
            return self.semantic_root
        return digest({"source_ref":self.source_ref,"generation":self.generation,"current":self.current})


@dataclass(frozen=True)
class ReconcileReceipt:
    disposition:str; changed_sources:tuple[str,...]; appended_events:tuple[str,...]; affected:tuple[str,...]; hydrate:tuple[str,...]; cold_preserved:tuple[str,...]; witness_digest:str
    rebound_sources:tuple[str,...]=(); cursor_advanced_sources:tuple[str,...]=(); effect_authority:bool=False


class ReconcileEngine:
    def __init__(self,store:JSpaceStore,*,jid:int,visit_id:str,owner_epoch:str): self.store,self.jid,self.visit_id,self.owner_epoch=store,jid,visit_id,owner_epoch

    def _projected_source_state(self)->tuple[dict[str,SourceCursor3D],dict[str,bool],int]:
        projected=self.store.project().get(self.jid,{})
        cursors:dict[str,SourceCursor3D]={}; currentness:dict[str,bool]={}
        for key,cursor in projected.get("source_cursors",{}).items():
            source,subject=key.split("|",1)
            if source==subject:
                cursors[source]=SourceCursor3D(cursor["source_sequence"],cursor["provider_generation"],cursor["semantic_root"])
        for key,current in projected.get("source_currentness",{}).items():
            source,subject=key.split("|",1)
            if source==subject:
                currentness[source]=bool(current)
        return cursors,currentness,int(projected.get("last_seq",0))

    def reconcile(self,snapshots:Iterable[SourceState],*,all_nodes:set[str],capability_nodes:set[str],deterministic_closed:set[str]=frozenset())->ReconcileReceipt:
        prior,prior_currentness,event_epoch=self._projected_source_state(); changed=[]; appended=[]; rebound=[]; cursor_advanced=[]
        for snapshot in sorted(snapshots,key=lambda item:item.source_ref):
            if not snapshot.source_ref or not snapshot.generation: raise ValueError("SOURCE_BINDING_REQUIRED")
            root=snapshot.resolved_semantic_root(); before=prior.get(snapshot.source_ref); currentness_known=snapshot.source_ref in prior_currentness; before_current=prior_currentness.get(snapshot.source_ref)
            transition="SEMANTIC_ADVANCE"
            if before is not None and snapshot.source_sequence is not None:
                observed=SourceCursor3D(snapshot.source_sequence,snapshot.generation,root)
                transition=classify_source_cursor_transition(before,observed)
                if transition=="HISTORICAL_RECEIPT_ONLY": continue
                if transition=="SOURCE_POSITION_SEMANTIC_CONFLICT": raise ValueError("SOURCE_SEQUENCE_CONFLICT")
                if transition=="EXACT_REPLAY_NOOP" and currentness_known and snapshot.current==before_current: continue
            elif before is not None and snapshot.source_sequence is None:
                same_cursor_identity=before.provider_generation==snapshot.generation and before.semantic_root==root
                if same_cursor_identity and currentness_known and snapshot.current==before_current: continue
                transition="SEMANTIC_ADVANCE" if before.semantic_root!=root else "CURRENTNESS_REBIND_ONLY"

            currentness_changed=(currentness_known and snapshot.current!=before_current) or (before is not None and not currentness_known and not snapshot.current)
            material_changed=transition=="SEMANTIC_ADVANCE" or currentness_changed
            if transition=="CURRENTNESS_REBIND_ONLY" and snapshot.current: rebound.append(snapshot.source_ref)
            if transition=="CURSOR_ADVANCE_NO_SEMANTIC_WAKE" and snapshot.current: cursor_advanced.append(snapshot.source_ref)
            if material_changed: changed.append(snapshot.source_ref)
            payload={"observed_generation":snapshot.generation,"current":snapshot.current,"semantic_root":root}
            if snapshot.source_sequence is not None: payload["source_sequence"]=snapshot.source_sequence
            event_type="RECONCILIATION" if snapshot.current else "CURRENTNESS_INVALIDATION"
            event_id="reconcile:"+hashlib.sha256(f"{self.jid}|{snapshot.source_ref}|{snapshot.generation}|{snapshot.current}|{snapshot.source_sequence}|{root}|{event_epoch}".encode()).hexdigest()
            event=JSpaceEvent(event_id,event_type,self.jid,self.visit_id,snapshot.source_ref,snapshot.generation,self.owner_epoch,snapshot.source_ref,payload,time.time_ns())
            disposition,event_seq=self.store.append(event)
            if disposition=="APPENDED":
                appended.append(event_id); event_epoch=max(event_epoch,event_seq)
            if snapshot.source_sequence is not None:
                prior[snapshot.source_ref]=SourceCursor3D(snapshot.source_sequence,snapshot.generation,root)
            prior_currentness[snapshot.source_ref]=snapshot.current

        decision=WakeReducer(self.store).decide(set(changed),capability_nodes,set(deterministic_closed),set(all_nodes))
        if changed:
            disposition="RECONCILED_CLOSED" if decision.disposition=="CLOSED_DETERMINISTIC" else "RECONCILED_RESIDUAL"
        elif appended:
            disposition="RECONCILED_CURRENTNESS_ONLY"
        else:
            disposition="NOOP_SOURCE_SNAPSHOT"
        body={"disposition":disposition,"changed_sources":sorted(changed),"appended_events":sorted(appended),"affected":decision.affected,"hydrate":decision.hydrate,"cold_preserved":decision.cold_preserved,"rebound_sources":sorted(rebound),"cursor_advanced_sources":sorted(cursor_advanced)}
        return ReconcileReceipt(disposition,tuple(sorted(changed)),tuple(sorted(appended)),decision.affected,decision.hydrate,decision.cold_preserved,digest(body),tuple(sorted(rebound)),tuple(sorted(cursor_advanced)))


@dataclass(frozen=True)
class WorkflowObservation:
    owner:OwnerRef; run_id:int; name:str; head_sha:str; actor:str; status:str; conclusion:str|None; job_count:int


class GitHubObservationNormalizer:
    def workflow(self,observation:WorkflowObservation)->dict:
        observation.owner.validate(); semantic_failure=False; pre_job=False; admission="UNKNOWN"
        if observation.status=="completed" and observation.conclusion=="action_required" and observation.job_count==0: pre_job,admission=True,"PRE_JOB_ACTION_REQUIRED"
        elif observation.job_count>0 and observation.conclusion=="failure": semantic_failure,admission=True,"JOBS_EXECUTED_FAILURE"
        elif observation.job_count>0 and observation.conclusion=="success": admission="JOBS_EXECUTED_SUCCESS"
        elif observation.status in {"queued","in_progress"}: admission="IN_FLIGHT"
        return {"kind":"WORKFLOW_OBSERVATION","owner_ref":observation.owner.canonical,"run_id":observation.run_id,"name":observation.name,"head_sha":observation.head_sha,"actor":observation.actor,"job_count":observation.job_count,"admission_state":admission,"semantic_test_failure_proven":semantic_failure,"pre_job_gate_observed":pre_job,"effect_authority":False,"digest":digest(asdict(observation))}


@dataclass(frozen=True)
class JoinContext:
    protocol_root:str; intent_root:str; current_branch_head:str|None; active_residual:str|None; affected_neighborhood:tuple[str,...]; current_sources:tuple[tuple[str,str],...]; next_obligation:str|None; packet_digest:str; effect_authority:bool=False


class JoinContextCompiler:
    def compile(self,*,store:JSpaceStore,jid:int,protocol_root:str,intent_root:str,current_branch_head:str|None,active_residual:str|None,affected:Iterable[str],required_sources:Iterable[str],next_obligation:str|None,max_affected:int=25)->JoinContext:
        if not protocol_root or not intent_root: raise ValueError("ROOT_BINDING_REQUIRED")
        affected_sorted=tuple(sorted(set(affected)))
        if len(affected_sorted)>max_affected: raise ValueError("AFFECTED_NEIGHBORHOOD_TOO_BROAD")
        projected=store.project().get(jid,{}); sources=projected.get("sources",{}); inactive=set()
        for key,currentness in projected.get("source_currentness",{}).items():
            source,subject=key.split("|",1)
            if source==subject and currentness is False: inactive.add(source)
        current=tuple(sorted((source,sources[source]) for source in set(required_sources) if source in sources and source not in inactive))
        body={"protocol_root":protocol_root,"intent_root":intent_root,"current_branch_head":current_branch_head,"active_residual":active_residual,"affected_neighborhood":affected_sorted,"current_sources":current,"next_obligation":next_obligation}
        return JoinContext(protocol_root,intent_root,current_branch_head,active_residual,affected_sorted,current,next_obligation,digest(body))
