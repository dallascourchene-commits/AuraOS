import os
import sqlite3
import tempfile
import unittest
from tools.arena.transactional_shared_truth_commit import *

def adm(domain="CREATIVE", op="op", att="att", current=True, proof=True):
    return AttemptAdmission(domain, op, att, "src", "wc", "lease", current, proof)

class O19Tests(unittest.TestCase):
    def test_exact_commit(self):
        s=SharedTruthStore(); s.seed({"w":"1","opt":"a","rng":"r"}); pre=s.state_root()
        d=s.commit(adm("TRAINING"),CommitProposal(CommitMode.EXACT_PRESTATE,"op","att",pre,(("w","2"),),resume_root=pre))
        self.assertEqual(d.disposition,Disposition.COMMIT_D0); self.assertEqual(s.state()["w"],"2")
    def test_exact_stale_prestate_holds(self):
        s=SharedTruthStore(); s.seed({"w":"1"}); pre=s.state_root(); s.seed({"w":"2"})
        d=s.commit(adm("TRAINING"),CommitProposal(CommitMode.EXACT_PRESTATE,"op","att",pre,(("w","3"),),resume_root=pre))
        self.assertEqual(d.reason,"EXACT_PRESTATE_MOVED")
    def test_exact_resume_required(self):
        s=SharedTruthStore(); s.seed({"w":"1"}); pre=s.state_root()
        d=s.commit(adm("TRAINING"),CommitProposal(CommitMode.EXACT_PRESTATE,"op","att",pre,(("w","2"),),resume_root="wrong"))
        self.assertEqual(d.reason,"EXACT_RESUME_ROOT_REQUIRED")
    def test_disjoint_key_patches_compose(self):
        s=SharedTruthStore(); s.seed({"a":"0","b":"0"}); pre=s.state_root()
        d1=s.commit(adm(att="a1"),CommitProposal(CommitMode.KEY_PRECONDITION,"op","a1",pre,(("a","1"),),(("a","0"),)))
        d2=s.commit(adm(att="a2"),CommitProposal(CommitMode.KEY_PRECONDITION,"op","a2",pre,(("b","1"),),(("b","0"),)))
        self.assertEqual((d1.disposition,d2.disposition),(Disposition.COMMIT_D0,Disposition.COMMIT_D0))
    def test_same_target_conflict_holds(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root()
        s.commit(adm(att="a1"),CommitProposal(CommitMode.KEY_PRECONDITION,"op","a1",pre,(("a","1"),),(("a","0"),)))
        d=s.commit(adm(att="a2"),CommitProposal(CommitMode.KEY_PRECONDITION,"op","a2",pre,(("a","2"),),(("a","0"),)))
        self.assertEqual(d.reason,"KEY_PRECONDITION_CONFLICT")
    def test_identical_commit_dedup(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); p=CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),))
        d1=s.commit(adm(),p); d2=s.commit(adm(),p)
        self.assertEqual(d2.disposition,Disposition.DEDUP_D0); self.assertEqual(d1.commit_receipt_root,d2.commit_receipt_root)
    def test_publish_requires_commit(self): self.assertEqual(SharedTruthStore().publish("missing","p").reason,"COMMIT_RECEIPT_REQUIRED")
    def test_publication_separate(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),)))
        p=s.publish(d.commit_receipt_root,"projection"); self.assertEqual(p.disposition,Disposition.PUBLISH_D0); self.assertNotEqual(p.publication_root,d.commit_receipt_root)
    def test_stale_admission_holds(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(current=False),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),)))
        self.assertEqual(d.reason,"ATTEMPT_ADMISSION_STALE")
    def test_unproofed_admission_holds(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(proof=False),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),)))
        self.assertEqual(d.reason,"ATTEMPT_ADMISSION_NOT_PROOF_BOUND")
    def test_operation_mismatch_holds(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(op="other"),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),)))
        self.assertEqual(d.reason,"ATTEMPT_LINEAGE_MISMATCH")
    def test_attempt_mismatch_holds(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(att="other"),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),)))
        self.assertEqual(d.reason,"ATTEMPT_LINEAGE_MISMATCH")
    def test_precondition_coverage_required(self):
        s=SharedTruthStore(); s.seed({"a":"0","b":"0"}); pre=s.state_root(); d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),("b","1")),(("a","0"),)))
        self.assertEqual(d.reason,"PRECONDITION_COVERAGE_REQUIRED")
    def test_duplicate_write_keys_rejected(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),("a","2")),(("a","0"),)))
        self.assertEqual(d.reason,"MALFORMED_WRITES")
    def test_empty_writes_rejected(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(),()))
        self.assertEqual(d.reason,"MALFORMED_WRITES")
    def test_authority_ceiling_false_on_commit(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),)))
        self.assertFalse(d.effect_authority or d.checkpoint_authority or d.project_write_authority or d.gate10)
    def test_authority_ceiling_false_on_publish(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),))); p=s.publish(d.commit_receipt_root,"x")
        self.assertFalse(p.effect_authority or p.checkpoint_authority or p.project_write_authority or p.gate10)
    def test_same_patch_other_attempt_dedups_by_operation_patch(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); p1=CommitProposal(CommitMode.KEY_PRECONDITION,"op","att1",pre,(("a","1"),),(("a","0"),)); p2=CommitProposal(CommitMode.KEY_PRECONDITION,"op","att2",pre,(("a","1"),),(("a","0"),))
        d1=s.commit(adm(att="att1"),p1); d2=s.commit(adm(att="att2"),p2); self.assertEqual(d2.disposition,Disposition.DEDUP_D0)
    def test_different_operation_same_patch_not_dedup(self):
        s=SharedTruthStore(); s.seed({"a":"0","b":"0"}); pre=s.state_root(); s.commit(adm(op="op1",att="a1"),CommitProposal(CommitMode.KEY_PRECONDITION,"op1","a1",pre,(("a","1"),),(("a","0"),)))
        d2=s.commit(adm(op="op2",att="a2"),CommitProposal(CommitMode.KEY_PRECONDITION,"op2","a2",pre,(("b","1"),),(("b","0"),))); self.assertEqual(d2.disposition,Disposition.COMMIT_D0)
    def test_publication_idempotent(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root(); d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),))); p1=s.publish(d.commit_receipt_root,"x"); p2=s.publish(d.commit_receipt_root,"x"); self.assertEqual(p1.publication_root,p2.publication_root)
    def test_stale_cross_attempt_dedup_cannot_recover_receipt(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root()
        p1=CommitProposal(CommitMode.KEY_PRECONDITION,"op","good",pre,(("a","1"),),(("a","0"),)); d1=s.commit(adm(att="good"),p1)
        p2=CommitProposal(CommitMode.KEY_PRECONDITION,"op","stale",pre,(("a","1"),),(("a","0"),)); d2=s.commit(adm(att="stale",current=False),p2)
        self.assertEqual(d2.reason,"ATTEMPT_ADMISSION_STALE"); self.assertIsNone(d2.commit_receipt_root); self.assertIsNotNone(d1.commit_receipt_root)
    def test_unproofed_cross_attempt_dedup_cannot_recover_receipt(self):
        s=SharedTruthStore(); s.seed({"a":"0"}); pre=s.state_root()
        p1=CommitProposal(CommitMode.KEY_PRECONDITION,"op","good",pre,(("a","1"),),(("a","0"),)); s.commit(adm(att="good"),p1)
        p2=CommitProposal(CommitMode.KEY_PRECONDITION,"op","unproofed",pre,(("a","1"),),(("a","0"),)); d2=s.commit(adm(att="unproofed",proof=False),p2)
        self.assertEqual(d2.reason,"ATTEMPT_ADMISSION_NOT_PROOF_BOUND"); self.assertIsNone(d2.commit_receipt_root)
    def test_live_recheck_occurs_inside_sqlite_transaction(self):
        class ProbeStore(SharedTruthStore):
            def __init__(self): super().__init__(); self.calls=0; self.live_in_transaction=None
            def state(self):
                self.calls += 1
                if self.calls == 2: self.live_in_transaction = self.db.in_transaction
                return super().state()
        s=ProbeStore(); s.seed({"a":"0"}); pre=state_root({"a":"0"}.items())
        d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),)))
        self.assertEqual(d.disposition,Disposition.COMMIT_D0); self.assertTrue(s.live_in_transaction)
    def test_post_state_root_uses_locked_live_state(self):
        with tempfile.TemporaryDirectory() as td:
            path=os.path.join(td,"truth.db")
            class MoveDisjointAfterFirstSnapshot(SharedTruthStore):
                def __init__(self,p): self.path=p; self.calls=0; super().__init__(p)
                def state(self):
                    snapshot=super().state(); self.calls += 1
                    if self.calls == 1:
                        other=sqlite3.connect(self.path)
                        try:
                            with other: other.execute("UPDATE truth_state SET value='9' WHERE key='b'")
                        finally: other.close()
                    return snapshot
            s=MoveDisjointAfterFirstSnapshot(path); s.seed({"a":"0","b":"0"}); pre=state_root({"a":"0","b":"0"}.items())
            d=s.commit(adm(),CommitProposal(CommitMode.KEY_PRECONDITION,"op","att",pre,(("a","1"),),(("a","0"),)))
            self.assertEqual(d.disposition,Disposition.COMMIT_D0); self.assertEqual(s.state(),{"a":"1","b":"9"}); self.assertEqual(d.post_state_root,s.state_root())

def _mk_variant(i):
    def test(self):
        s=SharedTruthStore(); s.seed({"a":"0","b":"0"}); pre=s.state_root()
        if i % 2 == 0:
            a=adm(att=f"a{i}"); p=CommitProposal(CommitMode.KEY_PRECONDITION,"op",f"a{i}",pre,(("a",str(i+1)),),(("a","0"),))
        else:
            a=adm("TRAINING",att=f"a{i}"); p=CommitProposal(CommitMode.EXACT_PRESTATE,"op",f"a{i}",pre,(("b",str(i+1)),),resume_root=pre)
        self.assertEqual(s.commit(a,p).disposition,Disposition.COMMIT_D0)
    return test
for _i in range(5): setattr(O19Tests,f"test_variant_{_i}",_mk_variant(_i))
if __name__=="__main__": unittest.main()
