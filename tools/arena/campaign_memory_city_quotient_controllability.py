from __future__ import annotations
import itertools, json, random, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_quotient_controllability import *


def oracle_components(nodes, edges):
    adj={n:set() for n in nodes}
    for e in edges:
        for a in e.members:
            for b in e.members:
                if a!=b: adj[a].add(b)
    seen=set(); groups=[]
    for n in sorted(nodes):
        if n in seen: continue
        comp=set([n]); q=[n]; seen.add(n)
        while q:
            x=q.pop(0)
            for y in sorted(adj[x]):
                if y not in seen: seen.add(y); comp.add(y); q.append(y)
        groups.append(tuple(sorted(comp)))
    return tuple(sorted(groups))


def main():
    rng=random.Random(20260907)
    cases=5000; mismatch=0; false_ready=0; conflation=0; cycle_holds=0; ready=0
    support_only_smaller=0; reproof_larger=0; uncontrollable=0; late=0; stale=0; rows=[]
    for case in range(cases):
        n=rng.randint(8,60); nodes=[f'N{i}' for i in range(n)]
        support=[]
        for j in range(rng.randint(0,max(1,n//5))):
            k=rng.randint(2,min(6,n)); support.append(HardSupportEdge(f'h{j}',tuple(rng.sample(nodes,k))))
        groups=oracle_components(nodes,support)
        comp_of={x:i for i,g in enumerate(groups) for x in g}
        dep=[]; cycle_case=rng.random()<0.08 and len(groups)>1
        order=list(range(len(groups))); rng.shuffle(order); pos={c:i for i,c in enumerate(order)}
        for _ in range(rng.randint(0,max(1,len(groups)*2))):
            a,b=rng.sample(range(len(groups)),2) if len(groups)>1 else (0,0)
            if a==b: continue
            if pos[a]>pos[b]: a,b=b,a
            dep.append(DependencyEdge(rng.choice(groups[a]),rng.choice(groups[b]),rng.choice(['READ','INFLUENCE'])))
        if cycle_case:
            a,b=rng.sample(range(len(groups)),2)
            dep.append(DependencyEdge(rng.choice(groups[a]),rng.choice(groups[b]),'READ'))
            dep.append(DependencyEdge(rng.choice(groups[b]),rng.choice(groups[a]),'INFLUENCE'))
        q=compile_hard_support_quotient(nodes,support,dep,support_generation=7)
        if q.disposition=='HOLD_DEPENDENCY_CYCLE':
            cycle_holds+=1; rows.append((case,'CYCLE',len(groups))); continue
        if q.disposition!='READY_HARD_SUPPORT_QUOTIENT_D0': mismatch+=1; continue
        got_groups=tuple(sorted(c.members for c in q.components))
        if got_groups!=groups: mismatch+=1
        group_to_cid={c.members:c.component_id for c in q.components}
        wanted={}
        for e in dep:
            s,d=comp_of[e.source_item],comp_of[e.dependent_item]
            if s==d: continue
            cs=group_to_cid[groups[s]]; cd=group_to_cid[groups[d]]
            wanted.setdefault((cs,cd),set()).add(e.relation)
        got={(e.source_component,e.dependent_component):set(e.relations) for e in q.dependencies}
        if got!=wanted: mismatch+=1
        direct=[rng.choice(nodes)]
        support_cut=set(support_components_for_items(q,direct))
        rep=set(reproof_cone(q,direct))
        if len(support_cut)<len(q.components): support_only_smaller+=1
        if len(rep)>len(support_cut): reproof_larger+=1
        if len(rep)>len(support_cut) and support_components_for_items(q,direct)==tuple(sorted(rep)): conflation+=1
        req=support_components_for_items(q,direct)
        avail={}
        expected='READY_CONTROLLABLE_SUPPORT_D0'
        for cid in req:
            mode=rng.random()
            if mode<0.08:
                avail[cid]=ComponentAvailability(cid,False,True,0,f'e{case}'); expected='HOLD_STALE_REQUIRED_SUPPORT'; stale+=1
            elif mode<0.18 and expected=='READY_CONTROLLABLE_SUPPORT_D0':
                avail[cid]=ComponentAvailability(cid,True,False,0,f'e{case}'); expected='HOLD_UNCONTROLLABLE_SUPPORT'; uncontrollable+=1
            elif mode<0.28 and expected=='READY_CONTROLLABLE_SUPPORT_D0':
                avail[cid]=ComponentAvailability(cid,True,True,6,f'e{case}'); expected='HOLD_LATE_REQUIRED_SUPPORT'; late+=1
            else:
                avail[cid]=ComponentAvailability(cid,True,True,2,f'e{case}')
        d=compile_controllability_cut(q,direct,avail,decision_tick=5)
        if any(not a.current for a in avail.values()): expected='HOLD_STALE_REQUIRED_SUPPORT'
        elif any(not a.obtainable for a in avail.values()): expected='HOLD_UNCONTROLLABLE_SUPPORT'
        elif any(a.available_by_tick>5 for a in avail.values()): expected='HOLD_LATE_REQUIRED_SUPPORT'
        else: expected='READY_CONTROLLABLE_SUPPORT_D0'
        if d.status!=expected: mismatch+=1
        if d.status=='READY_CONTROLLABLE_SUPPORT_D0': ready+=1
        if d.status=='READY_CONTROLLABLE_SUPPORT_D0' and any((not a.current or not a.obtainable or a.available_by_tick>5) for a in avail.values()): false_ready+=1
        rows.append((case,d.status,len(groups),len(q.dependencies),len(support_cut),len(rep)))
    false13=0; states13=0
    for axes in itertools.product(range(3),repeat=13):
        states13+=1; got=hard13d_quotient(axes); hard=axes[:8]
        want='HOLD_HARD_INVALID' if 0 in hard else ('HOLD_UNRESOLVED' if 1 in hard else 'READY_D0')
        false13 += got!=want
    receipt={
      'schema':'aura.memory_city.quotient_controllability.campaign.v1','cases':cases,
      'oracle_mismatches':mismatch,'false_ready':false_ready,'semantic_conflation':conflation,
      'cycle_holds':cycle_holds,'ready':ready,'support_cut_not_global_cases':support_only_smaller,
      'reproof_larger_than_support_cases':reproof_larger,'uncontrollable_samples':uncontrollable,
      'late_samples':late,'stale_samples':stale,'13d_states':states13,'13d_mismatches':false13,
      '8_crystalline_lenses':['identity','support','dependency-direction','currentness','obtainability','deadline','reproof','authority'],
      'authority_minted':False,'gate10':False,
    }
    receipt['campaign_root']=digest({'rows':rows,'receipt':receipt})
    print(json.dumps(receipt,sort_keys=True,indent=2))

if __name__=='__main__': main()
