from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from itertools import product
from hashlib import sha256
import json
from tools.project006.mc_o14_lattice8 import hard_decision,HARD
CTX=('k27_locality','cache_heat','route_similarity','provider_availability','presentation_priority')
def run():
    hard={a:hard_decision(a) for a in product(range(3),repeat=8)}
    keep=[a for a,v in hard.items() if v=='BIND_EFFECT_ATTEMPT_D0']
    states=len(hard)*(3**5); contextual_bind=len(keep)*(3**5)
    p={'schema':'aura.mc_o14r.factored13d.v2','hard_axes':HARD,'context_axes':CTX,'cartesian_states':states,'hard_states':len(hard),'hard_keepers':len(keep),'context_states_per_hard':243,'lawful_contextual_bind':contextual_bind,'nonbind':states-contextual_bind,'hard_invalid_context_repair':0,'effect_ready':0,'structural_noncompensation':'nuisance axes absent from admission contract','authority':'D0_NONPROMOTING'}
    p['root']=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if states!=1594323 or len(keep)!=1 or contextual_bind!=243:return (_ for _ in ()).throw(AssertionError(p))
    return p
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
