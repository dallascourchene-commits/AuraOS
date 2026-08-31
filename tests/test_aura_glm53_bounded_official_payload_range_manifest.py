from __future__ import annotations

from dataclasses import asdict
import inspect
import unittest

from tools.quantization import aura_glm53_bounded_official_payload_range_manifest as q10


class BoundedOfficialPayloadRangeManifestTests(unittest.TestCase):
    def test_exact_six_historical_slices_and_total_bytes(self) -> None:
        slices = q10.current_payload_slices()
        self.assertEqual(len(slices), 6)
        self.assertEqual(sum(s.expected_bytes for s in slices), 37_757_952)
        self.assertEqual({s.shard for s in slices}, {q10.SHARD})
        self.assertEqual({s.header_sha256 for s in slices}, {q10.HISTORICAL_HEADER_SHA256})

    def test_each_slice_byte_count_matches_shape_dtype_and_offsets(self) -> None:
        dtype_bytes = {"F8_E4M3": 1, "F32": 4}
        for s in q10.current_payload_slices():
            count = 1
            for dim in s.shape:
                count *= dim
            self.assertEqual(s.expected_bytes, count * dtype_bytes[s.dtype])
            self.assertEqual(s.expected_bytes, s.relative_end - s.relative_begin)

    def test_exact_historical_relative_offsets_are_retained(self) -> None:
        by_key = {s.tensor_key: s for s in q10.current_payload_slices()}
        prefix = "model.layers.3.mlp.experts.0."
        expected = {
            prefix + "gate_proj.weight": (4070207936, 4082790848),
            prefix + "gate_proj.weight_scale_inv": (993728, 996800),
            prefix + "up_proj.weight": (4082790848, 4095373760),
            prefix + "up_proj.weight_scale_inv": (996800, 999872),
            prefix + "down_proj.weight": (4057625024, 4070207936),
            prefix + "down_proj.weight_scale_inv": (990656, 993728),
        }
        self.assertEqual(set(by_key), set(expected))
        for key, offsets in expected.items():
            self.assertEqual((by_key[key].relative_begin, by_key[key].relative_end), offsets)

    def test_absolute_range_uses_current_header_length_not_historical_guess(self) -> None:
        first = q10.current_payload_slices()[0]
        start, end = first.absolute_range(1000)
        self.assertEqual(start, 1008 + first.relative_begin)
        self.assertEqual(end, 1008 + first.relative_end)
        with self.assertRaisesRegex(ValueError, "CURRENT_HEADER_LENGTH_INVALID"):
            first.absolute_range(1)

    def test_target_role_grouping_is_explicit_but_transform_is_unowned(self) -> None:
        slices = q10.current_payload_slices()
        self.assertEqual(sum(s.target_role == "gate_up_proj" for s in slices), 4)
        self.assertEqual(sum(s.target_role == "down_proj" for s in slices), 2)
        r = q10.current_bounded_payload_range_manifest()
        self.assertTrue(r.target_role_names_bound)
        self.assertFalse(r.source_to_target_layout_relation_bound)
        self.assertFalse(r.block_fp8_dequantization_semantics_bound)

    def test_manifest_is_plan_ready_but_no_live_effect_is_claimed(self) -> None:
        r = q10.current_bounded_payload_range_manifest()
        self.assertEqual(r.disposition, "PLAN_READY_LIVE_EFFECT_NOT_EXECUTED")
        self.assertTrue(r.historical_relative_offsets_bound)
        self.assertTrue(r.absolute_ranges_require_current_header_length)
        self.assertTrue(r.current_header_revalidation_required)
        self.assertTrue(r.payload_fetch_plan_complete_for_representative_expert)
        self.assertEqual(r.slice_count, 6)
        self.assertEqual(r.total_payload_bytes, 37_757_952)
        self.assertFalse(r.live_payload_observation_executed)
        self.assertFalse(r.live_payload_digests_bound)
        self.assertFalse(r.exact_live_official_tensor_to_concrete_source_tensor_set_relation)
        self.assertFalse(r.candidate_page_materialization_owner_bound)
        self.assertFalse(r.baseline_same_live_official_source_tensor_set_proven)

    def test_exact_parent_and_page_owner_generations_are_pinned(self) -> None:
        r = q10.current_bounded_payload_range_manifest()
        self.assertEqual(r.convergence_commit, q10.CONVERGENCE_COMMIT)
        self.assertEqual(r.exact_parent_heads, (q10.PR649_HEAD, q10.PR641_HEAD))
        self.assertEqual(r.exact_parent_runs, (q10.PR649_RUN, q10.PR641_RUN))
        self.assertEqual(r.pr641_binding_blob, q10.PR641_BINDING_BLOB)
        self.assertEqual(r.pr628_page_blob, q10.PR628_PAGE_BLOB)

    def test_public_current_api_is_zero_input(self) -> None:
        self.assertFalse(q10.public_api_has_promotion_inputs())
        self.assertEqual(len(inspect.signature(q10.current_bounded_payload_range_manifest).parameters), 0)

    def test_complete_nonpromotion_ceiling(self) -> None:
        r = asdict(q10.current_bounded_payload_range_manifest())
        for key in (
            "real_tensor_quantization_eligible",
            "model_execution_eligible",
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
        a = q10.current_bounded_payload_range_manifest()
        b = q10.current_bounded_payload_range_manifest()
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(len(a.receipt_digest), 64)


if __name__ == "__main__":
    unittest.main()
