import inspect
import unittest

from tools.quantization import aura_glm53_live_official_tensor_payload_canary as canary
from tools.quantization import aura_glm53_live_payload_coverage_delta as delta
from tools.quantization import aura_glm53_remaining_official_payload_slices as q12


class RemainingOfficialPayloadSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = {}
        for index, spec in enumerate(q12.missing_source_slices(), start=1):
            cls.payloads[spec.tensor_key] = bytes([index]) * spec.expected_bytes

    def test_exact_missing_four_slice_geometry_and_minimum_byte_cone(self):
        missing = q12.missing_source_slices()
        self.assertEqual(4, len(missing))
        self.assertEqual({"up", "down"}, {item.projection for item in missing})
        self.assertEqual(25_171_968, sum(item.expected_bytes for item in missing))
        self.assertLessEqual(sum(item.expected_bytes for item in missing), q12.MAX_NEW_PAYLOAD_BYTES)

    def test_build_receipt_closes_only_representative_raw_payload_coverage(self):
        receipt = q12._build_receipt(
            header_len=delta.LIVE_HEADER_LENGTH_BYTES,
            header_sha=canary.SELECTED_HEADER_SHA256,
            payloads=self.payloads,
        )
        self.assertEqual(4, receipt.newly_observed_slice_count)
        self.assertEqual(6, receipt.combined_slice_count)
        self.assertEqual(25_171_968, receipt.newly_observed_payload_bytes)
        self.assertEqual(37_757_952, receipt.combined_representative_payload_bytes)
        self.assertTrue(receipt.up_pair_observed)
        self.assertTrue(receipt.down_pair_observed)
        self.assertTrue(receipt.representative_expert_raw_payload_coverage_complete)
        self.assertFalse(receipt.full_shard_payload_observed)
        self.assertFalse(receipt.all_layers_experts_payload_coverage_proven)

    def test_payload_hashes_do_not_cross_cast_to_float32_source_identity(self):
        receipt = q12._build_receipt(
            header_len=delta.LIVE_HEADER_LENGTH_BYTES,
            header_sha=canary.SELECTED_HEADER_SHA256,
            payloads=self.payloads,
        )
        self.assertFalse(receipt.raw_fp8_payload_is_canonical_float32_source_identity)
        self.assertFalse(receipt.block_fp8_dequantization_semantics_bound)
        self.assertFalse(receipt.gate_up_source_layout_relation_bound)
        self.assertFalse(receipt.exact_official_tensor_to_pr628_source_tensor_relation_proven)
        self.assertFalse(receipt.candidate_page_materialization_owner_bound)
        self.assertFalse(receipt.baseline_same_official_source_tensor_set_proven)

    def test_exact_missing_keyset_is_required(self):
        payloads = dict(self.payloads)
        payloads.pop(next(iter(payloads)))
        with self.assertRaisesRegex(q12.RemainingPayloadError, "EXACT_MISSING_PAYLOAD_KEYSET"):
            q12._build_receipt(
                header_len=delta.LIVE_HEADER_LENGTH_BYTES,
                header_sha=canary.SELECTED_HEADER_SHA256,
                payloads=payloads,
            )

    def test_payload_length_drift_is_rejected(self):
        payloads = dict(self.payloads)
        key = next(iter(payloads))
        payloads[key] = payloads[key][:-1]
        with self.assertRaisesRegex(q12.RemainingPayloadError, "PAYLOAD_LENGTH_MISMATCH"):
            q12._build_receipt(
                header_len=delta.LIVE_HEADER_LENGTH_BYTES,
                header_sha=canary.SELECTED_HEADER_SHA256,
                payloads=payloads,
            )

    def test_header_metadata_offset_or_role_substitution_is_rejected(self):
        header = {}
        for spec in delta.exact_source_slices():
            header[spec.tensor_key] = {
                "dtype": spec.dtype,
                "shape": list(spec.shape),
                "data_offsets": list(spec.relative_offsets),
            }
        q12._validate_header_metadata(header)
        mutated = {key: dict(value) for key, value in header.items()}
        key = next(item.tensor_key for item in delta.exact_source_slices() if item.projection == "up")
        mutated[key]["data_offsets"] = [0, 1]
        with self.assertRaisesRegex(q12.RemainingPayloadError, "HEADER_OFFSET_DRIFT"):
            q12._validate_header_metadata(mutated)

    def test_header_digest_drift_is_rejected(self):
        with self.assertRaisesRegex(q12.RemainingPayloadError, "HEADER_DIGEST_DRIFT"):
            q12._build_receipt(
                header_len=delta.LIVE_HEADER_LENGTH_BYTES,
                header_sha="0" * 64,
                payloads=self.payloads,
            )

    def test_receipt_is_deterministic_and_authority_ceiling_is_closed(self):
        left = q12._build_receipt(
            header_len=delta.LIVE_HEADER_LENGTH_BYTES,
            header_sha=canary.SELECTED_HEADER_SHA256,
            payloads=self.payloads,
        )
        right = q12._build_receipt(
            header_len=delta.LIVE_HEADER_LENGTH_BYTES,
            header_sha=canary.SELECTED_HEADER_SHA256,
            payloads=dict(reversed(tuple(self.payloads.items()))),
        )
        self.assertEqual(left.receipt_digest, right.receipt_digest)
        for field in (
            "real_tensor_quantization_eligible",
            "model_execution_observed",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(getattr(left, field), field)
        self.assertFalse(q12.public_api_has_promotion_inputs())
        self.assertEqual(0, len(inspect.signature(q12.current_live_remaining_observation).parameters))


if __name__ == "__main__":
    unittest.main()
