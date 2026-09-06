import unittest
from dataclasses import replace
from successor_admission_gate import ParentArtifact, AdmissionContext, ARENA_TERMINAL, D0, consequence_root, sha256_obj
from successor_parent_admission_r2 import ImmediateTerminalReceipt, ParentEvidence
from rebase_use_site_admission import ConveyorReceiptRef, ReceiptParentBinding, compile_rebase_after_parent_admission, digest, KEEP
from succession_claim_admission import PersistedSuccessionClaim, admit_persisted_succession_claim, historical_label_only_accepts

CTX=AdmissionContext('GPT-5.6 Sol','ARENA-R1.2','2026-09-06T03:03:18.153Z','2026-09-06T03:12:00.000Z')
H=lambda x: sha256_obj(x)

def evidence(label,actor,created):
    lineage=H(('lineage',label)); deriv=H(('derivation',label)); source_revision=H(('source',label))
    p0=ParentArtifact(label,actor,lineage,created,ARENA_TERMINAL,True,None,(label,'succession'),f'action-{label}',f'invariant-{label}','0'*64,deriv)
    cons=consequence_root(p0)
    ir=ImmediateTerminalReceipt('receipt-'+label,label,actor,lineage,created,ARENA_TERMINAL,True,None,cons,deriv,'drive:'+label,source_revision,(),D0)
    p=replace(p0,receipt_root=ir.receipt_root)
    return ParentEvidence(p,ir)

def wrap(ev):
    p=ev.parent; r=ConveyorReceiptRef(p.artifact_id,p.lineage_root,consequence_root(p),H(('conveyor',p.artifact_id)),KEEP)
    ir=ev.immediate_receipt
    return r,ReceiptParentBinding(r.receipt_digest,ev,ir.receipt_root,ir.source_owner_ref,ir.source_revision_root)

def material(actor_a='AGENT_01',actor_b='AGENT_14'):
    ea=evidence('R1.2',actor_a,'2026-09-06T03:04:00.000Z'); eb=evidence('R8',actor_b,'2026-09-06T03:05:00.000Z')
    ra,ba=wrap(ea); rb,bb=wrap(eb); receipts=[ra,rb]; bindings={ra.receipt_digest:ba,rb.receipt_digest:bb}
    canon=compile_rebase_after_parent_admission(receipts,bindings,CTX)
    claim=PersistedSuccessionClaim('R9','GPT-5.6 Sol',CTX.predecessor_artifact_id,CTX.predecessor_cut,True,(canon.parent_a_receipt or '0'*64,canon.parent_b_receipt or '0'*64),(actor_a,actor_b),canon.parent_pair_root or '0'*64,canon.binding_roots if canon.binding_roots else ('0'*64,'0'*64),canon.objective_seed or '0'*64)
    return receipts,bindings,claim,canon

class Tests(unittest.TestCase):
    def test_valid_foreign_pair_claim(self):
        receipts,bindings,claim,canon=material(); self.assertTrue(canon.admitted); self.assertTrue(admit_persisted_succession_claim(claim,receipts,bindings,CTX).admitted)
    def test_r9_same_actor_narrative_laundering_is_rejected(self):
        receipts,bindings,claim,_=material('GPT-5.6 Sol','GPT-5.6 Sol')
        forged=replace(claim,declared_parent_actor_ids=('AGENT_R1.2','AGENT_R8'),parent_pair_root='f'*64,binding_roots=('e'*64,'d'*64),objective_seed='c'*64)
        self.assertTrue(historical_label_only_accepts(forged)); self.assertFalse(admit_persisted_succession_claim(forged,receipts,bindings,CTX).admitted)
    def test_one_self_parent_holds(self):
        receipts,bindings,claim,_=material('GPT-5.6 Sol','AGENT_14'); self.assertFalse(admit_persisted_succession_claim(claim,receipts,bindings,CTX).admitted)
    def test_same_foreign_actor_holds(self):
        receipts,bindings,claim,_=material('AGENT_01','AGENT_01'); self.assertFalse(admit_persisted_succession_claim(claim,receipts,bindings,CTX).admitted)
    def test_declared_actor_substitution_holds(self):
        receipts,bindings,claim,_=material(); self.assertFalse(admit_persisted_succession_claim(replace(claim,declared_parent_actor_ids=('A','B')),receipts,bindings,CTX).admitted)
    def test_pair_root_substitution_holds(self):
        receipts,bindings,claim,_=material(); self.assertFalse(admit_persisted_succession_claim(replace(claim,parent_pair_root='1'*64),receipts,bindings,CTX).admitted)
    def test_binding_root_substitution_holds(self):
        receipts,bindings,claim,_=material(); self.assertFalse(admit_persisted_succession_claim(replace(claim,binding_roots=('1'*64,'2'*64)),receipts,bindings,CTX).admitted)
    def test_seed_substitution_holds(self):
        receipts,bindings,claim,_=material(); self.assertFalse(admit_persisted_succession_claim(replace(claim,objective_seed='1'*64),receipts,bindings,CTX).admitted)
    def test_predecessor_cut_substitution_holds(self):
        receipts,bindings,claim,_=material(); self.assertFalse(admit_persisted_succession_claim(replace(claim,predecessor_cut='2026-09-06T03:00:00.000Z'),receipts,bindings,CTX).admitted)
    def test_source_owner_detachment_holds(self):
        receipts,bindings,claim,_=material(); rd=receipts[0].receipt_digest; bindings[rd]=replace(bindings[rd],source_owner_ref='drive:detached'); self.assertFalse(admit_persisted_succession_claim(claim,receipts,bindings,CTX).admitted)
    def test_source_revision_detachment_holds(self):
        receipts,bindings,claim,_=material(); rd=receipts[1].receipt_digest; bindings[rd]=replace(bindings[rd],source_revision_root='1'*64); self.assertFalse(admit_persisted_succession_claim(claim,receipts,bindings,CTX).admitted)
    def test_authority_widening_holds(self):
        receipts,bindings,claim,_=material(); self.assertFalse(admit_persisted_succession_claim(replace(claim,effect_authority=True),receipts,bindings,CTX).admitted)

if __name__=='__main__': unittest.main()
