from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import itertools, json, re
from typing import Any, Mapping, Sequence

SCHEMA='AURA-TWO-STAGE-READJUDICATION-v1'
SEMANTIC_DOMAIN_PARENT='3ecfedd97c1e156108e9a01796ccd867f813c0dc9fe6ce3492f97b1be0ceb213'
AUTH_CUTSET_PARENT='abd455bce37017b3ed166e65908b2c59da2ebeaaef7e69d9451f713e2a787144'
HEX40=re.compile(r'^[0-9a-f]{40}$'); HEX64=re.compile(r'^[0-9a-f]{64}$'); ID=re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')
SUBJECTS=('AIRLLM_SECURITY_PARENT','COST_PARENT_07','EFFICIENCY_PARENT_27','EVIDENCE_DAG_PARENT')
BUNDLES={
 'BUNDLE_EFFICIENCY_COST':frozenset({'EFFICIENCY_PARENT_27','COST_PARENT_07'}),
 'BUNDLE_SECURITY_DAG':frozenset({'AIRLLM_SECURITY_PARENT','EVIDENCE_DAG_PARENT'}),
 'SINGLE_AIRLLM_SECURITY_PARENT':frozenset({'AIRLLM_SECURITY_PARENT'}),
 'SINGLE_COST_PARENT_07':frozenset({'COST_PARENT_07'}),
 'SINGLE_EFFICIENCY_PARENT_27':frozenset({'EFFICIENCY_PARENT_27'}),
 'SINGLE_EVIDENCE_DAG_PARENT':frozenset({'EVIDENCE_DAG_PARENT'}),
}
class E(ValueError):pass
class ProviderState(str,Enum):
 OBSERVED='OBSERVED';ATTESTED='ATTESTED';CONTESTED='CONTESTED';EXPIRED='EXPIRED';INDETERMINATE='INDETERMINATE'
class Decision(str,Enum):
 REPROVE_LOCAL_FIRST='REPROVE_LOCAL_FIRST';HOLD_AUTHENTICATION_CUTSET='HOLD_AUTHENTICATION_CUTSET';ELIGIBLE_FOR_FRESH_READJUDICATION='ELIGIBLE_FOR_FRESH_READJUDICATION'
def cj(v:Any)->bytes:
 try:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
 except Exception as ex:raise E('NON_CANONICAL') from ex
def dig(v:Any)->str:return sha256(cj(v)).hexdigest()
def h40(x):
 if not isinstance(x,str) or not HEX40.fullmatch(x):raise E('BAD_GENERATION')
 return x
def h64(x):
 if not isinstance(x,str) or not HEX64.fullmatch(x):raise E('BAD_ROOT')
 return x
def sid(x):
 if not isinstance(x,str) or not ID.fullmatch(x):raise E('BAD_ID')
 return x
@dataclass(frozen=True)
class LocalSurface:
 proof_generation:str;current_generation:str
 proof_projection_root:str;current_projection_root:str
 proof_domain_root:str;current_domain_root:str
 proof_graph_root:str;current_graph_root:str
 proof_admission_root:str;current_admission_root:str
 reproof_receipt_root:str;expected_reproof_receipt_root:str
 d0:bool=True;effect_authority:bool=False;gate10:bool=False
 def normalized(self):
  for x in (self.proof_generation,self.current_generation):h40(x)
  for x in (self.proof_projection_root,self.current_projection_root,self.proof_domain_root,self.current_domain_root,self.proof_graph_root,self.current_graph_root,self.proof_admission_root,self.current_admission_root,self.reproof_receipt_root,self.expected_reproof_receipt_root):h64(x)
  if any(type(x) is not bool for x in (self.d0,self.effect_authority,self.gate10)):raise E('BAD_BOOL')
  return self
 def exact(self):
  self.normalized()
  return self.d0 and not self.effect_authority and not self.gate10 and self.proof_generation==self.current_generation and self.proof_projection_root==self.current_projection_root and self.proof_domain_root==self.current_domain_root and self.proof_graph_root==self.current_graph_root and self.proof_admission_root==self.current_admission_root and self.reproof_receipt_root==self.expected_reproof_receipt_root
 def mismatch_keys(self):
  self.normalized();out=[]
  checks=(('GENERATION',self.proof_generation,self.current_generation),('PROJECTION',self.proof_projection_root,self.current_projection_root),('SEMANTIC_DOMAIN',self.proof_domain_root,self.current_domain_root),('GRAPH',self.proof_graph_root,self.current_graph_root),('ADMISSION_SURFACE',self.proof_admission_root,self.current_admission_root),('REPROOF_RECEIPT',self.reproof_receipt_root,self.expected_reproof_receipt_root))
  for k,a,b in checks:
   if a!=b:out.append(k)
  if not self.d0 or self.effect_authority or self.gate10:out.append('AUTHORITY_CEILING')
  return tuple(out)
