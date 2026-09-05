from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json, re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA='AURA-GENERATION-AWARE-SECURITY-REPROOF-v1'
GEN_COMPAT_PARENT='0ca532c02ce0bb427428bbf11d97cba58d61c6e73482aa347c658e3ddecfb747'
EFFICIENCY_REPLAY_PARENT='d1299c440ae1c2109c6999578f652186e81cc2b3fbae721a6241e0fbf2b33c09'
SECURITY_GRAPH_PARENT='bafcbbcf8c0e3e8fb9d690f3dc8a735ea531fed6c85743e7237ced119df86375'
HEX40=re.compile(r'^[0-9a-f]{40}$'); HEX64=re.compile(r'^[0-9a-f]{64}$'); ID=re.compile(r'^[A-Z][A-Z0-9_]{0,63}$'); FIELD=re.compile(r'^[a-z][a-z0-9_]{0,63}$')

class ReproofError(ValueError): pass
class ChangeClass(str,Enum):
    EXACT_UNCHANGED='EXACT_UNCHANGED'; PROOF_NEUTRAL='PROOF_NEUTRAL'; CONSEQUENCE_CHANGED='CONSEQUENCE_CHANGED'; UNKNOWN='UNKNOWN'
class Decision(str,Enum):
    REUSE_EXACT='REUSE_EXACT'; REPROVE_CONE='REPROVE_CONE'; HOLD_UNKNOWN='HOLD_UNKNOWN'

def cjson(v:Any)->bytes:
    try:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    except Exception as e: raise ReproofError('NON_CANONICAL') from e
def digest(v:Any)->str:return sha256(cjson(v)).hexdigest()
def h40(x,label='generation'):
    if not isinstance(x,str) or not HEX40.fullmatch(x):raise ReproofError('MALFORMED_'+label.upper())
    return x
def h64(x,label='root'):
    if not isinstance(x,str) or not HEX64.fullmatch(x):raise ReproofError('MALFORMED_'+label.upper())
    return x
def sid(x,label='identity'):
    if not isinstance(x,str) or not ID.fullmatch(x):raise ReproofError('MALFORMED_'+label.upper())
    return x
def field_id(x,label='semantic_field'):
    if not isinstance(x,str) or not FIELD.fullmatch(x):raise ReproofError('MALFORMED_'+label.upper())
    return x

DEPS={
'MODEL_BYTES':(), 'LOADER_SOURCE':(), 'PACKAGE_MANIFEST':(), 'TRACE_PROVENANCE':(), 'WORKLOAD_ENV':(),
'SAFETENSORS_STRUCTURE':('MODEL_BYTES',), 'MODEL_ALLOWLIST':('MODEL_BYTES',),
'REMOTE_CODE_POLICY':('LOADER_SOURCE','PACKAGE_MANIFEST'), 'NONDESTRUCTIVE_LOAD':('LOADER_SOURCE',),
'SECURE_ENTRYPOINT':('SAFETENSORS_STRUCTURE','MODEL_ALLOWLIST','LOADER_SOURCE','PACKAGE_MANIFEST','REMOTE_CODE_POLICY','NONDESTRUCTIVE_LOAD'),
'SECURITY_RECEIPT':('SECURE_ENTRYPOINT',),
'TRACE_WORKLOAD_REUSE':('SECURITY_RECEIPT','TRACE_PROVENANCE','WORKLOAD_ENV'),
'FINAL_REUSE_RECEIPT':('TRACE_WORKLOAD_REUSE',),
}
DIM_TO_NODE={
'model_root':'MODEL_BYTES','loader_root':'LOADER_SOURCE','package_root':'PACKAGE_MANIFEST','trace_root':'TRACE_PROVENANCE','workload_root':'WORKLOAD_ENV',
'safetensors_root':'SAFETENSORS_STRUCTURE','allowlist_root':'MODEL_ALLOWLIST','remote_code_policy_root':'REMOTE_CODE_POLICY','nondestructive_root':'NONDESTRUCTIVE_LOAD',
'entrypoint_root':'SECURE_ENTRYPOINT','security_receipt_root':'SECURITY_RECEIPT','reuse_projection_root':'TRACE_WORKLOAD_REUSE','final_receipt_root':'FINAL_REUSE_RECEIPT'
}
SEMANTIC_FIELDS=tuple(DIM_TO_NODE)

