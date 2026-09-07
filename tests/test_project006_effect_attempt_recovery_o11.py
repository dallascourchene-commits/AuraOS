import os
import tempfile
import unittest

from tools.arena.effect_return_atomicity import (
    Action,
    EffectContract,
    EffectIntent,
    Phase,
    RecoveryContext,
    RecoveryMode,
)
from tools.project006.effect_attempt_recovery import EffectAttemptJournal
from tools.project006.terminal_outbox import CommandIdentity, OutboxJournal, TerminalResponse


def root(char: str) -> str:
    return char * 64


class EffectAttemptRecoveryO11Tests(unittest.TestCase):
    def fixture(self, mode=RecoveryMode.NON_RETRYABLE):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        ident = CommandIdentity("C", "K", "FILE", "REV", root("a"))
        intent = EffectIntent("C", "K", root("a"), root("b"), root("c"), "MAIL")
        contract = EffectContract(mode, root("d"), "MAIL")
        journal = EffectAttemptJournal(os.path.join(td.name, "effect.db"))
        outbox = OutboxJournal(os.path.join(td.name, "outbox.db"))
        journal.bind_admitted(ident, intent, contract)
        context = RecoveryContext(
            intent.identity_root,
            contract.contract_root,
            contract.capability_receipt_root,
            "K",
            root("c"),
            True,
            True,
        )
        return ident, intent, contract, journal, outbox, context

    def test_binding_rejects_wrong_source(self):
        ident, intent, contract, journal, _, _ = self.fixture()
        bad = CommandIdentity("C", "K", "FILE", "REV", root("e"))
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_DIVERGED"):
            journal._bind(bad, intent, contract)

    def test_ack_failure_forbids_provider(self):
        ident, intent, contract, journal, _, context = self.fixture()
        def fail(_):
            raise RuntimeError("writer failed")
        with self.assertRaises(RuntimeError):
            journal.publish_ack(ident, intent, contract, fail)
        self.assertEqual(journal.status("C")["phase"], Phase.DECIDED_ADMITTED.value)
        self.assertEqual(journal.decide_and_persist(ident, intent, contract, context).action,
                         Action.WRITE_ACK_PRE_EFFECT)

    def test_ack_published_then_first_attempt_is_durable_before_call(self):
        ident, intent, contract, journal, _, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK-1")
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(permit.action, Action.CALL_PROVIDER_FIRST_TIME)
        self.assertEqual(permit.provider_request_count, 1)
        row = journal.status("C")
        self.assertEqual(row["phase"], Phase.EFFECT_ATTEMPT_DURABLE.value)
        self.assertEqual(row["effect_attempt_root"], permit.effect_attempt_root)

    def test_nonretryable_crash_holds(self):
        ident, intent, contract, journal, _, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C")
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(permit.action, Action.HOLD_COMPLETION_AMBIGUOUS)
        self.assertEqual(permit.provider_request_count, 1)

    def test_idempotent_crash_retries_exact_and_increments_attempt(self):
        ident, intent, contract, journal, _, context = self.fixture(RecoveryMode.IDEMPOTENT_RETRY)
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        first = journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C")
        second = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(second.action, Action.RETRY_EXACT_SAME_EFFECT)
        self.assertEqual(second.provider_request_count, 2)
        self.assertNotEqual(first.effect_attempt_root, second.effect_attempt_root)

    def test_queryable_crash_queries_not_resends(self):
        ident, intent, contract, journal, _, context = self.fixture(RecoveryMode.QUERY_RECONCILE)
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C", root("e"))
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(permit.action, Action.QUERY_PROVIDER_STATUS)
        self.assertEqual(permit.provider_request_count, 1)

    def test_payload_move_holds_idempotency(self):
        ident, intent, contract, journal, _, _ = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        bad = RecoveryContext(
            intent.identity_root, contract.contract_root, contract.capability_receipt_root,
            "K", root("e"), True, True,
        )
        self.assertEqual(journal.decide_and_persist(ident, intent, contract, bad).action,
                         Action.HOLD_IDEMPOTENCY_CONFLICT)

    def test_result_final_return_writer_retry_only(self):
        ident, intent, contract, journal, outbox, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_result("C", root("f"))
        journal.stage_final_terminal(outbox, ident)
        calls = [0]
        def writer(_):
            calls[0] += 1
            if calls[0] == 1:
                raise RuntimeError("return writer failed")
            return "RETURN-1"
        with self.assertRaises(RuntimeError):
            outbox.publish_pending("C", writer)
        self.assertEqual(journal.decide_and_persist(ident, intent, contract, context).action,
                         Action.RETRY_RETURN_WRITER_ONLY)
        ref = outbox.publish_pending("C", writer)
        journal.mark_return_written("C", ref)
        self.assertEqual(calls[0], 2)
        self.assertEqual(journal.status("C")["phase"], Phase.RETURN_WRITTEN.value)

    def test_ambiguous_post_effect_is_publishable_with_nonzero_count(self):
        ident, intent, contract, journal, outbox, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C")
        journal.stage_final_terminal(outbox, ident)
        import json
        body = json.loads(outbox.status("C")["response_json"])
        self.assertEqual(body["kind"], "COMPLETION_AMBIGUOUS")
        self.assertEqual(body["provider_request_count"], 1)

    def test_pre_effect_rejection_still_forbids_provider_count(self):
        ident, _, _, _, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "NEGATIVE_RESPONSE_HAS_PROVIDER_EFFECT"):
            TerminalResponse(ident, "COMMAND_BLOCKED", provider_request_count=1).canonical()

    def test_ack_with_provider_count_is_forbidden(self):
        ident, _, _, _, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "NEGATIVE_RESPONSE_HAS_PROVIDER_EFFECT"):
            TerminalResponse(ident, "ACK_ACCEPTED_PRE_EFFECT", provider_request_count=1).canonical()

    def test_ack_not_terminal_outbox_item(self):
        ident, _, _, _, outbox, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "ACK_IS_NOT_TERMINAL_RETURN"):
            outbox.stage_terminal(TerminalResponse(ident, "ACK_ACCEPTED_PRE_EFFECT"))

    def test_result_without_attempt_rejected(self):
        _, _, _, journal, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "RESULT_WITHOUT_DURABLE_ATTEMPT"):
            journal.record_result("C", root("f"))

    def test_ambiguous_without_attempt_rejected(self):
        _, _, _, journal, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_WITHOUT_DURABLE_ATTEMPT"):
            journal.record_ambiguous("C")

    def test_completion_ambiguous_zero_attempt_rejected_by_outbox(self):
        ident, _, _, _, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_COMPLETION_REQUIRES_EFFECT_ATTEMPT"):
            TerminalResponse(ident, "COMPLETION_AMBIGUOUS", provider_request_count=0).canonical()

    def test_currentness_move_holds_before_effect(self):
        ident, intent, contract, journal, _, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        stale = RecoveryContext(
            intent.identity_root, contract.contract_root, contract.capability_receipt_root,
            "K", root("c"), False, True,
        )
        permit = journal.decide_and_persist(ident, intent, contract, stale)
        self.assertEqual(permit.action, Action.HOLD_REBIND_REQUIRED)
        self.assertEqual(journal.status("C")["provider_request_count"], 0)


if __name__ == "__main__":
    unittest.main()
