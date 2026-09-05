from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
import json, random, time
from provider_bound_efficiency_rebind import *

SEED=1010032; P="a"*40; C="b"*40; G="AuraOS CODEMAP Bot"; PATHS=(".aura/CODEMAP.json",".aura/CODEMAP.md")
def base_evidence():
    m=ProviderMovement(P,C,P,C,G,G,PATHS,PATHS,observation_root(P,C,G,PATHS),True)
    p=EfficiencyProjection(P,"1"*64,{"event_root":"trace","events":8192,"schema":"fused-v1"},{"transfer_root":"cost","bytes":25851592704,"spec_bytes":67108864,"schema":"cost-v1"},"bench-1","host-1")
    return RebindEvidence(m,p,p,p.projection_root,p.projection_root,False)
def hs1000():
    base=base_evidence(); false=0; families=[]
    for i in range(1000):
        k=i%12; e=base
        if k==0: e=replace(e,movement=replace(e.movement,provider_observation_verified=False)); f="provider_unverified"
        elif k==1: e=replace(e,movement=replace(e.movement,observed_child_head="c"*40)); f="child"
        elif k==2: e=replace(e,movement=replace(e.movement,observed_generator_identity="Other")); f="generator"
        elif k==3: e=replace(e,movement=replace(e.movement,changed_paths=PATHS+("runtime.py",))); f="path"
        elif k==4: e=replace(e,current_projection=replace(e.current_projection,runtime_sha256="2"*64)); f="runtime"
        elif k==5: e=replace(e,current_projection=replace(e.current_projection,trace_projection={"x":"drift"})); f="trace"
        elif k==6: e=replace(e,current_projection=replace(e.current_projection,cost_projection={"x":"drift"})); f="cost"
        elif k==7: e=replace(e,current_projection=replace(e.current_projection,benchmark_generation="bench-2")); f="benchmark"
        elif k==8: e=replace(e,current_projection=replace(e.current_projection,hardware_fingerprint="host-2")); f="hardware"
        elif k==9: e=replace(e,expected_current_projection_root="f"*64); f="current_root"
        elif k==10: e=replace(e,authority_requested=True); f="authority"
        else: e=replace(e,movement=replace(e.movement,expected_provider_observation_root="f"*64)); f="observation_root"
        false += int(decide(e)==Decision.REUSE_AFTER_PROVIDER_BOUND_REBIND); families.append(f)
    return {"cases":1000,"families":len(set(families)),"false_reuses":false,"root":sha256(json.dumps(families,separators=(",",":")).encode()).hexdigest()}
def destructive(n=50000):
    rng=random.Random(SEED); base=base_evidence(); false=0
    mutations=(lambda e:replace(e,movement=replace(e.movement,provider_observation_verified=False)),lambda e:replace(e,movement=replace(e.movement,observed_parent_head="c"*40)),lambda e:replace(e,movement=replace(e.movement,changed_paths=PATHS+("x.py",))),lambda e:replace(e,current_projection=replace(e.current_projection,runtime_sha256="2"*64)),lambda e:replace(e,current_projection=replace(e.current_projection,trace_projection={"drift":rng.randrange(999999)})),lambda e:replace(e,current_projection=replace(e.current_projection,cost_projection={"drift":rng.randrange(999999)})),lambda e:replace(e,current_projection=replace(e.current_projection,semantic_source_head=C)),lambda e:replace(e,expected_proof_time_projection_root="f"*64))
    for _ in range(n): false += int(decide(mutations[rng.randrange(len(mutations))](base))==Decision.REUSE_AFTER_PROVIDER_BOUND_REBIND)
    return {"cases":n,"false_reuses":false}
def campaign13(n=100000):
    rng=random.Random(SEED); seen=set(); repairs=0
    while len(seen)<n:
        s=tuple(rng.randrange(3) for _ in range(13))
        if s in seen: continue
        seen.add(s); d=classify13(s)
        if classify8(s[:8])!="REUSE_AFTER_PROVIDER_BOUND_REBIND" and d=="REUSE_AFTER_PROVIDER_BOUND_REBIND": repairs+=1
    return {"unique_states":len(seen),"hard_invalid_repairs":repairs}
def main():
    e=base_evidence(); t=time.perf_counter(); r=make_receipt(e); build=time.perf_counter()-t; t=time.perf_counter(); ok=verify_receipt(e,r); verify=time.perf_counter()-t
    omega=exhaustive8(); hs=hs1000(); dest=destructive(); c13=campaign13()
    semantic={"schema":"AGENT10_PROVIDER_BOUND_EFFICIENCY_REBIND_CAMPAIGN_V1","seed":SEED,"verified":ok,"receipt_root":r.receipt_root,"build_seconds":build,"verify_seconds":verify,"hs1000":hs,"destructive":dest,"omega8_states":sum(omega.values()),"omega8_keepers":omega.get("REUSE_AFTER_PROVIDER_BOUND_REBIND",0),"context13d":c13}
    semantic["campaign_root"]=sha256(json.dumps({k:v for k,v in semantic.items() if k not in ("build_seconds","verify_seconds","campaign_root")},sort_keys=True,separators=(",",":")).encode()).hexdigest(); print(json.dumps(semantic,sort_keys=True))
    if not ok or hs["false_reuses"] or dest["false_reuses"] or c13["hard_invalid_repairs"] or semantic["omega8_keepers"]!=1: raise SystemExit(1)
if __name__=="__main__": main()
