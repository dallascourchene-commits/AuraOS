from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from host_receipt_registry import HostReceiptError, HostReceiptRegistry, RECEIPT_SCHEMA


def manifest():
    m={
        "schema": "AuraPhysicalSwarmCompileReceiptV1",
        "parent_command_id": "parent",
        "parent_idempotency_key": "parent-idem",
        "parent_payload_digest": "c" * 64,
        "target_size": 1,
        "child_count": 1,
        "child_refs": [{
            "command_id": "child-A",
            "idempotency_key": "child-A-idem",
            "role_id": "A+",
            "worker_id": "W-A",
            "ordinal": 0,
        }],
        "manifest_digest": "PENDING",
        "effect_started": False,
    }
    body={"schema":m["schema"],"parent_command_id":m["parent_command_id"],"parent_idempotency_key":m["parent_idempotency_key"],"parent_payload_digest":m["parent_payload_digest"],"target_size":m["target_size"],"children":m["child_refs"]}
    m["manifest_digest"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    return m


def make_registry(tmp):
    return HostReceiptRegistry(Path(tmp) / "registry.jsonl", host_instance_id="host-1", executor_id="executor-1")


def make_plan(reg):
    return reg.allocate_plan(
        manifest(),
        fanout_id="fanout-1",
        objective_id="work-1",
        source_generation="GEN25",
        command_digests_by_id={"child-A": "a" * 64},
    )


def receipt(plan, **overrides):
    child = plan.children[0]
    out = {
        "receipt_schema": RECEIPT_SCHEMA,
        "receipt_id": "receipt-A",
        "command_id": child["command_id"],
        "idempotency_key": child["idempotency_key"],
        "parent_command_id": "parent",
        "fanout_id": child["fanout_id"],
        "cohort_id": "cohort-1",
        "attempt_id": child["attempt_id"],
        "worker_id": child["worker_id"],
        "worker_instance_id": "W-A#1",
        "role_id": child["role_id"],
        "role_instance_id": child["role_instance_id"],
        "objective_id": child["objective_id"],
        "work_order_id": "work-1",
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "source_generation": child["source_generation"],
        "command_digest": child["command_digest"],
        "parent_payload_digest": child["parent_payload_digest"],
        "plan_digest": child["plan_digest"],
        "manifest_digest": child["manifest_digest"],
        "route_admission_digest": "d" * 64,
        "ordinal": child["ordinal"],
        "effect_kind": "MODEL_OUTPUT_ONLY",
        "artifact_identity": "leaf-A",
        "result_digest": "b" * 64,
        "provider_request_id": "request-A",
        "observed_at": "2026-09-02T18:00:00Z",
        "event_seq": 1,
        "execution_state": "COMMITTED",
        "reconcile_key": "reconcile-A",
        "host_instance_id": "host-1",
        "executor_id": "executor-1",
    }
    out.update(overrides)
    return out


class HostReceiptRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = make_registry(self.tmp.name)
        self.plan = make_plan(self.registry)
        self.child = dict(self.plan.children[0])

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_current_receipt_resolves(self):
        self.registry.record(receipt(self.plan))
        projection = self.registry.resolve(self.plan, self.child, required_evidence=("provider_request_id", "result_digest"))
        self.registry.assert_owned_projection(projection)
        self.assertEqual("receipt-A", projection.records[-1]["receipt_id"])

    def test_sibling_command_is_invisible(self):
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_CHILD_NOT_IN_HOST_PLAN"):
            self.registry.record(receipt(self.plan, command_id="child-B", receipt_id="receipt-B"))

    def test_previous_attempt_is_invisible(self):
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_CHILD_NOT_IN_HOST_PLAN"):
            self.registry.record(receipt(self.plan, attempt_id="attempt-old", receipt_id="receipt-old"))

    def test_wrong_fanout_is_invisible(self):
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_CHILD_NOT_IN_HOST_PLAN"):
            self.registry.record(receipt(self.plan, fanout_id="fanout-old", receipt_id="receipt-old"))

    def test_wrong_role_instance_is_invisible(self):
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_CHILD_NOT_IN_HOST_PLAN"):
            self.registry.record(receipt(self.plan, role_instance_id="other-role", receipt_id="receipt-other"))

    def test_wrong_objective_is_invisible(self):
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_CHILD_NOT_IN_HOST_PLAN"):
            self.registry.record(receipt(self.plan, objective_id="other-work", receipt_id="receipt-other"))

    def test_wrong_source_generation_is_invisible(self):
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_CHILD_NOT_IN_HOST_PLAN"):
            self.registry.record(receipt(self.plan, source_generation="GEN24", receipt_id="receipt-old"))

    def test_wrong_command_digest_is_invisible(self):
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_CHILD_NOT_IN_HOST_PLAN"):
            self.registry.record(receipt(self.plan, command_digest="f" * 64, receipt_id="receipt-wrong"))

    def test_untrusted_free_form_projection_cannot_be_minted(self):
        self.registry.record(receipt(self.plan))
        projection = self.registry.resolve(self.plan, self.child)
        forged = copy.copy(projection)
        object.__setattr__(forged, "_seal", object())
        with self.assertRaisesRegex(HostReceiptError, "UNTRUSTED_RECEIPT_PROJECTION"):
            self.registry.assert_owned_projection(forged)

    def test_untrusted_execution_plan_rejected(self):
        forged = copy.copy(self.plan)
        object.__setattr__(forged, "_seal", object())
        with self.assertRaisesRegex(HostReceiptError, "UNTRUSTED_EXECUTION_PLAN"):
            self.registry.resolve(forged, self.child)

    def test_duplicate_receipt_id_rejected(self):
        self.registry.record(receipt(self.plan))
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_ID_REPLAY"):
            self.registry.record(receipt(self.plan, event_seq=2))

    def test_event_sequence_must_be_monotonic(self):
        with self.assertRaisesRegex(HostReceiptError, "EVENT_SEQ_NOT_NEXT"):
            self.registry.record(receipt(self.plan, event_seq=2))

    def test_failed_receipt_does_not_authorize(self):
        self.registry.record(receipt(self.plan, execution_state="FAILED", result_digest="NONE"))
        with self.assertRaisesRegex(HostReceiptError, "EXACT_HOST_RECEIPT_MISSING"):
            self.registry.resolve(self.plan, self.child)

    def test_stub_receipt_missing_substantive_digest_rejected_at_record(self):
        with self.assertRaisesRegex(HostReceiptError, "RESULT_DIGEST_INVALID"):
            self.registry.record(receipt(self.plan, result_digest="not-a-digest"))

    def test_host_instance_mismatch_rejected(self):
        with self.assertRaisesRegex(HostReceiptError, "HOST_INSTANCE_MISMATCH"):
            self.registry.record(receipt(self.plan, host_instance_id="other-host"))

    def test_executor_identity_mismatch_rejected(self):
        with self.assertRaisesRegex(HostReceiptError, "EXECUTOR_ID_MISMATCH"):
            self.registry.record(receipt(self.plan, executor_id="other-executor"))

    def test_receipt_for_non_host_plan_is_rejected(self):
        bad = receipt(self.plan, plan_digest="f" * 64)
        with self.assertRaisesRegex(HostReceiptError, "RECEIPT_PLAN_NOT_HOST_OWNED"):
            self.registry.record(bad)

    def test_restart_reloads_plan_and_receipt(self):
        self.registry.record(receipt(self.plan))
        reopened = make_registry(self.tmp.name)
        plan2 = reopened.get_plan(self.plan.plan_digest)
        projection = reopened.resolve(plan2, plan2.children[0])
        reopened.assert_owned_projection(projection)
        self.assertEqual(1, projection.records[-1]["event_seq"])


if __name__ == "__main__":
    unittest.main()
