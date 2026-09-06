from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json,random,itertools
from dataclasses import replace
from atomic_absorption import Proposal,OwnerSnapshot,digest
from resource_absorption import *
H='1'*64; T='2'*64; NOW=100000; RNG=random.Random(85403)
def L(i,key,actor,line,mode=LeaseMode.EXCLUSIVE,issued=90000,expires=110000,released=None): return Lease(digest(('lease',i,key,actor,line,mode.value)),key,actor,line,mode,issued,expires,1,released)
def P(i,actor='A',line='LA',base=H,files=None,cons=None,rec=None): return Proposal('P'+str(i),actor,line,base,cons or digest(('c',i)),rec or digest(('r',i)),files or {f'f{i}.py':digest(('b',i))},False)
def classify(i,k):
    key='db:'+str(i%17); p=P(i); l=L(i,key,'A','LA')
    if k==0: return LeaseRegistrySnapshot(1,(l,)),[ResourceProposal(p,(ResourceRequirement(key,RequirementMode.WRITE,l.lease_id),))],ResourceDisposition.READY
    if k==1: return LeaseRegistrySnapshot(1,()),[ResourceProposal(p,(ResourceRequirement(key,RequirementMode.WRITE,l.lease_id),))],ResourceDisposition.LEASE_MISSING_HOLD
    if k==2:
        bad=L(i,key,'B','LB'); return LeaseRegistrySnapshot(1,(bad,)),[ResourceProposal(p,(ResourceRequirement(key,RequirementMode.WRITE,bad.lease_id),))],ResourceDisposition.LEASE_IDENTITY_HOLD
    if k==3:
        s=L(i,key,'A','LA',LeaseMode.SHARED_READ); return LeaseRegistrySnapshot(1,(s,)),[ResourceProposal(p,(ResourceRequirement(key,RequirementMode.WRITE,s.lease_id),))],ResourceDisposition.LEASE_IDENTITY_HOLD
    if k==4:
        ex=L(i,key,'A','LA'); sh=L(i+1,key,'B','LB',LeaseMode.SHARED_READ); return LeaseRegistrySnapshot(1,(ex,sh)),[ResourceProposal(p,())],ResourceDisposition.LEASE_CONFLICT_HOLD
    if k==5: return LeaseRegistrySnapshot(1,()),[ResourceProposal(P(i,base='0'*64),())],ResourceDisposition.BASE_HOLD
    if k==6:
        a=P(i,files={'x':'1'*64}); b=P(i+1,actor='B',line='LB',files={'x':'2'*64}); return LeaseRegistrySnapshot(1,()),[ResourceProposal(a,()),ResourceProposal(b,())],ResourceDisposition.BASE_HOLD
    if k==7:
        s1=L(i,key,'A','LA',LeaseMode.SHARED_READ); s2=L(i+1,key,'B','LB',LeaseMode.SHARED_READ); a=P(i,'A','LA'); b=P(i+1,'B','LB'); return LeaseRegistrySnapshot(1,(s1,s2)),[ResourceProposal(a,(ResourceRequirement(key,RequirementMode.READ,s1.lease_id),)),ResourceProposal(b,(ResourceRequirement(key,RequirementMode.READ,s2.lease_id),))],ResourceDisposition.READY
    if k==8:
        old=L(i,key,'A','LA',issued=80000,expires=NOW); return LeaseRegistrySnapshot(1,(old,)),[ResourceProposal(p,(ResourceRequirement(key,RequirementMode.WRITE,old.lease_id),))],ResourceDisposition.LEASE_STALE_HOLD
    if k==9: return LeaseRegistrySnapshot(1,()),[ResourceProposal(p,())],ResourceDisposition.READY
    raise ValueError(k)

def run(n=100000):
    mismatch=false_ready=owner_cas_false=lease_cas_false=forged_plan_escape=expiry_escape=legacy_escape=0; roots=[]
    owner=OwnerSnapshot(H,T)
    for i in range(n):
        k=i%10; reg,ps,exp=classify(i,k); q=plan_resource_absorption(owner,reg,ps,now_s=NOW)
        mismatch += q.disposition!=exp
        false_ready += exp is not ResourceDisposition.READY and q.disposition is ResourceDisposition.READY
        if i<1000: roots.append(q.manifest_root)
    for i in range(1000):
        reg,ps,_=classify(i,0); q=plan_resource_absorption(owner,reg,ps,now_s=NOW)
        r1=commit_resource_absorption(q,observed_owner_head='9'*64,observed_lease_root=reg.root,owner=owner,registry=reg,proposals=ps,now_s=NOW+1)
        moved=LeaseRegistrySnapshot(2,reg.leases); r2=commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=moved.root,owner=owner,registry=moved,proposals=ps,now_s=NOW+1)
        owner_cas_false += r1.committed or bool(r1.write_count); lease_cas_false += r2.committed or bool(r2.write_count)
        forged=replace(q,manifest_root='f'*64,effect_authority=True,gate10=True)
        forged_plan_escape += commit_resource_absorption(forged,observed_owner_head=H,observed_lease_root=reg.root,owner=owner,registry=reg,proposals=ps,now_s=NOW+1).committed
        legacy_escape += commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=reg.root).committed
        key='lease-aging:'+str(i); l=L(i,key,'A','LA',expires=NOW+1); rr=LeaseRegistrySnapshot(1,(l,)); pp=[ResourceProposal(P(i),(ResourceRequirement(key,RequirementMode.WRITE,l.lease_id),))]
        qq=plan_resource_absorption(owner,rr,pp,now_s=NOW)
        expiry_escape += commit_resource_absorption(qq,observed_owner_head=H,observed_lease_root=rr.root,owner=owner,registry=rr,proposals=pp,now_s=NOW+1).committed
    omega=sum(omega8_resource_keeper(x) for x in itertools.product(range(3),repeat=8)); repairs=sum(context13_resource_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5))
    out={'cases':n,'mismatches':mismatch,'false_ready':false_ready,'owner_cas_false':owner_cas_false,'lease_cas_false':lease_cas_false,'forged_plan_escapes':forged_plan_escape,'commit_time_expiry_escapes':expiry_escape,'legacy_commit_escapes':legacy_escape,'hs1000':1000,'omega8_keepers':omega,'omega8_states':6561,'13d_repairs':repairs,'13d_tails':243,'sample_root':digest(roots)}; out['campaign_root']=digest(out)
    print(json.dumps(out,sort_keys=True))
    assert mismatch==false_ready==owner_cas_false==lease_cas_false==forged_plan_escape==expiry_escape==legacy_escape==repairs==0 and omega==1
    return out
if __name__=='__main__': run()