@dataclass(frozen=True)
class GenerationSurface:
    generation:str
    schema_root:str
    admission_surface_root:str
    verifier_generation:str
    semantic_roots:tuple[tuple[str,str],...]
    provider_attested:bool
    current:bool
    complete:bool
    truth_authority:bool=False
    effect_authority:bool=False
    gate10:bool=False
    def normalized(self):
        h40(self.generation);h64(self.schema_root,'schema_root');h64(self.admission_surface_root,'admission_surface_root');h40(self.verifier_generation,'verifier_generation')
        if any(type(x) is not bool for x in (self.provider_attested,self.current,self.complete,self.truth_authority,self.effect_authority,self.gate10)):raise ReproofError('MALFORMED_BOOL')
        pairs=tuple(sorted((field_id(k,'semantic_field'),h64(v,'semantic_root')) for k,v in self.semantic_roots))
        if len(pairs)!=len(set(k for k,_ in pairs)):raise ReproofError('DUPLICATE_SEMANTIC_FIELD')
        if set(k for k,_ in pairs)!=set(SEMANTIC_FIELDS):raise ReproofError('INCOMPLETE_SEMANTIC_SURFACE')
        return GenerationSurface(self.generation,self.schema_root,self.admission_surface_root,self.verifier_generation,pairs,self.provider_attested,self.current,self.complete,self.truth_authority,self.effect_authority,self.gate10)
    def roots(self):return dict(self.normalized().semantic_roots)

@dataclass(frozen=True)
class CompatibilityReceipt:
    schema:str; change_class:ChangeClass; decision:Decision; old_generation:str; current_generation:str
    changed_fields:tuple[str,...]; recompute_order:tuple[str,...]; reusable:tuple[str,...]
    old_surface_root:str; current_surface_root:str; provider_status_separate:bool=True
    d0:bool=True; truth_authority:bool=False; effect_authority:bool=False; gate10:bool=False; receipt_root:str=''
    def payload(self):
        d=asdict(self);d['change_class']=self.change_class.value;d['decision']=self.decision.value;d.pop('receipt_root');return d
    def verify(self):
        if self.schema!=SCHEMA+'-RECEIPT':return False
        if any(type(x) is not bool for x in (self.provider_status_separate,self.d0,self.truth_authority,self.effect_authority,self.gate10)):return False
        if not self.provider_status_separate or not self.d0 or self.truth_authority or self.effect_authority or self.gate10:return False
        try:h40(self.old_generation);h40(self.current_generation);h64(self.old_surface_root);h64(self.current_surface_root);h64(self.receipt_root)
        except ReproofError:return False
        return self.receipt_root==digest(self.payload())

def surface_root(s:GenerationSurface)->str:
    n=s.normalized();d=asdict(n);return digest({'schema':SCHEMA+'-SURFACE',**d})

def descendants(changed:Iterable[str])->set[str]:
    roots={sid(x,'node') for x in changed}
    if not roots<=set(DEPS):raise ReproofError('UNKNOWN_NODE')
    out=set(roots);progress=True
    while progress:
        progress=False
        for n,deps in DEPS.items():
            if n not in out and any(d in out for d in deps):out.add(n);progress=True
    return out

def topo(subset:set[str])->tuple[str,...]:
    seen=set();out=[]
    def visit(n):
        if n in seen:return
        for d in sorted(DEPS[n]):
            if d in subset:visit(d)
        seen.add(n);out.append(n)
    for n in sorted(subset):visit(n)
    return tuple(out)

def classify(old:GenerationSurface,current:GenerationSurface)->CompatibilityReceipt:
    o=old.normalized();c=current.normalized();osr=surface_root(o);csr=surface_root(c)
    if not c.current or not c.complete or not c.provider_attested or c.truth_authority or c.effect_authority or c.gate10:
        cc=ChangeClass.UNKNOWN;dec=Decision.HOLD_UNKNOWN;changed=();order=();reuse=()
    else:
        oroot=o.roots();croot=c.roots();changed_fields=tuple(sorted(k for k in SEMANTIC_FIELDS if oroot[k]!=croot[k]))
        structural=(o.schema_root!=c.schema_root or o.admission_surface_root!=c.admission_surface_root or o.verifier_generation!=c.verifier_generation)
        if not changed_fields and not structural:
            cc=ChangeClass.EXACT_UNCHANGED if o.generation==c.generation else ChangeClass.PROOF_NEUTRAL
            dec=Decision.REUSE_EXACT;changed=();order=();reuse=tuple(sorted(DEPS))
        elif not changed_fields and structural:
            cc=ChangeClass.UNKNOWN;dec=Decision.HOLD_UNKNOWN;changed=();order=();reuse=()
        else:
            cc=ChangeClass.CONSEQUENCE_CHANGED;dec=Decision.REPROVE_CONE;changed=changed_fields
            cone=descendants(DIM_TO_NODE[k] for k in changed_fields);order=topo(cone);reuse=tuple(sorted(set(DEPS)-cone))
    r=CompatibilityReceipt(SCHEMA+'-RECEIPT',cc,dec,o.generation,c.generation,changed,order,reuse,osr,csr)
    return CompatibilityReceipt(**{**r.__dict__,'receipt_root':digest(r.payload())})

def crystalline_admission(state8:Sequence[int])->bool:return len(state8)==8 and all(type(x) is int and x==2 for x in state8)
def admission_13d(state13:Sequence[int])->bool:
    return len(state13)==13 and all(type(x) is int and x in (0,1,2) for x in state13) and crystalline_admission(state13[:8])
