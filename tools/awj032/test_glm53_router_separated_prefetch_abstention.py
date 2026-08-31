from __future__ import annotations

import unittest

from tools.awj032.glm53_router_separated_prefetch import (
    NATIVE_ROUTE_SCHEMA,
    PREFETCH_SCHEMA,
    NativeRoute,
    PrefetchPrediction,
    build_prefetch_trace,
    stage_then_demand_load,
)

NUM_EXPERTS = 16
BINDING = "binding:glm53:layer-7:index-rev"
BYTES = {i: 100 + i for i in range(NUM_EXPERTS)}


def abstain() -> PrefetchPrediction:
    return PrefetchPrediction(
        schema=PREFETCH_SCHEMA,
        predictor_generation="predictor-abstain-v1",
        layer_id="layer-7",
        binding_digest=BINDING,
        predicted_experts=(),
    )


def route(ids=(1, 3, 5, 9)) -> NativeRoute:
    return NativeRoute(
        schema=NATIVE_ROUTE_SCHEMA,
        router_generation="native-glm-router-v1",
        layer_id="layer-7",
        binding_digest=BINDING,
        top_k=len(ids),
        selected_experts=tuple(ids),
    )


class FakePager:
    def __init__(self):
        self.calls = []

    def load_selected(self, expert_ids, *, model_revision, index_digest):
        self.calls.append((tuple(expert_ids), model_revision, index_digest))
        return {"loaded": tuple(expert_ids)}


class PrefetchAbstentionW3Tests(unittest.TestCase):
    def test_predictor_may_abstain_without_mutating_native_execution(self):
        native = route()
        out = build_prefetch_trace(
            prediction=abstain(),
            native_route=native,
            num_experts=NUM_EXPERTS,
            logical_bytes_by_expert=BYTES,
        )
        self.assertEqual(out.predicted_experts, ())
        self.assertEqual(out.prefetch_hits, ())
        self.assertEqual(out.wasted_prefetches, ())
        self.assertEqual(out.demand_misses, native.selected_experts)
        self.assertEqual(out.executed_experts, native.selected_experts)
        self.assertEqual(out.logical_prefetch_bytes, 0)
        self.assertEqual(out.logical_wasted_prefetch_bytes, 0)
        self.assertEqual(out.logical_demand_bytes, out.logical_native_required_bytes)
        self.assertEqual(out.prediction_recall_numerator, 0)
        self.assertEqual(out.prediction_recall_denominator, native.top_k)
        self.assertEqual(out.prediction_precision_numerator, 0)
        self.assertEqual(out.prediction_precision_denominator, 0)
        self.assertFalse(out.routing_mutated_by_predictor)
        self.assertFalse(out.output_semantics_changed_by_prediction)
        self.assertFalse(out.physical_io_attested)
        self.assertIsNone(out.physical_total_bytes)

    def test_abstention_skips_speculative_load_then_demands_exact_native_route(self):
        pager = FakePager()
        native = route()
        out = stage_then_demand_load(
            pager=pager,
            prediction=abstain(),
            native_route=native,
            num_experts=NUM_EXPERTS,
            logical_bytes_by_expert=BYTES,
            model_revision="glm53-rev",
            index_digest="index-digest",
        )
        self.assertEqual([call[0] for call in pager.calls], [native.selected_experts])
        self.assertEqual(out.demand_misses, native.selected_experts)
        self.assertEqual(out.executed_experts, native.selected_experts)

    def test_native_route_may_not_abstain(self):
        native = NativeRoute(
            schema=NATIVE_ROUTE_SCHEMA,
            router_generation="native-glm-router-v1",
            layer_id="layer-7",
            binding_digest=BINDING,
            top_k=1,
            selected_experts=(),
        )
        with self.assertRaises(Exception):
            build_prefetch_trace(
                prediction=abstain(),
                native_route=native,
                num_experts=NUM_EXPERTS,
                logical_bytes_by_expert=BYTES,
            )

    def test_empty_prediction_does_not_self_mint_physical_savings(self):
        out = build_prefetch_trace(
            prediction=abstain(),
            native_route=route(),
            num_experts=NUM_EXPERTS,
            logical_bytes_by_expert=BYTES,
        )
        self.assertEqual(out.logical_prefetch_bytes, 0)
        self.assertFalse(out.physical_io_attested)
        self.assertIsNone(out.physical_prefetch_bytes)
        self.assertIsNone(out.physical_demand_bytes)
        self.assertIsNone(out.physical_total_bytes)


if __name__ == "__main__":
    unittest.main()
