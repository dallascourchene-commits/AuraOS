import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"/"arena"))
import unittest
from hashlib import sha256
from effect_return_atomicity import *

def hx(s): return sha256(s.encode()).hexdigest()

def fixture(mode=RecoveryMode.IDEMPOTENT_RETRY, admitted=True):
    contract=EffectContract(mode,hx('cap'),'EMAIL_SEND')
    intent=EffectIntent('cmd-1','idem-1',hx('source'),hx('tecc-auth'),hx('payload'),'EMAIL_SEND')
    state=compile_initial_state(intent,contract,admitted=admitted,terminal_class='COMMAND_BLOCKED')
    ctx=RecoveryContext(intent.identity_root,contract.contract_root,contract.capability_receipt_root,intent.idempotency_key,intent.effect_payload_root,True,True)
    return intent,contract,state,ctx

class ERACFocused(unittest.TestCase):
    def test_negative_decision_returns(self):
        i,c,s,x=fixture(admitted=False); self.assertEqual(decide_recovery(s,i,c,x).action,Action.WRITE_TERMINAL_RETURN)
    def test_admitted_writes_ack_first(self):
        i,c,s,x=fixture(); self.assertEqual(decide_recovery(s,i,c,x).action,Action.WRITE_ACK_PRE_EFFECT)
    def test_ack_allows_first_call(self):
        i,c,s,x=fixture(); s=DurableEffectState(Phase.ACK_WRITTEN_PRE_EFFECT,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,ack_receipt_root=hx('ack'))
        d=decide_recovery(s,i,c,x); self.assertEqual(d.action,Action.CALL_PROVIDER_FIRST_TIME); self.assertEqual(d.provider_request_delta,1)
    def test_idempotent_ambiguous_retries_exact(self):
        i,c,s,x=fixture(); s=DurableEffectState(Phase.COMPLETION_AMBIGUOUS,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,1,hx('ack'),hx('attempt'))
        self.assertEqual(decide_recovery(s,i,c,x).action,Action.RETRY_EXACT_SAME_EFFECT)
    def test_queryable_ambiguous_queries(self):
        i,c,s,x=fixture(RecoveryMode.QUERY_RECONCILE); s=DurableEffectState(Phase.COMPLETION_AMBIGUOUS,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,1,hx('ack'),hx('attempt'))
        self.assertEqual(decide_recovery(s,i,c,x).action,Action.QUERY_PROVIDER_STATUS)
    def test_nonretryable_ambiguous_holds(self):
        i,c,s,x=fixture(RecoveryMode.NON_RETRYABLE); s=DurableEffectState(Phase.COMPLETION_AMBIGUOUS,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,1,hx('ack'),hx('attempt'))
        self.assertEqual(decide_recovery(s,i,c,x).action,Action.HOLD_COMPLETION_AMBIGUOUS)
    def test_result_never_recalls_provider(self):
        i,c,s,x=fixture(); s=DurableEffectState(Phase.RESULT_OBSERVED,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,1,hx('ack'),hx('attempt'),result_root=hx('result'))
        d=decide_recovery(s,i,c,x); self.assertEqual(d.action,Action.RETRY_RETURN_WRITER_ONLY); self.assertEqual(d.provider_request_delta,0)
    def test_return_written_terminal(self):
        i,c,s,x=fixture(); s=DurableEffectState(Phase.RETURN_WRITTEN,s.intent_root,s.idempotency_key,s.effect_payload_root,s.contract_root,1,hx('ack'),hx('attempt'),result_root=hx('result'),return_receipt_root=hx('return'))
        self.assertEqual(decide_recovery(s,i,c,x).action,Action.NOOP_TERMINAL)
    def test_same_key_different_payload_holds(self):
        i,c,s,x=fixture(); x=RecoveryContext(x.current_intent_root,x.current_contract_root,x.current_capability_receipt_root,x.observed_idempotency_key,hx('other-payload'),True,True)
        self.assertEqual(decide_recovery(s,i,c,x).action,Action.HOLD_IDEMPOTENCY_CONFLICT)
    def test_capability_movement_rebinds(self):
        i,c,s,x=fixture(); x=RecoveryContext(x.current_intent_root,x.current_contract_root,hx('newcap'),x.observed_idempotency_key,x.observed_effect_payload_root,True,True)
        self.assertEqual(decide_recovery(s,i,c,x).action,Action.HOLD_REBIND_REQUIRED)
    def test_auth_movement_rebinds(self):
        i,c,s,x=fixture(); x=RecoveryContext(x.current_intent_root,x.current_contract_root,x.current_capability_receipt_root,x.observed_idempotency_key,x.observed_effect_payload_root,True,False)
        self.assertEqual(decide_recovery(s,i,c,x).action,Action.HOLD_REBIND_REQUIRED)
    def test_intent_movement_rebinds(self):
        i,c,s,x=fixture(); x=RecoveryContext(hx('newintent'),x.current_contract_root,x.current_capability_receipt_root,x.observed_idempotency_key,x.observed_effect_payload_root,True,True)
        self.assertEqual(decide_recovery(s,i,c,x).action,Action.HOLD_REBIND_REQUIRED)
    def test_d0_never_mints_authority(self):
        i,c,s,x=fixture(); d=decide_recovery(s,i,c,x); self.assertFalse(d.effect_authority_minted); self.assertFalse(d.gate10)
    def test_effect_attempt_root_binds_payload_and_key(self):
        i,c,_,_=fixture(); r1=effect_attempt_root(i,c,0); i2=EffectIntent(i.command_id,i.idempotency_key,i.source_root,i.tecc_authorization_root,hx('p2'),i.effect_type); self.assertNotEqual(r1,effect_attempt_root(i2,c,0))
    def test_context_axes_cannot_repair_hard_invalid(self):
        self.assertEqual(hard13d_erac((0,2,2,2,2,2,2,2,2,2,2,2,2)),'HOLD_HARD_INVALID')
        self.assertEqual(hard13d_erac((2,2,2,2,2,2,2,2,0,0,0,0,0)),'READY_RECOVERY_ACTION_D0')

if __name__=='__main__': unittest.main()
