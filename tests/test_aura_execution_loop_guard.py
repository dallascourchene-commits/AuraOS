from __future__ import annotations
import unittest
from tools.aura_execution_loop_guard import ExecutionLoopGuard, MutationIntent, RetrievalFingerprint, VERSION

class ExecutionLoopGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = ExecutionLoopGuard(objective_id="project-x")
        self.read = RetrievalFingerprint("github.fetch", "run:123", "workflow status", "page:1", "verify exact hosted proof")
        self.intent = MutationIntent.build(
            action_class="github.update_pull_request",
            target_object="pr:740",
            allowed_fields=("state",),
            expected_state_delta="pull_request event: reopened",
            repair_route="restore PR metadata through github.update_pull_request",
        )

    def test_version_and_authority_negative_snapshot(self):
        snap = self.guard.snapshot()
        self.assertEqual(snap["version"], VERSION)
        for key in ("effect_authority", "semantic_authority", "provider_authority", "native_private_transformer_kv"):
            self.assertFalse(snap[key])

    def test_first_read_is_admitted(self):
        self.assertTrue(self.guard.admit_read(self.read, observed_state_token="s1").allowed)

    def test_identical_read_without_state_transition_is_blocked(self):
        self.guard.admit_read(self.read, observed_state_token="s1")
        d = self.guard.admit_read(self.read, observed_state_token="s1")
        self.assertFalse(d.allowed)
        self.assertEqual(d.disposition, "CHANGE_AXIS_OR_COLLAPSE")

    def test_same_read_after_new_provider_state_is_admitted(self):
        self.guard.admit_read(self.read, observed_state_token="s1")
        self.assertTrue(self.guard.admit_read(self.read, observed_state_token="s2").allowed)

    def test_exact_write_intent_is_admitted(self):
        d = self.guard.admit_write(self.intent, selected_action_class="github.update_pull_request",
                                   selected_target_object="pr:740", selected_fields=("state",))
        self.assertTrue(d.allowed)

    def test_wrong_action_class_freezes_primitive(self):
        d1 = self.guard.admit_write(self.intent, selected_action_class="github.update_file",
                                    selected_target_object="workflow:file", selected_fields=("content",))
        self.assertEqual(d1.disposition, "STOP_PRIMITIVE")
        intent2 = MutationIntent.build(action_class="github.update_file", target_object="workflow:file",
                                       allowed_fields=("content",), expected_state_delta="file changes",
                                       repair_route="tree restore")
        d2 = self.guard.admit_write(intent2, selected_action_class="github.update_file",
                                    selected_target_object="workflow:file", selected_fields=("content",))
        self.assertFalse(d2.allowed)
        self.assertEqual(d2.disposition, "STOP_PRIMITIVE")

    def test_wrong_target_or_fields_are_blocked(self):
        d = self.guard.admit_write(self.intent, selected_action_class="github.update_pull_request",
                                   selected_target_object="pr:741", selected_fields=("state",))
        self.assertFalse(d.allowed)
        g2 = ExecutionLoopGuard(objective_id="fields")
        d2 = g2.admit_write(self.intent, selected_action_class="github.update_pull_request",
                            selected_target_object="pr:740", selected_fields=("state", "body"))
        self.assertFalse(d2.allowed)

    def test_noop_content_identity_blocks_repeated_write(self):
        self.assertTrue(self.guard.admit_write(
            self.intent, selected_action_class="github.update_pull_request",
            selected_target_object="pr:740", selected_fields=("state",)).allowed)
        d = self.guard.record_write_result(self.intent, before_content_identity="same",
                                           after_content_identity="same",
                                           expected_transition_observed=False)
        self.assertEqual(d.disposition, "NO_OP_HISTORY_DRIFT")
        retry = self.guard.admit_write(
            self.intent, selected_action_class="github.update_pull_request",
            selected_target_object="pr:740", selected_fields=("state",))
        self.assertEqual(retry.disposition, "NO_OP_HISTORY_DRIFT_BLOCKED")

    def test_unintended_semantic_mutation_freezes_all_writes(self):
        d = self.guard.record_write_result(self.intent, before_content_identity="a",
                                           after_content_identity="b",
                                           expected_transition_observed=False,
                                           unintended_semantic_mutation=True)
        self.assertEqual(d.disposition, "MUTATION_STOP")
        blocked = self.guard.admit_write(
            self.intent, selected_action_class="github.update_pull_request",
            selected_target_object="pr:740", selected_fields=("state",))
        self.assertEqual(blocked.disposition, "MUTATION_STOP")

    def test_repeated_terminal_poll_is_blocked(self):
        self.assertTrue(self.guard.admit_poll(poll_key="workflow:123",
                                             observed_state_token="completed:success",
                                             terminal=True).allowed)
        d = self.guard.admit_poll(poll_key="workflow:123",
                                  observed_state_token="completed:success",
                                  terminal=True)
        self.assertEqual(d.disposition, "CHANGE_AXIS_OR_COLLAPSE")

    def test_nonterminal_poll_can_progress_then_terminal_repeat_blocks(self):
        self.assertTrue(self.guard.admit_poll(poll_key="workflow:123",
                                             observed_state_token="queued",
                                             terminal=False).allowed)
        self.assertTrue(self.guard.admit_poll(poll_key="workflow:123",
                                             observed_state_token="completed:success",
                                             terminal=True).allowed)
        self.assertFalse(self.guard.admit_poll(poll_key="workflow:123",
                                              observed_state_token="completed:success",
                                              terminal=True).allowed)

if __name__ == "__main__":
    unittest.main()
