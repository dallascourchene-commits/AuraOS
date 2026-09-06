import hashlib, unittest, itertools
from dataclasses import replace
from atomic_absorption import Proposal, OwnerSnapshot, Disposition, plan, commit, omega8_keeper, context13_preserves_invalid

H=hashlib.sha256(b'AuraOS-main:7a2c7a16f845752ffb7c16c68636d8d542ecd72e').hexdigest()
T=hashlib.sha256(b'ResearchTestSpec-owner-tree-v0').hexdigest()
C='24bff04a0eb14449f4fd03f796516f602b959e3eeca5b5d666295a8378692b25'
R='30b7aeb9b5f520f7532631603f30e3660052492e59f5847aa89579c993bb63be'
LINEAGE=hashlib.sha256(b'GPT56SOL-HS1000-TestSpec-Bridge').hexdigest()
FILES={
 'tools/arena/research_testspec/hs1000_testspec_bridge.py':'722042d9963f51e4bf44d8ceb3cfc50ad7093edb1a35898d8a1867a5fb8b28ab',
 'tools/arena/research_testspec/test_hs1000_testspec_bridge.py':'2f8cc918ad7874960310efe97497686fe60240c4eeb46b3236b6447cd4595525',
 'tools/arena/research_testspec/hs1000_testspec_campaign.py':'83e2939cc01a982dc5dd3ffbbfa9e37d614d0f1efc5874a02eeded2971d96b13',
 'tools/arena/research_testspec/HS1000_TOP27_TESTSPECS.jsonl':'af5e8517aef5161c5c28938f502d9c8b06faf95720f64068e2cd9a6aed883153',
 'tools/arena/research_testspec/HS1000_TESTSPEC_BRIDGE.md':'4e2debe910a6f9a2fd4e41939908a8f656bb3c202aba2665ec090e27ad4f7f30',
}

def prop(pid='bridge', consequence=C, receipt=R, files=None, actor='GPT56SOL', lineage=LINEAGE, base=H, auth=False):
    return Proposal(pid, actor, lineage, base, consequence, receipt, dict(FILES if files is None else files), auth)

