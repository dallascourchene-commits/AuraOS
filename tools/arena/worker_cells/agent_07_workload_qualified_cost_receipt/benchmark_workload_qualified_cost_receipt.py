from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import random
import time

from workload_qualified_cost_receipt import *

HEAD="7a2c7a16f845752ffb7c16c68636d8d542ecd72e"
N=12000

def build():
    samples=[]
    cats=("code","reasoning","tool")
    for i in range(N):
        cat=cats[i%3]
        samples.append(WorkloadSample(f"s{i}",cat,f"{cat}:rendered:{i}",True))
    for i in range(60):
        samples.append(WorkloadSample(f"c{i}","control",f"code:rendered:{i*3}",False,"shared-prefix-control"))
    transfers=[]; seq=1
    for i,s in enumerate(samples[:N]):
        transfers.append(TransferCharge(f"d{seq}",seq,s.sample_id,"DEMAND",1_048_576)); seq+=1
        if i%200==0:
            transfers.append(TransferCharge(f"p{seq}",seq,s.sample_id,"SPECULATIVE",262_144)); seq+=1
    env=CostEnvelope(HEAD,"rt-synth-v2","hw-synth-v2","workload-qualified-v1","2.4","0.05")
    return tuple(samples),tuple(transfers),env

def hs1000(samples,transfers,env,receipt):
    false=0; rng=random.Random(707)
    small_samples=samples[:90] + tuple(s for s in samples if not s.ranking_eligible)[:3]
    small_ids={s.sample_id for s in small_samples}
    small_transfers=tuple(t for t in transfers if t.sample_id in small_ids)
    sr=compile_receipt(small_samples,small_transfers,env)
    for i in range(1000):
        ss=list(small_samples); tt=small_transfers; ee=env; rr=sr
        mode=i%8
        try:
            if mode==0:
                target=next(j for j,s in enumerate(ss) if s.ranking_eligible and s.category!="code")
                source=next(s for s in ss if s.ranking_eligible and s.category=="code")
                ss[target]=replace(ss[target],rendered_prefix=source.rendered_prefix)
            elif mode==1:
                j=next(j for j,s in enumerate(ss) if not s.ranking_eligible); ss[j]=replace(ss[j],ranking_eligible=True,control_group=None,category="reasoning")
                source=next(s for s in ss if s.ranking_eligible and s.category=="code"); ss[j]=replace(ss[j],rendered_prefix=source.rendered_prefix)
            elif mode==2: rr=replace(rr,result_root="f"*64)
            elif mode==3: rr=replace(rr,total_bytes=rr.total_bytes+1)
            elif mode==4: ee=replace(ee,source_head="1"*40)
            elif mode==5: tt=(replace(tt[0],bytes_moved=True),)+tt[1:]
            elif mode==6: tt=(tt[0],replace(tt[1],transfer_id=tt[0].transfer_id))+tt[2:]
            else: rr=replace(rr,policy_ranking_eligible=False)
            if verify_receipt(tuple(ss),tt,ee,rr): false+=1
        except QualifiedCostError:
            pass
    return false

def exact_boundary_probe(env):
    per=1001
    total=per*1000
    direct=energy_from_bytes(total,env)
    incremental=sum((energy_from_bytes(per,env) for _ in range(1000)),Decimal("0"))
    return direct==incremental, format(direct.normalize(), "f")

def main():
    samples,transfers,env=build()
    start=time.perf_counter(); receipt=compile_receipt(samples,transfers,env); compile_s=time.perf_counter()-start
    start=time.perf_counter(); ok=verify_receipt(samples,transfers,env,receipt); verify_s=time.perf_counter()-start
    false=hs1000(samples,transfers,env,receipt)
    boundary_ok,boundary_energy=exact_boundary_probe(env)
    rng=random.Random(1707); repairs=0
    for _ in range(100000):
        o=[rng.randrange(3) for _ in range(8)]; r=[rng.randrange(3) for _ in range(5)]
        if 0 in o and admission_13d(o,r): repairs+=1
    out={
        "schema":SCHEMA,"samples":len(samples),"ranking_samples":receipt.ranking_sample_count,"controls":receipt.control_sample_count,
        "categories":list(receipt.ranking_categories),"transfers":receipt.transfer_count,"demand_transfers":receipt.demand_transfer_count,
        "speculative_transfers":receipt.speculative_transfer_count,"total_bytes":receipt.total_bytes,"speculative_bytes":receipt.speculative_bytes,
        "total_modeled_energy_j":receipt.total_modeled_energy_j,"speculative_modeled_energy_j":receipt.speculative_modeled_energy_j,
        "speculative_budget_j":receipt.speculative_energy_budget_j,"speculative_remaining_j":receipt.speculative_energy_remaining_j,
        "compile_s":compile_s,"verify_s":verify_s,"samples_per_s_compile":len(samples)/compile_s,"samples_per_s_verify":len(samples)/verify_s,
        "verify_ok":ok,"hs1000_false_admissions":false,"boundary_1000_plan_exact":boundary_ok,"boundary_energy_j":boundary_energy,
        "sampled_13d":100000,"hard_invalid_repairs":repairs,"workload_root":receipt.workload_root,"transfer_root":receipt.transfer_root,
        "result_root":receipt.result_root,"effect_authority":receipt.effect_authority,"gate10":receipt.gate10,
    }
    stable={k:v for k,v in out.items() if k not in {"compile_s","verify_s","samples_per_s_compile","samples_per_s_verify"}}
    out["stable_campaign_root"]=hashlib.sha256(json.dumps(stable,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    print(json.dumps(out,sort_keys=True))
    if not ok or false or repairs or not boundary_ok: raise SystemExit(1)

if __name__=="__main__": main()
