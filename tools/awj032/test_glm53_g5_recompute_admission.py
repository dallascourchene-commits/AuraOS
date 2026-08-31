from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_g5_recompute_admission import (
    CANDIDATE_G3_RECOMPUTE_EXTERNAL_TRUST_REQUIRED,
    COLLAPSE_RECOMPUTE_CONE,
    G4_HOLD_RECOMPUTE,
    G4_STRUCTURAL_MATCH,
    HOLD_G4_OWNER_CURRENTNESS_AUTH_REQUIRED,
    HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
    HOLD_SOURCE_READ_CURRENTNESS_REQUIRED,
    HOLD_VERSION_TRANSITION_REQUIRED,
    PROGRESS_ALLOW_CHANGED_AXIS,
    PROGRESS_ALLOW_INITIAL,
    PROGRESS_ALLOW_STATE_TRANSITION,
    PROGRESS_CHANGE_AXIS_REQUIRED,
    PROGRESS_COLLAPSE_CONE,
    READ_RESOLVED_CURRENT,
    READ_STALE,
    READ_UNKNOWN,
    G4RevalidationProjection,
    RetrievalProgressProjection,
    SourceReadCurrentnessProjection,
    VersionTransitionProjection,
    assess_g3_recompute_admission,
    disposition_table,
    disposition_tree,
    prove_finite_recompute_lattice,
)


def d(ch: str) -> str:
    return ch * 64


