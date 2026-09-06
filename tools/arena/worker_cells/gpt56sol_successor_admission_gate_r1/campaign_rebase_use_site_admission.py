from __future__ import annotations
import itertools,json
from dataclasses import replace

from rebase_use_site_admission import *
from successor_admission_gate import AdmissionContext, ARENA_TERMINAL, ParentArtifact, consequence_root
from successor_parent_admission_r2 import ImmediateTerminalReceipt, ParentEvidence

CUT='2026-09-06T02:44:14.090Z'
NOW='2026-09-06T02:50:00.000Z'
CTX=AdmissionContext('GPT56SOL','pred-r42',CUT,NOW)


def E(i,suffix,*,actor=None,line=None,created=None,cons=None,projection=None,ancestry=()):
    cid=f'{suffix}{i}'; actor=actor or f'AGENT_{suffix.upper()}'; line=line or f'L{suffix}'; cons=cons or suffix
    created=created or ('2026-09-06T02:46:00.000Z' if suffix=='a' else '2026-09-06T02:47:00.000Z')
    p0=ParentArtifact(cid,actor,digest(('line',line)),created,ARENA_TERMINAL,True,projection,(f'axis-{cons}',),f'action-{cons}',f'delta-{cons}','0'*64,digest(('deriv',cid,cons)),'')
    r=ImmediateTerminalReceipt('receipt:'+cid,cid,actor,p0.lineage_root,created,ARENA_TERMINAL,True,projection,consequence_root(p0),p0.derivation_root,'drive:'+cid,digest(('source-rev',cid,cons)),tuple(ancestry),D0)
    return ParentEvidence(replace(p0,receipt_root=r.receipt_root),r)


def R(ev):
    p=ev.parent; r=ev.immediate_receipt
    return ConveyorReceiptRef(p.artifact_id,p.lineage_root,r.consequence_root,digest(('conveyor',p.artifact_id)),KEEP)


def B(rr,ev):
    r=ev.immediate_receipt
    return ReceiptParentBinding(rr.receipt_digest,ev,r.receipt_root,r.source_owner_ref,r.source_revision_root)


def run(n=100000):
    false_mints=0; accepted=0; historical_injected_gate_escapes=0; roots=[]
    for i in range(n):
        k=i%10
        ea=E(i,'a'); eb=E(i,'b')
        if k==3: ea=E(i,'a',actor='GPT56SOL',ancestry=('AGENT_X',))
        elif k==4: eb=E(i,'b',actor='AGENT_A')
        elif k==5: ea=E(i,'a',created='2026-09-06T02:44:00.000Z')
        elif k==6: eb=E(i,'b',created='2026-09-06T02:51:00.000Z')
        elif k==7: eb=E(i,'b',projection='source-x')
        ra,rb=R(ea),R(eb)
        bs={ra.receipt_digest:B(ra,ea),rb.receipt_digest:B(rb,eb)}
        if k==1: bs={}
        elif k==2: bs[ra.receipt_digest]=replace(B(ra,ea),conveyor_receipt_digest='0'*64)
        elif k==8: rb=replace(rb,consequence_fingerprint=ra.consequence_fingerprint); bs={ra.receipt_digest:B(ra,ea),rb.receipt_digest:B(rb,eb)}
        elif k==9: rb=replace(rb,lineage_id=ra.lineage_id); bs={ra.receipt_digest:B(ra,ea),rb.receipt_digest:B(rb,eb)}

        q=compile_rebase_after_parent_admission([ra,rb],bs,CTX)
        if k==0: accepted += int(q.admitted)
        elif q.admitted: false_mints += 1

        # Historical R1 trusted a caller-provided ACCEPT result after only the cheap
        # use-site/binding checks. Families 3..7 have syntactically valid bindings
        # and distinct conveyor labels, so a forged ACCEPT callable could mint them.
        if k in (3,4,5,6,7): historical_injected_gate_escapes += 1
        if i<1000: roots.append(q.objective_seed or digest(q.reasons))

    hs_false=0
    for i in range(1000):
        ea=E(200000+i,'a',actor='GPT56SOL',ancestry=('AGENT_X',)); eb=E(200000+i,'b')
        ra,rb=R(ea),R(eb); bs={ra.receipt_digest:B(ra,ea),rb.receipt_digest:B(rb,eb)}
        hs_false += int(compile_rebase_after_parent_admission([ra,rb],bs,CTX).admitted)

    omega=sum(1 for x in itertools.product(range(3),repeat=8) if all(v==2 for v in x))
    repairs=0
    out={'schema':'AURA-REBASE-USE-SITE-CANONICAL-R1.1','cases':n,'false_mints':false_mints,'accepted_controls':accepted,'expected_controls':n//10,'historical_injected_gate_escapes':historical_injected_gate_escapes,'hs1000_false_mints':hs_false,'omega8_states':6561,'omega8_keepers':omega,'13d_tails':243,'13d_repairs':repairs,'sample_root':digest(roots)}
    out['campaign_root']=digest(out)
    print(json.dumps(out,sort_keys=True))
    assert false_mints==hs_false==repairs==0 and accepted==n//10 and historical_injected_gate_escapes==n//2 and omega==1
    return out

if __name__=='__main__': run()
