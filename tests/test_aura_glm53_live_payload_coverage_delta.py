from __future__ import annotations

from dataclasses import asdict, replace
import inspect
import unittest

from tools.quantization import aura_glm53_live_payload_coverage_delta as q11


class LivePayloadCoverageDeltaTests(unittest.TestCase):
    def test_exact_gate_pair_is_the_only_observed_subset(self) -> None:
        slices = q11.exact_source_slices()
        observed = [x for x in slices if x.observed_live]
        remaining = [x for x in slices if not x.observed_live]
        self.assertEqual(len(observed), 2)
        self.assertEqual({x.projection for x in observed}, {"gate"})
        self.assertEqual(len(remaining), 4)
        self.assertEqual({x.projection for x in remaining}, {"up", "down"})
        self.assertEqual(sum(x.expected_bytes for x in observed), 12_585_984)
        self.assertEqual(sum(x.expected_bytes for x in remaining), 25_171_968)
        self.assertEqual(sum(x.expected_bytes for x in slices), 37_757_952)

    def test_live_hashes_are_bound_only_to_gate_pair(self) -> None:
        by_key = {x.tensor_key: x for x in q11.exact_source_slices()}
        prefix = "model.layers.3.mlp.experts.0."
        self.assertEqual(
            by_key[prefix + "gate_proj.weight"].payload_sha256,
            "2d4e5f36478b598043431b3691ce6a48639e01b6f804b1db62ca4af4d14063e8",
        )
        self.assertEqual(
            by_key[prefix + "gate_proj.weight_scale_inv"].payload_sha256,
            "671dd3b32b3f4cc651b93f3420ae47957ae09c1f745d278c0795d56e5d511c55",
        )
        for suffix in (
            "up_proj.weight",
            "up_proj.weight_scale_inv",
            "down_proj.weight",
            "down_proj.weight_scale_inv",
        ):
            self.assertIsNone(by_key[prefix + suffix].payload_sha256)
            self.assertFalse(by_key[prefix + suffix].observed_live)

    def test_remaining_offsets_are_exact_and_unpromoted(self) -> None:
        by_key = {x.tensor_key: x for x in q11.exact_source_slices()}
        prefix = "model.layers.3.mlp.experts.0."
        expected = {
            prefix + "up_proj.weight": (4_082_790_848, 4_095_373_760),
            prefix + "up_proj.weight_scale_inv": (996_800, 999_872),
            prefix + "down_proj.weight": (4_057_625_024, 4_070_207_936),
            prefix + "down_proj.weight_scale_inv": (990_656, 993_728),
        }
        for key, offsets in expected.items():
            self.assertEqual(by_key[key].relative_offsets, offsets)
            self.assertFalse(by_key[key].observed_live)

    def test_receipt_subtracts_only_proven_slices(self) -> None:
        r = q11.current_live_payload_coverage_delta()
        self.assertEqual(r.observed_slice_count, 2)
        self.assertEqual(r.remaining_slice_count, 4)
        self.assertEqual(r.total_slice_count, 6)
        self.assertEqual(r.observed_payload_bytes, 12_585_984)
        self.assertEqual(r.remaining_payload_bytes, 25_171_968)
        self.assertEqual(r.total_representative_payload_bytes, 37_757_952)
        self.assertEqual(r.observed_payload_bytes + r.remaining_payload_bytes, r.total_representative_payload_bytes)
        self.assertTrue(r.partial_representative_payload_observed)
        self.assertFalse(r.full_representative_expert_payload_observed)
        self.assertTrue(r.remaining_up_pair_observation_required)
        self.assertTrue(r.remaining_down_pair_observation_required)
        self.assertFalse(r.payload_coverage_complete)

    def test_exact_parent_generations_and_live_receipt_are_pinned(self) -> None:
        r = q11.current_live_payload_coverage_delta()
        self.assertEqual(r.convergence_commit, q11.CONVERGENCE_COMMIT)
        self.assertEqual(r.exact_parent_heads, (q11.PR650_HEAD, q11.PR649_HEAD))
        self.assertEqual(r.exact_parent_runs, (q11.PR650_RUN, q11.PR649_RUN))
        self.assertEqual(r.pr650_job, q11.PR650_JOB)
        self.assertEqual(r.pr650_receipt_digest, q11.PR650_RECEIPT_DIGEST)
        self.assertEqual(r.pr649_source_blob, q11.PR649_SOURCE_BLOB)
        self.assertEqual(r.live_header_length_bytes, 105_424)
        self.assertTrue(r.gate_pair_independently_replayed)

    def test_partial_payload_does_not_promote_transformation_or_materialization(self) -> None:
        r = q11.current_live_payload_coverage_delta()
        for value in (
            r.raw_fp8_payload_is_canonical_float32_source_identity,
            r.block_fp8_dequantization_semantics_bound,
            r.gate_up_source_layout_relation_bound,
            r.exact_official_tensor_to_concrete_source_tensor_set_relation,
            r.candidate_page_materialization_owner_bound,
            r.baseline_same_official_source_tensor_set_proven,
        ):
            self.assertFalse(value)
        self.assertEqual(r.disposition, "PARTIAL_LIVE_PAYLOAD_COVERAGE_REMAINING_UP_DOWN")

    def test_no_public_promotion_inputs(self) -> None:
        self.assertFalse(q11.public_api_has_promotion_inputs())
        self.assertEqual(len(inspect.signature(q11.current_live_payload_coverage_delta).parameters), 0)

    def test_unobserved_slice_cannot_be_assigned_a_digest(self) -> None:
        item = next(x for x in q11.exact_source_slices() if x.projection == "up" and not x.observed_live)
        forged = replace(item, payload_sha256="a" * 64)
        with self.assertRaisesRegex(ValueError, "UNOBSERVED_SLICE_CANNOT_HAVE_PAYLOAD_DIGEST"):
            forged.validate()

    def test_observed_slice_requires_digest(self) -> None:
        item = next(x for x in q11.exact_source_slices() if x.observed_live)
        forged = replace(item, payload_sha256=None)
        with self.assertRaisesRegex(ValueError, "OBSERVED_SLICE_DIGEST_REQUIRED"):
            forged.validate()

    def test_complete_nonpromotion_ceiling(self) -> None:
        r = asdict(q11.current_live_payload_coverage_delta())
        for key in (
            "real_tensor_quantization_eligible",
            "model_execution_observed",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(r[key], key)
        self.assertTrue(r["representative_scope_only"])
        self.assertFalse(r["all_layers_experts_uniformity_proven"])

    def test_receipt_is_deterministic(self) -> None:
        a = q11.current_live_payload_coverage_delta()
        b = q11.current_live_payload_coverage_delta()
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(len(a.receipt_digest), 64)


if __name__ == "__main__":
    unittest.main()
