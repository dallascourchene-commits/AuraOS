import pathlib, sys, unittest
from dataclasses import replace

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from runtime_bound_memory import *
from campaign import fixture, independent_oracle, run, H

class RuntimeBoundMemoryTests(unittest.TestCase):
    def setUp(self):
        self.memory,self.producer,self.current=fixture()

    def test_clean_is_eligible(self):
        d=admit_memory(self.memory,self.producer,self.current)
        self.assertEqual(d.disposition,Disposition.ELIGIBLE_FOR_OWNER_REVIEW)
        self.assertIsNotNone(d.k27)
        self.assertFalse(d.promotion_authorized); self.assertFalse(d.gate10)

    def test_subject_generation_move_reproves_subject(self):
        m=replace(self.memory,subject_generation="new-generation")
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.REPROVE_SUBJECT_STATE)

    def test_subject_state_move_reproves_subject(self):
        m=replace(self.memory,subject_state_root=H("new-state"))
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.REPROVE_SUBJECT_STATE)

    def test_semantic_domain_move_reproves_semantic(self):
        m=replace(self.memory,semantic_domain_root=H("new-domain"))
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.REPROVE_SEMANTIC)

    def test_semantic_projection_move_reproves_semantic(self):
        m=replace(self.memory,semantic_projection_root=H("new-proj"))
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.REPROVE_SEMANTIC)

    def test_unisolated_producer_reproves_runtime(self):
        p=replace(self.producer,process_isolated=False)
        d=admit_memory(self.memory,p,self.current)
        self.assertEqual(d.disposition,Disposition.REPROVE_PRODUCER_RUNTIME)
        self.assertIsNone(d.k27)

    def test_same_pid_producer_reproves_runtime(self):
        p=replace(self.producer,worker_pid=self.producer.parent_pid)
        self.assertEqual(admit_memory(self.memory,p,self.current).disposition,Disposition.REPROVE_PRODUCER_RUNTIME)

    def test_wrong_start_method_reproves_runtime(self):
        p=replace(self.producer,start_method="fork")
        self.assertEqual(admit_memory(self.memory,p,self.current).disposition,Disposition.REPROVE_PRODUCER_RUNTIME)

    def test_current_impl_move_reproves_runtime(self):
        c=replace(self.current,producer_implementation_generation=H("impl-next"))
        self.assertEqual(admit_memory(self.memory,self.producer,c).disposition,Disposition.REPROVE_PRODUCER_RUNTIME)

    def test_current_owner_move_reproves_runtime(self):
        c=replace(self.current,producer_owner_generation=H("owner-next"))
        self.assertEqual(admit_memory(self.memory,self.producer,c).disposition,Disposition.REPROVE_PRODUCER_RUNTIME)

    def test_memory_receipt_splice_reproves_runtime(self):
        m=replace(self.memory,producer_receipt_root=H("spliced"))
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.REPROVE_PRODUCER_RUNTIME)

    def test_revoked_quarantines_authority(self):
        m=replace(self.memory,revoked=True)
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.QUARANTINE_AUTHORITY)

    def test_external_auth_missing_quarantines_authority(self):
        m=replace(self.memory,externally_authenticated=False)
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.QUARANTINE_AUTHORITY)

    def test_procedural_memory_requires_explicit_authority(self):
        m=replace(self.memory,memory_class="PROCEDURAL",procedure_authority=False)
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.QUARANTINE_AUTHORITY)

    def test_authority_widening_quarantines_integrity(self):
        m=replace(self.memory,authority_ceiling="EFFECT_AUTHORIZED")
        self.assertEqual(admit_memory(m,self.producer,self.current).disposition,Disposition.QUARANTINE_INTEGRITY)

    def test_corroboration_collapses_same_independence_tuple(self):
        c=Corroborator(self.memory.lineage_root,self.memory.source_root,self.memory.consequence_root)
        d=admit_memory(self.memory,self.producer,self.current,[c,c,c],require_independent_corroborators=2)
        self.assertEqual(d.disposition,Disposition.HOLD_CORROBORATION)

    def test_distinct_corroboration_can_clear_hold_but_not_promote(self):
        c1=Corroborator(H("l1"),H("s1"),H("c1"))
        c2=Corroborator(H("l2"),H("s2"),H("c2"))
        d=admit_memory(self.memory,self.producer,self.current,[c1,c2],require_independent_corroborators=2)
        self.assertEqual(d.disposition,Disposition.ELIGIBLE_FOR_OWNER_REVIEW)
        self.assertFalse(d.promotion_authorized)

    def test_k27_shape_and_locality_only(self):
        d=admit_memory(self.memory,self.producer,self.current)
        self.assertEqual(len(d.k27),3); self.assertTrue(all(0<=x<27 for x in d.k27))

    def test_route_scoring_requires_semantic_admission_first(self):
        p=replace(self.producer,process_isolated=False)
        d=admit_memory(self.memory,p,self.current)
        with self.assertRaises(ValueError): route_score(d,1,2,3,4)

    def test_reverse_cone_is_minimal(self):
        graph={"P":["M"],"M":["K","A"],"K":["F"],"A":["F"],"U":["V"]}
        self.assertEqual(reverse_dependency_cone(graph,["P"]),("A","F","K","M","P"))

    def test_campaign(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            s=run(td,1000,1000)
            self.assertEqual(s["hs1000_false_admissions"],0)
            self.assertEqual(s["oracle_mismatches"],0)
            self.assertEqual(s["omega8_keepers"],1)
            self.assertEqual(s["13d_hard_invalid_repairs"],0)

if __name__=="__main__": unittest.main()
