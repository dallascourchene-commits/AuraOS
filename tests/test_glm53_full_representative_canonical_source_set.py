import hashlib
import json
import struct
import unittest

import numpy as np

from tools.quantization import aura_glm53_full_representative_canonical_source_set as q13


class FullRepresentativeCanonicalSourceSetTests(unittest.TestCase):
    def test_exact_nonself_parent_generations_and_raw_receipt(self):
        self.assertEqual(q13.PR656_SEMANTIC_HEAD, "ac3247ed75aa8646490db8d953b16aecd5ebec2d")
        self.assertEqual(q13.PR656_RUN, 33395608248)
        self.assertEqual(q13.PR656_JOB, 99499276445)
        self.assertEqual(q13.PR656_SOURCE_BLOB, "87e581cbe5a25c538a34eb3475bdd13bb52bd158")
        self.assertEqual(q13.PR656_RECEIPT_DIGEST, "f3bbd2f6654d0cc254ff2bc5a14e9dff3b59cdca83ccf86729e9f5ad270a1943")
        self.assertEqual(q13.PR641_HEAD, "a8d4605a36e04d64cf03f43f457be4bde553e602")
        self.assertEqual(q13.PR641_SOURCE_BLOB, "157afcb2e457c630d03a8c72aef09f0a6ba04a4d")

    def test_all_six_slice_generation_is_exact(self):
        self.assertEqual(len(q13.SLICES), 6)
        self.assertEqual(sum(int(x["bytes"]) for x in q13.SLICES.values()), 37_757_952)
        for spec in q13.SLICES.values():
            self.assertEqual(spec["offset"][1] - spec["offset"][0], spec["bytes"])
            self.assertEqual(len(spec["sha256"]), 64)
        self.assertEqual(q13.SLICES["down_scale"]["shape"], (48, 16))
        self.assertEqual(q13.SLICES["gate_scale"]["shape"], (16, 48))
        self.assertEqual(q13.SLICES["up_scale"]["shape"], (16, 48))

    def test_dequantization_orientation_128_square_blocks(self):
        codes = np.empty((256, 256), dtype=np.uint8)
        codes[:128, :128] = 0x38
        codes[:128, 128:] = 0x40
        codes[128:, :128] = 0x30
        codes[128:, 128:] = 0xB8
        scales = np.asarray([[0.25, 0.5], [2.0, 4.0]], dtype="<f4")
        raw = q13.dequantize_pair(codes.tobytes(), scales.tobytes(), (256, 256), (2, 2))
        out = np.frombuffer(raw, dtype="<f4").reshape(256, 256)
        self.assertTrue(np.all(out[:128, :128] == np.float32(0.25)))
        self.assertTrue(np.all(out[:128, 128:] == np.float32(1.0)))
        self.assertTrue(np.all(out[128:, :128] == np.float32(1.0)))
        self.assertTrue(np.all(out[128:, 128:] == np.float32(-4.0)))
        self.assertEqual(raw[:4], struct.pack("<f", 0.25))

    def test_down_projection_scale_grid_orientation_is_not_transposable(self):
        # Shape 256x128 with scale 2x1 is valid (128x128 blocks); swapping the
        # scale grid to 1x2 changes the required weight geometry and must fail.
        codes = bytes([0x38]) * (256 * 128)
        good_scale = np.asarray([[1.0], [2.0]], dtype="<f4").tobytes()
        raw = q13.dequantize_pair(codes, good_scale, (256, 128), (2, 1))
        out = np.frombuffer(raw, dtype="<f4").reshape(256, 128)
        self.assertTrue(np.all(out[:128] == 1.0))
        self.assertTrue(np.all(out[128:] == 2.0))
        with self.assertRaisesRegex(q13.CanonicalSourceSetError, "BLOCK_GEOMETRY"):
            q13.dequantize_pair(codes, good_scale, (256, 128), (1, 2))

    def test_gate_up_hash_is_exact_row_concatenation(self):
        gate = np.arange(256 * 128, dtype=np.float32).reshape(256, 128)
        up = -gate
        gate_b = np.asarray(gate, dtype="<f4").tobytes(order="C")
        up_b = np.asarray(up, dtype="<f4").tobytes(order="C")
        h = hashlib.sha256(); h.update(gate_b); h.update(up_b)
        concat = np.concatenate([gate, up], axis=0)
        self.assertEqual(h.hexdigest(), hashlib.sha256(np.asarray(concat, dtype="<f4").tobytes(order="C")).hexdigest())

    def test_pr641_source_set_grammar_exact(self):
        gate_up = "11" * 32
        down = "22" * 32
        digest, entries = q13.source_set_digest(gate_up_sha256=gate_up, down_sha256=down)
        self.assertEqual([x["tensor_role"] for x in entries], ["down_proj", "gate_up_proj"])
        self.assertEqual(entries[0]["source_shape"], [6144, 2048])
        self.assertEqual(entries[1]["source_shape"], [4096, 6144])
        body = {"schema": "AURA_GLM53_E8_SOURCE_TENSOR_SET_V1", "entries": list(entries)}
        expected = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()
        self.assertEqual(digest, expected)

    def test_source_digest_rejects_non_sha_input(self):
        with self.assertRaises(q13.CanonicalSourceSetError):
            q13.source_set_digest(gate_up_sha256="abc", down_sha256="22" * 32)

    def test_nan_codes_bad_scales_and_bad_geometry_fail_closed(self):
        codes = bytearray([0x38]) * (128 * 128)
        scale = struct.pack("<f", 1.0)
        codes[2] = 0x7F
        with self.assertRaisesRegex(q13.CanonicalSourceSetError, "NAN"):
            q13.dequantize_pair(bytes(codes), scale, (128, 128), (1, 1))
        clean = bytes([0x38]) * (128 * 128)
        for bad in (0.0, -1.0, float("nan"), float("inf")):
            with self.assertRaisesRegex(q13.CanonicalSourceSetError, "SCALE"):
                q13.dequantize_pair(clean, struct.pack("<f", bad), (128, 128), (1, 1))
        with self.assertRaisesRegex(q13.CanonicalSourceSetError, "BLOCK_GEOMETRY"):
            q13.dequantize_pair(clean, scale, (128, 128), (2, 1))

    def test_claim_ceiling_retains_page_execution_and_authority_leaves(self):
        fields = q13.FullRepresentativeCanonicalSourceSetReceipt.__dataclass_fields__
        for name in (
            "actual_e8_page_payload_materialized",
            "official_tensor_to_e8_page_derivation_proven",
            "candidate_page_materialization_owner_bound",
            "baseline_same_official_source_tensor_set_proven",
            "whole_model_coverage_proven",
            "model_execution_observed",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertIn(name, fields)


if __name__ == "__main__":
    unittest.main()
