from __future__ import annotations

import unittest

from tools.quantization.aura_glm53_packed_expert_quantization_plan import (
    BANK_ONLY_UNBOUNDED,
    BANK_RESIDENT_BOUNDED,
    PER_EXPERT_SLICEABLE,
    IndexedQuantizedRepresentation,
    PackedExpertQuantizationRequest,
    build_packed_expert_quantization_plan,
)


def rep_2p5(layout=PER_EXPERT_SLICEABLE, *, companion=4096, bank=0):
    return IndexedQuantizedRepresentation(
        representation_id="E8_2P5",
        vector_dim=8,
        index_bits_per_vector=18,
        scale_group_weights=64,
        scale_bits_per_group=16,
        companion_layout=layout,
        companion_bytes_per_expert=companion,
        bank_resident_companion_bytes=bank,
    )


def rep_3p0():
    return IndexedQuantizedRepresentation(
        representation_id="E8_3P0",
        vector_dim=8,
        index_bits_per_vector=22,
        scale_group_weights=64,
        scale_bits_per_group=16,
        companion_layout=PER_EXPERT_SLICEABLE,
        companion_bytes_per_expert=4096,
    )


def request(assignments, selected=(3, 4, 9, 17, 18, 19, 31, 200), budget=8_000_000, cap=1_000_000):
    return PackedExpertQuantizationRequest(
        num_experts=len(assignments),
        parameters_per_expert=1_000_000,
        expert_representation_ids=tuple(assignments),
        selected_expert_ids=tuple(selected),
        cache_budget_bytes=budget,
        bank_resident_companion_cap_bytes=cap,
        lifecycle_mode="BACKGROUND",
    )


class PackedExpertQuantizationPlanTests(unittest.TestCase):
    def test_mixed_precision_plan_has_exact_selected_runs_and_byte_accounting(self):
        assignments = ["E8_2P5"] * 256
        assignments[31] = "E8_3P0"
        plan = build_packed_expert_quantization_plan(
            request=request(assignments),
            representations={"E8_2P5": rep_2p5(), "E8_3P0": rep_3p0()},
        )
        self.assertEqual(plan.selected_contiguous_runs, ((3, 5), (9, 10), (17, 20), (31, 32), (200, 201)))
        # 2.5 bpw = 312,500 payload bytes/expert, plus 4,096 companion bytes.
        # Expert 31 uses 3.0 bpw = 375,000 + 4,096.
        expected = 7 * (312_500 + 4_096) + (375_000 + 4_096)
        self.assertEqual(plan.selected_expert_working_set_bytes, expected)
        self.assertTrue(plan.working_set_fits_cache_budget)
        self.assertGreater(plan.static_compression_ratio_vs_fp8, 2.0)

    def test_selected_working_set_is_not_full_static_model(self):
        assignments = ["E8_2P5"] * 256
        plan = build_packed_expert_quantization_plan(
            request=request(assignments), representations={"E8_2P5": rep_2p5()}
        )
        self.assertLess(plan.selected_expert_working_set_bytes, plan.full_routed_expert_static_bytes)
        self.assertEqual(plan.fp8_reference_static_bytes, 256_000_000)

    def test_unsliceable_bank_companion_fails_closed(self):
        bad = rep_2p5(BANK_ONLY_UNBOUNDED, companion=0)
        assignments = ["E8_2P5"] * 16
        with self.assertRaisesRegex(ValueError, "UNSLICEABLE_COMPANION_LAYOUT"):
            build_packed_expert_quantization_plan(request=request(assignments, selected=(1, 2)), representations={"E8_2P5": bad})

    def test_bounded_bank_companion_is_explicit_one_time_working_set_cost(self):
        bank = rep_2p5(BANK_RESIDENT_BOUNDED, companion=0, bank=200_000)
        assignments = ["E8_2P5"] * 16
        plan = build_packed_expert_quantization_plan(
            request=request(assignments, selected=(1, 2), cap=250_000), representations={"E8_2P5": bank}
        )
        self.assertTrue(plan.bank_companion_loaded_as_bounded_exception)
        self.assertEqual(plan.selected_expert_working_set_bytes, 2 * 312_500 + 200_000)
        self.assertEqual(plan.full_routed_expert_static_bytes, 16 * 312_500 + 200_000)

    def test_bank_companion_over_cap_rejects(self):
        bank = rep_2p5(BANK_RESIDENT_BOUNDED, companion=0, bank=300_000)
        assignments = ["E8_2P5"] * 16
        with self.assertRaisesRegex(ValueError, "BANK_COMPANION_CAP_EXCEEDED"):
            build_packed_expert_quantization_plan(
                request=request(assignments, selected=(1, 2), cap=250_000), representations={"E8_2P5": bank}
            )

    def test_unindexed_lattice_coordinate_representation_is_not_admitted(self):
        unindexed = IndexedQuantizedRepresentation(
            representation_id="RAW_E8_COORDINATES",
            vector_dim=8,
            index_bits_per_vector=64,
            scale_group_weights=64,
            scale_bits_per_group=16,
            companion_layout=PER_EXPERT_SLICEABLE,
            indexed_bitstring_mapping_proven=False,
        )
        assignments = ["RAW_E8_COORDINATES"] * 16
        with self.assertRaisesRegex(ValueError, "INDEXED_BITSTRING_MAPPING_REQUIRED"):
            build_packed_expert_quantization_plan(request=request(assignments, selected=(1, 2)), representations={"RAW_E8_COORDINATES": unindexed})

    def test_duplicate_router_ids_are_deduped_without_widening_runs(self):
        assignments = ["E8_2P5"] * 16
        plan = build_packed_expert_quantization_plan(
            request=request(assignments, selected=(2, 2, 3, 7, 7)), representations={"E8_2P5": rep_2p5()}
        )
        self.assertEqual(plan.selected_expert_ids, (2, 3, 7))
        self.assertEqual(plan.selected_contiguous_runs, ((2, 4), (7, 8)))

    def test_budget_fit_is_descriptive_not_performance_or_authority(self):
        assignments = ["E8_2P5"] * 16
        plan = build_packed_expert_quantization_plan(
            request=request(assignments, selected=(1, 2), budget=1_000_000), representations={"E8_2P5": rep_2p5()}
        )
        self.assertTrue(plan.working_set_fits_cache_budget)
        self.assertFalse(plan.expert_quality_preserved_proven)
        self.assertFalse(plan.selected_expert_router_frequency_measured)
        self.assertFalse(plan.kv_cache_compression_proven)
        self.assertFalse(plan.physical_io_observed)
        self.assertFalse(plan.planned_backend_executed)
        self.assertFalse(plan.model_execution_performed)
        self.assertFalse(plan.lifecycle_mode_performance_safe_proven)
        self.assertFalse(plan.native_private_transformer_kv_accessed)
        self.assertFalse(plan.semantic_k27_authority_minted)
        self.assertFalse(plan.deployment_authorized)
        self.assertEqual(len(plan.plan_digest), 64)


if __name__ == "__main__":
    unittest.main()
