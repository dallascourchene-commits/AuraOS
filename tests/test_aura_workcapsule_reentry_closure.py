from __future__ import annotations

import copy
import unittest

from scripts.aura_workcapsule_context_binding import ACTIVE, COLD, CURRENT, STALE, compile_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_closure import (
    CLOSED,
    HOLD,
    compile_reentry_closure,
    verify_reentry_closure,
)
from scripts.aura_workcapsule_reentry_invalidation import (
    FULL_GRAPH,
    NONE,
    SELECTED_SOURCES,
    compile_reentry_invalidation,
)


def identity(value: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "TEST_V1",
        "scope_profile": "TEST_SCOPE",
        "value": value,
        "schema_version": "1",
    }


class WorkCapsuleReentryClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule = {
            "capsule_id": "CAP-O10-1",
            "capsule_generation": 4,
            "parent_work_order_interface_binding_generation": 6,
            "execution_basis_identity": identity("basis-o10"),
        }
        self.graph = {
            "graph_id": "ASTGE-GRAPH-10",
            "graph_generation": 10,
            "graph_basis_identity": identity("graph-10"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:10:CURRENT",
        }
        self.sources = [
            {
                "role": ACTIVE,
                "file_id": 3,
                "relative_path": "src/a.py",
                "source_generation": 1,
                "source_sha256": "a" * 64,
                "source_byte_len": 100,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:3:1",
            },
            {
                "role": ACTIVE,
                "file_id": 4,
                "relative_path": "src/b.py",
                "source_generation": 1,
                "source_sha256": "b" * 64,
                "source_byte_len": 200,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:4:1",
            },
            {
                "role": COLD,
                "file_id": 9,
                "relative_path": "docs/frontier.md",
                "source_generation": 2,
                "source_sha256": "c" * 64,
                "source_byte_len": 50,
                "currentness": "UNKNOWN",
                "witness_ref": "SOURCE:9:UNKNOWN",
            },
        ]
        self.previous = self.binding(self.graph, self.sources)

    def binding(self, graph, sources):
        return compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=copy.deepcopy(graph),
            source_witnesses=copy.deepcopy(sources),
        )

    def selected_plan(self):
        observed = copy.deepcopy(self.sources)
        observed[0]["currentness"] = STALE
        observed[0]["witness_ref"] = "SOURCE:3:STALE"
        return compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=observed,
        )

    def test_none_scope_closes_with_same_active_basis_even_if_cold_frontier_changes(self):
        observed = copy.deepcopy(self.sources)
        observed[2]["currentness"] = STALE
        observed[2]["source_generation"] = 3
        observed[2]["source_sha256"] = "d" * 64
        plan = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=observed,
        )
        self.assertEqual(NONE, plan["minimum_reentry_scope"])
        candidate = self.binding(self.graph, observed)
        receipt = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=plan,
            candidate_binding=candidate,
        )
        self.assertEqual(CLOSED, receipt["closure_status"])
        self.assertEqual([], verify_reentry_closure(receipt))

    def test_selected_source_rebind_closes_when_only_selected_active_identity_changes(self):
        plan = self.selected_plan()
        self.assertEqual(SELECTED_SOURCES, plan["minimum_reentry_scope"])
        rebound = copy.deepcopy(self.sources)
        rebound[0]["source_generation"] = 2
        rebound[0]["source_sha256"] = "d" * 64
        rebound[0]["source_byte_len"] = 101
        rebound[0]["witness_ref"] = "SOURCE:3:2:CURRENT"
        candidate = self.binding(self.graph, rebound)
        receipt = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=plan,
            candidate_binding=candidate,
        )
        self.assertEqual(CLOSED, receipt["closure_status"])
        self.assertTrue(receipt["unaffected_active_basis_preserved"])
        self.assertEqual([], verify_reentry_closure(receipt))

    def test_selected_rebind_holds_if_retained_active_source_changes(self):
        plan = self.selected_plan()
        rebound = copy.deepcopy(self.sources)
        rebound[0]["source_generation"] = 2
        rebound[0]["source_sha256"] = "d" * 64
        rebound[1]["source_generation"] = 2
        rebound[1]["source_sha256"] = "e" * 64
        candidate = self.binding(self.graph, rebound)
        receipt = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=plan,
            candidate_binding=candidate,
        )
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertTrue(any(reason.startswith("RETAINED_ACTIVE_SOURCE_CHANGED:4:") for reason in receipt["closure_reasons"]))
        self.assertEqual([], verify_reentry_closure(receipt))

    def test_selected_rebind_holds_if_graph_changes(self):
        plan = self.selected_plan()
        rebound = copy.deepcopy(self.sources)
        rebound[0]["source_generation"] = 2
        rebound[0]["source_sha256"] = "d" * 64
        graph = copy.deepcopy(self.graph)
        graph["graph_generation"] = 11
        graph["graph_basis_identity"] = identity("graph-11")
        graph["witness_ref"] = "GRAPH:11:CURRENT"
        candidate = self.binding(graph, rebound)
        receipt = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=plan,
            candidate_binding=candidate,
        )
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertIn("GRAPH_CHANGED_OUTSIDE_FULL_GRAPH_REENTRY", receipt["closure_reasons"])

    def test_dependency_membership_cannot_change_during_closure(self):
        plan = self.selected_plan()
        rebound = copy.deepcopy(self.sources)
        rebound[0]["source_generation"] = 2
        rebound[0]["source_sha256"] = "d" * 64
        rebound.append(
            {
                "role": COLD,
                "file_id": 12,
                "relative_path": "docs/new.md",
                "source_generation": 1,
                "source_sha256": "f" * 64,
                "source_byte_len": 10,
                "currentness": "UNKNOWN",
                "witness_ref": "SOURCE:12:UNKNOWN",
            }
        )
        candidate = self.binding(self.graph, rebound)
        receipt = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=plan,
            candidate_binding=candidate,
        )
        self.assertEqual(HOLD, receipt["closure_status"])
        self.assertIn("DEPENDENCY_MEMBERSHIP_OR_ROLE_CHANGED", receipt["closure_reasons"])

    def test_full_graph_reentry_can_close_on_new_current_graph_identity(self):
        observed_graph = copy.deepcopy(self.graph)
        observed_graph["currentness"] = STALE
        observed_graph["witness_ref"] = "GRAPH:10:STALE"
        plan = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=observed_graph,
            observed_source_witnesses=self.sources,
        )
        self.assertEqual(FULL_GRAPH, plan["minimum_reentry_scope"])
        rebound_graph = copy.deepcopy(self.graph)
        rebound_graph["graph_generation"] = 11
        rebound_graph["graph_basis_identity"] = identity("graph-11")
        rebound_graph["witness_ref"] = "GRAPH:11:CURRENT"
        candidate = self.binding(rebound_graph, self.sources)
        receipt = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=plan,
            candidate_binding=candidate,
        )
        self.assertEqual(CLOSED, receipt["closure_status"])
        self.assertEqual([], verify_reentry_closure(receipt))

    def test_full_graph_revalidation_may_restore_same_identity(self):
        observed_graph = copy.deepcopy(self.graph)
        observed_graph["currentness"] = STALE
        observed_graph["witness_ref"] = "GRAPH:10:STALE"
        plan = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=observed_graph,
            observed_source_witnesses=self.sources,
        )
        candidate = self.binding(self.graph, self.sources)
        receipt = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=plan,
            candidate_binding=candidate,
        )
        self.assertEqual(CLOSED, receipt["closure_status"])

    def test_plan_from_different_previous_binding_is_rejected(self):
        other_capsule = copy.deepcopy(self.capsule)
        other_capsule["capsule_generation"] = 99
        other_previous = compile_workcapsule_context_binding(
            capsule=other_capsule,
            graph_witness=self.graph,
            source_witnesses=self.sources,
        )
        observed = copy.deepcopy(self.sources)
        observed[0]["currentness"] = STALE
        plan = compile_reentry_invalidation(
            previous_binding=other_previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=observed,
        )
        with self.assertRaisesRegex(ValueError, "does not bind the supplied previous_binding"):
            compile_reentry_closure(
                previous_binding=self.previous,
                reentry_receipt=plan,
                candidate_binding=self.previous,
            )

    def test_candidate_capsule_basis_cannot_change_inside_reentry_closure(self):
        plan = self.selected_plan()
        changed_capsule = copy.deepcopy(self.capsule)
        changed_capsule["capsule_generation"] = 5
        candidate = compile_workcapsule_context_binding(
            capsule=changed_capsule,
            graph_witness=self.graph,
            source_witnesses=self.sources,
        )
        with self.assertRaisesRegex(ValueError, "changed capsule identity/basis"):
            compile_reentry_closure(
                previous_binding=self.previous,
                reentry_receipt=plan,
                candidate_binding=candidate,
            )

    def test_closure_authority_and_node_cone_tamper_are_detected(self):
        plan = self.selected_plan()
        rebound = copy.deepcopy(self.sources)
        rebound[0]["source_generation"] = 2
        rebound[0]["source_sha256"] = "d" * 64
        candidate = self.binding(self.graph, rebound)
        receipt = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=plan,
            candidate_binding=candidate,
        )
        receipt["authority"]["commit_authorized"] = True
        receipt["node_level_dependency_cone_proven"] = True
        violations = verify_reentry_closure(receipt)
        self.assertIn("AUTHORITY_MINTED_BY_REENTRY_CLOSURE", violations)
        self.assertIn("UNPROVEN_NODE_CONE_PROMOTED", violations)
        self.assertIn("RECEIPT_IDENTITY_MISMATCH", violations)


if __name__ == "__main__":
    unittest.main()
