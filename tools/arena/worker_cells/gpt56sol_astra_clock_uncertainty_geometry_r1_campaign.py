from tools.arena.worker_cells.gpt56sol_astra_clock_uncertainty_geometry_r1 import *
from itertools import product
import random,json,hashlib

SEED=0xA57A07; CASES=12000
AXES=('source','currentness','causal','validity','authority','owner','evidence','capability','resource','privacy','externalization','topology','coordinate')
HARD_AXES=frozenset({'source','currentness','causal','validity','authority','owner','evidence','capability','externalization'})

def relation(rng,src,dst,i):
    width=rng.randint(0,20_000); center=rng.randint(-5_000,5_000)
    return ClockRelation(src,dst,center-width//2,center+(width-width//2),rng.randint(0,500),1_000_000,rng.randint(500_000,60_000_000),rng.random()>0.08,f'r{i}')

def make_route(rng):
    length=rng.randint(1,3); middle=rng.sample([d for d in DOMAINS if d not in ('causal','externalization')],k=length-1)
    ds=['causal']+middle+['externalization']; rels=[relation(rng,ds[i],ds[i+1],i) for i in range(len(ds)-1)]; rng.shuffle(rels)
    return compile_route('causal','externalization',rels)

def oracle_status(mapped,deadline):
    if mapped.hi<=deadline:return 'READY_D0'
    if mapped.lo>deadline:return 'HOLD_DEADLINE_MISS'
    return 'HOLD_TEMPORAL_UNCERTAINTY'

def run():
    rng=random.Random(SEED); stats={k:0 for k in ['cases','oracle_mismatches','naive_false_accepts','currentness_holds','k27_attacks','bad_k27_accepts','ready','uncertain','miss']}; roots=[]; perm_audits=0
    for i in range(CASES):
        route=make_route(rng); src0=rng.randint(800_000,1_200_000); source=TimeInterval(src0,src0+rng.randint(0,5_000)); mapped,stale=propagate(route,source)
        k27='K27:'+str(rng.randint(0,26)) if rng.random()<0.15 else None; deadline=src0+rng.randint(-20_000,40_000); d=decide(route,source,DeadlineRequirement(deadline),k27_coordinate=k27); stats['cases']+=1
        if k27: stats['k27_attacks']+=1
        if stale:
            stats['currentness_holds']+=1
            if d.status!='HOLD_CURRENTNESS': stats['oracle_mismatches']+=1
            if k27 and d.status=='READY_D0': stats['bad_k27_accepts']+=1
        else:
            brute=brute_extrema(route,source)
            if mapped!=brute: stats['oracle_mismatches']+=1
            if d.status!=oracle_status(brute,deadline): stats['oracle_mismatches']+=1
            if d.status=='READY_D0': stats['ready']+=1
            elif d.status=='HOLD_TEMPORAL_UNCERTAINTY': stats['uncertain']+=1
            elif d.status=='HOLD_DEADLINE_MISS': stats['miss']+=1
            if naive_midpoint_deadline_accept(route,source,deadline) and brute.hi>deadline: stats['naive_false_accepts']+=1
            if k27 and d.status=='READY_D0' and brute.hi>deadline: stats['bad_k27_accepts']+=1
        if i<64 and len(route.relations)<=3:
            if len(permutation_roots(route.source_domain,route.target_domain,route.relations))!=1: stats['oracle_mismatches']+=1
            perm_audits+=1
        roots.append(digest({'i':i,'route':route.route_root,'source':[source.lo,source.hi],'deadline':deadline,'status':d.status,'mapped':None if d.mapped is None else [d.mapped.lo,d.mapped.hi],'k27':k27}))
    states=0; false_ready=0
    for vals in product(range(3),repeat=13):
        states+=1; state=dict(zip(AXES,vals)); hard_invalid=any(state[a]==2 for a in HARD_AXES); ready=state['resource']<2 and state['topology']<2 and not hard_invalid
        if hard_invalid and state['coordinate']==0 and ready:false_ready+=1
    summary={'schema':'aura.astra.o7.clock_uncertainty_geometry.campaign.v1','seed':SEED,'stats':stats,'permutation_audits':perm_audits,'13d_states':states,'13d_false_ready':false_ready,'keeper_laws':['CrossClockPointEstimate != ConservativeTemporalWitness','AdmissibleTimeSetStraddlesBoundary => HOLD_TEMPORAL_UNCERTAINTY','AllAdmissibleTimesMeetBoundary => READY_D0','CalibrationCurrentness != EventTime','K27Coordinate != ClockEvidence != Authority','Hard13DAxisCannotBeCompensatedByTimingOrCoordinate'],'case_root':hashlib.sha256(''.join(roots).encode()).hexdigest()}; summary['campaign_root']=digest(summary); print(json.dumps(summary,sort_keys=True,separators=(',',':')))
    return int(bool(stats['oracle_mismatches'] or stats['bad_k27_accepts'] or false_ready or stats['naive_false_accepts']==0))

if __name__=='__main__': raise SystemExit(run())
