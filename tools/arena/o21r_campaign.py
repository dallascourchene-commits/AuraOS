import json
from dataclasses import replace
from hashlib import sha256
from tools.arena.proof_carrying_cache_consumption import *

def base():
    proto=ImmutableCacheArtifact("op","content","AUDIO","renderer","deps","producer-semantics","producer-receipt","PROJECT_TRUTH",True,"")
    a=replace(proto,claimed_artifact_root=proto.canonical_root())
    p=RuntimeBoundConsumerPermit("op","source","permit",frozenset({"AUDIO","VIDEO"}),frozenset({"PROJECT_TRUTH"}),7,True,True)
    x=EffectTimeProcessWitness("permit","source","process-current",True,True)
    r=CacheConsumptionRequest("op","source","content","AUDIO","renderer","deps","PROJECT_TRUTH","actor-a","view-a","K27:1,2,3",11)
    return a,p,x,r

def oracle(a,p,x,r):
    return (a.authenticated_producer and bool(a.producer_receipt_root) and a.claimed_artifact_root==a.canonical_root() and
            r.stable_operation_root==a.stable_operation_root and r.content_root==a.content_root and r.output_kind==a.output_kind and
            r.renderer_root==a.renderer_root and r.dependency_closure_root==a.dependency_closure_root and r.namespace==a.namespace and
            p.stable_operation_root==r.stable_operation_root and p.current and p.proof_bound and r.output_kind in p.allowed_output_kinds and
            r.namespace in p.allowed_namespaces and p.source_incarnation_root==r.source_incarnation_root and x.authenticated and x.current and
            bool(x.effect_time_process_root) and x.runtime_bound_permit_root==p.runtime_bound_permit_root and x.source_incarnation_root==r.source_incarnation_root)

def scenario(mode):
    a,p,x,r=base()
    if mode==0: pass
    elif mode==1: r=replace(r,actor="actor-b",view_id="view-b",k27_coordinate="K27:9,9,9",attempt_generation=12)
    elif mode==2: p=replace(p,current=False)
    elif mode==3: p=replace(p,proof_bound=False)
    elif mode==4: r=replace(r,stable_operation_root="op2")
    elif mode==5: a=replace(a,authenticated_producer=False)
    elif mode==6: a=replace(a,claimed_artifact_root="poison")
    elif mode==7: r=replace(r,renderer_root="renderer2")
    elif mode==8: r=replace(r,dependency_closure_root="deps2")
    elif mode==9: x=replace(x,current=False)
    elif mode==10: x=replace(x,runtime_bound_permit_root="permit2")
    elif mode==11: r=replace(r,source_incarnation_root="source2")
    return a,p,x,r

def naive_cache_hit(a,p,x,r):
    return (a.claimed_artifact_root==a.canonical_root() and r.stable_operation_root==a.stable_operation_root and r.content_root==a.content_root and
            r.output_kind==a.output_kind and r.renderer_root==a.renderer_root and r.dependency_closure_root==a.dependency_closure_root and r.namespace==a.namespace)

def naive_cache_plus_permit(a,p,x,r):
    return (naive_cache_hit(a,p,x,r) and p.current and p.proof_bound and p.stable_operation_root==r.stable_operation_root and
            r.output_kind in p.allowed_output_kinds and r.namespace in p.allowed_namespaces and p.source_incarnation_root==r.source_incarnation_root)

def run(n=24000):
    out={"cases":n,"false_reuse":0,"false_hold":0,"naive_cache_hit_unsafe":0,"naive_cache_plus_permit_unsafe":0,"authority_promotions":0}; reasons={}
    for i in range(n):
        a,p,x,r=scenario(i%12); expected=oracle(a,p,x,r); d=decide(a,p,x,r); reuse=d.disposition is Disposition.REUSE_D0
        out["false_reuse"]+=int(reuse and not expected); out["false_hold"]+=int((not reuse) and expected)
        out["naive_cache_hit_unsafe"]+=int(naive_cache_hit(a,p,x,r) and not expected)
        out["naive_cache_plus_permit_unsafe"]+=int(naive_cache_plus_permit(a,p,x,r) and not expected)
        out["authority_promotions"]+=int(d.cache_write_authority or d.render_authority or d.effect_authority or d.gate10)
        reasons[d.reason]=reasons.get(d.reason,0)+1
    out["reasons"]=dict(sorted(reasons.items())); out["root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return out
if __name__=="__main__": print(json.dumps(run(),sort_keys=True,indent=2))
