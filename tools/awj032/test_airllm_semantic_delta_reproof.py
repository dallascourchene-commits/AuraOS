import random
import unittest

import airllm_semantic_delta_reproof as r


def by_id(plan: dict) -> dict:
    return {item["leaf_id"]: item for item in plan["decisions"]}


class SemanticDeltaReproofTests(unittest.TestCase):
    def test_current_pr311_delta_reopens_only_source_admission(self):
        leaves, deltas = r.pr311_current_fixture()
        plan = by_id(r.compile_reproof(leaves, deltas))
        self.assertEqual(plan["G1_SOURCE_ADMISSION"]["disposition"], "REPROOF_REQUIRED")
        self.assertEqual(
            tuple(plan["G1_SOURCE_ADMISSION"]["invalidators"]),
            ("airllm_source_admission.py",),
        )
        self.assertEqual(plan["HARD_FALSE_REMEDIATION"]["disposition"], "HISTORICAL_COMPATIBLE_SUPPORT")
        self.assertEqual(plan["RUNTIME_HARD_FALSE_GUARD"]["disposition"], "HISTORICAL_COMPATIBLE_SUPPORT")
        self.assertEqual(plan["TINY_SPLIT_GENERATE_REOPEN"]["disposition"], "HISTORICAL_COMPATIBLE_SUPPORT")

    def test_owner_host_current_claim_requires_physical_reproof(self):
        leaves, deltas = r.pr311_current_fixture()
        plan = by_id(r.compile_reproof(leaves, deltas, claiming_owner_host_current=True))
        self.assertEqual(plan["G1_SOURCE_ADMISSION"]["disposition"], "REPROOF_REQUIRED")
        self.assertEqual(plan["RUNTIME_HARD_FALSE_GUARD"]["disposition"], "OWNER_HOST_REPROOF_REQUIRED")
        self.assertEqual(plan["TINY_SPLIT_GENERATE_REOPEN"]["disposition"], "OWNER_HOST_REPROOF_REQUIRED")
        self.assertEqual(plan["OWNER_HOST_G3"]["disposition"], "OWNER_HOST_REPROOF_REQUIRED")

    def test_runtime_delta_does_not_reopen_unrelated_tiny_leaf(self):
        leaves, _ = r.pr311_current_fixture()
        plan = by_id(
            r.compile_reproof(
                leaves,
                [r.GenerationDelta("airllm_runtime_hard_false.py", "old", "new")],
            )
        )
        self.assertEqual(plan["RUNTIME_HARD_FALSE_GUARD"]["disposition"], "REPROOF_REQUIRED")
        self.assertEqual(plan["TINY_SPLIT_GENERATE_REOPEN"]["disposition"], "HISTORICAL_COMPATIBLE_SUPPORT")

    def test_fixture_revision_delta_reopens_tiny_only(self):
        leaves, _ = r.pr311_current_fixture()
        plan = by_id(
            r.compile_reproof(
                leaves,
                [r.GenerationDelta("tiny_fixture_revision", "old", "new")],
            )
        )
        self.assertEqual(plan["TINY_SPLIT_GENERATE_REOPEN"]["disposition"], "REPROOF_REQUIRED")
        self.assertEqual(plan["G1_SOURCE_ADMISSION"]["disposition"], "HISTORICAL_COMPATIBLE_SUPPORT")

    def test_equal_generation_is_not_an_invalidator(self):
        leaves, _ = r.pr311_current_fixture()
        plan = r.compile_reproof(
            leaves,
            [r.GenerationDelta("airllm_source_admission.py", "same", "same")],
        )
        self.assertTrue(all(x["disposition"] == "HISTORICAL_COMPATIBLE_SUPPORT" for x in plan["decisions"]))

    def test_plan_root_is_deterministic(self):
        leaves, deltas = r.pr311_current_fixture()
        self.assertEqual(
            r.compile_reproof(leaves, deltas)["plan_root"],
            r.compile_reproof(leaves, deltas)["plan_root"],
        )

    def test_random_selective_invalidation(self):
        rnd = random.Random(530311)
        deps = [f"d{i}" for i in range(20)]
        for _ in range(5000):
            leaf_deps = tuple(sorted(rnd.sample(deps, rnd.randint(0, 5))))
            leaf = r.EvidenceLeaf("x", r.SOURCE_SECURITY, leaf_deps, "historical")
            changed = set(rnd.sample(deps, rnd.randint(0, 5)))
            deltas = [r.GenerationDelta(dep, "old", "new") for dep in changed]
            decision = r.compile_reproof([leaf], deltas)["decisions"][0]
            self.assertEqual(
                decision["disposition"] == "REPROOF_REQUIRED",
                bool(set(leaf_deps) & changed),
            )


if __name__ == "__main__":
    unittest.main()
