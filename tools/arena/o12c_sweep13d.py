from __future__ import annotations
from itertools import product
from hashlib import sha256
import json, multiprocessing as mp, os
from campaign_memory_city_horizon_fenced_handoff import build_hard_state, invoke, digest
from memory_city_horizon_fenced_handoff import HandoffDisposition

HARD_AXES=('current_read_binding','component_correct_reproof','canonical_coverage_admission','effect_obligation_refinement','mutation_identity','installed_lease_holder_fence','owner_verifier_evidence','authority_separation')
CONTEXT_AXES=('k27_locality','cache_heat','route_similarity','provider_availability','presentation_priority')

def worker(prefix):
    prepared=[(hard,build_hard_state(hard)) for hard in product(range(3),repeat=8)]
    counts={'states':0,'tecc_route':0,'invalid_route':0,'valid_false_hold':0,'effect_ready':0,'hard_invalid_repaired_by_context':0}
    hh=sha256()
    for tail in product(range(3),repeat=3):
        context=prefix+tail
        context_root=digest({'kind':'non_authoritative_context','axes':context})
        for hard,fx in prepared:
            d=invoke(fx); valid=all(x==2 for x in hard); routed=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0
            counts['states']+=1; counts['tecc_route']+=int(routed); counts['invalid_route']+=int(routed and not valid)
            counts['valid_false_hold']+=int(valid and not routed); counts['effect_ready']+=int(d.effect_authority)
            counts['hard_invalid_repaired_by_context']+=int(routed and not valid)
            hh.update((''.join(map(str,hard+context))+'|'+d.disposition.value+'|'+d.reason+'|'+(d.tecc_input_root or '-')+'|'+context_root+'\n').encode())
    return prefix,counts,hh.hexdigest()

def run():
    prefixes=list(product(range(3),repeat=2))
    procs=min(len(prefixes),max(1,os.cpu_count() or 1))
    with mp.Pool(procs) as pool: parts=pool.map(worker,prefixes)
    parts=sorted(parts,key=lambda x:x[0])
    total={'states':0,'tecc_route':0,'invalid_route':0,'valid_false_hold':0,'effect_ready':0,'hard_invalid_repaired_by_context':0}
    for _,c,_ in parts:
        for k in total: total[k]+=c[k]
    payload={'schema':'aura.mc_o13.sweep13d.executable.v1','hard_axes':HARD_AXES,'context_axes':CONTEXT_AXES,
             'context_variants':3**5,**total,'partition_roots':[{'prefix':list(p),'root':h} for p,_,h in parts],
             'authority':'D0_NONPROMOTING_GATE10_FALSE'}
    payload['root']=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if payload['states']!=3**13 or payload['tecc_route']!=3**5 or payload['invalid_route'] or payload['valid_false_hold'] or payload['effect_ready'] or payload['hard_invalid_repaired_by_context']:
        raise AssertionError(payload)
    return payload
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
