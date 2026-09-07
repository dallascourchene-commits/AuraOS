import dataclasses
import tempfile
import unittest
from pathlib import Path

from tools.arena.effect_return_atomicity import (
    Action, EffectContract, EffectIntent, RecoveryContext, RecoveryMode, effect_attempt_root,
)
from tools.project006.consumer_admitted_currentness import (
    CanonicalConsumerAdmissionResolver, CanonicalConsumerCut, EXPECTED_REPROOF_SEMANTICS,
    build_canonical_effect_attempt_journal, digest, sign_consumer_admission,
)
from tools.project006.effect_attempt_recovery import EffectAttemptJournal
from tools.project006.terminal_outbox import CommandIdentity, OutboxJournal


def r(s): return digest(s)

class O12R2Integration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); base=Path(self.tmp.name)
        self.journal_path=base/'effect.db'; self.outbox_path=base/'outbox.db'
        self.secret=b'o12r2-hosted-secret'; self.now=1000
        self.ident=CommandIdentity('cmd-1','idem-1','file-1','rev-1',r('source'))
        self.intent=EffectIntent('cmd-1','idem-1',r('source'),r('auth'),r('payload'),'SEND')
        self.contract=EffectContract(RecoveryMode.IDEMPOTENT_RETRY,r('capability'),'SEND')
        self.context=RecoveryContext(self.intent.identity_root,self.contract.contract_root,
            self.contract.capability_receipt_root,self.intent.idempotency_key,self.intent.effect_payload_root)
    def tearDown(self): self.tmp.cleanup()

    def admission(self,generation=7,currentness='current-7',**changes):
        d=dict(secret=self.secret,command_id=self.intent.command_id,intent_root=self.intent.identity_root,
            contract_root=self.contract.contract_root,source_root=self.intent.source_root,
            authorization_root=self.intent.tecc_authorization_root,consumer_generation=generation,
            currentness_root=r(currentness),verifier_instance='tecc-consumer',producer_lineage_root=r('producer'),
            observer_lineage_root=r('observer-lineage'),observer_receipt_root=r('observer-receipt'),
            proof_semantics_id=EXPECTED_REPROOF_SEMANTICS,source_owner_id='source-owner',
            authorization_owner_id='auth-owner',observer_id='observer',issued_at=900,expires_at=1100)
        d.update(changes); return sign_consumer_admission(**d)
    def cut(self,generation=7,currentness='current-7'):
        return CanonicalConsumerCut(generation,r(currentness),'tecc-consumer','source-owner','auth-owner')
    def resolver(self,admission,generation=7,currentness='current-7'):
        return CanonicalConsumerAdmissionResolver(secret=self.secret,cut=self.cut(generation,currentness),
            admission_provider=lambda *_: admission,now_provider=lambda:self.now)

    def prepared(self):
        a=self.admission(); j=build_canonical_effect_attempt_journal(self.journal_path,secret=self.secret,cut=self.cut(),
            admission_provider=lambda *_: a,now_provider=lambda:self.now)
        j.bind_admitted(self.ident,self.intent,self.contract)
        j.publish_ack(self.ident,self.intent,self.contract,lambda _: 'ack-ref')
        return j,a

    def test_first_provider_attempt_binds_exact_canonical_admission(self):
        j,a=self.prepared(); p=j.decide_and_persist(self.ident,self.intent,self.contract,self.context)
        self.assertEqual(p.action,Action.CALL_PROVIDER_FIRST_TIME)
        cur=j.currentness_resolver(self.intent,self.contract); self.assertIsNotNone(cur)
        self.assertEqual(cur.consumer_admission_root,a.receipt_root)
        self.assertEqual(p.provider_action_currentness_root,cur.identity_root)
        self.assertEqual(p.effect_attempt_root,effect_attempt_root(self.intent,self.contract,1,cur.identity_root))
        self.assertEqual(j.status('cmd-1')['provider_action_currentness_root'],cur.identity_root)

    def test_stale_consumer_generation_holds_before_retry(self):
        j,_=self.prepared(); first=j.decide_and_persist(self.ident,self.intent,self.contract,self.context)
        self.assertEqual(first.action,Action.CALL_PROVIDER_FIRST_TIME); j.record_ambiguous('cmd-1',r('provider-op'))
        old=self.admission(generation=7,currentness='current-7')
        j.currentness_resolver=self.resolver(old,generation=8,currentness='current-8')
        hold=j.decide_and_persist(self.ident,self.intent,self.contract,self.context)
        self.assertEqual(hold.action,Action.HOLD_REBIND_REQUIRED)
        self.assertEqual(j.status('cmd-1')['provider_request_count'],1)

    def test_fresh_rebind_allows_contract_retry_and_changes_attempt_root(self):
        j,_=self.prepared(); first=j.decide_and_persist(self.ident,self.intent,self.contract,self.context)
        j.record_ambiguous('cmd-1',r('provider-op'))
        fresh=self.admission(generation=8,currentness='current-8')
        j.currentness_resolver=self.resolver(fresh,generation=8,currentness='current-8')
        retry=j.decide_and_persist(self.ident,self.intent,self.contract,self.context)
        self.assertEqual(retry.action,Action.RETRY_EXACT_SAME_EFFECT)
        self.assertEqual(retry.provider_request_count,2)
        self.assertNotEqual(first.effect_attempt_root,retry.effect_attempt_root)
        cur=j.currentness_resolver(self.intent,self.contract)
        self.assertEqual(retry.effect_attempt_root,effect_attempt_root(self.intent,self.contract,2,cur.identity_root))

    def test_post_result_consumer_drift_does_not_erase_owed_return(self):
        j,_=self.prepared(); j.decide_and_persist(self.ident,self.intent,self.contract,self.context)
        j.record_result('cmd-1',r('result'),r('provider-op'))
        forged=dataclasses.replace(self.admission(),mac=r('forged'))
        j.currentness_resolver=self.resolver(forged)
        out=OutboxJournal(self.outbox_path)
        terminal_root=j.stage_final_terminal(out,self.ident)
        self.assertEqual(len(terminal_root),64)
        self.assertEqual(j.status('cmd-1')['provider_request_count'],1)

    def test_raw_structural_resolver_is_not_canonical_factory(self):
        forged=dataclasses.replace(self.admission(),mac=r('forged'))
        canonical=build_canonical_effect_attempt_journal(self.journal_path,secret=self.secret,cut=self.cut(),
            admission_provider=lambda *_: forged,now_provider=lambda:self.now)
        canonical.bind_admitted(self.ident,self.intent,self.contract)
        with self.assertRaises(ValueError): canonical.publish_ack(self.ident,self.intent,self.contract,lambda _:'ack-ref')
        self.assertIsInstance(canonical,EffectAttemptJournal)

if __name__=='__main__': unittest.main()
