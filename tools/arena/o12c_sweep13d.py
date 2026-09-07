from itertools import product
from hashlib import sha256
import json
HARD_AXES=('current_read_world_binding','component_correct_reproof','current_coverage_and_admission','effect_mode_tecc_seal','mutation_identity','installed_current_fence_and_lease','owner_verifier_evidence','authority_ceiling_separation')
CONTEXT_AXES=('k27_locality','cache_heat','route_similarity','provider_availability','presentation_priority')
def run():
    n=tecc=hard_invalid_repaired=legacy_effect=legacy_false=0
    for a in product(range(3),repeat=13):
        n+=1; hard=a[:8]; candidate=all(x==2 for x in hard); tecc+=candidate; hard_invalid_repaired+=int(candidate and any(x!=2 for x in hard)); legacy=all(hard[i]==2 for i in (0,4,5,6)); legacy_effect+=legacy; legacy_false+=int(legacy and not candidate)
    p={'schema':'aura.o12c.sweep13d.v1','hard_axes':HARD_AXES,'context_axes':CONTEXT_AXES,'states':n,'candidate_tecc_route':tecc,'candidate_effect_ready':0,'hard_invalid_repaired':hard_invalid_repaired,'legacy_effect_ready':legacy_effect,'legacy_false_effect_upgrade':legacy_false,'authority':'D0_NONPROMOTING_GATE10_FALSE'}; p['root']=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return p
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
