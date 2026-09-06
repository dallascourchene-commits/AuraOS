from __future__ import annotations
import itertools,json,random
from dataclasses import replace
from successor_admission_gate import AdmissionContext,ARENA_TERMINAL,ParentArtifact,consequence_root,sha256_obj
from successor_parent_admission_r2 import *

CUT='2026-09-06T00:16:36.186Z'; NOW='2026-09-06T02:00:00.000Z'; CTX=AdmissionContext('GPT56SOL','O1',CUT,NOW)
def h(x): return sha256_obj(x)
def ev(i,actor,tag='A',created='2026-09-06T01:00:00.000Z',same_cons=None,ancestry=()):
    p0=ParentArtifact(f'ART-{tag}-{i}',actor,h(('lin',actor,i)),created,ARENA_TERMINAL,True,None,(tag,str(i)),('advance-'+tag if same_cons is None else 'same'),('delta-'+tag if same_cons is None else 'same'),'0'*64,h(('der',tag,i)),actor)
    if same_cons is not None: p0=replace(p0,consequence_axes=('same',))
    r=ImmediateTerminalReceipt(f'REC-{tag}-{i}',p0.artifact_id,p0.actor_id,p0.lineage_root,p0.created_at,p0.artifact_class,p0.semantic_terminal,p0.projection_of,consequence_root(p0),p0.derivation_root,'Drive:'+tag,h(('rev',tag,i)),tuple(ancestry))
    return ParentEvidence(replace(p0,receipt_root=r.receipt_root),r)
def case(i,k):
    a=ev(i,'AGENT_01','A'); b=ev(i,'AGENT_14','B')
    if k==0:return [a,b],SuccessionDisposition.FOREIGN_PARENT_PAIR_ACCEPTED
    if k==1:return [replace(a,immediate_receipt=None),b],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
    if k==2:return [replace(a,parent=replace(a.parent,actor_id='AGENT_08')),b],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
    if k==3:return [replace(a,parent=replace(a.parent,receipt_root='f'*64)),b],SuccessionDisposition.TERMINAL_RECEIPT_INTEGRITY_HOLD
    if k==4:return [ev(i,'GPT56SOL','A',ancestry=('AGENT_01','AGENT_14')),b],SuccessionDisposition.FOREIGN_ANCESTRY_ONLY_HOLD
    if k==5:
        lin=h(('same',i)); return [replace(a,parent=replace(a.parent,lineage_root=lin),immediate_receipt=replace(a.immediate_receipt,lineage_root=lin)),replace(b,parent=replace(b.parent,lineage_root=lin),immediate_receipt=replace(b.immediate_receipt,lineage_root=lin))],SuccessionDisposition.TERMINAL_RECEIPT_INTEGRITY_HOLD
    if k==6:return [ev(i,'AGENT_01','A',same_cons=1),ev(i,'AGENT_14','B',same_cons=1)],SuccessionDisposition.CONSEQUENCE_DUPLICATE_HOLD
    if k==7:return [ev(i,'AGENT_01','A',created='2026-09-06T00:00:00.000Z'),b],SuccessionDisposition.TEMPORAL_CURRENTNESS_HOLD
    if k==8:
        r=replace(a.immediate_receipt,source_owner_ref='',source_revision_root=''); return [replace(a,immediate_receipt=r),b],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
    if k==9:
        r=replace(a.immediate_receipt,authority_ceiling='D1'); return [replace(a,immediate_receipt=r),b],SuccessionDisposition.AUTHORITY_HOLD
    raise ValueError(k)

def run(n=100000):
    mismatch=false_accept=0
    roots=[]
    counts={x.value:0 for x in SuccessionDisposition}
    for i in range(n):
        es,expected=case(i,i%10); got=admit_successor_pair(es,CTX); oracle=independent_r2_oracle(es,CTX)
        counts[got.disposition.value]+=1
        if got.disposition!=expected or oracle!=expected: mismatch+=1
        if i%10!=0 and got.disposition is SuccessionDisposition.FOREIGN_PARENT_PAIR_ACCEPTED: false_accept+=1
        if i<1000: roots.append(got.pair_root)
    hs_false=0
    for i in range(1000):
        k=1+(i%9); es,_=case(i,k)
        if admit_successor_pair(es,CTX).disposition is SuccessionDisposition.FOREIGN_PARENT_PAIR_ACCEPTED: hs_false+=1
    omega=sum(1 for x in itertools.product((0,1,2),repeat=8) if all(v==2 for v in x))
    repairs=sum(1 for tail in itertools.product((0,1,2),repeat=5) if all(v==2 for v in (2,2,2,2,2,2,2,1)))
    out={'cases':n,'mismatches':mismatch,'false_accepts':false_accept,'hs1000_false_accepts':hs_false,'omega8_states':6561,'omega8_keepers':omega,'13d_tails':243,'13d_repairs':repairs,'sample_root':h(roots),'counts':counts}
    out['campaign_root']=h(out)
    print(json.dumps(out,sort_keys=True))
    assert mismatch==false_accept==hs_false==repairs==0 and omega==1
if __name__=='__main__':run()
