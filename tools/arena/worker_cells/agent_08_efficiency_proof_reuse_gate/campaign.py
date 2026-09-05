from dataclasses import replace, asdict
from decimal import Decimal
import hashlib,json,itertools,random,time
from efficiency_proof_reuse_gate import *
from test_efficiency_proof_reuse_gate import valid_proof,valid_cost,valid_evidence,oracle_parent_decision,oracle_proof_root,oracle_cost

def proof_differential(n=10000):
    rng=random.Random(803); mism=0
    fields=['internal_receipt_valid','source_truth_bound','required_steps_complete','cumulative_resource_budget_verified','benchmark_oracle_ceiling_verified','canonical_trace_schema_verified','execution_source_provenance_verified','fused_event_structure_verified','expected_result_root','expected_trace_root','expected_environment_root','expected_resource_budget_root','expected_trace_schema_root','reconstructed_event_root']
    for i in range(n):
        p=valid_proof(); f=fields[i%len(fields)]
        if f.endswith('_verified') or f in {'internal_receipt_valid','source_truth_bound','required_steps_complete'}: p=replace(p,**{f:bool(rng.randrange(2))})
        else:p=replace(p,**{f:hashlib.sha256(f'{f}:{i}'.encode()).hexdigest()})
        if p.parent_decision().value!=oracle_parent_decision(p):mism+=1
        if p.validate_shape() and p.parent_evidence_root()!=oracle_proof_root(p):mism+=1
    return mism

def cost_differential(n=10000):
    rng=random.Random(807);mism=0;roots=[]
    for i in range(n):
        ns=2+(i%5); samples=[];trans=[]
        for j in range(ns):
            cat=('code','reason','tool')[j%3]
            samples.append(WorkloadSample(f's{j}',cat,f'{cat}:{i}:{j}',True))
            trans.append(TransferCharge(f't{j}',j+1,f's{j}','SPECULATIVE' if j%4==0 else 'DEMAND',rng.randrange(1,100000)))
        samples.append(WorkloadSample('ctl','control',f'control:{i}',False,'ctl'))
        env=CostEnvelope(CURRENT_BASE_HEAD,f'rt{i%7}',f'hw{i%5}',f'b{i%11}','2.4','1000',1_000_000_000,False,False)
        c=CostParentEvidence(COST_PARENT_SEMANTIC_COMMIT,COST_PARENT_SOURCE_BLOB,tuple(samples),tuple(trans),env)
        a=c.independently_compile();b=oracle_cost(c)
        if a!=b:mism+=1
        if i<100: roots.append(a['result_root'])
    return mism,digest(roots)

def hs1000():
    e=valid_evidence(); false=0
    for i in range(1000):
        mode=i%10; x=e
        if mode==0:x=replace(x,proved_proof_projection_root='f'*64)
        elif mode==1:x=replace(x,proved_cost_projection_root='e'*64)
        elif mode==2:x=replace(x,authority_requested=True)
        elif mode==3:x=replace(x,proof=replace(x.proof,source_truth_bound=False))
        elif mode==4:x=replace(x,proof=replace(x.proof,reconstructed_event_root='d'*64))
        elif mode==5:x=replace(x,proof=replace(x.proof,expected_resource_budget_root='c'*64))
        elif mode==6:x=replace(x,proof=replace(x.proof,changed_paths=('.aura/CODEMAP.md',)))
        elif mode==7:x=replace(x,cost=replace(x.cost,envelope=replace(x.cost.envelope,effect_authority=True)))
        elif mode==8:x=replace(x,cost=replace(x.cost,envelope=replace(x.cost.envelope,gate10=True)))
        else:x=replace(x,cost=replace(x.cost,envelope=replace(x.cost.envelope,speculative_energy_budget_j='0')))
        if assess(x).decision==Decision.REUSE_EXACT:false+=1
    return false

def destructive(n=50000):
    e=valid_evidence();rng=random.Random(811);false=0
    for i in range(n):
        p=e.proof
        mode=i%7
        if mode==0:p=replace(p,internal_receipt_valid=False)
        elif mode==1:p=replace(p,source_truth_bound=False)
        elif mode==2:p=replace(p,required_steps_complete=False)
        elif mode==3:p=replace(p,canonical_trace_schema_verified=False)
        elif mode==4:p=replace(p,execution_source_provenance_verified=False)
        elif mode==5:p=replace(p,fused_event_structure_verified=False)
        else:p=replace(p,expected_event_root=hashlib.sha256(str(rng.random()).encode()).hexdigest())
        if assess(replace(e,proof=p)).decision==Decision.REUSE_EXACT:false+=1
    return false

def omega8():
    admits=0
    for o in itertools.product(range(3),repeat=8):admits+=int(crystalline_admission(o))
    return admits

def context13d(n=100000):
    e=valid_evidence();bad=assess(replace(e,proof=replace(e.proof,source_truth_bound=False)))
    repairs=0;roots=set();rng=random.Random(813)
    for _ in range(n):
        tail=tuple(rng.randrange(3) for _ in range(5));r=recontextualize(bad,tail);roots.add(r.context_root);repairs+=int(r.decision==Decision.REUSE_EXACT)
    return repairs,len(roots)

def main():
    t=time.perf_counter();pd=proof_differential();cd,croot=cost_differential();false=hs1000();handoff=destructive();om=omega8();rep,ctx=context13d();elapsed=time.perf_counter()-t
    stable={'schema':SCHEMA,'proof_differential_cases':10000,'proof_differential_mismatches':pd,'cost_differential_cases':10000,'cost_differential_mismatches':cd,'cost_sample_root':croot,'hs1000_false_reuses':false,'destructive_handoffs':50000,'destructive_false_reuses':handoff,'omega8_states':6561,'omega8_keepers':om,'context13d_cases':100000,'context_roots':ctx,'context_repairs':rep,'valid_receipt_root':assess(valid_evidence()).receipt_root}
    stable['campaign_root']=digest(stable)
    out={**stable,'elapsed_s':elapsed}
    print(json.dumps(out,sort_keys=True))
    if any((pd,cd,false,handoff,rep)) or om!=1 or ctx!=243:raise SystemExit(1)
if __name__=='__main__':main()
