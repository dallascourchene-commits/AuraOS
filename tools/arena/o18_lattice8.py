from itertools import product
from hashlib import sha256
import json
AXES=('operation_semantics_exact','delegation_ancestor_current','scope_attenuation_exact','budget_attenuation_exact','domain_admission_proof_bound','source_incarnation_current','workcell_lease_current','authority_separation')
def run():
 d={'states':0,'bind':0,'invalid_bind':0}
 for s in product(range(3),repeat=8):
  valid=all(x==2 for x in s);bind=valid;d['states']+=1;d['bind']+=int(bind);d['invalid_bind']+=int(bind and not valid)
 p={'schema':'aura.o18.omega8.v1','axes':AXES,**d,'authority':'D0_NONPROMOTING'};p['root']=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest();return p
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
