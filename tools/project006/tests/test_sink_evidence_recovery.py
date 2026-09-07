from dataclasses import replace
from hashlib import sha256
import os,sys,unittest
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from project006_sink_evidence_recovery import *
def r(s): return sha256(s.encode()).hexdigest()
SECRET=b'test-only-sink-verifier-secret'; ISSUER=r('sink-issuer'); VERIFIER=r('sink-verifier')
def base():
 op=OperationIdentity('cmd','op','idem',r('payload'),'file','rev1',r('src'),r('auth'),r('proof'),r('fence')); return op,CurrentOwnerContext(op,r('auth'),r('proof'),r('fence'))
def ev(d=SinkDisposition.ACCEPTED,*,result=True,gen=3,op='op',secret=SECRET,expires=100): return sign_sink_evidence(secret=secret,operation_id=op,disposition=d,sink_result_digest=r('result'),result_locator_root=r('locator') if result else None,issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=expires,sink_fence_generation=gen)
def fence(gen=4,installed=4): return SinkFenceContext(gen,installed,r(f'fence-receipt-{gen}-{installed}'))
class T(unittest.TestCase):
 def d(self,**kw):
  op,cur=base(); a=dict(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=cur,capability=RecoveryCapability.NON_RETRYABLE,sink_evidence=None,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20,sink_fence=None); a.update(kw); return decide_recovery(**a)
 def test_accepted_recoverable_consumes(self): self.assertIs(self.d(sink_evidence=ev()).action,RecoveryAction.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY)
 def test_accepted_without_result_holds(self): self.assertEqual(self.d(sink_evidence=ev(result=False)).reason,'ACCEPTED_RESULT_UNAVAILABLE')
 def test_accepted_never_replays_after_auth_move(self):
  op,cur=base(); self.assertIs(self.d(operation=op,current=replace(cur,authorization_root=r('moved')),sink_evidence=ev()).action,RecoveryAction.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY)
 def test_notaccepted_requires_new_installed_fence(self): self.assertEqual(self.d(capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED)).reason,'OLD_INFLIGHT_REQUEST_NOT_FENCED')
 def test_notaccepted_equal_fence_holds(self): self.assertEqual(self.d(capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED),sink_fence=fence(3,3)).reason,'OLD_INFLIGHT_REQUEST_NOT_FENCED')
 def test_notaccepted_uninstalled_new_fence_holds(self): self.assertEqual(self.d(capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED),sink_fence=fence(4,3)).reason,'OLD_INFLIGHT_REQUEST_NOT_FENCED')
 def test_notaccepted_new_installed_fence_retries(self): self.assertIs(self.d(capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED),sink_fence=fence()).action,RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID)
 def test_notaccepted_new_fence_still_needs_current_auth(self):
  op,cur=base(); self.assertIs(self.d(operation=op,current=replace(cur,authorization_root=r('moved')),capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED),sink_fence=fence()).action,RecoveryAction.HOLD_CURRENTNESS_MOVED)
 def test_verified_unknown_holds(self): self.assertEqual(self.d(capability=RecoveryCapability.QUERY_RECONCILE,sink_evidence=ev(SinkDisposition.UNKNOWN)).reason,'SINK_STATUS_UNKNOWN')
 def test_no_status_query_cap_queries(self): self.assertIs(self.d(capability=RecoveryCapability.QUERY_RECONCILE).action,RecoveryAction.QUERY_RECONCILE)
 def test_no_evidence_idempotent_contract_may_retry(self): self.assertIs(self.d(capability=RecoveryCapability.IDEMPOTENT_RETRY).action,RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID)
 def test_bad_mac_holds(self): self.assertIs(self.d(sink_evidence=replace(ev(),mac=r('bad'))).action,RecoveryAction.HOLD_INVALID_SINK_EVIDENCE)
 def test_wrong_operation_holds(self): self.assertIs(self.d(sink_evidence=ev(op='other')).action,RecoveryAction.HOLD_INVALID_SINK_EVIDENCE)
 def test_expired_holds(self): self.assertIs(self.d(sink_evidence=ev(expires=15)).action,RecoveryAction.HOLD_INVALID_SINK_EVIDENCE)
 def test_pre_effect_current_starts_once(self): self.assertIs(self.d(state=NativeState.ACK_WRITTEN_PRE_EFFECT).action,RecoveryAction.START_PROVIDER_ONCE)
 def test_pre_effect_auth_move_holds(self):
  op,cur=base(); self.assertIs(self.d(state=NativeState.ACK_WRITTEN_PRE_EFFECT,operation=op,current=replace(cur,authorization_root=r('m'))).action,RecoveryAction.HOLD_CURRENTNESS_MOVED)
 def test_result_observed_return_only_despite_drift(self):
  op,cur=base(); self.assertIs(self.d(state=NativeState.RESULT_OBSERVED,operation=op,current=replace(cur,authorization_root=r('m'))).action,RecoveryAction.RETRY_RETURN_WRITER_ONLY)
 def test_error_terminal_return_only(self): self.assertIs(self.d(state=NativeState.ERROR_TERMINAL).action,RecoveryAction.RETRY_RETURN_WRITER_ONLY)
 def test_return_written_done(self): self.assertIs(self.d(state=NativeState.RETURN_WRITTEN).action,RecoveryAction.DONE)
 def test_payload_move_blocks_notaccepted_retry(self):
  op,cur=base(); moved=replace(cur,operation=replace(cur.operation,payload_digest=r('m'))); self.assertIs(self.d(operation=op,current=moved,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED),sink_fence=fence()).action,RecoveryAction.HOLD_CURRENTNESS_MOVED)
 def test_never_mints_authority(self):
  d=self.d(sink_evidence=ev()); self.assertFalse(d.authority_minted or d.effect_authority or d.gate10)
if __name__=='__main__': unittest.main()
