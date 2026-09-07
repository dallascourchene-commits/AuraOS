import itertools
import random
import unittest

from tools.arena.k27_memory_navigator.route_card_admission import (
    CapacityEnvelope, Disposition, Polarity, ProofReceipt, RouteIdentity,
    TemporalRequirement, UseContext,
)
from tools.arena.k27_memory_navigator.route_delta_planner import (
    DeltaStrategy, RouteChange, RouteSegment, plan_route_delta,
)
from tools.arena.k27_memory_navigator.minimal_evidence import (
    EvidenceMode, EvidenceWorld, compile_minimal_evidence, evaluate,
)

H = "0" * 64
A = "1" * 64
B = "2" * 64


def identity(**kw):
    base = dict(objective_root=H, target_id="target", source_root=A,
                dependency_root=B, map_generation="g", lifecycle_epoch=1,
                owner_incarnation="boot", currentness_generation=1, k27=(1,))
    base.update(kw)
    return RouteIdentity(**base)


def envelope(**kw):
    base = dict(hydration=5, route_cost=5, lawfield_crossings=1, disclosure=2)
    base.update(kw)
    return CapacityEnvelope(**base)


def temporal(**kw):
    base = dict(event_time=1, deadline=None, worst_case_finish=None,
                phase_tolerance=None, lawfield_transition=False,
                irreversible_or_external=False)
    base.update(kw)
    return TemporalRequirement(**base)


def receipt(polarity=Polarity.POSITIVE, **kw):
    t = temporal()
    return ProofReceipt(polarity, kw.pop("route_identity", identity()), envelope(),
                        t.mode, t.event_time, **kw)


def use(identity_value=None, **kw):
    return UseContext(identity_value or identity(), kw.pop("envelope", envelope()),
                      kw.pop("temporal", temporal()), **kw)


