from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
import itertools, json, re
from typing import Iterable, Mapping, Sequence

SCHEMA='AURA-O7-EXTERNAL-AUTHENTICATION-CUTSET-v1'
AUTHORITY='D0_NONPROMOTING'
HEX40=re.compile(r'^[0-9a-f]{40}$')
HEX64=re.compile(r'^[0-9a-f]{64}$')
ID=re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')

AGENT08_HEAD='1553ae94d934690e8f490632b4c4e5dc98b10e4a'
AGENT08_RECEIPT='d1299c440ae1c2109c6999578f652186e81cc2b3fbae721a6241e0fbf2b33c09'
AGENT12_HEAD='1e24402224a7d0c12f11eea4c2c0d3b23d4c5341'
AGENT12_GRAPH='bafcbbcf8c0e3e8fb9d690f3dc8a735ea531fed6c85743e7237ced119df86375'

SUBJECTS=(
 'EFFICIENCY_PARENT_27','COST_PARENT_07','AIRLLM_SECURITY_PARENT','EVIDENCE_DAG_PARENT'
)

class CutsetError(ValueError): pass
class ProviderState(str,Enum):
    ATTESTED='ATTESTED'; OBSERVED='OBSERVED'; CONTESTED='CONTESTED'; EXPIRED='EXPIRED'; INDETERMINATE='INDETERMINATE'
class Decision(str,Enum):
    REPROVE_LOCAL_FIRST='REPROVE_LOCAL_FIRST'
    HOLD_AUTHENTICATION_CUTSET='HOLD_AUTHENTICATION_CUTSET'
    ELIGIBLE_FOR_FRESH_READJUDICATION='ELIGIBLE_FOR_FRESH_READJUDICATION'
    HOLD_MALFORMED='HOLD_MALFORMED'

def canonical(x):
    try: return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
    except (TypeError,ValueError) as e: raise CutsetError('NON_CANONICAL') from e

def digest(x): return sha256(canonical(x).encode('ascii')).hexdigest()
def _id(x):
    if not isinstance(x,str) or not ID.fullmatch(x): raise CutsetError('BAD_ID')
    return x
def _h40(x):
    if not isinstance(x,str) or not HEX40.fullmatch(x): raise CutsetError('BAD_GEN')
    return x
def _h64(x):
    if not isinstance(x,str) or not HEX64.fullmatch(x): raise CutsetError('BAD_ROOT')
    return x

@dataclass(frozen=True)
class ParentReplay:
    owner: str
    generation: str
    expected_generation: str
    projection_root: str
    expected_projection_root: str
    graph_root: str|None=None
    expected_graph_root: str|None=None
    source_bound: bool=True
    d0: bool=True
    effect_authority: bool=False
    gate10: bool=False
    def validate(self):
        _id(self.owner); _h40(self.generation); _h40(self.expected_generation)
        _h64(self.projection_root); _h64(self.expected_projection_root)
        if (self.graph_root is None)!=(self.expected_graph_root is None): raise CutsetError('GRAPH_PAIR')
        if self.graph_root is not None: _h64(self.graph_root); _h64(self.expected_graph_root)
        for v in (self.source_bound,self.d0,self.effect_authority,self.gate10):
            if type(v) is not bool: raise CutsetError('BOOL_AMBIGUITY')
    def exact(self)->bool:
        self.validate()
        return (self.generation==self.expected_generation and
                self.projection_root==self.expected_projection_root and
                (self.graph_root is None or self.graph_root==self.expected_graph_root) and
                self.source_bound is True and self.d0 is True and
                self.effect_authority is False and self.gate10 is False)

@dataclass(frozen=True)
class SubjectAuth:
    subject: str
    state: ProviderState
    evidence_root: str
    observation_generation: str
    external_receipt_root: str|None=None
    def validate(self):
        _id(self.subject); _h64(self.evidence_root); _id(self.observation_generation)
        if not isinstance(self.state,ProviderState): raise CutsetError('BAD_PROVIDER_STATE')
        if self.external_receipt_root is not None: _h64(self.external_receipt_root)
        if self.state is ProviderState.ATTESTED and self.external_receipt_root is None:
            raise CutsetError('ATTESTED_REQUIRES_EXTERNAL_RECEIPT')

@dataclass(frozen=True)
class AttestationBundle:
    bundle_id: str
    covers: tuple[str,...]
    provider_id: str
    expected_schema: str='AURA-EXTERNAL-ATTESTATION-v1'
    def normalized(self):
        bid=_id(self.bundle_id); pid=_id(self.provider_id)
        cov=tuple(sorted({_id(x) for x in self.covers}))
        if not cov or len(cov)!=len(self.covers) or any(x not in SUBJECTS for x in cov): raise CutsetError('BAD_BUNDLE')
        return AttestationBundle(bid,cov,pid,self.expected_schema)

