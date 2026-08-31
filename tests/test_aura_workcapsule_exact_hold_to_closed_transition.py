from __future__ import annotations

import copy
import inspect

from scripts.aura_workcapsule_exact_hold_to_closed_transition import (
    POST_NOT_CLOSED,
    PRE_NOT_HOLD,
    admit_exact_hold_to_closed_transition,
    verify_exact_hold_to_closed_transition,
)
from scripts.aura_workcapsule_observation_bound_closure import (
    compile_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_reentry_closure import CLOSED, HOLD, compile_reentry_closure
from scripts.aura_workcapsule_two_phase_source_bound_closure import derive_post_reentry_candidate
from tests.test_aura_workcapsule_two_phase_source_bound_closure import (
    WorkCapsuleTwoPhaseSourceBoundClosureTests,
    identity,
)


class WorkCapsuleExactHoldToClosedTransitionTests(
    WorkCapsuleTwoPhaseSourceBoundClosureTests
):
    def setUp(self) -> None:
        super().setUp()
        self.pre_observation = compile_observation_bound_reentry_closure(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=self.graph,
        )
        self.assertEqual(HOLD, self.pre_observation["closure_status"])

    def verify_transition(self, *, pre_receipt=None, post_closure=None, post_graph=None):
        return verify_exact_hold_to_closed_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            pre_observation_closure_receipt=(
                pre_receipt if pre_receipt is not None else self.pre_observation
            ),
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=post_graph if post_graph is not None else self.graph,
            post_closure_receipt=(
                post_closure if post_closure is not None else self.closure
            ),
        )

    def admit_transition(self):
        return admit_exact_hold_to_closed_transition(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            pre_observation_closure_receipt=self.pre_observation,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=self.graph,
            post_closure_receipt=self.closure,
        )

    def test_exact_pre_hold_to_distinct_post_closed_transition(self) -> None:
        self.assertEqual([], self.verify_transition())
        admission = self.admit_transition()
        self.assertEqual("EXACT_PRE_HOLD_TO_POST_CLOSED", admission["transition_status"])
        self.assertEqual(HOLD, admission["pre_closure_status"])
        self.assertEqual(CLOSED, admission["post_closure_status"])
        self.assertTrue(admission["exact_pre_observation_reproduction"])
        self.assertTrue(admission["exact_two_phase_lifecycle"])
        self.assertTrue(admission["pre_and_post_evidence_are_distinct_phases"])
        self.assertFalse(admission["semantic_repair_correctness_minted"])
        self.assertFalse(any(admission["authority"].values()))

    def test_coherent_foreign_pre_world_receipt_is_rejected(self) -> None:
        foreign = b"def target(x):\n    return x + 4\n"
        self.assertEqual(len(self.stale), len(foreign))
        (self.pre_root / "src/a.py").write_bytes(foreign)
        foreign_receipt = compile_observation_bound_reentry_closure(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=self.graph,
        )
        self.assertEqual(HOLD, foreign_receipt["closure_status"])
        (self.pre_root / "src/a.py").write_bytes(self.stale)
        violations = self.verify_transition(pre_receipt=foreign_receipt)
        self.assertTrue(any(item.startswith("PRE_EXACT_OBSERVATION_") for item in violations))

    def test_exact_pre_closed_receipt_is_not_a_hold_to_closed_transition(self) -> None:
        (self.pre_root / "src/a.py").write_bytes(self.original)
        current_receipt = compile_observation_bound_reentry_closure(
            root=self.pre_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=self.graph,
        )
        self.assertEqual(CLOSED, current_receipt["closure_status"])
        violations = self.verify_transition(pre_receipt=current_receipt)
        self.assertIn(PRE_NOT_HOLD, violations)

    def test_exact_post_hold_is_preserved_but_not_admitted_as_transition_closed(self) -> None:
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
        violations = self.verify_transition(post_closure=hold_closure, post_graph=graph)
        self.assertIn(POST_NOT_CLOSED, violations)

    def test_public_boundary_has_no_candidate_or_source_witness_escape_hatch(self) -> None:
        params = inspect.signature(verify_exact_hold_to_closed_transition).parameters
        self.assertNotIn("candidate_binding", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertNotIn("source_observation_receipt", params)
        self.assertIn("reentry_receipt", params)  # O19, not O26, owns removal of this slot.
        self.assertIn("pre_observation_closure_receipt", params)
        self.assertIn("pre_root", params)
        self.assertIn("post_root", params)


if __name__ == "__main__":
    import unittest

    unittest.main()
