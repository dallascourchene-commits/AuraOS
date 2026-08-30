import unittest
from dataclasses import replace

from tools.bughound.resource_settlement import (
    MatchedResourceObservationV1,
    ResourceSettlementError,
    settle_matched_resource_use,
)
from tools.bughound.seedlab_benchmark import (
    FindingV1,
    build_matched_plan,
    score_findings,
    seeded_cases,
)


class BugHoundResourceSettlementTests(unittest.TestCase):
    def setUp(self):
        self.cases = seeded_cases()
        self.plan = build_matched_plan(
            "W5",
            self.cases,
            worker_budget=3,
            tool_budget=5,
        )
        self.findings = tuple(
            FindingV1(
                case_id=case.case_id,
                detected=case.is_bug,
                localized_symbols=(case.expected_symbol,) if case.is_bug else (),
                finding_ref=f"candidate:{case.case_id}",
            )
            for case in self.cases
        )
        self.score = score_findings(self.plan, self.cases, self.findings)

    def observation(self, **overrides):
        values = {
            "run_plan_digest": self.plan.run_plan_digest,
            "topology_id": self.plan.topology_id,
            "source_generation": self.plan.source_generation,
            "observed_worker_ids": ("worker-a", "worker-b", "worker-c"),
            "observed_tool_call_ids": ("tool-1", "tool-2", "tool-3", "tool-4", "tool-5"),
            "observer_generation": "BUGHOUND-EVAL-GEN-1",
        }
        values.update(overrides)
        return MatchedResourceObservationV1(**values)

    def test_exact_observed_budget_admits_cross_topology_comparison(self):
        out = settle_matched_resource_use(
            plan=self.plan, score=self.score, observation=self.observation()
        )
        self.assertEqual("ADMITTED_MATCHED_OBSERVED_RESOURCES", out.status)
        self.assertTrue(out.resource_budget_satisfied)
        self.assertTrue(out.benchmark_score_valid)
        self.assertTrue(out.admitted_for_cross_topology_comparison)
        self.assertEqual(3, out.observed_worker_count)
        self.assertEqual(5, out.observed_tool_call_count)
        self.assertFalse(out.authority)
        self.assertFalse(out.promotion_authorized)

    def test_under_budget_is_valid_when_measured(self):
        obs = self.observation(
            observed_worker_ids=("worker-a",),
            observed_tool_call_ids=("tool-1",),
        )
        out = settle_matched_resource_use(plan=self.plan, score=self.score, observation=obs)
        self.assertTrue(out.admitted_for_cross_topology_comparison)

    def test_worker_budget_exceeded_blocks_comparison(self):
        obs = self.observation(
            observed_worker_ids=("a", "b", "c", "d"),
            observed_tool_call_ids=(),
        )
        out = settle_matched_resource_use(plan=self.plan, score=self.score, observation=obs)
        self.assertEqual("BLOCKED", out.status)
        self.assertIn("WORKER_BUDGET_EXCEEDED", out.blockers)
        self.assertFalse(out.admitted_for_cross_topology_comparison)

    def test_tool_budget_exceeded_blocks_comparison(self):
        obs = self.observation(
            observed_worker_ids=("a",),
            observed_tool_call_ids=tuple(f"t{i}" for i in range(6)),
        )
        out = settle_matched_resource_use(plan=self.plan, score=self.score, observation=obs)
        self.assertIn("TOOL_BUDGET_EXCEEDED", out.blockers)
        self.assertFalse(out.resource_budget_satisfied)

    def test_plan_digest_mismatch_is_hard_failure(self):
        with self.assertRaises(ResourceSettlementError) as ctx:
            settle_matched_resource_use(
                plan=self.plan,
                score=self.score,
                observation=self.observation(run_plan_digest="f" * 64),
            )
        self.assertEqual("RESOURCE_RUN_PLAN_BINDING_MISMATCH", ctx.exception.code)

    def test_topology_and_source_generation_mismatch_are_hard_failures(self):
        with self.assertRaises(ResourceSettlementError) as ctx:
            settle_matched_resource_use(
                plan=self.plan,
                score=self.score,
                observation=self.observation(topology_id="W0"),
            )
        self.assertEqual("RESOURCE_TOPOLOGY_BINDING_MISMATCH", ctx.exception.code)
        with self.assertRaises(ResourceSettlementError) as ctx:
            settle_matched_resource_use(
                plan=self.plan,
                score=self.score,
                observation=self.observation(source_generation="STALE"),
            )
        self.assertEqual("RESOURCE_SOURCE_GENERATION_MISMATCH", ctx.exception.code)

    def test_score_from_other_match_basis_is_rejected(self):
        other_plan = build_matched_plan(
            "W5", self.cases, worker_budget=4, tool_budget=5
        )
        other_score = score_findings(other_plan, self.cases, self.findings)
        with self.assertRaises(ResourceSettlementError) as ctx:
            settle_matched_resource_use(
                plan=self.plan, score=other_score, observation=self.observation()
            )
        self.assertEqual("RESOURCE_MATCH_BASIS_MISMATCH", ctx.exception.code)

    def test_stale_nonindependent_or_incomplete_observation_blocks(self):
        for field, blocker in (
            ("observer_current", "RESOURCE_OBSERVER_STALE"),
            ("independent_observer", "INDEPENDENT_RESOURCE_OBSERVER_REQUIRED"),
            ("run_completed", "RESOURCE_RUN_NOT_COMPLETED"),
        ):
            with self.subTest(field=field):
                out = settle_matched_resource_use(
                    plan=self.plan,
                    score=self.score,
                    observation=self.observation(**{field: False}),
                )
                self.assertIn(blocker, out.blockers)
                self.assertFalse(out.admitted_for_cross_topology_comparison)

    def test_duplicate_worker_or_tool_identity_is_rejected(self):
        with self.assertRaises(ResourceSettlementError) as ctx:
            self.observation(observed_worker_ids=("a", "a"), observed_tool_call_ids=())
        self.assertEqual("RESOURCE_OBSERVATION_DUPLICATE_ID", ctx.exception.code)
        with self.assertRaises(ResourceSettlementError) as ctx:
            self.observation(observed_worker_ids=("a",), observed_tool_call_ids=("t", "t"))
        self.assertEqual("RESOURCE_OBSERVATION_DUPLICATE_ID", ctx.exception.code)

    def test_missing_worker_observation_is_rejected(self):
        with self.assertRaises(ResourceSettlementError) as ctx:
            self.observation(observed_worker_ids=(), observed_tool_call_ids=())
        self.assertEqual("OBSERVED_WORKER_IDS_REQUIRED", ctx.exception.code)

    def test_leakage_invalidated_score_cannot_be_rescued_by_good_resource_use(self):
        leaked_plan = build_matched_plan(
            "W5",
            self.cases,
            worker_budget=3,
            tool_budget=5,
            fixed_patch_visible=True,
        )
        leaked_score = score_findings(leaked_plan, self.cases, self.findings)
        leaked_obs = MatchedResourceObservationV1(
            run_plan_digest=leaked_plan.run_plan_digest,
            topology_id=leaked_plan.topology_id,
            source_generation=leaked_plan.source_generation,
            observed_worker_ids=("a",),
            observed_tool_call_ids=(),
            observer_generation="EVAL-G1",
        )
        out = settle_matched_resource_use(
            plan=leaked_plan, score=leaked_score, observation=leaked_obs
        )
        self.assertIn("BENCHMARK_SCORE_NOT_VALID_FOR_COMPARISON", out.blockers)
        self.assertFalse(out.admitted_for_cross_topology_comparison)

    def test_resource_observation_cannot_widen_authority_or_effect(self):
        for field in ("authority", "external_effect"):
            with self.subTest(field=field):
                with self.assertRaises(ResourceSettlementError) as ctx:
                    self.observation(**{field: True})
                self.assertEqual(
                    "RESOURCE_OBSERVATION_AUTHORITY_WIDENING_FORBIDDEN",
                    ctx.exception.code,
                )


if __name__ == "__main__":
    unittest.main()
