from __future__ import annotations

from dataclasses import replace
import unittest

from tools.quantization import aura_glm53_canonical_expert_source_set_transform_manifest as q


class CanonicalExpertSourceSetTransformManifestTests(unittest.TestCase):
    def test_exact_pr652_six_slice_manifest_is_bound(self) -> None:
        rows = q.source_slices()
        self.assertEqual(6, len(rows))
        actual = {
            (r.projection, r.role): (r.relative_begin, r.relative_end, r.shape, r.dtype)
            for r in rows
        }
        self.assertEqual((4_070_207_936, 4_082_790_848, (2048, 6144), "F8_E4M3"), actual[("gate", "weight")])
        self.assertEqual((993_728, 996_800, (16, 48), "F32"), actual[("gate", "scale")])
        self.assertEqual((4_082_790_848, 4_095_373_760, (2048, 6144), "F8_E4M3"), actual[("up", "weight")])
        self.assertEqual((996_800, 999_872, (16, 48), "F32"), actual[("up", "scale")])
        self.assertEqual((4_057_625_024, 4_070_207_936, (6144, 2048), "F8_E4M3"), actual[("down", "weight")])
        self.assertEqual((990_656, 993_728, (48, 16), "F32"), actual[("down", "scale")])
        self.assertEqual(37_757_952, sum(r.expected_bytes for r in rows))

    def test_transform_profile_is_structurally_bound_for_all_three_projections(self) -> None:
        receipt, projections = q.build_manifest()
        self.assertTrue(receipt.transform_profile_bound)
        self.assertEqual(["gate", "up", "down"], [p.projection for p in projections])
        for p in projections:
            self.assertEqual((128, 128), p.block_shape)
            self.assertEqual(q.FP8_FORMAT, p.fp8_format)
            self.assertEqual(q.CANONICAL_DTYPE, p.canonical_dtype)
            self.assertEqual(q.CANONICAL_ORDER, p.canonical_order)
            self.assertEqual(50_331_648, p.canonical_bytes)

    def test_only_gate_has_earned_canonical_identity(self) -> None:
        receipt, projections = q.build_manifest()
        gate, up, down = projections
        self.assertTrue(gate.raw_payload_observed)
        self.assertTrue(gate.canonical_identity_earned)
        self.assertEqual(q.EARNED_GATE_CANONICAL_SHA256, gate.canonical_sha256)
        self.assertEqual(q.EARNED_GATE_CANONICAL_SHA256, receipt.gate_canonical_sha256)
        for p in (up, down):
            self.assertFalse(p.raw_payload_observed)
            self.assertFalse(p.canonical_identity_earned)
            self.assertIsNone(p.canonical_sha256)
            self.assertEqual("RAW_PAYLOAD_UNOBSERVED_CANONICAL_IDENTITY_HOLD", p.status)

    def test_source_set_byte_sums_do_not_promote_gate_up_layout(self) -> None:
        receipt, _ = q.build_manifest()
        self.assertEqual(100_663_296, receipt.gate_up_independent_source_set_bytes)
        self.assertEqual(150_994_944, receipt.full_independent_projection_source_set_bytes)
        self.assertFalse(receipt.gate_up_concatenation_order_bound)
        self.assertFalse(receipt.gate_up_concatenation_axis_bound)
        self.assertFalse(receipt.gate_up_tensor_layout_bound)
        self.assertFalse(receipt.full_expert_canonical_source_set_materialized)

    def test_bad_range_shape_and_scale_contracts_fail_closed(self) -> None:
        base = q.source_slices()[0]
        with self.assertRaisesRegex(ValueError, "Q13_RANGE_BYTE_COUNT_MISMATCH"):
            replace(base, relative_end=base.relative_end + 1).validate()
        with self.assertRaisesRegex(ValueError, "Q13_WEIGHT_SHAPE_DRIFT"):
            replace(base, shape=(1, q.PROJECTION_ELEMENT_COUNT)).validate()
        scale = q.source_slices()[1]
        with self.assertRaisesRegex(ValueError, "Q13_SCALE_CONTRACT_DRIFT"):
            replace(scale, expected_bytes=4_096, relative_end=scale.relative_begin + 4_096).validate()

    def test_unobserved_projection_cannot_reuse_gate_identity(self) -> None:
        _, projections = q.build_manifest()
        gate, up, down = projections
        self.assertNotEqual(gate.canonical_sha256, up.canonical_sha256)
        self.assertNotEqual(gate.canonical_sha256, down.canonical_sha256)
        forged_up = replace(up, raw_payload_observed=True, canonical_identity_earned=True, canonical_sha256=q.EARNED_GATE_CANONICAL_SHA256)
        self.assertNotEqual(up, forged_up)
        self.assertEqual("RAW_PAYLOAD_UNOBSERVED_CANONICAL_IDENTITY_HOLD", up.status)

    def test_manifest_is_deterministic_and_tamper_sensitive(self) -> None:
        a, _ = q.build_manifest()
        b, _ = q.build_manifest()
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertNotEqual(a.receipt_digest, replace(a, disposition="FORGED").receipt_digest)

    def test_public_boundary_and_claim_ceiling(self) -> None:
        receipt, _ = q.build_manifest()
        self.assertFalse(q.public_api_has_promotion_inputs())
        self.assertEqual(
            "GATE_CANONICALIZED__UP_DOWN_RAW_UNOBSERVED__GATE_UP_LAYOUT_UNBOUND",
            receipt.disposition,
        )
        for field in (
            "up_payload_observed",
            "down_payload_observed",
            "up_canonical_identity_earned",
            "down_canonical_identity_earned",
            "full_expert_canonical_source_set_materialized",
            "source_to_e8_page_materialization_bound",
            "real_e8_page_materialized",
            "model_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(getattr(receipt, field), field)


if __name__ == "__main__":
    unittest.main()
