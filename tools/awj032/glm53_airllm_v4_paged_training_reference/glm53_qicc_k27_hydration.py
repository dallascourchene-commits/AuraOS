"""D0 consequence-specific K27 hydration lease for GLM-5.3 paged training.

Replay identity is owned by glm53_paged_training.route_root(full ordered route).
This addendum owns only the narrower hydration consequence: are the exact source-bound
expert pages needed by this layer already present? Token assignment/order is not part of
that consequence when the required page set is identical.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from glm53_paged_training import canonical_route_matrix, route_union, route_root, Source

def _h(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
@dataclass(frozen=True)
class K27HydrationLease:
    layer:int
    page_set:tuple[int,...]
    page_set_root:str
    condition_root:str
    hydration_key:str
    claim_ceiling:str="K27_HYDRATION_ONLY"
def page_set_root(rows,*,layer,pager_binding):
    ids=route_union(rows)
    return _h({"layer":int(layer),"pager":str(pager_binding),"pages":ids})
def condition_root(source:Source,*,adapter_generation,optimizer_generation,qicc_runtime_fingerprint):
    return _h({"source":source.__dict__,"adapter_generation":adapter_generation,"optimizer_generation":optimizer_generation,"qicc_runtime_fingerprint":qicc_runtime_fingerprint})
def mint_k27_hydration_lease(source:Source,rows,*,layer,adapter_generation,optimizer_generation,qicc_runtime_fingerprint):
    matrix=canonical_route_matrix(rows); pages=route_union(matrix)
    psr=page_set_root(matrix,layer=layer,pager_binding=source.pager_binding)
    cr=condition_root(source,adapter_generation=adapter_generation,optimizer_generation=optimizer_generation,qicc_runtime_fingerprint=qicc_runtime_fingerprint)
    return K27HydrationLease(layer,pages,psr,cr,_h({"page_set":psr,"condition":cr}))
def can_reuse_hydration(a:K27HydrationLease,b:K27HydrationLease): return a.hydration_key==b.hydration_key
def replay_identity_differs(rows_a,rows_b,*,layer,pager_binding):
    return route_root(rows_a,layer=layer,pager_binding=pager_binding)!=route_root(rows_b,layer=layer,pager_binding=pager_binding)
