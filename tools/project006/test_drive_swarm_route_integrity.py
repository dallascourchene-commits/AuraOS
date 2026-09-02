from __future__ import annotations

import unittest

from drive_route_admission import DEFAULT_MODEL
from drive_swarm_fanout import (
    ROLE_SCHEMA,
    SWARM_SCHEMA,
    compile_role_distinct_children,
    fanout_manifest,
)
from drive_swarm_integrity import SwarmIntegrityError
from drive_swarm_route_integrity import validate_route_bound_physical_swarm_receipts


def _parent():
    return {
        "schema": SWARM_SCHEMA,
        "parent_command_id": "target3-parent",
        "parent_idempotency_key": "target3-parent-idem",
        "target_size": 3,
        "base_command": {
            "schema": "AuraCommandEnvelopeV1-candidate",
            "command_id": "base",
            "idempotency_key": "base-idem",
            "authority_ref": "owner",
            "queue_state": "AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND",
            "message_authorized": True,
            "execution_authorized": True,
            "transport": {"type": "CHATGPT"},
            "objective": {
                "text": "Return one independent bounded leaf.",
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
            {"schema": ROLE_SCHEMA, "role_id": "A+", "worker_id": "W-A", "objective_suffix": "Construct."},
            {"schema": ROLE_SCHEMA, "role_id": "B-", "worker_id": "W-B", "objective_suffix": "Challenge."},
            {"schema": ROLE_SCHEMA, "role_id": "C0", "worker_id": "W-C", "objective_suffix": "Verify."},
        ],
    }


def _fixtures():
    parent = _parent()
    children = compile_role_distinct_children(parent)
    manifest = fanout_manifest(parent)
    receipts = []
    for i, child in enumerate(children):
        ctx = child["_host_child_context"]
        receipts.append(
            {
                "record_type": "RESULT",
                "status": "RESULT_PARTIAL",
                "parent_command_id": ctx["parent_command_id"],
                "parent_payload_digest": ctx["parent_payload_digest"],
                "command_id": child["command_id"],
                "idempotency_key": child["idempotency_key"],
                "ordinal": ctx["ordinal"],
                "role_id": ctx["role_id"],
                "worker_id": ctx["worker_id"],
                "attempt_id": f"attempt-{i}",
                "provider_request_id": f"request-{i}",
                "provider": "deepseek",
                "model": DEFAULT_MODEL,
                "route_provider": "deepseek",
                "route_model": DEFAULT_MODEL,
                "route_admission_digest": (f"{i + 1:x}" * 64)[:64],
                "result": f"bounded leaf {i}",
            }
        )
    return manifest, receipts


class RouteBoundPhysicalReducerTests(unittest.TestCase):
    def test_exact_target3_proves_three_route_bound_leaves(self):
        manifest, receipts = _fixtures()
        out = validate_route_bound_physical_swarm_receipts(
            parent_command_id="target3-parent",
            target_size=3,
            fanout_manifest=manifest,
            child_receipts=receipts,
            expected_provider="deepseek",
            expected_model=DEFAULT_MODEL,
        )
        self.assertTrue(out["physical_fanout_proven"])
        self.assertTrue(out["route_bound"])
        self.assertEqual(3, out["unique_provider_request_count"])
        self.assertEqual(3, out["route_admission_count"])
        self.assertEqual(DEFAULT_MODEL, out["expected_model"])

    def test_missing_expected_model_fails_closed(self):
        manifest, receipts = _fixtures()
        with self.assertRaisesRegex(SwarmIntegrityError, "EXPECTED_MODEL_REQUIRED"):
            validate_route_bound_physical_swarm_receipts(
                parent_command_id="target3-parent",
                target_size=3,
                fanout_manifest=manifest,
                child_receipts=receipts,
                expected_provider="deepseek",
                expected_model="",
            )

    def test_retired_expected_model_fails_closed(self):
        manifest, receipts = _fixtures()
        with self.assertRaisesRegex(SwarmIntegrityError, "EXPECTED_MODEL_RETIRED"):
            validate_route_bound_physical_swarm_receipts(
                parent_command_id="target3-parent",
                target_size=3,
                fanout_manifest=manifest,
                child_receipts=receipts,
                expected_provider="deepseek",
                expected_model="deepseek-chat",
            )

    def test_one_wrong_leaf_route_model_fails(self):
        manifest, receipts = _fixtures()
        receipts[1]["route_model"] = "deepseek-v4-pro"
        with self.assertRaisesRegex(SwarmIntegrityError, "CHILD_ROUTE_MODEL_MISMATCH"):
            validate_route_bound_physical_swarm_receipts(
                parent_command_id="target3-parent",
                target_size=3,
                fanout_manifest=manifest,
                child_receipts=receipts,
                expected_provider="deepseek",
                expected_model=DEFAULT_MODEL,
            )

    def test_duplicate_route_admission_digest_fails(self):
        manifest, receipts = _fixtures()
        receipts[2]["route_admission_digest"] = receipts[0]["route_admission_digest"]
        with self.assertRaisesRegex(SwarmIntegrityError, "CHILD_ROUTE_ADMISSION_DUPLICATE"):
            validate_route_bound_physical_swarm_receipts(
                parent_command_id="target3-parent",
                target_size=3,
                fanout_manifest=manifest,
                child_receipts=receipts,
                expected_provider="deepseek",
                expected_model=DEFAULT_MODEL,
            )

    def test_provider_request_identity_still_must_be_unique(self):
        manifest, receipts = _fixtures()
        receipts[2]["provider_request_id"] = receipts[0]["provider_request_id"]
        with self.assertRaisesRegex(SwarmIntegrityError, "PROVIDER_REQUEST_ID_MISSING_OR_DUPLICATE"):
            validate_route_bound_physical_swarm_receipts(
                parent_command_id="target3-parent",
                target_size=3,
                fanout_manifest=manifest,
                child_receipts=receipts,
                expected_provider="deepseek",
                expected_model=DEFAULT_MODEL,
            )


if __name__ == "__main__":
    unittest.main()