@dataclass(frozen=True)
class AuthSubject:
 subject:str;generation:str;state:ProviderState;receipt_root:str|None
 def normalized(self):
  if sid(self.subject) not in SUBJECTS:raise E('UNKNOWN_SUBJECT')
  h40(self.generation)
  if not isinstance(self.state,ProviderState):raise E('BAD_PROVIDER_STATE')
  if self.state==ProviderState.ATTESTED:
   if self.receipt_root is None:h64('')
   h64(self.receipt_root)
  elif self.receipt_root is not None:h64(self.receipt_root)
  return self
 def resolved(self):return self.normalized().state==ProviderState.ATTESTED and self.receipt_root is not None
@dataclass(frozen=True)
class Receipt:
 schema:str;decision:Decision;local_mismatches:tuple[str,...];missing_subjects:tuple[str,...];bundle_ids:tuple[str,...];local_root:str;auth_root:str
 provider_attestation_is_truth:bool=False;d0:bool=True;effect_authority:bool=False;gate10:bool=False;receipt_root:str=''
 def payload(self):
  d=asdict(self);d['decision']=self.decision.value;d.pop('receipt_root');return d
 def verify(self):
  if self.schema!=SCHEMA+'-RECEIPT' or self.provider_attestation_is_truth or not self.d0 or self.effect_authority or self.gate10:return False
  try:h64(self.local_root);h64(self.auth_root);h64(self.receipt_root)
  except E:return False
  return self.receipt_root==dig(self.payload())
def local_root(x:LocalSurface):return dig({'schema':SCHEMA+'-LOCAL','surface':asdict(x.normalized())})
def auth_root(xs:Sequence[AuthSubject]):
 ns=tuple(sorted((x.normalized() for x in xs),key=lambda x:x.subject));
 if tuple(x.subject for x in ns)!=tuple(sorted(SUBJECTS)):raise E('INCOMPLETE_AUTH_SURFACE')
 if len({x.subject for x in ns})!=len(ns):raise E('DUPLICATE_SUBJECT')
 return dig({'schema':SCHEMA+'-AUTH','subjects':[{'subject':x.subject,'generation':x.generation,'state':x.state.value,'receipt_root':x.receipt_root} for x in ns]})
def minimum_bundles(missing:set[str])->tuple[str,...]:
 if not missing:return ()
 choices=sorted(BUNDLES)
 best=None
 for r in range(1,len(choices)+1):
  for combo in itertools.combinations(choices,r):
   cover=set().union(*(BUNDLES[x] for x in combo))
   if missing<=cover:
    key=(len(combo),sum(len(BUNDLES[x]) for x in combo),combo)
    if best is None or key<best[0]:best=(key,combo)
  if best:return best[1]
 raise E('UNCOVERED_SUBJECT')
def adjudicate(local:LocalSurface,subjects:Sequence[AuthSubject])->Receipt:
 lr=local_root(local);ar=auth_root(subjects);lm=local.mismatch_keys()
 ns=tuple(sorted((x.normalized() for x in subjects),key=lambda x:x.subject))
 if lm:
  dec=Decision.REPROVE_LOCAL_FIRST;missing=();bundles=()
 else:
  missing=tuple(x.subject for x in ns if not x.resolved())
  if missing:
   dec=Decision.HOLD_AUTHENTICATION_CUTSET;bundles=minimum_bundles(set(missing))
  else:
   dec=Decision.ELIGIBLE_FOR_FRESH_READJUDICATION;bundles=()
 r=Receipt(SCHEMA+'-RECEIPT',dec,lm,missing,bundles,lr,ar)
 return Receipt(**{**r.__dict__,'receipt_root':dig(r.payload())})
def crystalline(s:Sequence[int])->bool:return len(s)==8 and all(type(x)is int and x==2 for x in s)
def admission13(s:Sequence[int])->bool:return len(s)==13 and all(type(x)is int and x in (0,1,2) for x in s) and crystalline(s[:8])
