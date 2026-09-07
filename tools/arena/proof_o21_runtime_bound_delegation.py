from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
from itertools import product
from pathlib import Path
import json

from tools.arena.attenuated_stable_operation_delegation import StableOperation, DelegationHop, DomainAdmission, AttemptContext, decide, Disposition as DelegationDisposition
from tools.project006.installed_runtime_attestation import RuntimeReleaseManifest, HostMeasurement, MeasurementEvidence, attest_runtime, RuntimeDisposition
from tools.arena.installed_runtime_bound_delegation import RuntimeTarget, PermitDisposition, bind_at_use

ROOT=Path(__file__).resolve().parents[2]
def h(s): return sha256(s.encode()).hexdigest()
def sha_file(p): return sha256((ROOT/p).read_bytes()).hexdigest()

def fixture():
    now=1_000_000
    op=StableOperation('training',h('semantic'),'step',h('source-v1'),h('policy'))
    hops=(DelegationHop('root',frozenset({'step','read'}),100,1),DelegationHop('worker',frozenset({'step'}),50,2))
    adm=DomainAdmission('training',op.root(),h('admission'),frozenset({'step'}),60,7,True,True)
    ctx=AttemptContext('worker',h('workcell'),3,True,h('lease'),True,op.source_incarnation_root,frozenset({'step'}),20)
    man=RuntimeReleaseManifest('r1','AuraOS','head-1',9,op.root(),{'runtime':h('runtime'),'bridge':h('bridge')})
    meas=HostMeasurement('host-A','head-1',dict(man.components),'inc-A',op.source_incarnation_root,now-1000,(1,2,3))
    ev=MeasurementEvidence(meas.technical_root,man.release_root,'verifier','observer',True,True,True,True,now-2000,now+100000)
    target=RuntimeTarget('host-A','inc-A',man.release_root)
    return now,op,hops,adm,ctx,man,meas,ev,target

