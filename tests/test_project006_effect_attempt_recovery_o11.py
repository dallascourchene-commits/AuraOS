import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.arena.effect_return_atomicity import (
    Action,
    EffectContract,
    EffectIntent,
    EXPECTED_REPROOF_SEMANTICS,
    Phase,
    ProviderActionCurrentness,
    RecoveryContext,
    RecoveryMode,
)
from tools.project006.effect_attempt_recovery import EffectAttemptJournal
from tools.project006.project006_consumer_outbox_wrapper import publish_receipts
from tools.project006.terminal_outbox import AckState, CommandIdentity, OutboxJournal, TerminalResponse


def root(char: str) -> str:
    return char * 64


def currentness(intent, *, generation=7, source=None, authorization=None, semantics=EXPECTED_REPROOF_SEMANTICS,
                observer="CURRENTNESS_OBSERVER"):
    return ProviderActionCurrentness(
        source or intent.source_root,
        authorization or intent.tecc_authorization_root,
        root("9"),
        semantics,
        generation,
        "SOURCE_OWNER",
        "TECC_OWNER",
        observer,
    )


class EffectAttemptRecoveryO11Tests(unittest.TestCase):
    def fixture(self, mode=RecoveryMode.NON_RETRYABLE, resolver="valid"):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        ident = CommandIdentity("C", "K", "FILE", "REV", root("a"))
        intent = EffectIntent("C", "K", root("a"), root("b"), root("c"), "MAIL")
        contract = EffectContract(mode, root("d"), "MAIL")
        if resolver == "valid":
            resolve = lambda _i, _c: currentness(intent)
        elif resolver == "none":
            resolve = lambda _i, _c: None
        elif resolver == "stale_source":
            resolve = lambda _i, _c: currentness(intent, source=root("e"))
        elif resolver == "stale_auth":
            resolve = lambda _i, _c: currentness(intent, authorization=root("e"))
        elif resolver == "legacy_semantics":
            resolve = lambda _i, _c: currentness(intent, semantics="LEGACY_REPROOF-v0")
        else:
            raise AssertionError(resolver)
        journal = EffectAttemptJournal(os.path.join(td.name, "effect.db"), currentness_resolver=resolve)
        outbox = OutboxJournal(os.path.join(td.name, "outbox.db"))
        journal.bind_admitted(ident, intent, contract)
        context = RecoveryContext(intent.identity_root, contract.contract_root, contract.capability_receipt_root,
                                  "K", root("c"))
        return ident, intent, contract, journal, outbox, context

    def test_binding_rejects_wrong_source(self):
        ident, intent, contract, journal, _, _ = self.fixture()
        bad = CommandIdentity("C", "K", "FILE", "REV", root("e"))
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_DIVERGED"):
            journal._bind(bad, intent, contract)

    def test_missing_currentness_owner_cannot_publish_ack_or_call_provider(self):
        ident, intent, contract, journal, _, context = self.fixture(resolver="none")
        with self.assertRaisesRegex(ValueError, "CURRENTNESS_OWNER_UNAVAILABLE"):
            journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(permit.action, Action.HOLD_REBIND_REQUIRED)
        self.assertEqual(journal.status("C")["provider_request_count"], 0)

    def test_stale_source_owner_currentness_holds(self):
        ident, intent, contract, journal, _, context = self.fixture(resolver="stale_source")
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual((permit.action, journal.status("C")["provider_request_count"]),
                         (Action.HOLD_REBIND_REQUIRED, 0))

    def test_stale_tecc_authorization_currentness_holds(self):
        ident, intent, contract, journal, _, context = self.fixture(resolver="stale_auth")
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(permit.action, Action.HOLD_REBIND_REQUIRED)

    def test_legacy_proof_semantics_holds(self):
        ident, intent, contract, journal, _, context = self.fixture(resolver="legacy_semantics")
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(permit.action, Action.HOLD_REBIND_REQUIRED)

    def test_same_lineage_currentness_observer_rejected(self):
        intent = EffectIntent("C", "K", root("a"), root("b"), root("c"), "MAIL")
        with self.assertRaisesRegex(ValueError, "CURRENTNESS_OBSERVER_NOT_INDEPENDENT"):
            currentness(intent, observer="SOURCE_OWNER")

    def test_ack_failure_becomes_ambiguous_and_forbids_blind_resend(self):
        ident, intent, contract, journal, _, context = self.fixture()
        def fail(_):
            raise RuntimeError("writer failed after unknown delivery")
        with self.assertRaises(RuntimeError):
            journal.publish_ack(ident, intent, contract, fail)
        self.assertEqual(journal.status("C")["phase"], Phase.ACK_WRITE_AMBIGUOUS.value)
        self.assertEqual(journal.decide_and_persist(ident, intent, contract, context).action,
                         Action.HOLD_ACK_RECONCILIATION)
        with self.assertRaisesRegex(ValueError, "ACK_RECONCILIATION_REQUIRED"):
            journal.publish_ack(ident, intent, contract, lambda _: "ACK-RETRY")

    def test_ack_crash_after_external_success_is_reconciliation_not_duplicate(self):
        ident, intent, contract, journal, _, context = self.fixture()
        payload, payload_root = journal.prepare_ack(ident, intent, contract)
        self.assertEqual(journal.status("C")["phase"], Phase.ACK_WRITE_INFLIGHT.value)
        external_ref = "ACK-EXTERNALLY-WRITTEN"
        self.assertTrue(payload["kind"].startswith("ACK_"))
        reopened = EffectAttemptJournal(journal.path, currentness_resolver=lambda _i, _c: currentness(intent))
        with self.assertRaisesRegex(ValueError, "ACK_RECONCILIATION_REQUIRED"):
            reopened.publish_ack(ident, intent, contract, lambda _: "MUST-NOT-WRITE")
        reopened.resolve_ambiguous_ack_as_written("C", payload_root, external_ref)
        self.assertEqual(reopened.status("C")["phase"], Phase.ACK_WRITTEN_PRE_EFFECT.value)
        self.assertEqual(reopened.decide_and_persist(ident, intent, contract, context).action,
                         Action.CALL_PROVIDER_FIRST_TIME)

    def test_ack_published_then_first_attempt_binds_currentness(self):
        ident, intent, contract, journal, _, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK-1")
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(permit.action, Action.CALL_PROVIDER_FIRST_TIME)
        self.assertEqual(permit.provider_request_count, 1)
        self.assertIsNotNone(permit.provider_action_currentness_root)
        row = journal.status("C")
        self.assertEqual(row["effect_attempt_root"], permit.effect_attempt_root)
        self.assertEqual(row["provider_action_currentness_root"], permit.provider_action_currentness_root)

    def test_nonretryable_crash_holds_and_can_publish_ambiguous_terminal(self):
        ident, intent, contract, journal, outbox, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C")
        permit = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(permit.action, Action.HOLD_COMPLETION_AMBIGUOUS)
        journal.stage_final_terminal(outbox, ident)
        self.assertEqual(json.loads(outbox.status("C")["response_json"])["kind"], "COMPLETION_AMBIGUOUS")

    def test_idempotent_ambiguity_cannot_finalize_and_retries_exact(self):
        ident, intent, contract, journal, outbox, context = self.fixture(RecoveryMode.IDEMPOTENT_RETRY)
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C")
        with self.assertRaisesRegex(ValueError, "AMBIGUITY_REQUIRES_RECOVERY_DECISION"):
            journal.stage_final_terminal(outbox, ident)
        second = journal.decide_and_persist(ident, intent, contract, context)
        self.assertEqual(second.action, Action.RETRY_EXACT_SAME_EFFECT)
        self.assertEqual(second.provider_request_count, 2)

    def test_queryable_ambiguity_cannot_finalize_and_requires_query(self):
        ident, intent, contract, journal, outbox, context = self.fixture(RecoveryMode.QUERY_RECONCILE)
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C", root("e"))
        with self.assertRaisesRegex(ValueError, "AMBIGUITY_REQUIRES_RECOVERY_DECISION"):
            journal.stage_final_terminal(outbox, ident)
        self.assertEqual(journal.decide_and_persist(ident, intent, contract, context).action,
                         Action.QUERY_PROVIDER_STATUS)

    def test_payload_move_holds_idempotency(self):
        ident, intent, contract, journal, _, _ = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        bad = RecoveryContext(intent.identity_root, contract.contract_root, contract.capability_receipt_root,
                              "K", root("e"))
        self.assertEqual(journal.decide_and_persist(ident, intent, contract, bad).action,
                         Action.HOLD_IDEMPOTENCY_CONFLICT)

    def test_result_preserves_existing_provider_operation_root(self):
        ident, intent, contract, journal, _, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C", root("e"))
        journal.record_result("C", root("f"))
        self.assertEqual(journal.status("C")["provider_operation_root"], root("e"))

    def test_result_rejects_conflicting_provider_operation_root(self):
        ident, intent, contract, journal, _, context = self.fixture()
        journal.publish_ack(ident, intent, contract, lambda _: "ACK")
        journal.decide_and_persist(ident, intent, contract, context)
        journal.record_ambiguous("C", root("e"))
        with self.assertRaisesRegex(ValueError, "PROVIDER_OPERATION_ROOT_CONFLICT"):
            journal.record_result("C", root("f"), root("7"))

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

    def test_pre_effect_rejection_still_forbids_provider_count(self):
        ident, _, _, _, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "NEGATIVE_RESPONSE_HAS_PROVIDER_EFFECT"):
            TerminalResponse(ident, "COMMAND_BLOCKED", provider_request_count=1).canonical()

    def test_ack_with_provider_count_is_forbidden(self):
        ident, _, _, _, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "NEGATIVE_RESPONSE_HAS_PROVIDER_EFFECT"):
            TerminalResponse(ident, "ACK_ACCEPTED_PRE_EFFECT", provider_request_count=1).canonical()

    def test_ack_not_final_terminal_outbox_item(self):
        ident, _, _, _, outbox, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "ACK_IS_NOT_TERMINAL_RETURN"):
            outbox.stage_terminal(TerminalResponse(ident, "ACK_ACCEPTED_PRE_EFFECT"))

    def test_outbox_ack_route_publishes_and_dedupes(self):
        ident, _, _, _, outbox, _ = self.fixture()
        ack = TerminalResponse(ident, "ACK_ACCEPTED_PRE_EFFECT")
        outbox.stage_ack(ack)
        calls = []
        ref1 = outbox.publish_ack_pending("C", lambda _: calls.append(1) or "ACK-FILE")
        ref2 = outbox.publish_ack_pending("C", lambda _: calls.append(2) or "BAD")
        self.assertEqual((ref1, ref2, calls), ("ACK-FILE", "ACK-FILE", [1]))

    def test_outbox_ack_failure_enters_reconciliation_and_no_blind_retry(self):
        ident, _, _, _, outbox, _ = self.fixture()
        outbox.stage_ack(TerminalResponse(ident, "ACK_ACCEPTED_PRE_EFFECT"))
        with self.assertRaises(RuntimeError):
            outbox.publish_ack_pending("C", lambda _: (_ for _ in ()).throw(RuntimeError("unknown write outcome")))
        self.assertEqual(outbox.ack_status("C")["state"], AckState.WRITE_AMBIGUOUS.value)
        with self.assertRaisesRegex(ValueError, "ACK_RECONCILIATION_REQUIRED"):
            outbox.publish_ack_pending("C", lambda _: "MUST-NOT-SEND")

    def test_wrapper_migrates_ack_to_ack_route_not_final_outbox(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        receipt = Path(td.name) / "ack.json"
        receipt.write_text(json.dumps({
            "command_id": "CW", "idempotency_key": "KW", "source_file_id": "F",
            "source_revision": "R", "source_digest": root("a"),
            "kind": "ACK_ACCEPTED_PRE_EFFECT", "provider_request_count": 0,
        }))
        config = Path(td.name) / "config.json"
        config.write_text("{}")
        journal_path = str(Path(td.name) / "outbox.db")
        class FakeWriter:
            def __init__(self, *_args, **_kwargs): pass
            def __call__(self, _payload): return "ACK-WRAPPER"
        with patch("tools.project006.project006_consumer_outbox_wrapper.AuraDriveBusWriterV1", FakeWriter):
            rows = publish_receipts([receipt], journal_path=journal_path, config_path=str(config))
        self.assertEqual(rows[0]["status"], "ACK_WRITTEN_PRE_EFFECT")
        outbox = OutboxJournal(journal_path)
        self.assertEqual(outbox.ack_status("CW")["state"], AckState.WRITTEN.value)
        with self.assertRaisesRegex(ValueError, "COMMAND_NOT_INGESTED"):
            outbox.status("CW")

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


if __name__ == "__main__":
    unittest.main()
