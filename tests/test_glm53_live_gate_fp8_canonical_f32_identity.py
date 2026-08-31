import math
import struct
import unittest

import numpy as np

from tools.quantization import aura_glm53_live_gate_fp8_canonical_f32_identity as q12


class LiveGateFP8CanonicalF32IdentityTests(unittest.TestCase):
    def test_e4m3fn_exact_known_codes(self):
        cases = {
            0x00: 0.0,
            0x01: 2.0 ** -9,
            0x07: 7.0 * 2.0 ** -9,
            0x08: 2.0 ** -6,
            0x38: 1.0,
            0x3C: 1.5,
            0x7E: 448.0,
            0xB8: -1.0,
            0xFE: -448.0,
        }
        for code, expected in cases.items():
            self.assertEqual(q12.decode_e4m3fn_byte(code), expected, hex(code))
        neg_zero = q12.decode_e4m3fn_byte(0x80)
        self.assertEqual(neg_zero, 0.0)
        self.assertLess(math.copysign(1.0, neg_zero), 0.0)

    def test_outer_nan_codes_and_invalid_inputs_fail_closed(self):
        for code in (0x7F, 0xFF):
            with self.assertRaisesRegex(q12.GateDequantizationError, "NaN"):
                q12.decode_e4m3fn_byte(code)
        for value in (-1, 256, True, 1.5, "56"):
            with self.assertRaisesRegex(q12.GateDequantizationError, "invalid"):
                q12.decode_e4m3fn_byte(value)  # type: ignore[arg-type]

    def test_lookup_table_matches_scalar_oracle_except_nan_codes(self):
        table = q12.e4m3fn_lookup_table()
        self.assertEqual(table.dtype, np.dtype("<f4"))
        self.assertEqual(table.shape, (256,))
        for code in range(256):
            if code in (0x7F, 0xFF):
                self.assertTrue(np.isnan(table[code]))
            else:
                self.assertEqual(float(table[code]), q12.decode_e4m3fn_byte(code))

    def test_blockwise_dequantization_orientation_and_canonical_bytes(self):
        # Four independently scaled 128x128 blocks. Using different quantized
        # values per quadrant catches row/column block-grid transposition.
        codes = np.empty((256, 256), dtype=np.uint8)
        codes[:128, :128] = 0x38  # 1.0
        codes[:128, 128:] = 0x40  # 2.0
        codes[128:, :128] = 0x30  # 0.5
        codes[128:, 128:] = 0xB8  # -1.0
        scales = np.array([[0.25, 0.5], [2.0, 4.0]], dtype="<f4")

        raw = q12.dequantize_blockwise_to_canonical_f32(
            codes.tobytes(order="C"),
            scales.tobytes(order="C"),
            weight_shape=(256, 256),
            scale_shape=(2, 2),
        )
        out = np.frombuffer(raw, dtype="<f4").reshape(256, 256)
        self.assertEqual(len(raw), 256 * 256 * 4)
        self.assertTrue(np.all(out[:128, :128] == np.float32(0.25)))
        self.assertTrue(np.all(out[:128, 128:] == np.float32(1.0)))
        self.assertTrue(np.all(out[128:, :128] == np.float32(1.0)))
        self.assertTrue(np.all(out[128:, 128:] == np.float32(-4.0)))
        # Canonical bytes are explicitly little-endian float32 C-order.
        self.assertEqual(raw[:4], struct.pack("<f", 0.25))

    def test_non_128_block_geometry_fails_closed(self):
        codes = bytes([0x38]) * (128 * 128)
        scale = struct.pack("<f", 1.0)
        with self.assertRaisesRegex(q12.GateDequantizationError, "block geometry"):
            q12.dequantize_blockwise_to_canonical_f32(
                codes,
                scale,
                weight_shape=(128, 128),
                scale_shape=(1, 2),
            )

    def test_payload_length_nan_code_and_bad_scale_fail_closed(self):
        good_codes = bytearray([0x38]) * (128 * 128)
        good_scale = struct.pack("<f", 1.0)
        with self.assertRaisesRegex(q12.GateDequantizationError, "weight payload length"):
            q12.dequantize_blockwise_to_canonical_f32(
                bytes(good_codes[:-1]), good_scale, weight_shape=(128, 128), scale_shape=(1, 1)
            )
        good_codes[5] = 0x7F
        with self.assertRaisesRegex(q12.GateDequantizationError, "NaN"):
            q12.dequantize_blockwise_to_canonical_f32(
                bytes(good_codes), good_scale, weight_shape=(128, 128), scale_shape=(1, 1)
            )
        clean_codes = bytes([0x38]) * (128 * 128)
        for bad_scale in (0.0, -1.0, float("nan"), float("inf")):
            with self.assertRaisesRegex(q12.GateDequantizationError, "positive finite"):
                q12.dequantize_blockwise_to_canonical_f32(
                    clean_codes,
                    struct.pack("<f", bad_scale),
                    weight_shape=(128, 128),
                    scale_shape=(1, 1),
                )

    def test_exact_parent_and_byte_domain_constants(self):
        self.assertEqual(q12.PR650_HEAD, "e8e0eecb5fce9f95bf1b71e97b528776ecd8b51c")
        self.assertEqual(q12.PR641_HEAD, "a8d4605a36e04d64cf03f43f457be4bde553e602")
        self.assertEqual(q12.PR641_SOURCE_BLOB, "157afcb2e457c630d03a8c72aef09f0a6ba04a4d")
        self.assertEqual(q12.PR628_SOURCE_BLOB, "5df2cd69a1519b2626cb52c1d8f23a25504425d9")
        self.assertEqual(q12.EXPECTED_WEIGHT_BYTES, 12_582_912)
        self.assertEqual(q12.EXPECTED_SCALE_BYTES, 3_072)
        self.assertEqual(q12.EXPECTED_CANONICAL_F32_BYTES, 50_331_648)
        self.assertEqual(q12.BLOCK_SHAPE, (128, 128))
        self.assertEqual(len(q12.EXPECTED_WEIGHT_SHA256), 64)
        self.assertEqual(len(q12.EXPECTED_SCALE_SHA256), 64)

    def test_receipt_ceiling_cannot_be_laundered_by_canonical_hash(self):
        fields = q12.LiveGateCanonicalF32IdentityReceipt.__dataclass_fields__
        for name in (
            "up_payload_observed",
            "down_payload_observed",
            "full_expert_payload_observed",
            "gate_up_composition_bound",
            "official_tensor_to_pr641_page_set_relation_proven",
            "candidate_page_materialization_owner_bound",
            "baseline_same_official_source_tensor_set_proven",
            "real_e8_page_materialized",
            "model_execution_observed",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertIn(name, fields)


if __name__ == "__main__":
    unittest.main()
