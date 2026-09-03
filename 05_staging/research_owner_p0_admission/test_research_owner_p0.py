import random
import unittest
from dataclasses import replace

from research_owner_p0 import *


class Tests(unittest.TestCase):
    def lead(self):
        return ResearchLead(
            "arxiv:2606.05348",
            "v1",
            "rev1",
            "sem1",
            "arxiv",
            "incremental-computation",
            "selective invalidation can reduce re-execution",
            "affected-cone mismatch",
            (8, 12, 23),
        )

    def target(self):
        return OwnerTarget(
            "github",
            "dallascourchene-commits/AuraOS",
            "pull",
            311,
            "d951404e0ba15a04682f47610f4643ce55d9ff7e",
            "pr311:g1",
            "AUTHORIZED",
        )

    def compiler(self):
        return ResearchOwnerP0Admission()

    def cmd(self):
        return self.compiler().compile(self.lead(), self.target(), command_id="AWJ032-P0")

    def test_compile_binds_owner_and_head(self):
        c = self.cmd()
        self.assertEqual(c.owner_ref, "github://dallascourchene-commits/AuraOS/pull/311")
        self.assertEqual(c.requested_rung, "P0")

    def test_k27_does_not_authorize_target(self):
        with self.assertRaisesRegex(ValueError, "TARGET_NOT_AUTHORIZED"):
            self.compiler().compile(
                self.lead(), replace(self.target(), authorization="UNKNOWN"), command_id="x"
            )

    def test_source_currentness_independent(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_STALE"):
            self.compiler().compile(
                replace(self.lead(), source_current=False), self.target(), command_id="x"
            )

    def test_target_currentness_independent(self):
        with self.assertRaisesRegex(ValueError, "TARGET_STALE"):
            self.compiler().compile(
                self.lead(), replace(self.target(), target_current=False), command_id="x"
            )

    def test_source_access_denied(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_ACCESS_DENIED"):
            self.compiler().compile(
                replace(self.lead(), source_access="DENIED"), self.target(), command_id="x"
            )

    def test_bare_repo_rejected(self):
        with self.assertRaisesRegex(ValueError, "OWNER_NOT_QUALIFIED"):
            self.compiler().compile(
                self.lead(), replace(self.target(), repository="AuraOS"), command_id="x"
            )

    def test_missing_command_id(self):
        with self.assertRaisesRegex(ValueError, "COMMAND_ID_REQUIRED"):
            self.compiler().compile(self.lead(), self.target(), command_id="")

    def test_p0_negative_intents(self):
        c = self.cmd()
        self.assertIn("MODEL_GENERATION", c.negative_intent)
        self.assertIn("P1_PROFILE", c.negative_intent)
        self.assertEqual(c.effect_ceiling, "D0")

    def test_command_root_stable(self):
        self.assertEqual(self.cmd().command_root, self.cmd().command_root)

    def test_k27_change_changes_root_not_authority(self):
        c1 = self.cmd()
        c2 = self.compiler().compile(
            replace(self.lead(), k27=(1, 2, 3)), self.target(), command_id="AWJ032-P0"
        )
        self.assertNotEqual(c1.command_root, c2.command_root)
        self.assertEqual(c2.effect_ceiling, "D0")

    def test_no_observation_waits(self):
        self.assertEqual(
            self.compiler().observe(self.cmd(), []).disposition,
            "WAIT_COMMAND_OBSERVATION",
        )

    def test_materialized_not_execution(self):
        c = self.cmd()
        o = CommandObservation(c.command_id, "MATERIALIZED", c.owner_ref, c.exact_head)
        self.assertEqual(self.compiler().observe(c, [o]).disposition, "MATERIALIZED_WAIT_ACK")

    def test_ack_not_result(self):
        c = self.cmd()
        o = CommandObservation(c.command_id, "ACKED", c.owner_ref, c.exact_head)
        self.assertEqual(self.compiler().observe(c, [o]).disposition, "ACKED_WAIT_RESULT")

    def test_result_requires_lease(self):
        c = self.cmd()
        o = CommandObservation(c.command_id, "RESULT", c.owner_ref, c.exact_head)
        self.assertEqual(self.compiler().observe(c, [o]).disposition, "HOLD_RESULT_UNBOUND")

    def test_bound_result_admissible(self):
        c = self.cmd()
        o = CommandObservation(c.command_id, "RESULT", c.owner_ref, c.exact_head, "lease", "semantic")
        self.assertEqual(self.compiler().observe(c, [o]).disposition, "P0_RESULT_ADMISSIBLE")

    def test_observation_head_drift_fails(self):
        c = self.cmd()
        o = CommandObservation(c.command_id, "ACKED", c.owner_ref, "other")
        with self.assertRaisesRegex(ValueError, "COMMAND_TARGET_DRIFT"):
            self.compiler().observe(c, [o])

    def test_observation_owner_drift_fails(self):
        c = self.cmd()
        o = CommandObservation(c.command_id, "ACKED", "github://x/y/pull/1", c.exact_head)
        with self.assertRaisesRegex(ValueError, "COMMAND_TARGET_DRIFT"):
            self.compiler().observe(c, [o])

    def test_observation_effect_widening_fails(self):
        c = self.cmd()
        o = CommandObservation(c.command_id, "ACKED", c.owner_ref, c.exact_head, effect_authority=True)
        with self.assertRaisesRegex(ValueError, "OBSERVATION_AUTHORITY_WIDENING"):
            self.compiler().observe(c, [o])

    def test_actual_command_state_fixture_is_materialized_only(self):
        c = self.cmd()
        o = CommandObservation(c.command_id, "MATERIALIZED", c.owner_ref, c.exact_head)
        r = self.compiler().observe(c, [o])
        self.assertEqual((r.evidence_state, r.effect_authority), ("MATERIALIZED", False))

    def test_random_authority_laundering(self):
        rng = random.Random(27)
        for i in range(1000):
            auth = "AUTHORIZED" if i % 5 == 0 else rng.choice(["UNKNOWN", "PROHIBITED", "DENIED"])
            t = replace(self.target(), authorization=auth)
            if auth == "AUTHORIZED":
                c = self.compiler().compile(self.lead(), t, command_id=f"c{i}")
                self.assertEqual(c.effect_ceiling, "D0")
            else:
                with self.assertRaises(ValueError):
                    self.compiler().compile(self.lead(), t, command_id=f"c{i}")


if __name__ == "__main__":
    unittest.main()
