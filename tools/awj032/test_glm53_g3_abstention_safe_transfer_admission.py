import unittest
from dataclasses import dataclass

from tools.awj032.glm53_router_separated_prefetch import (
    NATIVE_ROUTE_SCHEMA,
    PREFETCH_SCHEMA,
    NativeRoute,
    PrefetchPrediction,
    stage_then_demand_load,
)
from tools.awj032.glm53_prefetch_transfer_admission import (
    CalibratedExpertForecast,
    PrefetchTransferPolicy,
    admit_prefetch_transfers,
)


@dataclass(frozen=True)
class _PageResult:
    binding_digest: str
    expert_ids: tuple[int, ...]


class _Pager:
    def __init__(self, binding_digest: str):
        self.binding_digest = binding_digest
        self.calls: list[tuple[tuple[int, ...], str, str]] = []

    def load_selected(self, expert_ids, *, model_revision: str, index_digest: str):
        ids = tuple(expert_ids)
        self.calls.append((ids, model_revision, index_digest))
        return _PageResult(binding_digest=self.binding_digest, expert_ids=ids)


class _DishonestPager(_Pager):
    def load_selected(self, expert_ids, *, model_revision: str, index_digest: str):
        ids = tuple(expert_ids)
        self.calls.append((ids, model_revision, index_digest))
        return _PageResult(binding_digest="wrong-binding", expert_ids=ids)


