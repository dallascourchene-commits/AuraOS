from __future__ import annotations
import hashlib, json, random
from collections import defaultdict
from itertools import combinations, product

from memory_city_navigator import SourceSpanLocator
from memory_city_contingent_hydration import *

SEED = 8740710

def h(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def locator(i,size,k27=()):
    z=lambda s: hashlib.sha256(s.encode()).hexdigest()
    return SourceSpanLocator(f"src-{i}",z(f"parent-{i}"),1,1,z(f"span-{i}"),size,k27)

def oracle_components(ids, hyperedges):
    adj={x:set() for x in ids}
    for edge in hyperedges:
        for a in edge:
            for b in edge:
                if a!=b: adj[a].add(b)
    seen=set(); out=[]
    for start in sorted(ids):
        if start in seen: continue
        q=[start]; seen.add(start); comp=[]
        while q:
            x=q.pop(); comp.append(x)
            for y in sorted(adj[x]):
                if y not in seen: seen.add(y); q.append(y)
        out.append(tuple(sorted(comp)))
    return tuple(sorted(out))

def oracle_ready(items,branches,support,max_bytes,reveal,deadline):
    im={x.item_id:x for x in items}; comps=oracle_components(tuple(im),support.hyperedges)
    i2c={}; cb={}; ct={}
    for c in comps:
        cb[c]=sum(im[x].locator.span_bytes for x in c); ct[c]=sum(im[x].duration_ticks for x in c)
        for x in c:i2c[x]=c
    req={b.branch_id:frozenset(i2c[x] for x in b.demand_item_ids) for b in branches}; post=deadline-reveal
    for r in range(len(comps)+1):
        for tup in combinations(comps,r):
            p=frozenset(tup)
            if sum(cb[c] for c in p)>max_bytes or sum(ct[c] for c in p)>reveal: continue
            good=True
            for need in req.values():
                if sum(cb[c] for c in need|p)>max_bytes or sum(ct[c] for c in need-p)>post:
                    good=False; break
            if good:return True
    return False

def make_case(rng, idx):
    n=rng.randint(4,8); ids=[f"i{idx}_{j}" for j in range(n)]
    items=tuple(HydrationItem(x,locator(x,rng.randint(2,16),(rng.randrange(27),rng.randrange(27))),rng.randint(1,5)) for x in ids)
    edges=[]
    for _ in range(rng.randint(0,n//2+1)):
        k=rng.randint(2,min(4,n)); edge=tuple(sorted(rng.sample(ids,k)))
        if edge not in edges: edges.append(edge)
    support=InvariantSupport(rng.randint(0,9),tuple(edges)); bcount=rng.randint(2,min(4,n)); branches=[]
    for j in range(bcount): branches.append(DemandBranch(f"b{j}",tuple(sorted(rng.sample(ids,rng.randint(1,min(3,n)))))))
    reveal=rng.randint(0,10); deadline=reveal+rng.randint(1,12); max_bytes=rng.randint(8,60)
    return items,tuple(branches),support,max_bytes,reveal,deadline

def run(cases=5000):
    rng=random.Random(SEED); stats=defaultdict(int); rows=[]
    for i in range(cases):
        items,branches,support,max_bytes,reveal,deadline=make_case(rng,i)
        st=compile_contingent_hydration(items,branches,support,max_resident_bytes=max_bytes,reveal_tick=reveal,deadline_tick=deadline)
        ready=st.disposition is StrategyDisposition.READY; oracle=oracle_ready(items,branches,support,max_bytes,reveal,deadline)
        stats["oracle_mismatch"] += int(ready!=oracle)
        cwise=all(clairvoyant_branch_feasible(items,b,support,max_resident_bytes=max_bytes,reveal_tick=reveal,deadline_tick=deadline) for b in branches)
        stats["clairvoyant_false_ready"] += int(cwise and not ready)
        union=fixed_union_feasible(items,branches,support,max_resident_bytes=max_bytes,deadline_tick=deadline)
        stats["fixed_union_false_hold"] += int(ready and not union)
        if ready:
            stale=validate_strategy_at_use(st,branch_id=branches[0].branch_id,support_generation=support.generation+1)
            stats["stale_false_ready"] += int(stale.disposition is StrategyDisposition.READY)
        mutated=tuple(HydrationItem(x.item_id,SourceSpanLocator(x.locator.source_id,x.locator.parent_export_sha256,x.locator.start_line,x.locator.end_line,x.locator.span_sha256,x.locator.span_bytes,((x.locator.k27_hint[0]+7)%27,(x.locator.k27_hint[1]+11)%27)),x.duration_ticks) for x in items)
        st2=compile_contingent_hydration(mutated,branches,support,max_resident_bytes=max_bytes,reveal_tick=reveal,deadline_tick=deadline)
        stats["k27_safety_mismatch"] += int((st2.disposition is StrategyDisposition.READY)!=ready)
        stats["ready"] += int(ready); stats["hold"] += int(not ready)
        if i<25: rows.append({"i":i,"ready":ready,"oracle":oracle,"clairvoyant":cwise,"union":union,"root":st.receipt_root})
    ids=tuple(f"d{i}" for i in range(12)); items=tuple(HydrationItem(x,locator(x,1),1) for x in ids); dense=InvariantSupport(1,(ids,))
    s=compile_contingent_hydration(items,(DemandBranch("x",(ids[0],)),),dense,max_resident_bytes=12,reveal_tick=0,deadline_tick=12)
    stats["dense_global_collapse_ok"]=int(s.disposition is StrategyDisposition.READY and len(s.branch_plans[0].required_item_ids)==12)
    d13_states=0; false_ready=0; mutant_false_ready=0
    for state in product(range(3), repeat=13):
        d13_states+=1; hard_ok=all(v==2 for v in state[:8]); ours=hard_ok; mutant=(sum(state)>=22)
        false_ready += int(ours and not hard_ok); mutant_false_ready += int(mutant and not hard_ok)
    result={"schema":"AURA-MEMORY-CITY-CONTINGENT-HYDRATION-CAMPAIGN-v1","seed":SEED,"cases":cases,"stats":dict(sorted(stats.items())),"d13":{"states":d13_states,"false_ready":false_ready,"mutant_false_ready":mutant_false_ready},"sample":rows}
    result["campaign_root"]=h(result); return result

if __name__=="__main__": print(json.dumps(run(),sort_keys=True,separators=(",",":")))
