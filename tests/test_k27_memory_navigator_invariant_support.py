import random
import unittest

from tools.arena.k27_memory_navigator.invariant_support import (
    HardInvariantSupport, SupportDisposition, SupportState,
    compile_invariant_support,
)


def support(i, members, state=SupportState.CURRENT):
    return HardInvariantSupport(i, frozenset(members), state)


class InvariantSupportTests(unittest.TestCase):
    def test_direct_geometry_seed_selects_component(self):
        plan = compile_invariant_support(
            ["a", "b", "c", "d"], ["a"], [support("I", ["a", "c"])],
            eager_threshold=.75,
        )
        self.assertEqual(plan.disposition, SupportDisposition.SELECTIVE_REPROOF)
        self.assertEqual(plan.reproof_segment_ids, ("a", "c"))

    def test_hyperedges_transitively_couple(self):
        plan = compile_invariant_support(
            ["a", "b", "c", "d"], ["a"],
            [support("I1", ["a", "b"]), support("I2", ["b", "c"])],
            eager_threshold=1.0,
        )
        self.assertEqual(plan.reproof_segment_ids, ("a", "b", "c"))

    def test_changed_invariant_seeds_without_geometry(self):
        plan = compile_invariant_support(
            ["a", "b", "c"], [], [support("I", ["b", "c"])],
            changed_invariant_ids=["I"], eager_threshold=1.0,
        )
        self.assertEqual(plan.reproof_segment_ids, ("b", "c"))

    def test_dense_support_collapses_to_eager(self):
        plan = compile_invariant_support(
            ["a", "b", "c", "d"], ["a"], [support("I", ["a", "b", "c"])],
            eager_threshold=.5,
        )
        self.assertEqual(plan.disposition, SupportDisposition.EAGER_SHARED_REPROOF)
        self.assertEqual(plan.reproof_segment_ids, ("a", "b", "c", "d"))

    def test_stale_support_holds_global(self):
        plan = compile_invariant_support(
            ["a", "b", "c"], ["a"],
            [support("I", ["a", "b"], SupportState.STALE)],
        )
        self.assertEqual(plan.disposition, SupportDisposition.HOLD_SUPPORT_UNCERTAINTY)
        self.assertTrue(plan.support_refresh_required)
        self.assertEqual(plan.reproof_segment_ids, ("a", "b", "c"))

    def test_unknown_support_holds_global(self):
        plan = compile_invariant_support(
            ["a", "b"], [], [support("I", ["a", "b"], SupportState.UNKNOWN)],
        )
        self.assertEqual(plan.disposition, SupportDisposition.HOLD_SUPPORT_UNCERTAINTY)

    def test_duplicate_invariant_rejected(self):
        with self.assertRaises(ValueError):
            compile_invariant_support(
                ["a", "b"], ["a"], [support("I", ["a"]), support("I", ["b"])],
            )

    def test_unknown_segment_rejected(self):
        with self.assertRaises(ValueError):
            compile_invariant_support(["a"], [], [support("I", ["b"])])

    def test_unknown_changed_invariant_rejected(self):
        with self.assertRaises(ValueError):
            compile_invariant_support(["a"], [], [], changed_invariant_ids=["missing"])

    def test_raw_state_rejected(self):
        with self.assertRaises(ValueError):
            HardInvariantSupport("I", frozenset({"a"}), "CURRENT")

    def test_no_seed_no_reproof(self):
        plan = compile_invariant_support(["a", "b"], [], [support("I", ["a", "b"])])
        self.assertEqual(plan.disposition, SupportDisposition.NO_REPROOF)
        self.assertEqual(plan.reproof_segment_ids, ())

    def test_root_stable_across_input_order(self):
        first = compile_invariant_support(
            ["a", "b", "c"], ["a"],
            [support("Z", ["b", "c"]), support("A", ["a", "b"])],
            eager_threshold=1.0,
        )
        second = compile_invariant_support(
            ["c", "b", "a"], ["a"],
            [support("A", ["b", "a"]), support("Z", ["c", "b"])],
            eager_threshold=1.0,
        )
        self.assertEqual(first.support_root, second.support_root)

    def test_authority_never_minted(self):
        plan = compile_invariant_support(["a"], ["a"], [])
        self.assertFalse(plan.authority_minted)
        self.assertFalse(plan.effect_authority)
        self.assertFalse(plan.gate10)

    def test_random_matches_reference_closure(self):
        rng = random.Random(12012)
        for _ in range(5000):
            n = rng.randint(2, 12)
            segments = [f"s{i}" for i in range(n)]
            supports = []
            for j in range(rng.randint(0, 8)):
                members = frozenset(rng.sample(segments, rng.randint(1, n)))
                supports.append(support(f"I{j}", members))
            seeds = set(rng.sample(segments, rng.randint(0, n)))
            plan = compile_invariant_support(
                segments, seeds, supports, eager_threshold=1.0,
            )
            reference = set(seeds)
            changed = True
            while changed:
                changed = False
                for item in supports:
                    if reference & item.segment_ids and not item.segment_ids <= reference:
                        reference.update(item.segment_ids)
                        changed = True
            self.assertEqual(set(plan.reproof_segment_ids), reference)

    def test_random_stale_never_certifies_split(self):
        rng = random.Random(12013)
        for _ in range(2000):
            n = rng.randint(2, 10)
            segments = [f"s{i}" for i in range(n)]
            members = frozenset(rng.sample(segments, rng.randint(1, n)))
            state = rng.choice([SupportState.STALE, SupportState.UNKNOWN])
            plan = compile_invariant_support(
                segments, [segments[0]], [support("I", members, state)],
            )
            self.assertEqual(plan.disposition, SupportDisposition.HOLD_SUPPORT_UNCERTAINTY)
            self.assertEqual(set(plan.reproof_segment_ids), set(segments))


if __name__ == "__main__":
    unittest.main()