class GLM53G5RecomputeAdmissionTests(unittest.TestCase):
    def g4(
        self, *, source_changed: bool = False, structural_match: bool = False
    ) -> G4RevalidationProjection:
        if structural_match:
            return G4RevalidationProjection(
                receipt_digest=d("a"),
                disposition=G4_STRUCTURAL_MATCH,
                changed_axes=(),
                frozen_source_binding_generation="source::17",
                current_source_binding_generation="source::17",
            )
        return G4RevalidationProjection(
            receipt_digest=d("a"),
            disposition=G4_HOLD_RECOMPUTE,
            changed_axes=(
                ("source_binding_generation",)
                if source_changed
                else ("runtime_generation",)
            ),
            frozen_source_binding_generation="source::17",
            current_source_binding_generation=(
                "source::18" if source_changed else "source::17"
            ),
        )

    def progress(
        self, disposition: str = PROGRESS_ALLOW_STATE_TRANSITION
    ) -> RetrievalProgressProjection:
        return RetrievalProgressProjection(
            receipt_digest=d("b"),
            disposition=disposition,
            retrieval_fingerprint_digest=d("c"),
            provider_state_generation="provider::17",
            evidence_digest=d("d"),
        )

    def version(self) -> VersionTransitionProjection:
        return VersionTransitionProjection(
            receipt_digest=d("e"),
            predecessor_source_binding_generation="source::17",
            successor_source_binding_generation="source::18",
            explicit_successor_edge=True,
            future_read_currentness_required=True,
        )

    def currentness(
        self,
        state: str = READ_RESOLVED_CURRENT,
        *,
        source: str = "source::18",
    ) -> SourceReadCurrentnessProjection:
        return SourceReadCurrentnessProjection(
            witness_digest=d("f"),
            source_binding_generation=source,
            owner_generation="reader::17",
            state=state,
        )

    def assess(self, *, g4=None, progress=None, version=None, currentness=None):
        return assess_g3_recompute_admission(
            g4=g4 or self.g4(),
            progress=progress or self.progress(),
            version=version,
            currentness=currentness,
        )

    def test_structural_match_cannot_suppress_recompute_without_owner_auth(self) -> None:
        receipt = self.assess(
            g4=self.g4(structural_match=True),
            currentness=self.currentness(source="source::17"),
        )
        self.assertEqual(
            receipt.disposition, HOLD_G4_OWNER_CURRENTNESS_AUTH_REQUIRED
        )
        self.assertFalse(receipt.bounded_g3_recompute_attempt_admitted)
        self.assertTrue(receipt.external_owner_currentness_auth_required)

    def test_no_progress_first_repeat_holds_before_candidate(self) -> None:
        receipt = self.assess(progress=self.progress(PROGRESS_CHANGE_AXIS_REQUIRED))
        self.assertEqual(receipt.disposition, HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED)
        self.assertFalse(receipt.bounded_g3_recompute_attempt_admitted)

    def test_repeated_no_progress_collapses_recompute_cone(self) -> None:
        receipt = self.assess(progress=self.progress(PROGRESS_COLLAPSE_CONE))
        self.assertEqual(receipt.disposition, COLLAPSE_RECOMPUTE_CONE)
        self.assertFalse(receipt.bounded_g3_recompute_attempt_admitted)

    def test_non_source_drift_with_progress_is_candidate_not_admission(self) -> None:
        for disposition in (
            PROGRESS_ALLOW_INITIAL,
            PROGRESS_ALLOW_CHANGED_AXIS,
            PROGRESS_ALLOW_STATE_TRANSITION,
        ):
            with self.subTest(disposition=disposition):
                receipt = self.assess(progress=self.progress(disposition))
                self.assertEqual(
                    receipt.disposition,
                    CANDIDATE_G3_RECOMPUTE_EXTERNAL_TRUST_REQUIRED,
                )
                self.assertFalse(receipt.bounded_g3_recompute_attempt_admitted)
                self.assertTrue(receipt.g4_repaired_terminal_proof_required)
                self.assertFalse(receipt.g4_repaired_terminal_proof_available)
                self.assertTrue(receipt.external_owner_currentness_auth_required)
                self.assertFalse(receipt.recompute_executed_by_this_contract)

    def test_source_drift_without_version_transition_holds(self) -> None:
        receipt = self.assess(g4=self.g4(source_changed=True))
        self.assertEqual(receipt.disposition, HOLD_VERSION_TRANSITION_REQUIRED)

    def test_source_version_transition_without_read_currentness_holds(self) -> None:
        receipt = self.assess(
            g4=self.g4(source_changed=True), version=self.version()
        )
        self.assertEqual(receipt.disposition, HOLD_SOURCE_READ_CURRENTNESS_REQUIRED)

    def test_stale_or_unknown_read_currentness_cannot_pay_future_read_debt(self) -> None:
        for state in (READ_STALE, READ_UNKNOWN):
            with self.subTest(state=state):
                receipt = self.assess(
                    g4=self.g4(source_changed=True),
                    version=self.version(),
                    currentness=self.currentness(state),
                )
                self.assertEqual(
                    receipt.disposition, HOLD_SOURCE_READ_CURRENTNESS_REQUIRED
                )

    def test_caller_resolved_current_is_still_only_external_trust_candidate(self) -> None:
        receipt = self.assess(
            g4=self.g4(source_changed=True),
            version=self.version(),
            currentness=self.currentness(),
        )
        self.assertEqual(
            receipt.disposition,
            CANDIDATE_G3_RECOMPUTE_EXTERNAL_TRUST_REQUIRED,
        )
        self.assertFalse(receipt.bounded_g3_recompute_attempt_admitted)
        self.assertTrue(receipt.external_owner_currentness_auth_required)

    def test_no_progress_dominates_currentness_surplus(self) -> None:
        receipt = self.assess(
            g4=self.g4(source_changed=True),
            progress=self.progress(PROGRESS_COLLAPSE_CONE),
            version=self.version(),
            currentness=self.currentness(),
        )
        self.assertEqual(receipt.disposition, COLLAPSE_RECOMPUTE_CONE)

    def test_source_version_binding_must_match_g4_transition(self) -> None:
        with self.assertRaises(ValueError):
            self.assess(
                g4=self.g4(source_changed=True),
                version=replace(
                    self.version(), successor_source_binding_generation="source::19"
                ),
            )

    def test_currentness_witness_must_bind_current_source_generation(self) -> None:
        with self.assertRaises(ValueError):
            self.assess(
                g4=self.g4(source_changed=True),
                version=self.version(),
                currentness=self.currentness(source="source::19"),
            )

    def test_g4_source_drift_declaration_cannot_be_inconsistent(self) -> None:
        with self.assertRaises(ValueError):
            replace(
                self.g4(),
                changed_axes=("source_binding_generation",),
                current_source_binding_generation="source::17",
            ).validate()

    def test_g4_projection_cannot_self_mint_currentness_or_reuse(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.g4(), owner_currentness_authenticated=True).validate()
        with self.assertRaises(ValueError):
            replace(self.g4(), reuse_authorized=True).validate()

    def test_version_transition_must_carry_future_read_debt(self) -> None:
        with self.assertRaises(ValueError):
            replace(
                self.version(), future_read_currentness_required=False
            ).validate()

    def test_version_projection_cannot_self_authenticate_source(self) -> None:
        with self.assertRaises(ValueError):
            replace(
                self.version(), source_owner_authenticated_by_this_contract=True
            ).validate()
        with self.assertRaises(ValueError):
            replace(
                self.version(), source_currentness_proven_by_this_contract=True
            ).validate()

    def test_currentness_projection_cannot_self_authenticate_owner(self) -> None:
        currentness = self.currentness()
        with self.assertRaises(ValueError):
            replace(currentness, authenticated_by_this_contract=True).validate()
        with self.assertRaises(ValueError):
            replace(
                currentness, external_owner_authentication_required=False
            ).validate()

    def test_different_j_classifiers_commute(self) -> None:
        kwargs = dict(
            g4=self.g4(source_changed=True),
            progress=self.progress(PROGRESS_ALLOW_CHANGED_AXIS),
            version=self.version(),
            currentness=self.currentness(),
        )
        self.assertEqual(disposition_tree(**kwargs), disposition_table(**kwargs))

    def test_finite_recompute_lattice_exhausts_90_without_any_admission(self) -> None:
        proof = prove_finite_recompute_lattice()
        self.assertEqual(proof["states"], 90)
        self.assertGreater(
            proof[CANDIDATE_G3_RECOMPUTE_EXTERNAL_TRUST_REQUIRED], 0
        )
        self.assertGreater(proof[HOLD_G4_OWNER_CURRENTNESS_AUTH_REQUIRED], 0)
        self.assertGreater(proof[COLLAPSE_RECOMPUTE_CONE], 0)
        self.assertGreater(proof[HOLD_VERSION_TRANSITION_REQUIRED], 0)
        self.assertGreater(proof[HOLD_SOURCE_READ_CURRENTNESS_REQUIRED], 0)

    def test_receipt_is_deterministic(self) -> None:
        kwargs = dict(
            g4=self.g4(source_changed=True),
            progress=self.progress(),
            version=self.version(),
            currentness=self.currentness(),
        )
        a = assess_g3_recompute_admission(**kwargs)
        b = assess_g3_recompute_admission(**kwargs)
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_receipt_cannot_self_close_missing_g4_or_owner_trust(self) -> None:
        receipt = self.assess()
        for field, value in (
            ("bounded_g3_recompute_attempt_admitted", True),
            ("g4_repaired_terminal_proof_required", False),
            ("g4_repaired_terminal_proof_available", True),
            ("external_owner_currentness_auth_required", False),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(receipt, **{field: value}).validate_claim_ceiling()

    def test_claim_ceiling_cannot_be_widened(self) -> None:
        receipt = self.assess()
        for field in (
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
                replace(receipt, **{field: True}).validate_claim_ceiling()

    def test_bad_digest_rejected(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.progress(), evidence_digest="bad").validate()


if __name__ == "__main__":
    unittest.main()
