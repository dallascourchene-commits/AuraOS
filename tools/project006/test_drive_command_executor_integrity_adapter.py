import copy
import unittest

from drive_command_executor_hook import CommandHookError
from drive_command_executor_integrity_adapter import (
    execute_integrity_checked_command,
    integrity_gate_result,
    validate_single_call_route,
)
from drive_swarm_fanout import (
    ROLE_SCHEMA,
    SWARM_SCHEMA,
    compile_role_distinct_children,
)


def compiled_child():
    parent = {
        "schema": SWARM_SCHEMA,
        "parent_command_id": "parent",
        "parent_idempotency_key": "parent-idem",
        "target_size": 3,
        "base_command": {
            "schema": "AuraCommandEnvelopeV1-candidate",
            "command_id": "parent-base",
            "idempotency_key": "parent-base-idem",
            "authority_ref": "owner",
            "queue_state": "AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND",
            "message_authorized": True,
            "execution_authorized": True,
            "transport": {"type": "CHATGPT"},
            "objective": {
                "text": "Investigate the bounded task.",
                "requested_effect": "D0",
                "positive_intent": [],
                "negative_intent": [],
                "success_criteria": [],
            },
            "constraints": {"workspace_scope": "AURA_DRIVE_ONLY"},
            "requested_capability": {
                "semantic_id_or_alias": "EXISTING_AURA_DEEPSEEK_EXECUTOR"
            },
        },
        "roles": [
            {
                "schema": ROLE_SCHEMA,
                "role_id": "A+",
                "worker_id": "W-A",
                "objective_suffix": "Construct.",
            },
            {
                "schema": ROLE_SCHEMA,
                "role_id": "B-",
                "worker_id": "W-B",
                "objective_suffix": "Challenge.",
            },
            {
                "schema": ROLE_SCHEMA,
                "role_id": "C0",
                "worker_id": "W-C",
                "objective_suffix": "Verify.",
            },
        ],
    }
    return compile_role_distinct_children(parent)[0]


def expected_context(raw):
    return copy.deepcopy(raw["_host_child_context"])


class RouteGuardTests(unittest.TestCase):
    def test_parent_swarm_schema_fails_before_single_call(self):
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_SWARM_PARENT_REQUIRES_FANOUT_COORDINATOR"
        ):
            validate_single_call_route({"schema": SWARM_SCHEMA})

    def test_top_level_target3_without_child_context_fails(self):
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_SWARM_PARENT_REQUIRES_FANOUT_COORDINATOR"
        ):
            validate_single_call_route(
                {"schema": "AuraCommandEnvelopeV1-candidate", "target_size": 3}
            )

    def test_self_asserted_child_context_is_not_authority(self):
        raw = compiled_child()
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_CHILD_EXPECTATION_REQUIRED"
        ):
            validate_single_call_route(raw)

    def test_child_context_must_match_host_expected_child(self):
        raw = compiled_child()
        expected = expected_context(raw)
        raw["_host_child_context"]["worker_id"] = "FORGED-WORKER"
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_CHILD_EXPECTATION_MISMATCH"
        ):
            validate_single_call_route(raw, expected_child_context=expected)

    def test_forged_self_consistent_context_cannot_bypass_expected_child(self):
        raw = compiled_child()
        expected = expected_context(raw)
        forged = copy.deepcopy(raw)
        forged["_host_child_context"]["parent_command_id"] = "attacker-parent"
        forged["_host_child_context"]["parent_idempotency_key"] = "attacker-idem"
        forged["_host_child_context"]["parent_payload_digest"] = "f" * 64
        forged["_host_child_context"]["role_id"] = "ATTACKER"
        forged["_host_child_context"]["worker_id"] = "ATTACKER-WORKER"
        forged["_host_child_context"]["child_command_id"] = forged["command_id"]
        forged["_host_child_context"]["child_idempotency_key"] = forged["idempotency_key"]
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_CHILD_EXPECTATION_MISMATCH"
        ):
            validate_single_call_route(forged, expected_child_context=expected)

    def test_child_context_must_bind_command_and_idempotency(self):
        raw = compiled_child()
        expected = expected_context(raw)
        raw["_host_child_context"]["child_command_id"] = "WRONG"
        expected["child_command_id"] = "WRONG"
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_CHILD_COMMAND_BINDING_MISMATCH"
        ):
            validate_single_call_route(raw, expected_child_context=expected)

    def test_child_context_requires_parent_payload_digest(self):
        raw = compiled_child()
        expected = expected_context(raw)
        del raw["_host_child_context"]["parent_payload_digest"]
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_CHILD_PAYLOAD_DIGEST_INVALID"
        ):
            validate_single_call_route(raw, expected_child_context=expected)

    def test_top_level_target_must_match_child_context_when_present(self):
        raw = compiled_child()
        expected = expected_context(raw)
        raw["target_size"] = 2
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_CHILD_TARGET_SIZE_BINDING_MISMATCH"
        ):
            validate_single_call_route(raw, expected_child_context=expected)


