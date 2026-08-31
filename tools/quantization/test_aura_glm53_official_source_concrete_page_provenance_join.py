from __future__ import annotations

from dataclasses import asdict
import unittest

from tools.quantization.aura_glm53_official_source_concrete_page_provenance_join import (
    CONCRETE_TRIAL_HEAD,
    CONCRETE_TRIAL_RUN,
    CONCRETE_TRIAL_SOURCE_BLOB,
    CONVERGENCE_COMMIT,
    OFFICIAL_BRIDGE_HEAD,
    OFFICIAL_BRIDGE_RUN,
    OFFICIAL_BRIDGE_SOURCE_BLOB,
    REQUIRED_SUCCESSOR_EVIDENCE,
    current_provenance_frontier,
    public_api_has_promotion_inputs,
)


class OfficialSourceConcretePageProvenanceJoinTests(unittest.TestCase):
    def test_exact_parent_generation_is_pinned(self) -> None:
        r = current_provenance_frontier()
        self.assertEqual(r.convergence_commit, CONVERGENCE_COMMIT)
        self.assertEqual(r.exact_parent_heads, (OFFICIAL_BRIDGE_HEAD, CONCRETE_TRIAL_HEAD))
        self.assertEqual(r.exact_parent_runs, (OFFICIAL_BRIDGE_RUN, CONCRETE_TRIAL_RUN))
        self.assertEqual(r.exact_parent_source_blobs, (OFFICIAL_BRIDGE_SOURCE_BLOB, CONCRETE_TRIAL_SOURCE_BLOB))

    def test_current_frontier_preserves_concrete_candidate_evidence(self) -> None:
        r = current_provenance_frontier()
        self.assertTrue(r.concrete_candidate_identity_bound)
        self.assertTrue(r.concrete_candidate_sample_bound)
        self.assertTrue(r.concrete_independent_verifier_bound)

    def test_source_transport_and_cross_domain_provenance_are_independent_holds(self) -> None:
        r = current_provenance_frontier()
        self.assertFalse(r.official_source_transport_frontier_complete)
        self.assertFalse(r.official_source_tensor_payload_observed)
        self.assertFalse(r.official_source_byte_domain_bound_to_trial)
        self.assertFalse(r.concrete_page_source_tensor_set_bound_to_official_source)
        self.assertFalse(r.candidate_page_materialization_owner_bound)
        self.assertFalse(r.source_transport_repair_alone_sufficient)
        self.assertTrue(r.cross_domain_provenance_reopen_required)

    def test_successor_evidence_is_explicit_and_non_collapsible(self) -> None:
        r = current_provenance_frontier()
        self.assertEqual(r.required_successor_evidence, REQUIRED_SUCCESSOR_EVIDENCE)
        self.assertEqual(len(set(r.required_successor_evidence)), 4)
        self.assertIn("EXACT_OFFICIAL_TENSOR_TO_CONCRETE_SOURCE_TENSOR_SET_RELATION", r.required_successor_evidence)
        self.assertIn("CANDIDATE_PAGE_MATERIALIZATION_OWNER_RECEIPT", r.required_successor_evidence)

    def test_current_disposition_is_fail_closed(self) -> None:
        r = current_provenance_frontier()
        self.assertEqual(r.disposition, "HOLD_OFFICIAL_SOURCE_TO_CONCRETE_PAGE_PROVENANCE")
        self.assertFalse(r.concrete_page_official_source_authenticated)
        self.assertFalse(r.baseline_same_official_source_tensor_set_proven)

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
        self.assertEqual(current_provenance_frontier().receipt_digest, current_provenance_frontier().receipt_digest)
        self.assertEqual(len(current_provenance_frontier().receipt_digest), 64)


if __name__ == "__main__":
    unittest.main()
