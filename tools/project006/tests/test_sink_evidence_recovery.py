from dataclasses import replace
from hashlib import sha256
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from project006_sink_evidence_recovery import *


def r(s): return sha256(s.encode()).hexdigest()
SECRET=b'test-only-sink-verifier-secret'
ISSUER=r('sink-issuer'); VERIFIER=r('sink-verifier')

def base():
    op=OperationIdentity('cmd','op','idem',r('payload'),'file','rev1',r('src'),r('auth'),r('proof'),r('fence'))
    cur=CurrentOwnerContext(op,r('auth'),r('proof'),r('fence'))
    return op,cur

def ev(disposition=SinkDisposition.ACCEPTED, operation_id='op', secret=SECRET, expires_at=100):
    return sign_sink_evidence(secret=secret,operation_id=operation_id,disposition=disposition,
        sink_result_digest=r('sink-result'),issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=expires_at)

class T(unittest.TestCase):
    def d(self, **kw):
        op,cur=base(); args=dict(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=cur,
            capability=RecoveryCapability.NON_RETRYABLE,sink_evidence=None,secret=SECRET,
            expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20); args.update(kw); return decide_recovery(**args)
    def test_sink_accepted_consumes_without_replay(self): self.assertIs(self.d(sink_evidence=ev()).action, RecoveryAction.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY)
    def test_accepted_survives_later_auth_move(self):
        op,cur=base(); moved=replace(cur,authorization_root=r('moved')); self.assertIs(self.d(operation=op,current=moved,sink_evidence=ev()).action, RecoveryAction.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY)
    def test_not_accepted_needs_current_auth(self):
        op,cur=base(); moved=replace(cur,authorization_root=r('moved')); self.assertIs(self.d(operation=op,current=moved,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED)).action, RecoveryAction.HOLD_CURRENTNESS_MOVED)
    def test_not_accepted_idempotent_retry(self): self.assertIs(self.d(capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED)).action, RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID)
    def test_not_accepted_nonretryable_holds(self): self.assertIs(self.d(sink_evidence=ev(SinkDisposition.NOT_ACCEPTED)).action, RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY)
    def test_unknown_query_reconcile(self): self.assertIs(self.d(capability=RecoveryCapability.QUERY_RECONCILE,sink_evidence=ev(SinkDisposition.UNKNOWN)).action, RecoveryAction.QUERY_RECONCILE)
    def test_unknown_nonretryable_holds(self): self.assertIs(self.d(sink_evidence=ev(SinkDisposition.UNKNOWN)).action, RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY)
    def test_no_evidence_idempotent_retry(self): self.assertIs(self.d(capability=RecoveryCapability.IDEMPOTENT_RETRY).action, RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID)
    def test_no_evidence_query(self): self.assertIs(self.d(capability=RecoveryCapability.QUERY_RECONCILE).action, RecoveryAction.QUERY_RECONCILE)
    def test_bad_mac_holds(self):
        e=ev(); bad=replace(e,mac=r('forged')); self.assertIs(self.d(sink_evidence=bad).action, RecoveryAction.HOLD_INVALID_SINK_EVIDENCE)
    def test_wrong_operation_holds(self): self.assertIs(self.d(sink_evidence=ev(operation_id='other')).action, RecoveryAction.HOLD_INVALID_SINK_EVIDENCE)
    def test_expired_holds(self): self.assertIs(self.d(sink_evidence=ev(expires_at=15),now=20).action, RecoveryAction.HOLD_INVALID_SINK_EVIDENCE)
    def test_wrong_issuer_holds(self):
        e=sign_sink_evidence(secret=SECRET,operation_id='op',disposition=SinkDisposition.ACCEPTED,sink_result_digest=r('x'),issuer_root=r('other'),verifier_root=VERIFIER,observed_at=10,expires_at=100)
        self.assertIs(self.d(sink_evidence=e).action, RecoveryAction.HOLD_INVALID_SINK_EVIDENCE)
    def test_pre_effect_auth_move_holds(self):
        op,cur=base(); moved=replace(cur,authorization_root=r('moved')); self.assertIs(self.d(state=NativeState.ACK_WRITTEN_PRE_EFFECT,operation=op,current=moved).action, RecoveryAction.HOLD_CURRENTNESS_MOVED)
    def test_pre_effect_current_starts_once(self): self.assertIs(self.d(state=NativeState.ACK_WRITTEN_PRE_EFFECT).action, RecoveryAction.START_PROVIDER_ONCE)
    def test_result_observed_only_retries_return(self):
        op,cur=base(); moved=replace(cur,authorization_root=r('moved')); self.assertIs(self.d(state=NativeState.RESULT_OBSERVED,operation=op,current=moved).action, RecoveryAction.RETRY_RETURN_WRITER_ONLY)
    def test_error_terminal_only_retries_return(self): self.assertIs(self.d(state=NativeState.ERROR_TERMINAL).action, RecoveryAction.RETRY_RETURN_WRITER_ONLY)
    def test_return_written_done(self): self.assertIs(self.d(state=NativeState.RETURN_WRITTEN).action, RecoveryAction.DONE)
    def test_payload_move_holds_ambiguous(self):
        op,cur=base(); movedop=replace(cur.operation,payload_digest=r('moved')); moved=replace(cur,operation=movedop); self.assertIs(self.d(operation=op,current=moved,capability=RecoveryCapability.IDEMPOTENT_RETRY).action, RecoveryAction.HOLD_CURRENTNESS_MOVED)
    def test_never_mints_authority(self):
        d=self.d(sink_evidence=ev()); self.assertFalse(d.authority_minted); self.assertFalse(d.effect_authority); self.assertFalse(d.gate10)

if __name__=='__main__': unittest.main()
