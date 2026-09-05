from __future__ import annotations
import hashlib, json, random, time
from dataclasses import replace
from decimal import Decimal
from recomputed_evidence_cost_admission import *

SEED=909032

def make_case(n=12060):
    runtime=(b'def native_router(x):\n    return x\n' * 128)
    source=SourceEvidence('a'*40,'a'*40,'C:/AuraModels/GLM-5.3/aura-k27/glm53_airllm_k27_runtime.py',runtime,hashlib.sha256(runtime).hexdigest(),'src-awj032','bench-agent09','synthetic-owner-host-envelope')
    samples=[]; events=[]; transfers=[]
    categories=('code','reasoning','tool')
    for i in range(n):
        control=i>=12000
        category=categories[i%3]
        prefix='shared-control-prefix' if control else f'{category}-prefix-{i}'
        samples.append(WorkloadSample(f's{i}',category,prefix,'src-awj032',not control,'shared-control' if control else None))
        events.append(FusedEvent(f'e{i}',f's{i}',i, i%78, (i%64,(i*7+3)%64)))
        kind='SPECULATIVE' if i%200==0 else 'DEMAND'
        transfers.append(TransferCharge(f't{i}',i+1,f'e{i}',kind,1_048_576))
    spec_bytes=sum(t.bytes_moved for t in transfers if t.kind=='SPECULATIVE')
    spec_energy=Decimal(spec_bytes)*Decimal('2.4')/Decimal(1_000_000_000)
    cost=CostEvidence('2.4',format(spec_energy+Decimal('0.001'),'f'),1_000_000_000,tuple(transfers))
    return source,tuple(events),tuple(samples),cost

def hs1000(base):
    source,events,samples,cost=base; rng=random.Random(SEED); admitted=0
    for i in range(1000):
        family=i%10; s=source; es=events[:64]; ss=samples[:64]; c=CostEvidence(cost.joules_per_gb,cost.speculative_budget_j,cost.bytes_per_gb,cost.transfers[:64])
        try:
            if family==0: s=replace(s,current_head='b'*40)
            elif family==1: s=replace(s,runtime_bytes=s.runtime_bytes+b'x')
            elif family==2:
                x=list(es); x[1]=replace(x[1],event_id=x[0].event_id); es=tuple(x)
            elif family==3:
                x=list(es); x[0]=replace(x[0],native_experts=(1,1)); es=tuple(x)
            elif family==4:
                x=list(ss); x[1]=replace(x[1],rendered_prefix=x[0].rendered_prefix); ss=tuple(x)
            elif family==5:
                x=list(ss); x[0]=replace(x[0],source_generation='forged'); ss=tuple(x)
            elif family==6:
                x=list(c.transfers); x[1]=replace(x[1],transfer_id=x[0].transfer_id); c=replace(c,transfers=tuple(x))
            elif family==7:
                x=list(c.transfers); x[0]=replace(x[0],event_id='missing'); c=replace(c,transfers=tuple(x))
            elif family==8: c=replace(c,speculative_budget_j='0')
            else:
                r=compile_composite(s,es,ss,c); admitted += int(verify_composite(s,es,ss,c,replace(r,gate10=True))); continue
            r=compile_composite(s,es,ss,c); admitted += int(verify_composite(s,es,ss,c,r))
        except AdmissionError:
            pass
    return admitted

def sampled13(n=100000):
    rng=random.Random(SEED); seen=set(); repairs=0; admits=0
    while len(seen)<n:
        state=tuple(rng.randrange(3) for _ in range(13))
        if state in seen: continue
        seen.add(state); d=classify13(state)
        if d=='ADMIT_D0_RECOMPUTED_EVIDENCE': admits+=1
        if classify8(state[:8])!='ADMIT_D0_RECOMPUTED_EVIDENCE' and d=='ADMIT_D0_RECOMPUTED_EVIDENCE': repairs+=1
    return len(seen),repairs,admits

def main():
    base=make_case()
    t=time.perf_counter(); receipt=compile_composite(*base); compile_s=time.perf_counter()-t
    t=time.perf_counter(); ok=verify_composite(*base,receipt); verify_s=time.perf_counter()-t
    hs=hs1000(base); unique13,repairs,admits13=sampled13(); omega=exhaustive8()
    result={
        'schema':'AGENT09_RECOMPUTED_EVIDENCE_CAMPAIGN_V1','seed':SEED,'verified':ok,
        'samples':len(base[2]),'events':len(base[1]),'transfers':len(base[3].transfers),
        'compile_seconds':compile_s,'verify_seconds':verify_s,
        'compile_samples_per_s':len(base[2])/compile_s,'verify_samples_per_s':len(base[2])/verify_s,
        'hs1000_false_admissions':hs,'omega8_states':sum(omega.values()),'omega8_admits':omega.get('ADMIT_D0_RECOMPUTED_EVIDENCE',0),
        'sampled13_unique_states':unique13,'sampled13_hard_invalid_repairs':repairs,'sampled13_admits':admits13,
        'total_bytes':receipt.total_bytes,'speculative_bytes':receipt.speculative_bytes,
        'total_modeled_energy_j':receipt.total_modeled_energy_j,'speculative_modeled_energy_j':receipt.speculative_modeled_energy_j,
        'campaign_root':hashlib.sha256(json.dumps({'receipt':receipt.result_root,'omega8':omega,'hs1000':hs,'13d':{'n':unique13,'repairs':repairs}},sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    }
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
