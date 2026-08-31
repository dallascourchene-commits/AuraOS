from dataclasses import replace
import unittest

from tools.awj032.glm53_packed_expert_pager import (
    BACKEND_IO_ATTESTATION_SCHEMA,
    ExpertSourceBinding,
    PackedExpertPager,
    PagerReceipt,
)
from tools.awj032.glm53_speculative_prefetch_accounting import (
    PrefetchAccountingError,
    account_speculative_prefetch,
)


class FakeBackend:
    def __init__(self, *, attested=False):
        self.tensors = {
            "gate_up": tuple(range(8)),
            "down": tuple(range(100, 108)),
        }
        self.reads = []
        self.attested = attested

    def read_rows(self, key, start, end):
        self.reads.append((key, start, end))
        return self.tensors[key][start:end]

    def io_attestation(self, binding_digest):
        if not self.attested:
            return None
        return {
            "schema": BACKEND_IO_ATTESTATION_SCHEMA,
            "binding_digest": binding_digest,
            "attestation_id": "synthetic-selected-only",
            "physical_selected_only": True,
            "whole_bank_reads": 0,
            "whole_bank_materialized": False,
        }


def binding(layer="model.layers.7.mlp.experts"):
    return ExpertSourceBinding(
        model_revision="glm53-rev-exact",
        index_digest="weight-index-exact",
        layer_id=layer,
        num_experts=8,
        tensor_map={"gate_up": "gate_up", "down": "down"},
        scale_map={},
        representation="GROUPED_EXPERT_TEST",
    )


def staged(predicted=(1, 3, 4), *, source=None, attested=False):
    source = source or binding()
    pager = PackedExpertPager(source, FakeBackend(attested=attested))
    pager.load_selected(
        predicted,
        model_revision=source.model_revision,
        index_digest=source.index_digest,
    )
    return source, pager.receipt()


class RouterSeparatedPrefetchAccountingTests(unittest.TestCase):
    def test_hit_waste_and_demand_load_sets_are_exact(self):
        source, prefetch = staged((1, 3, 4))
        out = account_speculative_prefetch(
            binding=source,
            predicted_expert_ids=(4, 3, 1, 3),
            native_route_expert_ids=(5, 4, 3),
            prefetch_receipt=prefetch,
        )
        self.assertEqual(out.predicted_experts, (1, 3, 4))
        self.assertEqual(out.native_route_experts, (3, 4, 5))
        self.assertEqual(out.useful_prefetch_experts, (3, 4))
        self.assertEqual(out.wasted_prefetch_experts, (1,))
        self.assertEqual(out.demand_load_experts, (5,))
        self.assertEqual(out.prediction_precision_ppm, 666666)
        self.assertEqual(out.native_route_coverage_ppm, 666666)
        self.assertTrue(out.demand_load_required_for_misses)
        self.assertFalse(out.demand_load_observed)

    def test_prediction_never_changes_native_route(self):
        first_source, first_prefetch = staged((1, 2))
        second_source, second_prefetch = staged((3, 4), source=first_source)
        route = (5, 6)
        first = account_speculative_prefetch(
            binding=first_source,
            predicted_expert_ids=(1, 2),
            native_route_expert_ids=route,
            prefetch_receipt=first_prefetch,
        )
        second = account_speculative_prefetch(
            binding=second_source,
            predicted_expert_ids=(3, 4),
            native_route_expert_ids=route,
            prefetch_receipt=second_prefetch,
        )
        self.assertEqual(first.native_route_experts, (5, 6))
        self.assertEqual(second.native_route_experts, (5, 6))
        self.assertFalse(first.prediction_can_change_native_route)
        self.assertFalse(second.prediction_can_change_native_route)
        self.assertEqual(first.demand_load_experts, (5, 6))
        self.assertEqual(second.demand_load_experts, (5, 6))

    def test_full_bank_prediction_is_forbidden(self):
        source = binding()
        forged = PagerReceipt(
            schema="AuraPackedExpertPagerReceiptV1",
            binding_digest=source.digest,
            layer_id=source.layer_id,
            selected_experts=tuple(range(8)),
            contiguous_runs=((0, 8),),
            read_count=2,
            logical_bounded_row_requests=True,
            physical_io_attested=False,
            physical_selected_only=None,
            whole_tensor_reads=None,
            whole_bank_materialized=None,
            backend_attestation_id=None,
        )
        with self.assertRaisesRegex(PrefetchAccountingError, "FULL_EXPERT_BANK"):
            account_speculative_prefetch(
                binding=source,
                predicted_expert_ids=tuple(range(8)),
                native_route_expert_ids=(1, 2),
                prefetch_receipt=forged,
            )

    def test_prefetch_receipt_must_match_source_and_staged_set(self):
        source, prefetch = staged((1, 2))
        other = binding("model.layers.8.mlp.experts")
        with self.assertRaisesRegex(PrefetchAccountingError, "SOURCE_BINDING_MISMATCH"):
            account_speculative_prefetch(
                binding=other,
                predicted_expert_ids=(1, 2),
                native_route_expert_ids=(1, 2),
                prefetch_receipt=prefetch,
            )
        forged = replace(prefetch, selected_experts=(1, 3))
        with self.assertRaisesRegex(PrefetchAccountingError, "STAGED_EXPERT_SET_MISMATCH"):
            account_speculative_prefetch(
                binding=source,
                predicted_expert_ids=(1, 2),
                native_route_expert_ids=(1, 2),
                prefetch_receipt=forged,
            )

    def test_physical_bytes_stay_unknown_without_byte_attestation(self):
        source, prefetch = staged((1, 2))
        out = account_speculative_prefetch(
            binding=source,
            predicted_expert_ids=(1, 2),
            native_route_expert_ids=(1, 2),
            prefetch_receipt=prefetch,
        )
        self.assertFalse(out.physical_io_attested)
        self.assertIsNone(out.physical_selected_only)
        self.assertIsNone(out.physical_bytes_read)

    def test_selected_only_attestation_still_does_not_invent_byte_count(self):
        source, prefetch = staged((1, 2), attested=True)
        out = account_speculative_prefetch(
            binding=source,
            predicted_expert_ids=(1, 2),
            native_route_expert_ids=(1, 2),
            prefetch_receipt=prefetch,
        )
        self.assertTrue(out.physical_io_attested)
        self.assertTrue(out.physical_selected_only)
        self.assertEqual(out.whole_bank_reads, 0)
        self.assertFalse(out.whole_bank_materialized)
        self.assertIsNone(out.physical_bytes_read)

    def test_claim_ceiling_and_digest_are_deterministic(self):
        source, prefetch = staged((1, 2))
        kwargs = dict(
            binding=source,
            predicted_expert_ids=(2, 1),
            native_route_expert_ids=(2, 3),
            prefetch_receipt=prefetch,
        )
        first = account_speculative_prefetch(**kwargs)
        second = account_speculative_prefetch(**kwargs)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertFalse(first.execution_authorized)
        self.assertFalse(first.provider_effect_authorized)
        self.assertFalse(first.g2_admitted)
        self.assertFalse(first.semantic_k27_authority)
        self.assertFalse(first.native_private_transformer_kv_accessed)


if __name__ == "__main__":
    unittest.main()
