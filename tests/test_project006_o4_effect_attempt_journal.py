from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace

from tools.arena.effect_return_atomicity import (
    Action, EffectContract, EffectIntent, EXPECTED_REPROOF_SEMANTICS,
    ProviderActionCurrentness, RecoveryContext, RecoveryMode,
)
from tools.project006.o4_effect_attempt_journal import O4EffectAttemptJournal
from tools.project006.o4_owner_row_convergence import ProofAdmission, digest, proof_crossbind_root
from tools.project006.terminal_outbox import CommandIdentity


def root(c: str) -> str:
    return c * 64


def currentness(intent, generation=7):
    return ProviderActionCurrentness(intent.source_root, intent.tecc_authorization_root, root("9"),
        EXPECTED_REPROOF_SEMANTICS, generation, "SOURCE_OWNER", "TECC_OWNER", "CURRENTNESS_OBSERVER")


def proof(ident, intent, contract, *, generation=7, current=None, expiry=2000, recovery=None):
    from tools.project006.o4_effect_attempt_journal import O4EffectAttemptJournal
    semantic = O4EffectAttemptJournal._semantic(ident, intent, contract)
    a = ProofAdmission("0"*64, root("1"), digest(["consumer",generation,current]), digest(["auth",generation]),
        digest(["proof-generation",generation]), "PSEM-O4", generation, current or digest(["current",generation]),
        "VERIFIER-O4", root("2"), 4, expiry, recovery or contract.recovery_mode.value)
    return replace(a, proof_bound_admission_root=proof_crossbind_root(semantic, a))


class O4ActualJournalPathTests(unittest.TestCase):
    def fixture(self, mode=RecoveryMode.IDEMPOTENT_RETRY, proof_resolver=None, now=1000):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        ident=CommandIdentity("C","K","FILE","REV",root("a"))
        intent=EffectIntent("C","K",root("a"),root("b"),root("c"),"MAIL")
        contract=EffectContract(mode,root("d"),"MAIL")
        resolver=proof_resolver or (lambda i,x,c: proof(i,x,c))
        journal=O4EffectAttemptJournal(os.path.join(td.name,"effect.db"),
            currentness_resolver=lambda _i,_c: currentness(intent), proof_admission_resolver=resolver,
            now_resolver=lambda: now)
        journal.bind_admitted(ident,intent,contract)
        context=RecoveryContext(intent.identity_root,contract.contract_root,contract.capability_receipt_root,"K",root("c"))
        return ident,intent,contract,journal,context

    def test_first_provider_candidate_is_owner_bound(self):
        ident,intent,contract,journal,context=self.fixture()
        journal.publish_ack(ident,intent,contract,lambda _:"ACK")
        permit=journal.decide_and_persist(ident,intent,contract,context)
        self.assertEqual(permit.action,Action.CALL_PROVIDER_FIRST_TIME)
        self.assertTrue(permit.stable_provider_operation_root)
        self.assertTrue(permit.proof_bound_admission_root)
        row=journal.status("C")
        self.assertEqual(row["effect_attempt_root"],permit.effect_attempt_root)
        self.assertEqual(row["stable_provider_operation_root"],permit.stable_provider_operation_root)
        self.assertEqual(row["proof_bound_admission_root"],permit.proof_bound_admission_root)
        self.assertIsNone(row["provider_operation_root"])

    def test_missing_proof_owner_cannot_call_provider(self):
        ident,intent,contract,journal,context=self.fixture(proof_resolver=lambda *_:None)
        journal.publish_ack(ident,intent,contract,lambda _:"ACK")
        p=journal.decide_and_persist(ident,intent,contract,context)
        self.assertEqual(p.action,Action.HOLD_REBIND_REQUIRED)
        self.assertEqual(journal.status("C")["provider_request_count"],0)

    def test_recovery_mode_crosscast_cannot_call_provider(self):
        def bad(i,x,c): return proof(i,x,c,recovery="QUERY_RECONCILE")
        ident,intent,contract,journal,context=self.fixture(proof_resolver=bad)
        journal.publish_ack(ident,intent,contract,lambda _:"ACK")
        self.assertEqual(journal.decide_and_persist(ident,intent,contract,context).action,Action.HOLD_REBIND_REQUIRED)
        self.assertEqual(journal.status("C")["provider_request_count"],0)

    def test_expired_proof_cannot_call_provider(self):
        def expired(i,x,c): return proof(i,x,c,expiry=1000)
        ident,intent,contract,journal,context=self.fixture(proof_resolver=expired,now=1000)
        journal.publish_ack(ident,intent,contract,lambda _:"ACK")
        self.assertEqual(journal.decide_and_persist(ident,intent,contract,context).action,Action.HOLD_REBIND_REQUIRED)
        self.assertEqual(journal.status("C")["provider_request_count"],0)

    def test_consumer_rebind_keeps_operation_changes_attempt(self):
        state={"generation":7}
        def moving(i,x,c):
            g=state["generation"]; return proof(i,x,c,generation=g,current=digest(["current",g]))
        ident,intent,contract,journal,context=self.fixture(proof_resolver=moving)
        journal.publish_ack(ident,intent,contract,lambda _:"ACK")
        p1=journal.decide_and_persist(ident,intent,contract,context); journal.record_ambiguous("C",root("e"))
        state["generation"]=8
        p2=journal.decide_and_persist(ident,intent,contract,context)
        self.assertEqual(p2.action,Action.RETRY_EXACT_SAME_EFFECT)
        self.assertEqual(p1.stable_provider_operation_root,p2.stable_provider_operation_root)
        self.assertNotEqual(p1.proof_action_currentness_root,p2.proof_action_currentness_root)
        self.assertNotEqual(p1.effect_attempt_root,p2.effect_attempt_root)
        self.assertEqual(journal.status("C")["provider_operation_root"],root("e"))

    def test_result_observed_survives_later_proof_failure(self):
        switch={"bad":False}
        def moving(i,x,c):
            return None if switch["bad"] else proof(i,x,c)
        ident,intent,contract,journal,context=self.fixture(proof_resolver=moving)
        journal.publish_ack(ident,intent,contract,lambda _:"ACK")
        journal.decide_and_persist(ident,intent,contract,context); journal.record_result("C",root("f"))
        switch["bad"]=True
        p=journal.decide_and_persist(ident,intent,contract,context)
        self.assertEqual(p.action,Action.RETRY_RETURN_WRITER_ONLY)
        self.assertEqual(journal.status("C")["result_root"],root("f"))


if __name__ == "__main__": unittest.main()
