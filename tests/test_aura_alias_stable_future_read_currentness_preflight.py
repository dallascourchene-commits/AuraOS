import unittest
from dataclasses import replace

import tools.aura_alias_stable_future_read_currentness_preflight as m
from tools.aura_nav13d_eki4_hydrated_version_handoff import (
    HandoffDisposition,
    HydratedVersionHandoffReceiptV1,
)

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


class AliasStableFutureReadCurrentnessPreflightTests(unittest.TestCase):
    def handoff(self, **overrides):
        values = dict(
            disposition=HandoffDisposition.HANDOFF_READY_CANDIDATE,
            reason="ready",
            hydration_completion_digest=D0,
            transition_receipt_digest=D1,
            subject_key=D0,
            evidence_generation_key=D1,
            material_digest=D2,
            exact_source_uri="https://example.test/source",
            future_read_axes=m.EXPECTED_FUTURE_AXES,
            eki2_read_axes=m.EXPECTED_EKI2_AXES,
            handoff_digest=D3,
        )
        values.update(overrides)
        return HydratedVersionHandoffReceiptV1(**values)

    def progress(self, decision=m.AliasProgressDecision.ALLOW_STATE_TRANSITION, **overrides):
        values = dict(
            schema=m.ALIAS_PROGRESS_SCHEMA,
            semantic_owner_head=m.PR759_SEMANTIC_HEAD,
            proof_head=m.PR759_PROOF_HEAD,
            proof_run=m.PR759_PROOF_RUN,
            proof_job=m.PR759_PROOF_JOB,
            decision=decision,
            current_view_digest=D2,
            semantic_fingerprint_digest=D3,
            source_sid_same=True,
            route_projection_changed=True,
            alias_projection_required=True,
            alias_projection_consumed=(
                decision is not m.AliasProgressDecision.HOLD_ALIAS_RESOLUTION_REQUIRED
            ),
            prior_no_progress_count=0,
            next_no_progress_count=0,
        )
        values.update(overrides)
        return m.AliasAwareRetrievalProgressProjectionV1(**values)

    def binding(self, **overrides):
        values = dict(
            schema=m.BINDING_SCHEMA,
            subject_key=D0,
            evidence_generation_key=D1,
            exact_source_uri="https://example.test/source",
            handoff_source_view_canonical_key="https://example.test/source",
            handoff_source_view_digest=D0,
            current_view_digest=D2,
            source_sid="sid:source",
            owner_ref="source-owner",
            owner_generation="owner-g1",
            owner_receipt_digest=D3,
        )
        values.update(overrides)
        return m.HandoffSourceRouteAliasBindingProjectionV1(**values)

    def intent(self, **overrides):
        values = dict(
            subject_key=D0,
            evidence_generation_key=D1,
            requested_future_read_axes=m.EXPECTED_FUTURE_AXES,
            requested_eki2_read_axes=m.EXPECTED_EKI2_AXES,
        )
        values.update(overrides)
        return m.FutureReadCurrentnessProbeIntentV1(**values)

    def admit(self, **overrides):
        values = dict(
            handoff_semantic_head=m.PR760_SEMANTIC_HEAD,
            handoff=self.handoff(),
            progress=self.progress(),
            binding=self.binding(),
            intent=self.intent(),
        )
        values.update(overrides)
        return m.admit_alias_stable_future_read_currentness_probe(**values)

    def test_exact_state_admits_probe_candidate_only(self):
        receipt = self.admit()
        self.assertEqual(
            receipt.disposition,
            m.FutureReadPreflightDisposition.FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE,
        )
        self.assertTrue(receipt.probe_admissible_candidate)
        self.assertTrue(receipt.read_currentness_debt_carried)
        self.assertFalse(receipt.source_currentness_proven)
        self.assertFalse(receipt.read_currentness_proven)
        self.assertFalse(receipt.semantic_truth_proven)
        self.assertFalse(receipt.evidence_admitted)
        self.assertFalse(receipt.retrieval_executed)
        self.assertFalse(receipt.persistent_use_authorized)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.semantic_k27_authority_minted)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)

    def test_all_positive_progress_states_can_only_admit_probe_candidate(self):
        for decision in (
            m.AliasProgressDecision.ALLOW_INITIAL,
            m.AliasProgressDecision.ALLOW_CHANGED_AXIS,
            m.AliasProgressDecision.ALLOW_STATE_TRANSITION,
        ):
            with self.subTest(decision=decision):
                receipt = self.admit(progress=self.progress(decision))
                self.assertTrue(receipt.probe_admissible_candidate)
                self.assertFalse(receipt.read_currentness_proven)

    def test_wrong_parent_generation_holds(self):
        receipt = self.admit(handoff_semantic_head="wrong")
        self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.HOLD_PARENT_GENERATION)

    def test_handoff_not_ready_holds(self):
        receipt = self.admit(
            handoff=self.handoff(disposition=HandoffDisposition.HOLD_TRANSITION_NOT_READY)
        )
        self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.HOLD_HANDOFF_NOT_READY)

    def test_carried_read_debt_must_be_exact(self):
        receipt = self.admit(handoff=self.handoff(future_read_axes=("wrong",)))
        self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.HOLD_READ_DEBT_NOT_CARRIED)

    def test_requested_axes_must_equal_carried_debt(self):
        receipt = self.admit(intent=self.intent(requested_future_read_axes=("wrong",)))
        self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.HOLD_READ_AXES_MISMATCH)

    def test_binding_is_required(self):
        receipt = self.admit(binding=None)
        self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.HOLD_SOURCE_BINDING_REQUIRED)

    def test_subject_evidence_source_and_current_view_binding_mismatches_hold(self):
        cases = (
            dict(subject_key=D1),
            dict(evidence_generation_key=D2),
            dict(exact_source_uri="https://example.test/other", handoff_source_view_canonical_key="https://example.test/other"),
            dict(current_view_digest=D3),
        )
        for change in cases:
            with self.subTest(change=change):
                receipt = self.admit(binding=self.binding(**change))
                self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.HOLD_SOURCE_BINDING_MISMATCH)

    def test_binding_uri_must_equal_handoff_source_view_key(self):
        with self.assertRaises(ValueError):
            self.admit(binding=self.binding(handoff_source_view_canonical_key="session:source"))

    def test_alias_resolution_hold_propagates(self):
        receipt = self.admit(
            progress=self.progress(m.AliasProgressDecision.HOLD_ALIAS_RESOLUTION_REQUIRED)
        )
        self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.HOLD_ALIAS_RESOLUTION_REQUIRED)

    def test_change_axis_required_propagates(self):
        receipt = self.admit(
            progress=self.progress(
                m.AliasProgressDecision.CHANGE_AXIS_REQUIRED,
                prior_no_progress_count=0,
                next_no_progress_count=1,
            )
        )
        self.assertEqual(
            receipt.disposition,
            m.FutureReadPreflightDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
        )

    def test_repeated_no_progress_collapses_probe_cone(self):
        receipt = self.admit(
            progress=self.progress(
                m.AliasProgressDecision.COLLAPSE_CONE,
                prior_no_progress_count=1,
                next_no_progress_count=2,
            )
        )
        self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.COLLAPSE_RETRIEVAL_CONE)

    def test_parent_proof_identity_is_exact(self):
        with self.assertRaises(ValueError):
            self.admit(progress=self.progress(proof_run="wrong"))

    def test_upstream_or_binding_authority_widening_fails_closed(self):
        with self.assertRaises(ValueError):
            self.admit(progress=self.progress(authority_granted=True))
        with self.assertRaises(ValueError):
            self.admit(binding=self.binding(source_currentness_proven=True))
        receipt = self.admit(handoff=self.handoff(effect_authorized=True))
        self.assertEqual(receipt.disposition, m.FutureReadPreflightDisposition.HOLD_CLAIM_CEILING)

    def test_receipt_is_deterministic_and_identity_sensitive(self):
        one = self.admit()
        two = self.admit()
        self.assertEqual(one.probe_receipt_digest, two.probe_receipt_digest)
        changed = self.admit(
            progress=self.progress(semantic_fingerprint_digest=D2)
        )
        self.assertNotEqual(one.probe_receipt_digest, changed.probe_receipt_digest)

    def test_different_j_complete_matrix(self):
        self.assertEqual(m.prove_different_j(), 192)


if __name__ == "__main__":
    unittest.main()
