from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
D0='D0_NONPROMOTING'
def _canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x):return sha256(_canon(x)).hexdigest()
def edge(a,b):
    if a==b:raise ValueError('self edge')
    return tuple(sorted((a,b)))
@dataclass(frozen=True)
class CutCertificate:
    left:frozenset[str];right:frozenset[str];absent_pairs:frozenset[tuple[str,str]];current:bool=True;trusted_partition:bool=False
    def __post_init__(self):
        if not self.left or not self.right or self.left & self.right:raise ValueError('bad partition')
    @property
    def complete_pairs(self):return frozenset(edge(a,b) for a in self.left for b in self.right)
    @property
    def complete(self):return self.absent_pairs==self.complete_pairs
@dataclass(frozen=True)
class EvidenceProbe:
    name:str;activates_couplings:frozenset[tuple[str,str]];current:bool=True;mutating:bool=True
    def __post_init__(self):
        for a,b in self.activates_couplings:
            if a==b:raise ValueError('self coupling')
@dataclass(frozen=True)
class CouplingDecision:
    status:str;final_edges:frozenset[tuple[str,str]];changed_cone:frozenset[str];invalidating_probes:tuple[str,...];reason:str;authority:str=D0;gate10:bool=False;effect_authority:bool=False;k27_coordinate:str|None=None;result_root:str=''
def _normalize_edges(edges):return frozenset(edge(*e) for e in edges)
def certificate_valid(cert,edges):
    if not cert.current:return False
    if not cert.complete and not cert.trusted_partition:return False
    return not bool(cert.complete_pairs&_normalize_edges(edges))
def _components(nodes,edges):
    adj={n:set() for n in nodes}
    for a,b in _normalize_edges(edges):adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
    out=[];seen=set()
    for n in sorted(adj):
        if n in seen:continue
        stack=[n];comp=set()
        while stack:
            x=stack.pop()
            if x in seen:continue
            seen.add(x);comp.add(x);stack.extend(adj[x]-seen)
        out.append(frozenset(comp))
    return tuple(out)
def cross_connected(cert,edges):
    for c in _components(cert.left|cert.right,edges):
        if c&cert.left and c&cert.right:return True
    return False
def apply_probes(initial_edges,probes):
    edges=set(_normalize_edges(initial_edges));added=set()
    for p in probes:
        if not p.current:return None,None,(p.name,),f'stale_probe:{p.name}'
        new=set(_normalize_edges(p.activates_couplings))-edges;added|=new;edges|=new
    return frozenset(edges),frozenset(added),(),''
def changed_cone(initial_edges,final_edges,added_edges):
    if not added_edges:return frozenset()
    nodes=set(sum((list(e) for e in final_edges),[]));touched=set(sum((list(e) for e in added_edges),[]));cone=set()
    for c in _components(nodes,final_edges):
        if c&touched:cone|=set(c)
    return frozenset(cone)
def compile_independence(cert,initial_edges,probes,*,k27_coordinate=None):
    initial=_normalize_edges(initial_edges);probes=tuple(probes)
    if not cert.current:return CouplingDecision('HOLD_CERT_CURRENTNESS',initial,frozenset(),(), 'cut certificate stale',k27_coordinate=k27_coordinate)
    if not cert.complete and not cert.trusted_partition:return CouplingDecision('HOLD_INCOMPLETE_CUT',initial,frozenset(),(), 'absence of observed coupling is not independence',k27_coordinate=k27_coordinate)
    if cross_connected(cert,initial):return CouplingDecision('HOLD_ALREADY_COUPLED',initial,frozenset(),(), 'initial topology crosses certified cut',k27_coordinate=k27_coordinate)
    final,added,stale,reason=apply_probes(initial,probes)
    if final is None:return CouplingDecision('HOLD_PROBE_CURRENTNESS',initial,frozenset(),stale,reason,k27_coordinate=k27_coordinate)
    invalidating=tuple(p.name for p in probes if _normalize_edges(p.activates_couplings)&cert.complete_pairs);cone=changed_cone(initial,final,added)
    if cross_connected(cert,final):status='HOLD_PROBE_INDUCED_COUPLING';reason='probe program invalidated independence cut; conservative join required'
    else:status='READY_D0';reason='complete cut remains independent after probe program'
    root=digest({'status':status,'left':sorted(cert.left),'right':sorted(cert.right),'initial':sorted(initial),'final':sorted(final),'added':sorted(added),'invalidating':invalidating,'cone':sorted(cone)})
    return CouplingDecision(status,final,cone,invalidating,reason,k27_coordinate=k27_coordinate,result_root=root)
def naive_preprobe_independence(cert,initial_edges,probes):return certificate_valid(cert,initial_edges)
def oracle_independence_after_probes(cert,initial_edges,probes):
    final,_,_,_=apply_probes(initial_edges,probes)
    return bool(final is not None and cert.current and (cert.complete or cert.trusted_partition) and not cross_connected(cert,final))
