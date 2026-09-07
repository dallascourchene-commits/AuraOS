import unittest,sys
from pathlib import Path
HERE=Path(__file__).resolve()
for candidate in (HERE.parent, HERE.parents[1]/'tools'/'arena'):
    if candidate.exists() and str(candidate) not in sys.path: sys.path.insert(0,str(candidate))
from dataclasses import replace
from effect_refinement_seal import *

class T(unittest.TestCase):
    def setUp(self): self.base,self.ref,self.cur=fixture()
    def test_valid_routes_to_tecc_not_effect_ready(self):
        d=compile_refined_tecc_seal(self.base,self.ref,self.cur); self.assertEqual(d.disposition,Disp.HOLD_TECC_REQUIRED_D0); self.assertIsNotNone(d.refined_tecc_input_root); self.assertFalse(d.effect_authority)
    def test_intent_move_rebinds(self): self.assertEqual(compile_refined_tecc_seal(self.base,self.ref,replace(self.cur,intent_binding_root=root('intent2'))).reason,'EFFECT_INTENT_MOVED')
    def test_escalation_move_rebinds(self): self.assertEqual(compile_refined_tecc_seal(self.base,self.ref,replace(self.cur,effect_escalation_root=root('esc2'))).reason,'EFFECT_ESCALATION_MOVED')
    def test_plan_move_rebinds(self): self.assertEqual(compile_refined_tecc_seal(self.base,self.ref,replace(self.cur,refinement_plan_root=root('plan2'))).reason,'EFFECT_REFINEMENT_PLAN_MOVED')
    def test_obligation_move_rebinds(self): self.assertEqual(compile_refined_tecc_seal(self.base,self.ref,replace(self.cur,effect_obligation_root=root('obl2'))).reason,'EFFECT_OBLIGATION_MOVED')
    def test_owner_receipt_move_rebinds(self): self.assertEqual(compile_refined_tecc_seal(self.base,self.ref,replace(self.cur,refinement_owner_receipt_root=root('own2'))).reason,'EFFECT_REFINEMENT_OWNER_RECEIPT_STALE')
    def test_binding_move_rebinds(self): self.assertEqual(compile_refined_tecc_seal(self.base,self.ref,replace(self.cur,active_read_binding_root=root('bind2'))).reason,'EFFECT_REFINEMENT_BINDING_MOVED')
    def test_partial_plan_holds(self): self.assertEqual(compile_refined_tecc_seal(self.base,replace(self.ref,plan_status='PARTIAL_HOLD_D0'),self.cur).disposition,Disp.HOLD)
    def test_read_only_or_hold_base_cannot_route(self): self.assertEqual(compile_refined_tecc_seal(replace(self.base,disposition='HOLD'),self.ref,self.cur).disposition,Disp.HOLD)
    def test_authority_taint_holds(self): self.assertEqual(compile_refined_tecc_seal(self.base,replace(self.ref,effect_authority=True),self.cur).reason,'EFFECT_REFINEMENT_AUTHORITY_ESCALATION')
    def test_refinement_changes_tecc_identity(self):
        d1=compile_refined_tecc_seal(self.base,self.ref,self.cur)
        r2=replace(self.ref,effect_obligation_root=root('obligation-x')); c2=replace(self.cur,effect_obligation_root=root('obligation-x'))
        d2=compile_refined_tecc_seal(self.base,r2,c2)
        self.assertNotEqual(d1.refined_tecc_input_root,d2.refined_tecc_input_root)
        self.assertEqual(self.base.tecc_input_root,self.base.tecc_input_root)
    def test_invalid_root_fails_construction(self):
        with self.assertRaises(ValueError): EffectRefinementSeal('bad',root('i'),root('e'),root('p'),root('o'),root('r'))
if __name__=='__main__':unittest.main()