class AtomicAbsorptionR2Tests(unittest.TestCase):
    def setUp(self): self.snap=OwnerSnapshot(H,T)
    def test_01_real_bridge_fixture_ready(self):
        x=plan(self.snap,[prop()]); self.assertEqual(x.disposition,Disposition.READY); self.assertEqual(len(x.writes),5)
    def test_02_exact_redelivery_collapses_without_losing_writes(self):
        x=plan(self.snap,[prop('A'),prop('B',actor='relay',lineage=hashlib.sha256(b'relay').hexdigest())]); self.assertEqual(x.disposition,Disposition.READY); self.assertEqual(len(x.writes),5); self.assertEqual(x.collapsed_proposals,('B',))
    def test_03_same_consequence_different_receipt_holds(self): self.assertEqual(plan(self.snap,[prop('A'),prop('B',receipt='e'*64)]).disposition,Disposition.CONFLICT_HOLD)
    def test_04_same_consequence_different_blob_holds(self):
        f=dict(FILES); f[next(iter(f))]='f'*64; self.assertEqual(plan(self.snap,[prop('A'),prop('B',files=f)]).disposition,Disposition.CONFLICT_HOLD)
    def test_05_same_consequence_extra_file_holds(self):
        f=dict(FILES); f['tools/arena/research_testspec/EXTRA.md']='a'*64; self.assertEqual(plan(self.snap,[prop('A'),prop('B',files=f)]).disposition,Disposition.CONFLICT_HOLD)
    def test_06_duplicate_proposal_id_holds(self): self.assertEqual(plan(self.snap,[prop('X'),prop('X',consequence='a'*64,receipt='b'*64)]).disposition,Disposition.CONFLICT_HOLD)
    def test_07_distinct_consequence_path_conflict_holds(self):
        f={'owner.py':'1'*64}; g={'owner.py':'2'*64}; self.assertEqual(plan(self.snap,[prop('A',consequence='a'*64,receipt='b'*64,files=f),prop('B',consequence='c'*64,receipt='d'*64,files=g)]).disposition,Disposition.CONFLICT_HOLD)
    def test_08_distinct_consequence_disjoint_writes_ready(self): self.assertEqual(plan(self.snap,[prop('A',consequence='a'*64,receipt='b'*64,files={'a.py':'1'*64}),prop('B',consequence='c'*64,receipt='d'*64,files={'b.py':'2'*64})]).disposition,Disposition.READY)
    def test_09_stale_base_rebase(self): self.assertEqual(plan(self.snap,[prop(base='0'*64)]).disposition,Disposition.REBASE_REQUIRED)
    def test_10_debris_holds(self): self.assertEqual(plan(self.snap,[prop(files={'x.tmp':'1'*64})]).disposition,Disposition.DEBRIS_HOLD)
    def test_11_authority_holds(self): self.assertEqual(plan(self.snap,[prop(auth=True)]).disposition,Disposition.AUTHORITY_HOLD)
    def test_12_cas_head_move_zero_writes(self):
        ps=[prop()]; p=plan(self.snap,ps); r=commit(p,'9'*64,snapshot=self.snap,proposals=ps); self.assertFalse(r.committed); self.assertEqual(r.write_count,0)
    def test_13_exact_commit_receipt(self):
        ps=[prop()]; p=plan(self.snap,ps); r=commit(p,H,snapshot=self.snap,proposals=ps); self.assertTrue(r.committed); self.assertEqual(r.write_count,5)
    def test_14_actor_provenance_changes_manifest(self): self.assertNotEqual(plan(self.snap,[prop(actor='actor-A')]).manifest_root,plan(self.snap,[prop(actor='actor-B')]).manifest_root)
    def test_15_lineage_provenance_changes_manifest(self): self.assertNotEqual(plan(self.snap,[prop(lineage='1'*64)]).manifest_root,plan(self.snap,[prop(lineage='2'*64)]).manifest_root)
    def test_16_collapsed_actor_is_bound(self): self.assertNotEqual(plan(self.snap,[prop('A'),prop('B',actor='relay1',lineage='1'*64)]).manifest_root,plan(self.snap,[prop('A'),prop('B',actor='relay2',lineage='1'*64)]).manifest_root)
    def test_17_omega8_exactly_one_keeper(self): self.assertEqual(sum(omega8_keeper(x) for x in itertools.product(range(3), repeat=8)),1)
    def test_18_13d_tail_cannot_repair_invalid(self): self.assertFalse(any(context13_preserves_invalid((2,2,2,2,2,2,1,1),t) for t in itertools.product(range(3), repeat=5)))
    def test_19_same_consequence_different_paths_regression(self):
        a=prop('A',files={'owner/tests.py':'1'*64}); b=prop('B',receipt='e'*64,files={'owner/bridge.py':'2'*64}); self.assertEqual(plan(self.snap,[a,b]).disposition,Disposition.CONFLICT_HOLD)
    def test_20_public_ready_plan_without_authoritative_inputs_cannot_commit(self):
        p=plan(self.snap,[prop()]); self.assertFalse(commit(p,H).committed)
    def test_21_forged_writes_cannot_commit(self):
        ps=[prop()]; p=plan(self.snap,ps); forged=replace(p,writes=(('evil.py','f'*64),)); self.assertFalse(commit(forged,H,snapshot=self.snap,proposals=ps).committed)
    def test_22_forged_manifest_cannot_commit(self):
        ps=[prop()]; p=plan(self.snap,ps); forged=replace(p,manifest_root='f'*64); self.assertFalse(commit(forged,H,snapshot=self.snap,proposals=ps).committed)
    def test_23_authority_widened_ready_plan_cannot_commit(self):
        ps=[prop()]; p=plan(self.snap,ps); forged=replace(p,effect_authority=True,gate10=True); self.assertFalse(commit(forged,H,snapshot=self.snap,proposals=ps).committed)

if __name__=='__main__': unittest.main()
