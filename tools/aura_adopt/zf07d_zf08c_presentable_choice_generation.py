"""ZF-07D/ZF-08C D0 presentable-choice typed-generation membrane.

This module transports choice/currentness questions; it is not an authority
owner. Candidate-set summaries are diagnostic only. All effects remain false.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,re
from typing import Any,Mapping,Protocol,Sequence

SCHEMA="PresentableChoiceGenerationMembraneV1"; CHOICE_SCHEMA="PresentableChoiceEnvelopeV1"
REQ_SCHEMA="ChoiceGenerationRequirementV1"; QUERY_SCHEMA="ChoiceGenerationQueryV1"
RES_SCHEMA="ChoiceGenerationResolutionV1"; DEC_SCHEMA="PresentableChoiceDecisionV1"
SET_SCHEMA="PresentableChoiceSetDecisionV1"
SOURCE="SOURCE";PLACEMENT="PLACEMENT";OWNER="OWNER";RESOLVER="RESOLVER";TARGET="TARGET";RUNTIME="RUNTIME_CACHE_ROUTE";PRINCIPAL="PRINCIPAL_CONTEXT"
ALLOWED=frozenset({SOURCE,PLACEMENT,OWNER,RESOLVER,TARGET,RUNTIME,PRINCIPAL});BASE=frozenset({SOURCE,OWNER,RESOLVER,TARGET,PRINCIPAL})
DOMAIN_BY_AXIS={SOURCE:"CHOICE_SOURCE_CURRENTNESS",PLACEMENT:"CHOICE_PLACEMENT_CURRENTNESS",OWNER:"CHOICE_OWNER_CURRENTNESS",RESOLVER:"CHOICE_RESOLVER_CURRENTNESS",TARGET:"CHOICE_TARGET_CURRENTNESS",RUNTIME:"CHOICE_RUNTIME_CACHE_ROUTE_CURRENTNESS",PRINCIPAL:"CHOICE_PRINCIPAL_CONTEXT_CURRENTNESS"}
_SHA=re.compile(r"^[0-9a-f]{64}$");_TOKEN=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")

class ChoiceMembraneError(ValueError):
 def __init__(self,code,detail=""):super().__init__(f"{code}:{detail}" if detail else code);self.code=code;self.detail=detail

def _canon(v):
 try:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
 except (TypeError,ValueError) as e:raise ChoiceMembraneError("NONCANONICAL_VALUE") from e
def _dig(domain,v):return hashlib.sha256(domain.encode()+b"\0"+_canon(v)).hexdigest()
def _tok(v,code,empty=False):
 if not isinstance(v,str):raise ChoiceMembraneError(code)
 v=v.strip()
 if empty and not v:return ""
 if not v or not _TOKEN.fullmatch(v):raise ChoiceMembraneError(code)
 return v
def _sha(v,code):
 if not isinstance(v,str):raise ChoiceMembraneError(code)
 v=v.strip().lower()
 if not _SHA.fullmatch(v):raise ChoiceMembraneError(code)
 return v
def _uniq(v,code):
 if isinstance(v,(str,bytes)) or not isinstance(v,Sequence):raise ChoiceMembraneError(code)
 out=tuple(_tok(x,code) for x in v)
 if len(out)!=len(set(out)):raise ChoiceMembraneError(code,"duplicate")
 return out

@dataclass(frozen=True)
class PresentableChoiceEnvelopeV1:
 owner_ref:str;owner_generation:str;owner_projection_digest:str;principal_ref:str;principal_policy_generation:str;source_generation:str;target_generation:str;route_id:str;model_ref:str;provider_ref:str;execution_location:str;cost_class:str;required_actions:tuple[str,...];candidate_evidence_ref:str;candidate_evidence_digest:str;choice_digest:str=""
 def __post_init__(self):
  for f in ("owner_ref","owner_generation","principal_ref","principal_policy_generation","source_generation","target_generation","route_id","model_ref","candidate_evidence_ref"):object.__setattr__(self,f,_tok(getattr(self,f),f"CHOICE_{f.upper()}_INVALID"))
  object.__setattr__(self,"provider_ref",_tok(self.provider_ref,"CHOICE_PROVIDER_REF_INVALID",True));object.__setattr__(self,"owner_projection_digest",_sha(self.owner_projection_digest,"CHOICE_OWNER_PROJECTION_DIGEST_INVALID"));object.__setattr__(self,"candidate_evidence_digest",_sha(self.candidate_evidence_digest,"CHOICE_CANDIDATE_EVIDENCE_DIGEST_INVALID"));object.__setattr__(self,"required_actions",_uniq(self.required_actions,"CHOICE_REQUIRED_ACTION_INVALID"))
  if self.execution_location not in {"LOCAL","REMOTE"}:raise ChoiceMembraneError("CHOICE_EXECUTION_LOCATION_INVALID")
  if self.cost_class not in {"INCLUDED","FREE_BOUNDED","PAID","UNKNOWN"}:raise ChoiceMembraneError("CHOICE_COST_CLASS_INVALID")
  if self.execution_location=="REMOTE" and not self.provider_ref:raise ChoiceMembraneError("REMOTE_CHOICE_PROVIDER_REQUIRED")
  if self.execution_location=="LOCAL" and self.provider_ref:raise ChoiceMembraneError("LOCAL_CHOICE_PROVIDER_FORBIDDEN")
  expected=_dig("AURA_PRESENTABLE_CHOICE_V1",self.payload())
  if self.choice_digest and _sha(self.choice_digest,"CHOICE_DIGEST_INVALID")!=expected:raise ChoiceMembraneError("CHOICE_DIGEST_MISMATCH")
  object.__setattr__(self,"choice_digest",expected)
 def payload(self):return {"schema":CHOICE_SCHEMA,"owner_ref":self.owner_ref,"owner_generation":self.owner_generation,"owner_projection_digest":self.owner_projection_digest,"principal_ref":self.principal_ref,"principal_policy_generation":self.principal_policy_generation,"source_generation":self.source_generation,"target_generation":self.target_generation,"route_id":self.route_id,"model_ref":self.model_ref,"provider_ref":self.provider_ref,"execution_location":self.execution_location,"cost_class":self.cost_class,"required_actions":list(self.required_actions),"candidate_evidence_ref":self.candidate_evidence_ref,"candidate_evidence_digest":self.candidate_evidence_digest}
 def target_ref(self):return "choice-target:"+_dig("AURA_PRESENTABLE_CHOICE_TARGET_V1",{"route_id":self.route_id,"model_ref":self.model_ref,"provider_ref":self.provider_ref,"candidate_evidence_ref":self.candidate_evidence_ref,"candidate_evidence_digest":self.candidate_evidence_digest})

@dataclass(frozen=True)
class GenerationAxisRequirementV1:
 axis:str;evidence_domain:str;issuer_ref:str;issuer_generation:str;identity_ref:str;generation:str;currentness_ref:str;authoritative_basis_ref:str
 def __post_init__(self):
  if self.axis not in ALLOWED:raise ChoiceMembraneError("GENERATION_AXIS_INVALID",self.axis)
  object.__setattr__(self,"evidence_domain",_tok(self.evidence_domain,"GENERATION_EVIDENCE_DOMAIN_INVALID"))
  if self.evidence_domain!=DOMAIN_BY_AXIS[self.axis]:raise ChoiceMembraneError("GENERATION_EVIDENCE_DOMAIN_MISMATCH",self.axis)
  for f in ("issuer_ref","issuer_generation","identity_ref","generation","currentness_ref","authoritative_basis_ref"):object.__setattr__(self,f,_tok(getattr(self,f),f"GENERATION_{f.upper()}_INVALID"))
 def payload(self):return self.__dict__

@dataclass(frozen=True)
class ChoiceGenerationRequirementV1:
 choice_digest:str;axes:tuple[GenerationAxisRequirementV1,...];requirement_digest:str=""
 def __post_init__(self):
  object.__setattr__(self,"choice_digest",_sha(self.choice_digest,"REQUIREMENT_CHOICE_DIGEST_INVALID"))
  if isinstance(self.axes,(str,bytes)) or not isinstance(self.axes,Sequence):raise ChoiceMembraneError("REQUIREMENT_AXES_SEQUENCE_REQUIRED")
  axes=tuple(self.axes);by={x.axis:x for x in axes if isinstance(x,GenerationAxisRequirementV1)}
  if len(by)!=len(axes):raise ChoiceMembraneError("REQUIREMENT_AXIS_INVALID_OR_DUPLICATE")
  if not BASE.issubset(by):raise ChoiceMembraneError("REQUIREMENT_BASE_AXIS_MISSING",",".join(sorted(BASE-set(by))))
  axes=tuple(sorted(axes,key=lambda x:x.axis));object.__setattr__(self,"axes",axes)
  expected=_dig("AURA_CHOICE_GENERATION_REQUIREMENT_V1",{"schema":REQ_SCHEMA,"choice_digest":self.choice_digest,"axes":[x.payload() for x in axes]})
  if self.requirement_digest and _sha(self.requirement_digest,"REQUIREMENT_DIGEST_INVALID")!=expected:raise ChoiceMembraneError("REQUIREMENT_DIGEST_MISMATCH")
  object.__setattr__(self,"requirement_digest",expected)
 def by_axis(self):return {x.axis:x for x in self.axes}

def _issuer(m,axis):
 if not isinstance(m,Mapping) or axis not in m:raise ChoiceMembraneError("GENERATION_ISSUER_BINDING_REQUIRED",axis)
 v=m[axis]
 if not isinstance(v,(tuple,list)) or len(v)!=2:raise ChoiceMembraneError("GENERATION_ISSUER_BINDING_INVALID",axis)
 return _tok(v[0],"GENERATION_ISSUER_REF_INVALID"),_tok(v[1],"GENERATION_ISSUER_GENERATION_INVALID")

def build_choice_generation_requirement(choice,*,issuer_by_axis,resolver_ref,resolver_generation,resolver_currentness_ref,source_currentness_ref,owner_currentness_ref,target_currentness_ref,principal_currentness_ref,source_basis_ref,owner_basis_ref,resolver_basis_ref,target_basis_ref,principal_basis_ref,runtime_cache_route_generation=None,runtime_cache_route_currentness_ref=None,runtime_cache_route_basis_ref=None):
 def ar(axis,identity,generation,currentness,basis):
  ir,ig=_issuer(issuer_by_axis,axis);return GenerationAxisRequirementV1(axis,DOMAIN_BY_AXIS[axis],ir,ig,identity,generation,currentness,basis)
 axes=[ar(SOURCE,choice.candidate_evidence_ref,choice.source_generation,source_currentness_ref,source_basis_ref),ar(OWNER,choice.owner_ref,choice.owner_generation,owner_currentness_ref,owner_basis_ref),ar(RESOLVER,resolver_ref,resolver_generation,resolver_currentness_ref,resolver_basis_ref),ar(TARGET,choice.target_ref(),choice.target_generation,target_currentness_ref,target_basis_ref),ar(PRINCIPAL,choice.principal_ref,choice.principal_policy_generation,principal_currentness_ref,principal_basis_ref)]
 extra=(runtime_cache_route_generation,runtime_cache_route_currentness_ref,runtime_cache_route_basis_ref)
 if any(extra) and not all(extra):raise ChoiceMembraneError("RUNTIME_CACHE_ROUTE_REQUIREMENT_INCOMPLETE")
 if choice.execution_location=="REMOTE":
  if not all(extra):raise ChoiceMembraneError("REMOTE_RUNTIME_CACHE_ROUTE_REQUIREMENT_REQUIRED")
  axes.append(ar(RUNTIME,choice.provider_ref,*extra))
 elif all(extra):axes.append(ar(RUNTIME,choice.model_ref,*extra))
 return ChoiceGenerationRequirementV1(choice.choice_digest,tuple(axes))

def verify_requirement_binding(choice,req):
 if req.choice_digest!=choice.choice_digest:raise ChoiceMembraneError("REQUIREMENT_CHOICE_BINDING_MISMATCH")
 by=req.by_axis();expected={SOURCE:(choice.candidate_evidence_ref,choice.source_generation),OWNER:(choice.owner_ref,choice.owner_generation),TARGET:(choice.target_ref(),choice.target_generation),PRINCIPAL:(choice.principal_ref,choice.principal_policy_generation)}
 for axis,pair in expected.items():
  r=by[axis]
  if (r.identity_ref,r.generation)!=pair:raise ChoiceMembraneError("REQUIREMENT_CHOICE_AXIS_MISMATCH",axis)
 if choice.execution_location=="REMOTE":
  if RUNTIME not in by:raise ChoiceMembraneError("REMOTE_RUNTIME_CACHE_ROUTE_REQUIREMENT_REQUIRED")
  if by[RUNTIME].identity_ref!=choice.provider_ref:raise ChoiceMembraneError("REMOTE_RUNTIME_CACHE_ROUTE_PROVIDER_MISMATCH")
 elif RUNTIME in by and by[RUNTIME].identity_ref!=choice.model_ref:raise ChoiceMembraneError("LOCAL_RUNTIME_CACHE_ROUTE_MODEL_MISMATCH")

@dataclass(frozen=True)
class ChoiceGenerationQueryV1:
 choice_digest:str;requirement_digest:str;axis:str;evidence_domain:str;issuer_ref:str;issuer_generation:str;identity_ref:str;generation:str;currentness_ref:str;authoritative_basis_ref:str;principal_ref:str;query_digest:str=""
 def __post_init__(self):
  object.__setattr__(self,"choice_digest",_sha(self.choice_digest,"QUERY_CHOICE_DIGEST_INVALID"));object.__setattr__(self,"requirement_digest",_sha(self.requirement_digest,"QUERY_REQUIREMENT_DIGEST_INVALID"))
  if self.axis not in ALLOWED:raise ChoiceMembraneError("QUERY_AXIS_INVALID")
  object.__setattr__(self,"evidence_domain",_tok(self.evidence_domain,"QUERY_EVIDENCE_DOMAIN_INVALID"))
  if self.evidence_domain!=DOMAIN_BY_AXIS[self.axis]:raise ChoiceMembraneError("QUERY_EVIDENCE_DOMAIN_MISMATCH",self.axis)
  for f in ("issuer_ref","issuer_generation","identity_ref","generation","currentness_ref","authoritative_basis_ref","principal_ref"):object.__setattr__(self,f,_tok(getattr(self,f),f"QUERY_{f.upper()}_INVALID"))
  expected=_dig("AURA_CHOICE_GENERATION_QUERY_V1",{"schema":QUERY_SCHEMA,**{k:v for k,v in self.__dict__.items() if k!="query_digest"}})
  if self.query_digest and _sha(self.query_digest,"QUERY_DIGEST_INVALID")!=expected:raise ChoiceMembraneError("QUERY_DIGEST_MISMATCH")
  object.__setattr__(self,"query_digest",expected)

@dataclass(frozen=True)
class ChoiceGenerationResolutionV1:
 query_digest:str;evidence_domain:str;issuer_ref:str;issuer_generation:str;resolver_ref:str;resolver_generation:str;resolver_currentness_ref:str;proof_ref:str;currentness_state:str;revoked:bool;resolution_digest:str=""
 def __post_init__(self):
  object.__setattr__(self,"query_digest",_sha(self.query_digest,"RESOLUTION_QUERY_DIGEST_INVALID"));object.__setattr__(self,"evidence_domain",_tok(self.evidence_domain,"RESOLUTION_EVIDENCE_DOMAIN_INVALID"))
  for f in ("issuer_ref","issuer_generation","resolver_ref","resolver_generation","resolver_currentness_ref","proof_ref"):object.__setattr__(self,f,_tok(getattr(self,f),f"RESOLUTION_{f.upper()}_INVALID"))
  if self.currentness_state not in {"CURRENT","STALE","UNKNOWN"}:raise ChoiceMembraneError("RESOLUTION_CURRENTNESS_STATE_INVALID")
  if type(self.revoked) is not bool:raise ChoiceMembraneError("RESOLUTION_REVOKED_BOOL_REQUIRED")
  expected=_dig("AURA_CHOICE_GENERATION_RESOLUTION_V1",{"schema":RES_SCHEMA,**{k:v for k,v in self.__dict__.items() if k!="resolution_digest"}})
  if self.resolution_digest and _sha(self.resolution_digest,"RESOLUTION_DIGEST_INVALID")!=expected:raise ChoiceMembraneError("RESOLUTION_DIGEST_MISMATCH")
  object.__setattr__(self,"resolution_digest",expected)

class ChoiceGenerationResolverV1(Protocol):
 def resolve_choice_generation(self,query:ChoiceGenerationQueryV1)->ChoiceGenerationResolutionV1|None:...
def _query(c,r,a):return ChoiceGenerationQueryV1(c.choice_digest,r.requirement_digest,a.axis,a.evidence_domain,a.issuer_ref,a.issuer_generation,a.identity_ref,a.generation,a.currentness_ref,a.authoritative_basis_ref,c.principal_ref)

def compile_presentable_choice(choice,req,*,resolver,candidate_set_summary:Mapping[str,Any]|None=None):
 verify_requirement_binding(choice,req);block=[];resolved=[];rr=req.by_axis()[RESOLVER]
 if resolver is None:block.append("GENERATION_RESOLVER_REQUIRED")
 else:
  method=getattr(resolver,"resolve_choice_generation",None)
  if not callable(method):raise ChoiceMembraneError("GENERATION_RESOLVER_METHOD_REQUIRED")
  for a in req.axes:
   q=_query(choice,req,a);r=method(q)
   if r is None:block.append(f"GENERATION_EVIDENCE_REQUIRED:{a.axis}");continue
   if not isinstance(r,ChoiceGenerationResolutionV1):raise ChoiceMembraneError("GENERATION_RESOLUTION_INVALID",a.axis)
   if r.query_digest!=q.query_digest:block.append(f"GENERATION_QUERY_MISMATCH:{a.axis}");continue
   if r.evidence_domain!=a.evidence_domain:block.append(f"EVIDENCE_DOMAIN_MISMATCH:{a.axis}");continue
   if (r.issuer_ref,r.issuer_generation)!=(a.issuer_ref,a.issuer_generation):block.append(f"ISSUER_GENERATION_MISMATCH:{a.axis}");continue
   if (r.resolver_ref,r.resolver_generation,r.resolver_currentness_ref)!=(rr.identity_ref,rr.generation,rr.currentness_ref):block.append(f"RESOLVER_GENERATION_MISMATCH:{a.axis}");continue
   if r.currentness_state!="CURRENT":block.append(f"GENERATION_NOT_CURRENT:{a.axis}");continue
   if r.revoked:block.append(f"GENERATION_PROOF_REVOKED:{a.axis}");continue
   resolved.append((a.axis,r.resolution_digest))
 block=sorted(set(block));presentable=not block
 payload={"schema":DEC_SCHEMA,"membrane_schema":SCHEMA,"choice_digest":choice.choice_digest,"requirement_digest":req.requirement_digest,"principal_ref":choice.principal_ref,"route_id":choice.route_id,"model_ref":choice.model_ref,"provider_ref":choice.provider_ref,"required_actions":list(choice.required_actions),"candidate_evidence_ref":choice.candidate_evidence_ref,"candidate_evidence_digest":choice.candidate_evidence_digest,"disposition":"PRESENTABLE" if presentable else "EVIDENCE_REQUIRED","presentable":presentable,"blockers":block,"resolution_digests":resolved,"domain_authority_proven_by_this_module":False,"resolver_trust_proven_by_this_module":False,"credential_authorized":False,"model_download_authorized":False,"provider_call_authorized":False,"payment_authorized":False,"network_authorized":False,"effect_authorized":False,"execution_proven":False}
 admission=_dig("AURA_PRESENTABLE_CHOICE_DECISION_V1",payload);diag=_dig("AURA_CHOICE_CANDIDATE_SET_DIAGNOSTICS_V1",dict(candidate_set_summary)) if candidate_set_summary is not None else None
 return {**payload,"admission_digest":admission,"candidate_set_diagnostics_digest":diag}

def compile_presentable_choice_set(choices,*,resolver,candidate_set_summary=None):
 if isinstance(choices,(str,bytes)) or not isinstance(choices,Sequence) or not choices:raise ChoiceMembraneError("CHOICE_SET_REQUIRED")
 routes=set();decisions=[]
 for pair in choices:
  if not isinstance(pair,(tuple,list)) or len(pair)!=2:raise ChoiceMembraneError("CHOICE_SET_PAIR_INVALID")
  c,r=pair
  if c.route_id in routes:raise ChoiceMembraneError("CHOICE_SET_ROUTE_DUPLICATE",c.route_id)
  routes.add(c.route_id);decisions.append(compile_presentable_choice(c,r,resolver=resolver,candidate_set_summary=candidate_set_summary))
 payload={"schema":SET_SCHEMA,"membrane_schema":SCHEMA,"choices":[{"choice_digest":d["choice_digest"],"route_id":d["route_id"],"disposition":d["disposition"],"admission_digest":d["admission_digest"]} for d in decisions],"presentable_route_ids":[d["route_id"] for d in decisions if d["presentable"]],"blocked_route_ids":[d["route_id"] for d in decisions if not d["presentable"]],"candidate_set_diagnostics_digest":_dig("AURA_CHOICE_CANDIDATE_SET_DIAGNOSTICS_V1",dict(candidate_set_summary)) if candidate_set_summary is not None else None,"domain_authority_proven_by_this_module":False,"resolver_trust_proven_by_this_module":False,"effect_authorized":False,"execution_proven":False}
 payload["set_digest"]=_dig("AURA_PRESENTABLE_CHOICE_SET_DECISION_V1",payload);payload["choice_decisions"]=decisions;return payload
