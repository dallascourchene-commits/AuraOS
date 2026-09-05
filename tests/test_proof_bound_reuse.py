import os,sys,unittest
from dataclasses import replace
ROOT=os.path.dirname(os.path.dirname(__file__));sys.path.insert(0,os.path.join(ROOT,'tools','arena'))
from proof_bound_reuse import *

class T(unittest.TestCase):
 def setUp(self):
  self.l=ProofBoundReuseLedger();self.l.bind('P',['D1','D2'],['compile','test']);self.payload={'x':1}
  self.i=self.l.set_current_context('P',source_head='h1',workflow_generation='w1',input_payload=self.payload)
  self.result={'ok':True};self.r=ProofReceipt.build(self.i,self.result,['compile','test'])
 def test_01_admit_and_reuse(self):self.assertTrue(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));self.assertTrue(self.l.reusable('P'))
 def test_02_missing_step_holds(self):self.assertFalse(self.l.admit_fresh_proof(self.i,self.result,['compile'],ProofReceipt.build(self.i,self.result,['compile'])))
 def test_03_tamper_holds(self):self.assertFalse(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],replace(self.r,receipt_digest='0'*64)))
 def test_04_head_change_invalidates_reuse(self):
  self.assertTrue(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));self.l.set_current_context('P',source_head='h2',workflow_generation='w1',input_payload=self.payload);self.assertFalse(self.l.reusable('P'))
 def test_05_workflow_change_invalidates_reuse(self):
  self.assertTrue(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));self.l.set_current_context('P',source_head='h1',workflow_generation='w2',input_payload=self.payload);self.assertFalse(self.l.reusable('P'))
 def test_06_input_change_invalidates_reuse(self):
  self.assertTrue(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));self.l.set_current_context('P',source_head='h1',workflow_generation='w1',input_payload={'x':2});self.assertFalse(self.l.reusable('P'))
 def test_07_dependency_invalidation(self):
  self.assertTrue(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));self.assertEqual(self.l.invalidate(['D1']),{'P'});self.assertFalse(self.l.reusable('P'))
 def test_08_unrelated_dependency_does_not_wake(self):
  self.assertTrue(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));self.assertEqual(self.l.invalidate(['DX']),set());self.assertTrue(self.l.reusable('P'))
 def test_09_rebind_old_dependency_removed(self):
  self.l.bind('P',['D3'],['compile','test']);self.assertEqual(self.l.invalidate(['D1']),set());self.assertEqual(self.l.invalidate(['D3']),{'P'})
 def test_10_old_receipt_fails_after_rebind(self):
  self.l.bind('P',['D1','D2','D3'],['compile','test']);self.assertFalse(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r))
 def test_11_fresh_reproof_closes_stale(self):
  self.assertTrue(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));self.l.invalidate(['D1']);j=self.l.current_identity('P');rr=ProofReceipt.build(j,self.result,['compile','test']);self.assertTrue(self.l.admit_fresh_proof(j,self.result,['compile','test'],rr));self.assertTrue(self.l.reusable('P'))
 def test_12_authority_cannot_promote(self):self.assertFalse(self.r.effect_authority);self.assertFalse(self.r.gate10)
 def test_13_receipt_result_tamper(self):self.assertFalse(self.r.validate(self.i,{'ok':False},['compile','test']))
 def test_14_receipt_steps_tamper(self):self.assertFalse(self.r.validate(self.i,self.result,['compile']))
 def test_15_unknown_project_not_reusable(self):self.assertFalse(self.l.reusable('X'))
 def test_16_empty_binding_rejected(self):
  with self.assertRaises(ValueError):self.l.bind('X',[],['a'])
 def test_17_omega8_hard_invalid_dominance(self):self.assertTrue(omega8_admit((2,2,2,2,2,2,2,1)));self.assertFalse(omega8_admit((2,2,0,2,2,2,2,1)))
 def test_18_forged_alternate_head_cannot_be_admitted(self):
  forged=replace(self.i,source_head='evil');rr=ProofReceipt.build(forged,self.result,['compile','test']);self.assertFalse(self.l.admit_fresh_proof(forged,self.result,['compile','test'],rr))
 def test_19_rebind_requires_new_generation_receipt(self):
  self.assertTrue(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));self.l.bind('P',['D1','D2'],['compile','test']);j=self.l.current_identity('P');self.assertNotEqual(j.binding_generation,self.i.binding_generation);self.assertFalse(self.l.reusable('P'));self.assertFalse(self.l.admit_fresh_proof(self.i,self.result,['compile','test'],self.r));rr=ProofReceipt.build(j,self.result,['compile','test']);self.assertTrue(self.l.admit_fresh_proof(j,self.result,['compile','test'],rr))

if __name__=='__main__':unittest.main()
