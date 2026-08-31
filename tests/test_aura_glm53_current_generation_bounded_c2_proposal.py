from __future__ import annotations

from dataclasses import replace
import unittest

from tools.quantization import aura_glm53_current_generation_bounded_c2_proposal as q18


class CurrentGenerationBoundedC2ProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.representative = q18.current_q16_fixture()
        self.source = q18.current_s1_fixture()

    def test_exact_current_generations_admit_only_bounded_proposal(self):
        receipt = q18.admit_current_generation_bounded_c2_proposal(
            self.representative, self.source
        )
        self.assertEqual(receipt["disposition"], q18.ELIGIBLE)
        self.assertTrue(receipt["bounded_c2_request_proposal_eligible"])
        self.assertTrue(receipt["current_representative_generation_bound"])
        self.assertTrue(receipt["current_source_generation_bound"])
        self.assertFalse(receipt["legacy_q7_disposition_reused"])
        self.assertEqual(
            receipt["receipt_digest"],
            "c53acb3ff471dbe3971ee4e7a75b28c4316b50fba88a414f406b93c271c90230",
        )
        for key in (
            "tensor_payload_bound",
            "real_tensor_quantization_observed",
            "model_execution_observed",
            "execution_authorized",
            "owner_host_execution_observed",
            "physical_io_performance_proven",
            "full_tensor_superiority_proven",
            "whole_model_superiority_proven",
            "quality_superiority_proven",
            "runtime_superiority_proven",
            "g2_admitted",
            "gate10_promoted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
        ):
            self.assertFalse(receipt[key], key)

    def test_q16_generation_identity_substitutions_fail_closed(self):
        cases = (
            ("producer_head", "0" * 40),
            ("producer_run", q18.Q16_RUN + 1),
            ("producer_job", q18.Q16_JOB + 1),
            ("artifact_id", q18.Q16_ARTIFACT_ID + 1),
        )
        for field, value in cases:
            with self.subTest(field=field):
                changed = replace(self.representative, **{field: value})
                with self.assertRaisesRegex(ValueError, "Q16_GENERATION_IDENTITY_MISMATCH"):
                    q18.admit_current_generation_bounded_c2_proposal(changed, self.source)

    def test_q16_digest_substitutions_fail_closed(self):
        cases = (
            ("artifact_zip_sha256", "0" * 64, "Q16_ARTIFACT_MISMATCH"),
            ("receipt_digest", "1" * 64, "Q16_RECEIPT_MISMATCH"),
            ("scope_admission_receipt", "2" * 64, "Q16_SCOPE_RECEIPT_MISMATCH"),
            ("q5_receipt_digest", "3" * 64, "Q5_RECEIPT_MISMATCH"),
            ("source_set_digest", "4" * 64, "SOURCE_SET_MISMATCH"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                changed = replace(self.representative, **{field: value})
                with self.assertRaisesRegex(ValueError, message):
                    q18.admit_current_generation_bounded_c2_proposal(changed, self.source)

    def test_q16_scope_or_measurement_drift_fails_closed(self):
        cases = (
            ({"representative_scope_complete": False}, "Q16_REPRESENTATIVE_SCOPE_INCOMPLETE"),
            ({"minimum_missing_evidence_cone": ("missing",)}, "Q16_REPRESENTATIVE_SCOPE_INCOMPLETE"),
            ({"aggregate_outcome": "CONTROL_WIN"}, "Q16_REPRESENTATIVE_OUTCOME_NOT_E8_WIN"),
            ({"aggregate_e8_over_control": 0.7}, "Q16_AGGREGATE_RATIO_DRIFT"),
            ({"candidate_bpw": 1.5}, "Q16_EQUAL_RATE_DRIFT"),
            ({"control_bpw": 1.5}, "Q16_EQUAL_RATE_DRIFT"),
            ({"total_official_weights": 511}, "Q16_SCOPE_COUNT_DRIFT"),
            ({"tile_count": 7}, "Q16_SCOPE_COUNT_DRIFT"),
        )
        for changes, message in cases:
            with self.subTest(changes=changes):
                changed = replace(self.representative, **changes)
                with self.assertRaisesRegex(ValueError, message):
                    q18.admit_current_generation_bounded_c2_proposal(changed, self.source)

    def test_s1_generation_identity_substitutions_fail_closed(self):
        cases = (
            ("producer_head", "0" * 40),
            ("producer_run", q18.S1_RUN + 1),
            ("producer_job", q18.S1_JOB + 1),
            ("artifact_id", q18.S1_ARTIFACT_ID + 1),
        )
        for field, value in cases:
            with self.subTest(field=field):
                changed = replace(self.source, **{field: value})
                with self.assertRaisesRegex(ValueError, "S1_GENERATION_IDENTITY_MISMATCH"):
                    q18.admit_current_generation_bounded_c2_proposal(self.representative, changed)

    def test_s1_digest_substitutions_fail_closed(self):
        cases = (
            ("artifact_zip_sha256", "0" * 64, "S1_ARTIFACT_MISMATCH"),
            ("receipt_digest", "1" * 64, "S1_RECEIPT_MISMATCH"),
            ("source_admission_digest", "2" * 64, "S1_SOURCE_ADMISSION_MISMATCH"),
            ("c2_request_digest", "3" * 64, "S1_C2_REQUEST_MISMATCH"),
            ("index_sha256", "4" * 64, "S1_INDEX_MISMATCH"),
            ("header_sha256", "5" * 64, "S1_HEADER_MISMATCH"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                changed = replace(self.source, **{field: value})
                with self.assertRaisesRegex(ValueError, message):
                    q18.admit_current_generation_bounded_c2_proposal(self.representative, changed)

    def test_s1_materialization_or_gate_drift_fails_closed(self):
        cases = (
            ({"index_size_bytes": 11_359_250}, "S1_BOUNDED_METADATA_SIZE_DRIFT"),
            ({"header_prefix_bytes": 105_431}, "S1_BOUNDED_METADATA_SIZE_DRIFT"),
            ({"total_source_evidence_bytes": 11_464_682}, "S1_TOTAL_SOURCE_EVIDENCE_DRIFT"),
            ({"source_header_trial_eligible": False}, "S1_CURRENT_SOURCE_GATE_NOT_GREEN"),
            ({"source_bound_c2_request_admissible": False}, "S1_CURRENT_SOURCE_GATE_NOT_GREEN"),
            ({"blocker": "STALE"}, "S1_BLOCKER_STATE_DRIFT"),
        )
        for changes, message in cases:
            with self.subTest(changes=changes):
                changed = replace(self.source, **changes)
                with self.assertRaisesRegex(ValueError, message):
                    q18.admit_current_generation_bounded_c2_proposal(self.representative, changed)

    def test_legacy_q7_disposition_injection_is_rejected(self):
        changed = replace(
            self.source,
            legacy_q7_disposition_digest=q18.LEGACY_Q7_DISPOSITION_DIGEST,
        )
        with self.assertRaisesRegex(ValueError, "LEGACY_Q7_DISPOSITION_LAUNDERING"):
            q18.admit_current_generation_bounded_c2_proposal(self.representative, changed)

    def test_official_source_identity_drift_is_rejected_on_both_parents(self):
        with self.assertRaisesRegex(ValueError, "Q16_OFFICIAL_SOURCE_MISMATCH"):
            q18.admit_current_generation_bounded_c2_proposal(
                replace(self.representative, official_revision="deadbeef"), self.source
            )
        with self.assertRaisesRegex(ValueError, "S1_OFFICIAL_SOURCE_MISMATCH"):
            q18.admit_current_generation_bounded_c2_proposal(
                self.representative, replace(self.source, official_revision="deadbeef")
            )

    def test_receipt_is_deterministic_and_authority_ceiling_cannot_widen(self):
        a = q18.admit_current_generation_bounded_c2_proposal(
            self.representative, self.source
        )
        b = q18.admit_current_generation_bounded_c2_proposal(
            q18.current_q16_fixture(), q18.current_s1_fixture()
        )
        self.assertEqual(a, b)
        self.assertEqual(a["receipt_digest"], b["receipt_digest"])
        forbidden_true = {
            key for key, value in a.items()
            if key in {
                "tensor_payload_bound",
                "real_tensor_quantization_observed",
                "model_execution_observed",
                "execution_authorized",
                "owner_host_execution_observed",
                "physical_io_performance_proven",
                "full_tensor_superiority_proven",
                "whole_model_superiority_proven",
                "quality_superiority_proven",
                "runtime_superiority_proven",
                "g2_admitted",
                "gate10_promoted",
                "semantic_k27_authority_minted",
                "native_private_transformer_kv_accessed",
            }
            and value is True
        }
        self.assertEqual(forbidden_true, set())


if __name__ == "__main__":
    unittest.main()
