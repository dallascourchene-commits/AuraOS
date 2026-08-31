from __future__ import annotations

from dataclasses import asdict
import inspect
import unittest

from tools.quantization import aura_glm53_minimum_live_payload_cover_verification as q12


class MinimumLivePayloadCoverVerificationTests(unittest.TestCase):
    def test_remaining_source_cone_is_exactly_up_and_down_pairs(self) -> None:
        rows = q12.remaining_source_slices()
        self.assertEqual(len(rows), 4)
        self.assertEqual({x.projection for x in rows}, {"up", "down"})
        self.assertEqual(sum(x.expected_bytes for x in rows), 25_171_968)
        self.assertEqual(
            {x.tensor_key.rsplit(".", 2)[-2] + "." + x.tensor_key.rsplit(".", 1)[-1] for x in rows},
            {
                "up_proj.weight",
                "up_proj.weight_scale_inv",
                "down_proj.weight",
                "down_proj.weight_scale_inv",
            },
        )

    def test_exact_parent_generations_are_pinned(self) -> None:
        self.assertEqual(q12.PR653_PROOF_HEAD, "b2da1ada1568b6e7c3629001b4ecca3c1ba4fe76")
        self.assertEqual(q12.PR653_RUN, 33375061325)
        self.assertEqual(q12.PR653_SOURCE_BLOB, "314ab1bb75278b18d8d5a3335ffeede1a0f2b57b")
        self.assertEqual(q12.PR654_PROOF_HEAD, "26e377fe543b8c1906832b8c1e968dfe63480005")
        self.assertEqual(q12.PR654_RUN, 33375530171)
        self.assertEqual(q12.PR654_SOURCE_BLOB, "0b6a53612d4d2d9993da49180cfc74d5f4996548")
        self.assertEqual(q12.ADMITTED_OBSERVATIONS, ("down-pair", "up-pair"))
        self.assertEqual(q12.ADMITTED_NEW_BYTES, 25_171_968)

    def test_parent_delta_is_exact_and_incomplete_before_q12(self) -> None:
        q12._validate_parent_delta()

    def test_build_receipt_closes_only_representative_raw_payload_coverage(self) -> None:
        payloads = {x.tensor_key: bytes(x.expected_bytes) for x in q12.remaining_source_slices()}
        r = q12._build_receipt(header_len=q12.EXPECTED_HEADER_LENGTH, payloads=payloads)
        self.assertEqual(r.newly_observed_slice_count, 4)
        self.assertEqual(r.total_observed_slice_count, 6)
        self.assertEqual(r.remaining_slice_count, 0)
        self.assertEqual(r.newly_observed_payload_bytes, 25_171_968)
        self.assertEqual(r.total_observed_payload_bytes, 37_757_952)
        self.assertTrue(r.full_representative_raw_payload_coverage_observed)
        self.assertEqual(r.result_consequence, q12.RESULT_CONSEQUENCE)
        self.assertTrue(r.consequence_state_changed)
        self.assertTrue(r.result_new_sck_candidate)
        self.assertFalse(r.admission_itself_counts_as_terminal_semantic_sibling)
        self.assertTrue(r.terminal_sibling_requires_exact_hosted_proof)

    def test_build_receipt_requires_exact_payload_key_set(self) -> None:
        rows = q12.remaining_source_slices()
        payloads = {x.tensor_key: bytes(x.expected_bytes) for x in rows[:-1]}
        with self.assertRaisesRegex(q12.MinimumCoverObservationError, "Q12_PAYLOAD_KEY_SET_MISMATCH"):
            q12._build_receipt(header_len=q12.EXPECTED_HEADER_LENGTH, payloads=payloads)

    def test_build_receipt_rejects_header_drift(self) -> None:
        payloads = {x.tensor_key: bytes(x.expected_bytes) for x in q12.remaining_source_slices()}
        with self.assertRaisesRegex(q12.MinimumCoverObservationError, "Q12_LIVE_HEADER_LENGTH_DRIFT"):
            q12._build_receipt(header_len=q12.EXPECTED_HEADER_LENGTH + 1, payloads=payloads)

    def test_build_receipt_rejects_payload_length_drift(self) -> None:
        rows = q12.remaining_source_slices()
        payloads = {x.tensor_key: bytes(x.expected_bytes) for x in rows}
        payloads[rows[0].tensor_key] = b"x"
        with self.assertRaisesRegex(q12.MinimumCoverObservationError, "Q12_PAYLOAD_LENGTH_MISMATCH"):
            q12._build_receipt(header_len=q12.EXPECTED_HEADER_LENGTH, payloads=payloads)

    def test_nonpromotion_ceiling_is_complete(self) -> None:
        payloads = {x.tensor_key: bytes(x.expected_bytes) for x in q12.remaining_source_slices()}
        r = asdict(q12._build_receipt(header_len=q12.EXPECTED_HEADER_LENGTH, payloads=payloads))
        for key in (
            "block_fp8_dequantization_semantics_bound",
            "gate_up_source_layout_relation_bound",
            "raw_fp8_payload_is_canonical_float32_source_identity",
            "exact_official_tensor_to_concrete_source_tensor_set_relation",
            "candidate_page_materialization_owner_bound",
            "baseline_same_official_source_tensor_set_proven",
            "all_layers_experts_uniformity_proven",
            "real_tensor_quantization_eligible",
            "model_execution_observed",
            "generalized_quality_proven",
            "runtime_performance_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(r[key], key)
        self.assertTrue(r["representative_scope_only"])

    def test_receipt_is_deterministic_for_identical_evidence(self) -> None:
        payloads = {x.tensor_key: bytes(x.expected_bytes) for x in q12.remaining_source_slices()}
        a = q12._build_receipt(header_len=q12.EXPECTED_HEADER_LENGTH, payloads=payloads)
        b = q12._build_receipt(header_len=q12.EXPECTED_HEADER_LENGTH, payloads=payloads)
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(len(a.receipt_digest), 64)

    def test_public_live_boundary_has_no_effect_escape_hatch(self) -> None:
        self.assertEqual(len(inspect.signature(q12.current_live_minimum_cover_observation).parameters), 0)
        self.assertFalse(q12.public_api_has_effect_boolean())


if __name__ == "__main__":
    unittest.main()
