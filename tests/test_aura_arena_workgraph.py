import unittest

from aura_arena_workgraph import (
    WORKGRAPH_SCHEMA,
    WorkGraphError,
    apply_action,
    continuity_tick,
    eligible_cells,
    project_workgraph,
)


def cell(
    cell_id,
    *,
    state="OPEN",
    priority="P1",
    dependencies=(),
    capabilities=(),
    effect_class="D0",
    execution_state="NOT_STARTED",
    reuse_value=0,
):
    return {
        "cell_id": cell_id,
        "parent_objective": "HARNESS-G2",
        "state": state,
        "priority": priority,
        "dependencies": list(dependencies),
        "required_capabilities": list(capabilities),
        "effect_class": effect_class,
        "reuse_value": reuse_value,
        "estimated_effort": 1,
        "cost_ceiling_provider_usd": 0.0,
        "free_first_route": ["R0_REUSE", "R1_DETERMINISTIC"],
        "expected_output": f"receipt:{cell_id}",
        "acceptance": ["TESTS_PASS"],
        "currentness_ref": "HEAD-R1",
        "reopen_conditions": ["CURRENTNESS_CHANGE"],
        "execution_state": execution_state,
        "execution_receipt_refs": [],
    }


def state():
    return {
        "schema": WORKGRAPH_SCHEMA,
        "project_id": "CS-PROJ-001",
        "mission_ref": "CS-HARNESS-001",
        "canonical_orientation_ref": "DRIVE:FRONT-DOOR",
        "board_ref": "DRIVE:COLLAB-BOARD",
        "board_revision": "REV-1",
        "route_policy_ref": "DRIVE:ROUTE-POLICY",
        "source_digests": ["sha256:source"],
        "currentness_ref": "HEAD-R1",
        "workers": [
            {
                "worker_id": "W-A",
                "worker_class": "CHATGPT",
                "capabilities": ["CODE", "VERIFY"],
                "currentness_ref": "HEAD-R1",
                "joined": True,
                "state": "IDLE",
                "effect_ceiling": "D0",
            },
            {
                "worker_id": "W-B",
                "worker_class": "CHATGPT",
                "capabilities": ["MEDIA"],
                "currentness_ref": "HEAD-R1",
                "joined": True,
                "state": "IDLE",
                "effect_ceiling": "D0",
            },
        ],
        "cells": [
            cell("A", priority="P0", capabilities=("CODE",), reuse_value=5),
            cell("B", dependencies=("A",), capabilities=("VERIFY",)),
            cell("C", priority="P0", capabilities=("MEDIA",), reuse_value=1),
        ],
        "claims": [],
    }


def claim_action(p, cell_id="A", worker_id="W-A", lease_ms=1000):
    return {
        "action": "CLAIM",
        "cell_id": cell_id,
        "worker_id": worker_id,
        "basis_graph_digest": p["graph_digest"],
        "lease_ms": lease_ms,
    }


