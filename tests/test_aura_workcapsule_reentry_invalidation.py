import copy
import unittest

from scripts.aura_workcapsule_context_binding import (
    ACTIVE,
    COLD,
    CURRENT,
    STALE,
    UNKNOWN,
    compile_workcapsule_context_binding,
)
from scripts.aura_workcapsule_reentry_invalidation import (
    FULL_GRAPH,
    NONE,
    SELECTED_SOURCES,
    compile_reentry_invalidation,
    verify_reentry_invalidation,
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


class WorkCapsuleReentryInvalidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule = {
            "capsule_id": "CAP-REENTRY-001",
            "capsule_generation": 8,
            "parent_work_order_interface_binding_generation": 12,
            "execution_basis_identity": identity("execution-basis-8"),
        }
        self.graph = {
            "graph_id": "ASTGE-GRAPH-1",
            "graph_generation": 41,
            "graph_basis_identity": identity("graph-basis-41"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:41:CURRENT",
        }
        self.sources = [
            {
                "role": ACTIVE,
                "file_id": 3,
                "relative_path": "src/alpha.py",
                "source_generation": 9001,
                "source_sha256": "a" * 64,
                "source_byte_len": 123,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:3:GEN9001",
            },
            {
                "role": ACTIVE,
                "file_id": 4,
                "relative_path": "src/beta.py",
                "source_generation": 9002,
                "source_sha256": "b" * 64,
                "source_byte_len": 456,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:4:GEN9002",
            },
            {
                "role": COLD,
                "file_id": 9,
                "relative_path": "docs/frontier.md",
                "source_generation": 12,
                "source_sha256": "c" * 64,
                "source_byte_len": 77,
                "currentness": UNKNOWN,
                "witness_ref": "SOURCE:9:UNKNOWN",
            },
        ]
        self.previous = compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=self.graph,
            source_witnesses=self.sources,
        )
        self.assertTrue(self.previous["context_admitted"])

    def compile(self, *, graph=None, sources=None):
        return compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=graph or self.graph,
            observed_source_witnesses=sources if sources is not None else self.sources,
        )

    def test_unchanged_current_dependencies_require_no_reentry(self):
        receipt = self.compile()
        self.assertEqual(receipt["minimum_reentry_scope"], NONE)
        self.assertFalse(receipt["graph_rebind_required"])
        self.assertEqual(len(receipt["retained_current_active_sources"]), 2)
        self.assertEqual(receipt["selected_source_rebinds"], [])
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_one_stale_active_source_rebinds_only_that_source(self):
        observed = copy.deepcopy(self.sources)
        observed[0]["currentness"] = STALE
        observed[0]["witness_ref"] = "SOURCE:3:STALE"
        receipt = self.compile(sources=observed)
        self.assertEqual(receipt["minimum_reentry_scope"], SELECTED_SOURCES)
        self.assertEqual(receipt["minimum_reentry_source_keys"], [{"file_id": 3, "relative_path": "src/alpha.py"}])
        self.assertEqual(len(receipt["retained_current_active_sources"]), 1)
        self.assertEqual(receipt["retained_current_active_sources"][0]["file_id"], 4)
        self.assertEqual(receipt["selected_source_rebinds"][0]["reason"], "ACTIVE_SOURCE_STALE")
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_unknown_active_source_is_selected_not_promoted_to_current(self):
        observed = copy.deepcopy(self.sources)
        observed[1]["currentness"] = UNKNOWN
        observed[1]["witness_ref"] = "SOURCE:4:UNKNOWN"
        receipt = self.compile(sources=observed)
        self.assertEqual(receipt["minimum_reentry_scope"], SELECTED_SOURCES)
        self.assertEqual(receipt["selected_source_rebinds"][0]["prior"]["file_id"], 4)
        self.assertEqual(receipt["selected_source_rebinds"][0]["reason"], "ACTIVE_SOURCE_UNKNOWN")
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_current_new_source_generation_requires_selected_rebind(self):
        observed = copy.deepcopy(self.sources)
        observed[0]["source_generation"] = 9003
        observed[0]["source_sha256"] = "d" * 64
        observed[0]["source_byte_len"] = 124
        observed[0]["witness_ref"] = "SOURCE:3:GEN9003"
        receipt = self.compile(sources=observed)
        self.assertEqual(receipt["minimum_reentry_scope"], SELECTED_SOURCES)
        self.assertEqual(receipt["selected_source_rebinds"][0]["reason"], "ACTIVE_SOURCE_BINDING_CHANGED")
        self.assertEqual(receipt["selected_source_rebinds"][0]["prior"]["source_generation"], 9001)
        self.assertEqual(receipt["selected_source_rebinds"][0]["observed"]["source_generation"], 9003)
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_missing_active_observation_is_unresolved_selected_rebind(self):
        observed = copy.deepcopy(self.sources[1:])
        receipt = self.compile(sources=observed)
        self.assertEqual(receipt["minimum_reentry_scope"], SELECTED_SOURCES)
        self.assertEqual(len(receipt["unresolved_active_sources"]), 1)
        self.assertEqual(receipt["unresolved_active_sources"][0]["prior"]["file_id"], 3)
        self.assertEqual(receipt["unresolved_active_sources"][0]["observed"], None)
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_stale_graph_forces_full_graph_rebind(self):
        graph = copy.deepcopy(self.graph)
        graph["currentness"] = STALE
        graph["witness_ref"] = "GRAPH:41:STALE"
        receipt = self.compile(graph=graph)
        self.assertEqual(receipt["minimum_reentry_scope"], FULL_GRAPH)
        self.assertTrue(receipt["graph_rebind_required"])
        self.assertIn("GRAPH_STALE", receipt["graph_rebind_reasons"])
        self.assertEqual(receipt["minimum_reentry_source_keys"], [])
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_graph_generation_change_forces_full_graph_rebind_even_when_current(self):
        graph = copy.deepcopy(self.graph)
        graph["graph_generation"] = 42
        graph["graph_basis_identity"] = identity("graph-basis-42")
        graph["witness_ref"] = "GRAPH:42:CURRENT"
        receipt = self.compile(graph=graph)
        self.assertEqual(receipt["minimum_reentry_scope"], FULL_GRAPH)
        self.assertIn("GRAPH_IDENTITY_CHANGED", receipt["graph_rebind_reasons"])
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_cold_source_drift_does_not_invalidate_active_context(self):
        observed = copy.deepcopy(self.sources)
        observed[2]["currentness"] = STALE
        observed[2]["source_generation"] = 13
        observed[2]["source_sha256"] = "e" * 64
        observed[2]["witness_ref"] = "SOURCE:9:STALE"
        receipt = self.compile(sources=observed)
        self.assertEqual(receipt["minimum_reentry_scope"], NONE)
        self.assertEqual(len(receipt["cold_frontier_changes"]), 1)
        self.assertFalse(receipt["cold_change_invalidates_active_context"])
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_new_observed_source_is_recorded_but_not_auto_promoted(self):
        observed = copy.deepcopy(self.sources)
        observed.append(
            {
                "role": ACTIVE,
                "file_id": 11,
                "relative_path": "src/new.py",
                "source_generation": 1,
                "source_sha256": "f" * 64,
                "source_byte_len": 22,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:11:GEN1",
            }
        )
        receipt = self.compile(sources=observed)
        self.assertEqual(receipt["minimum_reentry_scope"], NONE)
        self.assertEqual(len(receipt["unbound_observations"]), 1)
        self.assertFalse(receipt["unbound_observations"][0]["auto_promoted_to_active_dependency"])
        self.assertEqual(verify_reentry_invalidation(receipt), [])

    def test_previous_binding_tamper_is_rejected_before_comparison(self):
        self.previous["graph_witness"]["graph_generation"] = 99
        with self.assertRaisesRegex(ValueError, "previous_binding is not a coherent"):
            self.compile()

    def test_receipt_authority_tamper_is_detected(self):
        receipt = self.compile()
        receipt["authority"]["commit_authorized"] = True
        violations = verify_reentry_invalidation(receipt)
        self.assertIn("AUTHORITY_MINTED_BY_REENTRY_RECEIPT", violations)
        self.assertIn("RECEIPT_IDENTITY_MISMATCH", violations)

    def test_receipt_cannot_promote_unproven_node_cone(self):
        receipt = self.compile()
        receipt["node_level_dependency_cone_proven"] = True
        violations = verify_reentry_invalidation(receipt)
        self.assertIn("UNPROVEN_NODE_LEVEL_CONE_PROMOTED", violations)
        self.assertIn("RECEIPT_IDENTITY_MISMATCH", violations)


if __name__ == "__main__":
    unittest.main()
