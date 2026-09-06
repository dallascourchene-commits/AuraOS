import inspect
import unittest
from dataclasses import replace

from rebase_use_site_admission import *
from successor_admission_gate import AdmissionContext, ARENA_TERMINAL, ParentArtifact, consequence_root
from successor_parent_admission_r2 import ImmediateTerminalReceipt, ParentEvidence

CUT='2026-09-06T02:44:14.090Z'
NOW='2026-09-06T02:50:00.000Z'
CTX=AdmissionContext('GPT56SOL','pred-r42',CUT,NOW)


def E(cid,actor,line,created='2026-09-06T02:46:00.000Z',cons='x',projection=None,ancestry=()):
    p0=ParentArtifact(
        cid,actor,digest(('line',line)),created,ARENA_TERMINAL,True,projection,
        (f'axis-{cons}',),f'action-{cons}',f'delta-{cons}','0'*64,digest(('deriv',cid,cons)),''
    )
    r=ImmediateTerminalReceipt(
        'receipt:'+cid,cid,actor,p0.lineage_root,created,ARENA_TERMINAL,True,projection,
        consequence_root(p0),p0.derivation_root,'drive:'+cid,digest(('source-rev',cid,cons)),tuple(ancestry),D0
    )
    return ParentEvidence(replace(p0,receipt_root=r.receipt_root),r)


def R(ev):
    p=ev.parent; r=ev.immediate_receipt
    return ConveyorReceiptRef(p.artifact_id,p.lineage_root,r.consequence_root,digest(('conveyor',p.artifact_id)),KEEP)


def B(rr,ev):
    r=ev.immediate_receipt
    return ReceiptParentBinding(rr.receipt_digest,ev,r.receipt_root,r.source_owner_ref,r.source_revision_root)


def pair(a=None,b=None):
    ea=a or E('a','AGENT_A','L1',cons='c1')
    eb=b or E('b','AGENT_B','L2',created='2026-09-06T02:47:00.000Z',cons='c2')
    ra,rb=R(ea),R(eb)
    return ea,eb,ra,rb,{ra.receipt_digest:B(ra,ea),rb.receipt_digest:B(rb,eb)}


class Tests(unittest.TestCase):
    def test_valid_pair_mints_seed_through_canonical_r2(self):
        ea,eb,a,b,bs=pair()
        q=compile_rebase_after_parent_admission([a,b],bs,CTX)
        self.assertTrue(q.admitted)
        self.assertTrue(hex64(q.objective_seed))
        self.assertEqual(q.disposition,ACCEPT)
        self.assertFalse(q.effect_authority)

    def test_no_gate_injection_parameter_exists(self):
        self.assertEqual(tuple(inspect.signature(compile_rebase_after_parent_admission).parameters),('receipts','bindings','ctx'))
        _,_,a,b,bs=pair()
        with self.assertRaises(TypeError):
            compile_rebase_after_parent_admission([a,b],bs,CTX,lambda *_: object())

    def test_old_distinct_labels_not_enough_without_bindings(self):
        _,_,a,b,_=pair()
        q=compile_rebase_after_parent_admission([a,b],{},CTX)
        self.assertFalse(q.admitted)

    def test_same_lineage_withheld_before_gate(self):
        eb=E('b','AGENT_B','L2',cons='c2')
        ea=E('a','AGENT_A','L1',cons='c1')
        ra,rb=R(ea),R(eb)
        rb=replace(rb,lineage_id=ra.lineage_id)
        q=compile_rebase_after_parent_admission([ra,rb],{ra.receipt_digest:B(ra,ea),rb.receipt_digest:B(rb,eb)},CTX)
        self.assertFalse(q.admitted)

    def test_same_consequence_withheld(self):
        ea,eb,a,b,bs=pair()
        b=replace(b,consequence_fingerprint=a.consequence_fingerprint)
        q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:B(a,ea),b.receipt_digest:B(b,eb)},CTX)
        self.assertFalse(q.admitted)

    def test_same_actor_rejected_by_canonical_gate(self):
        ea=E('a','AGENT_A','L1',cons='c1')
        eb=E('b','AGENT_A','L2',created='2026-09-06T02:47:00.000Z',cons='c2')
        _,_,a,b,bs=pair(ea,eb)
        q=compile_rebase_after_parent_admission([a,b],bs,CTX)
        self.assertFalse(q.admitted)

    def test_current_actor_rejected_by_canonical_gate(self):
        ea=E('a','GPT56SOL','L1',cons='c1')
        _,_,a,b,bs=pair(ea,None)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_pre_cut_parent_rejected(self):
        ea=E('a','AGENT_A','L1',created='2026-09-06T02:44:00.000Z',cons='c1')
        _,_,a,b,bs=pair(ea,None)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_future_parent_rejected(self):
        eb=E('b','AGENT_B','L2',created='2026-09-06T02:51:00.000Z',cons='c2')
        _,_,a,b,bs=pair(None,eb)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_projection_parent_rejected(self):
        eb=E('b','AGENT_B','L2',created='2026-09-06T02:47:00.000Z',cons='c2',projection='source-x')
        _,_,a,b,bs=pair(None,eb)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_foreign_ancestry_on_same_actor_does_not_launder(self):
        ea=E('a','GPT56SOL','L1',cons='c1',ancestry=('AGENT_A',))
        _,_,a,b,bs=pair(ea,None)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_binding_receipt_mismatch_blocks(self):
        ea,eb,a,b,bs=pair()
        bs[a.receipt_digest]=replace(bs[a.receipt_digest],conveyor_receipt_digest='0'*64)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_terminal_receipt_mismatch_blocks(self):
        ea,eb,a,b,bs=pair()
        bs[a.receipt_digest]=replace(bs[a.receipt_digest],terminal_receipt_root='0'*64)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_missing_immediate_receipt_blocks(self):
        ea,eb,a,b,bs=pair()
        bs[a.receipt_digest]=replace(bs[a.receipt_digest],parent_evidence=ParentEvidence(ea.parent,None))
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_source_owner_binding_mismatch_blocks(self):
        ea,eb,a,b,bs=pair()
        bs[a.receipt_digest]=replace(bs[a.receipt_digest],source_owner_ref='drive:detached-owner')
        q=compile_rebase_after_parent_admission([a,b],bs,CTX)
        self.assertFalse(q.admitted)
        self.assertIn('A_SOURCE_OWNER_BINDING_MISMATCH',q.reasons)

    def test_source_revision_binding_mismatch_blocks(self):
        ea,eb,a,b,bs=pair()
        bs[a.receipt_digest]=replace(bs[a.receipt_digest],source_revision_root='f'*64)
        q=compile_rebase_after_parent_admission([a,b],bs,CTX)
        self.assertFalse(q.admitted)
        self.assertIn('A_SOURCE_REVISION_BINDING_MISMATCH',q.reasons)

    def test_effect_bearing_receipt_excluded(self):
        _,_,a,b,bs=pair(); a=replace(a,effect_authority=True)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_gate10_receipt_excluded(self):
        _,_,a,b,bs=pair(); b=replace(b,gate10=True)
        self.assertFalse(compile_rebase_after_parent_admission([a,b],bs,CTX).admitted)

    def test_deterministic_order(self):
        _,_,a,b,bs=pair()
        q1=compile_rebase_after_parent_admission([a,b],bs,CTX)
        q2=compile_rebase_after_parent_admission([b,a],bs,CTX)
        self.assertEqual(q1.objective_seed,q2.objective_seed)
        self.assertEqual(q1.parent_pair_root,q2.parent_pair_root)

if __name__=='__main__': unittest.main()