class WorkGraphHarnessTests(unittest.TestCase):
    def test_01_dependency_and_capability_filter(self):
        p = project_workgraph(state(), now_ms=100)
        self.assertEqual([c["cell_id"] for c in eligible_cells(p, worker_id="W-A")], ["A"])
        self.assertEqual([c["cell_id"] for c in eligible_cells(p, worker_id="W-B")], ["C"])
        b = next(c for c in p["cells"] if c["cell_id"] == "B")
        self.assertEqual(b["effective_state"], "BLOCKED")

    def test_02_claim_prevents_duplicate_selection(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s2, _ = apply_action(s, action=claim_action(p), now_ms=100)
        p2 = project_workgraph(s2, now_ms=101)
        self.assertNotIn("A", [c["cell_id"] for c in eligible_cells(p2, worker_id="W-A")])
        self.assertEqual(continuity_tick(p2, worker_id="W-A")["disposition"], "CURRENT_CLAIM_ACTIVE")

    def test_03_stale_claim_not_started_reopens(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action=claim_action(p, lease_ms=10), now_ms=100)
        p2 = project_workgraph(s, now_ms=110)
        a = next(c for c in p2["cells"] if c["cell_id"] == "A")
        self.assertEqual(a["effective_state"], "OPEN")
        self.assertEqual(p2["stale_claims"][0]["recovery_code"], "STALE_CLAIM_RECOVERED")
        self.assertFalse(a["runtime_execution_proven"])

    def test_04_stale_claim_unknown_effect_blocks_replay(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action=claim_action(p, lease_ms=10), now_ms=100)
        for row in s["cells"]:
            if row["cell_id"] == "A":
                row["execution_state"] = "UNKNOWN"
        p2 = project_workgraph(s, now_ms=110)
        a = next(c for c in p2["cells"] if c["cell_id"] == "A")
        self.assertEqual(a["effective_state"], "BLOCKED")
        self.assertIn("RECONCILE_EFFECT_STATE_REQUIRED", a["projection_reasons"])
        self.assertEqual(p2["stale_claims"][0]["recovery_code"], "RECONCILE_EFFECT_STATE_REQUIRED")

    def test_05_complete_requires_acceptance_and_output_evidence(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action=claim_action(p), now_ms=100)
        p = project_workgraph(s, now_ms=101)
        with self.assertRaisesRegex(WorkGraphError, "COMPLETE_EVIDENCE_REQUIRED"):
            apply_action(s, action={
                "action": "COMPLETE", "cell_id": "A", "worker_id": "W-A",
                "basis_graph_digest": p["graph_digest"],
            }, now_ms=101)

    def test_06_complete_unlocks_dependency_and_preserves_receipts(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action=claim_action(p), now_ms=100)
        p = project_workgraph(s, now_ms=101)
        s, _ = apply_action(s, action={
            "action": "COMPLETE", "cell_id": "A", "worker_id": "W-A",
            "basis_graph_digest": p["graph_digest"],
            "acceptance_refs": ["TEST:14OF14"],
            "output_refs": ["PR:313"],
        }, now_ms=101)
        p = project_workgraph(s, now_ms=102)
        self.assertIn("B", [c["cell_id"] for c in eligible_cells(p, worker_id="W-A")])
        a = next(c for c in p["cells"] if c["cell_id"] == "A")
        self.assertEqual(a["execution_state"], "VERIFIED_COMPLETE")
        self.assertEqual(a["execution_receipt_refs"], ["PR:313", "TEST:14OF14"])

    def test_07_no_change_tick_is_zero_model_and_zero_delivery(self):
        p = project_workgraph(state(), now_ms=100)
        tick = continuity_tick(p, worker_id="W-A", previous_graph_digest=p["graph_digest"])
        self.assertEqual(tick["disposition"], "NO_CHANGE_NO_MODEL")
        self.assertFalse(tick["delivery_required"])
        self.assertFalse(tick["model_call_required_for_scheduler_tick"])
        self.assertFalse(tick["effect_allowed"])

    def test_08_changed_tick_selects_highest_eligible_and_only_emits_intent(self):
        p = project_workgraph(state(), now_ms=100)
        tick = continuity_tick(p, worker_id="W-A", previous_graph_digest="older")
        self.assertEqual(tick["selected_cell_id"], "A")
        self.assertEqual(tick["decision"], "SELECT_WORK")
        self.assertTrue(tick["delivery_required"])
        self.assertTrue(tick["requires_external_authorized_turn_delivery"])
        self.assertFalse(tick["runtime_execution_proven"])

    def test_09_stale_graph_basis_rejected(self):
        with self.assertRaisesRegex(WorkGraphError, "STALE_GRAPH_BASIS"):
            apply_action(state(), action={
                "action": "CLAIM", "cell_id": "A", "worker_id": "W-A",
                "basis_graph_digest": "0" * 64,
            }, now_ms=100)

    def test_10_collision_fails_closed(self):
        s = state()
        s["claims"] = [
            {
                "claim_id": "c1", "cell_id": "A", "worker_id": "W-A",
                "claimed_at_ms": 0, "lease_expires_at_ms": 1000,
                "basis_graph_digest": "a" * 64, "currentness_ref": "HEAD-R1",
                "dependency_snapshot": [], "capability_snapshot": ["CODE", "VERIFY"],
                "active": True,
            },
            {
                "claim_id": "c2", "cell_id": "A", "worker_id": "W-B",
                "claimed_at_ms": 0, "lease_expires_at_ms": 1000,
                "basis_graph_digest": "b" * 64, "currentness_ref": "HEAD-R1",
                "dependency_snapshot": [], "capability_snapshot": ["MEDIA"],
                "active": True,
            },
        ]
        p = project_workgraph(s, now_ms=100)
        a = next(c for c in p["cells"] if c["cell_id"] == "A")
        self.assertEqual(a["effective_state"], "BLOCKED")
        self.assertIn("ACTIVE_CLAIM_COLLISION_FAIL_CLOSED", a["projection_reasons"])

    def test_11_dependency_cycle_rejected(self):
        s = state()
        s["cells"][0]["dependencies"] = ["B"]
        with self.assertRaisesRegex(WorkGraphError, "CELL_DEPENDENCY_CYCLE"):
            project_workgraph(s, now_ms=100)

    def test_12_currentness_mismatch_requires_rebase(self):
        s = state()
        s["workers"][0]["currentness_ref"] = "STALE"
        p = project_workgraph(s, now_ms=100)
        self.assertEqual(eligible_cells(p, worker_id="W-A"), [])
        self.assertEqual(continuity_tick(p, worker_id="W-A")["decision"], "REBASE")

    def test_13_add_successor_cell_is_cas_bound(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        d = cell("D", dependencies=("A",), capabilities=("CODE",))
        s2, receipt = apply_action(s, action={
            "action": "ADD_CELL", "worker_id": "W-A",
            "basis_graph_digest": p["graph_digest"], "cell": d,
        }, now_ms=100)
        self.assertIn("D", {c["cell_id"] for c in s2["cells"]})
        self.assertEqual(receipt["action"], "ADD_CELL")
        self.assertFalse(receipt["runtime_execution_proven"])

    def test_14_clock_only_movement_does_not_change_graph_digest(self):
        p1 = project_workgraph(state(), now_ms=100)
        p2 = project_workgraph(state(), now_ms=101)
        self.assertEqual(p1["graph_digest"], p2["graph_digest"])

    def test_15_lease_expiry_boundary_changes_graph_digest(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action=claim_action(p, lease_ms=10), now_ms=100)
        before = project_workgraph(s, now_ms=109)
        after = project_workgraph(s, now_ms=110)
        self.assertNotEqual(before["graph_digest"], after["graph_digest"])

    def test_16_d1_effect_cell_not_autonomously_selected(self):
        s = state()
        s["cells"][0]["effect_class"] = "D1"
        p = project_workgraph(s, now_ms=100)
        self.assertNotIn("A", [c["cell_id"] for c in eligible_cells(p, worker_id="W-A")])

    def test_17_record_execution_requires_bound_receipt(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action=claim_action(p), now_ms=100)
        p = project_workgraph(s, now_ms=101)
        with self.assertRaisesRegex(WorkGraphError, "EXECUTION_RECEIPT_REQUIRED"):
            apply_action(s, action={
                "action": "RECORD_EXECUTION", "cell_id": "A", "worker_id": "W-A",
                "basis_graph_digest": p["graph_digest"], "execution_state": "EFFECT_ADMITTED",
            }, now_ms=101)

    def test_18_release_after_effect_started_requires_reconciliation(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action=claim_action(p), now_ms=100)
        for next_state, ref, now in [
            ("EFFECT_ADMITTED", "ACK:1", 101),
            ("EFFECT_STARTED", "EFFECT:1", 102),
        ]:
            p = project_workgraph(s, now_ms=now)
            s, _ = apply_action(s, action={
                "action": "RECORD_EXECUTION", "cell_id": "A", "worker_id": "W-A",
                "basis_graph_digest": p["graph_digest"], "execution_state": next_state,
                "receipt_refs": [ref],
            }, now_ms=now)
        p = project_workgraph(s, now_ms=103)
        with self.assertRaisesRegex(WorkGraphError, "RECONCILE_EFFECT_STATE_REQUIRED"):
            apply_action(s, action={
                "action": "RELEASE", "cell_id": "A", "worker_id": "W-A",
                "basis_graph_digest": p["graph_digest"],
            }, now_ms=103)

    def test_19_historical_complete_cannot_be_silently_reopened(self):
        s = state()
        s["cells"][0]["state"] = "COMPLETE"
        s["cells"][0]["execution_state"] = "VERIFIED_COMPLETE"
        s["cells"][0]["execution_receipt_refs"] = ["RECEIPT:OLD"]
        p = project_workgraph(s, now_ms=100)
        with self.assertRaisesRegex(WorkGraphError, "HISTORICAL_COMPLETION_REQUIRES_SUCCESSOR"):
            apply_action(s, action={
                "action": "REOPEN", "cell_id": "A", "worker_id": "W-A",
                "basis_graph_digest": p["graph_digest"],
            }, now_ms=100)

    def test_20_block_requires_reason_and_can_reopen_when_no_effect_started(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action=claim_action(p), now_ms=100)
        p = project_workgraph(s, now_ms=101)
        s, _ = apply_action(s, action={
            "action": "BLOCK", "cell_id": "A", "worker_id": "W-A",
            "basis_graph_digest": p["graph_digest"],
            "blocker_reason": "DEPENDENCY_CHANGED",
            "reopen_condition": "dependency closes",
        }, now_ms=101)
        p = project_workgraph(s, now_ms=102)
        self.assertEqual(next(c for c in p["cells"] if c["cell_id"] == "A")["effective_state"], "BLOCKED")
        s, _ = apply_action(s, action={
            "action": "REOPEN", "cell_id": "A", "worker_id": "W-A",
            "basis_graph_digest": p["graph_digest"],
        }, now_ms=102)
        self.assertEqual(next(c for c in s["cells"] if c["cell_id"] == "A")["state"], "OPEN")

    def test_21_unknown_execution_state_is_not_selectable(self):
        s = state()
        s["cells"][0]["execution_state"] = "UNKNOWN"
        p = project_workgraph(s, now_ms=100)
        self.assertNotIn("A", [c["cell_id"] for c in eligible_cells(p, worker_id="W-A")])

    def test_22_worker_action_fails_on_stale_currentness(self):
        s = state()
        s["workers"][0]["currentness_ref"] = "OLD"
        p = project_workgraph(s, now_ms=100)
        with self.assertRaisesRegex(WorkGraphError, "ACTION_WORKER_STALE_CURRENTNESS"):
            apply_action(s, action={
                "action": "ADD_CELL", "worker_id": "W-A",
                "basis_graph_digest": p["graph_digest"],
                "cell": cell("D", capabilities=("CODE",)),
            }, now_ms=100)


if __name__ == "__main__":
    unittest.main()
