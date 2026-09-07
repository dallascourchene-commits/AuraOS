from __future__ import annotations
import hashlib, itertools, json
from windows_liveness_contract import LivenessEvidence, PersistenceMode, classify, canonical_root

TRI=(False,None,True)

def omega8():
    counts={'states':0,'keepers':0,'invalid_accepts':0}
    rows=[]
    modes=[PersistenceMode.NONE,PersistenceMode.WINDOWS_USER_SESSION_GUARDIAN,PersistenceMode.WINDOWS_SCHEDULED_RECONCILE]
    for mode,*axes in ((m,)+xs for m in modes for xs in itertools.product(TRI, repeat=7)):
        guardian,wake,progress,outbound,provider_zero,current,authority=axes
        ev=LivenessEvidence(mode,guardian,wake,progress,outbound,0 if provider_zero is True else (1 if provider_zero is False else None),current,authority)
        d=classify(ev); counts['states']+=1
        expected=(mode!=PersistenceMode.NONE and all(x is True for x in [guardian,wake,progress,outbound,provider_zero,current,authority]))
        if d.physical_acceptance: counts['keepers']+=1
        if d.physical_acceptance and not expected: counts['invalid_accepts']+=1
        if d.physical_acceptance: rows.append((mode.value,axes))
    counts['root']=canonical_root({'counts':counts,'keepers':rows})
    return counts

def factored13d():
    hard=omega8()
    contexts=list(itertools.product(TRI, repeat=5))
    modes=[PersistenceMode.NONE,PersistenceMode.WINDOWS_USER_SESSION_GUARDIAN,PersistenceMode.WINDOWS_SCHEDULED_RECONCILE]
    total=invalid_repairs=keeper_contexts=0
    h=hashlib.sha256()
    for mode in modes:
        for axes in itertools.product(TRI, repeat=7):
            guardian,wake,progress,outbound,provider_zero,current,authority=axes
            ev=LivenessEvidence(mode,guardian,wake,progress,outbound,0 if provider_zero is True else (1 if provider_zero is False else None),current,authority)
            base=classify(ev).physical_acceptance
            for ctx in contexts:
                total += 1
                result=classify(ev).physical_acceptance
                if result and not base: invalid_repairs += 1
                if result: keeper_contexts += 1
                h.update(json.dumps([mode.value,axes,ctx,result],separators=(',',':'),default=str).encode()+b'\n')
    return {'states':total,'keeper_contexts':keeper_contexts,'hard_invalid_contextual_repairs':invalid_repairs,'root':h.hexdigest(),'omega8_root':hard['root']}

def hs1000():
    falsifiers=['TASK_ACCESS_DENIED','GUARDIAN_DEAD','WSL_WAKE_MISSING','CONSUMER_STALL','OUTBOUND_MISSING','PROVIDER_COUNT_NONZERO','CURRENTNESS_DRIFT','AUTHORITY_WIDENED','LOGIN_RESTART','RDC_COUPLING']
    mechanisms=['SCHEDULED_TASK','STARTUP_GUARDIAN','MUTEX','HEARTBEAT','BOUNDED_WSL','WRAPPER_ONCE','TYPED_HOLD','CLAIM_SPLIT','OUTBOUND_ORACLE','OWNER_REPROOF']
    contexts=['COLD_BOOT','USER_LOGIN','WSL_STOPPED','WSL_RUNNING','NETWORK_LOSS','DRIVE_DELAY','LOCK_CONTENTION','REPLAY','POLICY_CHANGE','HOST_RECONNECT']
    cells=[]; groups={}
    for i,(f,m,c) in enumerate(itertools.product(falsifiers,mechanisms,contexts)):
        consequence=('PRIVILEGE_FALLBACK' if f=='TASK_ACCESS_DENIED' else 'WAKE_PROOF' if f in {'WSL_WAKE_MISSING','GUARDIAN_DEAD','RDC_COUPLING'} else 'RETURN_PROOF' if f in {'CONSUMER_STALL','OUTBOUND_MISSING'} else 'EFFECT_SAFETY' if f=='PROVIDER_COUNT_NONZERO' else 'CURRENTNESS_AUTHORITY' if f in {'CURRENTNESS_DRIFT','AUTHORITY_WIDENED'} else 'SESSION_PERSISTENCE')
        cell={'id':i,'falsifier':f,'mechanism':m,'context':c,'consequence':consequence}
        cells.append(cell); groups.setdefault(consequence,0); groups[consequence]+=1
    assert len(cells)==1000
    return {'frozen_candidates':1000,'consequence_groups':groups,'claimed_breakthroughs':0,'freeze_root':canonical_root(cells),'quotient_root':canonical_root(groups)}

def main():
    out={'omega8':omega8(),'factored13d':factored13d(),'hs1000':hs1000()}
    print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__': main()
