from __future__ import annotations

from dataclasses import dataclass
import unittest

from tools.awj032.glm53_router_separated_prefetch import (
    NATIVE_ROUTE_SCHEMA,
    PREFETCH_SCHEMA,
    NativeRoute,
    PrefetchPrediction,
)
from tools.awj032.glm53_router_separated_prefetch_source_guard import (
    stage_then_demand_load_source_bound,
)

NUM_EXPERTS = 16
BINDING = "binding:glm53:layer-7:index-rev"
REVISION = "glm53-rev"
INDEX = "index-digest"
BYTES = {i: 100 + i for i in range(NUM_EXPERTS)}


def prediction(ids=(1, 3, 5, 7), *, binding=BINDING, layer="layer-7"):
    return PrefetchPrediction(
        schema=PREFETCH_SCHEMA,
        predictor_generation="predictor-v1",
        layer_id=layer,
        binding_digest=binding,
        predicted_experts=tuple(ids),
    )


def route(ids=(1, 3, 5, 9), *, binding=BINDING, layer="layer-7"):
    return NativeRoute(
        schema=NATIVE_ROUTE_SCHEMA,
        router_generation="native-glm-router-v1",
        layer_id=layer,
        binding_digest=binding,
        top_k=len(tuple(ids)),
        selected_experts=tuple(ids),
    )


@dataclass(frozen=True)
class FakeBinding:
    digest: str = BINDING
    layer_id: str = "layer-7"
    num_experts: int = NUM_EXPERTS
    model_revision: str = REVISION
    index_digest: str = INDEX


@dataclass(frozen=True)
class FakePage:
    expert_ids: tuple[int, ...]
    binding_digest: str


class FakePager:
    def __init__(self, *, binding=None, returned_binding=None, returned_experts=None):
        self.binding = binding or FakeBinding()
        self.returned_binding = returned_binding
        self.returned_experts = returned_experts
        self.calls = []

    def load_selected(self, expert_ids, *, model_revision, index_digest):
        ids = tuple(expert_ids)
        self.calls.append((ids, model_revision, index_digest))
        return FakePage(
            expert_ids=ids if self.returned_experts is None else tuple(self.returned_experts),
            binding_digest=self.binding.digest if self.returned_binding is None else self.returned_binding,
        )


class SourceBoundPrefetchGuardTests(unittest.TestCase):
    def run_guard(self, pager=None, *, p=None, r=None, revision=REVISION, index=INDEX):
        return stage_then_demand_load_source_bound(
            pager=pager or FakePager(),
            prediction=p or prediction(),
            native_route=r or route(),
            num_experts=NUM_EXPERTS,
            logical_bytes_by_expert=BYTES,
            model_revision=revision,
            index_digest=index,
        )

    def test_exact_source_binding_preserves_prediction_then_demand_order(self):
        pager = FakePager()
        trace = self.run_guard(pager)
        self.assertEqual([call[0] for call in pager.calls], [(1, 3, 5, 7), (9,)])
        self.assertEqual(trace.executed_experts, (1, 3, 5, 9))
        self.assertFalse(trace.routing_mutated_by_predictor)
        self.assertFalse(trace.execution_authorized)

    def test_concrete_pager_binding_digest_mismatch_fails_before_any_read(self):
        pager = FakePager(binding=FakeBinding(digest="other-binding"))
        with self.assertRaisesRegex(ValueError, "PAGER_BINDING_DIGEST_MISMATCH"):
            self.run_guard(pager)
        self.assertEqual(pager.calls, [])

    def test_pager_layer_or_num_experts_mismatch_fails_before_read(self):
        for binding, reason in (
            (FakeBinding(layer_id="layer-8"), "PAGER_LAYER_ID_MISMATCH"),
            (FakeBinding(num_experts=32), "PAGER_NUM_EXPERTS_MISMATCH"),
        ):
            with self.subTest(reason=reason):
                pager = FakePager(binding=binding)
                with self.assertRaisesRegex(ValueError, reason):
                    self.run_guard(pager)
                self.assertEqual(pager.calls, [])

    def test_call_revision_and_index_must_equal_immutable_pager_source(self):
        pager = FakePager()
        with self.assertRaisesRegex(ValueError, "PAGER_MODEL_REVISION_ARGUMENT_MISMATCH"):
            self.run_guard(pager, revision="other-rev")
        self.assertEqual(pager.calls, [])

        pager = FakePager()
        with self.assertRaisesRegex(ValueError, "PAGER_INDEX_DIGEST_ARGUMENT_MISMATCH"):
            self.run_guard(pager, index="other-index")
        self.assertEqual(pager.calls, [])

    def test_returned_page_binding_cross_cast_is_rejected(self):
        pager = FakePager(returned_binding="wrong-source")
        with self.assertRaisesRegex(ValueError, "RETURNED_PAGE_BINDING_DIGEST_MISMATCH"):
            self.run_guard(pager)
        self.assertEqual(len(pager.calls), 1)

    def test_returned_page_expert_cross_cast_is_rejected(self):
        pager = FakePager(returned_experts=(1, 3, 5, 9))
        with self.assertRaisesRegex(ValueError, "RETURNED_PAGE_EXPERT_SET_MISMATCH"):
            self.run_guard(pager)
        self.assertEqual(len(pager.calls), 1)

    def test_prediction_and_native_route_still_must_commute(self):
        with self.assertRaisesRegex(ValueError, "PREFETCH_NATIVE_SOURCE_BINDING_MISMATCH"):
            self.run_guard(p=prediction(binding="A"), r=route(binding="B"))

    def test_source_guard_never_promotes_effect_authority(self):
        trace = self.run_guard()
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
            self.assertIs(getattr(trace, field), False, field)


if __name__ == "__main__":
    unittest.main()
