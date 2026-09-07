from itertools import product
from hashlib import sha256
import json
from tools.arena.o18_lattice8 import AXES
NUISANCE=('k27_locality','cache_heat','route_similarity','provider_availability','presentation_priority')
def run():
 hard=0;lawful=0;repair=0
 for s in product(range(3),repeat=8):
  hard+=1;valid=all(x==2 for x in s)
  for _ in product(range(3),repeat=5):
   lawful+=int(valid);repair+=0
 p={'schema':'aura.o18.13d.v1','hard_axes':AXES,'nuisance_axes':NUISANCE,'hard_states':hard,'cartesian_states':3**13,'lawful_contextual_bind':lawful,'hard_invalid_context_repair':repair,'authority':'D0_NONPROMOTING'};p['root']=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest();return p
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
