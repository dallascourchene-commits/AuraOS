from __future__ import annotations
import json,os,random,sys,time
from hashlib import sha256
ROOT=os.path.dirname(os.path.dirname(__file__));sys.path.insert(0,os.path.join(ROOT,'tools','arena'))
from proof_bound_reuse import *
SEED=2702001

def expensive(project,payload,source_head,workflow):
    x=json.dumps([project,payload,source_head,workflow],sort_keys=True).encode();h=sha256(x).digest()
    for _ in range(1500):h=sha256(h+x[:16]).digest()
    return {'digest':h.hex(),'ok':True}

def build(n=1000):
    l=ProofBoundReuseLedger();ids={};payloads={}
    for i in range(n):
        p=f'P{i:04d}';deps=[f'D{i%100}',f'D{(i*7)%100}'];l.bind(p,deps,['compile','test','receipt'])
        payload={'i':i,'seed':SEED};payloads[p]=payload
        ident=l.set_current_context(p,source_head='h1',workflow_generation='w1',input_payload=payload);ids[p]=ident
        result=expensive(p,payload,'h1','w1');r=ProofReceipt.build(ident,result,['compile','test','receipt'])
        assert l.admit_fresh_proof(ident,result,['compile','test','receipt'],r)
    return l,ids,payloads

def main():
    l,ids,payloads=build();projects=sorted(ids)
    t=time.perf_counter();full={p:expensive(p,payloads[p],'h1','w1') for p in projects};full_s=time.perf_counter()-t
    affected=l.invalidate(['D17'])
    t=time.perf_counter();selective={};reused=reeval=0
    for p in projects:
        ident=ids[p]
        if p in affected:
            result=expensive(p,payloads[p],'h1','w1');reeval+=1
            rr=ProofReceipt.build(ident,result,['compile','test','receipt']);assert l.admit_fresh_proof(ident,result,['compile','test','receipt'],rr);selective[p]=result
        else:
            selective[p]=l.reusable_result(p);reused+=1
    selective_s=time.perf_counter()-t
    assert selective==full
    stale_reuses=0
    for p in projects:
        l.set_current_context(p,source_head='h2',workflow_generation='w1',input_payload=payloads[p]);stale_reuses+=int(l.reusable(p))
    out={'seed':SEED,'projects':len(projects),'affected':len(affected),'full_evaluations':len(projects),'selective_evaluations':reeval,'reused':reused,'stale_reuses_after_head_change':stale_reuses,'result_root_equal':digest(full)==digest(selective),'full_wall_s':full_s,'selective_wall_s':selective_s,'evaluation_reduction':1-reeval/len(projects),'wall_time_reduction':1-selective_s/full_s}
    print(json.dumps(out,indent=2,sort_keys=True))
if __name__=='__main__':main()
