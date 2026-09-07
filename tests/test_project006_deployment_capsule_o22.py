from __future__ import annotations
import dataclasses, unittest
from deployment_capsule_admission import *
K=b'finite-test-key'
COMP=(('consumer.py','1'*64),('guardian.ps1','2'*64),('terminal.py','3'*64))
REQ=('O19_PHYSICAL_WAKE_PROOF','O20_RUNTIME_ATTESTATION','O21_UPDATE_TRANSACTION_PROOF')
CAP=DeploymentCapsule('CAP22','dallascourchene-commits/AuraOS','HEAD22','4'*64,'5'*64,'host-inc-1',COMP,REQ,'6'*64,'7'*64)
HOST=ObservedHostBasis('laptop','host-inc-1','OLDHEAD','5'*64,COMP,'8'*64,1200)
def claims(executed=10,skipped=0,status='PASS',head='HEAD22'):
 return tuple(ProofClaim(n,hashlib.sha256(n.encode()).hexdigest(),head,status,executed,skipped,'v-'+n,'o-'+n) for n in REQ)
def ev(host=HOST,cs=None): return sign_evidence(K,CAP,host,cs or claims(),issued_at_ms=1000,expires_at_ms=5000)
class T(unittest.TestCase):
 def test_no_host_is_observation_required(self): self.assertEqual(admit_capsule(CAP,host=None,claims=claims(),evidence=None,key=K,now_ms=1300)['disposition'],'HOST_OBSERVATION_REQUIRED')
 def test_ready_exact(self): self.assertTrue(admit_capsule(CAP,host=HOST,claims=claims(),evidence=ev(),key=K,now_ms=1300)['ready'])
 def test_bad_mac_holds(self):
  e=dataclasses.replace(ev(),mac_hex='0'*64);self.assertEqual(admit_capsule(CAP,host=HOST,claims=claims(),evidence=e,key=K,now_ms=1300)['disposition'],'HOLD_EVIDENCE_UNAUTHENTICATED')
 def test_host_incarnation_moves(self):
  h=dataclasses.replace(HOST,host_incarnation='inc2');self.assertEqual(admit_capsule(CAP,host=h,claims=claims(),evidence=ev(h),key=K,now_ms=1300)['disposition'],'HOLD_HOST_INCARNATION_MOVED')
 def test_base_moves(self):
  h=dataclasses.replace(HOST,installed_release_root='9'*64);self.assertEqual(admit_capsule(CAP,host=h,claims=claims(),evidence=ev(h),key=K,now_ms=1300)['disposition'],'HOLD_BASE_MOVED')
 def test_component_set_moves(self):
  h=dataclasses.replace(HOST,components=COMP[:-1]);self.assertEqual(admit_capsule(CAP,host=h,claims=claims(),evidence=ev(h),key=K,now_ms=1300)['disposition'],'HOLD_COMPONENT_SET_MOVED')
 def test_component_values_move(self):
  h=dataclasses.replace(HOST,components=(('consumer.py','1'*64),('guardian.ps1','2'*64),('terminal.py','a'*64)));self.assertEqual(admit_capsule(CAP,host=h,claims=claims(),evidence=ev(h),key=K,now_ms=1300)['disposition'],'HOLD_COMPONENT_VALUE_MOVED')
 def test_missing_proof_holds(self):
  c=claims()[:-1];self.assertEqual(admit_capsule(CAP,host=HOST,claims=c,evidence=ev(HOST,c),key=K,now_ms=1300)['disposition'],'HOLD_PROOF_SET_INCOMPLETE')
 def test_extra_proof_holds(self):
  c=claims()+(ProofClaim('EXTRA','a'*64,'HEAD22','PASS',1,0,'v','o'),);self.assertEqual(admit_capsule(CAP,host=HOST,claims=c,evidence=ev(HOST,c),key=K,now_ms=1300)['disposition'],'HOLD_PROOF_SET_INCOMPLETE')
 def test_skipped_required_holds(self):
  c=claims(skipped=1);self.assertEqual(admit_capsule(CAP,host=HOST,claims=c,evidence=ev(HOST,c),key=K,now_ms=1300)['disposition'],'HOLD_PROOF_VACUOUS')
 def test_zero_executed_holds(self):
  c=claims(executed=0);self.assertEqual(admit_capsule(CAP,host=HOST,claims=c,evidence=ev(HOST,c),key=K,now_ms=1300)['disposition'],'HOLD_PROOF_VACUOUS')
 def test_wrong_head_holds(self):
  c=claims(head='OTHER');self.assertEqual(admit_capsule(CAP,host=HOST,claims=c,evidence=ev(HOST,c),key=K,now_ms=1300)['disposition'],'HOLD_PROOF_NOT_EXACT_HEAD')
 def test_failed_proof_holds(self):
  c=claims(status='FAIL');self.assertEqual(admit_capsule(CAP,host=HOST,claims=c,evidence=ev(HOST,c),key=K,now_ms=1300)['disposition'],'HOLD_PROOF_FAILED')
 def test_stale_host_holds(self): self.assertEqual(admit_capsule(CAP,host=HOST,claims=claims(),evidence=ev(),key=K,now_ms=999999,max_host_age_ms=100)['disposition'],'HOLD_STALE_OBSERVATION')
 def test_deep_immutability_rejects_dict(self):
  with self.assertRaises(CapsuleError): DeploymentCapsule('x','r','h','1'*64,'2'*64,'i',{'x':'3'*64},REQ,'4'*64,'5'*64).validate()
 def test_canonical_pair_order_required(self):
  with self.assertRaises(CapsuleError): dataclasses.replace(CAP,expected_components=tuple(reversed(COMP))).validate()
 def test_prepare_root_exists(self):
  a=admit_capsule(CAP,host=HOST,claims=claims(),evidence=ev(),key=K,now_ms=1300)['o21_prepare_root'];self.assertEqual(len(a),64)
 def test_k27_not_in_identity(self): self.assertNotIn('k27',CAP.capsule_root)
 def test_operator_plan_has_accept_or_rollback(self): self.assertEqual(operator_plan(CAP)[-1],'ACCEPT_OR_EXACT_ROLLBACK')
if __name__=='__main__':unittest.main()
