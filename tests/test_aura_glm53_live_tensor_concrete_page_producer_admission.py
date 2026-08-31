from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from tools.quantization import aura_glm53_historical_official_w2_bridge as historical
from tools.quantization import aura_glm53_live_tensor_concrete_page_producer_admission as q9
from tools.quantization import aura_glm53_official_source_concrete_page_provenance_join as provenance


class LiveTensorConcretePageProducerAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current = provenance.current_provenance_frontier()
        self.past = historical.build_historical_official_w2_bridge(
            historical.canonical_pr398_observation()
        )

    def test_current_state_is_fail_closed_and_deterministic(self) -> None:
        first = q9.current_live_producer_admission()
        second = q9.current_live_producer_admission()
        self.assertEqual(first, second)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertEqual(first.schema, "AURA_GLM53_LIVE_TENSOR_CONCRETE_PAGE_PRODUCER_ADMISSION_V2")
        self.assertEqual(
            first.disposition,
            "HOLD_LIVE_OFFICIAL_TENSOR_TO_CONCRETE_PAGE_PRODUCER",
        )
        self.assertTrue(first.historical_representative_header_schema_qualified)
        self.assertTrue(first.historical_representative_header_provenance_bound)
        self.assertTrue(first.historical_fp8_companion_geometry_bound)
        self.assertTrue(first.historical_evidence_revision_matches_pinned_frontier_revision)
        self.assertFalse(first.ambient_repository_head_observed_by_q9_process)
        self.assertTrue(first.historical_evidence_reduces_header_schema_uncertainty)
        self.assertTrue(first.current_concrete_page_frontier_bound)
        self.assertFalse(first.historical_header_evidence_sufficient_for_live_producer)
        self.assertFalse(first.live_official_tensor_payload_observed)
        self.assertFalse(first.exact_live_official_tensor_to_concrete_source_tensor_set_relation)
        self.assertFalse(first.candidate_page_materialization_owner_bound)
        self.assertFalse(first.baseline_same_live_official_source_tensor_set_proven)
        self.assertFalse(first.live_tensor_to_concrete_page_producer_admissible)
        self.assertTrue(first.currentness_revalidation_required_at_use)
        self.assertTrue(first.representative_scope_only)
        self.assertFalse(first.all_layers_experts_uniformity_proven)
        self.assertEqual(first.required_live_evidence, q9.REQUIRED_LIVE_EVIDENCE)
        for field in (
            "real_tensor_quantization_eligible",
            "model_execution_eligible",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(getattr(first, field), field)

    def test_public_api_has_no_promotion_inputs(self) -> None:
        self.assertFalse(q9.public_api_has_promotion_inputs())
        self.assertEqual(
            len(inspect.signature(q9.current_live_producer_admission).parameters),
            0,
        )

    def test_historical_header_cannot_self_mint_payload(self) -> None:
        promoted = replace(self.past, source_tensor_payload_bound=True)
        with self.assertRaisesRegex(
            ValueError, "Q9_PR646_HISTORICAL_HEADER_EVIDENCE_PROMOTED_TO_PAYLOAD"
        ):
            q9._join_exact_parents(self.current, promoted)

    def test_historical_observation_cannot_self_mint_current_byte_residency(self) -> None:
        promoted = replace(self.past, current_consumer_raw_index_bytes_materialized=True)
        with self.assertRaisesRegex(
            ValueError, "Q9_PR646_HISTORICAL_EVIDENCE_PROMOTED_TO_CURRENT_INDEX_BYTES"
        ):
            q9._join_exact_parents(self.current, promoted)

        promoted = replace(self.past, current_consumer_raw_header_prefixes_materialized=True)
        with self.assertRaisesRegex(
            ValueError, "Q9_PR646_HISTORICAL_EVIDENCE_PROMOTED_TO_CURRENT_HEADER_BYTES"
        ):
            q9._join_exact_parents(self.current, promoted)

    def test_representative_headers_cannot_promote_to_global_layout(self) -> None:
        promoted = replace(self.past, all_layers_experts_uniformity_proven=True)
        with self.assertRaisesRegex(
            ValueError, "Q9_PR646_REPRESENTATIVE_SCOPE_PROMOTED_TO_GLOBAL"
        ):
            q9._join_exact_parents(self.current, promoted)

    def test_current_frontier_cannot_be_toggled_into_live_producer(self) -> None:
        cases = (
            (
                replace(self.current, official_source_tensor_payload_observed=True),
                "Q9_PR645_PARENT_UNEXPECTEDLY_HAS_TENSOR_PAYLOAD",
            ),
            (
                replace(
                    self.current,
                    concrete_page_source_tensor_set_bound_to_official_source=True,
                ),
                "Q9_PR645_PARENT_UNEXPECTEDLY_HAS_SOURCE_TO_PAGE_RELATION",
            ),
            (
                replace(self.current, candidate_page_materialization_owner_bound=True),
                "Q9_PR645_PARENT_UNEXPECTEDLY_HAS_MATERIALIZATION_OWNER",
            ),
            (
                replace(self.current, baseline_same_official_source_tensor_set_proven=True),
                "Q9_PR645_PARENT_UNEXPECTEDLY_HAS_BASELINE_SOURCE_EQUIVALENCE",
            ),
        )
        for altered, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    q9._join_exact_parents(altered, self.past)

    def test_source_revision_and_repository_must_match(self) -> None:
        wrong_repo = replace(self.past, official_repository="example.invalid/GLM-5.3")
        with self.assertRaisesRegex(ValueError, "Q9_OFFICIAL_REPOSITORY_MISMATCH"):
            q9._join_exact_parents(self.current, wrong_repo)

        wrong_revision = replace(self.past, official_revision="0" * 40)
        with self.assertRaisesRegex(ValueError, "Q9_OFFICIAL_REVISION_MISMATCH"):
            q9._join_exact_parents(self.current, wrong_revision)


if __name__ == "__main__":
    unittest.main()
