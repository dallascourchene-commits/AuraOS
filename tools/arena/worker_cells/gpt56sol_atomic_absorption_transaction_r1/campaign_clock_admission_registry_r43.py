from __future__ import annotations
import itertools,json
from dataclasses import replace
from atomic_absorption import Proposal,OwnerSnapshot,digest
from resource_absorption import Lease,LeaseMode,LeaseRegistrySnapshot,RequirementMode,ResourceProposal,ResourceRequirement,plan_resource_absorption
from clock_admission_r42 import guarded_resource_commit,make_admission,make_witness
from clock_admission_registry_r43 import *
H='1'*64;T='2'*64;PLAN=100000;EXP=101000

def fixture(i):
    owner=OwnerSnapshot(H,T); key=f'db:{i%31}'; lease=Lease(digest(('lease',i)),key,'A','LA',LeaseMode.EXCLUSIVE,PLAN-1000,EXP+(i%101),1)
    registry=LeaseRegistrySnapshot(1,(lease,)); p=Proposal(f'P{i}','A','LA',H,digest(('c',i)),digest(('r',i)),{f'f{i%17}.py':digest(('b',i))},False)
    rp=ResourceProposal(p,(ResourceRequirement(key,RequirementMode.WRITE,lease.lease_id),)); submitted=plan_resource_absorption(owner,registry,(rp,),now_s=PLAN)
    return owner,registry,(rp,),submitted,lease.expires_s

def pair(i,t=PLAN+25):
    w=make_witness('owner-clock','g1',t,f'n{i}'); a=make_admission(w,'adm-g1'); return w,a

def decide(i,f):
    owner,registry,proposals,submitted,expiry=fixture(i); w,a=pair(i); e=trusted_entry(w,a); creg=make_registry((e,),i+1); obs=creg.root; expected=False
    if f==0: expected=True
    elif f==1: creg=make_registry((),i+1); obs=creg.root
    elif f==2: creg=make_registry((replace(e,consumed=True),),i+1); obs=creg.root
    elif f==3: obs='f'*64
    elif f==4: w,_=pair(i+1000000)
    elif f==5: creg=ClockAdmissionRegistrySnapshot(i+1,(e,),'D1',False); obs=creg.root
    elif f==6: creg=make_registry((e,e),i+1); obs=creg.root
    elif f==7:
        w,a=pair(i,PLAN-1); e=trusted_entry(w,a); creg=make_registry((e,),i+1); obs=creg.root
    elif f==8:
        w,a=pair(i,expiry); e=trusted_entry(w,a); creg=make_registry((e,),i+1); obs=creg.root
    elif f==9:
        creg=make_registry((),i+1); obs=creg.root
        old=guarded_resource_commit(submitted,observed_owner_head=H,observed_lease_root=registry.root,
            clock_witness=w,clock_admission=a,expected_clock_admission_root=a.currentness_root,
            owner=owner,registry=registry,proposals=proposals)
        assert old.admitted
    r=guarded_resource_commit_r43(submitted,observed_owner_head=H,observed_lease_root=registry.root,
        clock_witness=w,clock_admission=a,clock_registry=creg,observed_clock_registry_root=obs,
        owner=owner,registry=registry,proposals=proposals)
    return r.admitted,expected

def run(n=100000):
    mismatch=false_admit=false_reject=0; fam={i:0 for i in range(10)}
    for i in range(n):
        f=i%10;fam[f]+=1;a,e=decide(i,f);mismatch+=a!=e;false_admit+=a and not e;false_reject+=e and not a
    hs=0
    for f in range(10):
        for j in range(1000):
            a,e=decide(f*1000+j,f);hs+=a!=e
    omega=sum(omega8_r43_keeper(x) for x in itertools.product(range(3),repeat=8)); repairs=sum(collapse13_r43((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5))
    out={'cases':n,'mismatch':mismatch,'false_admit':false_admit,'false_reject':false_reject,'family_counts':fam,'hs1000_cases':10000,'hs1000_escapes':hs,'omega8_states':6561,'omega8_keepers':omega,'13d_tails':243,'13d_repairs':repairs};out['campaign_root']=digest(out)
    assert mismatch==false_admit==false_reject==hs==repairs==0 and omega==1
    print(json.dumps(out,sort_keys=True));return out
if __name__=='__main__':run()
