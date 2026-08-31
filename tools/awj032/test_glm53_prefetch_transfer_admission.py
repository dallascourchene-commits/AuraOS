from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_router_separated_prefetch import (
    PREFETCH_SCHEMA,
    PrefetchPrediction,
)
from tools.awj032.glm53_prefetch_transfer_admission import (
    ELIGIBLE,
    HOLD_ENERGY,
    SKIP_BATCH_BYTES,
    SKIP_CONFIDENCE,
    SKIP_ENERGY,
    SKIP_MARGIN,
    SKIP_WINDOW,
    CalibratedExpertForecast,
    PrefetchTransferPolicy,
    admit_prefetch_transfers,
)


def prediction(experts=(0, 1, 2)) -> PrefetchPrediction:
    return PrefetchPrediction(
        schema=PREFETCH_SCHEMA,
        predictor_generation="predictor:g2:v1",
        layer_id="layer:07",
        binding_digest="binding:g2:source",
        predicted_experts=tuple(experts),
    )


def forecast(
    expert: int,
    *,
    p_num: int = 9,
    p_den: int = 10,
    stall: float = 0.020,
    logical_bytes: int = 1_000_000,
    energy: float | None = None,
) -> CalibratedExpertForecast:
    return CalibratedExpertForecast(
        expert_id=expert,
        calibration_generation="calibration:g2:v1",
        hit_probability_numerator=p_num,
        hit_probability_denominator=p_den,
        expected_miss_stall_seconds=stall,
        logical_expert_bytes=logical_bytes,
        estimated_transfer_energy_joules=energy,
    )


def policy(**updates) -> PrefetchTransferPolicy:
    base = dict(
        policy_generation="policy:g2:v1",
        predictor_calibration_generation="calibration:g2:v1",
        layer_id="layer:07",
        binding_digest="binding:g2:source",
        effective_storage_bandwidth_bytes_per_second=1_000_000_000.0,
        prefetch_window_seconds=0.010,
        minimum_hit_probability_numerator=1,
        minimum_hit_probability_denominator=2,
        eviction_penalty_seconds=0.0,
        rework_penalty_seconds=0.0,
        max_logical_prefetch_bytes=None,
        max_estimated_transfer_energy_joules=None,
    )
    base.update(updates)
    return PrefetchTransferPolicy(**base)


