from __future__ import annotations

import hashlib, json, os, threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

RECEIPT_SCHEMA="AuraHostExecutionReceiptV1"; PROJECTION_SCHEMA="AuraHostReceiptProjectionV1"
IDENTITY_SCHEMA="AuraHostChildExecutionIdentityV1"; PLAN_SCHEMA="AuraHostExecutionPlanV1"
ELIGIBLE_STATES=frozenset({"COMMITTED","RECONCILED"})
IDENTITY_FIELDS=("command_id","idempotency_key","command_digest","parent_payload_digest","plan_digest","manifest_digest","attempt_id","fanout_id","worker_id","role_id","role_instance_id","objective_id","source_generation","ordinal")
RECEIPT_TEXT_FIELDS=("receipt_id","command_id","idempotency_key","parent_command_id","fanout_id","cohort_id","attempt_id","worker_id","worker_instance_id","role_id","role_instance_id","objective_id","work_order_id","provider","model","source_generation","effect_kind","artifact_identity","provider_request_id","observed_at","execution_state","reconcile_key","host_instance_id","executor_id")

class HostReceiptError(ValueError):
    def __init__(self,code:str)->None: super().__init__(code); self.code=code

def _text(name:str,value:Any)->str:
    if not isinstance(value,str) or not value.strip(): raise HostReceiptError(f"{name.upper()}_REQUIRED")
    return value.strip()

