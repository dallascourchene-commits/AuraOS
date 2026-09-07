from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from itertools import product
from hashlib import sha256
import json
from tools.project006.o17_lattice8 import HARD,decide,D0

CTX=("k27_locality","cache_heat","route_similarity","provider_availability","presentation_priority")
def run():
    states=0; lawful=0; repaired=0
    for axes in product(range(3),repeat=13):
        hard=axes[:8]; d=decide(hard); ok=all(x==2 for x in hard); states+=1
        lawful+=int(d=="BIND_OBSERVATION_D0")
        repaired+=int(d=="BIND_OBSERVATION_D0" and not ok)
    out={"schema":"aura.project006.o17.factored13d.v1","hard_axes":HARD,"context_axes":CTX,"cartesian_states":states,"lawful_contextual_bind":lawful,"hard_invalid_context_repair":repaired,"effect_ready":0,"authority":D0,"structural_noncompensation":"K27/cache/routing/provider/presentation context cannot repair source/proof invalidity"}
    out["root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if states!=1594323 or lawful!=243 or repaired: raise AssertionError(out)
    return out
if __name__=="__main__": print(json.dumps(run(),sort_keys=True,indent=2))
