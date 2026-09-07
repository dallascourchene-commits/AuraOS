from __future__ import annotations
import itertools, json, random, sys
from types import SimpleNamespace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'tools'/'arena'))
from k27_dynamic_navigator import digest
from memory_city_ecf_adapter import ECFCurrentCut, ECFLeafAdmissionWitness, ECFAdmissionIndex
from memory_city_quotient_controllability import *

REG=digest({'registry':'campaign'}); CUT=digest({'cut':'campaign'}); AUTH=digest({'auth':'campaign'}); GRANT=digest({'grant':'campaign'})

def oracle_components(nodes,edges):
    adj={n:set() for n in nodes}
    for e in edges:
        for a in e.members:
            for b in e.members:
                if a!=b: adj[a].add(b)
    seen=set(); groups=[]
    for n in sorted(nodes):
        if n in seen: continue
        comp={n}; q=[n]; seen.add(n)
        while q:
            x=q.pop(0)
            for y in sorted(adj[x]):
                if y not in seen: seen.add(y); comp.add(y); q.append(y)
        groups.append(tuple(sorted(comp)))
    return tuple(sorted(groups))

def ecf_for(availability):
    cut=ECFCurrentCut('JUR-MEM',1,REG,'availability-owner','boot-1',AVAILABILITY_EVIDENCE_SCOPE,CUT)
    witnesses=[]
    for i,a in enumerate(sorted(availability.values(),key=lambda x:x.component_id)):
        witnesses.append(ECFLeafAdmissionWitness(f'w{i}',a.evidence_root,'JUR-MEM',1,REG,'availability-owner','boot-1',AVAILABILITY_EVIDENCE_SCOPE,CUT,AUTH,GRANT))
    return ECFAdmissionIndex(cut,tuple(witnesses),admitted_witness_roots=tuple(w.witness_root for w in witnesses))

