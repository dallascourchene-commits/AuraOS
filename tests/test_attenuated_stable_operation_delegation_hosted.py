import unittest
from dataclasses import replace
from hashlib import sha256
from tools.arena.attenuated_stable_operation_delegation import *
def r(x):return sha256(x.encode()).hexdigest()
def fx(domain='TRAINING'):
 op=StableOperation(domain,r('semantic'),'TRAIN_ADAPTER' if domain=='TRAINING' else 'EDIT_CREATIVE',r('source'),r('policy'));h=(DelegationHop('A',frozenset({'read','train','render'}),100,1),DelegationHop('B',frozenset({'read','train'}),40,2));a=DomainAdmission(domain,op.root(),r('admission'),frozenset({'read','train'}),50,3,True,True);c=AttemptContext('B',r('wc'),1,True,r('lease'),True,op.source_incarnation_root,frozenset({'train'}),20);return op,h,a,c
class T(unittest.TestCase):
 def test_valid_d0(self):
  d=decide(*fx());self.assertIs(d.disposition,Disposition.ADMIT_D0);self.assertFalse(d.effect_authority or d.training_authority or d.checkpoint_authority or d.gate10)
 def test_creative_handoff_same_operation_new_attempt(self):
  op,h,a,c=fx('CREATIVE');c=replace(c,requested_scope=frozenset({'read'}));d1=decide(op,h,a,c);h2=h+(DelegationHop('C',frozenset({'read'}),10,3),);d2=decide(op,h2,a,replace(c,actor='C',workcell_root=r('wc2'),lease_root=r('lease2'),requested_budget=5));self.assertEqual(d1.operation_root,d2.operation_root);self.assertNotEqual(d1.attempt_root,d2.attempt_root)
 def test_scope_escalation_holds(self):
  op,h,a,c=fx();self.assertEqual(decide(op,(h[0],replace(h[1],scope=frozenset({'read','train','delete'}))),a,c).reason,'NON_ATTENUATING_DELEGATION')
 def test_budget_escalation_holds(self):
  op,h,a,c=fx();self.assertEqual(decide(op,(h[0],replace(h[1],budget=101)),a,c).reason,'NON_ATTENUATING_DELEGATION')
 def test_ancestor_stale_holds(self):
  op,h,a,c=fx();self.assertEqual(decide(op,(replace(h[0],current=False),h[1]),a,c).reason,'DELEGATION_ANCESTOR_STALE')
 def test_proof_bound_admission_required(self):
  op,h,a,c=fx();self.assertEqual(decide(op,h,replace(a,proof_bound=False),c).reason,'DOMAIN_ADMISSION_NOT_PROOF_BOUND')
 def test_source_incarnation_current(self):
  op,h,a,c=fx();self.assertEqual(decide(op,h,a,replace(c,source_incarnation_root=r('moved'))).reason,'SOURCE_INCARNATION_MOVED')
 def test_workcell_current(self):
  op,h,a,c=fx();self.assertEqual(decide(op,h,a,replace(c,workcell_current=False)).reason,'ATTEMPT_CURRENTNESS_FAILED')
 def test_lease_current(self):
  op,h,a,c=fx();self.assertEqual(decide(op,h,a,replace(c,lease_current=False)).reason,'ATTEMPT_CURRENTNESS_FAILED')
 def test_requested_scope_bounded(self):
  op,h,a,c=fx();self.assertEqual(decide(op,h,a,replace(c,requested_scope=frozenset({'render'}))).reason,'REQUESTED_SCOPE_EXCEEDS_EFFECTIVE_AUTHORITY')
 def test_requested_budget_bounded(self):
  op,h,a,c=fx();self.assertEqual(decide(op,h,a,replace(c,requested_budget=41)).reason,'REQUESTED_BUDGET_EXCEEDS_EFFECTIVE_AUTHORITY')
 def test_k27_not_identity(self):self.assertNotIn('k27',StableOperation.__dataclass_fields__)
if __name__=='__main__':unittest.main()
