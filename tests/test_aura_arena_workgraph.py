import unittest

from aura_arena_workgraph import (
    WORKGRAPH_SCHEMA,
    WorkGraphError,
    apply_action,
    continuity_tick,
    eligible_cells,
    project_workgraph,
)


def state():
    return {
        "schema": WORKGRAPH_SCHEMA,
        "project_id": "CS-PROJ-001",
        "mission_ref": "CS-HARNESS-001",
        "currentness_ref": "HEAD-R1",
        "workers": [
            {"worker_id": "W-A", "capabilities": ["CODE", "VERIFY"], "currentness_ref": "HEAD-R1", "joined": True},
            {"worker_id": "W-B", "capabilities": ["MEDIA"], "currentness_ref": "HEAD-R1", "joined": True},
        ],
        "cells": [
            {"cell_id": "A", "state": "OPEN", "priority": "P0", "required_capabilities": ["CODE"], "reuse_value": 5},
            {"cell_id": "B", "state": "OPEN", "priority": "P1", "dependencies": ["A"], "required_capabilities": ["VERIFY"]},
            {"cell_id": "C", "state": "OPEN", "priority": "P0", "required_capabilities": ["MEDIA"], "reuse_value": 1},
        ],
        "claims": [],
    }


class WorkGraphHarnessTests(unittest.TestCase):
    def test_dependency_and_capability_filter(self):
        p = project_workgraph(state(), now_ms=100)
        self.assertEqual([c["cell_id"] for c in eligible_cells(p, worker_id="W-A")], ["A"])
        self.assertEqual([c["cell_id"] for c in eligible_cells(p, worker_id="W-B")], ["C"])
        b = next(c for c in p["cells"] if c["cell_id"] == "B")
        self.assertEqual(b["effective_state"], "BLOCKED")

    def test_claim_prevents_duplicate_selection(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s2, _ = apply_action(s, action={
            "action": "CLAIM", "cell_id": "A", "worker_id": "W-A",
            "basis_graph_digest": p["graph_digest"], "lease_ms": 1000
        }, now_ms=100)
        p2 = project_workgraph(s2, now_ms=101)
        self.assertNotIn("A", [c["cell_id"] for c in eligible_cells(p2, worker_id="W-A")])
        self.assertEqual(continuity_tick(p2, worker_id="W-A")["disposition"], "CURRENT_CLAIM_ACTIVE")

    def test_stale_claim_reopens_without_liveness_claim(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s2, _ = apply_action(s, action={
            "action": "CLAIM", "cell_id": "A", "worker_id": "W-A",
            "basis_graph_digest": p["graph_digest"], "lease_ms": 10
        }, now_ms=100)
        p2 = project_workgraph(s2, now_ms=111)
        a = next(c for c in p2["cells"] if c["cell_id"] == "A")
        self.assertEqual(a["effective_state"], "OPEN")
        self.assertFalse(a["runtime_execution_proven"])
        self.assertEqual(p2["stale_claims"][0]["recovery_code"], "STALE_CLAIM_RECOVERED")

    def test_complete_unlocks_dependency(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action={
            "action":"CLAIM","cell_id":"A","worker_id":"W-A",
            "basis_graph_digest":p["graph_digest"],"lease_ms":1000
        }, now_ms=100)
        p = project_workgraph(s, now_ms=101)
        s, _ = apply_action(s, action={
            "action":"COMPLETE","cell_id":"A","worker_id":"W-A",
            "basis_graph_digest":p["graph_digest"]
        }, now_ms=101)
        p = project_workgraph(s, now_ms=102)
        self.assertIn("B", [c["cell_id"] for c in eligible_cells(p, worker_id="W-A")])

    def test_no_change_tick_never_calls_model_or_delivery(self):
        p = project_workgraph(state(), now_ms=100)
        tick = continuity_tick(p, worker_id="W-A", previous_graph_digest=p["graph_digest"])
        self.assertEqual(tick["disposition"], "NO_CHANGE_NO_MODEL")
        self.assertFalse(tick["delivery_required"])
        self.assertFalse(tick["model_call_required_for_scheduler_tick"])

    def test_changed_tick_selects_highest_eligible(self):
        p = project_workgraph(state(), now_ms=100)
        tick = continuity_tick(p, worker_id="W-A", previous_graph_digest="older")
        self.assertEqual(tick["selected_cell_id"], "A")
        self.assertTrue(tick["delivery_required"])
        self.assertTrue(tick["requires_external_authorized_turn_delivery"])
        self.assertFalse(tick["runtime_execution_proven"])

    def test_stale_basis_rejected(self):
        with self.assertRaisesRegex(WorkGraphError, "STALE_GRAPH_BASIS"):
            apply_action(state(), action={
                "action":"CLAIM","cell_id":"A","worker_id":"W-A",
                "basis_graph_digest":"0"*64
            }, now_ms=100)

    def test_collision_fails_closed(self):
        s = state()
        s["claims"] = [
            {"claim_id":"c1","cell_id":"A","worker_id":"W-A","claimed_at_ms":0,"lease_expires_at_ms":1000,"active":True},
            {"claim_id":"c2","cell_id":"A","worker_id":"W-B","claimed_at_ms":0,"lease_expires_at_ms":1000,"active":True},
        ]
        p = project_workgraph(s, now_ms=100)
        a = next(c for c in p["cells"] if c["cell_id"] == "A")
        self.assertEqual(a["effective_state"], "BLOCKED")
        self.assertIn("ACTIVE_CLAIM_COLLISION_FAIL_CLOSED", a["projection_reasons"])

    def test_dependency_cycle_rejected(self):
        s = state()
        s["cells"][0]["dependencies"] = ["B"]
        with self.assertRaisesRegex(WorkGraphError, "CELL_DEPENDENCY_CYCLE"):
            project_workgraph(s, now_ms=100)

    def test_currentness_mismatch_blocks_worker(self):
        s = state()
        s["workers"][0]["currentness_ref"] = "STALE"
        p = project_workgraph(s, now_ms=100)
        self.assertEqual(eligible_cells(p, worker_id="W-A"), [])
        self.assertEqual(continuity_tick(p, worker_id="W-A")["disposition"], "SUPERSEDED_CURRENTNESS")

    def test_add_successor_cell_cas(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s2, receipt = apply_action(s, action={
            "action":"ADD_CELL",
            "worker_id":"W-A",
            "basis_graph_digest":p["graph_digest"],
            "cell":{"cell_id":"D","state":"OPEN","priority":"P1","dependencies":["A"],"required_capabilities":["CODE"]}
        }, now_ms=100)
        self.assertIn("D", {c["cell_id"] for c in s2["cells"]})
        self.assertEqual(receipt["action"], "ADD_CELL")
        self.assertFalse(receipt["runtime_execution_proven"])

    def test_clock_only_change_does_not_change_digest(self):
        p1 = project_workgraph(state(), now_ms=100)
        p2 = project_workgraph(state(), now_ms=101)
        self.assertEqual(p1["graph_digest"], p2["graph_digest"])

    def test_stale_boundary_changes_digest(self):
        s = state()
        p = project_workgraph(s, now_ms=100)
        s, _ = apply_action(s, action={
            "action":"CLAIM","cell_id":"A","worker_id":"W-A",
            "basis_graph_digest":p["graph_digest"],"lease_ms":10
        }, now_ms=100)
        before = project_workgraph(s, now_ms=109)
        after = project_workgraph(s, now_ms=110)
        self.assertNotEqual(before["graph_digest"], after["graph_digest"])

    def test_provider_effect_cells_not_autonomous(self):
        s = state()
        s["cells"][0]["effect_class"] = "D1"
        p = project_workgraph(s, now_ms=100)
        self.assertNotIn("A", [c["cell_id"] for c in eligible_cells(p, worker_id="W-A")])


if __name__ == "__main__":
    unittest.main()
