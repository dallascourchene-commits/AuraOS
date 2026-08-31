from __future__ import annotations

import copy
import inspect

from scripts.aura_workcapsule_observation_bound_closure import HOLD
from scripts.aura_workcapsule_raw_owner_end_to_end_stale_lifecycle import (
    compile_raw_owner_end_to_end_stale_lifecycle,
)
from scripts.aura_workcapsule_raw_owner_hold_to_closed_transition import (
    admit_raw_owner_hold_to_closed_transition,
    verify_raw_owner_hold_to_closed_transition,
)
from scripts.aura_workcapsule_reentry_closure import compile_reentry_closure
from scripts.aura_workcapsule_two_phase_source_bound_closure import derive_post_reentry_candidate
from tests.test_aura_workcapsule_exact_hold_to_closed_transition import (
    WorkCapsuleExactHoldToClosedTransitionTests,
    identity,
)


class WorkCapsuleRawOwnerHoldToClosedTransitionTests(
    WorkCapsuleExactHoldToClosedTransitionTests
):
    def verify_raw_transition(
        self,
        *,
        pre_witness=None,
        post_root=None,
        post_witness=None,
        post_graph=None,
        post_closure=None,
    ):
        return verify_raw_owner_hold_to_closed_transition(
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
            post_closure_receipt=(
                post_closure if post_closure is not None else self.closure
            ),
        )

    def test_raw_owner_derives_pre_o8_and_hold_then_exactly_closes_post(self) -> None:
        self.assertEqual([], self.verify_raw_transition())
        admission = admit_raw_owner_hold_to_closed_transition(
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
            post_closure_receipt=self.closure,
        )
        self.assertTrue(admission["raw_owner_pre_lifecycle_derived"])
        self.assertFalse(admission["caller_reentry_receipt_accepted"])
        self.assertFalse(admission["caller_pre_observation_receipt_accepted"])
        self.assertTrue(admission["post_closure_receipt_pinned"])
        self.assertTrue(admission["exact_hold_to_closed_transition"])
        self.assertEqual("HOLD", admission["pre_closure_status"])
        self.assertEqual("CLOSED", admission["post_closure_status"])
        self.assertTrue(admission["pre_and_post_evidence_are_distinct_phases"])
        self.assertFalse(any(admission["authority"].values()))

    def test_public_boundary_has_no_pre_intermediate_escape_hatches(self) -> None:
        params = inspect.signature(verify_raw_owner_hold_to_closed_transition).parameters
        for forbidden in (
            "reentry_receipt",
            "pre_observation_closure_receipt",
            "source_observation_receipt",
            "observed_source_witnesses",
            "candidate_binding",
        ):
            self.assertNotIn(forbidden, params)
        self.assertIn("post_closure_receipt", params)
        self.assertIn("pre_root", params)
        self.assertIn("post_root", params)

    def test_current_only_pre_evidence_cannot_enter_rejected_currentness_transition(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        violations = self.verify_raw_transition()
        self.assertTrue(any(item.startswith("PRE_RAW_OWNER_RECOMPILE_FAILED:") for item in violations))

    def test_one_live_root_cannot_impersonate_both_temporal_phases(self) -> None:
        violations = self.verify_raw_transition(post_root=self.pre_root)
        self.assertIn("TRANSITION_TWO_PHASE_PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT", violations)

    def test_post_source_drift_invalidates_pinned_post_closure(self) -> None:
        (self.post_root / "src/a.py").write_bytes(b"def target(x):\n    return x + 4\n")
        violations = self.verify_raw_transition()
        self.assertTrue(any(item.startswith("TRANSITION_TWO_PHASE_") for item in violations))

    def test_exact_post_hold_is_preserved_and_rejected_as_transition_closed(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["graph_generation"] = 8
        graph["graph_basis_identity"] = identity("graph-8")
        graph["witness_ref"] = "GRAPH:8:CURRENT"
        _, candidate = derive_post_reentry_candidate(
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            previous_binding=self.previous,
            post_graph_witness=graph,
        )
        hold_closure = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_binding=candidate,
        )
        self.assertEqual(HOLD, hold_closure["closure_status"])
        violations = self.verify_raw_transition(post_graph=graph, post_closure=hold_closure)
        self.assertIn("TRANSITION_POST_EXACT_LIFECYCLE_NOT_CLOSED", violations)

    def test_unknown_pre_identity_is_derived_internally_and_can_close_after_repair(self) -> None:
        empty = {"version": self.pre_witness["version"], "witnesses": []}
        pre = compile_raw_owner_end_to_end_stale_lifecycle(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=empty,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            candidate_graph_witness=self.graph,
        )
        self.assertEqual(HOLD, pre["closure_status"])
        self.assertFalse(pre["unknown_identity_guessed"])
        _, candidate = derive_post_reentry_candidate(
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            previous_binding=self.previous,
            post_graph_witness=self.graph,
        )
        closure = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=pre["derived_reentry_receipt"],
            candidate_binding=candidate,
        )
        self.assertEqual("CLOSED", closure["closure_status"])
        self.assertEqual([], self.verify_raw_transition(pre_witness=empty, post_closure=closure))


if __name__ == "__main__":
    import unittest

    unittest.main()
