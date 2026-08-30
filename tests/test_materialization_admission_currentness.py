import unittest

from tools.aura_integration.materialization_admission_currentness import (
    AdmissionState,
    BridgeDisposition,
    BridgeError,
    ConsumerAdmissionObservationV1,
    ExecutionState,
    MaterializationAdmissionCurrentnessBridgeV1,
    MaterializationReceiptV1,
    TransportClass,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64


def materialization(**kw):
    data = dict(
        transport=TransportClass.GITHUB,
        producer_owner_ref="owner:generator",
        producer_generation="gen:7",
        policy_ref="policy:codemap-v2",
        policy_generation="policy-gen:3",
        parent_target_ref="git:h1",
        materialized_target_ref="git:h2",
        materialized_target_digest=A,
        artifact_set_digest=B,
        allowed_delta_digest=C,
        currentness_ref="cur:h2",
        idempotency_key="materialize:h1:h2",
        effect_receipt_ref="effect:commit-push:1",
    )
    data.update(kw)
    return MaterializationReceiptV1(**data)


def observation(**kw):
    data = dict(
        consumer_owner_ref="owner:ci",
        consumer_generation="ci-gen:4",
        observed_target_ref="git:h2",
        observed_target_digest=A,
        idempotency_key="materialize:h1:h2",
        consumer_currentness_ref="ci-cur:h2",
        consumer_current=True,
        admission_state=AdmissionState.ADMITTED,
        admission_receipt_ref="admit:h2:1",
    )
    data.update(kw)
    return ConsumerAdmissionObservationV1(**data)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = MaterializationAdmissionCurrentnessBridgeV1()

    def test_materialized_not_admitted(self):
        out = self.bridge.adjudicate(materialization(), None)
        self.assertEqual(out.disposition, BridgeDisposition.MATERIALIZED_NOT_ADMITTED)
        self.assertFalse(out.consumer_admitted)

    def test_exact_current_admission(self):
        out = self.bridge.adjudicate(materialization(), observation())
        self.assertEqual(out.disposition, BridgeDisposition.CONSUMER_ADMITTED_CURRENT)
        self.assertTrue(out.consumer_admitted)
        self.assertFalse(out.execution_observed)

    def test_execution_observed_is_not_quality(self):
        out = self.bridge.adjudicate(materialization(), observation(execution_state=ExecutionState.EXECUTED, execution_receipt_ref="exec:h2:1"))
        self.assertEqual(out.disposition, BridgeDisposition.EXECUTION_OBSERVED)
        self.assertTrue(out.execution_succeeded)
        self.assertFalse(out.quality_satisfied)
        self.assertFalse(out.authority)
        self.assertFalse(out.effect_authorized)

    def test_execution_failed(self):
        out = self.bridge.adjudicate(materialization(), observation(execution_state=ExecutionState.FAILED, execution_receipt_ref="exec:h2:failed"))
        self.assertEqual(out.disposition, BridgeDisposition.EXECUTION_FAILED)
        self.assertFalse(out.execution_succeeded)

    def test_reconcile_required(self):
        out = self.bridge.adjudicate(materialization(), observation(execution_state=ExecutionState.RECONCILE_REQUIRED, execution_receipt_ref="exec:h2:reconcile"))
        self.assertEqual(out.disposition, BridgeDisposition.RECONCILE_REQUIRED)

    def test_idempotency_mismatch(self):
        self.assertEqual(self.bridge.adjudicate(materialization(), observation(idempotency_key="different:key")).disposition, BridgeDisposition.IDEMPOTENCY_MISMATCH)

    def test_target_ref_mismatch(self):
        self.assertEqual(self.bridge.adjudicate(materialization(), observation(observed_target_ref="git:other")).disposition, BridgeDisposition.ADMISSION_TARGET_MISMATCH)

    def test_target_digest_mismatch(self):
        self.assertEqual(self.bridge.adjudicate(materialization(), observation(observed_target_digest=B)).disposition, BridgeDisposition.ADMISSION_TARGET_DIGEST_MISMATCH)

    def test_stale_boolean_currentness_reopens(self):
        self.assertEqual(self.bridge.adjudicate(materialization(), observation(consumer_current=False)).disposition, BridgeDisposition.CURRENTNESS_REOPEN)

    def test_explicit_stale_state_reopens(self):
        self.assertEqual(self.bridge.adjudicate(materialization(), observation(admission_state=AdmissionState.STALE_REOPEN, admission_receipt_ref="admit:stale")).disposition, BridgeDisposition.CURRENTNESS_REOPEN)

    def test_refusal(self):
        self.assertEqual(self.bridge.adjudicate(materialization(), observation(admission_state=AdmissionState.REFUSED, admission_receipt_ref="admit:refused")).disposition, BridgeDisposition.CONSUMER_REFUSED)

    def test_duplicate_noop_gets_no_admission_credit(self):
        out = self.bridge.adjudicate(materialization(), observation(admission_state=AdmissionState.DUPLICATE_NOOP, admission_receipt_ref="admit:dupe"))
        self.assertEqual(out.disposition, BridgeDisposition.DUPLICATE_NOOP_OBSERVED)
        self.assertFalse(out.consumer_admitted)

    def test_execution_requires_admission(self):
        with self.assertRaisesRegex(BridgeError, "EXECUTION_REQUIRES_ADMITTED_STATE"):
            observation(admission_state=AdmissionState.REFUSED, admission_receipt_ref="admit:refused", execution_state=ExecutionState.EXECUTED, execution_receipt_ref="exec:bad")

    def test_execution_receipt_required(self):
        with self.assertRaisesRegex(BridgeError, "EXECUTION_RECEIPT_REQUIRED"):
            observation(execution_state=ExecutionState.EXECUTED)

    def test_currentness_must_be_real_bool(self):
        with self.assertRaisesRegex(BridgeError, "CONSUMER_CURRENT_BOOL_REQUIRED"):
            observation(consumer_current="true")

    def test_materialization_must_be_observed(self):
        with self.assertRaisesRegex(BridgeError, "MATERIALIZATION_NOT_OBSERVED"):
            materialization(materialization_observed=False)

    def test_unknown_transport_fails(self):
        with self.assertRaisesRegex(BridgeError, "TRANSPORT_INVALID"):
            materialization(transport="GITHUB")

    def test_bad_digest_fails(self):
        with self.assertRaisesRegex(BridgeError, "MATERIALIZED_TARGET_DIGEST_INVALID"):
            materialization(materialized_target_digest="not-a-sha")

    def test_deterministic_materialization_digest(self):
        self.assertEqual(materialization().logical_digest, materialization().logical_digest)

    def test_target_change_changes_identity(self):
        self.assertNotEqual(materialization().logical_digest, materialization(materialized_target_ref="git:h3").logical_digest)

    def test_idempotency_change_changes_identity(self):
        self.assertNotEqual(materialization().logical_digest, materialization(idempotency_key="materialize:h1:h2:v2").logical_digest)

    def test_transport_does_not_widen_authority(self):
        for transport in (TransportClass.DRIVE_BUS, TransportClass.QUEUE, TransportClass.LOCAL_ARTIFACT):
            out = self.bridge.adjudicate(materialization(transport=transport), observation())
            self.assertEqual(out.disposition, BridgeDisposition.CONSUMER_ADMITTED_CURRENT)
            self.assertFalse(out.authority)

    def test_decision_digest_deterministic(self):
        a = self.bridge.adjudicate(materialization(), observation())
        b = self.bridge.adjudicate(materialization(), observation())
        self.assertEqual(a.logical_digest, b.logical_digest)

    def test_all_effect_flags_false_after_execution(self):
        out = self.bridge.adjudicate(materialization(), observation(execution_state=ExecutionState.EXECUTED, execution_receipt_ref="exec:h2:1"))
        self.assertFalse(out.quality_satisfied)
        self.assertFalse(out.authority)
        self.assertFalse(out.effect_authorized)
        self.assertFalse(out.promotion_authorized)
        self.assertFalse(out.merge_authorized)


if __name__ == "__main__":
    unittest.main()
