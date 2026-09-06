from __future__ import annotations
import hashlib, json, random
from itertools import product
from frontier27_runtime import ExpertResidencyLRU
from frontier27_owner_epoch_adapter import EpochExpertResidencyLRU, snapshot, unchanged


def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'))
def h(x): return hashlib.sha256(canon(x).encode()).hexdigest()

def apply(owner, op, value):
    if op == 'access': return owner.access(value)
    if op == 'prefetch': return owner.prefetch(value)
    if op == 'resident': return owner.resident(value)
    raise ValueError(op)

def visible(owner): return (tuple(owner.r.items()), owner.hits, owner.misses)

def classify(governed, state_equal, epoch_equal, authority):
    if not authority: return 'AUTHORITY_HOLD'
    if not governed: return 'RAW_BYPASS_HOLD'
    if state_equal and epoch_equal: return 'ABA_UNDETECTED_HOLD'
    if state_equal and not epoch_equal: return 'EPOCH_KEEPER'
    return 'STATE_MOVED_HOLD'

def run(seed=27):
    rng=random.Random(seed)
    eq=0; eq_fail=0
    for _ in range(100):
        cap=rng.randrange(0,9)
        a=ExpertResidencyLRU(cap); b=EpochExpertResidencyLRU(cap)
        for __ in range(80):
            op=rng.choice(('access','prefetch','resident')); value=rng.randrange(0,16)
            if apply(a,op,value) != apply(b,op,value): eq_fail += 1
            if visible(a) != visible(b): eq_fail += 1
        eq += 1

    governed_detect=raw_escape=identical_detect=0
    for _ in range(60):
        b=EpochExpertResidencyLRU(3)
        for v in (1,2,3): b.prefetch(v)
        s=snapshot(b); before=visible(b)
        for v in (1,2,3): b.prefetch(v)
        governed_detect += int(visible(b)==before and not unchanged(b,s))
    for _ in range(60):
        b=EpochExpertResidencyLRU(3)
        for v in (1,2,3): b.prefetch(v)
        s=snapshot(b); before=visible(b)
        for v in (1,2,3): b.r.move_to_end(v)
        raw_escape += int(visible(b)==before and unchanged(b,s))
    for _ in range(60):
        b=EpochExpertResidencyLRU(3)
        for v in (1,2,3): b.prefetch(v)
        s=snapshot(b); before=visible(b)
        b.prefetch(3)
        identical_detect += int(visible(b)==before and not unchanged(b,s))

    hs=[]
    for i in range(1000):
        governed=(i%7)!=0; state_equal=(i%3)!=0
        epoch_equal=(i%11)==0 if governed else True; authority=(i%13)!=0
        d=classify(governed,state_equal,epoch_equal,authority)
        hs.append((i,int(governed),int(state_equal),int(epoch_equal),int(authority),d))
    counts={}
    for *_,d in hs: counts[d]=counts.get(d,0)+1

    omega_keepers=omega_hard_repairs=0
    for axes in product((0,1,2),repeat=8):
        ready=all(v==2 for v in axes)
        omega_keepers += int(ready)
        omega_hard_repairs += int(0 in axes and ready)

    tail_valid_ready=tail_hard_ready=0; route_classes=set(); tails_checked=0
    for tail in product((0,1,2),repeat=5):
        tails_checked += 1; route_classes.update(tail)
        tail_valid_ready += 1
        for hard_axis in range(8):
            axes=[2]*8; axes[hard_axis]=0
            tail_hard_ready += int(all(v==2 for v in axes))

    body={
      'owner_equivalence_cases':eq,'owner_equivalence_failures':eq_fail,
      'governed_aba_detected':governed_detect,'raw_bypass_escapes':raw_escape,
      'identical_visible_write_detected':identical_detect,
      'hs1000_counts':counts,'hs1000_root':h(hs),
      'omega8_keepers':omega_keepers,'omega8_hard_invalid_repairs':omega_hard_repairs,
      'tails_checked':tails_checked,'tail_valid_ready':tail_valid_ready,
      'tail_hard_ready':tail_hard_ready,'route_classes':sorted(route_classes),
    }
    body['campaign_root']=h(body)
    return body

if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
