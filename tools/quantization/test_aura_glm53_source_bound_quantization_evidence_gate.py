#!/usr/bin/env python3
from dataclasses import replace
import inspect
import unittest

from tools.quantization.aura_glm53_source_bound_quantization_evidence_gate import (
    HISTORICAL_BRIDGE_OWNER_BLOB_SHA,
    HISTORICAL_BRIDGE_VERSION,
    HISTORICAL_W2_DRIVE_OBSERVATION,
    HISTORICAL_W2_HEADER_SHA256,
    HISTORICAL_W2_JOB,
    HISTORICAL_W2_PRODUCER_HEAD,
    HISTORICAL_W2_RECEIPT_DIGEST,
    HISTORICAL_W2_RUN,
    OFFICIAL_INDEX_SHA256,
    OFFICIAL_INDEX_SIZE,
    OFFICIAL_INDEX_XET_HASH,
    Q5_CURRENT_SOURCE_STATE_DIGEST,
    Q5_EXACT_HEAD,
    Q5_EXACT_RUN,
    Q6_EXACT_HEAD,
    Q6_EXACT_RUN,
    SYNTHETIC_DISTORTION_SCOPE,
    _current_historical_bridge,
    _current_q5_snapshot,
    _evaluate,
    current_source_bound_evidence_gate,
)


