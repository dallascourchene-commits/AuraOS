import itertools,os,sys,unittest
from dataclasses import replace
HERE=os.path.dirname(__file__);sys.path.insert(0,HERE)
from two_stage_readjudication import *
def R(x):return dig(x)
def local():
 return LocalSurface('1'*40,'1'*40,R('p'),R('p'),R('d'),R('d'),R('g'),R('g'),R('a'),R('a'),R('r'),R('r'))
def subjects(state=ProviderState.ATTESTED):
 return tuple(AuthSubject(s,'2'*40,state,R(s) if state==ProviderState.ATTESTED else None) for s in SUBJECTS)
class T(unittest.TestCase):
 def test_all_exact_eligible(self):
  r=adjudicate(local(),subjects());self.assertEqual(r.decision,Decision.ELIGIBLE_FOR_FRESH_READJUDICATION);self.assertTrue(r.verify())
 def test_local_projection_first(self):
  x=replace(local(),current_projection_root=R('x'));r=adjudicate(x,subjects(ProviderState.OBSERVED));self.assertEqual(r.decision,Decision.REPROVE_LOCAL_FIRST);self.assertEqual(r.bundle_ids,())
 def test_local_domain_first(self):self.assertEqual(adjudicate(replace(local(),current_domain_root=R('x')),subjects()).decision,Decision.REPROVE_LOCAL_FIRST)
 def test_local_generation_first(self):self.assertEqual(adjudicate(replace(local(),current_generation='3'*40),subjects()).decision,Decision.REPROVE_LOCAL_FIRST)
 def test_auth_missing_cutset(self):
  xs=list(subjects());xs[0]=AuthSubject(xs[0].subject,xs[0].generation,ProviderState.OBSERVED,None);r=adjudicate(local(),xs);self.assertEqual(r.decision,Decision.HOLD_AUTHENTICATION_CUTSET);self.assertIn(xs[0].subject,r.missing_subjects)
 def test_two_pair_bundles(self):
  xs=tuple(AuthSubject(s,'2'*40,ProviderState.OBSERVED,None) for s in SUBJECTS);r=adjudicate(local(),xs);self.assertEqual(set(r.bundle_ids),{'BUNDLE_EFFICIENCY_COST','BUNDLE_SECURITY_DAG'})
 def test_single_missing_prefers_singleton(self):
  xs=list(subjects());target='AIRLLM_SECURITY_PARENT';i=SUBJECTS.index(target);xs[i]=AuthSubject(target,'2'*40,ProviderState.EXPIRED,None);r=adjudicate(local(),xs);self.assertEqual(r.bundle_ids,('SINGLE_AIRLLM_SECURITY_PARENT',))
 def test_attested_requires_receipt(self):
  xs=list(subjects());xs[0]=AuthSubject(xs[0].subject,'2'*40,ProviderState.ATTESTED,None);self.assertRaises(E,adjudicate,local(),xs)
 def test_contested_unresolved(self):
  xs=list(subjects());xs[1]=AuthSubject(xs[1].subject,'2'*40,ProviderState.CONTESTED,None);self.assertEqual(adjudicate(local(),xs).decision,Decision.HOLD_AUTHENTICATION_CUTSET)
 def test_duplicate_subject_fails(self):
  xs=list(subjects());xs[0]=xs[1];self.assertRaises(E,adjudicate,local(),xs)
 def test_incomplete_auth_fails(self):self.assertRaises(E,adjudicate,local(),subjects()[:-1])
 def test_authority_first(self):self.assertEqual(adjudicate(replace(local(),gate10=True),subjects()).decision,Decision.REPROVE_LOCAL_FIRST)
 def test_receipt_tamper(self):self.assertFalse(replace(adjudicate(local(),subjects()),receipt_root='0'*64).verify())
 def test_provider_not_truth(self):self.assertFalse(adjudicate(local(),subjects()).provider_attestation_is_truth)
 def test_order_invariant(self):self.assertEqual(auth_root(subjects()),auth_root(tuple(reversed(subjects()))))
 def test_omega(self):self.assertEqual(sum(crystalline(s) for s in itertools.product(range(3),repeat=8)),1)
 def test_13d(self):
  for t in itertools.product(range(3),repeat=5):self.assertFalse(admission13((0,2,2,2,2,2,2,2)+t))
 def test_context_cannot_pay_auth(self):
  xs=list(subjects());xs[0]=AuthSubject(xs[0].subject,'2'*40,ProviderState.INDETERMINATE,None);self.assertEqual(adjudicate(local(),xs).decision,Decision.HOLD_AUTHENTICATION_CUTSET)
if __name__=='__main__':unittest.main()
