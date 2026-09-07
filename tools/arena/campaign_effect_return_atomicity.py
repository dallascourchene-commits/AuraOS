from hashlib import sha256
import json
from effect_return_atomicity import *

def hx(s): return sha256(s.encode()).hexdigest()

def make(mode=RecoveryMode.IDEMPOTENT_RETRY, admitted=True):
    c=EffectContract(mode,hx('cap'),'EMAIL_SEND')
    i=EffectIntent('cmd','idem',hx('source'),hx('tecc'),hx('payload'),'EMAIL_SEND')
    s=compile_initial_state(i,c,admitted=admitted,terminal_class='COMMAND_BLOCKED')
    x=RecoveryContext(i.identity_root,c.contract_root,c.capability_receipt_root,i.idempotency_key,i.effect_payload_root,True,True)
    return i,c,s,x

def scenario(idx):
    k=idx%12
    mode=(RecoveryMode.IDEMPOTENT_RETRY,RecoveryMode.QUERY_RECONCILE,RecoveryMode.NON_RETRYABLE)[(idx//12)%3]
    i,c,s,x=make(mode)
    if k==0: s=compile_initial_state(i,c,admitted=False,terminal_class='AUTHORITY_REJECTED'); expect=Action.WRITE_TERMINAL_RETURN
    elif k==1: expect=Action.WRITE_ACK_PRE_EFFECT
    elif k==2: s=DurableEffectState(Phase.ACK_WRITTEN_PRE_EFFECT,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,ack_receipt_root=hx('ack')); expect=Action.CALL_PROVIDER_FIRST_TIME
    elif k==3:
        s=DurableEffectState(Phase.COMPLETION_AMBIGUOUS,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,1,hx('ack'),hx('attempt'))
        expect={RecoveryMode.IDEMPOTENT_RETRY:Action.RETRY_EXACT_SAME_EFFECT,RecoveryMode.QUERY_RECONCILE:Action.QUERY_PROVIDER_STATUS,RecoveryMode.NON_RETRYABLE:Action.HOLD_COMPLETION_AMBIGUOUS}[mode]
    elif k==4: s=DurableEffectState(Phase.RESULT_OBSERVED,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,1,hx('ack'),hx('attempt'),result_root=hx('r')); expect=Action.RETRY_RETURN_WRITER_ONLY
    elif k==5: s=DurableEffectState(Phase.RETURN_WRITTEN,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,1,hx('ack'),hx('attempt'),result_root=hx('r'),return_receipt_root=hx('ret')); expect=Action.NOOP_TERMINAL
    elif k==6: x=RecoveryContext(hx('other'),x.current_contract_root,x.current_capability_receipt_root,x.observed_idempotency_key,x.observed_effect_payload_root,True,True); expect=Action.HOLD_REBIND_REQUIRED
    elif k==7: x=RecoveryContext(x.current_intent_root,x.current_contract_root,hx('othercap'),x.observed_idempotency_key,x.observed_effect_payload_root,True,True); expect=Action.HOLD_REBIND_REQUIRED
    elif k==8: x=RecoveryContext(x.current_intent_root,x.current_contract_root,x.current_capability_receipt_root,x.observed_idempotency_key,hx('otherpayload'),True,True); expect=Action.HOLD_IDEMPOTENCY_CONFLICT
    elif k==9: x=RecoveryContext(x.current_intent_root,x.current_contract_root,x.current_capability_receipt_root,'other-key',x.observed_effect_payload_root,True,True); expect=Action.HOLD_IDEMPOTENCY_CONFLICT
    elif k==10: x=RecoveryContext(x.current_intent_root,x.current_contract_root,x.current_capability_receipt_root,x.observed_idempotency_key,x.observed_effect_payload_root,False,True); expect=Action.HOLD_REBIND_REQUIRED
    else: x=RecoveryContext(x.current_intent_root,x.current_contract_root,x.current_capability_receipt_root,x.observed_idempotency_key,x.observed_effect_payload_root,True,False); expect=Action.HOLD_REBIND_REQUIRED
    return i,c,s,x,expect

def run(n=24000):
    false_ready=false_hold=mismatch=0
    naive_blind_resend=0
    counts={}
    for idx in range(n):
        i,c,s,x,expect=scenario(idx)
        got=decide_recovery(s,i,c,x).action
        counts[got.value]=counts.get(got.value,0)+1
        if got is not expect: mismatch+=1
        if s.phase in (Phase.EFFECT_ATTEMPT_DURABLE,Phase.COMPLETION_AMBIGUOUS) and c.recovery_mode is RecoveryMode.NON_RETRYABLE:
            naive_blind_resend+=1
        safe_exec={Action.CALL_PROVIDER_FIRST_TIME,Action.RETRY_EXACT_SAME_EFFECT}
        if got in safe_exec and expect not in safe_exec: false_ready+=1
        if got not in safe_exec and expect in safe_exec: false_hold+=1
    payload={'schema':'ERAC-CAMPAIGN-v1','cases':n,'mismatch':mismatch,'false_ready':false_ready,'false_hold':false_hold,
             'naive_nonretryable_blind_resends':naive_blind_resend,'counts':dict(sorted(counts.items()))}
    payload['campaign_root']=digest(payload)
    return payload

if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(',',':')))
