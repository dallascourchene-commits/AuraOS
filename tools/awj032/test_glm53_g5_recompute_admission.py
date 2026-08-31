from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_g5_recompute_admission import (
    ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT,
    ALLOW_CHANGED_AXIS,
    ALLOW_INITIAL,
    ALLOW_STATE_TRANSITION,
    CHANGE_AXIS_REQUIRED,
    COLLAPSE_CONE,
    COLLAPSE_RECOMPUTE_CONE,
    G4_HOLD_RECOMPUTE,
    G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED,
    HOLD_ALIAS_RESOLUTION,
    HOLD_ALIAS_RESOLUTION_REQUIRED,
    HOLD_G4_OWNER_CURRENTNESS_REQUIRED,
    HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
    HOLD_SOURCE_READ_CURRENTNESS_REQUIRED,
    HOLD_VERSION_TRANSITION_REQUIRED,
    READ_RESOLVED_CURRENT,
    READ_STALE,
    READ_UNKNOWN,
    AliasStableProgressProjection,
    G4V2RevalidationProjection,
    SourceReadCurrentnessProjection,
    VersionTransitionProjection,
    assess_g3_recompute_admission,
    disposition_table,
    disposition_tree,
    prove_finite_recompute_lattice,
)


def d(ch: str) -> str:
    return ch * 64


