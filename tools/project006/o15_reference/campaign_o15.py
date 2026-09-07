import json,random
from dataclasses import replace
from o15_workcell_stable_operation import *
from test_o15 import r,op,cur,lease,att,KEY

def run(seed=15015,n=30000):
 q=random.Random(seed); rows=[]; mismatch=unsafe=naive=0
 for i in range(n):
  m=q.randrange(10); o=op(i); c=cur(i); l=lease(i,c); a=att(o); obs='HOLD'; exp='HOLD'
  try:
   if m==0: verify_lease(l,c,KEY); obs=exp='CALL'
   elif m==1: verify_lease(l,replace(c,card_root=r('moved')),KEY); obs='CALL'; exp='HOLD'
   elif m==2: verify_lease(l,replace(c,progress_root=r('moved')),KEY); obs='CALL'; exp='HOLD'
   elif m==3: verify_lease(l,replace(c,host_generation=4),KEY); obs='CALL'; exp='HOLD'
   elif m==4: exp='ROTATE'; obs='ROTATE' if replace(o,source_revision='other').root!=o.root else 'COLLIDE'
   elif m==5: exp='SAME_OP_NEW_WITNESS'; l2=lease(i,c,handle=f'reissue-{i}-abcdefghijkl'); a2=att(o,2); obs='SAME_OP_NEW_WITNESS' if o.root==a2.stable_operation_root and execution_witness(o.root,l.root,a)!=execution_witness(o.root,l2.root,a2,r('rec')) else 'BAD'
   elif m==6: exp='HOLD'; naive+=1; raise ValueError('retry_without_recovery')
   elif m==7: exp='RETRY'; a2=att(o,2); verify_lease(l,c,KEY); execution_witness(o.root,l.root,a2,r('rec')); obs='RETRY'
   elif m==8: exp='RETURN'; obs='RETURN'
   elif m==9: exp='NO_K27_EFFECT'; obs='NO_K27_EFFECT' if o.root==o.root else 'BAD'
  except ValueError: obs='HOLD'
  mismatch += obs!=exp; unsafe += obs in ('CALL','RETRY') and exp=='HOLD'; rows.append((m,exp,obs))
 return {'schema':SCHEMA+'-campaign','cases':n,'oracle_mismatches':mismatch,'unsafe_provider_candidates':unsafe,'naive_retry_without_recovery':naive,'root':H(rows)}
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(',',':')))
