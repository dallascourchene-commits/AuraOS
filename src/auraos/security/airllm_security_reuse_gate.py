from __future__ import annotations
from dataclasses import asdict,dataclass
from hashlib import sha256
import json,re
from typing import Mapping

S="AURA-AIRLLM-SECURITY-RECEIPT-v1"; RS="AURA-AIRLLM-SECURITY-REUSE-ADMISSION-v1"; H=re.compile(r"^[0-9a-f]{64}$")
SC={"GENERAL_LOCAL_SECURITY","TRACE_SENSITIVE_LOCAL_SECURITY","WORKLOAD_SENSITIVE_LOCAL_SECURITY","TRACE_WORKLOAD_LOCAL_SECURITY"}
TS={"TRACE_SENSITIVE_LOCAL_SECURITY","TRACE_WORKLOAD_LOCAL_SECURITY"}; WS={"WORKLOAD_SENSITIVE_LOCAL_SECURITY","TRACE_WORKLOAD_LOCAL_SECURITY"}
P=("1fqAvyxo24Agxup7H6ijOD15iWWt9eLR6AvOb0bynSDs","1R4mqYlVPW2BKq21tFXOsz0uAAwS9BjiO2TntAdbOd0s")
class SecurityReuseError(ValueError): pass
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")
def dig(x): return sha256(canon(x)).hexdigest()
def reqh(x,n):
 if not isinstance(x,str) or H.fullmatch(x) is None: raise SecurityReuseError(f"{n} must be exact lowercase SHA-256")
 return x
def valid_receipt(r):
 if not isinstance(r,Mapping) or r.get("schema")!=S:return False
 h=r.get("receipt_sha256")
 if not isinstance(h,str) or H.fullmatch(h) is None:return False
 if any(r.get(k) is not False for k in ("effect_authority","promotion_authorized","owner_host_proven","hosted_ci_proven","gate10")):return False
 b=dict(r);b.pop("receipt_sha256",None);b.pop("k27",None);e=dig(b)
 if e!=h:return False
 raw=bytes.fromhex(e)
 return r.get("k27")==[raw[0]%27,raw[1]%27,raw[2]%27] and r.get("disposition")=="LOCAL_VERIFIED_NONPROMOTING" and r.get("stale_or_missing")==[]
def subject_root(r):
 x=r.get("subject")
 if not isinstance(x,Mapping):raise SecurityReuseError("receipt subject must be a mapping")
 return dig(dict(x))
def generation_root(r):
 x=r.get("current_generation")
 if not isinstance(x,Mapping):raise SecurityReuseError("receipt current_generation must be a mapping")
 return dig(dict(x))
@dataclass(frozen=True)
class TraceReuseContract:
 expected_trace_schema_root:str;proved_trace_schema_root:str;expected_event_root:str;proved_event_root:str;reconstructed_event_root:str;canonical_trace_schema_verified:bool;execution_source_provenance_verified:bool;fused_event_structure_verified:bool
 def __post_init__(self):
  for f in ("expected_trace_schema_root","proved_trace_schema_root","expected_event_root","proved_event_root","reconstructed_event_root"):reqh(getattr(self,f),f)
  for f in ("canonical_trace_schema_verified","execution_source_provenance_verified","fused_event_structure_verified"):
   if type(getattr(self,f)) is not bool:raise SecurityReuseError(f"{f} must be bool")
 def reasons(self):
  q=[]
  if self.proved_trace_schema_root!=self.expected_trace_schema_root:q.append("TRACE_SCHEMA_ROOT_MISMATCH")
  if not self.proved_event_root==self.expected_event_root==self.reconstructed_event_root:q.append("EVENT_IDENTITY_MISMATCH")
  if not self.canonical_trace_schema_verified:q.append("CANONICAL_TRACE_SCHEMA_UNVERIFIED")
  if not self.execution_source_provenance_verified:q.append("EXECUTION_SOURCE_PROVENANCE_UNVERIFIED")
  if not self.fused_event_structure_verified:q.append("FUSED_EVENT_STRUCTURE_UNVERIFIED")
  return q
