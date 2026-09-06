from __future__ import annotations
import itertools,json
from dataclasses import replace
from successor_admission_gate import ParentArtifact, AdmissionContext, ARENA_TERMINAL, D0, consequence_root, sha256_obj
from successor_parent_admission_r2 import ImmediateTerminalReceipt, ParentEvidence
from rebase_use_site_admission import ConveyorReceiptRef, ReceiptParentBinding, compile_rebase_after_parent_admission, digest, KEEP
from succession_claim_admission import PersistedSuccessionClaim, admit_persisted_succession_claim, historical_label_only_accepts
CTX=AdmissionContext('GPT-5.6 Sol','ARENA-R1.2','2026-09-06T03:03:18.153Z','2026-09-06T03:12:00.000Z'); H=lambda x:sha256_obj(x)
def evidence(i,label,actor,created):
 lineage=H(('line',label,i));deriv=H(('deriv',label,i));src=H(('src',label,i));p0=ParentArtifact(f'{label}-{i}',actor,lineage,created,ARENA_TERMINAL,True,None,(label,'succession'),f'action-{label}',f'invariant-{label}','0'*64,deriv);c=consequence_root(p0);ir=ImmediateTerminalReceipt(f'receipt-{label}-{i}',p0.artifact_id,actor,lineage,created,ARENA_TERMINAL,True,None,c,deriv,'drive:'+p0.artifact_id,src,(),D0);return ParentEvidence(replace(p0,receipt_root=ir.receipt_root),ir)
def wrap(e):
 p=e.parent;r=ConveyorReceiptRef(p.artifact_id,p.lineage_root,consequence_root(p),H(('conv',p.artifact_id)),KEEP);ir=e.immediate_receipt;return r,ReceiptParentBinding(r.receipt_digest,e,ir.receipt_root,ir.source_owner_ref,ir.source_revision_root)
def base(i,a='AGENT_01',b='AGENT_14'):
 ea=evidence(i,'R12',a,'2026-09-06T03:04:00.000Z');eb=evidence(i,'R8',b,'2026-09-06T03:05:00.000Z');ra,ba=wrap(ea);rb,bb=wrap(eb);rs=[ra,rb];bs={ra.receipt_digest:ba,rb.receipt_digest:bb};g=compile_rebase_after_parent_admission(rs,bs,CTX);c=PersistedSuccessionClaim('R9-'+str(i),CTX.current_actor_id,CTX.predecessor_artifact_id,CTX.predecessor_cut,True,(g.parent_a_receipt or '0'*64,g.parent_b_receipt or '0'*64),(a,b),g.parent_pair_root or '0'*64,g.binding_roots if g.binding_roots else ('0'*64,'0'*64),g.objective_seed or '0'*64);return rs,bs,c
def run(n=12000):
 mismatch=false_accept=false_hold=r9_old=r9_new=0;samples=[]
 for i in range(n):
  k=i%12;rs,bs,c=base(i);exp=True
  if k==1: rs,bs,c=base(i,'GPT-5.6 Sol','GPT-5.6 Sol');c=replace(c,declared_parent_actor_ids=('AGENT_R1.2','AGENT_R8'),parent_pair_root='f'*64,binding_roots=('e'*64,'d'*64),objective_seed='c'*64);exp=False;r9_old+=historical_label_only_accepts(c)
  elif k==2:c=replace(c,declared_parent_actor_ids=('X','Y'));exp=False
  elif k==3:c=replace(c,parent_pair_root='1'*64);exp=False
  elif k==4:c=replace(c,objective_seed='2'*64);exp=False
  elif k==5:c=replace(c,predecessor_cut='2026-09-06T03:00:00.000Z');exp=False
  elif k==6:c=replace(c,effect_authority=True);exp=False
  elif k==7:c=replace(c,gate10=True);exp=False
  elif k==8:rd=rs[0].receipt_digest;bs[rd]=replace(bs[rd],source_owner_ref='drive:detached');exp=False
  elif k==9:rd=rs[1].receipt_digest;bs[rd]=replace(bs[rd],source_revision_root='1'*64);exp=False
  elif k==10:rs,bs,c=base(i,'GPT-5.6 Sol','AGENT_14');exp=False
  elif k==11:c=replace(c,parent_receipts=('3'*64,'4'*64));exp=False
  g=admit_persisted_succession_claim(c,rs,bs,CTX);mismatch+=g.admitted!=exp;false_accept+=g.admitted and not exp;false_hold+=(not g.admitted) and exp
  if k==1:r9_new+=g.admitted
  if i<1000:samples.append(g.claim_root+str(int(g.admitted)))
 hs=0
 for i in range(1000):
  rs,bs,c=base(100000+i,'GPT-5.6 Sol','GPT-5.6 Sol');c=replace(c,declared_parent_actor_ids=('AGENT_FAKE_A','AGENT_FAKE_B'),parent_pair_root=H(('p',i)),binding_roots=(H(('b1',i)),H(('b2',i))),objective_seed=H(('s',i)));hs+=admit_persisted_succession_claim(c,rs,bs,CTX).admitted
 omega=sum(tuple(x)==(2,)*8 for x in itertools.product(range(3),repeat=8));rs,bs,c=base(999999,'GPT-5.6 Sol','GPT-5.6 Sol');tail=sum(admit_persisted_succession_claim(c,rs,bs,CTX).admitted for _ in itertools.product(range(3),repeat=5));out={'cases':n,'mismatches':mismatch,'false_accepts':false_accept,'false_holds':false_hold,'r9_historical_label_accepts':r9_old,'r9_repaired_accepts':r9_new,'hs1000_same_actor_false_accepts':hs,'omega8_keepers':omega,'tail13_repairs':tail,'sample_root':H(samples)};out['campaign_root']=H(out);assert mismatch==false_accept==false_hold==r9_new==hs==tail==0 and r9_old==n//12 and omega==1;return out
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
