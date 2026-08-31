import unittest

from tools.aura_scheme_serializable_hydration_transaction import (
    HydrationIntentProjection,
    HydrationTransactionDisposition,
    RETRIEVAL_SCHEMA,
    ROUTE_SCHEMA,
    RetrievalProgressDisposition,
    RetrievalProgressProjection,
    SchemeBoundRouteProjection,
    admit_scheme_serializable_hydration_transaction,
    prove_different_j,
)


A = "a" * 64
B = "b" * 64
C = "c" * 64


class SchemeSerializableHydrationTransactionTests(unittest.TestCase):
    def route(self, **overrides):
        values = dict(
            schema=ROUTE_SCHEMA,
            source_identity="source:paper:2607.04281",
            scheme_id="SESSION-B3MOD27-v1",
            normalization_version="norm-v1",
            canonical_key="arxiv:2607.04281",
            full_digest=A,
            coordinate_view_digest=B,
            k27_path="K27://5/7/13",
            route_generation="route-g1",
            owner_epoch="epoch-17",
            route_current=True,
        )
        values.update(overrides)
        return SchemeBoundRouteProjection(**values)

    def retrieval(self, disposition=RetrievalProgressDisposition.ALLOW_STATE_TRANSITION, **overrides):
        values = dict(
            schema=RETRIEVAL_SCHEMA,
            disposition=disposition,
            fingerprint_digest=A,
            provider_state_generation="provider-g2",
            evidence_digest=C,
            next_no_progress_count=0,
        )
        values.update(overrides)
        return RetrievalProgressProjection(**values)

    def intent(self, **overrides):
        values = dict(
            semantic_plan_digest=B,
            evidence_generation_key="evidence-g2",
            target_level=2,
            new_hydration_required=True,
            exact_reopen_handle="https://arxiv.org/abs/2607.04281",
        )
        values.update(overrides)
        return HydrationIntentProjection(**values)

    def admit(self, *, pre=None, post=None, retrieval=None, intent=None):
        return admit_scheme_serializable_hydration_transaction(
            pre_route=pre or self.route(),
            post_route=post or self.route(),
            retrieval=retrieval or self.retrieval(),
            intent=intent or self.intent(),
        )

    def test_stable_route_epoch_and_state_delta_admits_bounded_transaction(self):
        receipt = self.admit()
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION)
        self.assertTrue(receipt.bounded_transaction_admitted)
        self.assertFalse(receipt.source_currentness_proven)
        self.assertFalse(receipt.semantic_truth_proven)
        self.assertFalse(receipt.evidence_admitted)
        self.assertFalse(receipt.materialization_executed)
        self.assertFalse(receipt.authorization_issued)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.semantic_k27_authority)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)

    def test_initial_retrieval_is_admissible_but_nonpromoting(self):
        receipt = self.admit(retrieval=self.retrieval(RetrievalProgressDisposition.ALLOW_INITIAL))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION)
        self.assertFalse(receipt.source_currentness_proven)

    def test_changed_retrieval_axis_is_admissible(self):
        receipt = self.admit(retrieval=self.retrieval(RetrievalProgressDisposition.ALLOW_CHANGED_AXIS))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION)

    def test_source_identity_change_holds_before_other_axes(self):
        receipt = self.admit(post=self.route(source_identity="source:paper:other", owner_epoch="epoch-18"))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.HOLD_SOURCE_IDENTITY_MISMATCH)

    def test_owner_epoch_drift_holds(self):
        receipt = self.admit(post=self.route(owner_epoch="epoch-18"))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.HOLD_OWNER_EPOCH_CHANGED)

    def test_scheme_change_requires_route_recompute_without_semantic_divergence(self):
        receipt = self.admit(post=self.route(scheme_id="SESSION-ALT-v1"))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.HOLD_ROUTE_RECOMPUTE)
        self.assertEqual(receipt.source_identity, self.route().source_identity)

    def test_normalization_or_coordinate_route_change_requires_recompute(self):
        cases = (
            dict(normalization_version="norm-v2"),
            dict(canonical_key="arxiv:v2:2607.04281"),
            dict(full_digest=C),
            dict(coordinate_view_digest=C),
            dict(k27_path="K27://5/7/14"),
            dict(route_generation="route-g2"),
            dict(route_current=False),
        )
        for change in cases:
            with self.subTest(change=change):
                receipt = self.admit(post=self.route(**change))
                self.assertEqual(receipt.disposition, HydrationTransactionDisposition.HOLD_ROUTE_RECOMPUTE)

    def test_new_hydration_requires_exact_reopen_handle(self):
        receipt = self.admit(intent=self.intent(exact_reopen_handle=None))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.HOLD_REOPEN_BINDING_REQUIRED)

    def test_no_new_hydration_does_not_require_reopen_handle(self):
        receipt = self.admit(intent=self.intent(new_hydration_required=False, exact_reopen_handle=None))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION)

    def test_first_identical_no_progress_requires_axis_change(self):
        receipt = self.admit(retrieval=self.retrieval(RetrievalProgressDisposition.CHANGE_AXIS_REQUIRED, next_no_progress_count=1))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED)
        self.assertFalse(receipt.bounded_transaction_admitted)

    def test_repeated_identical_no_progress_collapses_cone(self):
        receipt = self.admit(retrieval=self.retrieval(RetrievalProgressDisposition.COLLAPSE_CONE, next_no_progress_count=2))
        self.assertEqual(receipt.disposition, HydrationTransactionDisposition.COLLAPSE_RETRIEVAL_CONE)
        self.assertFalse(receipt.bounded_transaction_admitted)

    def test_route_authority_widening_rejected(self):
        with self.assertRaises(ValueError):
            self.admit(pre=self.route(semantic_k27_authority=True))

    def test_retrieval_authority_widening_rejected(self):
        with self.assertRaises(ValueError):
            self.admit(retrieval=self.retrieval(authority_granted=True))

    def test_transaction_identity_is_deterministic(self):
        one = self.admit()
        two = self.admit()
        self.assertEqual(one.transaction_digest, two.transaction_digest)

    def test_retrieval_evidence_generation_is_identity_bearing(self):
        one = self.admit(retrieval=self.retrieval(evidence_digest=A))
        two = self.admit(retrieval=self.retrieval(evidence_digest=C))
        self.assertNotEqual(one.transaction_digest, two.transaction_digest)

    def test_different_j_exhaustive_matrix(self):
        self.assertEqual(prove_different_j(), 80)


if __name__ == "__main__":
    unittest.main()
