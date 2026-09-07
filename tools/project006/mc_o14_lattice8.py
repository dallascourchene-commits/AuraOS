from itertools import product
from hashlib import sha256
import json
HARD=('producer_exact','consumer_exact_independent','verifier_authorization_exact','semantic_generation_current','operation_lineage_exact','journal_owner_current','durable_admission_exact','authority_separation')
def hard_decision(a):
    if len(a)!=8 or any(x not in (0,1,2) for x in a): return 'HOLD_MALFORMED'
    if 0 in a:return 'HOLD_HARD_INVALID'
    if 1 in a:return 'HOLD_UNRESOLVED'
    return 'BIND_EFFECT_ATTEMPT_D0'
def run():
    d={'states':0,'bind':0,'invalid_bind':0}
    for a in product(range(3),repeat=8):
        x=hard_decision(a); valid=all(v==2 for v in a); d['states']+=1; d['bind']+=int(x=='BIND_EFFECT_ATTEMPT_D0'); d['invalid_bind']+=int(x=='BIND_EFFECT_ATTEMPT_D0' and not valid)
    p={'schema':'aura.mc_o14.omega8.v1','hard_axes':HARD,**d,'effect_ready':0,'authority':'D0_NONPROMOTING'}; p['root']=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if p['states']!=6561 or p['bind']!=1 or p['invalid_bind']: raise AssertionError(p)
    return p
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
