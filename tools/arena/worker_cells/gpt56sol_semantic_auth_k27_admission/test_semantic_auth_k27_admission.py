import itertools, unittest
from dataclasses import replace
import semantic_auth_k27_admission as m
H=lambda s:m.digest({'h':s}); G='1'*40
class T(unittest.TestCase):
 def fixture(self,sd=m.SemanticDecision.EXACT_CURRENT,rd=m.ReadjudicationDecision.ELIGIBLE_FOR_FRESH_READJUDICATION):
  d,p,dep,sem,prov,local,auth=map(H,['domain','proj','dep','sem','prov','local','auth'])
  s=m.make_semantic_transition(decision=sd,semantic_domain_root=d,semantic_projection_root=p,dependency_root=dep)
  r=m.make_readjudication(decision=rd,local_surface_root=local,auth_surface_root=auth)
  b=m.make_cross_plane_binding(s,r)
  a=m.make_admission_set(binding_roots=[b.binding_root],external_receipt_root=H('external'))
  e=m.make_entry(subject_id='kv://demo',semantic_root=sem,semantic_domain_root=d,semantic_projection_root=p,provider_anchor_root=prov,dependency_root=dep,runtime_owner='runtime',runtime_generation=G,compatibility_profile='cp1',benchmark_generation=G,payload_hash=H('payload'),cache_handle='opaque://1')
  c=m.CurrentContext(e.subject_id,sem,d,p,prov,dep,'runtime',G,'cp1',G,H('payload'),local,auth)
  return [s,r,b,a,e,c,m.RoutingSignals(5,2,3,1,0)]
 def test_green(self):
  x=m.decide(*self.fixture());self.assertEqual(x.decision,m.Decision.ADMIT_RUNTIME_REUSE);self.assertTrue(x.verify());self.assertIsNotNone(x.route_score)
 def test_semantic_reprove(self):
  f=self.fixture();f[0]=m.make_semantic_transition(decision=m.SemanticDecision.REPROVE_SECURITY,semantic_domain_root=f[0].semantic_domain_root,semantic_projection_root=f[0].semantic_projection_root,dependency_root=f[0].dependency_root);f[2]=m.make_cross_plane_binding(f[0],f[1]);f[3]=m.make_admission_set(binding_roots=[f[2].binding_root],external_receipt_root=H('x'));self.assertEqual(m.decide(*f).decision,m.Decision.REPROVE_SEMANTIC)
 def test_auth_cutset(self):
  f=self.fixture(rd=m.ReadjudicationDecision.HOLD_AUTHENTICATION_CUTSET);self.assertEqual(m.decide(*f).decision,m.Decision.READJUDICATE_EXTERNAL_AUTH)
 def test_local_first(self):
  f=self.fixture(rd=m.ReadjudicationDecision.REPROVE_LOCAL_FIRST);self.assertEqual(m.decide(*f).decision,m.Decision.REPROVE_SEMANTIC)
 def test_domain_mismatch(self):
  f=self.fixture();f[5]=replace(f[5],semantic_domain_root=H('drift'));self.assertEqual(m.decide(*f).decision,m.Decision.REPROVE_SEMANTIC)
 def test_projection_mismatch(self):
  f=self.fixture();f[5]=replace(f[5],semantic_projection_root=H('drift'));self.assertEqual(m.decide(*f).decision,m.Decision.REPROVE_SEMANTIC)
 def test_binding_not_admitted(self):
  f=self.fixture();f[3]=m.make_admission_set(binding_roots=[H('other')],external_receipt_root=H('x'));self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_semantic_owner_generation_mismatch(self):
  f=self.fixture();f[3]=m.make_admission_set(binding_roots=[f[2].binding_root],external_receipt_root=H('x'),semantic_owner_proof_root=H('othergen'));self.assertEqual(m.decide(*f).decision,m.Decision.REPROVE_SEMANTIC)
 def test_readj_owner_generation_mismatch(self):
  f=self.fixture();f[3]=m.make_admission_set(binding_roots=[f[2].binding_root],external_receipt_root=H('x'),readjudication_owner_generation='2'*40);self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_mix_and_match_parent_receipts_rejected(self):
  f=self.fixture();r2=m.make_readjudication(decision=m.ReadjudicationDecision.ELIGIBLE_FOR_FRESH_READJUDICATION,local_surface_root=H('local2'),auth_surface_root=H('auth2'));f[1]=r2
  self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
  self.assertIn('CROSS_PLANE_RECEIPT_MISMATCH',m.decide(*f).reasons)
 def test_detached_semantic_binding_rejected(self):
  f=self.fixture();f[2]=replace(f[2],semantic_domain_root=H('detached'),binding_root=f[2].binding_root);self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_runtime_generation(self):
  f=self.fixture();f[5]=replace(f[5],runtime_generation='2'*40);self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_benchmark(self):
  f=self.fixture();f[5]=replace(f[5],benchmark_generation='2'*40);self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_payload(self):
  f=self.fixture();f[5]=replace(f[5],payload_hash=H('other'));self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_local_surface(self):
  f=self.fixture();f[5]=replace(f[5],expected_local_surface_root=H('other'));self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_auth_surface(self):
  f=self.fixture();f[5]=replace(f[5],expected_auth_surface_root=H('other'));self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_tamper_semantic(self):
  f=self.fixture();f[0]=replace(f[0],semantic_domain_root=H('x'));self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_tamper_readj(self):
  f=self.fixture();f[1]=replace(f[1],auth_surface_root=H('x'));self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_tamper_binding(self):
  f=self.fixture();f[2]=replace(f[2],auth_surface_root=H('x'));self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_tamper_entry(self):
  f=self.fixture();f[4]=replace(f[4],coordinate=(0,0,0));self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_nan_route_holds(self):
  f=self.fixture();f[6]=m.RoutingSignals(float('nan'),1,1,1,0);self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_overflow_route_holds(self):
  f=self.fixture();f[6]=m.RoutingSignals(1e308,10**6,1e308,1e308,0);self.assertEqual(m.decide(*f).decision,m.Decision.HOLD)
 def test_route_cannot_pay_domain(self):
  f=self.fixture();f[5]=replace(f[5],semantic_domain_root=H('bad'));f[6]=m.RoutingSignals(1e100,10**5,1e100,1e100,0);x=m.decide(*f);self.assertEqual(x.decision,m.Decision.REPROVE_SEMANTIC);self.assertIsNone(x.route_score)
 def test_coordinate(self):
  f=self.fixture();self.assertEqual(f[4].coordinate,m.coordinate_for(f[4].identity_root))
 def test_omega8(self):self.assertEqual(sum(m.crystalline(x) for x in itertools.product(range(3),repeat=8)),1)
 def test_13d(self):
  for tail in itertools.product(range(3),repeat=5):self.assertFalse(m.admission13((0,2,2,2,2,2,2,2)+tail))
if __name__=='__main__':unittest.main()