class PrefetchTransferAdmissionTests(unittest.TestCase):
    def test_positive_expected_latency_value_admits_without_effect_authority(self):
        receipt = admit_prefetch_transfers(
            prediction=prediction((0, 1)),
            forecasts=[forecast(0), forecast(1)],
            policy=policy(),
            num_experts=8,
        )
        self.assertEqual((0, 1), receipt.admitted_experts)
        self.assertTrue(all(d.disposition == ELIGIBLE for d in receipt.candidate_decisions))
        self.assertGreater(receipt.admitted_expected_latency_margin_seconds, 0)
        self.assertFalse(receipt.physical_io_attested)
        self.assertIsNone(receipt.physical_prefetch_bytes)
        self.assertFalse(receipt.physical_storage_budget_proven)
        self.assertFalse(receipt.native_route_mutated)
        self.assertFalse(receipt.model_output_semantics_changed)
        self.assertFalse(receipt.transfer_effect_authorized)
        self.assertFalse(receipt.g2_admitted)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)
        self.assertFalse(receipt.semantic_k27_authority_minted)
        self.assertFalse(receipt.gate10_promoted)
        self.assertEqual(receipt.receipt_digest, receipt.receipt_digest)

    def test_low_confidence_skips_even_with_positive_raw_margin(self):
        receipt = admit_prefetch_transfers(
            prediction=prediction((0,)),
            forecasts=[forecast(0, p_num=4, p_den=10, stall=0.1)],
            policy=policy(),
            num_experts=8,
        )
        self.assertEqual((), receipt.admitted_experts)
        self.assertEqual(SKIP_CONFIDENCE, receipt.candidate_decisions[0].disposition)

    def test_nonpositive_latency_margin_skips(self):
        receipt = admit_prefetch_transfers(
            prediction=prediction((0,)),
            forecasts=[forecast(0, stall=0.0005)],
            policy=policy(),
            num_experts=8,
        )
        self.assertEqual(SKIP_MARGIN, receipt.candidate_decisions[0].disposition)
        self.assertEqual((), receipt.admitted_experts)

    def test_window_capacity_prefers_higher_expected_margin_deterministically(self):
        receipt = admit_prefetch_transfers(
            prediction=prediction((0, 1)),
            forecasts=[
                forecast(0, stall=0.020, logical_bytes=6_000_000),
                forecast(1, stall=0.030, logical_bytes=6_000_000),
            ],
            policy=policy(prefetch_window_seconds=0.006),
            num_experts=8,
        )
        self.assertEqual((1,), receipt.admitted_experts)
        by_id = {d.expert_id: d for d in receipt.candidate_decisions}
        self.assertEqual(SKIP_WINDOW, by_id[0].disposition)
        self.assertEqual(ELIGIBLE, by_id[1].disposition)

    def test_batch_logical_byte_cap_is_independent_hard_gate(self):
        receipt = admit_prefetch_transfers(
            prediction=prediction((0, 1)),
            forecasts=[forecast(0), forecast(1)],
            policy=policy(max_logical_prefetch_bytes=1_000_000),
            num_experts=8,
        )
        self.assertEqual((0,), receipt.admitted_experts)
        by_id = {d.expert_id: d for d in receipt.candidate_decisions}
        self.assertEqual(SKIP_BATCH_BYTES, by_id[1].disposition)

    def test_energy_budget_requires_typed_estimate_when_enabled(self):
        receipt = admit_prefetch_transfers(
            prediction=prediction((0,)),
            forecasts=[forecast(0, energy=None)],
            policy=policy(max_estimated_transfer_energy_joules=2.0),
            num_experts=8,
        )
        self.assertEqual(HOLD_ENERGY, receipt.candidate_decisions[0].disposition)
        self.assertEqual((), receipt.admitted_experts)

    def test_energy_budget_cannot_be_paid_by_latency_margin(self):
        receipt = admit_prefetch_transfers(
            prediction=prediction((0,)),
            forecasts=[forecast(0, stall=1.0, energy=3.0)],
            policy=policy(max_estimated_transfer_energy_joules=2.0),
            num_experts=8,
        )
        self.assertEqual(SKIP_ENERGY, receipt.candidate_decisions[0].disposition)
        self.assertEqual((), receipt.admitted_experts)

    def test_storage_reuse_requirement_is_preserved_as_storage_only_math(self):
        receipt = admit_prefetch_transfers(
            prediction=prediction((0, 1)),
            forecasts=[
                forecast(0, logical_bytes=10_000_000),
                forecast(1, logical_bytes=10_000_000),
            ],
            policy=policy(
                effective_storage_bandwidth_bytes_per_second=1_000_000_000,
                prefetch_window_seconds=0.010,
            ),
            num_experts=8,
        )
        self.assertAlmostEqual(0.5, receipt.cold_required_reuse_for_window)
        self.assertFalse(receipt.physical_storage_budget_proven)

    def test_binding_layer_and_calibration_substitutions_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "PREDICTION_POLICY_LAYER_MISMATCH"):
            admit_prefetch_transfers(
                prediction=prediction((0,)),
                forecasts=[forecast(0)],
                policy=policy(layer_id="layer:08"),
                num_experts=8,
            )
        with self.assertRaisesRegex(ValueError, "PREDICTION_POLICY_BINDING_MISMATCH"):
            admit_prefetch_transfers(
                prediction=prediction((0,)),
                forecasts=[forecast(0)],
                policy=policy(binding_digest="binding:other"),
                num_experts=8,
            )
        with self.assertRaisesRegex(ValueError, "FORECAST_CALIBRATION_GENERATION_MISMATCH"):
            admit_prefetch_transfers(
                prediction=prediction((0,)),
                forecasts=[replace(forecast(0), calibration_generation="calibration:stale")],
                policy=policy(),
                num_experts=8,
            )

    def test_forecast_set_must_exactly_match_prediction(self):
        with self.assertRaisesRegex(ValueError, "FORECAST_SET_MUST_EQUAL_PREDICTED_EXPERT_SET"):
            admit_prefetch_transfers(
                prediction=prediction((0, 1)),
                forecasts=[forecast(0)],
                policy=policy(),
                num_experts=8,
            )


if __name__ == "__main__":
    unittest.main()
