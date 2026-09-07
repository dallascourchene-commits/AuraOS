from itertools import product
from hashlib import sha256
import json
from campaign_memory_city_horizon_fenced_handoff import evaluate_hard_state
from memory_city_horizon_fenced_handoff import HandoffDisposition
HARD_AXES=('current_read_binding','component_correct_reproof','canonical_coverage_admission','effect_obligation_refinement','mutation_identity','installed_lease_holder_fence','owner_verifier_evidence','authority_separation')
def run():
    counts={'states':0,'tecc_route':0,'invalid_route':0,'valid_false_hold':0,'effect_ready':0}
    for hard in product(range(3),repeat=8):
        d,_=evaluate_hard_state(hard)
        valid=all(x==2 for x in hard); routed=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0
        counts['states']+=1; counts['tecc_route']+=int(routed); counts['invalid_route']+=int(routed and not valid); counts['valid_false_hold']+=int(valid and not routed); counts['effect_ready']+=int(d.effect_authority)
    p={'schema':'aura.mc_o13.omega8.executable.v1','hard_axes':HARD_AXES,**counts,'authority':'D0_NONPROMOTING_GATE10_FALSE'}
    p['root']=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if p['states']!=6561 or p['tecc_route']!=1 or p['invalid_route'] or p['valid_false_hold'] or p['effect_ready']: raise AssertionError(p)
    return p
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
