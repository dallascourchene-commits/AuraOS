from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_router_separated_prefetch import (
    IO_SCHEMA,
    NATIVE_ROUTE_SCHEMA,
    PREFETCH_SCHEMA,
    NativeRoute,
    PhysicalIOAttestation,
    PrefetchPrediction,
    build_prefetch_trace,
    stage_then_demand_load,
)

NUM_EXPERTS = 16
BINDING = "binding:glm53:layer-7:index-rev"
BYTES = {i: 100 + i for i in range(NUM_EXPERTS)}


def prediction(ids=(1, 3, 5, 7), **overrides):
    base = PrefetchPrediction(
        schema=PREFETCH_SCHEMA,
        predictor_generation="predictor-v1",
        layer_id="layer-7",
        binding_digest=BINDING,
        predicted_experts=tuple(ids),
    )
    return replace(base, **overrides)


def route(ids=(1, 3, 5, 9), **overrides):
    base = NativeRoute(
        schema=NATIVE_ROUTE_SCHEMA,
        router_generation="native-glm-router-v1",
        layer_id="layer-7",
        binding_digest=BINDING,
        top_k=len(tuple(ids)),
        selected_experts=tuple(ids),
    )
    return replace(base, **overrides)


class FakePager:
    def __init__(self):
        self.calls = []

    def load_selected(self, expert_ids, *, model_revision, index_digest):
        self.calls.append((tuple(expert_ids), model_revision, index_digest))
        return {"loaded": tuple(expert_ids)}


