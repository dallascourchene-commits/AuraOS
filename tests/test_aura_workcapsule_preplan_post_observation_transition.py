from __future__ import annotations

import inspect

from scripts.aura_workcapsule_preplan_post_observation_transition import (
    admit_preplan_post_observation_transition,
    verify_preplan_post_observation_transition,
)
from tests.test_aura_workcapsule_raw_owner_hold_to_closed_transition import (
    WorkCapsuleRawOwnerHoldToClosedTransitionTests,
)


class WorkCapsulePreplanPostObservationTransitionTests(
    WorkCapsuleRawOwnerHoldToClosedTransitionTests
):
    def verify_preplan_transition(
        self,
        *,
        pre_witness=None,
        post_root=None,
        post_witness=None,
        post_graph=None,
    ):
        return verify_preplan_post_observation_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=(
                pre_witness if pre_witness is not None else self.pre_witness
            ),
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            post_root=post_root if post_root is not None else self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=(
                post_witness if post_witness is not None else self.post_witness
            ),
            post_graph_witness=post_graph if post_graph is not None else self.graph,
        )

    def test_pre_plan_drives_fresh_post_observation_closure(self) -> None:
        self.assertEqual([], self.verify_preplan_transition())
        admission = admit_preplan_post_observation_transition(
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
        self.assertTrue(admission["pre_reentry_plan_derived_from_pre_raw_owner"])
        self.assertTrue(admission["post_candidate_derived_from_post_raw_observations"])
        self.assertTrue(admission["post_closure_derived_around_exact_pre_plan"])
        self.assertTrue(admission["exact_hold_to_closed_transition"])
        self.assertEqual("HOLD", admission["pre_closure_status"])
        self.assertEqual("CLOSED", admission["post_closure_status"])
        self.assertEqual(
            admission["post_derived_closure_receipt_identity"],
            admission["transition_post_closure_receipt_identity"],
        )
        self.assertTrue(admission["pre_and_post_evidence_are_distinct_phases"])
        self.assertFalse(admission["source_currentness_minted"])
        self.assertFalse(admission["semantic_repair_correctness_minted"])
        self.assertFalse(admission["producer_identity_authenticated"])
        self.assertFalse(any(admission["authority"].values()))

    def test_public_boundary_has_no_lifecycle_intermediate_escape_hatches(self) -> None:
        params = inspect.signature(verify_preplan_post_observation_transition).parameters
        for forbidden in (
            "reentry_receipt",
            "pre_observation_closure_receipt",
            "post_closure_receipt",
            "source_observation_receipt",
            "observed_source_witnesses",
            "candidate_binding",
        ):
            self.assertNotIn(forbidden, params)
        for required in (
            "pre_root",
            "post_root",
            "pre_witness_manifest",
            "post_witness_manifest",
        ):
            self.assertIn(required, params)

    def test_post_source_drift_cannot_reuse_old_post_evidence(self) -> None:
        (self.post_root / "src/a.py").write_bytes(b"def target(x):\n    return x + 4\n")
        violations = self.verify_preplan_transition()
        self.assertTrue(
            any(item.startswith("POST_OBSERVATION_OWNER_DERIVATION_FAILED:") for item in violations),
            violations,
        )

    def test_one_live_root_cannot_satisfy_rejected_pre_and_repaired_post(self) -> None:
        violations = self.verify_preplan_transition(post_root=self.pre_root)
        self.assertNotEqual([], violations)

    def test_current_only_pre_evidence_cannot_enter_rejected_transition(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        violations = self.verify_preplan_transition()
        self.assertTrue(
            any(item.startswith("PRE_RAW_OWNER_DERIVATION_FAILED:") for item in violations),
            violations,
        )

    def test_unknown_pre_identity_stays_unguessed_and_can_close_after_repair(self) -> None:
        empty = {"version": self.pre_witness["version"], "witnesses": []}
        self.assertEqual([], self.verify_preplan_transition(pre_witness=empty))
        admission = admit_preplan_post_observation_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=empty,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=self.graph,
        )
        self.assertTrue(admission["exact_hold_to_closed_transition"])
        self.assertEqual("CLOSED", admission["post_closure_status"])
        self.assertFalse(admission["source_currentness_minted"])


if __name__ == "__main__":
    import unittest

    unittest.main()
