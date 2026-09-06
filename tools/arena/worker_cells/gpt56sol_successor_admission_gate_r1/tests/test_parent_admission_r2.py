import unittest
from dataclasses import replace

from successor_admission_gate import AdmissionContext, ARENA_TERMINAL, ParentArtifact, consequence_root, sha256_obj
from successor_parent_admission_r2 import (
    ImmediateTerminalReceipt, ParentEvidence, SuccessionDisposition,
    admit_successor_pair, independent_r2_oracle,
)

CUT='2026-09-06T00:16:36.186Z'
NOW='2026-09-06T02:00:00.000Z'
CTX=AdmissionContext('GPT56SOL','O1',CUT,NOW)

def h(x): return sha256_obj(x)

def evidence(tag, actor, lineage=None, created='2026-09-06T01:00:00.000Z', axes=None, action=None, inv=None, ancestry=(), terminal=True, projection=None, source=True):
    lineage=lineage or h(('lin',actor))
    p0=ParentArtifact(
        artifact_id='ART-'+tag, actor_id=actor, lineage_root=lineage, created_at=created,
        artifact_class=ARENA_TERMINAL, semantic_terminal=terminal, projection_of=projection,
        consequence_axes=tuple(axes or ('identity',tag)), consequence_action=action or ('advance-'+tag), invariant_delta=inv or ('delta-'+tag),
        receipt_root='0'*64, derivation_root=h(('der',tag)), model_id=actor,
    )
    r=ImmediateTerminalReceipt(
        receipt_id='REC-'+tag, artifact_id=p0.artifact_id, actor_id=p0.actor_id, lineage_root=p0.lineage_root,
        created_at=p0.created_at, artifact_class=p0.artifact_class, semantic_terminal=p0.semantic_terminal, projection_of=p0.projection_of,
        consequence_root=consequence_root(p0), derivation_root=p0.derivation_root,
        source_owner_ref=('Drive:'+tag if source else ''), source_revision_root=(h(('rev',tag)) if source else ''),
        ancestry_actor_ids=tuple(ancestry),
    )
    p=replace(p0,receipt_root=r.receipt_root)
    return ParentEvidence(p,r)

class R2Tests(unittest.TestCase):
    def pair(self): return [evidence('A','AGENT_01'), evidence('B','AGENT_14')]
    def assertBoth(self, ev, expected):
        self.assertEqual(admit_successor_pair(ev,CTX).disposition, expected)
        self.assertEqual(independent_r2_oracle(ev,CTX), expected)
    def test_01_valid_foreign_pair(self): self.assertBoth(self.pair(), SuccessionDisposition.FOREIGN_PARENT_PAIR_ACCEPTED)
    def test_02_missing_receipt(self):
        a,b=self.pair(); self.assertBoth([replace(a,immediate_receipt=None),b],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD)
    def test_03_actor_field_forgery(self):
        a,b=self.pair(); a=replace(a,parent=replace(a.parent,actor_id='AGENT_08'))
        self.assertBoth([a,b],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD)
    def test_04_lineage_field_forgery(self):
        a,b=self.pair(); a=replace(a,parent=replace(a.parent,lineage_root=h('forged')))
        self.assertBoth([a,b],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD)
    def test_05_receipt_root_forgery(self):
        a,b=self.pair(); a=replace(a,parent=replace(a.parent,receipt_root='f'*64))
        self.assertBoth([a,b],SuccessionDisposition.TERMINAL_RECEIPT_INTEGRITY_HOLD)
    def test_06_foreign_ancestry_same_immediate_actor(self):
        a=evidence('A','GPT56SOL',ancestry=('AGENT_01','AGENT_14')); b=evidence('B','AGENT_08')
        self.assertBoth([a,b],SuccessionDisposition.FOREIGN_ANCESTRY_ONLY_HOLD)
    def test_07_two_same_lineage_foreign(self):
        lin=h('same'); self.assertBoth([evidence('A','AGENT_01',lin),evidence('B','AGENT_14',lin)],SuccessionDisposition.SAME_LINEAGE_PAIR_HOLD)
    def test_08_same_actor(self): self.assertBoth([evidence('A','AGENT_01'),evidence('B','AGENT_01')],SuccessionDisposition.SAME_LINEAGE_PAIR_HOLD)
    def test_09_consequence_duplicate(self):
        a=evidence('A','AGENT_01',axes=('x',),action='same',inv='same'); b=evidence('B','AGENT_14',axes=('x',),action='same',inv='same')
        self.assertBoth([a,b],SuccessionDisposition.CONSEQUENCE_DUPLICATE_HOLD)
    def test_10_pre_cut(self): self.assertBoth([evidence('A','AGENT_01',created='2026-09-06T00:00:00.000Z'),evidence('B','AGENT_14')],SuccessionDisposition.TEMPORAL_CURRENTNESS_HOLD)
    def test_11_future(self): self.assertBoth([evidence('A','AGENT_01',created='2026-09-06T03:00:00.000Z'),evidence('B','AGENT_14')],SuccessionDisposition.TEMPORAL_CURRENTNESS_HOLD)
    def test_12_nonterminal(self): self.assertBoth([evidence('A','AGENT_01',terminal=False),evidence('B','AGENT_14')],SuccessionDisposition.TERMINAL_CLASS_HOLD)
    def test_13_projection(self): self.assertBoth([evidence('A','AGENT_01',projection='SRC'),evidence('B','AGENT_14')],SuccessionDisposition.PROJECTION_HOLD)
    def test_14_source_owner_missing(self): self.assertBoth([evidence('A','AGENT_01',source=False),evidence('B','AGENT_14')],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD)
    def test_15_receipt_actor_forgery(self):
        a,b=self.pair(); r=replace(a.immediate_receipt,actor_id='AGENT_08'); a=replace(a,immediate_receipt=r)
        self.assertBoth([a,b],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD)
    def test_16_receipt_consequence_forgery(self):
        a,b=self.pair(); r=replace(a.immediate_receipt,consequence_root='e'*64); a=replace(a,immediate_receipt=r)
        self.assertBoth([a,b],SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD)
    def test_17_receipt_authority_widening(self):
        a,b=self.pair(); r=replace(a.immediate_receipt,authority_ceiling='D1'); a=replace(a,immediate_receipt=r)
        self.assertBoth([a,b],SuccessionDisposition.AUTHORITY_HOLD)
    def test_18_exactly_two(self): self.assertBoth([self.pair()[0]],SuccessionDisposition.EXACTLY_TWO_PARENTS_HOLD)
    def test_19_ancestry_does_not_change_valid_foreignness(self):
        a=evidence('A','AGENT_01',ancestry=('GPT56SOL','AGENT_08')); b=evidence('B','AGENT_14',ancestry=('GPT56SOL',))
        self.assertBoth([a,b],SuccessionDisposition.FOREIGN_PARENT_PAIR_ACCEPTED)
    def test_20_receipt_root_binds_ancestry(self):
        a,b=self.pair(); r=replace(a.immediate_receipt,ancestry_actor_ids=('AGENT_08',)); self.assertNotEqual(r.receipt_root,a.immediate_receipt.receipt_root)

if __name__=='__main__': unittest.main()
