import hashlib
import struct
import unittest

import numpy as np

from tools.quantization import aura_glm53_bounded_official_e8_page_materialization_canary as q14


class BoundedOfficialE8PageMaterializationTests(unittest.TestCase):
    def test_exact_fresh_parent_generations_and_convergence(self):
        self.assertEqual(q14.CONVERGENCE_COMMIT, "f93fe24fa5801378815d7094bbf64c815fd48af1")
        self.assertEqual(q14.Q13_HEAD, "eb09b5ffd14577d1676f57bb908e5ddd81125605")
        self.assertEqual(q14.Q13_RUN, 33397035043)
        self.assertEqual(q14.Q13_JOB, 99503908177)
        self.assertEqual(q14.A6_HEAD, "fa428111f83a0f69319c10c1b28bde910544b776")
        self.assertEqual(q14.A6_RUN, 33397763034)
        self.assertEqual(q14.A6_JOB, 99506305907)
        self.assertEqual(q14.A6_RECEIPT_DIGEST, "86f7f614167e95c0099c828f91b091675238c177c202beb65e11450bec97f847")

    def test_q13_full_source_generation_is_exact(self):
        self.assertEqual(q14.Q13_SOURCE_SET_DIGEST, "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6")
        self.assertEqual(q14.Q13_GATE_UP_SHA256, "46eb726b48a423865b50ffe261881dc5b3667344f93e24e5732b2484d6096c4a")
        self.assertEqual(q14.Q13_DOWN_SHA256, "6ddd0776b011cde6948d5d780630700dfd69ce49907356d371a6d54b59040953")
        self.assertEqual(q14.Q13_RECEIPT_DIGEST, "c143eab6f319689faf1315e32fa9cea1182f7e4ba52372ff5d0c8218d9f4f832")

    def test_minimum_materialization_cone_is_exactly_136_payload_bytes(self):
        self.assertEqual(q14.SLICE_WEIGHT_COUNT, 64)
        self.assertEqual(q14.EXPECTED_NEW_RAW_PAYLOAD_BYTES, 136)
        self.assertEqual(64 + 4 + 64 + 4, q14.EXPECTED_NEW_RAW_PAYLOAD_BYTES)
        self.assertEqual(q14.page_ref.DEFAULT_BLOCK_SIZE, 64)

    def test_first64_fp8_decode_uses_one_exact_scale_cell(self):
        # E4M3FN 0x38 is +1.0. One scale cell must cover this entire 64-value
        # prefix because the official source uses 128x128 blocks.
        raw = bytes([0x38]) * 64
        values = q14._decode_first64(raw, struct.pack("<f", 0.25))
        self.assertEqual(values.dtype, np.dtype("<f4"))
        self.assertTrue(np.all(values == np.float32(0.25)))
        self.assertEqual(values.tobytes()[:4], struct.pack("<f", 0.25))

    def test_nan_code_and_bad_scale_fail_closed(self):
        bad = bytearray([0x38]) * 64
        bad[7] = 0x7F
        with self.assertRaisesRegex(q14.BoundedMaterializationError, "NAN"):
            q14._decode_first64(bytes(bad), struct.pack("<f", 1.0))
        for scale in (0.0, -1.0, float("nan"), float("inf")):
            with self.assertRaisesRegex(q14.BoundedMaterializationError, "SCALE"):
                q14._decode_first64(bytes([0x38]) * 64, struct.pack("<f", scale))

    def test_real_page_payload_binds_slice_identity_not_full_tensor_identity(self):
        values = np.linspace(-1.0, 1.0, 64, dtype=np.float32)
        item, page = q14._materialize_slice_page(
            tensor_role="gate_up_proj",
            parent_full_source_sha256=q14.Q13_GATE_UP_SHA256,
            parent_full_source_shape=(4096, 6144),
            canonical_values=values,
        )
        expected_slice_sha = hashlib.sha256(np.asarray(values, dtype="<f4").tobytes(order="C")).hexdigest()
        self.assertEqual(item.source_slice_sha256, expected_slice_sha)
        self.assertEqual(page.identity.source_tensor_sha256, expected_slice_sha)
        self.assertNotEqual(item.source_slice_sha256, item.parent_full_source_sha256)
        self.assertEqual(item.slice_flat_offset, 0)
        self.assertEqual(item.slice_weight_count, 64)
        self.assertGreater(item.page_payload_bytes, 0)
        page.validate()

    def test_page_materialization_is_deterministic_and_tamper_sensitive(self):
        values = np.arange(64, dtype=np.float32) / np.float32(17.0)
        a, page_a = q14._materialize_slice_page(
            tensor_role="down_proj",
            parent_full_source_sha256=q14.Q13_DOWN_SHA256,
            parent_full_source_shape=(6144, 2048),
            canonical_values=values,
        )
        b, page_b = q14._materialize_slice_page(
            tensor_role="down_proj",
            parent_full_source_sha256=q14.Q13_DOWN_SHA256,
            parent_full_source_shape=(6144, 2048),
            canonical_values=values.copy(),
        )
        self.assertEqual(a, b)
        self.assertEqual(page_a.payload, page_b.payload)
        tampered = q14.page_ref.ExpertPage(
            page_a.identity,
            page_a.payload[:-1] + bytes([page_a.payload[-1] ^ 1]),
            page_a.payload_sha256,
            page_a.k27_coordinate,
            page_a.codec_bits_per_weight,
            page_a.serialized_bits_per_weight,
        )
        with self.assertRaisesRegex(ValueError, "payload digest"):
            tampered.validate()

    def test_parent_full_source_substitution_fails_closed(self):
        values = np.zeros(64, dtype=np.float32)
        with self.assertRaisesRegex(q14.BoundedMaterializationError, "PARENT_FULL_SOURCE"):
            q14._materialize_slice_page(
                tensor_role="down_proj",
                parent_full_source_sha256="not-a-sha",
                parent_full_source_shape=(6144, 2048),
                canonical_values=values,
            )

    def test_public_live_api_has_no_promotion_inputs(self):
        self.assertFalse(q14.public_api_has_promotion_inputs())

    def test_claim_ceiling_keeps_full_materialization_execution_and_authority_open(self):
        fields = q14.BoundedOfficialE8PageMaterializationReceipt.__dataclass_fields__
        for name in (
            "source_slice_identity_is_full_tensor_identity",
            "bounded_materialization_is_full_representative_source_set_materialization",
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
