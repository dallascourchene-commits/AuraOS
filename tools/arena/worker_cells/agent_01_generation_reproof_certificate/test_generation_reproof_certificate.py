import itertools
import os
import sys
import unittest
from dataclasses import replace

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
from generation_reproof_certificate import *


class T(unittest.TestCase):
    def setUp(self):
        self.p = demo_prior()
        self.a = self.p.parent_a
        self.b = self.p.parent_b

    def owner_root(self, role, tag): return digest({"role":role,"tag":tag})
    def trans(self, old, new=None, cls=TransitionClass.EXACT_UNCHANGED, fields=(), owner_ok=True):
        new = old if new is None else new
        r = self.owner_root(old.role, cls.value)
        return TransitionAttestation(old.role, old.snapshot_root, new, cls, tuple(fields), r, r if owner_ok else digest({"wrong":r}), owner_ok)

    def test_00_exact_reuse(self):
        r=compile_reproof(self.p,[self.trans(self.a),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.REUSE_EXACT); self.assertTrue(r.eligible_to_readjudicate); self.assertFalse(r.auto_admitted)
    def test_01_exact_transition_cannot_hide_generation_change(self):
        n=replace(self.a,generation="new")
        r=compile_reproof(self.p,[self.trans(self.a,n),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
    def test_02_neutral_generation_rebind(self):
        n=replace(self.a,generation="new",receipt_root=digest({"new":"receipt"}))
        t=self.trans(self.a,n,TransitionClass.PROOF_NEUTRAL_REBIND,("generation","receipt_root"))
        r=compile_reproof(self.p,[t,self.trans(self.b)])
        self.assertEqual(r.decision,Decision.REBIND_AND_READJUDICATE); self.assertTrue(r.eligible_to_readjudicate)
    def test_03_neutral_rebind_requires_same_consequence_root(self):
        n=replace(self.a,generation="new",receipt_root=digest({"r":2}),consequence_root=digest({"c":2}))
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.PROOF_NEUTRAL_REBIND,("generation","receipt_root")),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.REPROVE_MINIMUM_CONE); self.assertIn("WORKLOAD:REPROVE_PARENT",r.obligations)
    def test_04_neutral_rebind_cannot_change_source(self):
        n=replace(self.a,generation="new",receipt_root=digest({"r":3}),source_identity="other")
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.PROOF_NEUTRAL_REBIND,("generation","receipt_root")),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.REPROVE_MINIMUM_CONE)
    def test_05_consequence_change_reproofs_only_changed_parent_plus_cross_binding(self):
        n=replace(self.b,generation="new",receipt_root=digest({"r":4}),consequence_root=digest({"c":4}))
        r=compile_reproof(self.p,[self.trans(self.a),self.trans(self.b,n,TransitionClass.CONSEQUENCE_CHANGED,("generation","receipt_root"))])
        self.assertEqual(r.decision,Decision.REPROVE_MINIMUM_CONE); self.assertIn("COST:REPROVE_PARENT",r.obligations); self.assertNotIn("WORKLOAD:REPROVE_PARENT",r.obligations)
    def test_06_unknown_owner_attestation_holds(self):
        r=compile_reproof(self.p,[self.trans(self.a,cls=TransitionClass.UNKNOWN,owner_ok=False),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.HOLD_UNKNOWN); self.assertIn("WORKLOAD:VERIFY_OR_REPROVE_PARENT",r.obligations)
    def test_07_new_parent_not_verified_holds(self):
        n=replace(self.a,generation="new",verified=False)
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.UNKNOWN),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
    def test_08_new_parent_stale_holds(self):
        n=replace(self.a,generation="new",current=False)
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.UNKNOWN),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
    def test_09_non_d0_parent_holds(self):
        n=replace(self.a,generation="new",d0=False)
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.UNKNOWN),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
    def test_10_old_binding_mismatch_holds(self):
        t=replace(self.trans(self.a),old_snapshot_root=digest({"wrong":"old"}))
        r=compile_reproof(self.p,[t,self.trans(self.b)])
        self.assertEqual(r.decision,Decision.HOLD_UNKNOWN); self.assertIn("WORKLOAD:OLD_BINDING_MISMATCH",r.obligations)
    def test_11_cross_source_drift_requires_readjudication(self):
        n=replace(self.a,generation="new",receipt_root=digest({"r":5}),consequence_root=digest({"c":5}),source_identity="src-new")
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.CONSEQUENCE_CHANGED,("source_identity","generation")),self.trans(self.b)])
        self.assertTrue(any(x.startswith("CROSS_BINDINGS:READJUDICATE") for x in r.obligations))
    def test_12_cross_benchmark_drift_detected(self):
        n=replace(self.a,generation="new",receipt_root=digest({"r":6}),consequence_root=digest({"c":6}),benchmark_generation="bench-g2")
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.CONSEQUENCE_CHANGED,("benchmark_generation",)),self.trans(self.b)])
        self.assertTrue(any("benchmark_generation" in x for x in r.obligations))
    def test_13_cross_envelope_drift_detected(self):
        n=replace(self.a,generation="new",receipt_root=digest({"r":7}),consequence_root=digest({"c":7}),envelope_id="env-g2")
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.CONSEQUENCE_CHANGED,("envelope_id",)),self.trans(self.b)])
        self.assertTrue(any("envelope_id" in x for x in r.obligations))
    def test_14_two_transitions_required(self):
        with self.assertRaises(ReproofError): compile_reproof(self.p,[self.trans(self.a)])
    def test_15_duplicate_roles_rejected(self):
        with self.assertRaises(ReproofError): compile_reproof(self.p,[self.trans(self.a),self.trans(self.a)])
    def test_16_wrong_role_set_rejected(self):
        x=replace(self.b,role="OTHER"); t=self.trans(self.b,x)
        with self.assertRaises(ReproofError): compile_reproof(self.p,[self.trans(self.a),t])
    def test_17_duplicate_changed_field_rejected(self):
        t=replace(self.trans(self.a),changed_fields=("generation","generation"))
        with self.assertRaises(ReproofError): compile_reproof(self.p,[t,self.trans(self.b)])
    def test_18_unknown_changed_field_for_neutral_forces_reproof(self):
        n=replace(self.a,generation="new",receipt_root=digest({"r":8}))
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.PROOF_NEUTRAL_REBIND,("semantic_policy",)),self.trans(self.b)])
        self.assertEqual(r.decision,Decision.REPROVE_MINIMUM_CONE)
    def test_19_receipt_verification(self):
        ts=[self.trans(self.a),self.trans(self.b)]; r=compile_reproof(self.p,ts); self.assertTrue(verify_receipt(self.p,ts,r)); self.assertFalse(verify_receipt(self.p,ts,replace(r,bridge_id="x")))
    def test_20_receipt_never_auto_admits(self):
        for cls in Decision:
            if cls is Decision.REUSE_EXACT: ts=[self.trans(self.a),self.trans(self.b)]
            else: ts=[self.trans(self.a,cls=TransitionClass.UNKNOWN,owner_ok=False),self.trans(self.b)]
            self.assertFalse(compile_reproof(self.p,ts).auto_admitted)
    def test_21_omega8_one_keeper(self):
        keep=[o for o in itertools.product(range(3),repeat=8) if crystalline_admission(o)]
        self.assertEqual(keep,[(2,2,2,2,2,2,2,1)])
    def test_22_13d_tail_cannot_repair(self):
        bad=(0,2,2,2,2,2,2,1)
        self.assertTrue(all(not admission_13d(bad,t) for t in itertools.product(range(3),repeat=5)))
    def test_23_invalid_omega8_rejected(self):
        with self.assertRaises(ReproofError): crystalline_admission((2,)*7)
    def test_24_invalid_tail_rejected(self):
        with self.assertRaises(ReproofError): admission_13d((2,2,2,2,2,2,2,1),(0,)*4)
    def test_25_parent_bool_is_strict(self):
        with self.assertRaises(ReproofError): replace(self.a,verified=1).validate()
    def test_26_transition_bool_is_strict(self):
        with self.assertRaises(ReproofError): replace(self.trans(self.a),owner_verified=1).validate()
    def test_27_receipt_root_deterministic(self):
        ts=[self.trans(self.a),self.trans(self.b)]; self.assertEqual(compile_reproof(self.p,ts).receipt_root,compile_reproof(self.p,ts).receipt_root)
    def test_28_minimum_cone_deduplicates_cross_obligation(self):
        n=replace(self.a,generation="n",receipt_root=digest({"r":9}),consequence_root=digest({"c":9}),source_identity="x")
        r=compile_reproof(self.p,[self.trans(self.a,n,TransitionClass.CONSEQUENCE_CHANGED,("source_identity",)),self.trans(self.b)])
        self.assertEqual(len(r.obligations),len(set(r.obligations)))
    def test_29_live_o4_transition_is_not_reusable(self):
        # Agent 06 moved and remains review-invalid/unknown; Agent 05 changed arithmetic consequence.
        a_new=replace(self.a,generation=O4_PARENT_A_NEW,receipt_root=digest({"a":"new"}),consequence_root=digest({"a":"review-invalid"}),verified=False,current=True)
        b_new=replace(self.b,generation=O4_PARENT_B_NEW,receipt_root=digest({"b":"new"}),consequence_root=digest({"b":"exact-rational"}))
        ta=self.trans(self.a,a_new,TransitionClass.UNKNOWN,("generation","receipt_root"),owner_ok=False)
        tb=self.trans(self.b,b_new,TransitionClass.CONSEQUENCE_CHANGED,("generation","receipt_root"))
        r=compile_reproof(self.p,[ta,tb])
        self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
        self.assertIn("WORKLOAD:VERIFY_OR_REPROVE_PARENT",r.obligations)
        self.assertIn("COST:REPROVE_PARENT",r.obligations)
        self.assertFalse(r.eligible_to_readjudicate)

if __name__ == "__main__": unittest.main()
