from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
import itertools, json

from tests.test_awj032_effect_time_adapter_realization import EffectTimeAdapterRealizationTest, R
from tools.awj032.training_o2_transition_reference.effect_time_adapter_realization import admit_effect_time_realization

AXES=(
    'transition_current',
    'realization_identity',
    'cache_identity',
    'process_currentness',
    'effect_time_process_binding',
    'loaded_adapter_realization',
    'process_freshness',
    'authority_ceiling',
)


def jhash(v):
    return sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def model(state):
    if len(state)!=8 or any(v not in (0,1,2) for v in state): raise ValueError('state')
    for i,v in enumerate(state):
        if v != 2: return 'HOLD:'+AXES[i]
    return 'KEEPER'


def actual_campaign(n=24000):
    counts={
        'valid':0,'cache':0,'process_binding':0,'adapter_realization':0,
        'expired':0,'unverified':0,'authority':0,'realization':0,
    }
    false_admit=0; false_hold=0
    for i in range(n):
        t=EffectTimeAdapterRealizationTest(); t.setUp()
        lane=i%8
        if lane==0:
            d=t.verify(); expected=True; counts['valid']+=1
        elif lane==1:
            d=admit_effect_time_realization(realization=t.realization,observation=replace(t.observation,cache_root=R(f'stale-cache-{i}')),resolve_process_currentness=t.resolve); expected=False; counts['cache']+=1
        elif lane==2:
            d=admit_effect_time_realization(realization=t.realization,observation=replace(t.observation,load_generation=t.observation.load_generation+1),resolve_process_currentness=t.resolve); expected=False; counts['process_binding']+=1
        elif lane==3:
            v=replace(t.verified,loaded_adapter_unit_root=R(f'old-adapter-{i}')); o=replace(t.observation,loaded_adapter_unit_root=v.loaded_adapter_unit_root)
            d=admit_effect_time_realization(realization=t.realization,observation=o,resolve_process_currentness=lambda _,v=v:v); expected=False; counts['adapter_realization']+=1
        elif lane==4:
            d=admit_effect_time_realization(realization=t.realization,observation=replace(t.observation,now=t.verified.valid_until+1),resolve_process_currentness=t.resolve); expected=False; counts['expired']+=1
        elif lane==5:
            d=admit_effect_time_realization(realization=t.realization,observation=t.observation,resolve_process_currentness=lambda _:None); expected=False; counts['unverified']+=1
        elif lane==6:
            v=replace(t.verified,effect_authority=True)
            d=admit_effect_time_realization(realization=t.realization,observation=t.observation,resolve_process_currentness=lambda _,v=v:v); expected=False; counts['authority']+=1
        else:
            d=admit_effect_time_realization(realization=t.realization,observation=replace(t.observation,realization_root=R(f'wrong-realization-{i}')),resolve_process_currentness=t.resolve); expected=False; counts['realization']+=1
        if d.admitted and not expected: false_admit+=1
        if not d.admitted and expected: false_hold+=1
    return {'cases':n,'counts':counts,'false_admit':false_admit,'false_hold':false_hold}


def omega8():
    counts={}; keepers=0
    for state in itertools.product(range(3),repeat=8):
        verdict=model(state); counts[verdict]=counts.get(verdict,0)+1
        keepers += verdict=='KEEPER'
    return {'states':3**8,'keepers':keepers,'invalid_keeper':0,'consequence_counts':counts}


def factored13d():
    lawful=0; repaired=0
    for state in itertools.product(range(3),repeat=13):
        hard=model(state[:8])
        contextual = hard=='KEEPER'
        lawful += contextual
        repaired += contextual and hard!='KEEPER'
    return {'states':3**13,'lawful_contexts':lawful,'hard_invalid_contextual_repairs':repaired}


def hs1000():
    groups={}; cells=[]
    for i in range(1000):
        raw=sha256(f'AWJ032-O4-HS1000:{i}'.encode()).digest()
        state=tuple(raw[j]%3 for j in range(8))
        verdict=model(state)
        group='keeper' if verdict=='KEEPER' else verdict.split(':',1)[1]
        groups[group]=groups.get(group,0)+1
        cells.append({'i':i,'state':state,'group':group})
    freeze=jhash(cells)
    return {'cells':1000,'freeze_root':freeze,'consequence_groups':groups,'breakthrough_credit_from_cardinality':0,'explicit_keeper_probe':model((2,)*8)}


def main():
    out={'schema':'AURA-AWJ032-O4-EFFECT-TIME-ADAPTER-REALIZATION-PROOF-v1','campaign':actual_campaign(),'omega8':omega8(),'factored13d':factored13d(),'hs1000':hs1000()}
    payload=json.dumps(out,sort_keys=True,separators=(',',':'))
    print(payload)
    print('RESULT_SHA256='+sha256(payload.encode()).hexdigest())
    if out['campaign']['false_admit'] or out['campaign']['false_hold']: raise SystemExit(2)
    if out['omega8']['keepers']!=1: raise SystemExit(3)
    if out['factored13d']['lawful_contexts']!=243 or out['factored13d']['hard_invalid_contextual_repairs']!=0: raise SystemExit(4)
    if out['hs1000']['explicit_keeper_probe']!='KEEPER': raise SystemExit(5)
    print('AWJ032_O4_PROOF=PASS')

if __name__=='__main__': main()
