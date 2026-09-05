import unittest
from dataclasses import replace
from itertools import product
from efficiency_proof_reuse_gate import *

class T(unittest.TestCase):
    def test_exact(self): self.assertEqual(decide(valid_evidence()),Decision.REUSE_EXACT)
    def test_neutral_rebind(self): self.assertEqual(decide(valid_evidence(Decision.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)),Decision.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
    def test_parent_reprove(self):
        e=valid_evidence(); e=replace(e,proof=replace(e.proof,decision=Decision.REPROVE)); self.assertEqual(decide(e),Decision.REPROVE)
    def test_parent_integrity(self):
        for kw in ({"receipt_valid":False},{"trace_provenance_bound":False},{"expected_receipt_root":"drift"}):
            e=valid_evidence(); self.assertEqual(decide(replace(e,proof=replace(e.proof,**kw))),Decision.REPROVE)
    def test_cost_hard_flags(self):
        for k in ("receipt_valid","policy_ranking_eligible","exact_cumulative_cost_verified","source_current"):
            e=valid_evidence(); r=make_receipt(replace(e,cost=replace(e.cost,**{k:False}))); self.assertEqual(r.decision,Decision.REPROVE)
    def test_all_cost_identities_noncompensatory(self):
        e=valid_evidence()
        for _,b,reason in DRIFTS:
            r=make_receipt(replace(e,cost=replace(e.cost,**{b:"drift"}))); self.assertEqual(r.decision,Decision.REPROVE); self.assertIn(reason,r.reasons)
    def test_authority_never_minted(self):
        r=make_receipt(replace(valid_evidence(),authority_requested=True)); self.assertEqual(r.decision,Decision.REPROVE); self.assertFalse(r.effect_authority); self.assertFalse(r.gate10)
    def test_multiple_failures_do_not_compensate(self):
        e=valid_evidence(); c=replace(e.cost,policy_ranking_eligible=False,expected_workload_root="drift"); r=make_receipt(replace(e,cost=c)); self.assertEqual(r.decision,Decision.REPROVE); self.assertGreater(len(r.reasons),1)
    def test_receipt_deterministic(self):
        e=valid_evidence(); a=make_receipt(e); b=make_receipt(e); self.assertEqual(a.receipt_root,b.receipt_root); self.assertTrue(verify_receipt(e,a))
    def test_receipt_tamper(self):
        e=valid_evidence(); r=make_receipt(e); self.assertFalse(verify_receipt(e,replace(r,claim_generation="x")))
    def test_omega8_exact_keeper(self): self.assertEqual(sum(crystalline_admission(x) for x in product(range(3),repeat=8)),1)
    def test_13d_no_repair(self):
        bad=(0,2,2,2,2,2,2,1)
        for t in product(range(3),repeat=5): self.assertFalse(admission_13d(bad,t))
    def test_invalid_omega(self):
        with self.assertRaises(GateError): crystalline_admission((2,)*7)
    def test_invalid_tail(self):
        with self.assertRaises(GateError): admission_13d((2,2,2,2,2,2,2,1),(2,)*4)
if __name__=="__main__": unittest.main()
