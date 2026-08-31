from __future__ import annotations

import copy
import inspect
from pathlib import Path
from unittest.mock import patch

from scripts.aura_workcapsule_canonical_temporal_lifecycle_equivalence import (
    POST_DERIVED_CANDIDATE_IDENTITY_MISMATCH,
    POST_INNER_CLOSURE_IDENTITY_MISMATCH,
    POST_OUTER_INNER_CLOSURE_REQUIRED,
    PRE_SOURCE_OBSERVATION_IDENTITY_MISMATCH,
    admit_canonical_temporal_lifecycle_equivalence,
    verify_canonical_temporal_lifecycle_equivalence,
)
from scripts.aura_workcapsule_observation_bound_closure import (
    CLOSED,
    HOLD,
    compile_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_two_phase_observation_bound_exact import (
    admit_two_phase_observation_bound_exact,
)
from scripts.aura_workcapsule_two_phase_owner_reduced_transition import (
    admit_two_phase_owner_reduced_transition,
)
from tests.test_aura_workcapsule_two_phase_owner_reduced_transition import (
    WorkCapsuleTwoPhaseOwnerReducedTransitionTests,
    identity,
)


class WorkCapsuleCanonicalTemporalLifecycleEquivalenceTests(
    WorkCapsuleTwoPhaseOwnerReducedTransitionTests
):
    def setUp(self) -> None:
        super().setUp()
        self.post_outer = compile_observation_bound_reentry_closure(
            root=self.post_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.post_witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=self.graph,
        )
        self.assertEqual(CLOSED, self.post_outer["closure_status"])
        self.assertEqual(self.closure, self.post_outer["closure_receipt"])

    def kwargs(self, *, post_outer=None, post_graph=None) -> dict:
        return {
            "pre_root": self.pre_root,
            "pre_codemap": self.codemap,
            "pre_anchor_manifest": self.anchors,
            "pre_witness_manifest": self.pre_witness,
            "previous_binding": self.previous,
            "pre_graph_witness": self.graph,
            "reentry_receipt": self.reentry,
            "pre_observation_closure_receipt": self.pre_observation,
            "post_root": self.post_root,
            "post_codemap": self.codemap,
            "post_anchor_manifest": self.anchors,
            "post_witness_manifest": self.post_witness,
            "post_graph_witness": post_graph if post_graph is not None else self.graph,
            "post_observation_bound_receipt": (
                post_outer if post_outer is not None else self.post_outer
            ),
        }

    def specialized_admission(self) -> dict:
        return admit_two_phase_owner_reduced_transition(
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
            closure_receipt=self.closure,
        )

    def general_admission(self) -> dict:
        return admit_two_phase_observation_bound_exact(
            pre_root=self.pre_root,
            pre_codemap=self.codemap,
            pre_anchor_manifest=self.anchors,
            pre_witness_manifest=self.pre_witness,
            previous_binding=self.previous,
            pre_graph_witness=self.graph,
            reentry_receipt=self.reentry,
            post_root=self.post_root,
            post_codemap=self.codemap,
            post_anchor_manifest=self.anchors,
            post_witness_manifest=self.post_witness,
            post_graph_witness=self.graph,
            observation_bound_receipt=self.post_outer,
        )

    def test_exact_specialized_and_general_owners_canonicalize_one_lifecycle(self) -> None:
        self.assertEqual([], verify_canonical_temporal_lifecycle_equivalence(**self.kwargs()))
        admitted = admit_canonical_temporal_lifecycle_equivalence(**self.kwargs())
        self.assertTrue(admitted["canonical_temporal_lifecycle_equivalence_proven"])
        self.assertTrue(admitted["specialized_owner_reduced_transition_proven"])
        self.assertTrue(admitted["general_two_phase_observation_replay_proven"])
        self.assertTrue(admitted["cross_owner_identity_tuple_exact"])
        self.assertEqual(HOLD, admitted["pre_closure_status"])
        self.assertEqual(CLOSED, admitted["post_closure_status"])
        self.assertFalse(admitted["raw_replay_reimplemented_by_child"])
        self.assertFalse(admitted["semantic_repair_correctness_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_post_outer_without_inner_closure_cannot_claim_transition_equivalence(self) -> None:
        receipt = copy.deepcopy(self.post_outer)
        receipt["closure_receipt"] = None
        self.assertEqual(
            [POST_OUTER_INNER_CLOSURE_REQUIRED],
            verify_canonical_temporal_lifecycle_equivalence(**self.kwargs(post_outer=receipt)),
        )

    def test_exact_general_post_hold_is_not_specialized_closed_equivalence(self) -> None:
        graph8 = copy.deepcopy(self.graph)
        graph8["graph_generation"] = 8
        graph8["graph_basis_identity"] = identity("graph-o27-8")
        graph8["witness_ref"] = "GRAPH:O27:8:CURRENT"
        outer = compile_observation_bound_reentry_closure(
            root=self.post_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.post_witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=graph8,
        )
        self.assertEqual(HOLD, outer["closure_status"])
        violations = verify_canonical_temporal_lifecycle_equivalence(
            **self.kwargs(post_outer=outer, post_graph=graph8)
        )
        self.assertTrue(any(item.startswith("SPECIALIZED_") for item in violations))

    def test_split_brain_pre_identity_is_detected_after_both_verifiers_pass(self) -> None:
        specialized = copy.deepcopy(self.specialized_admission())
        specialized["pre_source_observation_identity"] = {"kind": "DIGEST", "value": "split-pre"}
        with patch(
            "scripts.aura_workcapsule_canonical_temporal_lifecycle_equivalence.admit_two_phase_owner_reduced_transition",
            return_value=specialized,
        ):
            violations = verify_canonical_temporal_lifecycle_equivalence(**self.kwargs())
        self.assertIn(PRE_SOURCE_OBSERVATION_IDENTITY_MISMATCH, violations)

    def test_split_brain_post_candidate_is_detected_after_both_verifiers_pass(self) -> None:
        general = copy.deepcopy(self.general_admission())
        general["inner_two_phase_exact_lifecycle"]["post_derived_candidate_binding_identity"] = {
            "kind": "DIGEST",
            "value": "split-post-candidate",
        }
        with patch(
            "scripts.aura_workcapsule_canonical_temporal_lifecycle_equivalence.admit_two_phase_observation_bound_exact",
            return_value=general,
        ):
            violations = verify_canonical_temporal_lifecycle_equivalence(**self.kwargs())
        self.assertIn(POST_DERIVED_CANDIDATE_IDENTITY_MISMATCH, violations)

    def test_split_brain_inner_closure_identity_is_detected_after_both_verifiers_pass(self) -> None:
        general = copy.deepcopy(self.general_admission())
        general["inner_two_phase_exact_lifecycle"]["exact_closure_admission"][
            "o10_closure_receipt_identity"
        ] = {"kind": "DIGEST", "value": "split-inner-closure"}
        with patch(
            "scripts.aura_workcapsule_canonical_temporal_lifecycle_equivalence.admit_two_phase_observation_bound_exact",
            return_value=general,
        ):
            violations = verify_canonical_temporal_lifecycle_equivalence(**self.kwargs())
        self.assertIn(POST_INNER_CLOSURE_IDENTITY_MISMATCH, violations)

    def test_child_public_boundary_consumes_only_parent_owner_inputs(self) -> None:
        params = inspect.signature(verify_canonical_temporal_lifecycle_equivalence).parameters
        self.assertNotIn("candidate_binding", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertNotIn("closure_receipt", params)
        self.assertIn("pre_observation_closure_receipt", params)
        self.assertIn("post_observation_bound_receipt", params)

        source = Path(
            "scripts/aura_workcapsule_canonical_temporal_lifecycle_equivalence.py"
        ).read_text()
        forbidden = [
            "compile_source_reentry_observations",
            "compile_expected_source_bound_reentry",
            "compile_observation_bound_reentry_closure",
            "compile_reentry_closure",
            "derive_post_reentry_candidate",
        ]
        for name in forbidden:
            self.assertNotIn(name, source)
        self.assertIn("verify_two_phase_owner_reduced_transition", source)
        self.assertIn("verify_two_phase_observation_bound_exact", source)
