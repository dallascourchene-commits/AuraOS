from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from tools.awj032 import glm53_prefetch_transfer_admission as g2
from tools.awj032.glm53_g2_abstention_neutral_admission import (
    ABSTENTION_DISPOSITION,
    REUSE_NOT_APPLICABLE,
    G1AbstentionProjection,
    admit_abstention_neutral,
    example_abstention,
    example_policy,
)


class G2AbstentionNeutralAdmissionTests(unittest.TestCase):
    def test_exact_abstention_returns_typed_empty_plan(self):
        receipt = admit_abstention_neutral(
            abstention=example_abstention(),
            forecasts=(),
            policy=example_policy(),
        )
        self.assertEqual((), receipt.predicted_experts)
        self.assertEqual((), receipt.admitted_experts)
        self.assertEqual((), receipt.candidate_decisions)
        self.assertEqual(0, receipt.cold_predicted_logical_bytes)
        self.assertIsNone(receipt.cold_required_reuse_for_window)
        self.assertEqual(REUSE_NOT_APPLICABLE, receipt.cold_required_reuse_disposition)
        self.assertEqual(0, receipt.admitted_logical_bytes)
        self.assertEqual(0.0, receipt.admitted_logical_transfer_seconds)
        self.assertEqual(0.0, receipt.admitted_expected_latency_margin_seconds)
        self.assertIsNone(receipt.admitted_estimated_energy_joules)
        self.assertEqual(ABSTENTION_DISPOSITION, receipt.disposition)

    def test_zero_bytes_never_enter_w4_required_reuse_math(self):
        with patch.object(g2, "required_reuse", side_effect=AssertionError("W4_ZERO_BYTE_CROSS_CAST")):
            receipt = admit_abstention_neutral(
                abstention=example_abstention(),
                forecasts=(),
                policy=example_policy(),
            )
        self.assertIsNone(receipt.cold_required_reuse_for_window)
        self.assertEqual(REUSE_NOT_APPLICABLE, receipt.cold_required_reuse_disposition)

    def test_nonempty_prediction_is_not_abstention(self):
        bad = replace(example_abstention(), predicted_experts=(1,))
        with self.assertRaisesRegex(ValueError, "G2A_REQUIRES_EXACT_EMPTY_PREDICTION"):
            admit_abstention_neutral(abstention=bad, forecasts=(), policy=example_policy())

    def test_nonempty_forecasts_reject_for_empty_prediction(self):
        forecast = g2.CalibratedExpertForecast(
            expert_id=1,
            calibration_generation="calibration:g2:v1",
            hit_probability_numerator=9,
            hit_probability_denominator=10,
            expected_miss_stall_seconds=0.02,
            logical_expert_bytes=1_000_000,
        )
        with self.assertRaisesRegex(ValueError, "G2A_EMPTY_PREDICTION_REQUIRES_EMPTY_FORECAST_SET"):
            admit_abstention_neutral(
                abstention=example_abstention(), forecasts=(forecast,), policy=example_policy()
            )

    def test_abstention_claims_must_be_exact_true(self):
        cases = (
            ("prediction_abstention_lawful", "G2A_ABSTENTION_MUST_BE_LAWFUL"),
            ("native_route_remains_authoritative", "G2A_NATIVE_ROUTE_AUTHORITY_MUST_REMAIN"),
            ("no_prefetch_call_required", "G2A_EMPTY_PREDICTION_MUST_REQUIRE_NO_PREFETCH_CALL"),
        )
        for field, reason in cases:
            with self.subTest(field=field):
                bad = replace(example_abstention(), **{field: False})
                with self.assertRaisesRegex(ValueError, reason):
                    admit_abstention_neutral(abstention=bad, forecasts=(), policy=example_policy())

    def test_layer_and_source_cross_casts_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "G2A_PREDICTION_POLICY_LAYER_MISMATCH"):
            admit_abstention_neutral(
                abstention=example_abstention(),
                forecasts=(),
                policy=replace(example_policy(), layer_id="layer:08"),
            )
        with self.assertRaisesRegex(ValueError, "G2A_PREDICTION_POLICY_BINDING_MISMATCH"):
            admit_abstention_neutral(
                abstention=example_abstention(),
                forecasts=(),
                policy=replace(example_policy(), binding_digest="binding:other"),
            )

    def test_identity_fields_are_required(self):
        for field in ("predictor_generation", "layer_id", "binding_digest"):
            with self.subTest(field=field):
                bad = replace(example_abstention(), **{field: ""})
                with self.assertRaises(ValueError):
                    admit_abstention_neutral(abstention=bad, forecasts=(), policy=example_policy())

    def test_abstention_never_mints_physical_or_effect_authority(self):
        receipt = admit_abstention_neutral(
            abstention=example_abstention(), forecasts=(), policy=example_policy()
        )
        self.assertFalse(receipt.physical_io_attested)
        self.assertIsNone(receipt.physical_prefetch_bytes)
        self.assertFalse(receipt.physical_storage_budget_proven)
        for field in (
            "native_route_mutated",
            "model_output_semantics_changed",
            "transfer_effect_authorized",
            "g2_admitted",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect",
        ):
            self.assertIs(getattr(receipt, field), False, field)

    def test_receipt_rejects_zero_reuse_cross_cast_and_authority_widening(self):
        receipt = admit_abstention_neutral(
            abstention=example_abstention(), forecasts=(), policy=example_policy()
        )
        with self.assertRaisesRegex(ValueError, "G2A_ZERO_BYTE_REUSE_MUST_REMAIN_NOT_APPLICABLE"):
            replace(receipt, cold_required_reuse_for_window=0.0).validate_claim_ceiling()
        with self.assertRaisesRegex(ValueError, "G2A_ABSTENTION_CANNOT_WIDEN_AUTHORITY"):
            replace(receipt, transfer_effect_authorized=True).validate_claim_ceiling()

    def test_receipt_digest_is_deterministic_and_identity_sensitive(self):
        a = admit_abstention_neutral(
            abstention=example_abstention(), forecasts=(), policy=example_policy()
        )
        b = admit_abstention_neutral(
            abstention=example_abstention(), forecasts=(), policy=example_policy()
        )
        c = admit_abstention_neutral(
            abstention=replace(example_abstention(), predictor_generation="predictor:g2a:v2"),
            forecasts=(),
            policy=example_policy(),
        )
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertNotEqual(a.receipt_digest, c.receipt_digest)


if __name__ == "__main__":
    unittest.main()
