from __future__ import annotations
import itertools, json, os, random, sys, time
from hashlib import sha256
HERE=os.path.dirname(__file__); sys.path.insert(0,HERE)
from airllm_security_reproof_dag import *


def fixture():
    nodes=airllm_security_nodes(); by={n.node_id:n for n in nodes}
    outputs={n.node_id:digest({"output":n.node_id,"v":1}) for n in nodes}
    verifiers={n.node_id:digest({"verifier":n.node_id,"security":AIRLLM_SECURITY_PARENT}) for n in nodes}
    witnesses={n.node_id:make_witness(n,outputs[n.node_id],outputs,verifiers[n.node_id]) for n in nodes}
    return nodes,by,outputs,verifiers,witnesses


def oracle_closure(by, changed):
    changed=set(changed); out=set(changed)
    progress=True
    while progress:
        progress=False
        for n in by.values():
            if n.node_id not in out and any(d in out for d in n.deps): out.add(n.node_id); progress=True
    return out


def randomized_oracle(n=100_000, seed=11011):
    rng=random.Random(seed); nodes,by,o,v,w=fixture(); ids=sorted(by); mismatches=0; total_fraction=0.0
    for _ in range(n):
        k=1 if rng.random()<0.7 else 2
        ch=tuple(sorted(rng.sample(ids,k)))
        p=compile_reproof_plan(ch,w,o,v)
        want=oracle_closure(by,ch)
        mismatches += int(set(p.recompute_order)!=want)
        total_fraction += len(want)/len(ids)
    return {"cases":n,"mismatches":mismatches,"mean_recompute_fraction":total_fraction/n}


def hs1000():
    nodes,by,o,v,w=fixture(); false_admits=0; families=[]
    for i in range(1000):
        oo=dict(o); vv=dict(v); ww=dict(w); mode=i%10; family=""
        try:
            if mode==0: ww["PACKAGE_MANIFEST"]=ww["PACKAGE_MANIFEST"].__class__(**{**ww["PACKAGE_MANIFEST"].__dict__,"witness_root":"0"*64}); family="witness_tamper"
            elif mode==1: oo["LOADER_SOURCE"]=digest({"drift":i}); family="dependency_drift"
            elif mode==2: vv["MODEL_ALLOWLIST"]=digest({"drift":i}); family="verifier_drift"
            elif mode==3: ww.pop("WORKLOAD_ENV"); family="incomplete_witness"
            elif mode==4: oo.pop("TRACE_PROVENANCE"); family="incomplete_output"
            elif mode==5: vv.pop("MODEL_BYTES"); family="incomplete_verifier"
            elif mode==6: compile_reproof_plan(["UNKNOWN"],ww,oo,vv); family="unknown_change"
            elif mode==7:
                bad=list(nodes); bad.pop(); compile_reproof_plan(["MODEL_BYTES"],ww,oo,vv,bad); family="weaker_graph"
            elif mode==8:
                x=ww["MODEL_ALLOWLIST"]; from dataclasses import replace; ww["MODEL_ALLOWLIST"]=replace(x,security_generation="1"*40); family="generation_replay"
            else:
                x=ww["MODEL_ALLOWLIST"]; from dataclasses import replace; ww["MODEL_ALLOWLIST"]=replace(x,graph_root="0"*64); family="cross_graph_replay"
            if mode not in (6,7): compile_reproof_plan(["TRACE_PROVENANCE"],ww,oo,vv)
            false_admits += 1
        except Exception:
            pass
        families.append(family or ["unknown_change","weaker_graph"][mode-6] if mode in (6,7) else family)
    return {"cases":1000,"false_admits":false_admits,"families":10,"root":sha256(json.dumps(families,separators=(",",":")).encode()).hexdigest()}


def omega8():
    states=3**8; keep=0; hard_invalid_escape=0; unknown_escape=0
    for s in itertools.product(range(3),repeat=8):
        ok=crystalline_admission(s); keep+=int(ok); hard_invalid_escape+=int(0 in s and ok); unknown_escape+=int(1 in s and ok)
    return {"states":states,"keepers":keep,"hard_invalid_escape":hard_invalid_escape,"unknown_escape":unknown_escape}


def campaign13d(n=100_000, seed=1311):
    rng=random.Random(seed); seen=set(); repairs=0; admits=0
    while len(seen)<n:
        s=tuple(rng.randrange(3) for _ in range(13))
        if s in seen: continue
        seen.add(s); ok=admission_13d(s); admits+=int(ok); repairs+=int(any(x!=2 for x in s[:8]) and ok)
    return {"unique_states":n,"admitted":admits,"hard_invalid_repairs":repairs}


def benchmark(rounds=5000):
    _,_,o,v,w=fixture(); t=time.perf_counter()
    for _ in range(rounds): compile_reproof_plan(["PACKAGE_MANIFEST"],w,o,v)
    elapsed=time.perf_counter()-t
    return {"rounds":rounds,"seconds":elapsed,"plans_per_second":rounds/elapsed}


def main():
    semantic={"schema":SCHEMA+"-CAMPAIGN","graph_root":CANONICAL_GRAPH_ROOT,"oracle":randomized_oracle(),"hs1000":hs1000(),"omega8":omega8(),"13d":campaign13d(),"parents":[AIRLLM_SECURITY_PARENT,EVIDENCE_DAG_PARENT]}
    root=sha256(json.dumps(semantic,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    out={"semantic":semantic,"campaign_root":root,"observational_timing":benchmark()}
    print(json.dumps(out,indent=2,sort_keys=True))
    assert semantic["oracle"]["mismatches"]==0
    assert semantic["hs1000"]["false_admits"]==0
    assert semantic["omega8"]["keepers"]==1 and semantic["omega8"]["hard_invalid_escape"]==0 and semantic["omega8"]["unknown_escape"]==0
    assert semantic["13d"]["hard_invalid_repairs"]==0

if __name__=="__main__": main()
