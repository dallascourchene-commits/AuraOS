import unittest
from tools.arena.transactional_shared_truth_commit import *

def adm(*, att="att", current=True, proof=True):
    return AttemptAdmission("CREATIVE", "op", att, "src", "wc", "lease", current, proof)

class PR924AtomicRepairTests(unittest.TestCase):
    def setUp(self):
        self.store=SharedTruthStore(); self.store.seed({"a":"0"}); self.pre=self.store.state_root()
    def proposal(self, att="att"):
        return CommitProposal(CommitMode.KEY_PRECONDITION,"op",att,self.pre,(("a","1"),),(("a","0"),))
    def test_truthy_string_current_is_not_current(self):
        d=self.store.commit(adm(current="false"),self.proposal())
        self.assertEqual(d.reason,"ATTEMPT_ADMISSION_BOOL_INVALID"); self.assertIsNone(d.commit_receipt_root)
    def test_integer_proof_bound_is_not_proof_boolean(self):
        d=self.store.commit(adm(proof=1),self.proposal())
        self.assertEqual(d.reason,"ATTEMPT_ADMISSION_BOOL_INVALID"); self.assertIsNone(d.commit_receipt_root)
    def test_non_bool_flags_cannot_unlock_existing_dedup_receipt(self):
        d1=self.store.commit(adm(att="good"),self.proposal("good")); self.assertEqual(d1.disposition,Disposition.COMMIT_D0)
        d2=self.store.commit(adm(att="bad",current="false",proof=1),self.proposal("bad"))
        self.assertEqual(d2.disposition,Disposition.HOLD); self.assertEqual(d2.reason,"ATTEMPT_ADMISSION_BOOL_INVALID"); self.assertIsNone(d2.commit_receipt_root)

if __name__=="__main__": unittest.main()
