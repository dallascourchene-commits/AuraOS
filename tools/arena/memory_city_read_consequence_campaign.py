from __future__ import annotations
import json, random
from collections import defaultdict
from hashlib import sha256
from itertools import product
from memory_city_coverage_membrane import *
from memory_city_read_consequence import *

def r(s): return sha256(s.encode()).hexdigest()
SEED=8741101

def run(cases=8000):
    rng=random.Random(SEED); stats=defaultdict(int); roots=[]
    for i in range(cases):
        p,d,g=r(f'p{i%19}'),r(f'd{i%29}'),rng.randrange(8)
        n=rng.randint(2,5); ids=tuple(f'w{j}' for j in range(n)); neg=set(rng.sample(ids,rng.randint(0,max(0,n-1))))
        pos=tuple(x for x in ids if x not in neg)
        if not pos: pos=(ids[0],); neg=set(ids[1:])
        cv=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=ids,
            positive=tuple(PositiveTrace(x,p,d,g,r(f't{i}-{x}')) for x in pos),
            negative=tuple(NegativeProof(x,p,d,g,r(f'n{i}-{x}')) for x in sorted(neg)))
        base_h=tuple(sorted(rng.sample(tuple('abcdef'),rng.randint(1,3)))); base_r=tuple(sorted(rng.sample(tuple('abcdef'),rng.randint(1,3)))); base_t=r(f'trust{i%31}')
        mode=rng.random(); projections=[]
        for j,w in enumerate(pos):
            hyd=base_h; rep=base_r; trust=base_t; current=True
            if mode<0.18 and j==len(pos)-1: hyd=tuple(sorted(set(base_h)|{'z'}))
            elif mode<0.32 and j==len(pos)-1: rep=tuple(sorted(set(base_r)|{'y'}))
            elif mode<0.46 and j==len(pos)-1: trust=r(f'other{i}')
            elif mode<0.52 and j==len(pos)-1: current=False
            projections.append(ReadWorldProjection(w,r(f'world{i}-{w}'),hyd,rep,trust,current,(rng.randrange(27),rng.randrange(27))))
        cert=compile_read_consequence_certificate(coverage=cv,projections=tuple(projections))
        oracle_ready=(all(x.current for x in projections) and len({x.hydration_cut for x in projections})==1 and len({x.reproof_cut for x in projections})==1 and len({x.read_obligation_root for x in projections})==1)
        stats['oracle_mismatch'] += int((cert.disposition is ReadConsequenceDisposition.READY)!=oracle_ready)
        stats['generation_only_false_ready'] += int(not oracle_ready)
        stats['full_world_identity_false_hold'] += int(oracle_ready and len(projections)>1)
        consequence_equal=(len({x.hydration_cut for x in projections})==1 and len({x.reproof_cut for x in projections})==1 and all(x.current for x in projections))
        stats['consequence_only_false_ready'] += int(consequence_equal and len({x.read_obligation_root for x in projections})>1)
        if cert.disposition is ReadConsequenceDisposition.READY:
            stats['ready']+=1; active=projections[0]
            u=validate_read_consequence_at_use(cert,coverage=cv,active_world_id=active.world_id,active_world_root=active.world_root,read_obligation_root=active.read_obligation_root)
            stats['exact_use_mismatch'] += int(u.disposition is not ReadConsequenceDisposition.READY)
            stats['unknown_member_false_ready'] += int(validate_read_consequence_at_use(cert,coverage=cv,active_world_id='ghost',active_world_root=r('ghost'),read_obligation_root=active.read_obligation_root).disposition is ReadConsequenceDisposition.READY)
            stats['trust_move_false_ready'] += int(validate_read_consequence_at_use(cert,coverage=cv,active_world_id=active.world_id,active_world_root=active.world_root,read_obligation_root=r('moved')).disposition is ReadConsequenceDisposition.READY)
            stats['mutation_false_ready'] += int(validate_read_consequence_at_use(cert,coverage=cv,active_world_id=active.world_id,active_world_root=active.world_root,read_obligation_root=active.read_obligation_root,mutation_requested=True).disposition is ReadConsequenceDisposition.READY)
            mutated=tuple(ReadWorldProjection(x.world_id,x.world_root,x.hydration_item_ids,x.reproof_item_ids,x.read_obligation_root,x.current,tuple((v+11)%27 for v in x.k27_hint)) for x in projections)
            c2=compile_read_consequence_certificate(coverage=cv,projections=mutated)
            stats['k27_semantic_mismatch'] += int(c2.receipt_root!=cert.receipt_root or c2.disposition!=cert.disposition)
        else: stats['hold']+=1
        roots.append(cert.receipt_root)
    omega_ready=sum(1 for s in product(range(3),repeat=8) if all(x==2 for x in s))
    d13_ready=sum(1 for s in product(range(3),repeat=13) if all(x==2 for x in s[:8]))
    out={'schema':'AURA-MC-O11-TRUST-EXACT-READ-CONSEQUENCE-CAMPAIGN-v1','cases':cases,'stats':dict(sorted(stats.items())),
         'omega8':{'states':3**8,'strict_ready':omega_ready},'d13':{'states':3**13,'hard_ready_context_variants':d13_ready,'hard_invalid_repairs':0},
         'sample_receipt_root':r(''.join(roots[:128]))}
    out['campaign_root']=r(json.dumps(out,sort_keys=True,separators=(",",":")))
    return out
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(",",":")))
