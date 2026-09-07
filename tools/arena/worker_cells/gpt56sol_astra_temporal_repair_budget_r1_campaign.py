from __future__ import annotations
import itertools,json,random
from hashlib import sha256
from tools.arena.worker_cells.gpt56sol_astra_temporal_repair_budget_r1 import *

def oracle(sens,budget):
    sm={s.domain:s for s in sens}; feasible=[]
    for mask in itertools.product((0,1),repeat=len(DOMAINS)):
        exact=frozenset(d for d,b in zip(DOMAINS,mask) if b)
        if not budget.hard_domains.issubset(exact): continue
        cost=sum(sm[d].exact_cost for d in exact)
        err=sum(sm[d].error_if_coarse for d in DOMAINS if d not in exact)
        if cost<=budget.max_cost and err<=budget.max_error: feasible.append((cost,err,tuple(sorted(exact))))
    if not feasible:return 'HOLD',None
    return 'READY',sorted(feasible)[0]

def run(seed=7301,cases=1000):
    rng=random.Random(seed); mism=hard_loss=promotions=0; roots=[]; statuses={}
    for i in range(cases):
        sens=tuple(Sensitivity(d,rng.randrange(0,21),rng.randrange(0,12)) for d in DOMAINS)
        hard=frozenset(d for d in sorted(HARD) if rng.random()>.08) | frozenset({'externalization'})
        b=ConsequenceBudget(rng.randrange(0,41),rng.randrange(0,41),hard)
        got=compile_exactness(sens,b); o,ov=oracle(sens,b)
        statuses[got.status]=statuses.get(got.status,0)+1
        if o=='HOLD': mism+=not got.status.startswith('HOLD')
        else:
            mismatch=(got.status!='READY_D0' or (got.exact_cost,got.bounded_error,tuple(sorted(got.exact_domains)))!=ov)
            mism+=mismatch
        hard_loss+=not b.hard_domains.issubset(got.exact_domains)
        promotions+=got.gate10 or got.effect_authority or got.authority!=D0
        roots.append(plan_root(sens,b))
    scalar_alias_fail=0
    for x in range(100):
        a=TemporalPoint(x,7,x*128,x,2,0); b=TemporalPoint(x,8,x*128,x,2,0)
        scalar_alias_fail+=not scalar_collision(a,b,('causal',))
    out={'seed':seed,'cases':cases,'oracle_mismatches':mism,'hard_domain_losses':hard_loss,'authority_promotions':promotions,'scalar_alias_failures':scalar_alias_fail,'statuses':dict(sorted(statuses.items())),'authority':D0}
    out['campaign_root']=sha256(json.dumps({'out':out,'roots':roots},sort_keys=True).encode()).hexdigest()
    if any((mism,hard_loss,promotions,scalar_alias_fail)): raise SystemExit(json.dumps(out,sort_keys=True))
    return out
if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
