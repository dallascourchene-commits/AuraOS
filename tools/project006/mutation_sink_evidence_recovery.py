from dataclasses import replace
from hashlib import sha256
from project006_sink_evidence_recovery import *
R=lambda s: sha256(s.encode()).hexdigest(); SECRET=b'test-only-sink-verifier-secret'; ISSUER=R('sink-issuer'); VERIFIER=R('sink-verifier')
def base():
    op=OperationIdentity('cmd','op','idem',R('payload'),'file','rev',R('src'),R('auth'),R('proof'),R('fence')); return op,CurrentOwnerContext(op,R('auth'),R('proof'),R('fence'))
def ev(d): return sign_sink_evidence(secret=SECRET,operation_id='op',disposition=d,sink_result_digest=R('res'),issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=100)
def run():
    op,cur=base(); killed={}
    expected=decide_recovery(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=cur,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.ACCEPTED),secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20).action
    killed['accepted_to_replay']= expected is not RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID
    moved=replace(cur,authorization_root=R('moved')); expected=decide_recovery(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=moved,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev(SinkDisposition.NOT_ACCEPTED),secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20).action
    killed['not_accepted_bypasses_auth']= expected is RecoveryAction.HOLD_CURRENTNESS_MOVED
    bad=replace(ev(SinkDisposition.ACCEPTED),mac=R('bad')); expected=decide_recovery(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=cur,capability=RecoveryCapability.NON_RETRYABLE,sink_evidence=bad,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20).action
    killed['forged_sink_accepted']= expected is RecoveryAction.HOLD_INVALID_SINK_EVIDENCE
    expected=decide_recovery(state=NativeState.RESULT_OBSERVED,operation=op,current=moved,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=None,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20).action
    killed['terminal_result_erased_by_currentness']= expected is RecoveryAction.RETRY_RETURN_WRITER_ONLY
    return {'mutants':len(killed),'killed':sum(killed.values()),'details':killed}
if __name__=='__main__': import json; print(json.dumps(run(),sort_keys=True,indent=2))
