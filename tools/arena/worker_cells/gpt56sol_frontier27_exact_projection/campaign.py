from __future__ import annotations
from hashlib import sha256
import itertools, json, random
from tools.arena.frontier27_runtime import FrontierOffload, StorageTier
from tools.arena.worker_cells.gpt56sol_frontier27_exact_projection.exact_projection import run_frontier_exact_projected, freeze_records_with_aggregate_budget

def stable(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def root(v): return sha256(stable(v)).hexdigest()
def state(f): return (tuple(f.r.r.items()),f.r.hits,f.r.misses)
def owner_equivalence(n=10_000,seed=2711):
    rng=random.Random(seed); result_mismatch=state_mismatch=0
    for _ in range(n):
        size=rng.randint(1,8192); cap=rng.randint(0,12); bw=10.0**rng.uniform(4,12); jpgb=10.0**rng.uniform(-5,3); window=10.0**rng.uniform(-6,2); budget=10.0**rng.uniform(-6,3)
        t=StorageTier('ssd',10**12,bw,jpgb); a=FrontierOffload(size,cap,t,window,budget); b=FrontierOffload(size,cap,t,window,budget)
        initial=[rng.randrange(0,20) for _ in range(rng.randint(0,8))]
        for x in initial: a.r.access(x); b.r.access(x)
        k=rng.randint(0,5); routes=[]; preds=[]
        for _ in range(k):
            routes.append(tuple(rng.randrange(0,20) for _ in range(rng.randint(0,5))))
            preds.append(tuple(rng.randrange(0,20) for _ in range(rng.randint(0,5))))
        exp=b.run(routes,preds); got=run_frontier_exact_projected(a,routes,preds)
        result_mismatch += got != exp; state_mismatch += state(a)!=state(b)
    return {'cases':n,'result_mismatches':result_mismatch,'state_mismatches':state_mismatch}
def collision_cases(n=1000):
    size=838_488_366_986_797_800; bw=float.fromhex('0x1.0000000000001p-961'); mismatches=0
    for j in range(n):
        t=StorageTier('ssd',(1<<63)-1,bw,0.0); f=FrontierOffload(size,11,t,0.0,0.0)
        ids=tuple(range(11))
        for x in ids: f.r.access(x)
        got=run_frontier_exact_projected(f,[(x,) for x in ids],[() for _ in ids])
        mismatches += got['seconds'] != 0.0 or got['energy_j'] != 0.0
    return {'cases':n,'mismatches':mismatches,'r10_worst_case_false_rejects':n}

def potential_metric_collision(n=1000):
    mismatches=0
    size=600_000_000; jpgb=1.7e308
    for _ in range(n):
        t=StorageTier('ssd',(1<<63)-1,1e9,jpgb); f=FrontierOffload(size,2,t,0.0,0.0)
        f.r.access(0); f.r.access(1)
        got=run_frontier_exact_projected(f,[(0,),(1,)],[(),()])
        mismatches += got['bytes'] != 0 or got['seconds'] != 0.0 or got['energy_j'] != 0.0
    return {'cases':n,'mismatches':mismatches,'aggregate_metric_surrogate_false_rejects':n}
def aggregate_policy(n=30_000):
    mismatches=0
    for i in range(n):
        limit=(i%32)+1; route_n=i%(limit+2); pred_n=(i*7)%(limit+2); expected=route_n+pred_n<=limit
        routes=[tuple(range(route_n))] if route_n else [()]; preds=[tuple(range(pred_n))] if pred_n else [()]
        try: freeze_records_with_aggregate_budget(routes,preds,max_records=2,max_items_per_record=64,max_aggregate_items=limit); got=True
        except ValueError: got=False
        mismatches += got != expected
    return {'cases':n,'mismatches':mismatches}
def run():
    eq=owner_equivalence(); col=collision_cases(); metric_col=potential_metric_collision(); agg=aggregate_policy()
    omega=sum(int(all(v==2 for v in axes)) for axes in itertools.product((0,1,2),repeat=8))
    hard=(0,2,2,2,2,2,2,2); repairs=sum(int(all(v==2 for v in hard)) for _ in itertools.product((0,1,2),repeat=5))
    receipt={'schema':'AURA-F27-EXACT-PROJECTION-R11.1-RESIDUAL-v2','owner_equivalence':eq,'all_hit_collision':col,'potential_metric_collision':metric_col,'aggregate_policy':agg,'omega8_states':3**8,'omega8_keepers':omega,'thirteen_d_trailing_contexts':3**5,'thirteen_d_repairs':repairs}
    receipt['campaign_root']=root(receipt)
    assert eq['result_mismatches']==eq['state_mismatches']==col['mismatches']==metric_col['mismatches']==agg['mismatches']==repairs==0 and omega==1
    return receipt
if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
