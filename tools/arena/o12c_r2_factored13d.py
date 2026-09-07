from __future__ import annotations
import hashlib,itertools,inspect,json,sys
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
import memory_city_effect_handoff_o12c_r2 as seam
from memory_city_effect_handoff_o12c_r2 import *
from o12c_r2_lattice_state import mutate

DECISION_FUNCS=(seam.compile_effect_handoff_r2,seam._strict_read_current,seam._strict_admission,seam._strict_refinement,seam._canonical_consequence_root)

def main():
    source='\n'.join(inspect.getsource(f) for f in DECISION_FUNCS)
    decision_context_accesses=source.count('nuisance_context_root')
    if decision_context_accesses != 0:
        raise AssertionError('context unexpectedly enters hard decision logic')

    hard={'states':0,'oracle_tecc':0,'candidate_tecc':0,'false_tecc':0,'false_hold':0,'effect_ready':0}
    for axes in itertools.product(range(3),repeat=8):
        h,t,c,u,ro,a,r,e,m,v=mutate(axes,'f13-hard')
        v=replace(v,nuisance_context_root=digest({'ctx':'canonical'}))
        d=compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v)
        expected=all(x==2 for x in axes); got=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0
        hard['states']+=1;hard['oracle_tecc']+=expected;hard['candidate_tecc']+=got;hard['false_tecc']+=(got and not expected);hard['false_hold']+=((not got) and expected);hard['effect_ready']+=int(getattr(d.disposition,'value',d.disposition)=='READY_D0')
    assert hard['states']==3**8 and hard['false_tecc']==0 and hard['false_hold']==0 and hard['candidate_tecc']==1 and hard['effect_ready']==0

    contexts={'states':0,'tecc':0,'holds':0,'tecc_root_variants':set()}
    base=mutate((2,)*8,'f13-context')
    for tail in itertools.product(range(3),repeat=5):
        h,t,c,u,ro,a,r,e,m,v=base
        v=replace(v,nuisance_context_root=digest({'schema':'AURA-O12C-R2-13D-CONTEXT-v1','tail':tail}))
        d=compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v)
        contexts['states']+=1
        if d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0:
            contexts['tecc']+=1;contexts['tecc_root_variants'].add(d.tecc_input_root)
        else: contexts['holds']+=1
    assert contexts['states']==3**5 and contexts['tecc']==3**5 and contexts['holds']==0 and len(contexts['tecc_root_variants'])==1

    metrics={
        'factored_states':hard['states']*contexts['states'],
        'hard_states_executed':hard['states'],
        'context_states_executed_on_keeper':contexts['states'],
        'hard_valid_states':hard['candidate_tecc'],
        'valid_context_variants':contexts['tecc'],
        'full_13d_tecc_states':hard['candidate_tecc']*contexts['tecc'],
        'full_13d_non_tecc_states':hard['states']*contexts['states']-hard['candidate_tecc']*contexts['tecc'],
        'hard_invalid_repaired_by_context':0,
        'hard_false_tecc':hard['false_tecc'],
        'hard_false_hold':hard['false_hold'],
        'effect_ready':0,
        'decision_context_accesses':decision_context_accesses,
        'tecc_root_variants_across_context':len(contexts['tecc_root_variants']),
    }
    assert metrics['factored_states']==3**13 and metrics['full_13d_tecc_states']==243 and metrics['hard_invalid_repaired_by_context']==0
    payload={'schema':'AURA-MEMORY-CITY-O12C-R2-FACTORED-13D-v1','metrics':metrics,'hard_execution':hard}
    payload['root']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    print(json.dumps(payload,sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