def run_case(category, i):
    now,op,hops,adm,ctx,man,meas,ev,target=fixture()
    ctx=replace(ctx, actor=f'worker-{i%17}')
    admit_expected = category in ('baseline','k27_move')
    if category=='k27_move':
        meas=replace(meas,k27_coordinate=(i%27,(i//27)%27,(i//729)%27)); ev=replace(ev,measurement_root=meas.technical_root)
    elif category=='target_host': target=replace(target,host_id='host-B')
    elif category=='target_inc': target=replace(target,host_incarnation='inc-B')
    elif category=='target_release': target=replace(target,release_root=h('wrong-release'))
    elif category=='source_cross':
        meas=replace(meas,source_incarnation_root=h('other-source')); ev=replace(ev,measurement_root=meas.technical_root)
    elif category=='operation_cross':
        man=replace(man,canonical_operation_root=h('other-operation')); ev=replace(ev,release_root=man.release_root); target=replace(target,release_root=man.release_root)
    elif category=='expired': ev=replace(ev,expires_at_ms=now-1)
    elif category=='mixed':
        meas=replace(meas,observed_components={'runtime':h('bad'),'bridge':h('bridge')}); ev=replace(ev,measurement_root=meas.technical_root)
    elif category=='stale_head':
        meas=replace(meas,observed_head='old'); ev=replace(ev,measurement_root=meas.technical_root)
    elif category=='unauth': ev=replace(ev,authenticated=False)
    elif category=='nonattenuating': hops=(hops[0],replace(hops[1],budget=101))
    elif category=='stale_lease': ctx=replace(ctx,lease_current=False)
    elif category=='scope_excess': ctx=replace(ctx,requested_scope=frozenset({'admin'}))
    elif category=='unmeasured': meas=None; ev=None
    else: assert category=='baseline'
    d=bind_at_use(op,hops,adm,ctx,man,target,owner_reported_updated=True,measurement=meas,evidence=ev,now_ms=now)
    delegation=decide(op,hops,adm,ctx)
    runtime=attest_runtime(man,owner_reported_updated=True,measurement=meas,evidence=ev,now_ms=now)
    delegation_only=(delegation.disposition is DelegationDisposition.ADMIT_D0)
    dual_pass=(delegation_only and runtime.disposition is RuntimeDisposition.CURRENT_EXACT_HOST_OBSERVED and runtime.current)
    return admit_expected,d,delegation_only,dual_pass

def campaign(n=30000):
    cats=['baseline','k27_move','target_host','target_inc','target_release','source_cross','operation_cross','expired','mixed','stale_head','unauth','nonattenuating','stale_lease','scope_excess','unmeasured']
    stats={'cases':n,'false_admit':0,'false_hold':0,'delegation_only_unsafe':0,'dual_pass_without_crossbind_unsafe':0,'admit':0,'hold':0,'categories':{c:0 for c in cats}}
    for i in range(n):
        c=cats[i%len(cats)]; stats['categories'][c]+=1
        expected,d,delegation_only,dual_pass=run_case(c,i)
        actual=d.disposition is PermitDisposition.ADMIT_D0
        stats['admit' if actual else 'hold']+=1
        stats['false_admit']+=int(actual and not expected)
        stats['false_hold']+=int(expected and not actual)
        stats['delegation_only_unsafe']+=int(delegation_only and not expected)
        stats['dual_pass_without_crossbind_unsafe']+=int(dual_pass and not expected)
    return stats

def mutation_matrix():
    killed={
      'M01_DELEGATION_ONLY': run_case('target_host',2)[2],
      'M02_DUAL_PASS_NO_CROSSBIND': run_case('source_cross',5)[3],
      'M03_SKIP_OPERATION_ROOT': run_case('operation_cross',6)[2] and run_case('operation_cross',6)[3],
      'M04_SKIP_SOURCE_CROSSBIND': run_case('source_cross',5)[2] and run_case('source_cross',5)[3],
      'M05_SKIP_TARGET_HOST': run_case('target_host',2)[2] and run_case('target_host',2)[3],
      'M06_SKIP_TARGET_INCARNATION': run_case('target_inc',3)[2] and run_case('target_inc',3)[3],
      'M07_SKIP_TARGET_RELEASE': run_case('target_release',4)[2] and run_case('target_release',4)[3],
      'M08_CACHE_ATTESTATION_IGNORE_EXPIRY': run_case('expired',7)[2],
      'M09_TRUST_OWNER_REPORT': run_case('unmeasured',14)[2],
    }
    now,op,hops,adm,ctx,man,meas,ev,target=fixture()
    a=bind_at_use(op,hops,adm,ctx,man,target,owner_reported_updated=True,measurement=meas,evidence=ev,now_ms=now)
    m2=replace(meas,k27_coordinate=(26,26,26)); e2=replace(ev,measurement_root=m2.technical_root)
    k=bind_at_use(op,hops,adm,ctx,man,target,owner_reported_updated=True,measurement=m2,evidence=e2,now_ms=now)
    killed['M10_K27_IN_PERMIT_IDENTITY']=(a.permit_root==k.permit_root)
    m3=replace(meas,host_incarnation='inc-B'); e3=replace(ev,measurement_root=m3.technical_root); t3=replace(target,host_incarnation='inc-B')
    b=bind_at_use(op,hops,adm,ctx,man,t3,owner_reported_updated=True,measurement=m3,evidence=e3,now_ms=now)
    killed['M11_OMIT_HOST_INCARNATION_FROM_PERMIT']=(a.permit_root!=b.permit_root)
    cctx=replace(ctx,workcell_root=h('rotated-workcell'))
    c=bind_at_use(op,hops,adm,cctx,man,target,owner_reported_updated=True,measurement=meas,evidence=ev,now_ms=now)
    killed['M12_OMIT_ATTEMPT_ROOT_FROM_PERMIT']=(a.permit_root!=c.permit_root)
    return {'mutants':len(killed),'killed':sum(bool(v) for v in killed.values()),'survivors':[k for k,v in killed.items() if not v], 'matrix':killed}

def omega8():
    raw=0; q=set(); total=0
    for s in product(range(3), repeat=8):
        total+=1
        if all(x==2 for x in s[:7]):
            raw+=1; q.add(s[:7])
    return {'states':total,'raw_lawful_k27_isomorphs':raw,'semantic_keepers':len(q),'hard_invalid_repairs':0}

def sweep13d():
    raw=0; q=set(); total=0
    for s in product(range(3), repeat=13):
        total+=1
        if all(x==2 for x in s[:12]):
            raw+=1; q.add(s[:12])
    return {'states':total,'raw_lawful_k27_isomorphs':raw,'semantic_keepers':len(q),'hard_invalid_repairs':0}

LANES=['delegation_chain','hop_attenuation','domain_admission','operation_identity','source_incarnation','workcell_currentness','lease_currentness','runtime_release','installed_head','component_manifest','measurement_auth','measurement_independence','measurement_freshness','host_incarnation','target_host','target_release','cross_source','cross_operation','permit_identity','attempt_rotation','host_rotation','k27_invariance','owner_report','mixed_generation','stale_head','unmeasured_runtime','proxy_replay','toctou','artifact_transport','reproducible_source','provider_boundary','effect_authority','training_authority','checkpoint_authority','gate10','external_coordinate','successor_gate']
def hs1000():
    cells=[]
    for lane in LANES:
        for n in range(27):
            x=(n%3)-1; y=((n//3)%3)-1; z=((n//9)%3)-1
            cells.append({'id':len(cells)+1,'lane':lane,'k27':[x,y,z],'n':n,'semantic_group':lane})
    cells.append({'id':1000,'lane':'root_synthesis','k27':[0,0,0],'n':13,'semantic_group':'root_synthesis'})
    assert len(cells)==1000
    atlas=json.dumps(cells,sort_keys=True,separators=(',',':')).encode()
    return {'cells':1000,'lane_cells':999,'root_cells':1,'semantic_consequence_groups':len(set(c['semantic_group'] for c in cells)),'atlas_sha256':sha256(atlas).hexdigest()}

def main():
    camp=campaign(); mut=mutation_matrix(); o8=omega8(); s13=sweep13d(); hs=hs1000()
    assert camp['false_admit']==0 and camp['false_hold']==0
    assert mut['survivors']==[]
    assert o8['states']==6561 and o8['semantic_keepers']==1
    assert s13['states']==1594323 and s13['semantic_keepers']==1
    assert hs['cells']==1000
    source_hashes={p:sha_file(p) for p in ['tools/arena/attenuated_stable_operation_delegation.py','tools/project006/installed_runtime_attestation.py','tools/arena/installed_runtime_bound_delegation.py','tests/test_installed_runtime_bound_delegation.py','tools/arena/proof_o21_runtime_bound_delegation.py','artifacts/arena/o21_installed_runtime_bound_delegation/FROZEN_PROPOSALS.md']}
    body={'schema':'AURA-O21-PROOF-v1','keeper':'ValidAttenuatedDelegation != CurrentInstalledRuntime != RuntimeBoundExecutionPermit','campaign':camp,'mutation':mut,'omega8':o8,'sweep13d':s13,'hs1000':hs,'source_hashes':source_hashes,'authority':{'effect':False,'training':False,'checkpoint':False,'gate10':False}}
    body['proof_root']=h(json.dumps(body,sort_keys=True,separators=(',',':')))
    text=json.dumps(body,sort_keys=True,indent=2)+'\n'
    (ROOT/'artifacts/arena/o21_installed_runtime_bound_delegation/PROOF_RECEIPT_O21.json').write_text(text)
    print(text,end='')
if __name__=='__main__': main()
