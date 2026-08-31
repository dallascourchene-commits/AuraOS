from __future__ import annotations

import hashlib
import struct
from types import SimpleNamespace
import unittest

import numpy as np

from tools.quantization import aura_glm53_full_representative_canonical_source_set as q13
from tools.quantization import aura_glm53_official_source_e8_materialization_canary as q14


class Q14MaterializationCanaryTests(unittest.TestCase):
    def fake_q13(self, *, authenticated: bool = True, bound: bool = True):
        return SimpleNamespace(
            full_representative_canonical_source_set_bound=bound,
            representative_official_source_tensor_set_authenticated=authenticated,
            source_set_schema=q13.SOURCE_SET_SCHEMA,
            actual_e8_page_payload_materialized=False,
            source_tensor_set_digest="ab" * 32,
            source_set_entries=(
                {
                    "layer_id": 3,
                    "expert_id": 0,
                    "tensor_role": "down_proj",
                    "source_tensor_sha256": "11" * 32,
                    "source_shape": [6144, 2048],
                },
                {
                    "layer_id": 3,
                    "expert_id": 0,
                    "tensor_role": "gate_up_proj",
                    "source_tensor_sha256": "22" * 32,
                    "source_shape": [4096, 6144],
                },
            ),
        )

    def test_first_block_decode_matches_q13_transform_prefix(self):
        # One full 128x128 source block with scale 1.25. Q14's bounded decode
        # must equal the first 64 canonical values of Q13's exact transform.
        codes = np.arange(128 * 128, dtype=np.uint8)
        codes[(codes == 0x7F) | (codes == 0xFF)] = 0
        scales = np.asarray([[1.25]], dtype="<f4")
        full = q13.dequantize_pair(codes.tobytes(), scales.tobytes(), (128, 128), (1, 1))
        expected = np.frombuffer(full, dtype="<f4")[:64]
        actual = q14.canonical_first_block(codes.tobytes()[:64], scales.tobytes()).reshape(-1)
        np.testing.assert_array_equal(actual, expected)

    def test_two_role_canary_uses_exact_existing_page_owner(self):
        receipt = self.fake_q13()
        scale = struct.pack("<f", 1.0)
        gate_codes = bytes([0x38] * 64)  # +1.0 E4M3FN
        down_codes = bytes([0xB8] * 64)  # -1.0 E4M3FN
        gate = q14.materialize_role_canary(
            q13_receipt=receipt,
            role="gate_up_proj",
            weight_raw=gate_codes,
            scale_raw=scale,
            source_component="gate_prefix",
        )
        down = q14.materialize_role_canary(
            q13_receipt=receipt,
            role="down_proj",
            weight_raw=down_codes,
            scale_raw=scale,
            source_component="down_prefix",
        )
        self.assertEqual(gate.full_role_source_sha256, "22" * 32)
        self.assertEqual(down.full_role_source_sha256, "11" * 32)
        self.assertTrue(gate.actual_e8_page_payload_materialized)
        self.assertTrue(down.official_source_to_e8_page_derivation_proven_for_tile)
        self.assertTrue(gate.page_materialization_owner_bound_for_tile)
        self.assertEqual(gate.canonical_tile_shape, (1, 64))
        self.assertEqual(gate.page_source_identity_matches_canonical_tile, True)
        expected_tile = np.asarray([1.0] * 64, dtype="<f4").tobytes()
        self.assertEqual(gate.canonical_tile_sha256, hashlib.sha256(expected_tile).hexdigest())
        self.assertNotEqual(gate.page_payload_sha256, gate.canonical_tile_sha256)

    def test_wrong_component_is_rejected(self):
        with self.assertRaisesRegex(q14.MaterializationCanaryError, "ROLE_COMPONENT_MISMATCH"):
            q14.materialize_role_canary(
                q13_receipt=self.fake_q13(),
                role="down_proj",
                weight_raw=bytes(64),
                scale_raw=struct.pack("<f", 1.0),
                source_component="gate_prefix",
            )

    def test_unbound_or_unauthenticated_q13_is_rejected(self):
        for receipt in (self.fake_q13(bound=False), self.fake_q13(authenticated=False)):
            with self.assertRaises(q14.MaterializationCanaryError):
                q14.materialize_role_canary(
                    q13_receipt=receipt,
                    role="gate_up_proj",
                    weight_raw=bytes(64),
                    scale_raw=struct.pack("<f", 1.0),
                    source_component="gate_prefix",
                )

    def test_nan_code_and_nonpositive_scale_fail_closed(self):
        with self.assertRaisesRegex(q14.MaterializationCanaryError, "E4M3FN_NAN_IN_TILE"):
            q14.canonical_first_block(bytes([0x7F]) + bytes(63), struct.pack("<f", 1.0))
        with self.assertRaisesRegex(q14.MaterializationCanaryError, "INVALID_TILE_SCALE"):
            q14.canonical_first_block(bytes(64), struct.pack("<f", 0.0))

    def test_reference_scaling_boundary_is_exact(self):
        self.assertEqual(q14.FULL_ROLE_WEIGHTS, 37_748_736)
        self.assertEqual(q14.FULL_ROLE_VECTOR_COUNT, 4_718_592)
        self.assertEqual(q14.REFERENCE_CODEBOOK_SIZE, 58_112)
        self.assertEqual(q14.NAIVE_FULL_ROLE_CODEWORD_SCORES, 274_206_818_304)
        self.assertEqual(q14.TILE_WEIGHTS * 2, 128)

    def test_provider_and_authority_ceiling_fields_are_explicit(self):
        fields = q14.OfficialSourceE8MaterializationCanaryReceipt.__dataclass_fields__
        for name in (
            "provider_gate_counts_as_materialization_failure",
            "provider_gate_counts_as_materialization_success",
            "full_role_page_payloads_materialized",
            "full_source_set_page_set_materialized",
            "model_execution_observed",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertIn(name, fields)


if __name__ == "__main__":
    unittest.main()
