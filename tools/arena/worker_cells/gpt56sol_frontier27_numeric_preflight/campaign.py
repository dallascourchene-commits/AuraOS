from __future__ import annotations
from hashlib import sha256
import itertools, json, math, random
from tools.arena.worker_cells.gpt56sol_frontier27_numeric_preflight.transactional_preflight import MAX_GOVERNED_INT, _freeze_records

LEGACY_BOUNDARY_SIZE=281_406_274_007_040
LEGACY_BOUNDARY_BW=float.fromhex('0x1.fffffffffffe1p-962')
LEGACY_BOUNDARY_ROUTES=(1,4096)*8
FRONTIER_BOUNDARY_SIZE=838_488_366_986_797_800
FRONTIER_BOUNDARY_BW=float.fromhex('0x1.0000000000001p-961')
FRONTIER_BOUNDARY_ROUTES=(1,)*11

def stable(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def root(v): return sha256(stable(v)).hexdigest()

def _finite_add_sequence(size, route_lengths, pred_lengths, bandwidth, jpgb, mode):
    try:
        if type(size) is not int or not 1 <= size <= MAX_GOVERNED_INT: return False
        if type(bandwidth) is not float or not math.isfinite(bandwidth) or bandwidth <= 0: return False
        if type(jpgb) is not float or not math.isfinite(jpgb) or jpgb < 0: return False
        total=sum(route_lengths)+sum(pred_lengths)
        if total*size > MAX_GOVERNED_INT: return False
        if mode=='legacy':
            secs=energy=0.0; unit_s=size/bandwidth; unit_e=size/1e9*jpgb
            for r,p in zip(route_lengths,pred_lengths):
                secs += (r*size)/bandwidth; energy += (r*size)/1e9*jpgb
                if not math.isfinite(secs) or not math.isfinite(energy): return False
                for _ in range(p):
                    secs += unit_s; energy += unit_e
                    if not math.isfinite(secs) or not math.isfinite(energy): return False
            return True
        if mode=='frontier':
            secs=energy=0.0; unit_s=size/bandwidth; unit_e=size/1e9*jpgb
            for _ in range(total):
                secs += unit_s; energy += unit_e
                if not math.isfinite(secs) or not math.isfinite(energy): return False
            return True
        return False
    except (OverflowError,ZeroDivisionError): return False

def implementation_decision(*, size, route_lengths, pred_lengths, bandwidth, jpgb, window_product, records_valid, authority_d0, mode):
    if len(route_lengths)!=len(pred_lengths): return False
    scalar_ok=type(size) is int and 1<=size<=MAX_GOVERNED_INT
    transfer_count=sum(route_lengths)+sum(pred_lengths) if all(type(x) is int and x>=0 for x in route_lengths+pred_lengths) else MAX_GOVERNED_INT+1
    byte_ok=scalar_ok and transfer_count*size<=MAX_GOVERNED_INT
    bandwidth_ok=type(bandwidth) is float and math.isfinite(bandwidth) and bandwidth>0
    jpgb_ok=type(jpgb) is float and math.isfinite(jpgb) and jpgb>=0
    window_ok=type(window_product) is float and math.isfinite(window_product) and window_product>=0
    accumulation_ok=False
    if byte_ok and bandwidth_ok and jpgb_ok:
        accumulation_ok=_finite_add_sequence(size,route_lengths,pred_lengths,bandwidth,jpgb,mode)
    return all((scalar_ok,byte_ok,bandwidth_ok,jpgb_ok,window_ok,records_valid,authority_d0,accumulation_ok))

def oracle(**x):
    if type(x['size']) is not int or x['size']<1 or x['size']>9223372036854775807: return False
    if len(x['route_lengths'])!=len(x['pred_lengths']): return False
    lengths=x['route_lengths']+x['pred_lengths']
    if any(type(v) is not int or v<0 for v in lengths): return False
    n=sum(lengths)*x['size']
    if n>9223372036854775807: return False
    bw=x['bandwidth']; jpgb=x['jpgb']; wp=x['window_product']
    if type(bw) is not float or not math.isfinite(bw) or bw<=0: return False
    if type(jpgb) is not float or not math.isfinite(jpgb) or jpgb<0: return False
    if type(wp) is not float or not math.isfinite(wp) or wp<0: return False
    if not x['records_valid'] or not x['authority_d0']: return False
    mode=x['mode']
    try:
        if mode=='legacy':
            s=e=0.0
            for rl,pl in zip(x['route_lengths'],x['pred_lengths']):
                s=s+(rl*x['size'])/bw; e=e+(rl*x['size'])/1_000_000_000.0*jpgb
                if not math.isfinite(s) or not math.isfinite(e): return False
                for _ in range(pl):
                    s=s+x['size']/bw; e=e+x['size']/1_000_000_000.0*jpgb
                    if not math.isfinite(s) or not math.isfinite(e): return False
            return True
        if mode=='frontier':
            s=e=0.0
            for _ in range(sum(lengths)):
                s=s+x['size']/bw; e=e+x['size']/1_000_000_000.0*jpgb
                if not math.isfinite(s) or not math.isfinite(e): return False
            return True
        return False
    except (OverflowError,ZeroDivisionError): return False

def random_case(rng):
    if rng.random()<0.35:
        m=rng.choice(('legacy','frontier')); k=rng.randint(1,4)
        routes=tuple(rng.randint(0,4) for _ in range(k)); preds=tuple(rng.randint(0,4) for _ in range(k))
        size=rng.randint(1,1_000_000); bw=10.0**rng.uniform(3,12); jpgb=10.0**rng.uniform(-6,4); window=10.0**rng.uniform(-6,6)
        return dict(size=size,route_lengths=routes,pred_lengths=preds,bandwidth=bw,jpgb=jpgb,window_product=bw*window,records_valid=True,authority_d0=True,mode=m)
    family=rng.randrange(11)
    base=dict(size=4096,route_lengths=(2,1),pred_lengths=(1,2),bandwidth=1e9,jpgb=2.0,window_product=1e8,records_valid=True,authority_d0=True,mode='frontier')
    if family==0: base['size']=10**1000
    elif family==1: base['route_lengths']=(MAX_GOVERNED_INT,)
    elif family==2: base['bandwidth']=5e-324
    elif family==3: base['jpgb']=1e308; base['size']=MAX_GOVERNED_INT; base['route_lengths']=(1,); base['pred_lengths']=(0,)
    elif family==4: base['window_product']=math.inf
    elif family==5: base['records_valid']=False
    elif family==6: base['authority_d0']=False
    elif family==7: base['bandwidth']=math.inf
    elif family==8: base['size']=0
    elif family==9: base.update(size=LEGACY_BOUNDARY_SIZE,route_lengths=LEGACY_BOUNDARY_ROUTES,pred_lengths=(0,)*16,bandwidth=LEGACY_BOUNDARY_BW,jpgb=0.0,window_product=0.0,mode='legacy')
    else: base.update(size=FRONTIER_BOUNDARY_SIZE,route_lengths=FRONTIER_BOUNDARY_ROUTES,pred_lengths=(0,)*11,bandwidth=FRONTIER_BOUNDARY_BW,jpgb=0.0,window_product=0.0,mode='frontier')
    return base

class _OuterFailure:
    def __init__(self,exc,on_next=False): self.exc=exc; self.on_next=on_next; self.used=False
    def __iter__(self):
        if not self.on_next: raise self.exc
        return self
    def __next__(self):
        if not self.used: self.used=True; return (1,)
        raise self.exc
class _InnerFailure(_OuterFailure):
    def __next__(self):
        if not self.used: self.used=True; return 1
        raise self.exc
class _InfiniteOuter:
    def __iter__(self):
        while True: yield (1,)
class _InfiniteInner:
    def __iter__(self):
        while True: yield 1

def materialization_case(i):
    family=i%10
    if family==0: routes,preds,expected=[(1,2),(3,)],[(1,),(3,4)],True
    elif family==1: routes,preds,expected=_OuterFailure(RuntimeError('outer')),[],False
    elif family==2: routes,preds,expected=_OuterFailure(KeyError('outer'),True),[(1,)],False
    elif family==3: routes,preds,expected=[_InnerFailure(LookupError('inner'))],[(1,)],False
    elif family==4: routes,preds,expected=[_InnerFailure(RuntimeError('inner'),True)],[(1,)],False
    elif family==5: routes,preds,expected=_InfiniteOuter(),[(1,)]*8,False
    elif family==6: routes,preds,expected=[_InfiniteInner()],[(1,)],False
    elif family==7: routes,preds,expected=[(True,)],[(1,)],False
    elif family==8: routes,preds,expected=[(1,)],[(1,),(2,)],False
    else: routes,preds,expected=[(),(1,)],[(),(1,)],True
    try: _freeze_records(routes,preds,max_records=8,max_items_per_record=8); got=True
    except ValueError: got=False
    return got,expected

def materialization_campaign(n=30_000):
    mismatches=false_accepts=false_rejects=uncontrolled=0
    for i in range(n):
        try: got,expected=materialization_case(i)
        except Exception: uncontrolled+=1; continue
        mismatches+=got!=expected; false_accepts+=got and not expected; false_rejects+=expected and not got
    hs_escapes=0
    for family in range(10):
        for j in range(1000):
            got,expected=materialization_case(family*1000+j); hs_escapes+=got!=expected
    return dict(cases=n,mismatches=mismatches,false_accepts=false_accepts,false_rejects=false_rejects,uncontrolled_exceptions=uncontrolled,hs1000_families=10,hs1000_cases=10_000,hs1000_escapes=hs_escapes)

def run(seed=270825,n=100_000):
    rng=random.Random(seed); mismatches=false_accepts=false_holds=0
    for _ in range(n):
        c=random_case(rng); got=implementation_decision(**c); exp=oracle(**c)
        mismatches+=got!=exp; false_accepts+=got and not exp; false_holds+=exp and not got
    hs=[random_case(random.Random(10_000+i)) for i in range(9)]
    hs.extend([
        dict(size=LEGACY_BOUNDARY_SIZE,route_lengths=LEGACY_BOUNDARY_ROUTES,pred_lengths=(0,)*16,bandwidth=LEGACY_BOUNDARY_BW,jpgb=0.0,window_product=0.0,records_valid=True,authority_d0=True,mode='legacy'),
        dict(size=FRONTIER_BOUNDARY_SIZE,route_lengths=FRONTIER_BOUNDARY_ROUTES,pred_lengths=(0,)*11,bandwidth=FRONTIER_BOUNDARY_BW,jpgb=0.0,window_product=0.0,records_valid=True,authority_d0=True,mode='frontier'),
    ])
    hs_escapes=0
    for family in hs:
        for _ in range(1000): hs_escapes+=implementation_decision(**family)!=oracle(**family)
    invocation=materialization_campaign()
    omega_keeper=sum(int(all(v==2 for v in axes)) for axes in itertools.product((0,1,2),repeat=8))
    hard_invalid=(0,2,2,2,2,2,2,2); repairs=sum(int(all(v==2 for v in hard_invalid)) for _ in itertools.product((0,1,2),repeat=5))
    receipt=dict(schema='AURA-F27-NUMERIC-INVOCATION-OWNER-ACCUMULATION-CAMPAIGN-v3',seed=seed,randomized_decisions=n,oracle_mismatches=mismatches,false_accepts=false_accepts,false_holds=false_holds,numeric_hs_families=len(hs),numeric_hs_cases=len(hs)*1000,numeric_hs_escapes=hs_escapes,invocation_materialization=invocation,omega8_states=3**8,omega8_keepers=omega_keeper,thirteen_d_trailing_contexts=3**5,thirteen_d_repairs=repairs,boundary_witnesses={'legacy':'aggregate-finite/owner-order-inf','frontier':'aggregate-finite/repeated-unit-inf'})
    receipt['campaign_root']=root(receipt)
    assert mismatches==false_accepts==false_holds==hs_escapes==repairs==0
    assert all(invocation[k]==0 for k in ('mismatches','false_accepts','false_rejects','uncontrolled_exceptions','hs1000_escapes'))
    assert omega_keeper==1
    return receipt

if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
