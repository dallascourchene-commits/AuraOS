import hashlib, json, os, random, sys, time
ROOT=os.path.dirname(__file__)
sys.path.insert(0,ROOT)
from evidence_slice_dag import *

SEED=20260905


def admission_for(d,w):
    return AdmissionSet(
        graph_root=d.graph_root,
        verifier_generations=(('AGENT09','agent09-e68b9188'),),
        accepted_witness_roots=tuple((k,v.witness_root) for k,v in w.items()),
        observation_generation='campaign-20260905',
        external_receipt_root=digest({'external':'agent09-campaign-admission'}),
    )


def closure_oracle(d,changed):
    want=set(changed)
    while True:
        old=len(want)
        for node in d.nodes.values():
            if any(dep in want for dep in node.deps): want.add(node.node_id)
        if len(want)==old: return want


def main():
    d=demo_dag(); w=demo_witnesses(d); a=admission_for(d,w); rng=random.Random(SEED)
    false=0; recompute=0; all_nodes=len(d.nodes); h=hashlib.sha256(); start=time.perf_counter()
    for i in range(100000):
        changed=set(rng.sample(list(d.nodes),1 if i%4 else 2))
        p=d.compile_plan(changed,w,a); want=closure_oracle(d,changed)
        false += set(p.invalidated)!=want
        recompute += len(p.invalidated)
        h.update(f'{i}|{",".join(sorted(changed))}|{p.plan_root}|{len(p.invalidated)}\n'.encode())
    elapsed=time.perf_counter()-start
    hs_false=0
    for i in range(1000):
        changed={list(d.nodes)[i%all_nodes]}
        if i%7==0: changed.add(list(d.nodes)[(i*5+3)%all_nodes])
        p=d.compile_plan(changed,w,a); hs_false += set(p.invalidated)!=closure_oracle(d,changed)
    out={
        'schema':'AURA-EVIDENCE-SLICE-DAG-CAMPAIGN-v2',
        'dag_root':d.graph_root,
        'admission_surface_root':a.surface_root,
        'oracle_cases':100000,
        'oracle_mismatches':false,
        'hs1000_false_cutsets':hs_false,
        'nodes':all_nodes,
        'average_recomputed_nodes':recompute/100000,
        'full_recompute_nodes':all_nodes,
        'average_recompute_fraction':recompute/(100000*all_nodes),
        'campaign_root':h.hexdigest(),
        'authority':'D0','gate10':False,
    }
    stable=json.dumps(out,sort_keys=True,separators=(',',':'))
    out['receipt_root']=hashlib.sha256(stable.encode()).hexdigest()
    out['decisions_per_second']=100000/elapsed
    print(json.dumps(out,sort_keys=True))
    if false or hs_false: raise SystemExit(1)


if __name__=='__main__': main()
