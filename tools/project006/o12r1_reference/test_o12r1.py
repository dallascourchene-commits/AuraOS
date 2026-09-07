import unittest
from dataclasses import replace
from hashlib import sha256
from o12r1_recovery import *
R=lambda s:sha256(s.encode()).hexdigest()
CS=b'current-secret'; SS=b'sink-secret'; FS=b'fence-secret'
CO=R('current-owner'); CV=R('current-verifier'); SI=R('sink-issuer'); SV=R('sink-verifier'); FO=R('fence-owner'); FV=R('fence-verifier')
class J:
    def __init__(self,row):self.row=dict(row)
    def status(self,c):
        if c!=self.row['command_id']:raise ValueError('missing')
        return dict(self.row)
def base(phase='COMPLETION_AMBIGUOUS'):
    row={'command_id':'cmd','idempotency_key':'idem','source_digest':R('src'),'intent_root':R('intent'),'contract_root':R('contract'),'effect_payload_root':R('payload'),'phase':phase,'provider_request_count':1,'effect_attempt_root':R('attempt'),'provider_operation_root':R('provider-op'),'result_root':None}
    return row
def owner(row=None,**kw):
    row=row or base(); p=dict(secret=CS,operation_id='op',resource_root=R('resource'),intent_root=row['intent_root'],contract_root=row['contract_root'],source_digest=row['source_digest'],idempotency_key=row['idempotency_key'],effect_payload_root=row['effect_payload_root'],authorization_root=R('auth'),proof_semantics_root=R('proof'),owner_generation=7,owner_root=CO,verifier_root=CV,observed_at=10,expires_at=100);p.update(kw);return sign_owner(**p)
def ev(row=None,d=SinkDisposition.NOT_ACCEPTED,result=None,fg=3,**kw):
    row=row or base();p=dict(secret=SS,operation_id='op',effect_attempt_root=row['effect_attempt_root'],provider_operation_root=row['provider_operation_root'],disposition=d,sink_result_digest=R('sink-result'),result_locator_root=result,fence_generation=fg,issuer_root=SI,verifier_root=SV,observed_at=10,expires_at=100);p.update(kw);return sign_sink(**p)
def fr(row=None,**kw):
    row=row or base();p=dict(secret=FS,operation_id='op',resource_root=R('resource'),fenced_attempt_root=row['effect_attempt_root'],previous_generation=3,generation=4,installed_generation=4,owner_root=FO,verifier_root=FV,owner_generation=9,observed_at=11,expires_at=100);p.update(kw);return sign_fence(**p)
def dec(row=None,mode=RecoveryMode.IDEMPOTENT_RETRY,o=None,e=None,f=None,now=20,**kw):
    row=row or base();o=owner(row) if o is None else o
    p=dict(journal=J(row),command_id='cmd',recovery_mode=mode,current_receipt=o,current_secret=CS,current_operation_id='op',current_resource_root=R('resource'),current_owner_root=CO,current_verifier_root=CV,current_owner_generation=7,sink_evidence=e,sink_secret=SS,sink_issuer_root=SI,sink_verifier_root=SV,fence_receipt=f,fence_secret=FS,fence_owner_root=FO,fence_verifier_root=FV,fence_owner_generation=9,now=now);p.update(kw);return decide_from_owner(**p)
