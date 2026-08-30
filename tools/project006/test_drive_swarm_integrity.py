import unittest

from drive_swarm_fanout import (
    ROLE_SCHEMA,
    SWARM_SCHEMA,
    SwarmFanoutError,
    compile_role_distinct_children,
    fanout_manifest,
)
from drive_swarm_integrity import (
    SwarmIntegrityError,
    classify_model_output,
    validate_physical_swarm_receipts,
)


def base_command():
    return {
        "schema": "AuraCommandEnvelopeV1-candidate",
        "queue_state": "AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND",
        "message_authorized": True,
        "execution_authorized": True,
        "authority_ref": "owner",
        "transport": {"type": "CHATGPT"},
        "objective": {
            "text": "Investigate the bounded task.",
            "requested_effect": "D0",
            "positive_intent": [],
            "negative_intent": [],
            "success_criteria": [],
        },
        "constraints": {"workspace_scope": "AURA_DRIVE_ONLY"},
        "requested_capability": {"semantic_id_or_alias": "EXISTING_AURA_DEEPSEEK_EXECUTOR"},
        "command_id": "parent",
        "idempotency_key": "parent-key",
    }


def parent_swarm():
    return {
        "schema": SWARM_SCHEMA,
        "parent_command_id": "swarm-1",
        "parent_idempotency_key": "swarm-key",
        "target_size": 3,
        "base_command": base_command(),
        "roles": [
            {"schema": ROLE_SCHEMA, "role_id": "A+", "worker_id": "W-A", "objective_suffix": "Construct."},
            {"schema": ROLE_SCHEMA, "role_id": "B-", "worker_id": "W-B", "objective_suffix": "Challenge."},
            {"schema": ROLE_SCHEMA, "role_id": "C0", "worker_id": "W-C", "objective_suffix": "Verify."},
        ],
    }


class FanoutTests(unittest.TestCase):
    def test_target3_compiles_three_distinct_children(self):
        children = compile_role_distinct_children(parent_swarm())
        self.assertEqual(3, len(children))
        self.assertEqual(3, len({c["command_id"] for c in children}))
        self.assertEqual(3, len({c["idempotency_key"] for c in children}))
        self.assertEqual(
            ["A+", "B-", "C0"],
            [c["_host_child_context"]["role_id"] for c in children],
        )

    def test_role_count_mismatch_fails_closed(self):
        raw = parent_swarm()
        raw["target_size"] = 2
        with self.assertRaisesRegex(SwarmFanoutError, "TARGET_SIZE_ROLE_COUNT_MISMATCH"):
            compile_role_distinct_children(raw)

    def test_manifest_starts_no_effect(self):
        receipt = fanout_manifest(parent_swarm())
        self.assertEqual(3, receipt["child_count"])
        self.assertFalse(receipt["effect_started"])


class IntegrityTests(unittest.TestCase):
    def test_claude_text_under_deepseek_is_quarantined(self):
        result = classify_model_output(
            {"provider": "deepseek", "result": "I'm Claude, an AI assistant created by Anthropic, not DeepSeek."},
            expected_provider="deepseek",
        )
        self.assertEqual("PROVIDER_IDENTITY_MISMATCH", result["classification"])

    def test_refusal_is_not_success(self):
        result = classify_model_output(
            {"provider": "deepseek", "result": "I cannot execute that work order because I don't have access."},
            expected_provider="deepseek",
        )
        self.assertEqual("MODEL_REFUSAL", result["classification"])

    def test_single_response_simulating_roles_is_flagged(self):
        result = classify_model_output(
            {
                "provider": "deepseek",
                "result": "I'll execute three distinct identity roles. A+ CONSTRUCT ... B- CHALLENGE ... C0 VERIFY ...",
            },
            expected_provider="deepseek",
            physical_swarm_expected=True,
        )
        self.assertEqual("ROLE_FANOUT_VIOLATION", result["classification"])

    def test_valid_physical_three_requires_three_request_ids(self):
        receipts = [
            {
                "parent_command_id": "swarm-1",
                "worker_id": f"W{i}",
                "role_id": role,
                "attempt_id": f"A{i}",
                "provider_request_id": f"R{i}",
                "provider": "deepseek",
                "result": "Completed bounded analysis; evidence refs follow.",
            }
            for i, role in enumerate(("A+", "B-", "C0"))
        ]
        result = validate_physical_swarm_receipts(
            parent_command_id="swarm-1", target_size=3, child_receipts=receipts
        )
        self.assertTrue(result["physical_fanout_proven"])
        self.assertEqual(3, result["unique_provider_request_count"])

    def test_one_request_id_reused_fails(self):
        receipts = [
            {
                "parent_command_id": "swarm-1",
                "worker_id": f"W{i}",
                "role_id": role,
                "attempt_id": f"A{i}",
                "provider_request_id": "SAME",
                "provider": "deepseek",
                "result": "Completed bounded analysis.",
            }
            for i, role in enumerate(("A+", "B-", "C0"))
        ]
        with self.assertRaisesRegex(
            SwarmIntegrityError, "PROVIDER_REQUEST_ID_MISSING_OR_DUPLICATE"
        ):
            validate_physical_swarm_receipts(
                parent_command_id="swarm-1", target_size=3, child_receipts=receipts
            )


if __name__ == "__main__":
    unittest.main()
