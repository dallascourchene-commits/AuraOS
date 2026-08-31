from __future__ import annotations

from copy import deepcopy
import unittest

from tools.quantization import aura_glm53_historical_official_w2_bridge as q6
from tools.quantization import aura_glm53_official_source_admission as q5


class HistoricalOfficialW2BridgeTests(unittest.TestCase):
    def observation(self):
        return q6.canonical_pr398_observation()

    def test_exact_historical_observation_rebinds_without_current_byte_promotion(self):
        receipt = q6.build_historical_official_w2_bridge(self.observation())
        self.assertEqual(receipt.parent_heads, (q6.PR639_HEAD, q6.PR398_HEAD))
        self.assertEqual(receipt.parent_runs, (q6.PR639_RUN, q6.PR398_RUN))
        self.assertTrue(receipt.historical_raw_index_verification_observed)
        self.assertTrue(receipt.historical_weight_map_relation_observed)
        self.assertTrue(receipt.historical_representative_headers_observed)
        self.assertTrue(receipt.historical_fp8_companions_bound)
        self.assertEqual(receipt.historical_payload_bytes_read, 0)
        self.assertTrue(receipt.current_pr639_schema_header_geometry_conforms)
        self.assertTrue(receipt.representative_per_expert_serialization_proven)
        self.assertFalse(receipt.all_layers_experts_uniformity_proven)
        self.assertFalse(receipt.current_consumer_raw_index_bytes_materialized)
        self.assertFalse(receipt.current_consumer_raw_header_prefixes_materialized)
        self.assertFalse(receipt.current_pr639_raw_byte_header_trial_eligible)
        self.assertFalse(receipt.source_tensor_payload_bound)
        self.assertFalse(receipt.real_tensor_quantization_eligible)

    def test_current_pr639_raw_public_state_remains_hold(self):
        state = q5.current_public_state()
        self.assertFalse(state.index_bytes_verified)
        self.assertFalse(state.representative_headers_observed)
        self.assertFalse(state.fp8_companions_bound)
        self.assertFalse(state.header_trial_eligible)
        self.assertFalse(state.source_tensor_payload_bound)
        self.assertFalse(state.real_tensor_quantization_eligible)
        self.assertEqual(
            state.blocker,
            "OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED",
        )

    def test_receipt_digest_is_deterministic(self):
        a = q6.build_historical_official_w2_bridge(self.observation())
        b = q6.build_historical_official_w2_bridge(self.observation())
        self.assertEqual(a.digest, b.digest)
        self.assertEqual(len(a.digest), 64)

    def test_producer_receipt_substitution_fails_closed(self):
        o = self.observation()
        o["receipt_digest"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "receipt_digest"):
            q6.build_historical_official_w2_bridge(o)

    def test_producer_head_run_job_and_drive_substitutions_fail_closed(self):
        for field, value in (
            ("producer_semantic_head", "f" * 40),
            ("producer_run", q6.PR398_RUN + 1),
            ("producer_job", q6.PR398_JOB + 1),
            ("drive_observation_id", "foreign-drive-id"),
        ):
            with self.subTest(field=field):
                o = self.observation()
                o[field] = value
                with self.assertRaisesRegex(ValueError, field):
                    q6.build_historical_official_w2_bridge(o)

    def test_source_revision_index_and_size_substitutions_fail_closed(self):
        for field, value in (
            ("repo_id", "other/model"),
            ("model_revision", "a" * 40),
            ("index_sha256", "b" * 64),
            ("index_size_bytes", q5.OFFICIAL_INDEX_SIZE + 1),
        ):
            with self.subTest(field=field):
                o = self.observation()
                o[field] = value
                with self.assertRaisesRegex(ValueError, field):
                    q6.build_historical_official_w2_bridge(o)

    def test_missing_or_extra_header_role_fails_closed(self):
        o = self.observation()
        o["entries"] = o["entries"][:-1]
        with self.assertRaisesRegex(ValueError, "entries"):
            q6.build_historical_official_w2_bridge(o)
        o = self.observation()
        o["entries"].append(deepcopy(o["entries"][0]))
        with self.assertRaisesRegex(ValueError, "entries"):
            q6.build_historical_official_w2_bridge(o)

    def test_weight_dtype_scale_dtype_and_scale_shape_substitutions_fail_closed(self):
        changes = (
            (0, "dtype", "F16"),
            (1, "dtype", "F16"),
            (1, "shape", [17, 48]),
        )
        for index, field, value in changes:
            with self.subTest(index=index, field=field):
                o = self.observation()
                o["entries"][index][field] = value
                with self.assertRaisesRegex(ValueError, "entries"):
                    q6.build_historical_official_w2_bridge(o)

    def test_shard_header_and_offset_substitutions_fail_closed(self):
        changes = (
            (0, "shard", "model-00039-of-00141.safetensors"),
            (0, "header_sha256", "c" * 64),
            (0, "data_offsets", [1, 2]),
        )
        for index, field, value in changes:
            with self.subTest(index=index, field=field):
                o = self.observation()
                o["entries"][index][field] = value
                with self.assertRaisesRegex(ValueError, "entries"):
                    q6.build_historical_official_w2_bridge(o)

    def test_representative_evidence_cannot_self_promote(self):
        r = q6.build_historical_official_w2_bridge(self.observation())
        for value in (
            r.all_layers_experts_uniformity_proven,
            r.current_consumer_raw_index_bytes_materialized,
            r.current_consumer_raw_header_prefixes_materialized,
            r.current_pr639_raw_byte_header_trial_eligible,
            r.source_tensor_payload_bound,
            r.real_tensor_quantization_eligible,
            r.semantic_k27_authority,
            r.native_transformer_kv_accessed,
            r.gate10_promoted,
        ):
            self.assertFalse(value)

    def test_exact_six_entries_match_current_block_geometry(self):
        o = self.observation()
        bundle = q6._rebind_entries_to_pr639(o)
        self.assertEqual(len(bundle.entries), 6)
        pairs = list(zip(bundle.entries[0::2], bundle.entries[1::2]))
        for weight, scale in pairs:
            expected = tuple(
                (dim + block - 1) // block
                for dim, block in zip(weight.shape, q5.EXPECTED_WEIGHT_BLOCK)
            )
            self.assertEqual(scale.shape, expected)


if __name__ == "__main__":
    unittest.main()
