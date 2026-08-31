from __future__ import annotations

from dataclasses import asdict, replace
import inspect
import unittest

from tools.quantization.aura_glm53_official_source_admission import current_public_state
from tools.quantization.aura_glm53_representation_specific_source_trial_gate import (
    Q5_SOURCE_BLOB_SHA,
    _classify_producer_state_for_test,
    _validate_source_admission,
    current_representation_specific_source_trial,
)
from tools.quantization.aura_glm53_quantization_evidence_transfer import q5_representation_identity


def hypothetical_header_green():
    return replace(
        current_public_state(),
        index_bytes_verified=True,
        representative_key_to_shard_bound=True,
        representative_headers_observed=True,
        fp8_companions_bound=True,
        header_trial_eligible=True,
        blocker="NONE_AT_HEADER_PLANE",
    )


class RepresentationSpecificSourceTrialGateTests(unittest.TestCase):
    def test_public_current_boundary_is_zero_input_and_producer_traversed(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(current_representation_specific_source_trial).parameters),
            (),
        )
        r = current_representation_specific_source_trial()
        self.assertEqual(r.disposition, "HOLD_SOURCE_HEADER_NOT_ELIGIBLE")
        self.assertFalse(r.header_bound_representation_trial_candidate)
        self.assertTrue(r.exact_target_representation_identity_bound)
        self.assertTrue(r.source_producer_traversed)
        self.assertFalse(r.source_snapshot_caller_supplied)
        self.assertEqual(r.q5_source_blob_sha, Q5_SOURCE_BLOB_SHA)

    def test_caller_mapping_cannot_enter_typed_producer_helper(self) -> None:
        forged = asdict(current_public_state())
        forged.update(
            index_bytes_verified=True,
            representative_key_to_shard_bound=True,
            representative_headers_observed=True,
            fp8_companions_bound=True,
            header_trial_eligible=True,
            blocker="CALLER_MINTED",
        )
        with self.assertRaisesRegex(ValueError, "Q5_ADMISSION_STATE_TYPE_REQUIRED"):
            _classify_producer_state_for_test(forged, q5_representation_identity())

    def test_header_green_exact_representation_only_grants_test_candidate(self) -> None:
        r = _classify_producer_state_for_test(
            hypothetical_header_green(), q5_representation_identity()
        )
        self.assertEqual(r.disposition, "HEADER_BOUND_REPRESENTATION_TRIAL_CANDIDATE")
        self.assertTrue(r.header_bound_representation_trial_candidate)
        self.assertTrue(r.source_producer_traversed)
        self.assertFalse(r.source_snapshot_caller_supplied)
        self.assertFalse(r.source_tensor_payload_bound)
        self.assertFalse(r.real_tensor_quantization_eligible)
        self.assertFalse(r.evidence_transfer_authorized)
        self.assertFalse(r.glm53_quality_evidence)
        self.assertFalse(r.runtime_evidence)
        self.assertFalse(r.gate10_promoted)

    def test_geometry_or_near_identity_drift_holds(self) -> None:
        target = q5_representation_identity()
        drifted = replace(target, index_bits_per_vector=8, codec_bits_per_weight=1.25)
        r = _classify_producer_state_for_test(hypothetical_header_green(), drifted)
        self.assertEqual(r.disposition, "HOLD_REPRESENTATION_IDENTITY_MISMATCH")
        self.assertFalse(r.exact_target_representation_identity_bound)
        self.assertFalse(r.header_bound_representation_trial_candidate)

    def test_header_boolean_cannot_skip_missing_q5_evidence(self) -> None:
        forged = replace(current_public_state(), header_trial_eligible=True)
        with self.assertRaisesRegex(ValueError, "Q5_SOURCE_EVIDENCE_ORDER_VIOLATION"):
            _validate_source_admission(forged)

    def test_payload_or_real_quantization_cannot_enter_header_gate(self) -> None:
        source = replace(hypothetical_header_green(), source_tensor_payload_bound=True)
        with self.assertRaisesRegex(
            ValueError, "Q7_HEADER_GATE_CANNOT_CONSUME_PAYLOAD_OR_EXECUTION_PROMOTION"
        ):
            _classify_producer_state_for_test(source, q5_representation_identity())

    def test_parent_authority_widening_rejected(self) -> None:
        for key in ("semantic_k27_authority", "native_transformer_kv_accessed", "gate10_promoted"):
            source = replace(current_public_state(), **{key: True})
            with self.assertRaisesRegex(ValueError, "Q5_PARENT_CEILING_WIDENED"):
                _validate_source_admission(source)

    def test_wrong_q5_generation_rejected(self) -> None:
        source = replace(current_public_state(), official_revision="foreign-revision")
        with self.assertRaisesRegex(ValueError, "OFFICIAL_SOURCE_GENERATION_MISMATCH"):
            _validate_source_admission(source)

    def test_receipt_is_deterministic(self) -> None:
        a = current_representation_specific_source_trial()
        b = current_representation_specific_source_trial()
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(a.source_admission_digest, current_public_state().digest())

    def test_claim_ceiling_is_complete_on_current_hold(self) -> None:
        r = asdict(current_representation_specific_source_trial())
        for key in (
            "header_bound_representation_trial_candidate",
            "source_snapshot_caller_supplied",
            "source_tensor_payload_bound",
            "real_tensor_quantization_eligible",
            "evidence_transfer_authorized",
            "glm53_quality_evidence",
            "runtime_evidence",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(r[key], key)


if __name__ == "__main__":
    unittest.main()
