import unittest

from drive_command_executor_hook import CommandHookError
from drive_command_executor_integrity_adapter import (
    execute_integrity_checked_command,
    integrity_gate_result,
    validate_single_call_route,
)
from drive_swarm_fanout import CHILD_CONTEXT_SCHEMA, SWARM_SCHEMA


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

    def test_child_context_must_bind_command_and_idempotency(self):
        raw = {
            "schema": "AuraCommandEnvelopeV1-candidate",
            "command_id": "child-1",
            "idempotency_key": "idem-1",
            "_host_child_context": {
                "schema": CHILD_CONTEXT_SCHEMA,
                "parent_command_id": "parent",
                "parent_idempotency_key": "parent-idem",
                "target_size": 3,
                "ordinal": 0,
                "role_id": "A+",
                "worker_id": "W-A",
                "child_command_id": "WRONG",
                "child_idempotency_key": "idem-1",
            },
        }
        with self.assertRaisesRegex(
            CommandHookError, "PHYSICAL_CHILD_COMMAND_BINDING_MISMATCH"
        ):
            validate_single_call_route(raw)


class IntegrityGateTests(unittest.TestCase):
    def test_good_transport_is_partial_not_success(self):
        out = integrity_gate_result(
            {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "deepseek",
                "result": "Completed bounded analysis with source references.",
            }
        )
        self.assertEqual("RESULT_PARTIAL", out["status"])
        self.assertEqual("EVIDENCE_REQUIRED", out["objective_adequacy"])
        self.assertFalse(out["reduction_allowed"])

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

    def test_wrapper_preserves_child_lineage_and_does_not_claim_swarm(self):
        raw = {
            "schema": "AuraCommandEnvelopeV1-candidate",
            "command_id": "child-1",
            "idempotency_key": "idem-1",
            "_host_child_context": {
                "schema": CHILD_CONTEXT_SCHEMA,
                "parent_command_id": "parent",
                "parent_idempotency_key": "parent-idem",
                "target_size": 3,
                "ordinal": 0,
                "role_id": "A+",
                "worker_id": "W-A",
                "child_command_id": "child-1",
                "child_idempotency_key": "idem-1",
            },
        }

        def fake_executor(_raw, **_kwargs):
            return {
                "record_type": "RESULT",
                "status": "OK",
                "provider": "deepseek",
                "result": "Construct result; evidence requires reducer verification.",
            }

        out = execute_integrity_checked_command(raw, executor=fake_executor)
        self.assertEqual("parent", out["parent_command_id"])
        self.assertEqual("A+", out["role_id"])
        self.assertEqual("W-A", out["worker_id"])
        self.assertFalse(out["physical_swarm_proven"])
        self.assertEqual("RESULT_PARTIAL", out["status"])


if __name__ == "__main__":
    unittest.main()