def _digest(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def _hex64(name:str,value:Any)->str:
    v=_text(name,value).lower()
    if len(v)!=64 or any(c not in "0123456789abcdef" for c in v): raise HostReceiptError(f"{name.upper()}_INVALID")
    return v

def _ordinal(value:Any)->int:
    if isinstance(value,bool) or not isinstance(value,int) or value<0: raise HostReceiptError("ORDINAL_INVALID")
    return value

def _manifest(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping) or raw.get("schema")!="AuraPhysicalSwarmCompileReceiptV1": raise HostReceiptError("FANOUT_MANIFEST_SCHEMA_MISMATCH")
    parent=_text("parent_command_id",raw.get("parent_command_id")); idem=_text("parent_idempotency_key",raw.get("parent_idempotency_key")); payload=_hex64("parent_payload_digest",raw.get("parent_payload_digest"))
    target=raw.get("target_size"); refs=raw.get("child_refs")
    if isinstance(target,bool) or not isinstance(target,int) or target<1: raise HostReceiptError("FANOUT_TARGET_SIZE_INVALID")
    if not isinstance(refs,Sequence) or isinstance(refs,(str,bytes)) or len(refs)!=target: raise HostReceiptError("FANOUT_MANIFEST_CHILD_REFS_INVALID")
    if raw.get("child_count")!=target or raw.get("effect_started") is not False: raise HostReceiptError("FANOUT_MANIFEST_STATE_INVALID")
    canon=[]; seen=[set() for _ in range(5)]
    for ref in refs:
        if not isinstance(ref,Mapping): raise HostReceiptError("FANOUT_CHILD_REF_INVALID")
        item={"command_id":_text("command_id",ref.get("command_id")),"idempotency_key":_text("idempotency_key",ref.get("idempotency_key")),"role_id":_text("role_id",ref.get("role_id")),"worker_id":_text("worker_id",ref.get("worker_id")),"ordinal":_ordinal(ref.get("ordinal"))}
        vals=(item["command_id"],item["idempotency_key"],item["role_id"],item["worker_id"],item["ordinal"])
        if any(v in bucket for v,bucket in zip(vals,seen)): raise HostReceiptError("FANOUT_MANIFEST_CHILD_DUPLICATE")
        for v,bucket in zip(vals,seen): bucket.add(v)
        canon.append(item)
    body={"schema":"AuraPhysicalSwarmCompileReceiptV1","parent_command_id":parent,"parent_idempotency_key":idem,"parent_payload_digest":payload,"target_size":target,"children":canon}
    md=_hex64("manifest_digest",raw.get("manifest_digest"))
    if _digest(body)!=md: raise HostReceiptError("FANOUT_MANIFEST_DIGEST_MISMATCH")
    return {"schema":body["schema"],"parent_command_id":parent,"parent_idempotency_key":idem,"parent_payload_digest":payload,"target_size":target,"child_count":target,"child_refs":canon,"manifest_digest":md,"effect_started":False}

def normalize_child_identity(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping) or raw.get("schema")!=IDENTITY_SCHEMA: raise HostReceiptError("CHILD_IDENTITY_SCHEMA_MISMATCH")
    out={"schema":IDENTITY_SCHEMA}
    for f in IDENTITY_FIELDS:
        out[f]=_hex64(f,raw.get(f)) if f in {"command_digest","parent_payload_digest","plan_digest","manifest_digest"} else (_ordinal(raw.get(f)) if f=="ordinal" else _text(f,raw.get(f)))
    return out

def _plan_canonical(body:Mapping[str,Any])->dict[str,Any]:
    out={k:v for k,v in body.items() if k!="plan_digest"}; out["children"]=[{k:v for k,v in c.items() if k!="plan_digest"} for c in out["children"]]; return out

@dataclass(frozen=True)
class ExactReceiptSet:
    schema:str; identity:Mapping[str,Any]; records:tuple[Mapping[str,Any],...]; projection_digest:str; _seal:object
@dataclass(frozen=True)
class HostExecutionPlan:
    schema:str; plan_digest:str; manifest:Mapping[str,Any]; parent_command_id:str; parent_payload_digest:str; manifest_digest:str; fanout_id:str; objective_id:str; source_generation:str; target_size:int; children:tuple[Mapping[str,Any],...]; _seal:object

class HostReceiptRegistry:
    """Host-owned plans and append-only observed execution receipts."""
    def __init__(self,path:str|os.PathLike[str],*,host_instance_id:str,executor_id:str)->None:
        self.path=Path(path); self.plan_path=self.path.with_name(self.path.name+".plans"); self.host_instance_id=_text("host_instance_id",host_instance_id); self.executor_id=_text("executor_id",executor_id)
        self._seal=object(); self._lock=threading.RLock(); self._records=[]; self._receipt_ids=set(); self._plans={}; self._event_seq=0; self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists(): self._load_receipts()
        if self.plan_path.exists(): self._load_plans()
    def _load_receipts(self)->None:
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r=self._validate_record(json.loads(line),loading=True); self._records.append(r); self._receipt_ids.add(r["receipt_id"]); self._event_seq=max(self._event_seq,r["event_seq"])
    def _load_plans(self)->None:
        for line in self.plan_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                b=json.loads(line); self._validate_plan_body(b); self._plans[b["plan_digest"]]=b
    def _validate_plan_body(self,b:Mapping[str,Any])->None:
        if not isinstance(b,Mapping) or b.get("schema")!=PLAN_SCHEMA: raise HostReceiptError("PLAN_SCHEMA_MISMATCH")
        claimed=_hex64("plan_digest",b.get("plan_digest"))
        if _digest(_plan_canonical(b))!=claimed: raise HostReceiptError("PLAN_DIGEST_MISMATCH")
        if len(b.get("children",[]))!=b.get("target_size"): raise HostReceiptError("PLAN_CHILD_COUNT_MISMATCH")
        for child in b["children"]: normalize_child_identity(child)
    def _plan(self,b:Mapping[str,Any])->HostExecutionPlan:
        return HostExecutionPlan(PLAN_SCHEMA,b["plan_digest"],dict(b["manifest"]),b["parent_command_id"],b["parent_payload_digest"],b["manifest_digest"],b["fanout_id"],b["objective_id"],b["source_generation"],b["target_size"],tuple(dict(x) for x in b["children"]),self._seal)
    def allocate_plan(self,fanout_manifest:Mapping[str,Any],*,fanout_id:str,objective_id:str,source_generation:str,command_digests_by_id:Mapping[str,str],attempt_generation:int=1)->HostExecutionPlan:
        if isinstance(attempt_generation,bool) or not isinstance(attempt_generation,int) or attempt_generation<1: raise HostReceiptError("ATTEMPT_GENERATION_INVALID")
        m=_manifest(fanout_manifest); fanout_id=_text("fanout_id",fanout_id); objective_id=_text("objective_id",objective_id); source_generation=_text("source_generation",source_generation); children=[]
        for ref in m["child_refs"]:
            cid=ref["command_id"]; cd=_hex64("command_digest",command_digests_by_id.get(cid)); seed={"parent_command_id":m["parent_command_id"],"manifest_digest":m["manifest_digest"],"fanout_id":fanout_id,"objective_id":objective_id,"source_generation":source_generation,"attempt_generation":attempt_generation,"command_id":cid,"command_digest":cd,"ordinal":ref["ordinal"],"role_id":ref["role_id"],"worker_id":ref["worker_id"]}
            children.append({"schema":IDENTITY_SCHEMA,"command_id":cid,"idempotency_key":ref["idempotency_key"],"command_digest":cd,"parent_payload_digest":m["parent_payload_digest"],"manifest_digest":m["manifest_digest"],"attempt_id":"ATT-"+_digest(seed)[:32],"fanout_id":fanout_id,"worker_id":ref["worker_id"],"role_id":ref["role_id"],"role_instance_id":f"{fanout_id}:{ref['ordinal']}:{ref['role_id']}","objective_id":objective_id,"source_generation":source_generation,"ordinal":ref["ordinal"]})
        body={"schema":PLAN_SCHEMA,"manifest":m,"parent_command_id":m["parent_command_id"],"parent_payload_digest":m["parent_payload_digest"],"manifest_digest":m["manifest_digest"],"fanout_id":fanout_id,"objective_id":objective_id,"source_generation":source_generation,"target_size":m["target_size"],"children":children}
        pd=_digest(_plan_canonical(body)); body["plan_digest"]=pd
        for child in body["children"]: child["plan_digest"]=pd
        with self._lock:
            if pd not in self._plans:
                fd=os.open(self.plan_path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
                try: os.write(fd,(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()); os.fsync(fd)
                finally: os.close(fd)
                self._plans[pd]=body
            return self._plan(self._plans[pd])
    def get_plan(self,plan_digest:str)->HostExecutionPlan:
        pd=_hex64("plan_digest",plan_digest); b=self._plans.get(pd)
        if b is None: raise HostReceiptError("HOST_EXECUTION_PLAN_MISSING")
        self._validate_plan_body(b); return self._plan(b)
    def assert_owned_plan(self,plan:HostExecutionPlan)->None:
        if not isinstance(plan,HostExecutionPlan) or plan._seal is not self._seal: raise HostReceiptError("UNTRUSTED_EXECUTION_PLAN")
        if plan.plan_digest not in self._plans: raise HostReceiptError("HOST_EXECUTION_PLAN_MISSING")
    def _validate_record(self,raw:Mapping[str,Any],*,loading:bool=False)->dict[str,Any]:
        if not isinstance(raw,Mapping) or raw.get("receipt_schema")!=RECEIPT_SCHEMA: raise HostReceiptError("RECEIPT_SCHEMA_MISMATCH")
        out={"receipt_schema":RECEIPT_SCHEMA}; out.update({f:_text(f,raw.get(f)) for f in RECEIPT_TEXT_FIELDS})
        for f in ("command_digest","parent_payload_digest","plan_digest","manifest_digest","route_admission_digest"): out[f]=_hex64(f,raw.get(f))
        out["ordinal"]=_ordinal(raw.get("ordinal")); seq=raw.get("event_seq")
        if isinstance(seq,bool) or not isinstance(seq,int) or seq<1: raise HostReceiptError("EVENT_SEQ_INVALID")
        out["event_seq"]=seq; state=out["execution_state"]
        if state not in {"STARTED","COMMITTED","RECONCILED","FAILED","UNKNOWN"}: raise HostReceiptError("EXECUTION_STATE_INVALID")
        out["result_digest"]=_hex64("result_digest",raw.get("result_digest")) if state in ELIGIBLE_STATES else str(raw.get("result_digest") or "NONE")
        if out["host_instance_id"]!=self.host_instance_id: raise HostReceiptError("HOST_INSTANCE_MISMATCH")
        if out["executor_id"]!=self.executor_id: raise HostReceiptError("EXECUTOR_ID_MISMATCH")
        if not loading and seq!=self._event_seq+1: raise HostReceiptError("EVENT_SEQ_NOT_NEXT")
        return out
    def record(self,observed_host_event:Mapping[str,Any])->Mapping[str,Any]:
        with self._lock:
            raw=dict(observed_host_event); raw.setdefault("receipt_schema",RECEIPT_SCHEMA); raw.setdefault("host_instance_id",self.host_instance_id); raw.setdefault("executor_id",self.executor_id); raw.setdefault("event_seq",self._event_seq+1); r=self._validate_record(raw)
            plan=self._plans.get(r["plan_digest"])
            if plan is None: raise HostReceiptError("RECEIPT_PLAN_NOT_HOST_OWNED")
            ident=normalize_child_identity({"schema":IDENTITY_SCHEMA,**{f:r[f] for f in IDENTITY_FIELDS}}); expected={c["command_id"]:normalize_child_identity(c) for c in plan["children"]}
            if expected.get(ident["command_id"])!=ident: raise HostReceiptError("RECEIPT_CHILD_NOT_IN_HOST_PLAN")
            if r["receipt_id"] in self._receipt_ids: raise HostReceiptError("RECEIPT_ID_REPLAY")
            fd=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
            try: os.write(fd,(json.dumps(r,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()); os.fsync(fd)
            finally: os.close(fd)
            self._records.append(r); self._receipt_ids.add(r["receipt_id"]); self._event_seq=r["event_seq"]; return dict(r)
    def resolve(self,plan:HostExecutionPlan,child_identity:Mapping[str,Any],required_evidence:Sequence[str]=())->ExactReceiptSet:
        self.assert_owned_plan(plan); ident=normalize_child_identity(child_identity); expected={c["command_id"]:normalize_child_identity(c) for c in plan.children}
        if expected.get(ident["command_id"])!=ident: raise HostReceiptError("CHILD_NOT_IN_HOST_PLAN")
        matches=[r for r in self._records if all(str(r[f])==str(ident[f]) for f in IDENTITY_FIELDS) and r["execution_state"] in ELIGIBLE_STATES]
        if not matches: raise HostReceiptError("EXACT_HOST_RECEIPT_MISSING")
        latest=matches[-1]
        for f in required_evidence:
            f=_text("required_evidence",f)
            if f not in latest or not str(latest[f]).strip(): raise HostReceiptError("REQUIRED_HOST_EVIDENCE_MISSING")
        body={"schema":PROJECTION_SCHEMA,"plan_digest":plan.plan_digest,"identity":ident,"receipt_ids":[r["receipt_id"] for r in matches],"record_digests":[_digest(r) for r in matches]}
        return ExactReceiptSet(PROJECTION_SCHEMA,ident,tuple(dict(r) for r in matches),_digest(body),self._seal)
    def assert_owned_projection(self,projection:ExactReceiptSet)->None:
        if not isinstance(projection,ExactReceiptSet) or projection._seal is not self._seal: raise HostReceiptError("UNTRUSTED_RECEIPT_PROJECTION")