class SourceBoundEvidenceGateTests(unittest.TestCase):
    def test_current_gate_separates_historical_source_proof_from_current_holds(self):
        out = current_source_bound_evidence_gate()
        bridge = _current_historical_bridge()
        self.assertEqual(out.q5_source_head, Q5_EXACT_HEAD)
        self.assertEqual(out.q5_source_run, Q5_EXACT_RUN)
        self.assertEqual(out.q6_evidence_head, Q6_EXACT_HEAD)
        self.assertEqual(out.q6_evidence_run, Q6_EXACT_RUN)
        self.assertEqual(out.source_state_digest, Q5_CURRENT_SOURCE_STATE_DIGEST)
        self.assertEqual(out.official_index_sha256, OFFICIAL_INDEX_SHA256)
        self.assertEqual(out.official_index_size, OFFICIAL_INDEX_SIZE)
        self.assertEqual(out.official_index_xet_hash, OFFICIAL_INDEX_XET_HASH)
        self.assertFalse(out.current_source_index_bytes_verified)
        self.assertFalse(out.current_source_headers_observed)
        self.assertFalse(out.current_source_header_trial_eligible)
        self.assertEqual(out.historical_bridge_version, HISTORICAL_BRIDGE_VERSION)
        self.assertEqual(out.historical_bridge_owner_blob, HISTORICAL_BRIDGE_OWNER_BLOB_SHA)
        self.assertEqual(out.historical_bridge_digest, bridge.digest)
        self.assertTrue(out.historical_official_index_relation_observed)
        self.assertTrue(out.historical_official_headers_observed)
        self.assertTrue(out.historical_official_fp8_companions_bound)
        self.assertTrue(out.historical_observation_representative_only)
        self.assertEqual(out.historical_producer_head, HISTORICAL_W2_PRODUCER_HEAD)
        self.assertEqual(out.historical_producer_run, HISTORICAL_W2_RUN)
        self.assertEqual(out.historical_producer_job, HISTORICAL_W2_JOB)
        self.assertEqual(out.historical_drive_observation, HISTORICAL_W2_DRIVE_OBSERVATION)
        self.assertEqual(out.historical_receipt_digest, HISTORICAL_W2_RECEIPT_DIGEST)
        self.assertEqual(out.historical_header_sha256, HISTORICAL_W2_HEADER_SHA256)
        self.assertEqual(out.historical_entry_count, 6)
        self.assertEqual(out.historical_payload_bytes_read, 0)
        self.assertFalse(out.historical_evidence_implies_current_raw_bytes)
        self.assertFalse(out.historical_evidence_implies_global_layout_uniformity)
        self.assertFalse(out.exact_representation_identity_match)
        self.assertTrue(out.geometry_family_label_match)
        self.assertTrue(out.independent_current_source_transport_residual)
        self.assertTrue(out.independent_representation_evidence_residual)
        self.assertFalse(out.source_bound_evidence_admitted)
        self.assertEqual(out.disposition, "HOLD_CURRENT_SOURCE_TRANSPORT_AND_REPRESENTATION_EVIDENCE")

    def test_public_current_gate_has_no_override_surface(self):
        self.assertEqual(tuple(inspect.signature(current_source_bound_evidence_gate).parameters), ())
        self.assertEqual(tuple(inspect.signature(_current_historical_bridge).parameters), ())

    def test_index_object_identity_cannot_self_mint_current_index_bytes(self):
        source = _current_q5_snapshot()
        forged = replace(source, representative_key_to_shard_bound=True)
        with self.assertRaisesRegex(ValueError, "Q5_SOURCE_EVIDENCE_ORDER_VIOLATION"):
            _evaluate(forged)

    def test_header_trial_requires_all_current_source_preconditions(self):
        source = _current_q5_snapshot()
        forged = replace(source, index_bytes_verified=True, header_trial_eligible=True)
        with self.assertRaisesRegex(ValueError, "Q5_HEADER_TRIAL_PRECONDITIONS_MISSING"):
            _evaluate(forged)

    def test_real_tensor_eligibility_cannot_skip_payload_binding(self):
        source = _current_q5_snapshot()
        forged = replace(
            source,
            index_bytes_verified=True,
            representative_key_to_shard_bound=True,
            representative_headers_observed=True,
            fp8_companions_bound=True,
            header_trial_eligible=True,
            real_tensor_quantization_eligible=True,
        )
        with self.assertRaisesRegex(ValueError, "Q5_REAL_TENSOR_PRECONDITIONS_MISSING"):
            _evaluate(forged)

    def test_q5_authority_ceiling_cannot_be_widened(self):
        for field in ("semantic_k27_authority", "native_transformer_kv_accessed", "gate10_promoted"):
            source = replace(_current_q5_snapshot(), **{field: True})
            with self.assertRaisesRegex(ValueError, "Q5_AUTHORITY_CEILING_WIDENED"):
                _evaluate(source)

    def test_historical_headers_do_not_self_mint_current_header_trial(self):
        out = current_source_bound_evidence_gate()
        self.assertTrue(out.historical_official_headers_observed)
        self.assertFalse(out.current_source_header_trial_eligible)
        self.assertTrue(out.independent_current_source_transport_residual)
        self.assertFalse(out.source_bound_evidence_admitted)

    def test_even_hypothetical_current_header_green_does_not_transfer_q4_evidence_to_q5(self):
        source = replace(
            _current_q5_snapshot(),
            index_bytes_verified=True,
            representative_key_to_shard_bound=True,
            representative_headers_observed=True,
            fp8_companions_bound=True,
            header_trial_eligible=True,
            blocker="NONE_AT_HEADER_LEVEL",
        )
        out = _evaluate(source)
        self.assertFalse(out.independent_current_source_transport_residual)
        self.assertTrue(out.independent_representation_evidence_residual)
        self.assertFalse(out.source_bound_evidence_admitted)
        self.assertEqual(out.disposition, "HOLD_REPRESENTATION_EXACT_EVIDENCE")
        self.assertFalse(out.glm53_tensor_evidence_admitted)
        self.assertFalse(out.coding_quality_evidence_admitted)
        self.assertFalse(out.runtime_evidence_admitted)

    def test_synthetic_scope_never_becomes_model_or_runtime_evidence(self):
        out = current_source_bound_evidence_gate()
        self.assertEqual(out.source_evidence_scope, SYNTHETIC_DISTORTION_SCOPE)
        self.assertFalse(out.glm53_tensor_evidence_admitted)
        self.assertFalse(out.coding_quality_evidence_admitted)
        self.assertFalse(out.runtime_evidence_admitted)
        self.assertFalse(out.semantic_k27_authority_minted)
        self.assertFalse(out.native_transformer_kv_accessed)
        self.assertFalse(out.gate10_promoted)

    def test_gate_and_bridge_are_deterministic(self):
        a = current_source_bound_evidence_gate()
        b = current_source_bound_evidence_gate()
        self.assertEqual(a.gate_digest, b.gate_digest)
        self.assertEqual(_current_historical_bridge().digest, _current_historical_bridge().digest)


if __name__ == "__main__":
    unittest.main()
