from __future__ import annotations

import inspect

from scripts.aura_workcapsule_exact_hold_to_closed_transition import (
    verify_exact_hold_to_closed_transition,
)
from scripts.aura_workcapsule_fully_raw_temporal_transition_v2 import (
    PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT,
    admit_fully_raw_temporal_transition_v2,
    verify_fully_raw_temporal_transition_v2,
)
from scripts.aura_workcapsule_observation_bound_closure import (
    compile_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_raw_owner_end_to_end_stale_lifecycle import (
    compile_raw_owner_end_to_end_stale_lifecycle,
)
from scripts.aura_workcapsule_source_bound_exact_reentry import (
    compile_expected_source_bound_reentry,
)
from tests.test_aura_workcapsule_exact_hold_to_closed_transition import (
    WorkCapsuleExactHoldToClosedTransitionTests,
)


class WorkCapsuleFullyRawTemporalTransitionV2Tests(
    WorkCapsuleExactHoldToClosedTransitionTests
):
    def child_kwargs(self) -> dict:
        return {
            "pre_root": self.pre_root,
            "pre_codemap": self.codemap,
            "pre_anchor_manifest": self.anchors,
            "pre_witness_manifest": self.pre_witness,
            "previous_binding": self.previous,
            "pre_graph_witness": self.graph,
            "post_root": self.post_root,
            "post_codemap": self.codemap,
            "post_anchor_manifest": self.anchors,
            "post_witness_manifest": self.post_witness,
            "post_graph_witness": self.graph,
        }

    def test_raw_pre_hold_to_raw_post_closed_preserves_one_pre_o8(self) -> None:
        self.assertEqual([], verify_fully_raw_temporal_transition_v2(**self.child_kwargs()))
        receipt = admit_fully_raw_temporal_transition_v2(**self.child_kwargs())
        self.assertTrue(receipt["exact_hold_to_closed_transition"])
        self.assertEqual("HOLD", receipt["pre_closure_status"])
        self.assertEqual("CLOSED", receipt["post_closure_status"])
        self.assertEqual(
            receipt["pre_rejected_reentry_receipt_identity"],
            receipt["post_observation_bound_reentry_receipt_identity"],
        )
        self.assertEqual(
            receipt["post_derived_closure_receipt_identity"],
            receipt["temporal_oracle_post_closure_receipt_identity"],
        )
        self.assertTrue(receipt["same_pre_rejected_o8_drives_post_closure"])
        self.assertFalse(receipt["producer_identity_authenticated"])
        self.assertFalse(receipt["semantic_repair_correctness_minted"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_same_root_cannot_impersonate_temporal_transition(self) -> None:
        kwargs = self.child_kwargs()
        kwargs["post_root"] = self.pre_root
        violations = verify_fully_raw_temporal_transition_v2(**kwargs)
        self.assertEqual([PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT], violations)

    def test_separately_derived_post_world_o8_is_not_interchangeable(self) -> None:
        pre = compile_raw_owner_end_to_end_stale_lifecycle(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            candidate_graph_witness=self.graph,
        )
        pre_o8 = pre["derived_reentry_receipt"]
        pre_hold = pre["closure_receipt"]

        _post_source_observation, post_world_o8 = compile_expected_source_bound_reentry(
            root=self.post_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.post_witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
        )
        self.assertNotEqual(pre_o8["receipt_identity"], post_world_o8["receipt_identity"])
        foreign_post = compile_observation_bound_reentry_closure(
            root=self.post_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.post_witness,
            previous_binding=self.previous,
            reentry_receipt=post_world_o8,
            candidate_graph_witness=self.graph,
        )
        self.assertEqual("CLOSED", foreign_post["closure_status"])
        oracle_violations = verify_exact_hold_to_closed_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=pre_o8,
            pre_observation_closure_receipt=pre_hold,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=self.graph,
            post_closure_receipt=foreign_post["closure_receipt"],
        )
        self.assertTrue(
            any("REENTRY_RECEIPT_IDENTITY_NOT_EXACT" in item for item in oracle_violations),
            oracle_violations,
        )

    def test_public_boundary_exposes_no_lifecycle_intermediate_slots(self) -> None:
        params = inspect.signature(verify_fully_raw_temporal_transition_v2).parameters
        for forbidden in (
            "reentry_receipt",
            "pre_observation_closure_receipt",
            "post_closure_receipt",
            "source_observation_receipt",
            "observed_source_witnesses",
            "source_witnesses",
            "candidate_binding",
        ):
            self.assertNotIn(forbidden, params)
        for required in (
            "pre_root",
            "pre_witness_manifest",
            "pre_graph_witness",
            "post_root",
            "post_witness_manifest",
            "post_graph_witness",
        ):
            self.assertIn(required, params)


if __name__ == "__main__":
    import unittest

    unittest.main()