@dataclass(frozen=True)
class WorkloadReuseContract:
 expected_workload_root:str;observed_workload_root:str;expected_environment_root:str;observed_environment_root:str;source_current:bool;cross_category_rendered_prefix_collision:bool;ranking_category_count:int
 def __post_init__(self):
  for f in ("expected_workload_root","observed_workload_root","expected_environment_root","observed_environment_root"):reqh(getattr(self,f),f)
  if type(self.source_current) is not bool or type(self.cross_category_rendered_prefix_collision) is not bool:raise SecurityReuseError("workload booleans must be bool")
  if type(self.ranking_category_count) is not int or self.ranking_category_count<0:raise SecurityReuseError("ranking_category_count must be non-negative int")
 def reasons(self):
  q=[]
  if self.observed_workload_root!=self.expected_workload_root:q.append("WORKLOAD_ROOT_MISMATCH")
  if self.observed_environment_root!=self.expected_environment_root:q.append("ENVIRONMENT_ROOT_MISMATCH")
  if not self.source_current:q.append("WORKLOAD_SOURCE_STALE")
  if self.cross_category_rendered_prefix_collision:q.append("RENDERED_PREFIX_CONTAMINATION")
  if self.ranking_category_count<2:q.append("INSUFFICIENT_RANKING_CATEGORIES")
  return q
@dataclass(frozen=True)
class SecurityReuseRequest:
 scope:str;expected_receipt_sha256:str;expected_subject_root:str;expected_current_generation_root:str;authority_requested:bool=False;trace:TraceReuseContract|None=None;workload:WorkloadReuseContract|None=None
 def __post_init__(self):
  if self.scope not in SC:raise SecurityReuseError("unsupported scope")
  for f in ("expected_receipt_sha256","expected_subject_root","expected_current_generation_root"):reqh(getattr(self,f),f)
  if type(self.authority_requested) is not bool:raise SecurityReuseError("authority_requested must be bool")
  if (self.scope in TS)!=(self.trace is not None):raise SecurityReuseError("trace contract shape mismatch")
  if (self.scope in WS)!=(self.workload is not None):raise SecurityReuseError("workload contract shape mismatch")
def admit(r:Mapping[str,object],x:SecurityReuseRequest):
 q=[];v=valid_receipt(r)
 if not v:q.append("SECURITY_RECEIPT_INVALID_OR_STALE")
 h=r.get("receipt_sha256") if isinstance(r,Mapping) else None
 if h!=x.expected_receipt_sha256:q.append("RECEIPT_IDENTITY_MISMATCH")
 if v:
  try:
   if subject_root(r)!=x.expected_subject_root:q.append("SECURITY_SUBJECT_MISMATCH")
   if generation_root(r)!=x.expected_current_generation_root:q.append("SECURITY_GENERATION_MISMATCH")
  except SecurityReuseError:q.append("SECURITY_RECEIPT_MALFORMED_CONTEXT")
 if x.trace:q+=x.trace.reasons()
 if x.workload:q+=x.workload.reasons()
 if x.authority_requested:q.append("AUTHORITY_REQUEST_REQUIRES_REPROOF")
 q=sorted(set(q)); ok=not q
 b={"schema":RS,"scope":x.scope,"exact_foreign_parents":list(P),"source_receipt_sha256":h,"expected_receipt_sha256":x.expected_receipt_sha256,"expected_subject_root":x.expected_subject_root,"expected_current_generation_root":x.expected_current_generation_root,"trace_contract":None if x.trace is None else asdict(x.trace),"workload_contract":None if x.workload is None else asdict(x.workload),"disposition":"REUSE_LOCAL_D0" if ok else "REPROVE","reusable":ok,"reasons":q,"truth_authority":False,"effect_authority":False,"promotion_authorized":False,"owner_host_proven":False,"hosted_ci_proven":False,"gate10":False,"laws":["MatchingResultRootDoesNotImplyReusableTraceProof","TraceReuseRequiresCanonicalSchemaExecutionProvenanceAndExactEventIdentity","WorkloadReuseRequiresExactEnvelopeCurrentSourceAndNoPrefixContamination","TraceAndWorkloadObligationsAreNoncompensatory","LocalReuseEligibilityDoesNotMintAuthority","TrailingContextCannotRepairFailedHardAxis"]}
 d=dig(b);b["decision_sha256"]=d;z=bytes.fromhex(d);b["k27"]=[z[0]%27,z[1]%27,z[2]%27];return b
def verify(d):
 if not isinstance(d,Mapping) or d.get("schema")!=RS:return False
 h=d.get("decision_sha256")
 if not isinstance(h,str) or H.fullmatch(h) is None:return False
 if any(d.get(k) is not False for k in ("truth_authority","effect_authority","promotion_authorized","owner_host_proven","hosted_ci_proven","gate10")):return False
 b=dict(d);b.pop("decision_sha256",None);b.pop("k27",None);e=dig(b);z=bytes.fromhex(e)
 return e==h and d.get("k27")==[z[0]%27,z[1]%27,z[2]%27]
