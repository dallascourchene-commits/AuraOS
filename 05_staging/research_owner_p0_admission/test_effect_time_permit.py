from dataclasses import replace
import random
import unittest

from effect_time_permit import *


class Tests(unittest.TestCase):
    def setUp(self):
        self.compiler = EffectTimePermitCompiler()
        self.target = EffectTarget(
            "github://dallascourchene-commits/AuraOS/pull/311",
            "head-new",
            "head-new",
            "pr311:g1+tiny",
            "AUTHORIZED",
        )
        self.keys = (
            ClaimKey("AWJ032", "PR311", "G1_SOURCE_SECURITY", "SOURCE_SECURITY"),
            ClaimKey("AWJ032", "AIRLLM_TINY", "HARD_FALSE_FIXTURE_RUNTIME", "RUNTIME_CAPABILITY"),
        )
        self.evidence = (
            ClaimEvidence(self.keys[0], "github:run:g1", "g1-gen", "sem-g1", "github-actions", "D0_HOSTED"),
            ClaimEvidence(self.keys[1], "github:run:tiny", "tiny-gen", "sem-tiny", "github-actions", "D0_HOSTED"),
        )
        self.refs = ("github://pull/311", "github://run/g1", "github://run/tiny")

    def permit(self):
        return self.compiler.compile(self.target, self.keys, self.evidence, reopen_refs=self.refs)

    def test_live_exact_authorized_ready(self):
        self.assertEqual(self.compiler.assess_target(self.target).state, "READY_FOR_CLAIM_EVIDENCE")

    def test_stale_materialized_command_invalidates(self):
        target = replace(self.target, command_head="old")
        self.assertEqual(self.compiler.assess_target(target).state, "INVALIDATE_STALE_COMMAND")

    def test_no_silent_retarget(self):
        with self.assertRaisesRegex(ValueError, "INVALIDATE_STALE_COMMAND"):
            self.compiler.compile(replace(self.target, command_head="old"), self.keys, self.evidence, reopen_refs=self.refs)

    def test_owner_reauthorization_required(self):
        target = replace(self.target, owner_authorization="UNKNOWN")
        self.assertEqual(self.compiler.assess_target(target).state, "OWNER_REAUTHORIZATION_REQUIRED")

    def test_stale_target_holds(self):
        self.assertEqual(self.compiler.assess_target(replace(self.target, target_current=False)).state, "HOLD_TARGET_STALE")

    def test_missing_claim_blocks(self):
        with self.assertRaisesRegex(ValueError, "MISSING_REQUIRED_CLAIM_EVIDENCE"):
            self.compiler.compile(self.target, self.keys, self.evidence[:1], reopen_refs=self.refs)

    def test_same_domain_wrong_claim_does_not_pay_debt(self):
        wrong = ClaimEvidence(
            ClaimKey("AWJ032", "OTHER", "OTHER_RUNTIME", "RUNTIME_CAPABILITY"),
            "x", "g", "s", "p", "D0_HOSTED"
        )
        with self.assertRaisesRegex(ValueError, "UNREQUESTED_CLAIM_EVIDENCE"):
            self.compiler.compile(self.target, self.keys, (self.evidence[0], wrong), reopen_refs=self.refs)

    def test_stale_evidence_blocks(self):
        with self.assertRaisesRegex(ValueError, "CLAIM_EVIDENCE_STALE"):
            self.compiler.compile(self.target, self.keys, (self.evidence[0], replace(self.evidence[1], current=False)), reopen_refs=self.refs)

    def test_conflicting_duplicate_blocks(self):
        conflict = replace(self.evidence[0], semantic_root="other")
        with self.assertRaisesRegex(ValueError, "CONFLICTING_CLAIM_EVIDENCE"):
            self.compiler.compile(self.target, self.keys, (*self.evidence, conflict), reopen_refs=self.refs)

    def test_missing_reopen_refs_blocks(self):
        with self.assertRaisesRegex(ValueError, "REOPEN_REFS_REQUIRED"):
            self.compiler.compile(self.target, self.keys, self.evidence, reopen_refs=())

    def test_compressed_permit_has_no_authority(self):
        permit = self.permit()
        self.assertFalse(permit.effect_authority)
        self.assertFalse(permit.gate10)

    def test_equivalence_witness_passes(self):
        witness = self.compiler.verify_equivalence(self.target, self.keys, self.evidence, self.permit(), reopen_refs=self.refs)
        self.assertTrue(witness.protected_semantics_preserved)
        self.assertEqual(witness.disposition, "EQUIVALENT_READY_TO_COMPILE_P0")

    def test_compressed_tamper_fails(self):
        with self.assertRaisesRegex(ValueError, "COMPRESSED_PERMIT_NOT_EQUIVALENT"):
            self.compiler.verify_equivalence(self.target, self.keys, self.evidence, replace(self.permit(), exact_head="other"), reopen_refs=self.refs)

    def test_claim_change_changes_root(self):
        permit = self.permit()
        evidence = (self.evidence[0], replace(self.evidence[1], semantic_root="new"))
        self.assertNotEqual(permit.commitment_root, self.compiler.compile(self.target, self.keys, evidence, reopen_refs=self.refs).commitment_root)

    def test_head_change_changes_or_invalidates(self):
        with self.assertRaisesRegex(ValueError, "INVALIDATE_STALE_COMMAND"):
            self.compiler.compile(replace(self.target, live_head="next"), self.keys, self.evidence, reopen_refs=self.refs)

    def test_live_awj032_fixture_requires_owner_reauth(self):
        live = EffectTarget(
            "github://dallascourchene-commits/AuraOS/pull/311",
            "d951404e0ba15a04682f47610f4643ce55d9ff7e",
            "d422ca4742888fc5fa3ba025c295ed145a3316cb",
            "pr311:g1+tiny",
            "UNKNOWN",
        )
        self.assertEqual(self.compiler.assess_target(live).state, "INVALIDATE_STALE_COMMAND")
        current = replace(live, command_head=live.live_head)
        self.assertEqual(self.compiler.assess_target(current).state, "OWNER_REAUTHORIZATION_REQUIRED")

    def test_randomized_no_laundering(self):
        rng = random.Random(27013)
        for i in range(1000):
            live = f"h{rng.randrange(7)}"
            cmd = live if rng.randrange(3) else f"h{(int(live[1:])+1)%7}"
            auth = "AUTHORIZED" if rng.randrange(4) == 0 else rng.choice(["UNKNOWN", "DENIED", "STALE"])
            target = replace(self.target, command_head=cmd, live_head=live, owner_authorization=auth)
            state = self.compiler.assess_target(target).state
            if cmd != live:
                self.assertEqual(state, "INVALIDATE_STALE_COMMAND")
            elif auth != "AUTHORIZED":
                self.assertEqual(state, "OWNER_REAUTHORIZATION_REQUIRED")
            else:
                self.assertEqual(state, "READY_FOR_CLAIM_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
