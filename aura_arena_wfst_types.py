"""Typed contracts for Aura's shared guarded Arena WFST fabric."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

ARENA_WFST_TYPES_VERSION = "AURA_ARENA_WFST_TYPES_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

@dataclass(frozen=True)
class GuardSpec:
    guard_id: str
    args: dict[str, Any] = field(default_factory=dict)
    @classmethod
    def from_dict(cls, value):
        if isinstance(value, str): return cls(value)
        if not isinstance(value, dict): raise TypeError("guard must be a string or object")
        guard_id=str(value.get("id") or value.get("guard_id") or "").strip()
        if not guard_id: raise ValueError("guard id is required")
        args=value.get("args") or {}
        if not isinstance(args, dict): raise TypeError(f"guard args for {guard_id} must be an object")
        return cls(guard_id, dict(args))
    def to_dict(self): return {"id":self.guard_id,"args":dict(self.args)}

@dataclass(frozen=True)
class SoftWeightProfile:
    base_priority: float=.5; empirical_uncertainty: float=1.; context_switch_cost: float=0.
    latency_cost: float|None=None; token_cost: float|None=None; thermal_cost: float|None=None; user_fit: float=.5
    @classmethod
    def from_dict(cls,value):
        d=dict(value or {})
        return cls(_bounded(d.get("base_priority",.5)),_bounded(d.get("empirical_uncertainty",1.)),_nonnegative(d.get("context_switch_cost",0.)),_optional_nonnegative(d.get("latency_cost")),_optional_nonnegative(d.get("token_cost")),_optional_nonnegative(d.get("thermal_cost")),_bounded(d.get("user_fit",.5)))
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ArenaTransition:
    transition_id:str; arena_id:str; grammar_version:str; from_state:str
    accepted_input_symbols:tuple[str,...]; aliases:tuple[str,...]; output_symbol:str; next_state:str
    hard_guards:tuple[GuardSpec,...]=(); requested_capabilities:tuple[str,...]=(); required_evidence:tuple[str,...]=(); produced_evidence:tuple[str,...]=()
    verifier_requirement:str="none"; approval_requirement:str="none"; risk:str="low"; soft_weight_profile:SoftWeightProfile=field(default_factory=SoftWeightProfile)
    ui_label:str=""; ui_description:str=""; explanation_ref:str=""; rollback_transition:str=""; deprecation_status:str="active"
    morphology_profile_ref:str=""; route_capsule_ref:str=""; provenance:dict[str,Any]=field(default_factory=dict)
    @classmethod
    def from_dict(cls,data,*,arena_id,grammar_version):
        if not isinstance(data,dict): raise TypeError("transition must be an object")
        tid=_required_text(data,"transition_id"); fs=_required_text(data,"from_state"); ns=_required_text(data,"next_state"); out=_required_text(data,"output_symbol")
        return cls(tid,arena_id,grammar_version,fs,_text_tuple(data.get("accepted_input_symbols") or (tid,)),_text_tuple(data.get("aliases") or ()),out,ns,tuple(GuardSpec.from_dict(x) for x in data.get("hard_guards",()) or ()),_text_tuple(data.get("requested_capabilities") or ()),_text_tuple(data.get("required_evidence") or ()),_text_tuple(data.get("produced_evidence") or ()),str(data.get("verifier_requirement") or "none").strip().lower(),str(data.get("approval_requirement") or "none").strip().lower(),str(data.get("risk") or "low").strip().lower(),SoftWeightProfile.from_dict(data.get("soft_weight_profile")),str(data.get("ui_label") or tid).strip(),str(data.get("ui_description") or "").strip(),str(data.get("explanation_ref") or "").strip(),str(data.get("rollback_transition") or "").strip(),str(data.get("deprecation_status") or "active").strip().lower(),str(data.get("morphology_profile_ref") or "").strip(),str(data.get("route_capsule_ref") or "").strip(),dict(data.get("provenance") or {}))
    def input_phrases(self): return _unique((*self.accepted_input_symbols,*self.aliases,self.transition_id,self.ui_label))
    def to_dict(self):
        return {"transition_id":self.transition_id,"arena_id":self.arena_id,"grammar_version":self.grammar_version,"from_state":self.from_state,"accepted_input_symbols":list(self.accepted_input_symbols),"aliases":list(self.aliases),"output_symbol":self.output_symbol,"next_state":self.next_state,"hard_guards":[x.to_dict() for x in self.hard_guards],"requested_capabilities":list(self.requested_capabilities),"required_evidence":list(self.required_evidence),"produced_evidence":list(self.produced_evidence),"verifier_requirement":self.verifier_requirement,"approval_requirement":self.approval_requirement,"risk":self.risk,"soft_weight_profile":self.soft_weight_profile.to_dict(),"ui_label":self.ui_label,"ui_description":self.ui_description,"explanation_ref":self.explanation_ref,"rollback_transition":self.rollback_transition,"deprecation_status":self.deprecation_status,"morphology_profile_ref":self.morphology_profile_ref,"route_capsule_ref":self.route_capsule_ref,"provenance":dict(self.provenance)}

@dataclass(frozen=True)
class CompiledArenaGrammar:
    arena_id:str; arena_version:str; grammar_version:str; start_state:str; states:tuple[str,...]; transitions:tuple[ArenaTransition,...]; manifest_digest:str; source_path:str=""; meta_grammar:bool=False
    def outgoing(self,state): return tuple(t for t in self.transitions if t.from_state==state or (self.meta_grammar and t.from_state=="*"))
    def transition_by_id(self,transition_id): return next((t for t in self.transitions if t.transition_id==str(transition_id or "").strip()),None)
    def to_dict(self): return {"version":ARENA_WFST_TYPES_VERSION,"arena_id":self.arena_id,"arena_version":self.arena_version,"grammar_version":self.grammar_version,"start_state":self.start_state,"states":list(self.states),"transitions":[t.to_dict() for t in self.transitions],"manifest_digest":self.manifest_digest,"source_path":self.source_path,"meta_grammar":self.meta_grammar,"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}

@dataclass(frozen=True)
class GuardResult:
    guard_id:str; passed:bool; reason:str; missing_evidence:tuple[str,...]=(); details:dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return {"guard_id":self.guard_id,"passed":self.passed,"reason":self.reason,"missing_evidence":list(self.missing_evidence),"details":dict(self.details)}

@dataclass(frozen=True)
class RankVector:
    unresolved_risk:float; declared_evidence_gap:float; empirical_uncertainty:float; semantic_ambiguity:float; context_switch_cost:float; latency_cost:float; token_cost:float; thermal_cost:float; negative_semantic_fit:float; negative_user_fit:float; stable_transition_id:str; measurement_classes:dict[str,str]=field(default_factory=dict)
    def sort_key(self): return (self.unresolved_risk,self.declared_evidence_gap,self.empirical_uncertainty,self.semantic_ambiguity,self.context_switch_cost,self.latency_cost,self.token_cost,self.thermal_cost,self.negative_semantic_fit,self.negative_user_fit,self.stable_transition_id)
    def to_dict(self): return asdict(self)

def _required_text(data,key):
    v=str(data.get(key) or "").strip()
    if not v: raise ValueError(f"{key} is required")
    return v
def _text_tuple(value):
    if isinstance(value,str): value=(value,)
    if not isinstance(value,(list,tuple,set)): raise TypeError("expected a string or sequence of strings")
    return _unique(str(x).strip() for x in value if str(x).strip())
def _unique(values):
    out=[]; seen=set()
    for raw in values:
        v=str(raw)
        if v not in seen: seen.add(v); out.append(v)
    return tuple(out)
def _bounded(value):
    try:n=float(value)
    except (TypeError,ValueError):n=0.
    return max(0.,min(1.,n))
def _nonnegative(value):
    try:return max(0.,float(value))
    except (TypeError,ValueError):return 0.
def _optional_nonnegative(value): return None if value is None else _nonnegative(value)
