from __future__ import annotations

from dataclasses import replace
import unittest

from tools.quantization.aura_glm53_historical_header_provenance_refinement import (
    CONVERGENCE_COMMIT,
    OFFICIAL_INDEX_SHA256,
    OFFICIAL_REVISION,
    PR398_HEAD,
    PR398_JOB,
    PR398_RECEIPT_DIGEST,
    PR398_RUN,
    Q8_HEAD,
    Q8_RUN,
    REQUIRED_SUCCESSOR_EVIDENCE,
    SELECTED_HEADER_SHA256,
    SELECTED_SHARD,
    current_refinement,
    public_api_has_promotion_inputs,
)


class HistoricalHeaderProvenanceRefinementTests(unittest.TestCase):
    def test_exact_parent_and_observation_identity(self) -> None:
        r = current_refinement()
        self.assertEqual(r.convergence_commit, CONVERGENCE_COMMIT)
        self.assertEqual(r.exact_parent_heads, (Q8_HEAD, PR398_HEAD))
        self.assertEqual(r.exact_parent_runs, (Q8_RUN, PR398_RUN))
        self.assertEqual(r.pr398_job, PR398_JOB)
        self.assertEqual(r.pr398_receipt_digest, PR398_RECEIPT_DIGEST)
        self.assertEqual(r.official_revision, OFFICIAL_REVISION)
        self.assertEqual(r.official_index_sha256, OFFICIAL_INDEX_SHA256)
        self.assertEqual(r.selected_shard, SELECTED_SHARD)
        self.assertEqual(r.selected_header_sha256, SELECTED_HEADER_SHA256)
        self.assertEqual(r.selected_entry_count, 6)

    def test_q8_candidate_binding_survives(self) -> None:
        r = current_refinement()
        self.assertTrue(r.q8_candidate_identity_bound)
        self.assertTrue(r.q8_candidate_sample_bound)
        self.assertTrue(r.q8_independent_verifier_bound)

    def test_historical_header_leaf_is_closed_only_at_representative_scope(self) -> None:
        r = current_refinement()
        self.assertTrue(r.historical_official_index_bytes_verified)
        self.assertTrue(r.historical_official_weight_map_observed)
        self.assertTrue(r.historical_representative_headers_observed)
        self.assertTrue(r.historical_fp8_companions_observed)
        self.assertTrue(r.historical_representative_header_transport_closed)
        self.assertTrue(r.historical_scope_is_representative_only)
        self.assertFalse(r.all_layer_expert_layout_uniformity_proven)

    def test_historical_observation_never_mints_present_byte_residency(self) -> None:
        r = current_refinement()
        self.assertFalse(r.current_process_raw_index_bytes_materialized)
        self.assertFalse(r.current_process_raw_header_prefixes_materialized)
        self.assertFalse(r.broad_official_source_transport_frontier_complete)

    def test_header_closure_never_mints_tensor_or_page_provenance(self) -> None:
        r = current_refinement()
        for key in (
            "official_source_tensor_payload_observed",
            "official_source_byte_domain_bound_to_trial",
            "concrete_page_official_source_authenticated",
            "concrete_page_source_tensor_set_bound_to_official_source",
            "candidate_page_materialization_owner_bound",
            "baseline_same_official_source_tensor_set_proven",
            "source_transport_repair_alone_sufficient",
        ):
            self.assertFalse(getattr(r, key), key)
        self.assertTrue(r.cross_domain_provenance_reopen_required)

    def test_successor_evidence_is_exactly_the_four_q8_cross_domain_leaves(self) -> None:
        r = current_refinement()
        self.assertEqual(r.required_successor_evidence, tuple(REQUIRED_SUCCESSOR_EVIDENCE))
        self.assertEqual(len(r.required_successor_evidence), 4)
        self.assertNotIn("OFFICIAL_REPRESENTATIVE_HEADER_OBSERVATION", r.required_successor_evidence)

    def test_complete_nonpromotion_ceiling(self) -> None:
        r = current_refinement()
        for key in (
            "real_tensor_quantization_eligible",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(getattr(r, key), key)

    def test_receipt_is_deterministic_and_tamper_sensitive(self) -> None:
        a = current_refinement()
        b = current_refinement()
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        tampered = replace(a, selected_header_sha256="0" * 64)
        self.assertNotEqual(a.receipt_digest, tampered.receipt_digest)
        widened = replace(a, official_source_tensor_payload_observed=True)
        self.assertNotEqual(a.receipt_digest, widened.receipt_digest)

    def test_zero_input_public_surface(self) -> None:
        self.assertFalse(public_api_has_promotion_inputs())


if __name__ == "__main__":
    unittest.main()
