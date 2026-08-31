from __future__ import annotations

from dataclasses import asdict
import unittest

from tools.quantization.aura_glm53_official_source_concrete_page_provenance_join import (
    CONCRETE_TRIAL_HEAD,
    CONCRETE_TRIAL_RUN,
    CONCRETE_TRIAL_SOURCE_BLOB,
    HISTORICAL_EVIDENCE_CONVERGENCE_COMMIT,
    HISTORICAL_W2_HEAD,
    HISTORICAL_W2_RUN,
    HISTORICAL_W2_SOURCE_BLOB,
    OFFICIAL_BRIDGE_HEAD,
    OFFICIAL_BRIDGE_RUN,
    OFFICIAL_BRIDGE_SOURCE_BLOB,
    ORIGINAL_CONVERGENCE_COMMIT,
    REQUIRED_SUCCESSOR_EVIDENCE,
    current_provenance_frontier,
    public_api_has_promotion_inputs,
)


class OfficialSourceConcretePageProvenanceJoinTests(unittest.TestCase):
    def test_exact_original_and_historical_generations_are_pinned(self) -> None:
        r = current_provenance_frontier()
        self.assertEqual(r.original_convergence_commit, ORIGINAL_CONVERGENCE_COMMIT)
        self.assertEqual(r.historical_evidence_convergence_commit, HISTORICAL_EVIDENCE_CONVERGENCE_COMMIT)
        self.assertEqual(r.exact_original_parent_heads, (OFFICIAL_BRIDGE_HEAD, CONCRETE_TRIAL_HEAD))
        self.assertEqual(r.exact_original_parent_runs, (OFFICIAL_BRIDGE_RUN, CONCRETE_TRIAL_RUN))
        self.assertEqual(r.exact_original_parent_source_blobs, (OFFICIAL_BRIDGE_SOURCE_BLOB, CONCRETE_TRIAL_SOURCE_BLOB))
        self.assertEqual(r.historical_w2_head, HISTORICAL_W2_HEAD)
        self.assertEqual(r.historical_w2_run, HISTORICAL_W2_RUN)
        self.assertEqual(r.historical_w2_source_blob, HISTORICAL_W2_SOURCE_BLOB)

    def test_concrete_candidate_evidence_is_retained(self) -> None:
        r = current_provenance_frontier()
        self.assertTrue(r.concrete_candidate_identity_bound)
        self.assertTrue(r.concrete_candidate_sample_bound)
        self.assertTrue(r.concrete_independent_verifier_bound)

    def test_historical_w2_rep_header_evidence_is_positive(self) -> None:
        r = current_provenance_frontier()
        self.assertTrue(r.historical_raw_index_verification_observed)
        self.assertTrue(r.historical_weight_map_relation_observed)
        self.assertTrue(r.historical_representative_headers_observed)
        self.assertTrue(r.historical_fp8_companions_bound)
        self.assertEqual(r.historical_payload_bytes_read, 0)
        self.assertTrue(r.historical_representative_header_geometry_conforms_current_schema)
        self.assertEqual(r.historical_representative_layer, 3)
        self.assertEqual(r.historical_representative_expert, 0)
        self.assertEqual(r.historical_representative_shard, "model-00038-of-00141.safetensors")
        self.assertTrue(r.representative_per_expert_serialization_proven)

    def test_historical_header_evidence_does_not_mint_current_bytes_or_global_layout(self) -> None:
        r = current_provenance_frontier()
        self.assertFalse(r.all_layers_experts_uniformity_proven)
        self.assertFalse(r.current_consumer_raw_index_bytes_materialized)
        self.assertFalse(r.current_consumer_raw_header_prefixes_materialized)
        self.assertFalse(r.official_source_transport_frontier_complete)
        self.assertFalse(r.historical_header_evidence_closes_current_transport)

    def test_historical_header_evidence_does_not_mint_tensor_or_page_provenance(self) -> None:
        r = current_provenance_frontier()
        self.assertFalse(r.official_source_tensor_payload_observed)
        self.assertFalse(r.official_source_byte_domain_bound_to_trial)
        self.assertFalse(r.concrete_page_official_source_authenticated)
        self.assertFalse(r.concrete_page_source_tensor_set_bound_to_official_source)
        self.assertFalse(r.candidate_page_materialization_owner_bound)
        self.assertFalse(r.baseline_same_official_source_tensor_set_proven)
        self.assertFalse(r.historical_header_evidence_closes_materialization_provenance)
        self.assertFalse(r.source_transport_repair_alone_sufficient)
        self.assertTrue(r.cross_domain_provenance_reopen_required)

    def test_successor_evidence_remains_non_collapsible(self) -> None:
        r = current_provenance_frontier()
        self.assertEqual(r.required_successor_evidence, REQUIRED_SUCCESSOR_EVIDENCE)
        self.assertEqual(len(set(r.required_successor_evidence)), 4)
        self.assertIn("OFFICIAL_SOURCE_TENSOR_PAYLOAD_OBSERVATION", r.required_successor_evidence)
        self.assertIn("EXACT_OFFICIAL_TENSOR_TO_CONCRETE_SOURCE_TENSOR_SET_RELATION", r.required_successor_evidence)
        self.assertIn("CANDIDATE_PAGE_MATERIALIZATION_OWNER_RECEIPT", r.required_successor_evidence)
        self.assertIn("BASELINE_SAME_OFFICIAL_SOURCE_TENSOR_SET_RELATION", r.required_successor_evidence)

    def test_current_disposition_is_still_fail_closed(self) -> None:
        r = current_provenance_frontier()
        self.assertEqual(r.disposition, "HOLD_OFFICIAL_SOURCE_TO_CONCRETE_PAGE_PROVENANCE")
        self.assertFalse(r.real_tensor_quantization_eligible)

    def test_no_public_promotion_boolean_input_exists(self) -> None:
        self.assertFalse(public_api_has_promotion_inputs())

    def test_complete_nonpromotion_ceiling(self) -> None:
        r = asdict(current_provenance_frontier())
        for key in (
            "real_tensor_quantization_eligible",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(r[key], key)

    def test_receipt_digest_is_deterministic(self) -> None:
        a = current_provenance_frontier()
        b = current_provenance_frontier()
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(len(a.receipt_digest), 64)
        self.assertEqual(len(a.historical_w2_receipt_digest), 64)


if __name__ == "__main__":
    unittest.main()
