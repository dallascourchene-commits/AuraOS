import hashlib,itertools,json,random,time
from dataclasses import replace
from transition_k27_cache_admission import *

def oracle(t,e,c):
    if not verify_transition(t) or not verify_entry(e): return False
    if t.disposition not in (TransitionDisposition.EXACT_UNCHANGED,TransitionDisposition.PROOF_NEUTRAL_REBIND): return False
    return (e.subject_id==c.subject_id and e.semantic_root==c.semantic_root and
            e.provider_anchor_root==c.provider_anchor_root==t.provider_anchor_root and
            e.dependency_root==c.dependency_root==t.dependency_root and
            e.runtime_owner==c.expected_runtime_owner and e.runtime_generation==c.runtime_generation and
            e.compatibility_profile==c.compatibility_profile and e.benchmark_generation==c.benchmark_generation and
            e.payload_hash==c.payload_hash)

def main():
    t,e,c,s=demo_fixture(); rng=random.Random(20260905); mismatches=0; h=hashlib.sha256(); start=time.perf_counter()
    for i in range(100000):
        ee,cc=e,c
        k=rng.randrange(9)
        if k==0: cc=replace(c,semantic_root=digest(f"s{i}"))
        elif k==1: cc=replace(c,provider_anchor_root=digest(f"p{i}"))
        elif k==2: cc=replace(c,dependency_root=digest(f"d{i}"))
        elif k==3: cc=replace(c,expected_runtime_owner="other")
        elif k==4: cc=replace(c,runtime_generation="5"*40)
        elif k==5: cc=replace(c,compatibility_profile="kv-v2")
        elif k==6: cc=replace(c,benchmark_generation="6"*40)
        elif k==7: cc=replace(c,payload_hash=digest(f"x{i}"))
        got=decide(t,ee,cc,s).decision is Decision.ADMIT_RUNTIME_REUSE
        want=oracle(t,ee,cc)
        mismatches += got!=want
        h.update(f"{i}|{k}|{int(got)}|{int(want)}\n".encode())
    hs_false=0
    # HS1000: 10 families x 100; route score is intentionally extreme for all mutations.
    extreme=RoutingSignals(1e9,100000,1e6,1e6,0)
    for family in range(10):
        for i in range(100):
            ee,cc=e,c
            if family==0: cc=replace(c,semantic_root=digest(f"hs-s{i}"))
            elif family==1: cc=replace(c,provider_anchor_root=digest(f"hs-p{i}"))
            elif family==2: cc=replace(c,dependency_root=digest(f"hs-d{i}"))
            elif family==3: cc=replace(c,expected_runtime_owner="other")
            elif family==4: cc=replace(c,runtime_generation="7"*40)
            elif family==5: cc=replace(c,compatibility_profile="kv-v3")
            elif family==6: cc=replace(c,benchmark_generation="8"*40)
            elif family==7: cc=replace(c,payload_hash=digest(f"hs-x{i}"))
            elif family==8: ee=replace(e,coordinate=((e.coordinate[0]+1)%27,e.coordinate[1],e.coordinate[2]))
            else: ee=replace(e,entry_root=digest(f"hs-r{i}"))
            hs_false += decide(t,ee,cc,extreme).decision is Decision.ADMIT_RUNTIME_REUSE
    omega=sum(classify8(x) for x in itertools.product(range(3),repeat=8))
    bad_core=(0,2,2,2,2,2,2,2)
    repairs=sum(classify13(bad_core+tail) for tail in itertools.product(range(3),repeat=5))
    out={
      "schema":SCHEMA+"-CAMPAIGN","oracle_cases":100000,"oracle_mismatches":mismatches,
      "hs1000_false_admits":hs_false,"omega8_keeper_count":omega,"tail_repairs":repairs,
      "coordinate":e.coordinate,"entry_root":e.entry_root,"transition_root":t.receipt_root,
      "campaign_root":h.hexdigest(),"authority":"D0","gate10":False,
    }
    stable=json.dumps(out,sort_keys=True,separators=(",",":"))
    out["receipt_root"]=hashlib.sha256(stable.encode()).hexdigest()
    out["decisions_per_second"]=100000/(time.perf_counter()-start)
    print(json.dumps(out,sort_keys=True))
    if mismatches or hs_false or omega!=1 or repairs: raise SystemExit(1)
if __name__=='__main__': main()
