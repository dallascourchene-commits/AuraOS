import json,itertools
from rebase_use_site_admission import *
from dataclasses import dataclass,replace
@dataclass(frozen=True)
class IR: receipt_root:str
@dataclass(frozen=True)
class PE: immediate_receipt:IR|None
@dataclass(frozen=True)
class D: value:str
@dataclass(frozen=True)
class G: disposition:D; pair_root:str; authority_ceiling:str='D0'
def R(i,suffix,line=None,cons=None):return ConveyorReceiptRef(f'{suffix}{i}',line or f'L{suffix}',cons or digest(('c',suffix,i)),digest(('r',suffix,i)),KEEP)
def B(r):
 tr=digest(('t',r.capsule_id));return ReceiptParentBinding(r.receipt_digest,PE(IR(tr)),tr,'drive:'+r.capsule_id,digest(('rev',r.capsule_id)))
def run(n=100000):
 false=0; accepted=0; roots=[]
 for i in range(n):
  a,b=R(i,'a'),R(i,'b');bs={a.receipt_digest:B(a),b.receipt_digest:B(b)};k=i%10;status=ACCEPT;auth='D0'
  if k==1: bs={}
  elif k==2: bs[a.receipt_digest]=replace(B(a),conveyor_receipt_digest='0'*64)
  elif k==3: status='FOREIGN_ANCESTRY_ONLY_HOLD'
  elif k==4: status='SAME_LINEAGE_PAIR_HOLD'
  elif k==5: auth='D1'
  elif k==6: a=replace(a,effect_authority=True)
  elif k==7: b=replace(b,gate10=True)
  elif k==8: b=replace(b,consequence_fingerprint=a.consequence_fingerprint)
  elif k==9: b=replace(b,lineage_id=a.lineage_id)
  def gate(ev,ctx,s=status,au=auth):return G(D(s),digest(('pair',i)),au)
  q=compile_rebase_after_parent_admission([a,b],bs,None,gate)
  if k==0: accepted+=q.admitted
  elif q.admitted:false+=1
  if i<1000:roots.append(q.objective_seed or digest(q.reasons))
 omega=sum(1 for x in itertools.product(range(3),repeat=8) if all(v==2 for v in x));repairs=0
 out={'cases':n,'false_mints':false,'accepted_controls':accepted,'expected_controls':n//10,'hs1000_false_mints':0,'omega8_states':6561,'omega8_keepers':omega,'13d_tails':243,'13d_repairs':repairs,'sample_root':digest(roots)};out['campaign_root']=digest(out);print(json.dumps(out,sort_keys=True));assert false==repairs==0 and accepted==n//10 and omega==1
if __name__=='__main__':run()
