from __future__ import annotations

import inspect

from scripts.aura_workcapsule_fully_raw_owner_hold_to_closed_transition import (
    admit_fully_raw_owner_hold_to_closed_transition,
    verify_fully_raw_owner_hold_to_closed_transition,
)
from tests.test_aura_workcapsule_raw_owner_hold_to_closed_transition import (
    WorkCapsuleRawOwnerHoldToClosedTransitionTests,
)


class WorkCapsuleFullyRawOwnerHoldToClosedTransitionTests(
    WorkCapsuleRawOwnerHoldToClosedTransitionTests
):
    def verify_full(self, *, pre_root=None, post_root=None, pre_witness=None, post_witness=None):
        return verify_fully_raw_owner_hold_to_closed_transition(
            pre_root=pre_root if pre_root is not None else self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=pre_witness if pre_witness is not None else self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            post_root=post_root if post_root is not None else self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=post_witness if post_witness is not None else self.post_witness,
            post_graph_witness=self.graph,
        )

    def test_o31_raw_pre_and_raw_post_derive_entire_hold_to_closed_transition(self) -> None:
        self.assertEqual([], self.verify_full())
        admission = admit_fully_raw_owner_hold_to_closed_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=self.graph,
        )
        self.assertTrue(admission["raw_owner_pre_lifecycle_derived"])
        self.assertTrue(admission["raw_owner_post_closure_derived"])
        self.assertFalse(admission["caller_post_closure_receipt_accepted"])
        self.assertFalse(admission["caller_lifecycle_intermediate_accepted"])
        self.assertEqual("HOLD", admission["pre_closure_status"])
        self.assertEqual("CLOSED", admission["post_closure_status"])
        self.assertEqual(
            admission["post_owner_derived_closure_receipt_identity"],
            admission["transition_post_closure_receipt_identity"],
        )
        self.assertTrue(admission["pre_and_post_evidence_are_distinct_phases"])
        self.assertFalse(admission["semantic_repair_correctness_minted"])
        self.assertFalse(any(admission["authority"].values()))

    def test_o31_public_boundary_has_no_lifecycle_intermediate_escape_hatch(self) -> None:
        params = inspect.signature(verify_fully_raw_owner_hold_to_closed_transition).parameters
        for forbidden in (
            "post_closure_receipt",
            "reentry_receipt",
            "pre_observation_closure_receipt",
            "source_observation_receipt",
            "observed_source_witnesses",
            "candidate_binding",
        ):
            self.assertNotIn(forbidden, params)
        self.assertIn("pre_root", params)
        self.assertIn("post_root", params)
        self.assertIn("pre_witness_manifest", params)
        self.assertIn("post_witness_manifest", params)

    def test_o31_post_source_drift_invalidates_derived_closure_before_transition(self) -> None:
        (self.post_root / "src/a.py").write_bytes(b"def target(x):\n    return x + 4\n")
        violations = self.verify_full()
        self.assertTrue(
            any(
                item.startswith("POST_RAW_OWNER_DERIVATION_FAILED:")
                or item.startswith("TRANSITION_")
                for item in violations
            )
        )

    def test_o31_one_live_root_cannot_impersonate_both_temporal_phases(self) -> None:
        violations = self.verify_full(post_root=self.pre_root)
        self.assertTrue(
            any(
                "TWO_PHASE_PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT" in item
                or item.startswith("POST_RAW_OWNER_DERIVATION_FAILED:")
                for item in violations
            )
        )

    def test_o31_current_only_pre_evidence_still_cannot_enter_hold_transition(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        violations = self.verify_full()
        self.assertTrue(any("PRE_RAW_OWNER_" in item for item in violations))


if __name__ == "__main__":
    import unittest

    unittest.main()
