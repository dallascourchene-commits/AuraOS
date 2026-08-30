import unittest

from aura_workgraph_abi import (
    ClaimFence,
    WorkGraphABIError,
    common_abi_revision,
    common_abi_view,
    compatibility_report,
    next_claim_fence,
    stable_projection_revision,
    validate_claim_fence,
)


def p315(now=100):
    return {
        "schema": "WorkGraphProjectionV1",
        "project_id": "CS-PROJ-001",
        "canonical_orientation_revision": "fd-r9",
        "board_ref": "board",
        "board_revision": "b7",
        "generated_at_ms": now,
        "work_items": [
            {
                "work": {
                    "work_id": "A",
                    "state": "OPEN",
                    "dependencies": [],
                    "required_capabilities": ["python"],
                    "required_effect_ceiling": "D0",
                    "execution_state": "NOT_STARTED",
                },
                "effective_state": "OPEN",
                "active_lease": None,
            }
        ],
        "source_digest": "s1",
        "execution_proven": False,
    }


def p313(now=100, generation=None):
    claims = []
    state = "OPEN"
    if generation is not None:
        state = "CLAIMED"
        claims = [
            {
                "claim_id": "c1",
                "worker_id": "W1",
                "basis_graph_digest": "g" * 64,
                "currentness_ref": "fd-r9",
                "generation": generation,
            }
        ]
    return {
        "schema": "AuraArenaWorkGraphProjectionV1",
        "project_id": "CS-PROJ-001",
        "currentness_ref": "fd-r9",
        "board_ref": "board",
        "board_revision": "b7",
        "now_ms": now,
        "cells": [
            {
                "cell_id": "A",
                "state": state,
                "effective_state": state,
                "dependencies": [],
                "required_capabilities": ["python"],
                "effect_class": "D0",
                "execution_state": "NOT_STARTED",
                "active_claims": claims,
            }
        ],
        "graph_digest": "x" * 64,
    }


class WorkGraphABITests(unittest.TestCase):
    def test_315_time_only_reprojection_is_clock_stable(self):
        self.assertEqual(
            stable_projection_revision(p315(100)),
            stable_projection_revision(p315(999999)),
        )

    def test_313_time_only_reprojection_is_clock_stable(self):
        self.assertEqual(
            stable_projection_revision(p313(100)),
            stable_projection_revision(p313(999999)),
        )

    def test_material_change_changes_stable_revision(self):
        left = p315()
        right = p315()
        right["work_items"][0]["effective_state"] = "BLOCKED"
        self.assertNotEqual(
            stable_projection_revision(left), stable_projection_revision(right)
        )

    def test_common_abi_maps_work_and_cell_ids(self):
        self.assertEqual("A", common_abi_view(p315())["cells"][0]["work_id"])
        self.assertEqual("A", common_abi_view(p313())["cells"][0]["work_id"])

    def test_equivalent_minimal_semantics_have_same_common_revision(self):
        self.assertEqual(common_abi_revision(p315()), common_abi_revision(p313()))

    def test_313_generation_maps_to_fence_epoch(self):
        view = common_abi_view(p313(generation=4))
        self.assertEqual(4, view["cells"][0]["lease"]["fence_epoch"])

    def test_fence_increments_monotonically(self):
        first = next_claim_fence(
            project_id="P", work_id="A", worker_id="W1", basis_revision="r1"
        )
        second = next_claim_fence(
            project_id="P",
            work_id="A",
            worker_id="W2",
            basis_revision="r2",
            previous=first,
        )
        self.assertEqual(1, first.fence_epoch)
        self.assertEqual(2, second.fence_epoch)
        self.assertNotEqual(first.token, second.token)

    def test_stale_fence_rejected(self):
        fence = ClaimFence("P", "A", "W1", "r1", 1)
        with self.assertRaisesRegex(WorkGraphABIError, "FENCE_STALE_OWNER"):
            validate_claim_fence(fence, minimum_epoch=1, basis_revision="r1")

    def test_stale_basis_rejected(self):
        fence = ClaimFence("P", "A", "W1", "r1", 2)
        with self.assertRaisesRegex(WorkGraphABIError, "FENCE_STALE_BASIS"):
            validate_claim_fence(fence, minimum_epoch=1, basis_revision="r2")

    def test_lineage_mismatch_rejected(self):
        first = ClaimFence("P", "A", "W1", "r1", 1)
        with self.assertRaisesRegex(WorkGraphABIError, "FENCE_LINEAGE_MISMATCH"):
            next_claim_fence(
                project_id="P",
                work_id="B",
                worker_id="W2",
                basis_revision="r2",
                previous=first,
            )

    def test_compatibility_report_refuses_ownership_promotion(self):
        report = compatibility_report(p315(), p313())
        self.assertTrue(report["same_project"])
        self.assertEqual(["A"], report["shared_work_ids"])
        self.assertEqual("UNRESOLVED", report["ownership_decision"])
        self.assertFalse(report["promotion_allowed"])

    def test_unknown_schema_fails_closed(self):
        with self.assertRaisesRegex(
            WorkGraphABIError, "PROJECTION_SCHEMA_UNSUPPORTED"
        ):
            stable_projection_revision({"schema": "Mystery"})


if __name__ == "__main__":
    unittest.main()