class GLM53G5V2Tests(unittest.TestCase):
    def g4(self, *, source_changed: bool = False, structural_match: bool = False):
        if structural_match:
            return G4V2RevalidationProjection(
                receipt_digest=d("a"),
                disposition=G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED,
                changed_axes=(),
                frozen_source_binding_generation="source::17",
                current_source_binding_generation="source::17",
            )
        return G4V2RevalidationProjection(
            receipt_digest=d("a"),
            disposition=G4_HOLD_RECOMPUTE,
            changed_axes=("source_binding_generation",) if source_changed else ("runtime_generation",),
            frozen_source_binding_generation="source::17",
            current_source_binding_generation="source::18" if source_changed else "source::17",
        )

    def progress(self, decision: str = ALLOW_STATE_TRANSITION, *, alias_hold: bool = False):
        return AliasStableProgressProjection(
            receipt_digest=d("b"),
            decision=HOLD_ALIAS_RESOLUTION_REQUIRED if alias_hold else decision,
            semantic_fingerprint_digest=d("c"),
            source_sid="sid::glm53",
            provider_state_generation="provider::17",
            evidence_digest=d("d"),
            route_projection_changed=alias_hold,
            source_sid_same=True,
            alias_projection_required=alias_hold,
            alias_projection_consumed=False,
            raw_decision=ALLOW_CHANGED_AXIS if alias_hold else decision,
            semantic_decision=None if alias_hold else decision,
        )

    def version(self):
        return VersionTransitionProjection(
            receipt_digest=d("e"),
            predecessor_source_binding_generation="source::17",
            successor_source_binding_generation="source::18",
            explicit_successor_edge=True,
            future_read_currentness_required=True,
        )

    def currentness(self, state: str = READ_RESOLVED_CURRENT, *, source: str = "source::18"):
        return SourceReadCurrentnessProjection(
            witness_digest=d("f"),
            source_binding_generation=source,
            owner_generation="read-owner::17",
            state=state,
        )

    def assess(self, **kwargs):
        return assess_g3_recompute_admission(
            g4=kwargs.get("g4", self.g4()),
            progress=kwargs.get("progress", self.progress()),
            version=kwargs.get("version"),
            currentness=kwargs.get("currentness"),
        )

    def test_structural_match_never_means_not_applicable_or_reusable(self):
        r = self.assess(g4=self.g4(structural_match=True))
        self.assertEqual(r.disposition, HOLD_G4_OWNER_CURRENTNESS_REQUIRED)
        self.assertFalse(r.bounded_g3_recompute_attempt_admitted)

    def test_legacy_g4_success_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.g4(structural_match=True), disposition="REVALIDATED_UNCHANGED").validate()

    def test_g4_projection_cannot_self_authenticate_owner_currentness(self):
        with self.assertRaises(ValueError):
            replace(self.g4(structural_match=True), owner_currentness_authenticated_by_this_contract=True).validate()

    def test_alias_resolution_hold_prevents_recompute_progress(self):
        r = self.assess(progress=self.progress(alias_hold=True))
        self.assertEqual(r.disposition, HOLD_ALIAS_RESOLUTION)
        self.assertFalse(r.bounded_g3_recompute_attempt_admitted)

    def test_unresolved_same_sid_route_alias_cannot_mint_progress(self):
        forged = replace(
            self.progress(ALLOW_CHANGED_AXIS),
            route_projection_changed=True,
            alias_projection_required=True,
            alias_projection_consumed=False,
        )
        with self.assertRaises(ValueError):
            forged.validate()

    def test_first_no_progress_repeat_requires_axis_change(self):
        r = self.assess(progress=self.progress(CHANGE_AXIS_REQUIRED))
        self.assertEqual(r.disposition, HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED)

    def test_repeated_no_progress_collapses_cone(self):
        r = self.assess(progress=self.progress(COLLAPSE_CONE))
        self.assertEqual(r.disposition, COLLAPSE_RECOMPUTE_CONE)

    def test_non_source_drift_with_alias_stable_independent_progress_admits(self):
        for decision in (ALLOW_INITIAL, ALLOW_CHANGED_AXIS, ALLOW_STATE_TRANSITION):
            with self.subTest(decision=decision):
                r = self.assess(progress=self.progress(decision))
                self.assertEqual(r.disposition, ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT)
                self.assertTrue(r.bounded_g3_recompute_attempt_admitted)

    def test_source_drift_requires_explicit_version_transition(self):
        r = self.assess(g4=self.g4(source_changed=True))
        self.assertEqual(r.disposition, HOLD_VERSION_TRANSITION_REQUIRED)

    def test_version_transition_does_not_pay_future_read_currentness(self):
        r = self.assess(g4=self.g4(source_changed=True), version=self.version())
        self.assertEqual(r.disposition, HOLD_SOURCE_READ_CURRENTNESS_REQUIRED)

    def test_stale_or_unknown_read_currentness_cannot_pay_debt(self):
        for state in (READ_STALE, READ_UNKNOWN):
            with self.subTest(state=state):
                r = self.assess(
                    g4=self.g4(source_changed=True),
                    version=self.version(),
                    currentness=self.currentness(state),
                )
                self.assertEqual(r.disposition, HOLD_SOURCE_READ_CURRENTNESS_REQUIRED)

    def test_source_drift_with_version_and_current_read_can_admit_candidate(self):
        r = self.assess(
            g4=self.g4(source_changed=True),
            version=self.version(),
            currentness=self.currentness(),
        )
        self.assertEqual(r.disposition, ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT)

    def test_version_edge_must_bind_exact_g4_source_generations(self):
        with self.assertRaises(ValueError):
            self.assess(
                g4=self.g4(source_changed=True),
                version=replace(self.version(), successor_source_binding_generation="source::19"),
            )

    def test_read_witness_must_bind_current_g4_source_generation(self):
        with self.assertRaises(ValueError):
            self.assess(
                g4=self.g4(source_changed=True),
                version=self.version(),
                currentness=self.currentness(source="source::19"),
            )

    def test_no_progress_dominates_extra_version_and_currentness_evidence(self):
        r = self.assess(
            g4=self.g4(source_changed=True),
            progress=self.progress(COLLAPSE_CONE),
            version=self.version(),
            currentness=self.currentness(),
        )
        self.assertEqual(r.disposition, COLLAPSE_RECOMPUTE_CONE)

    def test_different_j_classifiers_commute(self):
        kwargs = dict(
            g4=self.g4(source_changed=True),
            progress=self.progress(ALLOW_STATE_TRANSITION),
            version=self.version(),
            currentness=self.currentness(),
        )
        self.assertEqual(disposition_tree(**kwargs), disposition_table(**kwargs))

    def test_finite_lattice_exhausts_all_bounded_control_states(self):
        proof = prove_finite_recompute_lattice()
        self.assertEqual(proof["states"], 108)
        for outcome in (
            HOLD_G4_OWNER_CURRENTNESS_REQUIRED,
            HOLD_ALIAS_RESOLUTION,
            HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
            COLLAPSE_RECOMPUTE_CONE,
            HOLD_VERSION_TRANSITION_REQUIRED,
            HOLD_SOURCE_READ_CURRENTNESS_REQUIRED,
            ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT,
        ):
            self.assertGreater(proof.get(outcome, 0), 0, outcome)

    def test_receipt_is_deterministic(self):
        kwargs = dict(
            g4=self.g4(source_changed=True),
            progress=self.progress(ALLOW_STATE_TRANSITION),
            version=self.version(),
            currentness=self.currentness(),
        )
        self.assertEqual(
            assess_g3_recompute_admission(**kwargs).receipt_digest,
            assess_g3_recompute_admission(**kwargs).receipt_digest,
        )

    def test_claim_ceiling_cannot_be_widened(self):
        r = self.assess()
        for field in (
            "g4_owner_currentness_resolved_by_this_contract",
            "recompute_executed_by_this_contract",
            "retrieval_or_provider_effect_authorized",
            "transfer_effect_authorized",
            "native_route_mutated",
            "physical_io_proven",
            "source_currentness_minted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(r, **{field: True}).validate_claim_ceiling()


if __name__ == "__main__":
    unittest.main()
