from __future__ import annotations

import copy
import inspect

from scripts.aura_workcapsule_raw_owner_derived_post_closure_transition import (
    POST_NOT_CLOSED,
    admit_raw_owner_derived_post_closure_transition,
    verify_raw_owner_derived_post_closure_transition,
)
from tests.test_aura_workcapsule_raw_owner_hold_to_closed_transition import (
    WorkCapsuleRawOwnerHoldToClosedTransitionTests,
    identity,
)


class WorkCapsuleRawOwnerDerivedPostClosureTransitionTests(
    WorkCapsuleRawOwnerHoldToClosedTransitionTests
):
    def verify_corrected(
        self,
        *,
        pre_witness=None,
        post_root=None,
        post_witness=None,
        post_graph=None,
    ):
        return verify_raw_owner_derived_post_closure_transition(
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

    def test_raw_pre_and_raw_post_derive_exact_transition_without_caller_closure(self) -> None:
        self.assertEqual([], self.verify_corrected())
        admission = admit_raw_owner_derived_post_closure_transition(
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
        self.assertTrue(admission["raw_owner_post_candidate_derived"])
        self.assertTrue(admission["post_o10_closure_derived"])
        self.assertTrue(admission["pre_reentry_receipt_reused_for_post_o10"])
        self.assertFalse(admission["fresh_post_reentry_receipt_substituted"])
        self.assertFalse(admission["caller_post_closure_receipt_accepted"])
        self.assertEqual("HOLD", admission["pre_closure_status"])
        self.assertEqual("CLOSED", admission["post_closure_status"])
        self.assertEqual(
            admission["post_o10_closure_receipt_identity"],
            admission["pr518_post_o10_closure_receipt_identity"],
        )
        self.assertEqual(
            admission["post_o10_closure_receipt_identity"],
            admission["pr533_post_o10_closure_receipt_identity"],
        )
        self.assertTrue(admission["pre_and_post_evidence_are_distinct_phases"])
        self.assertTrue(admission["source_generation_domain_preserved"])
        self.assertFalse(any(admission["authority"].values()))

    def test_public_boundary_accepts_no_lifecycle_intermediate(self) -> None:
        params = inspect.signature(
            verify_raw_owner_derived_post_closure_transition
        ).parameters
        for forbidden in (
            "post_closure_receipt",
            "reentry_receipt",
            "pre_observation_closure_receipt",
            "candidate_binding",
            "source_observation_receipt",
        ):
            self.assertNotIn(forbidden, params)
        self.assertIn("pre_root", params)
        self.assertIn("post_root", params)

    def test_one_live_root_cannot_impersonate_both_temporal_phases(self) -> None:
        violations = self.verify_corrected(post_root=self.pre_root)
        self.assertIn(
            "PR518_TWO_PHASE_PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT",
            violations,
        )

    def test_post_source_drift_fails_before_transition_admission(self) -> None:
        (self.post_root / "src/a.py").write_bytes(b"def target(x):\n    return x + 4\n")
        violations = self.verify_corrected()
        self.assertTrue(violations)
        self.assertTrue(
            any(
                item.startswith("POST_RAW_OWNER_DERIVATION_FAILED:")
                or item.startswith("PR518_TWO_PHASE_")
                for item in violations
            )
        )

    def test_current_only_pre_state_cannot_enter_rejected_currentness_transition(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        violations = self.verify_corrected()
        self.assertTrue(violations)
        self.assertTrue(any("DERIVATION_FAILED:" in item for item in violations))

    def test_post_graph_drift_preserves_hold_instead_of_promoting_closed(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["graph_generation"] = 8
        graph["graph_basis_identity"] = identity("graph-8")
        graph["witness_ref"] = "GRAPH:8:CURRENT"
        violations = self.verify_corrected(post_graph=graph)
        self.assertIn(POST_NOT_CLOSED, violations)

    def test_causal_join_uses_pre_reentry_identity_not_a_fresh_post_reentry(self) -> None:
        admission = admit_raw_owner_derived_post_closure_transition(
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
        self.assertTrue(admission["pre_reentry_receipt_reused_for_post_o10"])
        self.assertFalse(admission["fresh_post_reentry_receipt_substituted"])
        self.assertEqual(
            admission["pre_reentry_receipt_identity"],
            self.reentry["receipt_identity"],
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