__all__=["SecurityReuseError","SecurityReuseRequest","TraceReuseContract","WorkloadReuseContract","admit","subject_root","generation_root","verify"]
if __name__=="__main__":
 import copy,itertools,random,unittest
 def br():
  b={"schema":S,"subject":{"model_id":"zai-org/GLM-5.3","model_sha256":"1"*64,"loader_source_sha256":"2"*64,"upstream_repository":"lyogavin/airllm","upstream_release":"v4.0.0","upstream_revision":"ff35db207a0c559af9aa95d686057c3fe84f1d40"},"bound_generation":{"semantic":"s","source":"v4","runtime":"p","security":"w","evidence":"e","dependency":"d"},"current_generation":{"semantic":"s","source":"v4","runtime":"p","security":"w","evidence":"e","dependency":"d"},"exact_foreign_parents":["a","b"],"leaves":[],"disposition":"LOCAL_VERIFIED_NONPROMOTING","stale_or_missing":[],"effect_authority":False,"promotion_authorized":False,"owner_host_proven":False,"hosted_ci_proven":False,"gate10":False,"claim_ceiling":"D0","laws":[]};h=dig(b);b["receipt_sha256"]=h;z=bytes.fromhex(h);b["k27"]=[z[0]%27,z[1]%27,z[2]%27];return b
 def tr(s=2,e=2,p=2):return TraceReuseContract("3"*64,"3"*64 if s==2 else "7"*64,"4"*64,"4"*64 if e==2 else "8"*64,"4"*64,True,p==2,True)
 def wl(w=2,c=2):return WorkloadReuseContract("5"*64,"5"*64 if w==2 else "9"*64,"6"*64,"6"*64,True,c!=2,2)
 def rq(r,**kw):
  d=dict(scope="TRACE_WORKLOAD_LOCAL_SECURITY",expected_receipt_sha256=r["receipt_sha256"],expected_subject_root=subject_root(r),expected_current_generation_root=generation_root(r),trace=tr(),workload=wl());d.update(kw);return SecurityReuseRequest(**d)
 class T(unittest.TestCase):
  def test_green(self):
   r=br();d=admit(r,rq(r));self.assertTrue(d["reusable"]);self.assertTrue(verify(d));self.assertFalse(d["gate10"])
  def test_receipt_tamper(self):
   r=br();q=rq(r);r["receipt_sha256"]="a"*64;self.assertFalse(admit(r,q)["reusable"])
  def test_trace(self):
   r=br()
   for x in (tr(s=1),tr(e=1),tr(p=1)):self.assertFalse(admit(r,rq(r,trace=x))["reusable"])
  def test_workload(self):
   r=br()
   for x in (wl(w=1),wl(c=1)):self.assertFalse(admit(r,rq(r,workload=x))["reusable"])
  def test_authority(self):
   r=br();self.assertFalse(admit(r,rq(r,authority_requested=True))["reusable"])
  def test_omega8(self):
   r=br();n=0
   for a in itertools.product(range(3),repeat=8):
    rr=copy.deepcopy(r);R,S0,G,T,E,P0,W,C=a
    if R!=2:rr["receipt_sha256"]=("a" if R==1 else "b")*64
    q=rq(r,expected_subject_root=subject_root(r) if S0==2 else "c"*64,expected_current_generation_root=generation_root(r) if G==2 else "d"*64,trace=tr(T,E,P0),workload=wl(W,C));o=admit(rr,q)["reusable"];self.assertEqual(o,all(x==2 for x in a));n+=int(o)
   self.assertEqual(n,1)
  def test_hs1000(self):
   r=br();g=random.Random(20260905);fa=fr=0
   for _ in range(1000):
    a=[g.choice((False,True)) for _ in range(8)];R,S0,G,T,E,P0,W,C=a;rr=copy.deepcopy(r)
    if not R:rr["receipt_sha256"]="a"*64
    q=rq(r,expected_subject_root=subject_root(r) if S0 else "b"*64,expected_current_generation_root=generation_root(r) if G else "c"*64,trace=tr(2 if T else 1,2 if E else 1,2 if P0 else 1),workload=wl(2 if W else 1,2 if C else 1));o=admit(rr,q)["reusable"];e=all(a);fa+=int(o and not e);fr+=int(e and not o)
   self.assertEqual((fa,fr),(0,0))
  def test_13d(self):
   r=br();o=admit(r,rq(r,trace=tr(p=1)))["reusable"]
   for x in itertools.product(range(3),repeat=5):self.assertFalse(o,x)
 unittest.main(verbosity=2)
