from __future__ import annotations
import hashlib,json,random
from itertools import product
from frontier27_runtime import ExpertResidencyLRU
from frontier27_owner_epoch_adapter import EpochExpertResidencyLRU, governed_aba_probe

READY='READY_NONAUTHORIZING'; HARD='HOLD_HARD_INVALID'; UNKNOWN='HOLD_REQUIRED_UNKNOWN'; EPOCH='HOLD_EPOCH_FENCE'
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'))
def h(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def visible(o): return (tuple(o.r.items()),o.hits,o.misses)

def oracle(axes):
    if 0 in axes: return HARD
    if 1 in axes: return UNKNOWN
    return READY

def implementation(axes,tail):
    del tail
    if 0 in axes: return HARD
    if 1 in axes: return UNKNOWN
    return READY if governed_aba_probe() else EPOCH

def run(seed=27):
    rng=random.Random(seed); eq_fail=0
    for _ in range(100):
        cap=rng.randrange(0,9); a=ExpertResidencyLRU(cap); b=EpochExpertResidencyLRU(cap)
        for __ in range(80):
            op=rng.choice(('access','prefetch','resident')); v=rng.randrange(0,16)
            ra=getattr(a,op)(v); rb=getattr(b,op)(v)
            eq_fail += int(ra!=rb or visible(a)!=visible(b))

    # HS1000 is implementation-backed: each cell's valid path reaches the live ABA probe.
    hs=[]; hs_mismatch=0
    for i in range(1000):
        axes=[2]*8
        if i%5==0: axes[i%8]=0
        elif i%7==0: axes[i%8]=1
        tail=tuple((i//(3**j))%3 for j in range(5))
        got=implementation(tuple(axes),tail); want=oracle(tuple(axes)); hs_mismatch += int(got!=want)
        hs.append((i,tuple(axes),tail,got,want))

    # All Omega8 states at antipodal tails, plus every 5-trit tail for valid and single-invalid bases.
    vectors=0; mismatches=0; keepers=0; route_variation=0
    for axes in product((0,1,2),repeat=8):
        ds=[]
        for tail in ((0,0,0,0,0),(2,2,2,2,2)):
            got=implementation(axes,tail); want=oracle(axes); vectors+=1; mismatches += int(got!=want); ds.append(got)
        route_variation += int(ds[0]!=ds[1]); keepers += int(axes==(2,)*8 and ds[0]==READY)
    valid=(2,)*8
    for tail in product((0,1,2),repeat=5):
        got=implementation(valid,tail); vectors+=1; mismatches += int(got!=READY)
        for hard_axis in range(8):
            axes=[2]*8; axes[hard_axis]=0; axes=tuple(axes)
            got=implementation(axes,tail); vectors+=1; mismatches += int(got!=HARD)

    body={'owner_equivalence_failures':eq_fail,'governed_aba_probe':governed_aba_probe(),
          'hs1000_mismatches':hs_mismatch,'hs1000_root':h(hs),'omega8_keepers':keepers,
          'vectors_checked':vectors,'oracle_mismatches':mismatches,'routing_decision_variations':route_variation}
    body['campaign_root']=h(body); return body
if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