@dataclass(frozen=True)
class CutsetPlan:
    decision: Decision
    local_reproof_owners: tuple[str,...]
    missing_subjects: tuple[str,...]
    minimum_bundle_ids: tuple[str,...]
    parent_generations: tuple[tuple[str,str],...]
    auth_surface_root: str
    authority: str=AUTHORITY
    truth_authority: bool=False
    effect_authority: bool=False
    gate10: bool=False
    receipt_root: str=''
    def payload(self):
        d=asdict(self); d['decision']=self.decision.value; d.pop('receipt_root'); return d
    def seal(self):
        return CutsetPlan(**{**asdict(self),'receipt_root':digest(self.payload())})
    def verify(self):
        if self.authority!=AUTHORITY or any(type(v) is not bool for v in (self.truth_authority,self.effect_authority,self.gate10)): return False
        if self.truth_authority or self.effect_authority or self.gate10: return False
        try: _h64(self.auth_surface_root); _h64(self.receipt_root)
        except CutsetError: return False
        return self.receipt_root==digest(self.payload())

def bundle_catalog():
    # No universal bundle: minimum routing remains consequence-sensitive.
    return (
      AttestationBundle('BUNDLE_EFFICIENCY',('EFFICIENCY_PARENT_27','COST_PARENT_07'),'PROVIDER_A'),
      AttestationBundle('BUNDLE_SECURITY',('AIRLLM_SECURITY_PARENT','EVIDENCE_DAG_PARENT'),'PROVIDER_B'),
      AttestationBundle('BUNDLE_RUNTIME_SECURITY',('EFFICIENCY_PARENT_27','AIRLLM_SECURITY_PARENT'),'PROVIDER_C'),
      AttestationBundle('BUNDLE_COST_DAG',('COST_PARENT_07','EVIDENCE_DAG_PARENT'),'PROVIDER_D'),
      *(AttestationBundle('BUNDLE_'+s,(s,),'PROVIDER_'+str(i+10)) for i,s in enumerate(SUBJECTS)),
    )

def minimum_cover(missing:Iterable[str], bundles:Sequence[AttestationBundle]):
    need=set(missing)
    if not need: return ()
    norm=tuple(b.normalized() for b in bundles)
    candidates=[b for b in norm if need.intersection(b.covers)]
    best=None
    for r in range(1,len(candidates)+1):
        for combo in itertools.combinations(candidates,r):
            covered=set().union(*(set(b.covers) for b in combo))
            if need <= covered:
                ids=tuple(sorted(b.bundle_id for b in combo))
                score=(len(ids),ids)
                if best is None or score<best[0]: best=(score,ids)
        if best: return best[1]
    raise CutsetError('UNCOVERABLE_AUTH_SUBJECT')

def compile_plan(parents:Sequence[ParentReplay], auth:Mapping[str,SubjectAuth], bundles=None):
    try:
        if len(parents)!=2: raise CutsetError('EXACT_TWO_PARENT_REPLAYS_REQUIRED')
        for p in parents: p.validate()
        owners=tuple(sorted(p.owner for p in parents))
        if len(set(owners))!=2: raise CutsetError('DUPLICATE_OWNER')
        expected={'AGENT08_EFFICIENCY_REPLAY','AGENT12_SECURITY_DAG'}
        if set(owners)!=expected: raise CutsetError('WRONG_PARENT_PAIR')
        for s,a in auth.items():
            if s!=a.subject or s not in SUBJECTS: raise CutsetError('AUTH_KEY_MISMATCH')
            a.validate()
        if set(auth)!=set(SUBJECTS): raise CutsetError('AUTH_SURFACE_INCOMPLETE')
        local_bad=tuple(sorted(p.owner for p in parents if not p.exact()))
        surface_root=digest({'schema':SCHEMA+'-AUTH-SURFACE','auth':[asdict(auth[s]) for s in sorted(auth)]})
        generations=tuple(sorted((p.owner,p.generation) for p in parents))
        if local_bad:
            plan=CutsetPlan(Decision.REPROVE_LOCAL_FIRST,local_bad,(),(),generations,surface_root)
            return plan.seal()
        missing=tuple(sorted(s for s in SUBJECTS if auth[s].state is not ProviderState.ATTESTED))
        if missing:
            cut=minimum_cover(missing,bundles or bundle_catalog())
            plan=CutsetPlan(Decision.HOLD_AUTHENTICATION_CUTSET,(),missing,cut,generations,surface_root)
            return plan.seal()
        plan=CutsetPlan(Decision.ELIGIBLE_FOR_FRESH_READJUDICATION,(),(),(),generations,surface_root)
        return plan.seal()
    except CutsetError:
        raise

def default_parents():
    return (
      ParentReplay('AGENT08_EFFICIENCY_REPLAY',AGENT08_HEAD,AGENT08_HEAD,AGENT08_RECEIPT,AGENT08_RECEIPT),
      ParentReplay('AGENT12_SECURITY_DAG',AGENT12_HEAD,AGENT12_HEAD,AGENT12_GRAPH,AGENT12_GRAPH,AGENT12_GRAPH,AGENT12_GRAPH),
    )

def make_auth(states=None):
    states=states or {s:ProviderState.OBSERVED for s in SUBJECTS}
    out={}
    for i,s in enumerate(SUBJECTS):
        st=states[s]; root=digest({'subject':s,'evidence':i})
        ext=digest({'external':s,'provider':'fixture'}) if st is ProviderState.ATTESTED else None
        out[s]=SubjectAuth(s,st,root,'OBS_GEN_'+str(i),ext)
    return out
