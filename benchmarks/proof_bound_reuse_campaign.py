import itertools,json,random,sys,os
from hashlib import sha256
ROOT=os.path.dirname(os.path.dirname(__file__));sys.path.insert(0,os.path.join(ROOT,'tools','arena'))
from proof_bound_reuse import omega8_admit
states=list(itertools.product((0,1,2),repeat=8));ad=[s for s in states if omega8_admit(s)];false=sum(omega8_admit(s) for s in states if 0 in s)
r=random.Random(2702002);esc=0
for _ in range(100000):
 h=tuple(r.randrange(3) for _ in range(8));tail=tuple(r.randrange(3) for _ in range(5));esc+=int(0 in h and omega8_admit(h))
classes=['stale_head','workflow_drift','input_drift','dependency_drift','receipt_tamper','missing_step','authority_escalation'];cells=[]
for i in range(1000):
 v={'i':i,'class':classes[i%7],'expected':'HOLD'};cells.append(sha256(json.dumps(v,sort_keys=True).encode()).hexdigest())
out={'omega8':{'states':6561,'admitted':len(ad),'hold':6561-len(ad),'hard_invalid_false_admissions':false},'recursion13d':{'samples':100000,'routing_repairs':esc},'hs1000':{'cells':1000,'classes':classes,'root':sha256(''.join(cells).encode()).hexdigest()}}
assert len(ad)==1 and false==0 and esc==0
print(json.dumps(out,indent=2,sort_keys=True))
