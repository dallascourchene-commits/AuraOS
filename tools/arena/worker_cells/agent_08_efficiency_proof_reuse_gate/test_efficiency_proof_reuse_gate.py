import unittest
from dataclasses import replace
from itertools import product
from efficiency_proof_reuse_gate import *

class T(unittest.TestCase):
    def test_exact_reuse(self): self.assertEqual(assess(valid_evidence()).decision, Decision.REUSE_EXACT)
    def test_no_caller_validity_booleans(self):
        self.assertNotIn("verified", ProofParentEvidence.__dataclass_fields__); self.assertNotIn("receipt_valid", CostParentEvidence.__dataclass_fields__)
    def test_proof_semantic_generation_pinned(self):
        e=valid_evidence(); p=replace(e.proof,semantic_commit="1"*40); self.assertEqual(assess(replace(e,proof=p)).decision,Decision.REPROVE)
    def test_proof_verifier_blob_pinned(self):
        e=valid_evidence(); p=replace(e.proof,verifier_blob="1"*40); self.assertEqual(assess(replace(e,proof=p)).decision,Decision.REPROVE)
    def test_proof_current_source_pinned(self):
        e=valid_evidence(); p=replace(e.proof,current_source_head="1"*40); self.assertEqual(assess(replace(e,proof=p)).decision,Decision.REPROVE)
    def test_proof_axes_noncompensatory(self):
        e=valid_evidence()
        for field in ("expected_result_root","expected_workflow_generation","expected_input_root","expected_dependency_root","expected_required_step_root","expected_trace_root","expected_environment_root","expected_resource_budget_root","expected_trace_schema_root","expected_event_root","reconstructed_event_root","expected_cumulative_budget_proof_root","expected_oracle_ceiling_proof_root","expected_execution_provenance_root","expected_fused_event_structure_root"):
            p=replace(e.proof,**{field:"drift" if "generation" in field else digest({"drift":field})}); self.assertEqual(assess(replace(e,proof=p)).decision,Decision.REPROVE,field)
    def test_cost_semantic_generation_pinned(self):
        e=valid_evidence(); c=replace(e.cost,semantic_commit="1"*40); self.assertEqual(assess(replace(e,cost=c)).decision,Decision.REPROVE)
    def test_cost_verifier_blob_pinned(self):
        e=valid_evidence(); c=replace(e.cost,verifier_blob="1"*40); self.assertEqual(assess(replace(e,cost=c)).decision,Decision.REPROVE)
    def test_cost_source_pinned(self):
        e=valid_evidence(); c=replace(e.cost,envelope=replace(e.cost.envelope,source_head="1"*40)); self.assertEqual(assess(replace(e,cost=c)).decision,Decision.REPROVE)
    def test_cost_contamination_recomputed(self):
        e=valid_evidence(); ss=list(e.cost.samples); ss[1]=replace(ss[1],rendered_prefix=ss[0].rendered_prefix); c=replace(e.cost,samples=tuple(ss)); self.assertEqual(assess(replace(e,cost=c)).decision,Decision.REPROVE)
    def test_cost_budget_recomputed(self):
        e=valid_evidence(); c=replace(e.cost,envelope=replace(e.cost.envelope,speculative_energy_budget_j="0.0000001")); self.assertEqual(assess(replace(e,cost=c)).decision,Decision.REPROVE)
    def test_cost_transfer_integrity_recomputed(self):
        e=valid_evidence(); ts=list(e.cost.transfers); ts[1]=replace(ts[1],sequence=9); c=replace(e.cost,transfers=tuple(ts)); self.assertEqual(assess(replace(e,cost=c)).decision,Decision.REPROVE)
    def test_recorded_projection_drift_reproves(self):
        e=valid_evidence(); self.assertEqual(assess(replace(e,proved_cost_projection_root="f"*64)).decision,Decision.REPROVE)
    def test_authority_never_minted(self):
        r=assess(replace(valid_evidence(),authority_requested=True)); self.assertEqual(r.decision,Decision.REPROVE); self.assertFalse(r.truth_authority); self.assertFalse(r.effect_authority); self.assertFalse(r.gate10)
    def test_context_changes_receipt_not_decision(self):
        e=valid_evidence(); a=assess(e,(0,0,0,0,0)); b=assess(e,(2,2,2,2,2)); self.assertEqual(a.decision,b.decision); self.assertNotEqual(a.context_root,b.context_root); self.assertNotEqual(a.receipt_root,b.receipt_root)
    def test_context_cannot_repair_invalid(self):
        e=replace(valid_evidence(),proved_cost_projection_root="f"*64); base=assess(e); roots=set()
        self.assertEqual(base.decision,Decision.REPROVE)
        for tail in product(range(3),repeat=5):
            r=recontextualize(base,tail); self.assertEqual(r.decision,Decision.REPROVE); roots.add(r.context_root)
        self.assertEqual(len(roots),243)
    def test_receipt_tamper(self):
        e=valid_evidence(); r=assess(e); self.assertFalse(verify_receipt(e,replace(r,claim_generation="x")))
    def test_omega8_one_keeper(self): self.assertEqual(sum(crystalline_admission(x) for x in product(range(3),repeat=8)),1)
    def test_13d_tail_applied_no_repair(self):
        bad=(0,2,2,2,2,2,2,1); roots=set()
        for tail in product(range(3),repeat=5):
            self.assertFalse(admission_13d(bad,tail)); roots.add(digest({"context5":list(tail)}))
        self.assertEqual(len(roots),243)
if __name__=="__main__": unittest.main()
