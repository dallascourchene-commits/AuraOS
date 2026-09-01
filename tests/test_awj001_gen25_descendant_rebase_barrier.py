import dataclasses
import unittest

from tools.awj001 import awj001_gen25_descendant_rebase_barrier as p


class AWJ001Gen25DescendantRebaseBarrierTests(unittest.TestCase):
    def test_gen24_bound_workcapsule_rebases(self):
        r = p.assess_descendant(p.gen24_fixture())
        self.assertEqual(r.disposition, p.REBASE_ROOT_GENERATION)
        self.assertTrue(r.rebase_required)
        self.assertFalse(r.effect_authorized)

    def test_gen24_command_rebases(self):
        r = p.assess_descendant(p.gen24_fixture("COMMAND"))
        self.assertTrue(r.rebase_required)
        self.assertFalse(r.current_candidate)

    def test_matching_gen25_is_current_candidate_only(self):
        r = p.assess_descendant(p.gen25_fixture())
        self.assertEqual(r.disposition, p.CURRENT_CANDIDATE)
        self.assertTrue(r.current_candidate)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.host_effect_ready)
        self.assertFalse(r.inherited_root_authority)
        r.validate()

    def test_wrong_root_receipt_holds(self):
        ctx = dataclasses.replace(p.gen25_fixture(), root_receipt_drive_id="foreign")
        self.assertEqual(p.assess_descendant(ctx).disposition, p.HOLD_ROOT_RECEIPT)

    def test_same_generation_wrong_head_rebases(self):
        ctx = dataclasses.replace(p.gen25_fixture(), compiled_root_head="deadbeefdeadbeef")
        self.assertEqual(p.assess_descendant(ctx).disposition, p.REBASE_ROOT_HEAD)

    def test_temporal_owner_stale_rebases(self):
        ctx = dataclasses.replace(p.gen25_fixture(), temporal_owner_generation=24)
        self.assertEqual(p.assess_descendant(ctx).disposition, p.REBASE_TEMPORAL_OWNER)

    def test_host_observation_owner_stale_rebases(self):
        ctx = dataclasses.replace(p.gen25_fixture(), host_observation_owner_generation=24)
        self.assertEqual(p.assess_descendant(ctx).disposition, p.REBASE_HOST_OBSERVATION)

    def test_command_currentness_stale_rebases(self):
        ctx = dataclasses.replace(p.gen25_fixture(), command_bound_root_head="3aeb8f3db921201f")
        self.assertEqual(p.assess_descendant(ctx).disposition, p.REBASE_COMMAND)

    def test_lease_fence_stale_rebases(self):
        ctx = dataclasses.replace(p.gen25_fixture(), lease_fence_root_generation=24, lease_fence_root_head="3aeb8f3db921201f")
        self.assertEqual(p.assess_descendant(ctx).disposition, p.REBASE_LEASE)

    def test_effect_authority_request_holds(self):
        ctx = dataclasses.replace(p.gen25_fixture(), effect_authority_requested=True)
        self.assertEqual(p.assess_descendant(ctx).disposition, p.HOLD_CEILING)

    def test_receipt_digest_tamper_rejected(self):
        r = p.assess_descendant(p.gen25_fixture())
        bad = dataclasses.replace(r, receipt_digest="0" * 64)
        with self.assertRaises(ValueError):
            bad.validate()

    def test_resealed_effect_authority_rejected(self):
        r = p.assess_descendant(p.gen25_fixture())
        bad = dataclasses.replace(r, effect_authorized=True)
        with self.assertRaises(ValueError):
            bad.validate()

    def test_complete_eight_gate_different_j(self):
        self.assertEqual(p.prove_different_j(), 256)

    def test_exact_foreign_parent_coordinates(self):
        self.assertEqual(p.PARENT_HOST_HEAD, "26201c63c3531bbf631ef34803c6f01ccd7499d3")
        self.assertEqual(p.PARENT_HOST_RUN, 33355149887)
        self.assertEqual(p.PARENT_CAUSAL_HEAD, "5fae4070f82a9b5882ae0f63877359bf6e5a9a2b")
        self.assertEqual(p.PARENT_CAUSAL_RUN, 33354561517)
        self.assertEqual(p.CONVERGENCE_COMMIT, "cf9f66a7854b34111566c6f532ebf45af9a82343")

    def test_core_laws(self):
        self.assertIn("GEN24BoundDescendantUnderGEN25=>RebaseRequiredBeforeEffect", p.LAWS)
        self.assertIn("POST_CLOSED!=HOST_OBSERVATION_COMPLETE!=HOST_EFFECT_READY", p.LAWS)
        self.assertIn("RootAuthority!=InheritedDescendantAuthority", p.LAWS)
        self.assertIn("CoordinateMemory!=MODEL_PREFIX_KV", p.LAWS)


if __name__ == "__main__":
    unittest.main()
