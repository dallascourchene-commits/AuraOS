from dataclasses import replace
import unittest
from tools.arena.frontier27_runtime import CollisionBucket, CurrentnessInvalidator
from tools.arena.consequence_admission_kernel import ConsequenceAdmissionKernel
from tools.arena.research_testspec_proof_reuse_adapter import *

def base(**kw):
    c=ResearchProofContract(
        principal="P1",claim_id="C1",claim_digest="cd1",k27=(6,6,14),semantic_key="planfence",
        testspec_root="ts1",semantic_admission_root="sa1",source_id="src1",source_owner_ref="arxiv",
        source_generation="g1",currentness_root="cur1",evidence_roots=frozenset({"e1","e2"}),min_independent_roots=2,
        proof_units=(ProofUnit("SOURCE",frozenset({"source.py"}),"p1"),ProofUnit("ORACLE",frozenset({"source.py","oracle.py"}),"p2"),ProofUnit("DOC",frozenset({"README.md"}),"p3")),
        proof_surface={"source.py":"b1","oracle.py":"b2","README.md":"b3"},resolution=2)
    return replace(c,**kw)

def adapter():
    return ResearchTestSpecProofReuseAdapter(secret=b"secret",bucket=CollisionBucket(),currentness=CurrentnessInvalidator(),kernel=ConsequenceAdmissionKernel())

class TestAdapter(unittest.TestCase):
    def setUp(self): self.a=adapter(); self.s=self.a.store(base())
    def test_exact_reuse(self):
        r=self.a.assess(base()); self.assertEqual(r.disposition,"REUSE_EXACT"); self.assertEqual(r.kernel_decision,"READY_NONAUTHORIZING"); self.assertFalse(r.effect_authority)
    def test_currentness_only_rebind(self): self.assertEqual(self.a.assess(base(currentness_root="cur2")).disposition,"REBIND_CURRENTNESS")
    def test_claim_drift_reproof(self): self.assertEqual(self.a.assess(base(claim_digest="cd2")).disposition,"REPROVE_CONE")
    def test_source_generation_reproof(self): self.assertEqual(self.a.assess(base(source_generation="g2")).disposition,"REPROVE_CONE")
    def test_evidence_ancestry_reproof(self): self.assertEqual(self.a.assess(base(evidence_roots=frozenset({"e1","e3"}))).disposition,"REPROVE_CONE")
    def test_same_lineage_duplicate_adds_no_mass(self):
        p=base(evidence_roots=frozenset(["e1","e1","e2"])); self.assertEqual(len(p.evidence_roots),2); self.assertEqual(self.a.assess(p).disposition,"REUSE_EXACT")
    def test_insufficient_evidence_rejected(self):
        with self.assertRaisesRegex(ValueError,"INSUFFICIENT_INDEPENDENT"):
            self.a.assess(base(evidence_roots=frozenset({"e1"})))
    def test_source_change_invalidates_source_and_oracle_units(self):
        p=base(proof_surface={"source.py":"x","oracle.py":"b2","README.md":"b3"}); r=self.a.assess(p)
        self.assertEqual(r.disposition,"REPROVE_CONE"); self.assertEqual(r.invalid_units,("ORACLE","SOURCE"))
    def test_doc_change_invalidates_doc_only(self):
        p=base(proof_surface={"source.py":"b1","oracle.py":"b2","README.md":"x"}); self.assertEqual(self.a.assess(p).invalid_units,("DOC",))
    def test_scope_expansion_holds_all(self):
        p=base(proof_surface={"source.py":"b1","oracle.py":"b2","README.md":"b3","new.py":"n"}); r=self.a.assess(p)
        self.assertEqual(r.disposition,"HOLD_UNKNOWN"); self.assertEqual(set(r.invalid_units),{"SOURCE","ORACLE","DOC"})
    def test_missing_dependency_is_classified_not_pre_rejected(self):
        p=base(proof_surface={"source.py":"b1","README.md":"b3"}); r=self.a.assess(p); self.assertEqual(r.disposition,"REPROVE_CONE"); self.assertIn("ORACLE",r.invalid_units)
    def test_currentness_plus_semantic_drift_preserves_both_reasons(self):
        p=base(currentness_root="cur2",proof_surface={"source.py":"x","oracle.py":"b2","README.md":"b3"}); r=self.a.assess(p)
        self.assertIn("CURRENTNESS_DRIFT",r.reasons); self.assertIn("PROOF_SURFACE_DRIFT",r.reasons)
    def test_cross_principal_miss(self): self.assertEqual(self.a.assess(base(principal="P2")).disposition,"MISS")
    def test_testspec_identity_is_physical_key(self): self.assertEqual(self.a.assess(base(testspec_root="ts2")).disposition,"MISS")
    def test_resolution_cannot_compensate(self): self.assertEqual(self.a.assess(base(resolution=1)).disposition,"REPROVE_CONE")
    def test_effect_request_rejected_before_cache(self):
        with self.assertRaisesRegex(ValueError,"D0_EFFECT_CEILING"):
            self.a.assess(base(asks_effect_authority=True))

if __name__=='__main__': unittest.main()