class IncrementalEvidenceTests(unittest.TestCase):
    def segments(self, n=4, negative=False):
        return [RouteSegment(
            f"s{i}", frozenset({f"n{i}", f"n{i+1}"}),
            receipt(Polarity.NEGATIVE if negative else Polarity.POSITIVE,
                    state_independent_negative=negative),
        ) for i in range(n)]

    def contexts(self, segs, **kwargs):
        return {s.segment_id: use(**kwargs) for s in segs}

    def test_sparse_corridor(self):
        segs = self.segments()
        plan = plan_route_delta(segs, self.contexts(segs),
                                RouteChange(frozenset({"n0"}), True), eager_threshold=.5)
        self.assertEqual(plan.strategy, DeltaStrategy.SELECTIVE)
        self.assertEqual(plan.selected_segment_ids, ("s0",))

    def test_dense_switches_eager(self):
        segs = self.segments()
        plan = plan_route_delta(segs, self.contexts(segs),
                                RouteChange(frozenset({"n1", "n2"}), True), eager_threshold=.5)
        self.assertEqual(plan.strategy, DeltaStrategy.EAGER_SHARED)
        self.assertEqual(plan.geometry_recomputations, 4)

    def test_currentness_rebind_does_not_rebuild_geometry(self):
        segs = self.segments(negative=True)
        contexts = {s.segment_id: use(identity(currentness_generation=2)) for s in segs}
        plan = plan_route_delta(segs, contexts, RouteChange(frozenset(), False))
        self.assertEqual(plan.strategy, DeltaStrategy.NO_GEOMETRY_REBUILD)
        self.assertEqual(plan.geometry_recomputations, 0)
        self.assertTrue(all(d.admission.disposition is Disposition.REBIND_NEGATIVE_CURRENTNESS_D0
                            for d in plan.decisions))

    def test_lifecycle_move_reproof_without_geometry_rebuild(self):
        segs = self.segments(negative=True)
        contexts = {s.segment_id: use(identity(lifecycle_epoch=2)) for s in segs}
        plan = plan_route_delta(segs, contexts, RouteChange(frozenset(), False))
        self.assertEqual(plan.geometry_recomputations, 0)
        self.assertTrue(all(d.admission.disposition is Disposition.REPROVE for d in plan.decisions))

    def test_duplicate_segments_rejected(self):
        seg = self.segments(1)[0]
        with self.assertRaises(ValueError):
            plan_route_delta([seg, seg], {"s0": use()}, RouteChange(frozenset(), False))

    def test_uniform_outcome_is_zero_disclosure(self):
        worlds = [EvidenceWorld("a", "HOLD", (0, 0)), EvidenceWorld("b", "HOLD", (1, 1))]
        plan = compile_minimal_evidence(worlds, [5, 1], hard_premises_valid=True)
        self.assertEqual(plan.mode, EvidenceMode.ZERO_DISCLOSURE)
        self.assertEqual(plan.worst_case_cost, 0)

    def test_hard_premise_holds_before_query(self):
        worlds = [EvidenceWorld("a", "A", (0,)), EvidenceWorld("b", "B", (1,))]
        self.assertEqual(compile_minimal_evidence(worlds, [2], hard_premises_valid=False).mode,
                         EvidenceMode.HOLD_BEFORE_QUERY)

    def test_weighted_tree_prefers_cheaper_equivalent_predicate(self):
        worlds = [EvidenceWorld("a", "A", (0, 0)), EvidenceWorld("b", "B", (1, 1))]
        plan = compile_minimal_evidence(worlds, [9, 2], hard_premises_valid=True)
        self.assertEqual(plan.worst_case_cost, 2)
        self.assertEqual(plan.tree.predicate_index, 1)

    def test_tree_classifies_every_world(self):
        worlds = [EvidenceWorld("a", "A", (0, 0)), EvidenceWorld("b", "B", (0, 1)),
                  EvidenceWorld("c", "C", (1, 0)), EvidenceWorld("d", "D", (1, 1))]
        plan = compile_minimal_evidence(worlds, [2, 3], hard_premises_valid=True)
        for world in worlds:
            self.assertEqual(evaluate(plan.tree, world.bits), world.outcome)

    def test_unsupported_family_falls_back(self):
        worlds = [EvidenceWorld("a", "A", (0,)), EvidenceWorld("b", "B", (1,))]
        self.assertEqual(compile_minimal_evidence(
            worlds, [1], hard_premises_valid=True,
            supported_single_bit_family=False).mode, EvidenceMode.FULL_REIFY)

    def test_unsplittable_family_falls_back(self):
        worlds = [EvidenceWorld("a", "A", (0,)), EvidenceWorld("b", "B", (0,))]
        self.assertEqual(compile_minimal_evidence(worlds, [1], hard_premises_valid=True).mode,
                         EvidenceMode.FULL_REIFY)

    def test_parity_requires_all_weighted_bits(self):
        worlds = [EvidenceWorld(str(bits), str(sum(bits) % 2), bits)
                  for bits in itertools.product((0, 1), repeat=3)]
        self.assertEqual(compile_minimal_evidence(worlds, [4, 2, 1], hard_premises_valid=True).worst_case_cost, 7)

    def test_plans_never_mint_authority(self):
        worlds = [EvidenceWorld("a", "A", (0,)), EvidenceWorld("b", "B", (1,))]
        plan = compile_minimal_evidence(worlds, [1], hard_premises_valid=True)
        self.assertFalse(plan.authority_minted)
        self.assertFalse(plan.effect_authority)
        self.assertFalse(plan.gate10)

    def test_random_small_cost_is_bruteforce_optimal(self):
        rng = random.Random(811)
        def brute(worlds, costs, ids, remaining):
            labels = {worlds[i].outcome for i in ids}
            if len(labels) == 1:
                return 0
            best = float("inf")
            for pred in remaining:
                zero = tuple(i for i in ids if worlds[i].bits[pred] == 0)
                one = tuple(i for i in ids if worlds[i].bits[pred] == 1)
                if not zero or not one:
                    continue
                rest = tuple(x for x in remaining if x != pred)
                best = min(best, costs[pred] + max(
                    brute(worlds, costs, zero, rest), brute(worlds, costs, one, rest)))
            return best
        for _ in range(100):
            width = rng.randint(1, 4)
            universe = list(itertools.product((0, 1), repeat=width))
            rng.shuffle(universe)
            count = rng.randint(2, min(6, len(universe)))
            worlds = [EvidenceWorld(str(i), str((sum(bits) + bits[-1]) % 3), bits)
                      for i, bits in enumerate(universe[:count])]
            costs = [rng.randint(1, 6) for _ in range(width)]
            expected = brute(worlds, costs, tuple(range(count)), tuple(range(width)))
            plan = compile_minimal_evidence(worlds, costs, hard_premises_valid=True)
            if expected == float("inf"):
                self.assertEqual(plan.mode, EvidenceMode.FULL_REIFY)
            else:
                self.assertEqual(plan.worst_case_cost, expected)

    def test_random_tree_classification(self):
        rng = random.Random(808)
        for _ in range(500):
            width = rng.randint(1, 5)
            universe = list(itertools.product((0, 1), repeat=width))
            rng.shuffle(universe)
            worlds = [EvidenceWorld(str(i), str((sum(bits) + bits[0]) % 3), bits)
                      for i, bits in enumerate(universe[:rng.randint(2, min(10, len(universe)))])]
            plan = compile_minimal_evidence(worlds, [rng.randint(1, 7) for _ in range(width)],
                                            hard_premises_valid=True)
            if plan.mode is EvidenceMode.ADAPTIVE:
                for world in worlds:
                    self.assertEqual(evaluate(plan.tree, world.bits), world.outcome)


if __name__ == "__main__":
    unittest.main()
