from itertools import product
from hashlib import sha256
import json
AXES=('current_read_world_binding','component_correct_reproof','current_coverage_and_admission','effect_mode_tecc_seal','mutation_identity','installed_current_fence_and_lease','owner_verifier_evidence','authority_ceiling_separation')
def candidate(a):
    if any(x==0 for x in a): return 'HOLD_HARD_INVALID'
    if any(x==1 for x in a): return 'HOLD_UNRESOLVED'
    return 'HOLD_TECC_REQUIRED_D0'
def generic_effect_baseline(a): return all(a[i]==2 for i in (0,4,5,6))
def run():
    counts={'states':0,'candidate_tecc_route':0,'candidate_effect_ready':0,'legacy_effect_ready':0,'legacy_false_effect_upgrade':0}
    for a in product(range(3),repeat=8):
        counts['states']+=1; c=candidate(a); valid=(a==(2,)*8); counts['candidate_tecc_route']+=int(c=='HOLD_TECC_REQUIRED_D0'); counts['legacy_effect_ready']+=int(generic_effect_baseline(a)); counts['legacy_false_effect_upgrade']+=int(generic_effect_baseline(a) and not valid)
    payload={'schema':'aura.o12c.lattice8.v1','axes':AXES,**counts,'keeper_states':1,'authority':'D0_NONPROMOTING_GATE10_FALSE'}; payload['root']=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return payload
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
