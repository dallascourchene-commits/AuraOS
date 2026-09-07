import random
import unittest

from tools.arena.k27_memory_navigator.invariant_support import (
    HardInvariantSupport, SupportDisposition, SupportState, SupportUseDisposition,
    SupportWorldIdentity, compile_invariant_support, validate_support_use,
)

C0 = "0" * 64
C1 = "1" * 64


def support(i, members, state=SupportState.CURRENT):
    return HardInvariantSupport(i, frozenset(members), state)


def world(config=C0, generation=1, owner="boot-a"):
    return SupportWorldIdentity(config, generation, owner)


class InvariantSupportTests(unittest.TestCase):
    def test_direct_geometry_seed_selects_component(self):
        plan = compile_invariant_support(
            ["a", "b", "c", "d"], ["a"], [support("I", ["a", "c"])],
            eager_threshold=.75, support_identity=world(),
        )
        self.assertEqual(plan.disposition, SupportDisposition.SELECTIVE_REPROOF)
        self.assertEqual(plan.reproof_segment_ids, ("a", "c"))

    def test_hyperedges_transitively_couple(self):
        plan = compile_invariant_support(
            ["a", "b", "c", "d"], ["a"],
            [support("I1", ["a", "b"]), support("I2", ["b", "c"])],
            eager_threshold=1.0, support_identity=world(),
        )
        self.assertEqual(plan.reproof_segment_ids, ("a", "b", "c"))

    def test_changed_invariant_seeds_without_geometry(self):
        plan = compile_invariant_support(
            ["a", "b", "c"], [], [support("I", ["b", "c"])],
            changed_invariant_ids=["I"], eager_threshold=1.0,
            support_identity=world(),
        )
        self.assertEqual(plan.reproof_segment_ids, ("b", "c"))

    def test_dense_support_collapses_to_eager(self):
        plan = compile_invariant_support(
            ["a", "b", "c", "d"], ["a"], [support("I", ["a", "b", "c"])],
            eager_threshold=.5, support_identity=world(),
        )
        self.assertEqual(plan.disposition, SupportDisposition.EAGER_SHARED_REPROOF)
        self.assertEqual(plan.reproof_segment_ids, ("a", "b", "c", "d"))

    def test_stale_support_holds_global(self):
        plan = compile_invariant_support(
            ["a", "b", "c"], ["a"],
            [support("I", ["a", "b"], SupportState.STALE)], support_identity=world(),
        )
        self.assertEqual(plan.disposition, SupportDisposition.HOLD_SUPPORT_UNCERTAINTY)
        self.assertTrue(plan.support_refresh_required)
        self.assertEqual(plan.reproof_segment_ids, ("a", "b", "c"))

    def test_unknown_support_holds_global(self):
        plan = compile_invariant_support(
            ["a", "b"], [], [support("I", ["a", "b"], SupportState.UNKNOWN)],
            support_identity=world(),
        )
        self.assertEqual(plan.disposition, SupportDisposition.HOLD_SUPPORT_UNCERTAINTY)

    def test_duplicate_invariant_rejected(self):
        with self.assertRaises(ValueError):
            compile_invariant_support(
                ["a", "b"], ["a"],
                [support("I", ["a"]), support("I", ["b"])], support_identity=world(),
            )

    def test_unknown_segment_rejected(self):
        with self.assertRaises(ValueError):
            compile_invariant_support(["a"], [], [support("I", ["b"])], support_identity=world())

    def test_unknown_changed_invariant_rejected(self):
        with self.assertRaises(ValueError):
            compile_invariant_support(
                ["a"], [], [], changed_invariant_ids=["missing"], support_identity=world(),
            )

    def test_raw_state_rejected(self):
        with self.assertRaises(ValueError):
            HardInvariantSupport("I", frozenset({"a"}), "CURRENT")

    def test_no_seed_no_reproof(self):
        plan = compile_invariant_support(
            ["a", "b"], [], [support("I", ["a", "b"])], support_identity=world(),
        )
        self.assertEqual(plan.disposition, SupportDisposition.NO_REPROOF)
        self.assertEqual(plan.reproof_segment_ids, ())

    def test_root_stable_across_input_order(self):
        first = compile_invariant_support(
            ["a", "b", "c"], ["a"],
            [support("Z", ["b", "c"]), support("A", ["a", "b"])],
            eager_threshold=1.0, support_identity=world(),
        )
        second = compile_invariant_support(
            ["c", "b", "a"], ["a"],
            [support("A", ["b", "a"]), support("Z", ["c", "b"])],
            eager_threshold=1.0, support_identity=world(),
        )
        self.assertEqual(first.support_identity_root, second.support_identity_root)

    def test_authority_never_minted(self):
        plan = compile_invariant_support(["a"], ["a"], [], support_identity=world())
        decision = validate_support_use(plan, [], world())
        self.assertFalse(plan.authority_minted or decision.authority_minted)
        self.assertFalse(plan.effect_authority or decision.effect_authority)
        self.assertFalse(plan.gate10 or decision.gate10)

    def test_exact_support_world_ready(self):
        supports = [support("I", ["a", "b"])]
        plan = compile_invariant_support(["a", "b"], ["a"], supports, support_identity=world())
        self.assertEqual(
            validate_support_use(plan, supports, world()).disposition,
            SupportUseDisposition.READY_D0,
        )

    def test_configuration_drift_reproofs(self):
        supports = [support("I", ["a", "b"])]
        plan = compile_invariant_support(["a", "b"], ["a"], supports, support_identity=world())
        self.assertEqual(
            validate_support_use(plan, supports, world(config=C1)).disposition,
            SupportUseDisposition.REPROVE_SUPPORT_WORLD,
        )

    def test_generation_drift_reproofs(self):
        supports = [support("I", ["a", "b"])]
        plan = compile_invariant_support(["a", "b"], ["a"], supports, support_identity=world())
        self.assertEqual(
            validate_support_use(plan, supports, world(generation=2)).disposition,
            SupportUseDisposition.REPROVE_SUPPORT_WORLD,
        )

    def test_owner_incarnation_drift_reproofs(self):
        supports = [support("I", ["a", "b"])]
        plan = compile_invariant_support(["a", "b"], ["a"], supports, support_identity=world())
        self.assertEqual(
            validate_support_use(plan, supports, world(owner="boot-b")).disposition,
            SupportUseDisposition.REPROVE_SUPPORT_WORLD,
        )

    def test_membership_drift_reproofs(self):
        before = [support("I", ["a", "b"])]
        after = [support("I", ["a"])]
        plan = compile_invariant_support(["a", "b"], ["a"], before, support_identity=world())
        self.assertEqual(
            validate_support_use(plan, after, world()).disposition,
            SupportUseDisposition.REPROVE_SUPPORT_WORLD,
        )

    def test_stale_at_use_holds(self):
        before = [support("I", ["a", "b"])]
        current = [support("I", ["a", "b"], SupportState.STALE)]
        plan = compile_invariant_support(["a", "b"], ["a"], before, support_identity=world())
        self.assertEqual(
            validate_support_use(plan, current, world()).disposition,
            SupportUseDisposition.HOLD_SUPPORT_UNCERTAINTY,
        )

    def test_unbound_plan_cannot_ready(self):
        supports = [support("I", ["a", "b"])]
        plan = compile_invariant_support(["a", "b"], ["a"], supports)
        self.assertEqual(
            validate_support_use(plan, supports, world()).disposition,
            SupportUseDisposition.HOLD_UNBOUND_SUPPORT_IDENTITY,
        )

    def test_random_matches_reference_closure(self):
        rng = random.Random(12012)
        for _ in range(5000):
            n = rng.randint(2, 12)
            segments = [f"s{i}" for i in range(n)]
            supports = []
            for j in range(rng.randint(0, 8)):
                supports.append(support(
                    f"I{j}", frozenset(rng.sample(segments, rng.randint(1, n))),
                ))
            seeds = set(rng.sample(segments, rng.randint(0, n)))
            plan = compile_invariant_support(
                segments, seeds, supports, eager_threshold=1.0, support_identity=world(),
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
                support_identity=world(),
            )
            self.assertEqual(plan.disposition, SupportDisposition.HOLD_SUPPORT_UNCERTAINTY)
            self.assertEqual(set(plan.reproof_segment_ids), set(segments))

    def test_random_mismatched_world_never_ready(self):
        rng = random.Random(13013)
        supports = [support("I", ["a", "b"])]
        plan = compile_invariant_support(["a", "b"], ["a"], supports, support_identity=world())
        for _ in range(10000):
            decision = validate_support_use(
                plan, supports, world(generation=rng.randint(2, 1_000_000)),
            )
            self.assertNotEqual(decision.disposition, SupportUseDisposition.READY_D0)


if __name__ == "__main__":
    unittest.main()
