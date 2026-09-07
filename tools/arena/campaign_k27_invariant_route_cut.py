from __future__ import annotations
import itertools,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from k27_invariant_route_cut import SupportHyperedge,SupportBeliefState,compile_invariant_route_cut,affected_by_change,hard13d_route_cut
from k27_dynamic_navigator import digest

def main():
    rng=random.Random(20260907)
    cases=3000; nodes=[f'N{i}' for i in range(1000)]
    false_unaffected=0; oracle_mismatch=0; naive_false_locality=0; safe_total=0; universe_total=0; ready=0; holds=0; dense=0
    rows=[]
    for case in range(cases):
        is_dense=rng.random()<0.10
        edges=[]
        if is_dense:
            dense+=1; members=frozenset(rng.sample(nodes,rng.randint(700,1000))); edges=[SupportHyperedge(f'i{case}-0',members)]
        else:
            for j in range(rng.randint(10,50)):
                members=frozenset(rng.sample(nodes,rng.randint(2,8))); edges.append(SupportHyperedge(f'i{case}-{j}',members))
        direct=set(rng.sample(nodes,rng.randint(1,5)))
        mutate=(rng.random()<0.12 and bool(edges))
        post=list(edges); actual_change=False
        if mutate:
            k=rng.randrange(len(post)); old=post[k]; replacement=set(old.members); replacement.add(rng.choice(nodes)); actual_change=(frozenset(replacement)!=old.members); post[k]=SupportHyperedge(old.invariant_id,frozenset(replacement))
        states=[SupportBeliefState(f'pre-{case}',tuple(edges),True,True),SupportBeliefState(f'post-{case}',tuple(post),True,True)]
        out=compile_invariant_route_cut(direct,states)
        want_ready=(not actual_change)
        if (out.status=='READY_INVARIANT_ROUTE_CUT_D0')!=want_ready: oracle_mismatch+=1
        if want_ready:
            ready+=1
            closure=set(direct); changed=True
            while changed:
                changed=False
                for edge in edges:
                    if closure & edge.members and not edge.members <= closure:
                        closure |= edge.members; changed=True
            if set(out.safe_support_cut)!=closure: oracle_mismatch+=1
            outside=set(nodes)-closure
            if outside:
                z=rng.choice(sorted(outside))
                if affected_by_change(out,z): false_unaffected+=1
            hidden=closure-direct
            if hidden: naive_false_locality+=1
            safe_total+=len(closure); universe_total+=len(nodes)
        else:
            holds+=1
            if not affected_by_change(out,rng.choice(nodes)): false_unaffected+=1
        rows.append((case,out.status,len(direct),len(out.safe_support_cut),is_dense,actual_change))
    false13=0; states13=0
    for axes in itertools.product(range(3),repeat=13):
        states13+=1; got=hard13d_route_cut(axes); hard=axes[:8]
        want='HOLD_HARD_INVALID' if 0 in hard else ('HOLD_UNRESOLVED' if 1 in hard else 'READY_D0')
        false13 += got!=want
    receipt={'schema':'aura.k27.invariant_route_cut.campaign.v1','cases':cases,'ready':ready,'holds_reflexive':holds,'dense_cases':dense,
      'oracle_mismatches':oracle_mismatch,'false_unaffected':false_unaffected,'naive_direct_false_locality_cases':naive_false_locality,
      'mean_safe_cut_fraction_of_universe':safe_total/universe_total if universe_total else 1.0,'13d_states':states13,'13d_mismatches':false13,
      '8_crystalline_lenses':['identity','currentness','support-completeness','support-invariance','hard-law','provenance','collision','authority'],
      'authority_minted':False,'gate10':False}
    receipt['campaign_root']=digest({'rows':rows,'receipt':receipt})
    print(json.dumps(receipt,sort_keys=True,indent=2))
if __name__=='__main__':main()