class IntegrityGateTests(unittest.TestCase):
    def test_good_transport_is_partial_not_success(self):
        out = integrity_gate_result(
            {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "deepseek",
                "model": "deepseek-chat",
                "result": "Completed bounded analysis with source references.",
            },
            expected_model="deepseek-chat",
        )
        self.assertEqual("RESULT_PARTIAL", out["status"])
        self.assertEqual("EVIDENCE_REQUIRED", out["objective_adequacy"])
        self.assertFalse(out["reduction_allowed"])

    def test_missing_required_provider_is_quarantined(self):
        out = integrity_gate_result(
            {
                "record_type": "RESULT",
                "status": "OK",
                "model": "deepseek-chat",
                "result": "Completed.",
            },
            expected_provider="deepseek",
            expected_model="deepseek-chat",
        )
        self.assertEqual("PROVIDER_IDENTITY_MISMATCH", out["status"])
        self.assertTrue(out["quarantine"])

    def test_missing_required_model_is_quarantined(self):
        out = integrity_gate_result(
            {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "deepseek",
                "result": "Completed.",
            },
            expected_provider="deepseek",
            expected_model="deepseek-chat",
        )
        self.assertEqual("MODEL_IDENTITY_MISMATCH", out["status"])
        self.assertTrue(out["quarantine"])

    def test_refusal_is_quarantined(self):
        out = integrity_gate_result(
            {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "deepseek",
                "result": "I cannot execute that work because I don't have access.",
            }
        )
        self.assertEqual("MODEL_REFUSAL", out["status"])
        self.assertTrue(out["quarantine"])

    def test_deepseek_claude_contradiction_is_quarantined(self):
        out = integrity_gate_result(
            {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "deepseek",
                "result": "I'm Claude, created by Anthropic, not DeepSeek.",
            }
        )
        self.assertEqual("PROVIDER_IDENTITY_MISMATCH", out["status"])
        self.assertTrue(out["quarantine"])

    def test_direct_provider_metadata_mismatch_is_quarantined(self):
        out = integrity_gate_result(
            {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "anthropic",
                "model": "claude-sonnet",
                "result": "Completed.",
            },
            expected_provider="deepseek",
        )
        self.assertEqual("PROVIDER_IDENTITY_MISMATCH", out["status"])
        self.assertTrue(out["quarantine"])

    def test_direct_model_metadata_mismatch_is_quarantined(self):
        out = integrity_gate_result(
            {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "deepseek",
                "model": "unexpected-model",
                "result": "Completed.",
            },
            expected_provider="deepseek",
            expected_model="deepseek-chat",
        )
        self.assertEqual("MODEL_IDENTITY_MISMATCH", out["status"])
        self.assertTrue(out["quarantine"])

    def test_wrapper_preserves_payload_bound_child_lineage_and_does_not_claim_swarm(self):
        raw = compiled_child()
        expected = expected_context(raw)

        def fake_executor(_raw, **_kwargs):
            return {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "deepseek",
                "model": "deepseek-chat",
                "result": "Construct result; evidence requires reducer verification.",
            }

        out = execute_integrity_checked_command(
            raw,
            executor=fake_executor,
            expected_child_context=expected,
            expected_model="deepseek-chat",
        )
        self.assertEqual("parent", out["parent_command_id"])
        self.assertEqual("A+", out["role_id"])
        self.assertEqual("W-A", out["worker_id"])
        self.assertEqual(0, out["ordinal"])
        self.assertEqual(raw["command_id"], out["child_command_id"])
        self.assertEqual(raw["idempotency_key"], out["child_idempotency_key"])
        self.assertEqual(
            raw["_host_child_context"]["parent_payload_digest"],
            out["parent_payload_digest"],
        )
        self.assertFalse(out["physical_swarm_proven"])
        self.assertEqual("RESULT_PARTIAL", out["status"])


if __name__ == "__main__":
    unittest.main()