class RouterSeparatedPrefetchTests(unittest.TestCase):
    def test_partial_prediction_demand_loads_miss_without_route_mutation(self):
        p = prediction((1, 3, 5, 7))
        r = route((1, 3, 5, 9))
        out = build_prefetch_trace(
            prediction=p, native_route=r, num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        self.assertEqual(out.prefetch_hits, (1, 3, 5))
        self.assertEqual(out.demand_misses, (9,))
        self.assertEqual(out.wasted_prefetches, (7,))
        self.assertEqual(out.executed_experts, r.selected_experts)
        self.assertFalse(out.routing_mutated_by_predictor)
        self.assertFalse(out.output_semantics_changed_by_prediction)
        self.assertFalse(out.physical_io_attested)
        self.assertIsNone(out.physical_total_bytes)

    def test_stage_then_demand_load_calls_prediction_then_only_native_misses(self):
        pager = FakePager()
        p = prediction((1, 3, 5, 7))
        r = route((1, 3, 5, 9))
        out = stage_then_demand_load(
            pager=pager,
            prediction=p,
            native_route=r,
            num_experts=NUM_EXPERTS,
            logical_bytes_by_expert=BYTES,
            model_revision="glm53-rev",
            index_digest="index-digest",
        )
        self.assertEqual([c[0] for c in pager.calls], [(1, 3, 5, 7), (9,)])
        self.assertEqual(out.executed_experts, (1, 3, 5, 9))

    def test_perfect_prediction_has_no_demand_or_waste(self):
        p = prediction((1, 3, 5, 9))
        r = route((1, 3, 5, 9))
        out = build_prefetch_trace(
            prediction=p, native_route=r, num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        self.assertEqual(out.demand_misses, ())
        self.assertEqual(out.wasted_prefetches, ())
        self.assertEqual(out.prediction_recall_numerator, 4)
        self.assertEqual(out.prediction_recall_denominator, 4)
        self.assertEqual(out.logical_demand_bytes, 0)

    def test_extra_predictions_are_waste_not_execution(self):
        p = prediction((1, 2, 3, 4, 5, 9))
        r = route((1, 3, 5, 9))
        out = build_prefetch_trace(
            prediction=p, native_route=r, num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        self.assertEqual(out.wasted_prefetches, (2, 4))
        self.assertEqual(out.executed_experts, (1, 3, 5, 9))
        self.assertEqual(out.logical_wasted_prefetch_bytes, BYTES[2] + BYTES[4])

    def test_predictor_cannot_change_native_route_by_label(self):
        a = build_prefetch_trace(
            prediction=prediction((1, 3, 5, 7)),
            native_route=route((1, 3, 5, 9)),
            num_experts=NUM_EXPERTS,
            logical_bytes_by_expert=BYTES,
        )
        b = build_prefetch_trace(
            prediction=prediction((0, 2, 4, 6)),
            native_route=route((1, 3, 5, 9)),
            num_experts=NUM_EXPERTS,
            logical_bytes_by_expert=BYTES,
        )
        self.assertEqual(a.executed_experts, b.executed_experts)
        self.assertNotEqual(a.prediction_digest, b.prediction_digest)

    def test_layer_and_source_binding_mismatch_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "PREFETCH_NATIVE_LAYER_MISMATCH"):
            build_prefetch_trace(
                prediction=prediction(),
                native_route=route(layer_id="layer-8"),
                num_experts=NUM_EXPERTS,
                logical_bytes_by_expert=BYTES,
            )
        with self.assertRaisesRegex(ValueError, "PREFETCH_NATIVE_SOURCE_BINDING_MISMATCH"):
            build_prefetch_trace(
                prediction=prediction(),
                native_route=route(binding_digest="other-binding"),
                num_experts=NUM_EXPERTS,
                logical_bytes_by_expert=BYTES,
            )

    def test_noncanonical_duplicate_or_out_of_range_predictions_reject(self):
        for ids in ((3, 1), (1, 1), (1, 99)):
            with self.subTest(ids=ids):
                with self.assertRaises(Exception):
                    build_prefetch_trace(
                        prediction=prediction(ids),
                        native_route=route(),
                        num_experts=NUM_EXPERTS,
                        logical_bytes_by_expert=BYTES,
                    )

    def test_native_top_k_mismatch_rejects(self):
        with self.assertRaisesRegex(ValueError, "NATIVE_ROUTE_TOP_K_MISMATCH"):
            build_prefetch_trace(
                prediction=prediction(),
                native_route=route(top_k=8),
                num_experts=NUM_EXPERTS,
                logical_bytes_by_expert=BYTES,
            )

    def test_logical_bytes_never_self_mint_physical_bytes(self):
        out = build_prefetch_trace(
            prediction=prediction(), native_route=route(), num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        self.assertGreater(out.logical_prefetch_bytes, 0)
        self.assertFalse(out.physical_io_attested)
        self.assertIsNone(out.physical_prefetch_bytes)
        self.assertIsNone(out.physical_demand_bytes)
        self.assertIsNone(out.physical_total_bytes)

    def test_syntactically_valid_caller_physical_attestation_cannot_fill_physical_plane(self):
        p = prediction()
        r = route()
        base = build_prefetch_trace(
            prediction=p, native_route=r, num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        io = PhysicalIOAttestation(
            schema=IO_SCHEMA,
            binding_digest=BINDING,
            prediction_digest=p.digest,
            native_route_digest=r.digest,
            prefetch_experts=p.predicted_experts,
            demand_experts=base.demand_misses,
            physical_prefetch_bytes=4096,
            physical_demand_bytes=2048,
            attestation_id="caller-claimed",
        )
        with self.assertRaisesRegex(ValueError, "CALLER_PHYSICAL_IO_ATTESTATION_FORBIDDEN"):
            build_prefetch_trace(
                prediction=p,
                native_route=r,
                num_experts=NUM_EXPERTS,
                logical_bytes_by_expert=BYTES,
                physical_io=io,
            )

    def test_even_exact_structural_physical_attestation_is_not_g1_authority(self):
        p = prediction()
        r = route()
        base = build_prefetch_trace(
            prediction=p, native_route=r, num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        io = PhysicalIOAttestation(
            schema=IO_SCHEMA,
            binding_digest=BINDING,
            prediction_digest=p.digest,
            native_route_digest=r.digest,
            prefetch_experts=p.predicted_experts,
            demand_experts=base.demand_misses,
            physical_prefetch_bytes=1,
            physical_demand_bytes=2,
            attestation_id="perfectly-bound-but-untrusted",
        )
        io.validate()
        with self.assertRaisesRegex(ValueError, "CALLER_PHYSICAL_IO_ATTESTATION_FORBIDDEN"):
            build_prefetch_trace(
                prediction=p, native_route=r, num_experts=NUM_EXPERTS,
                logical_bytes_by_expert=BYTES, physical_io=io,
            )

    def test_forged_trace_cannot_self_promote_physical_plane(self):
        out = build_prefetch_trace(
            prediction=prediction(), native_route=route(), num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        forged = replace(
            out,
            physical_io_attested=True,
            physical_prefetch_bytes=100,
            physical_demand_bytes=20,
            physical_total_bytes=120,
            io_attestation_id="caller-claimed",
        )
        with self.assertRaisesRegex(ValueError, "G1_PHYSICAL_IO_MUST_REMAIN_DELEGATED"):
            forged.validate_claim_ceiling()

    def test_prediction_and_route_identity_are_order_canonical_not_process_identity(self):
        p = prediction((1, 3, 5, 7))
        r = route((1, 3, 5, 9))
        a = build_prefetch_trace(
            prediction=p, native_route=r, num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        b = build_prefetch_trace(
            prediction=p, native_route=r, num_experts=NUM_EXPERTS, logical_bytes_by_expert=dict(reversed(list(BYTES.items())))
        )
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_claim_ceiling_stays_false(self):
        out = build_prefetch_trace(
            prediction=prediction(), native_route=route(), num_experts=NUM_EXPERTS, logical_bytes_by_expert=BYTES
        )
        self.assertFalse(out.physical_io_attested)
        for field in (
            "routing_mutated_by_predictor",
            "output_semantics_changed_by_prediction",
            "g2_admitted",
            "execution_authorized",
            "provider_effect_authorized",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect",
        ):
            self.assertIs(getattr(out, field), False, field)


if __name__ == "__main__":
    unittest.main()
