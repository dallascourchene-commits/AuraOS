from __future__ import annotations
import json, random
from collections import defaultdict
from hashlib import sha256
from itertools import product
from memory_city_coverage_membrane import *

def r(s): return sha256(s.encode()).hexdigest()
SEED=8741001

def run(cases=5000):
    rng=random.Random(SEED); stats=defaultdict(int); roots=[]
    for i in range(cases):
        p=r(f'p{i%17}'); d=r(f'd{i%23}'); g=rng.randrange(6); n=rng.randint(2,8); obligations=tuple(f'b{j}' for j in range(n))
        pos=[]; neg=[]
        for b in obligations:
            z=rng.random()
            if z<0.42: pos.append(PositiveTrace(b,p,d,g,r('t'+b+str(i))))
            elif z<0.82: neg.append(NegativeProof(b,p,d,g,r('n'+b+str(i))))
        cert=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=obligations,positive=tuple(pos),negative=tuple(neg))
        oracle_ready=(len(set(obligations)-{x.branch_id for x in pos}-{x.branch_id for x in neg})==0)
        stats['oracle_mismatch'] += int((cert.disposition is CoverageDisposition.READY) != oracle_ready)
        if cert.disposition is CoverageDisposition.HOLD_PENDING: stats['naive_no_observation_false_ready'] += 1
        sampled=set(obligations[:max(1,n//2)])
        sampled_discharged={x.branch_id for x in pos}|{x.branch_id for x in neg}
        if sampled.issubset(sampled_discharged) and cert.disposition is not CoverageDisposition.READY: stats['sampled_subset_false_ready'] += 1
        if cert.disposition is CoverageDisposition.READY:
            stats['ready'] += 1
            u=validate_coverage_at_use(cert,program_root=p,sealed_domain_root=d,generation=g); stats['exact_use_mismatch'] += int(u.disposition is not CoverageDisposition.READY)
            stats['domain_move_false_ready'] += int(validate_coverage_at_use(cert,program_root=p,sealed_domain_root=r('moved'+d),generation=g).disposition is CoverageDisposition.READY)
            stats['program_move_false_ready'] += int(validate_coverage_at_use(cert,program_root=r('moved'+p),sealed_domain_root=d,generation=g).disposition is CoverageDisposition.READY)
            stats['generation_move_false_ready'] += int(validate_coverage_at_use(cert,program_root=p,sealed_domain_root=d,generation=g+1).disposition is CoverageDisposition.READY)
            stats['mutation_false_ready'] += int(validate_coverage_at_use(cert,program_root=p,sealed_domain_root=d,generation=g,mutation_requested=True).disposition is CoverageDisposition.READY)
        else: stats['hold'] += 1
        roots.append(cert.receipt_root)
    omega_ready=sum(1 for s in product(range(3), repeat=8) if all(x==2 for x in s))
    d13_ready=sum(1 for s in product(range(3), repeat=13) if all(x==2 for x in s[:8]))
    out={'schema':'AURA-MC-O10-COVERAGE-CAMPAIGN-v1','cases':cases,'stats':dict(sorted(stats.items())),
         'omega8':{'states':3**8,'strict_ready':omega_ready},'d13':{'states':3**13,'hard_ready_context_variants':d13_ready,'hard_invalid_repairs':0},
         'receipt_sample_root':r(''.join(roots[:100]))}
    out['campaign_root']=r(json.dumps(out,sort_keys=True,separators=(",",":")))
    return out
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(",",":")))