class T(unittest.TestCase):
    def test_idempotent_no_status_retry(self):self.assertIs(dec().action,Action.RETRY_EXACT_SAME_EFFECT)
    def test_query_no_status(self):self.assertIs(dec(mode=RecoveryMode.QUERY_RECONCILE).action,Action.QUERY_PROVIDER_STATUS)
    def test_nonretry_no_status(self):self.assertIs(dec(mode=RecoveryMode.NON_RETRYABLE).action,Action.HOLD_AMBIGUOUS)
    def test_missing_current_owner(self):self.assertIs(dec(o=False).action,Action.HOLD_REBIND_REQUIRED)
    def test_forged_current_mac(self):self.assertIs(dec(o=replace(owner(),mac=R('bad'))).action,Action.HOLD_REBIND_REQUIRED)
    def test_wrong_current_owner(self):self.assertIs(dec(o=owner(owner_root=R('attacker'))).action,Action.HOLD_REBIND_REQUIRED)
    def test_wrong_current_generation(self):self.assertIs(dec(o=owner(owner_generation=8)).action,Action.HOLD_REBIND_REQUIRED)
    def test_expired_current(self):self.assertIs(dec(o=owner(expires_at=15),now=20).action,Action.HOLD_REBIND_REQUIRED)
    def test_current_source_drift(self):self.assertIs(dec(o=owner(source_digest=R('other'))).action,Action.HOLD_REBIND_REQUIRED)
    def test_current_payload_drift(self):self.assertIs(dec(o=owner(effect_payload_root=R('other'))).action,Action.HOLD_REBIND_REQUIRED)
    def test_current_intent_drift(self):self.assertIs(dec(o=owner(intent_root=R('other'))).action,Action.HOLD_REBIND_REQUIRED)
    def test_accepted_result(self):self.assertIs(dec(e=ev(d=SinkDisposition.ACCEPTED,result=R('locator'))).action,Action.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY)
    def test_accepted_missing_result(self):self.assertIs(dec(e=ev(d=SinkDisposition.ACCEPTED)).action,Action.HOLD_AMBIGUOUS)
    def test_unknown_holds(self):self.assertIs(dec(e=ev(d=SinkDisposition.UNKNOWN)).action,Action.HOLD_AMBIGUOUS)
    def test_wrong_sink_attempt(self):self.assertIs(dec(e=ev(effect_attempt_root=R('other'))).action,Action.HOLD_INVALID_EVIDENCE)
    def test_wrong_provider_operation(self):self.assertIs(dec(e=ev(provider_operation_root=R('other'))).action,Action.HOLD_INVALID_EVIDENCE)
    def test_forged_sink_mac(self):self.assertIs(dec(e=replace(ev(),mac=R('bad'))).action,Action.HOLD_INVALID_EVIDENCE)
    def test_notaccepted_needs_fence(self):self.assertIs(dec(e=ev()).action,Action.HOLD_AMBIGUOUS)
    def test_notaccepted_valid_fence(self):self.assertIs(dec(e=ev(),f=fr()).action,Action.RETRY_EXACT_SAME_EFFECT)
    def test_forged_fence_owner(self):self.assertIs(dec(e=ev(),f=fr(owner_root=R('attacker'))).action,Action.HOLD_INVALID_EVIDENCE)
    def test_forged_fence_mac(self):self.assertIs(dec(e=ev(),f=replace(fr(),mac=R('bad'))).action,Action.HOLD_INVALID_EVIDENCE)
    def test_wrong_fence_attempt(self):self.assertIs(dec(e=ev(),f=fr(fenced_attempt_root=R('other'))).action,Action.HOLD_INVALID_EVIDENCE)
    def test_uninstalled_fence(self):self.assertIs(dec(e=ev(),f=fr(installed_generation=3)).action,Action.HOLD_INVALID_EVIDENCE)
    def test_stale_fence_owner_generation(self):self.assertIs(dec(e=ev(),f=fr(owner_generation=8)).action,Action.HOLD_INVALID_EVIDENCE)
    def test_terminal_result_return_only(self):self.assertIs(dec(row=base('RESULT_OBSERVED')).action,Action.RETRY_RETURN_WRITER_ONLY)
    def test_done(self):self.assertIs(dec(row=base('RETURN_WRITTEN')).action,Action.DONE)
    def test_unsupported_pre_effect(self):self.assertIs(dec(row=base('ACK_WRITTEN_PRE_EFFECT')).action,Action.HOLD_UNSUPPORTED)
    def test_final_result_allowed(self):self.assertIs(guard_final_projection(journal=J(base('RESULT_OBSERVED')),command_id='cmd',recovery_mode=RecoveryMode.IDEMPOTENT_RETRY).action,FinalAction.STAGE_FINAL_RETURN)
    def test_final_retryable_ambiguity_blocked(self):self.assertIs(guard_final_projection(journal=J(base()),command_id='cmd',recovery_mode=RecoveryMode.IDEMPOTENT_RETRY).action,FinalAction.HOLD_RECOVERY_REQUIRED)
    def test_final_queryable_ambiguity_blocked(self):self.assertIs(guard_final_projection(journal=J(base()),command_id='cmd',recovery_mode=RecoveryMode.QUERY_RECONCILE).action,FinalAction.HOLD_RECOVERY_REQUIRED)
    def test_final_nonretry_ambiguity_allowed(self):self.assertIs(guard_final_projection(journal=J(base()),command_id='cmd',recovery_mode=RecoveryMode.NON_RETRYABLE).action,FinalAction.STAGE_FINAL_RETURN)
if __name__=='__main__':unittest.main()
