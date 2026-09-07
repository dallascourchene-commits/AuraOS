import json
from dataclasses import replace
from hashlib import sha256
from tools.arena.attenuated_stable_operation_delegation import *
def r(x):return sha256(x.encode()).hexdigest()
def base():
 op=StableOperation('TRAINING',r('sem'),'TRAIN_ADAPTER',r('src'),r('policy'));h=(DelegationHop('A',frozenset({'read','train','render'}),100,1),DelegationHop('B',frozenset({'read','train'}),50,2));a=DomainAdmission('TRAINING',op.root(),r('adm'),frozenset({'read','train'}),60,3,True,True);c=AttemptContext('B',r('wc'),1,True,r('lease'),True,op.source_incarnation_root,frozenset({'train'}),20);return op,h,a,c
def run(n=24000):
 out={'cases':n,'false_admit':0,'false_hold':0,'naive_local_token_unsafe':0,'naive_handoff_trust_unsafe':0,'authority_promotions':0};reasons={}
 for i in range(n):
  op,h,a,c=base();valid=True;mode=i%12
  if mode==0:pass
  elif mode==1:h=(h[0],replace(h[1],scope=frozenset({'read','train','delete'})));valid=False
  elif mode==2:h=(h[0],replace(h[1],budget=101));valid=False
  elif mode==3:h=(replace(h[0],current=False),h[1]);valid=False
  elif mode==4:a=replace(a,proof_bound=False);valid=False
  elif mode==5:a=replace(a,current=False);valid=False
  elif mode==6:c=replace(c,source_incarnation_root=r('moved'));valid=False
  elif mode==7:c=replace(c,workcell_current=False);valid=False
  elif mode==8:c=replace(c,lease_current=False);valid=False
  elif mode==9:c=replace(c,requested_scope=frozenset({'render'}));valid=False
  elif mode==10:c=replace(c,requested_budget=51);valid=False
  elif mode==11:op=replace(op,semantic_root=r('new'));valid=False
  d=decide(op,h,a,c);admitted=d.disposition is Disposition.ADMIT_D0;out['false_admit']+=int(admitted and not valid);out['false_hold']+=int((not admitted) and valid);local=h[-1];out['naive_local_token_unsafe']+=int(c.requested_scope.issubset(local.scope) and c.requested_budget<=local.budget and not valid);out['naive_handoff_trust_unsafe']+=int(a.operation_root==op.root() and a.domain==op.domain and not valid);out['authority_promotions']+=int(d.effect_authority or d.training_authority or d.checkpoint_authority or d.gate10);reasons[d.reason]=reasons.get(d.reason,0)+1
 out['reasons']=dict(sorted(reasons.items()));out['root']=sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest();return out
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
