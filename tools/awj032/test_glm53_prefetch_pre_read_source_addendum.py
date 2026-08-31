from __future__ import annotations

from dataclasses import dataclass
import unittest

from tools.awj032.glm53_router_separated_prefetch import (
    NATIVE_ROUTE_SCHEMA,
    PREFETCH_SCHEMA,
    NativeRoute,
    PrefetchPrediction,
)
from tools.awj032.glm53_prefetch_pre_read_source_addendum import (
    stage_then_demand_load_prebound,
)

NUM_EXPERTS = 16
BINDING = "binding:glm53:layer-7:index-rev"
REVISION = "glm53-rev"
INDEX = "index-digest"
BYTES = {i: 100 + i for i in range(NUM_EXPERTS)}


def prediction(binding=BINDING):
    return PrefetchPrediction(
        schema=PREFETCH_SCHEMA,
        predictor_generation="predictor-v1",
        layer_id="layer-7",
        binding_digest=binding,
        predicted_experts=(1, 3, 5, 7),
    )


def route(binding=BINDING):
    return NativeRoute(
        schema=NATIVE_ROUTE_SCHEMA,
        router_generation="native-router-v1",
        layer_id="layer-7",
        binding_digest=binding,
        top_k=4,
        selected_experts=(1, 3, 5, 9),
    )


@dataclass(frozen=True)
class Binding:
    digest: str = BINDING
    layer_id: str = "layer-7"
    num_experts: int = NUM_EXPERTS
    model_revision: str = REVISION
    index_digest: str = INDEX


@dataclass(frozen=True)
class Page:
    binding_digest: str
    expert_ids: tuple[int, ...]


class Pager:
    def __init__(self, binding=None):
        self.binding = binding or Binding()
        self.calls = []

    def load_selected(self, expert_ids, *, model_revision, index_digest):
        ids = tuple(expert_ids)
        self.calls.append((ids, model_revision, index_digest))
        return Page(binding_digest=self.binding.digest, expert_ids=ids)


class PreReadSourceAddendumTests(unittest.TestCase):
    def run(self, pager=None, *, p=None, r=None, revision=REVISION, index=INDEX):
        return stage_then_demand_load_prebound(
            pager=pager or Pager(),
            prediction=p or prediction(),
            native_route=r or route(),
            num_experts=NUM_EXPERTS,
            logical_bytes_by_expert=BYTES,
            model_revision=revision,
            index_digest=index,
        )

    def test_exact_concrete_source_delegates_to_canonical_post_read_owner(self):
        pager = Pager()
        trace = self.run(pager)
        self.assertEqual([x[0] for x in pager.calls], [(1, 3, 5, 7), (9,)])
        self.assertEqual(trace.executed_experts, (1, 3, 5, 9))
        self.assertFalse(trace.execution_authorized)

    def test_wrong_concrete_binding_fails_before_any_read(self):
        pager = Pager(Binding(digest="wrong-binding"))
        with self.assertRaisesRegex(ValueError, "PREFETCH_CONCRETE_PAGER_BINDING_MISMATCH"):
            self.run(pager)
        self.assertEqual(pager.calls, [])

    def test_wrong_layer_or_expert_count_fails_before_any_read(self):
        for binding, reason in (
            (Binding(layer_id="layer-8"), "PREFETCH_CONCRETE_PAGER_LAYER_MISMATCH"),
            (Binding(num_experts=32), "PREFETCH_CONCRETE_PAGER_NUM_EXPERTS_MISMATCH"),
        ):
            with self.subTest(reason=reason):
                pager = Pager(binding)
                with self.assertRaisesRegex(ValueError, reason):
                    self.run(pager)
                self.assertEqual(pager.calls, [])

    def test_wrong_revision_or_index_argument_fails_before_any_read(self):
        pager = Pager()
        with self.assertRaisesRegex(ValueError, "PREFETCH_CALL_REVISION_NOT_PAGER_REVISION"):
            self.run(pager, revision="other-revision")
        self.assertEqual(pager.calls, [])

        pager = Pager()
        with self.assertRaisesRegex(ValueError, "PREFETCH_CALL_INDEX_NOT_PAGER_INDEX"):
            self.run(pager, index="other-index")
        self.assertEqual(pager.calls, [])

    def test_prediction_route_mismatch_still_fails_before_any_read(self):
        pager = Pager()
        with self.assertRaisesRegex(ValueError, "PREFETCH_NATIVE_SOURCE_BINDING_MISMATCH"):
            self.run(pager, p=prediction("A"), r=route("B"))
        self.assertEqual(pager.calls, [])

    def test_claim_ceiling_remains_nonpromoting(self):
        trace = self.run()
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