class G3AbstentionSafeTransferAdmissionTests(unittest.TestCase):
    def _prediction(self):
        return PrefetchPrediction(
            schema=PREFETCH_SCHEMA,
            predictor_generation="predictor:abstain:v1",
            layer_id="layer:17",
            binding_digest="binding:official-source",
            predicted_experts=(),
        )

    def _policy(self, **overrides):
        values = dict(
            policy_generation="policy:g3:v1",
            predictor_calibration_generation="cal:g3:v1",
            layer_id="layer:17",
            binding_digest="binding:official-source",
            effective_storage_bandwidth_bytes_per_second=1_000_000_000.0,
            prefetch_window_seconds=0.01,
            minimum_hit_probability_numerator=3,
            minimum_hit_probability_denominator=4,
            max_logical_prefetch_bytes=8_000_000,
            max_estimated_transfer_energy_joules=1.0,
        )
        values.update(overrides)
        return PrefetchTransferPolicy(**values)

    def test_abstention_commutes_to_exact_zero_transfer_plan(self):
        receipt = admit_prefetch_transfers(
            prediction=self._prediction(),
            forecasts=(),
            policy=self._policy(),
            num_experts=256,
        )
        self.assertEqual(receipt.predicted_experts, ())
        self.assertEqual(receipt.admitted_experts, ())
        self.assertEqual(receipt.candidate_decisions, ())
        self.assertEqual(receipt.cold_predicted_logical_bytes, 0)
        self.assertEqual(receipt.cold_required_reuse_for_window, 0.0)
        self.assertEqual(receipt.admitted_logical_bytes, 0)
        self.assertEqual(receipt.admitted_logical_transfer_seconds, 0.0)
        self.assertEqual(receipt.admitted_expected_latency_margin_seconds, 0)
        self.assertEqual(receipt.admitted_estimated_energy_joules, 0.0)
        self.assertIs(receipt.physical_io_attested, False)
        self.assertIsNone(receipt.physical_prefetch_bytes)
        self.assertIs(receipt.transfer_effect_authorized, False)
        self.assertIs(receipt.g2_admitted, False)
        self.assertIs(receipt.native_route_mutated, False)
        self.assertIs(receipt.model_output_semantics_changed, False)

    def test_abstention_requires_empty_forecast_set(self):
        with self.assertRaisesRegex(ValueError, "FORECAST_SET_MUST_EQUAL_PREDICTED_EXPERT_SET"):
            admit_prefetch_transfers(
                prediction=self._prediction(),
                forecasts=(
                    CalibratedExpertForecast(
                        expert_id=3,
                        calibration_generation="cal:g3:v1",
                        hit_probability_numerator=9,
                        hit_probability_denominator=10,
                        expected_miss_stall_seconds=0.05,
                        logical_expert_bytes=1_000_000,
                        estimated_transfer_energy_joules=0.1,
                    ),
                ),
                policy=self._policy(),
                num_experts=256,
            )

    def test_abstention_still_requires_policy_layer_and_binding_identity(self):
        with self.assertRaisesRegex(ValueError, "PREDICTION_POLICY_LAYER_MISMATCH"):
            admit_prefetch_transfers(
                prediction=self._prediction(),
                forecasts=(),
                policy=self._policy(layer_id="layer:18"),
                num_experts=256,
            )
        with self.assertRaisesRegex(ValueError, "PREDICTION_POLICY_BINDING_MISMATCH"):
            admit_prefetch_transfers(
                prediction=self._prediction(),
                forecasts=(),
                policy=self._policy(binding_digest="binding:other"),
                num_experts=256,
            )

    def test_abstention_skips_speculation_but_demands_exact_native_route(self):
        prediction = self._prediction()
        native = NativeRoute(
            schema=NATIVE_ROUTE_SCHEMA,
            router_generation="native-router:g3:v1",
            layer_id=prediction.layer_id,
            binding_digest=prediction.binding_digest,
            top_k=2,
            selected_experts=(3, 11),
        )
        pager = _Pager(prediction.binding_digest)
        trace = stage_then_demand_load(
            pager=pager,
            prediction=prediction,
            native_route=native,
            num_experts=256,
            logical_bytes_by_expert={3: 1_000_000, 11: 1_000_000},
            model_revision="model:official-revision",
            index_digest="index:official-digest",
        )
        self.assertEqual(pager.calls, [((3, 11), "model:official-revision", "index:official-digest")])
        self.assertEqual(trace.predicted_experts, ())
        self.assertEqual(trace.prefetch_hits, ())
        self.assertEqual(trace.wasted_prefetches, ())
        self.assertEqual(trace.demand_misses, (3, 11))
        self.assertEqual(trace.executed_experts, (3, 11))
        self.assertEqual(trace.logical_prefetch_bytes, 0)
        self.assertEqual(trace.prediction_precision_numerator, 0)
        self.assertEqual(trace.prediction_precision_denominator, 0)
        self.assertIs(trace.physical_io_attested, False)

    def test_abstention_does_not_bypass_post_read_source_proof(self):
        prediction = self._prediction()
        native = NativeRoute(
            schema=NATIVE_ROUTE_SCHEMA,
            router_generation="native-router:g3:v1",
            layer_id=prediction.layer_id,
            binding_digest=prediction.binding_digest,
            top_k=1,
            selected_experts=(7,),
        )
        pager = _DishonestPager(prediction.binding_digest)
        with self.assertRaisesRegex(ValueError, "DEMAND_PAGER_RESULT_BINDING_MISMATCH"):
            stage_then_demand_load(
                pager=pager,
                prediction=prediction,
                native_route=native,
                num_experts=256,
                logical_bytes_by_expert={7: 1_000_000},
                model_revision="model:official-revision",
                index_digest="index:official-digest",
            )
        self.assertEqual(len(pager.calls), 1)

    def test_nonempty_g2_path_remains_unchanged(self):
        prediction = PrefetchPrediction(
            schema=PREFETCH_SCHEMA,
            predictor_generation="predictor:nonempty:v1",
            layer_id="layer:17",
            binding_digest="binding:official-source",
            predicted_experts=(5,),
        )
        receipt = admit_prefetch_transfers(
            prediction=prediction,
            forecasts=(
                CalibratedExpertForecast(
                    expert_id=5,
                    calibration_generation="cal:g3:v1",
                    hit_probability_numerator=9,
                    hit_probability_denominator=10,
                    expected_miss_stall_seconds=0.05,
                    logical_expert_bytes=1_000_000,
                    estimated_transfer_energy_joules=0.1,
                ),
            ),
            policy=self._policy(),
            num_experts=256,
        )
        self.assertEqual(receipt.admitted_experts, (5,))
        self.assertGreater(receipt.cold_predicted_logical_bytes, 0)
        self.assertGreaterEqual(receipt.cold_required_reuse_for_window, 0.0)
        self.assertIs(receipt.transfer_effect_authorized, False)
        self.assertIs(receipt.g2_admitted, False)


if __name__ == "__main__":
    unittest.main()
