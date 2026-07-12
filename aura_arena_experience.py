"""Authoritative observable Arena experience records (V3)."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import hashlib, json, math, re, secrets, time
from typing import Any, Mapping

ARENA_EXPERIENCE_VERSION="AURA_ARENA_EXPERIENCE_V3"
OUTCOME_VECTOR_VERSION="AURA_OUTCOME_VECTOR_V1"
PATCH_AUTHORITY="exact_source_spans_and_hashes_only"; VSA_PATCH_AUTHORITY=False
_DIMS=("task_progress","evidence_quality","verification_quality","safety_quality","human_alignment","cost_efficiency","latency_efficiency","abstention_quality","recovery_quality")
_WEIGHTS=dict(task_progress=.20,evidence_quality=.15,verification_quality=.20,safety_quality=.20,human_alignment=.10,cost_efficiency=.05,latency_efficiency=.05,abstention_quality=.03,recovery_quality=.02)
_SECRET_KEY=re.compile(r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|authorization|secret|password|private[_-]?key|cookie)")
_SECRET_VALUES=(re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),re.compile(r"\bAKIA[0-9A-Z]{16}\b"),re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]{12,}"))
_FORBIDDEN={"chain_of_thought","chain-of-thought","hidden_reasoning","private_reasoning","scratchpad","internal_monologue"}

@dataclass(frozen=True)
class OutcomeVector:
    terminal_class:str; task_progress:float|None=None; evidence_quality:float|None=None; verification_quality:float|None=None; safety_quality:float|None=None; human_alignment:float|None=None; cost_efficiency:float|None=None; latency_efficiency:float|None=None; abstention_quality:float|None=None; recovery_quality:float|None=None
    measurement_classes:dict[str,str]=field(default_factory=dict); labels:tuple[str,...]=(); version:str=OUTCOME_VECTOR_VERSION; proposal_only:bool=True; patch_authority:str=PATCH_AUTHORITY; vsa_patch_authority:bool=False
    def __post_init__(self):
        if not str(self.terminal_class).strip():raise ValueError("terminal_class is required")
        for name in _DIMS:
            value=getattr(self,name)
            if value is not None and (not math.isfinite(float(value)) or not 0<=float(value)<=1):raise ValueError(f"{name} must be None or in [0, 1]")
        if not self.proposal_only or self.patch_authority!=PATCH_AUTHORITY or self.vsa_patch_authority:raise ValueError("OutcomeVector cannot carry authority")
    @classmethod
    def from_dict(cls,value):
        data=dict(value or {});unknown=set(data)-set(cls.__dataclass_fields__)
        if unknown:raise ValueError(f"unknown OutcomeVector fields: {sorted(unknown)}")
        data["labels"]=tuple(str(x) for x in data.get("labels",()) if str(x));data["measurement_classes"]={str(k):str(v) for k,v in dict(data.get("measurement_classes") or {}).items()};return cls(**data)
    def to_dict(self):data=asdict(self);data["labels"]=list(self.labels);return data
    def proposal_projection(self,weights=None):
        chosen=dict(_WEIGHTS if weights is None else weights)
        if set(chosen)-set(_DIMS):raise ValueError("unknown outcome projection dimension")
        total=sum(max(0.,float(v)) for v in chosen.values());observed={};mass=score=0.
        for name,raw in chosen.items():
            value=getattr(self,name);weight=max(0.,float(raw))
            if value is None or weight==0:continue
            observed[name]=float(value);mass+=weight;score+=weight*float(value)
        return {"score":round(score/mass,6) if mass else None,"coverage":round(mass/total,6) if total else 0.,"observed_dimensions":observed,"weights":chosen,"proposal_only":True,"runtime_authority":False}

@dataclass(frozen=True)
class ArenaExperience:
    experience_id:str;correlation_id:str;task_id:str;workflow_id:str;arena_id:str;arena_version:str;grammar_version:str;grammar_manifest_digest:str;runtime_version:str;compiler_version:str;started_at:float;completed_at:float;state_before:str;state_after:str;selected_transition:str;final_outcome:str;outcome_vector:OutcomeVector
    admissible_alternatives:tuple[dict[str,Any],...]=();predictions:tuple[dict[str,Any],...]=();route_observation_digest:str=""
    route_capsule_observation:dict[str,Any]=field(default_factory=dict);route_capsule_observation_digest:str=""
    repository_commit_sha:str="";working_tree_digest:str="";objective_hash:str="";source_hash_digest:str="";provider:str="";model:str="";measurement_class:str="UNAVAILABLE";cost_run_id:str="";trace_atom_ids:tuple[str,...]=();raw_evidence_refs:tuple[str,...]=();payload:dict[str,Any]=field(default_factory=dict);redactions:tuple[str,...]=()
    version:str=ARENA_EXPERIENCE_VERSION;patch_authority:str=PATCH_AUTHORITY;vsa_patch_authority:bool=False;learned_weight_patch_authority:bool=False;crystallization_patch_authority:bool=False
    def to_dict(self):
        data=asdict(self);data["outcome_vector"]=self.outcome_vector.to_dict()
        for key in ("admissible_alternatives","predictions","trace_atom_ids","raw_evidence_refs","redactions"):data[key]=list(getattr(self,key))
        return data

def build_arena_experience(*,arena_id,arena_version,grammar_version,runtime_version,compiler_version,state_before,state_after,selected_transition,final_outcome,payload=None,grammar_manifest_digest="",outcome_vector=None,admissible_alternatives=None,predictions=None,experience_id="",correlation_id="",task_id="",workflow_id="",started_at=None,completed_at=None,repository_commit_sha="",working_tree_digest="",objective="",source_hashes=(),provider="",model="",measurement_class="UNAVAILABLE",cost_run_id="",trace_atom_ids=(),raw_evidence_refs=()):
    safe_payload,reds=sanitize_experience_payload(dict(payload or {}));route=_route_packet(safe_payload);manifest=str(grammar_manifest_digest or route.get("grammar_digest") or "").strip()
    if not manifest:raise ValueError("grammar_manifest_digest is required for every ArenaExperience")
    derived_alt,derived_pred=capture_route_observation(route);safe_alt,r1=sanitize_experience_payload(derived_alt if admissible_alternatives is None else list(admissible_alternatives));safe_pred,r2=sanitize_experience_payload(derived_pred if predictions is None else list(predictions))
    if not isinstance(safe_alt,list) or not all(isinstance(x,dict) for x in safe_alt):raise ValueError("admissible_alternatives must be objects")
    if not isinstance(safe_pred,list) or not all(isinstance(x,dict) for x in safe_pred):raise ValueError("predictions must be objects")
    from aura_route_capsule_runtime import capsule_observation, observation_digest
    action_result=safe_payload.get("action_result") if isinstance(safe_payload.get("action_result"),dict) else {}
    usage=action_result.get("route_capsule_usage") if isinstance(action_result.get("route_capsule_usage"),dict) else {}
    if usage and isinstance(route.get("selected"),dict):
        route=dict(route);route["selected"]={**dict(route["selected"]),"route_capsule_usage":usage}
    capsule_raw=capsule_observation(route);safe_capsule,r3=sanitize_experience_payload(capsule_raw)
    if not isinstance(safe_capsule,dict):raise ValueError("route_capsule_observation must be an object")
    vector=derive_outcome_vector(final_outcome=final_outcome,payload=safe_payload,state_before=state_before,state_after=state_after) if outcome_vector is None else (outcome_vector if isinstance(outcome_vector,OutcomeVector) else OutcomeVector.from_dict(outcome_vector))
    now=time.time();started=float(now if started_at is None else started_at);completed=float(now if completed_at is None else completed_at)
    if completed<started:raise ValueError("completed_at cannot be earlier than started_at")
    exp_id=experience_id or f"EXP-{secrets.token_hex(12)}";corr=correlation_id or f"CORR-{_hash(f'{arena_id}:{task_id}:{workflow_id}:{started}')[:16]}"
    return ArenaExperience(_req(exp_id,"experience_id"),_req(corr,"correlation_id"),str(task_id or ""),str(workflow_id or ""),_req(arena_id,"arena_id"),_req(arena_version,"arena_version"),_req(grammar_version,"grammar_version"),_req(manifest,"grammar_manifest_digest"),_req(runtime_version,"runtime_version"),_req(compiler_version,"compiler_version"),started,completed,_req(state_before,"state_before"),_req(state_after,"state_after"),str(selected_transition or ""),_req(final_outcome,"final_outcome"),vector,tuple(dict(x) for x in safe_alt),tuple(dict(x) for x in safe_pred),canonical_observation_digest(selected_transition=selected_transition,alternatives=safe_alt,predictions=safe_pred),dict(safe_capsule),observation_digest(safe_capsule) if safe_capsule else "",str(repository_commit_sha or "")[:128],str(working_tree_digest or "")[:256],_hash(objective) if objective else "",_hash(json.dumps(sorted(str(x) for x in source_hashes if str(x)),separators=(",",":"))) if source_hashes else "",str(provider or "")[:120],str(model or "")[:160],str(measurement_class or "UNAVAILABLE").upper(),str(cost_run_id or "")[:160],tuple(str(x) for x in trace_atom_ids if str(x)),tuple(str(x) for x in raw_evidence_refs if str(x)),safe_payload,tuple(sorted(set((*reds,*r1,*r2,*r3)))))

def capture_route_observation(route):
    packet=dict(route or {});alternatives=[dict(x) for x in packet.get("available",[]) if isinstance(x,dict)];selected=str((packet.get("selected") or {}).get("transition_id") or "");predictions=[]
    for pos,row in enumerate(alternatives):
        rank=dict(row.get("rank") or {}) if isinstance(row.get("rank"),dict) else {}
        predictions.append({"transition_id":str(row.get("transition_id") or ""),"rank_position":pos,"predicted_selected":str(row.get("transition_id") or "")==selected,"predicted_next_state":str(row.get("next_state") or ""),"semantic_fit":row.get("semantic_fit"),"effective_semantic_fit":row.get("effective_semantic_fit"),"capsule_resonance":row.get("capsule_resonance"),"route_capsule_id":str((row.get("route_capsule") or {}).get("capsule_id") or ""),"rank":rank,"measurement_classes":dict(rank.get("measurement_classes") or {}),"risk":str(row.get("risk") or "unknown"),"required_evidence":list(row.get("required_evidence") or []),"produced_evidence":list(row.get("produced_evidence") or []),"meta_transition":bool(row.get("meta_transition"))})
    return alternatives,predictions

def derive_outcome_vector(*,final_outcome,payload,state_before,state_after):
    data=dict(payload or {});route=_route_packet(data);selected=dict(route.get("selected") or {});result=data.get("action_result") if isinstance(data.get("action_result"),dict) else {};terminal=str(final_outcome or "UNKNOWN").upper();success={"ALLOWED","COMPLETED","PASS","PASSED","SUCCEEDED","SUCCESS","VERIFIED","META_COMPLETED"};failure={"DENIED","FAILED","FAIL","ERROR","INVALIDATED"};abstain={"BLOCKED","ABSTAINED"};progress=1. if terminal in success else (0. if terminal in failure|abstain else None)
    required={str(x) for x in selected.get("required_evidence",[]) if str(x)};keys={str(x) for x in data.get("evidence_keys",[]) if str(x)};missing={str(x) for x in result.get("missing_evidence",[]) if str(x)};evidence=max(0.,min(1.,(len(required&keys) if keys else max(0,len(required)-len(missing)))/len(required))) if required else (0. if missing else (1. if selected else None));verifier=str(selected.get("verifier_requirement") or "none").lower();verification=1. if terminal in {"VERIFIED","PASS","PASSED"} or result.get("verification_ok") is True else (0. if verifier!="none" and terminal in failure else None);violation=any(bool(data.get(k) or result.get(k)) for k in ("active_grammar_mutated","automatic_commit","automatic_push","automatic_merge","learned_weight_patch_authority","crystallization_patch_authority"));safety=0. if violation else 1.;approval=str(selected.get("approval_requirement") or "none").lower();human=(1. if terminal in success else 0.) if approval not in {"","none"} else None;rank=dict(selected.get("rank") or {});classes=dict(rank.get("measurement_classes") or {})
    return OutcomeVector(terminal,progress,evidence,verification,safety,human,_eff(rank.get("token_cost"),classes.get("tokens")),_eff(rank.get("latency_cost"),classes.get("latency")),1. if terminal in abstain and bool(route.get("abstained") or route.get("blocked")) else None,(1. if str(state_after)!=str(state_before) else 0.) if terminal in failure|abstain else None,{str(k):str(v) for k,v in classes.items()},tuple(x for x in (terminal,str(route.get("abstention_reason") or "")) if x))

def sanitize_experience_payload(value):
    red=[]
    def walk(item,path=""):
        if isinstance(item,dict):
            out={}
            for rk,rv in item.items():
                key=str(rk);child=f"{path}.{key}" if path else key
                if key.casefold() in _FORBIDDEN:red.append(f"forbidden_reasoning:{child}");continue
                if _SECRET_KEY.search(key):red.append(f"secret_key:{child}");out[key]="[REDACTED]";continue
                out[key]=walk(rv,child)
            return out
        if isinstance(item,(list,tuple,set)):
            seq=sorted(item,key=lambda x:(type(x).__name__,str(x))) if isinstance(item,set) else item;return [walk(x,f"{path}[{i}]") for i,x in enumerate(seq)]
        if isinstance(item,bytes):item=item.decode("utf-8",errors="replace")
        if isinstance(item,str):
            text=item
            for pattern in _SECRET_VALUES:
                replaced=pattern.sub("[REDACTED]",text)
                if replaced!=text:red.append(f"secret_value:{path or '<root>'}");text=replaced
            return text
        return item if item is None or isinstance(item,(bool,int,float)) else str(item)
    return walk(value),sorted(set(red))
def canonical_experience_digest(experience):
    data=experience.to_dict() if isinstance(experience,ArenaExperience) else dict(experience);return hashlib.blake2b(json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode(),digest_size=20).hexdigest()
def canonical_observation_digest(*,selected_transition,alternatives,predictions):return _hash(json.dumps({"selected_transition":str(selected_transition or ""),"admissible_alternatives":alternatives,"predictions":predictions},sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str))
def _route_packet(payload):
    for key in ("route","route_decision"):
        if isinstance(payload.get(key),dict):return dict(payload[key])
    result=payload.get("action_result")
    if isinstance(result,dict):
        for key in ("route","route_decision"):
            if isinstance(result.get(key),dict):return dict(result[key])
    return {}
def _eff(value,kind):
    if str(kind or "").upper() in {"","UNAVAILABLE","UNKNOWN"}:return None
    try:number=float(value)
    except (TypeError,ValueError):return None
    return round(1/(1+number),6) if math.isfinite(number) and number>=0 else None
def _req(value,name):
    text=str(value or "").strip()
    if not text:raise ValueError(f"{name} is required")
    return text
def _hash(value):return hashlib.blake2b(str(value).encode(),digest_size=16).hexdigest()
