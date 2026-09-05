import itertools
import unittest
from dataclasses import replace

from fused_route_event_contract import *


class FusedRouteContractTests(unittest.TestCase):
    def setUp(self):
        self.trace = generate_trace(tokens=4, layers=3, experts_per_layer=16, top_k=2, seed=7)
        self.flat = list(flatten_atomic_trace(self.trace))

    def test_valid_roundtrip(self):
        r = verify_atomic_roundtrip(self.trace, self.flat)
        self.assertTrue(r.atomic_semantics_preserved)
        self.assertEqual(r.original_event_root, r.reconstructed_event_root)
        self.assertFalse(r.effect_authority)
        self.assertFalse(r.gate10)

    def test_receipt_deterministic(self):
        self.assertEqual(verify_atomic_roundtrip(self.trace, self.flat).root, verify_atomic_roundtrip(self.trace, self.flat).root)

    def test_lossy_expert_only_stream_never_admitted(self):
        self.assertFalse(lossy_stream_is_admissible(naive_expert_only_flatten(self.trace)))

    def test_missing_access_rejected(self):
        with self.assertRaisesRegex(FusedRouteError, "INCOMPLETE_FLAT_ACCESS_STREAM"):
            reconstruct_atomic_trace(self.flat[:-1], tokens=4, layers=3, experts_per_layer=16, top_k=2)

    def test_event_boundary_loss_rejected(self):
        x = self.flat.copy(); x[2] = replace(x[2], event_sequence=1)
        with self.assertRaisesRegex(FusedRouteError, "EVENT_GROUP_BOUNDARY_LOST"):
            reconstruct_atomic_trace(x, tokens=4, layers=3, experts_per_layer=16, top_k=2)

    def test_member_order_loss_rejected(self):
        x = self.flat.copy(); x[0], x[1] = x[1], x[0]
        with self.assertRaisesRegex(FusedRouteError, "MEMBER_ORDER_LOST"):
            reconstruct_atomic_trace(x, tokens=4, layers=3, experts_per_layer=16, top_k=2)

    def test_group_size_mismatch_rejected(self):
        x = self.flat.copy(); x[0] = replace(x[0], group_size=3)
        with self.assertRaisesRegex(FusedRouteError, "GROUP_SIZE_MISMATCH"):
            reconstruct_atomic_trace(x, tokens=4, layers=3, experts_per_layer=16, top_k=2)

    def test_token_mismatch_rejected(self):
        x = self.flat.copy(); x[0] = replace(x[0], token=99)
        with self.assertRaisesRegex(FusedRouteError, "TOKEN_LAYER_GROUP_MISMATCH"):
            reconstruct_atomic_trace(x, tokens=4, layers=3, experts_per_layer=16, top_k=2)

    def test_layer_mismatch_rejected(self):
        x = self.flat.copy(); x[0] = replace(x[0], layer=2)
        with self.assertRaisesRegex(FusedRouteError, "TOKEN_LAYER_GROUP_MISMATCH"):
            reconstruct_atomic_trace(x, tokens=4, layers=3, experts_per_layer=16, top_k=2)

    def test_duplicate_expert_in_event_rejected(self):
        x = self.flat.copy(); x[1] = replace(x[1], expert=x[0].expert)
        with self.assertRaisesRegex(FusedRouteError, "DUPLICATE_NATIVE_EXPERT"):
            reconstruct_atomic_trace(x, tokens=4, layers=3, experts_per_layer=16, top_k=2)

    def test_expert_out_of_range_rejected(self):
        x = self.flat.copy(); x[0] = replace(x[0], expert=99)
        with self.assertRaisesRegex(FusedRouteError, "NATIVE_EXPERT_OUT_OF_RANGE"):
            reconstruct_atomic_trace(x, tokens=4, layers=3, experts_per_layer=16, top_k=2)

    def test_trace_sequence_gap_rejected(self):
        events = list(self.trace.events); events[2] = replace(events[2], sequence=99)
        bad = AtomicTrace(tuple(events), 4, 3, 16, 2)
        with self.assertRaisesRegex(FusedRouteError, "NON_CONTIGUOUS_EVENT_SEQUENCE"):
            bad.validate()

    def test_trace_grid_mismatch_rejected(self):
        events = list(self.trace.events); events[2] = replace(events[2], layer=0)
        bad = AtomicTrace(tuple(events), 4, 3, 16, 2)
        with self.assertRaisesRegex(FusedRouteError, "NON_CANONICAL_TOKEN_LAYER_GRID"):
            bad.validate()

    def test_incomplete_event_grid_rejected(self):
        bad = AtomicTrace(self.trace.events[:-1], 4, 3, 16, 2)
        with self.assertRaisesRegex(FusedRouteError, "INCOMPLETE_EVENT_GRID"):
            bad.validate()

    def test_topk_exceeds_experts_rejected(self):
        with self.assertRaisesRegex(FusedRouteError, "TOPK_EXCEEDS_EXPERTS"):
            AtomicTrace(tuple(), 1, 1, 1, 2).validate()

    def test_flat_root_changes_on_order(self):
        x = self.flat.copy(); x[0], x[1] = x[1], x[0]
        self.assertNotEqual(flat_access_root(self.flat), flat_access_root(x))

    def test_event_root_changes_on_router_choice(self):
        events = list(self.trace.events)
        current = events[0].native_experts
        replacement = tuple(x for x in range(16) if x not in current)[:2]
        mutated = AtomicTrace((replace(events[0], native_experts=replacement), *events[1:]), 4, 3, 16, 2)
        self.assertNotEqual(self.trace.root, mutated.root)

    def test_flatten_preserves_membership_fields(self):
        first = self.flat[:2]
        self.assertEqual([x.event_sequence for x in first], [1, 1])
        self.assertEqual([x.member_index for x in first], [0, 1])
        self.assertEqual([x.group_size for x in first], [2, 2])

    def test_omega8_hard_invalid_dominance(self):
        for i in range(8):
            state = [1] * 8; state[i] = 0
            self.assertFalse(crystalline_admission(state))

    def test_omega8_effect_axis_nonpromoting(self):
        self.assertTrue(crystalline_admission([1] * 8))
        self.assertFalse(crystalline_admission([1] * 7 + [2]))

    def test_omega8_exhaustive_count(self):
        self.assertEqual(sum(crystalline_admission(x) for x in itertools.product((0,1,2), repeat=8)), 128)


if __name__ == "__main__":
    unittest.main()
