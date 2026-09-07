from dataclasses import replace
from hashlib import sha256
import json, random
from project006_sink_evidence_recovery import *

R=lambda s: sha256(s.encode()).hexdigest()
SECRET=b'test-only-sink-verifier-secret'; ISSUER=R('sink-issuer'); VERIFIER=R('sink-verifier')

def make(seed_i):
    op=OperationIdentity(f'cmd{seed_i}',f'op{seed_i}',f'idem{seed_i}',R(f'payload{seed_i}'),f'file{seed_i}',f'rev{seed_i%7}',R(f'src{seed_i}'),R(f'auth{seed_i}'),R(f'proof{seed_i%3}'),R(f'fence{seed_i%5}'))
    return op, CurrentOwnerContext(op,op.authorization_root,op.proof_semantics_root,op.fence_root)

def oracle(state,op,cur,cap,evidence,now):
    terminal = state in (NativeState.RESULT_OBSERVED, NativeState.ERROR_TERMINAL)
    if state is NativeState.RETURN_WRITTEN: return RecoveryAction.DONE
    if terminal: return RecoveryAction.RETRY_RETURN_WRITER_ONLY
    same=(cur.operation==op and cur.authorization_root==op.authorization_root and cur.proof_semantics_root==op.proof_semantics_root and cur.fence_root==op.fence_root)
    if state is NativeState.ACK_WRITTEN_PRE_EFFECT:
        return RecoveryAction.START_PROVIDER_ONCE if same else RecoveryAction.HOLD_CURRENTNESS_MOVED
    if state is not NativeState.COMPLETION_AMBIGUOUS: return RecoveryAction.HOLD_UNSUPPORTED_STATE
    valid=False
    if evidence is not None:
        expected=hmac.new(SECRET,json.dumps(evidence.unsigned_payload(),sort_keys=True,separators=(',',':')).encode(),sha256).hexdigest()
        valid=(evidence.operation_id==op.operation_id and evidence.issuer_root==ISSUER and evidence.verifier_root==VERIFIER and now<=evidence.expires_at and hmac.compare_digest(expected,evidence.mac))
        if not valid: return RecoveryAction.HOLD_INVALID_SINK_EVIDENCE
        if evidence.disposition is SinkDisposition.ACCEPTED: return RecoveryAction.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY
        if evidence.disposition is SinkDisposition.NOT_ACCEPTED:
            if not same: return RecoveryAction.HOLD_CURRENTNESS_MOVED
            return RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID if cap is RecoveryCapability.IDEMPOTENT_RETRY else RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY
    if not same: return RecoveryAction.HOLD_CURRENTNESS_MOVED
    if cap is RecoveryCapability.IDEMPOTENT_RETRY: return RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID
    if cap is RecoveryCapability.QUERY_RECONCILE: return RecoveryAction.QUERY_RECONCILE
    return RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY

import hmac

def run(cases=20000):
    rng=random.Random(20260907)
    counts={'cases':cases,'oracle_mismatches':0,'unsafe_naive_replays':0,'accepted_provider_replays':0,'authority_minted':0}
    actions={}
    states=list(NativeState); caps=list(RecoveryCapability)
    for i in range(cases):
        op,cur=make(i); state=rng.choice(states); cap=rng.choice(caps); now=50; evidence=None
        mode=rng.randrange(12)
        if mode in (0,1,2,3):
            disp=[SinkDisposition.ACCEPTED,SinkDisposition.NOT_ACCEPTED,SinkDisposition.UNKNOWN][mode%3]
            evidence=sign_sink_evidence(secret=SECRET,operation_id=op.operation_id,disposition=disp,sink_result_digest=R(f'res{i}'),issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=100)
        elif mode==4:
            evidence=sign_sink_evidence(secret=SECRET,operation_id='wrong',disposition=SinkDisposition.ACCEPTED,sink_result_digest=R('x'),issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=100)
        elif mode==5:
            e=sign_sink_evidence(secret=SECRET,operation_id=op.operation_id,disposition=SinkDisposition.ACCEPTED,sink_result_digest=R('x'),issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=100); evidence=replace(e,mac=R('bad'))
        if mode in (6,7): cur=replace(cur,authorization_root=R('moved'+str(i)))
        elif mode==8: cur=replace(cur,operation=replace(cur.operation,payload_digest=R('movedpayload'+str(i))))
        elif mode==9: cur=replace(cur,proof_semantics_root=R('movedproof'+str(i)))
        elif mode==10: cur=replace(cur,fence_root=R('movedfence'+str(i)))
        d=decide_recovery(state=state,operation=op,current=cur,capability=cap,sink_evidence=evidence,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=now)
        o=oracle(state,op,cur,cap,evidence,now)
        counts['oracle_mismatches'] += int(d.action is not o)
        counts['authority_minted'] += int(d.authority_minted or d.effect_authority or d.gate10)
        actions[d.action.value]=actions.get(d.action.value,0)+1
        if state is NativeState.COMPLETION_AMBIGUOUS and evidence is not None and evidence.disposition is SinkDisposition.ACCEPTED:
            counts['accepted_provider_replays'] += int(d.action in (RecoveryAction.START_PROVIDER_ONCE,RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID))
        if state is NativeState.COMPLETION_AMBIGUOUS and o not in (RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID,):
            counts['unsafe_naive_replays'] += 1
    counts['actions']=dict(sorted(actions.items()))
    raw=json.dumps(counts,sort_keys=True,separators=(',',':')).encode(); counts['campaign_root']=sha256(raw).hexdigest()
    if counts['oracle_mismatches'] or counts['accepted_provider_replays'] or counts['authority_minted']: raise AssertionError(counts)
    return counts

if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