def main():
    rng=random.Random(20260907); cases=5000
    mismatch=false_ready=conflation=cycle_holds=ready=0
    support_only_smaller=reproof_larger=uncontrollable=late=stale=0
    support_identity_checks=support_identity_false_ready=legacy_generation_only_false_ready=0
    forged_availability_checks=forged_availability_false_ready=0; rows=[]
    for case in range(cases):
        n=rng.randint(8,60); nodes=[f'N{i}' for i in range(n)]; support=[]
        for j in range(rng.randint(0,max(1,n//5))): support.append(HardSupportEdge(f'h{j}',tuple(rng.sample(nodes,rng.randint(2,min(6,n))))))
        groups=oracle_components(nodes,support); comp_of={x:i for i,g in enumerate(groups) for x in g}
        dep=[]; cycle_case=rng.random()<0.08 and len(groups)>1; order=list(range(len(groups))); rng.shuffle(order); pos={c:i for i,c in enumerate(order)}
        for _ in range(rng.randint(0,max(1,len(groups)*2))):
            a,b=rng.sample(range(len(groups)),2) if len(groups)>1 else (0,0)
            if a==b: continue
            if pos[a]>pos[b]: a,b=b,a
            dep.append(DependencyEdge(rng.choice(groups[a]),rng.choice(groups[b]),rng.choice(['READ','INFLUENCE'])))
        if cycle_case:
            a,b=rng.sample(range(len(groups)),2); dep.append(DependencyEdge(rng.choice(groups[a]),rng.choice(groups[b]),'READ')); dep.append(DependencyEdge(rng.choice(groups[b]),rng.choice(groups[a]),'INFLUENCE'))
        q=compile_hard_support_quotient(nodes,support,dep,support_generation=7)
        if q.disposition=='HOLD_DEPENDENCY_CYCLE': cycle_holds+=1; rows.append((case,'CYCLE',len(groups))); continue
        if q.disposition!='READY_HARD_SUPPORT_QUOTIENT_D0': mismatch+=1; continue
        if tuple(sorted(c.members for c in q.components))!=groups: mismatch+=1
        group_to_cid={c.members:c.component_id for c in q.components}; wanted={}
        for e in dep:
            s,d=comp_of[e.source_item],comp_of[e.dependent_item]
            if s==d: continue
            cs,cd=group_to_cid[groups[s]],group_to_cid[groups[d]]; wanted.setdefault((cs,cd),set()).add(e.relation)
        if {(e.source_component,e.dependent_component):set(e.relations) for e in q.dependencies}!=wanted: mismatch+=1
        direct=[rng.choice(nodes)]; support_cut=set(support_components_for_items(q,direct)); rep=set(reproof_cone(q,direct))
        if len(support_cut)<len(q.components): support_only_smaller+=1
        if len(rep)>len(support_cut): reproof_larger+=1
        if len(rep)>len(support_cut) and support_components_for_items(q,direct)==tuple(sorted(rep)): conflation+=1
        req=support_components_for_items(q,direct); branch_components=tuple(sorted(c.members for c in q.components if c.component_id in set(req)))
        fake_plan=SimpleNamespace(branch_id='b',required_item_ids=tuple(direct),required_components=branch_components)
        stale_root=('0'*64 if q.support_world_root!='0'*64 else '1'*64)
        fake_strategy=SimpleNamespace(disposition='READY_D0',support_generation=q.support_generation,support_root=stale_root,branch_plans=(fake_plan,))
        identity_decision=validate_contingent_strategy_branch(q,fake_strategy,branch_id='b',availability={},decision_tick=5)
        support_identity_checks+=1; legacy_generation_only_false_ready+=1
        if identity_decision.status=='READY_CONTROLLABLE_SUPPORT_D0': support_identity_false_ready+=1
        if identity_decision.status!='HOLD_SUPPORT_WORLD_IDENTITY_MISMATCH': mismatch+=1
        availability={}
        for cid in req:
            mode=rng.random()
            if mode<0.08: a=make_component_availability(q,cid,current=False,obtainable=True,available_by_tick=0); stale+=1
            elif mode<0.18: a=make_component_availability(q,cid,current=True,obtainable=False,available_by_tick=0); uncontrollable+=1
            elif mode<0.28: a=make_component_availability(q,cid,current=True,obtainable=True,available_by_tick=6); late+=1
            else: a=make_component_availability(q,cid,current=True,obtainable=True,available_by_tick=2)
            availability[cid]=a
        index=ecf_for(availability); d=compile_controllability_cut(q,direct,availability,decision_tick=5,ecf_index=index)
        if any(not a.current for a in availability.values()): expected='HOLD_STALE_REQUIRED_SUPPORT'
        elif any(not a.obtainable for a in availability.values()): expected='HOLD_UNCONTROLLABLE_SUPPORT'
        elif any(a.available_by_tick>5 for a in availability.values()): expected='HOLD_LATE_REQUIRED_SUPPORT'
        else: expected='READY_CONTROLLABLE_SUPPORT_D0'
        if d.status!=expected: mismatch+=1
        if d.status=='READY_CONTROLLABLE_SUPPORT_D0': ready+=1
        if d.status=='READY_CONTROLLABLE_SUPPORT_D0' and any((not a.current or not a.obtainable or a.available_by_tick>5) for a in availability.values()): false_ready+=1
        target=next(iter(availability.values()))
        forged=ComponentAvailability(target.component_id,not target.current,target.obtainable,target.available_by_tick,target.evidence_root)
        forged_availability_checks+=1
        forged_map=dict(availability); forged_map[target.component_id]=forged
        if compile_controllability_cut(q,direct,forged_map,decision_tick=5,ecf_index=index).status=='READY_CONTROLLABLE_SUPPORT_D0': forged_availability_false_ready+=1
        rows.append((case,d.status,len(groups),len(q.dependencies),len(support_cut),len(rep)))
    false13=states13=0
    for axes in itertools.product(range(3),repeat=13):
        states13+=1; got=hard13d_quotient(axes); hard=axes[:8]; want='HOLD_HARD_INVALID' if 0 in hard else ('HOLD_UNRESOLVED' if 1 in hard else 'READY_D0'); false13+=got!=want
    receipt={'schema':'aura.memory_city.quotient_controllability.campaign.v3','cases':cases,'oracle_mismatches':mismatch,'false_ready':false_ready,'semantic_conflation':conflation,'cycle_holds':cycle_holds,'ready':ready,'support_cut_not_global_cases':support_only_smaller,'reproof_larger_than_support_cases':reproof_larger,'uncontrollable_samples':uncontrollable,'late_samples':late,'stale_samples':stale,'support_identity_checks':support_identity_checks,'legacy_generation_only_false_ready':legacy_generation_only_false_ready,'support_identity_false_ready':support_identity_false_ready,'forged_availability_checks':forged_availability_checks,'forged_availability_false_ready':forged_availability_false_ready,'13d_states':states13,'13d_mismatches':false13,'8_crystalline_lenses':['identity','support','dependency-direction','currentness','obtainability','deadline','reproof','authority'],'authority_minted':False,'gate10':False}
    receipt['campaign_root']=digest({'rows':rows,'receipt':receipt}); print(json.dumps(receipt,sort_keys=True,indent=2))
if __name__=='__main__': main()
