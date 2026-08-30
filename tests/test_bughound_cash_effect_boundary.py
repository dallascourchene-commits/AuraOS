import unittest

from tools.bughound.bounty_mission import (
    CANONICAL_PROFILE_ID,
    BugHoundCashMissionInputV1,
    admit_cash_bounty_mission,
)
from tools.bughound.cash_effect_boundary import (
    BountyLiveEffectGrantV1,
    CashEffectBoundaryError,
    GENERIC_REUSE_CONTEXTS,
    LIVE_EFFECT_CLASS,
    SanitizedPatternReceiptV1,
    SharedSecurityToolCapabilityV1,
    admit_live_effect,
    admit_shared_tool_for_cash_research,
    export_sanitized_pattern,
)
from tools.bughound.target_profile import AURAOS_HARDENING_PROFILE_ID


REMOVED = (
    "target_specific_material",
    "credentials_or_tokens",
    "private_endpoint",
    "undisclosed_exploit_material",
    "pii_or_third_party_data",
    "private_report_identifier",
)
LIVE_PRODUCER_REF = "live-effect-owner-v1"
LIVE_PRODUCER_GENERATION = "live-effect-owner-gen-1"
SANITIZER_PRODUCER_REF = "sanitizer-service-v2"
SANITIZER_PRODUCER_GENERATION = "sanitizer-service-gen-2"
SANITIZER_REVIEWER_REF = "independent-reviewer-v2"


class CashEffectBoundaryTests(unittest.TestCase):
    def mission(self):
        return admit_cash_bounty_mission(
            BugHoundCashMissionInputV1(
                profile_id=CANONICAL_PROFILE_ID,
                program_ref="program:hackerone-example",
                target_ref="asset.example",
                target_generation="deploy-42",
                program_state="ACTIVE",
                cash_reward_state="VERIFIED_CURRENT_CASH_REWARD",
                reward_currency="USD",
                reward_floor_minor=10000,
                reward_ceiling_minor=500000,
                payout_rules_digest="payout-digest-v3",
                scope_state="CURRENT_SCOPE_BOUND",
                scope_rules_digest="scope-digest-v7",
                source_state="CURRENT_SOURCE_BOUND",
                source_currentness_ref="source-current-42",
                testing_ceiling="LOCAL_RESEARCH_ONLY",
            )
        )

    def live_grant(self, mission, **changes):
        values = dict(
            profile_id=CANONICAL_PROFILE_ID,
            mission_receipt_digest=mission.receipt_digest,
            program_ref=mission.program_ref,
            target_ref=mission.target_ref,
            target_generation=mission.target_generation,
            program_policy_snapshot_digest="program-policy-digest-9",
            program_policy_generation="program-policy-gen-9",
            program_policy_current=True,
            scope_rules_digest="scope-digest-v7",
            scope_currentness_ref="scope-current-9",
            target_currentness_ref="target-current-42",
            effect_class=LIVE_EFFECT_CLASS,
            network_origin="https://asset.example",
            network_allowlist=("https://asset.example",),
            credential_aliases=("program-test-token",),
            human_authorization_ref="human-gate-9",
            revocation_currentness_ref="revocation-current-9",
            disclosure_policy_ref="program-disclosure-4",
            producer_ref=LIVE_PRODUCER_REF,
            producer_generation=LIVE_PRODUCER_GENERATION,
            producer_currentness_ref="live-effect-owner-current-1",
        )
        values.update(changes)
        return BountyLiveEffectGrantV1(**values)

    def admit_live(
        self,
        mission,
        grant=None,
        *,
        expected_digest=None,
        expected_ref=LIVE_PRODUCER_REF,
        expected_generation=LIVE_PRODUCER_GENERATION,
    ):
        if grant is None:
            grant = self.live_grant(mission)
        if expected_digest is None:
            expected_digest = grant.grant_digest
        return admit_live_effect(
            mission,
            grant,
            expected_grant_digest=expected_digest,
            expected_producer_ref=expected_ref,
            expected_producer_generation=expected_generation,
        )

    def sanitized(self, mission, **changes):
        values = dict(
            mission_receipt_digest=mission.receipt_digest,
            disclosure_state_ref="private-undisclosed-candidate",
            reusable_memory_policy_ref="bughound-sanitized-pattern-v1",
            sanitizer_generation="sanitizer-v2",
            reviewer_ref=SANITIZER_REVIEWER_REF,
            producer_ref=SANITIZER_PRODUCER_REF,
            producer_generation=SANITIZER_PRODUCER_GENERATION,
            producer_currentness_ref="sanitizer-service-current-2",
            removed_classes=REMOVED,
            retained_abstract_pattern_ref="pattern:generation-validated-used-drift",
            target_specific_material_present=False,
            credentials_or_tokens_present=False,
            private_endpoint_present=False,
            undisclosed_exploit_material_present=False,
            pii_or_third_party_data_present=False,
            private_report_identifier_present=False,
        )
        values.update(changes)
        return SanitizedPatternReceiptV1(**values)

    def export_pattern(
        self,
        mission,
        sanitized=None,
        *,
        destination_context="GENERIC_SECURITY_TOOL_FOUNDRY",
        expected_digest=None,
        expected_ref=SANITIZER_PRODUCER_REF,
        expected_generation=SANITIZER_PRODUCER_GENERATION,
        expected_reviewer=SANITIZER_REVIEWER_REF,
    ):
        if sanitized is None:
            sanitized = self.sanitized(mission)
        if expected_digest is None:
            expected_digest = sanitized.receipt_digest
        return export_sanitized_pattern(
            mission,
            sanitized,
            destination_context=destination_context,
            expected_sanitized_receipt_digest=expected_digest,
            expected_producer_ref=expected_ref,
            expected_producer_generation=expected_generation,
            expected_reviewer_ref=expected_reviewer,
        )

    def test_cash_mission_receipt_itself_grants_no_live_effect(self):
        mission = self.mission()
        self.assertTrue(mission.cash_bounty_mission_admitted)
        self.assertFalse(mission.live_target_testing_authorized)
        self.assertFalse(mission.credential_use_authorized)
        self.assertFalse(mission.submission_authorized)
        self.assertFalse(mission.claim_or_payment_authorized)
        self.assertFalse(mission.external_effect)

    def test_shared_local_tool_is_capability_not_cross_profile_authority(self):
        mission = self.mission()
        tool = SharedSecurityToolCapabilityV1(
            capability_id="SOURCE_GRAPH_ADAPTER@v2",
            contexts=(CANONICAL_PROFILE_ID, AURAOS_HARDENING_PROFILE_ID),
        )
        self.assertTrue(admit_shared_tool_for_cash_research(mission, tool))
        self.assertIn(AURAOS_HARDENING_PROFILE_ID, tool.contexts)
        self.assertFalse(tool.authority)

    def test_effectful_shared_tool_needs_separate_live_grant(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_shared_tool_for_cash_research(
                mission,
                SharedSecurityToolCapabilityV1(
                    capability_id="WEB_PROTOCOL_ADAPTER@v2",
                    contexts=(CANONICAL_PROFILE_ID,),
                    local_only=False,
                    network_required=True,
                ),
            )
        self.assertEqual("EFFECTFUL_TOOL_REQUIRES_SEPARATE_LIVE_GRANT", ctx.exception.code)

    def test_shared_tool_cannot_self_grant_authority(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_shared_tool_for_cash_research(
                mission,
                SharedSecurityToolCapabilityV1(
                    capability_id="bad-authority-tool",
                    contexts=(CANONICAL_PROFILE_ID,),
                    authority=True,
                ),
            )
        self.assertEqual("TOOL_CAPABILITY_CANNOT_SELF_GRANT_AUTHORITY", ctx.exception.code)

    def test_exact_current_live_grant_admits_only_named_cash_profile_test_authority(self):
        mission = self.mission()
        admission = self.admit_live(mission)
        self.assertTrue(admission.live_effect_authorized)
        self.assertEqual("EXACT_NAMED_CASH_PROFILE_LIVE_TEST_ONLY", admission.authority_scope)
        self.assertEqual(LIVE_PRODUCER_REF, admission.producer_ref)
        self.assertEqual(LIVE_PRODUCER_GENERATION, admission.producer_generation)
        self.assertFalse(admission.submission_authorized)
        self.assertFalse(admission.claim_or_payment_authorized)
        self.assertFalse(admission.external_effect_executed)

    def test_live_grant_must_bind_exact_mission_program_and_target(self):
        mission = self.mission()
        legitimate = self.live_grant(mission)
        cases = (
            ("mission_receipt_digest", "0" * 64, "LIVE_GRANT_MISSION_RECEIPT_MISMATCH"),
            ("program_ref", "program:other", "LIVE_GRANT_PROGRAM_MISMATCH"),
            ("target_generation", "deploy-41", "LIVE_GRANT_TARGET_MISMATCH"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                forged = self.live_grant(mission, **{field: value})
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    self.admit_live(mission, forged, expected_digest=legitimate.grant_digest)
                self.assertEqual(code, ctx.exception.code)

    def test_self_consistent_forged_live_grant_fails_independent_expectation(self):
        mission = self.mission()
        legitimate = self.live_grant(mission)
        forged = self.live_grant(
            mission,
            scope_rules_digest="forged-scope-digest",
            network_allowlist=("https://asset.example", "https://extra.example"),
        )
        self.assertNotEqual(legitimate.grant_digest, forged.grant_digest)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.admit_live(mission, forged, expected_digest=legitimate.grant_digest)
        self.assertEqual("LIVE_GRANT_EXPECTATION_MISMATCH", ctx.exception.code)

    def test_wrong_live_grant_producer_identity_fails_closed(self):
        mission = self.mission()
        grant = self.live_grant(mission)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.admit_live(mission, grant, expected_ref="different-owner")
        self.assertEqual("LIVE_GRANT_PRODUCER_MISMATCH", ctx.exception.code)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.admit_live(mission, grant, expected_generation="different-generation")
        self.assertEqual("LIVE_GRANT_PRODUCER_MISMATCH", ctx.exception.code)

    def test_stale_program_policy_and_auraos_profile_live_grant_fail_closed(self):
        mission = self.mission()
        stale = self.live_grant(mission, program_policy_current=False)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.admit_live(mission, stale, expected_digest=stale.grant_digest)
        self.assertEqual("LIVE_GRANT_PROGRAM_POLICY_STALE", ctx.exception.code)
        aura = self.live_grant(mission, profile_id=AURAOS_HARDENING_PROFILE_ID)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.admit_live(mission, aura, expected_digest=aura.grant_digest)
        self.assertEqual("LIVE_GRANT_NON_CASH_PROFILE", ctx.exception.code)

    def test_sanitized_pattern_can_cross_to_auraos_profile_only_as_authority_free_abstraction(self):
        mission = self.mission()
        export = self.export_pattern(
            mission,
            destination_context=AURAOS_HARDENING_PROFILE_ID,
        )
        self.assertIn(export.destination_context, GENERIC_REUSE_CONTEXTS)
        self.assertTrue(export.cross_profile_reuse)
        self.assertEqual(CANONICAL_PROFILE_ID, export.source_cash_profile_id)
        self.assertEqual(SANITIZER_PRODUCER_REF, export.producer_ref)
        self.assertEqual(SANITIZER_PRODUCER_GENERATION, export.producer_generation)
        self.assertFalse(export.bughound_mission_state_exported)
        self.assertFalse(export.payout_state_exported)
        self.assertFalse(export.scope_authority_exported)
        self.assertFalse(export.live_effect_authority_exported)
        self.assertFalse(export.disclosure_authority_exported)
        self.assertFalse(export.credential_state_exported)
        self.assertFalse(export.authority)
        self.assertFalse(export.external_effect)

    def test_self_consistent_forged_sanitizer_receipt_fails_independent_expectation(self):
        mission = self.mission()
        legitimate = self.sanitized(mission)
        forged = self.sanitized(
            mission,
            retained_abstract_pattern_ref="pattern:forged-broader-abstraction",
        )
        self.assertNotEqual(legitimate.receipt_digest, forged.receipt_digest)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.export_pattern(mission, forged, expected_digest=legitimate.receipt_digest)
        self.assertEqual("SANITIZED_PATTERN_EXPECTATION_MISMATCH", ctx.exception.code)

    def test_wrong_sanitizer_producer_or_reviewer_fails_closed(self):
        mission = self.mission()
        sanitized = self.sanitized(mission)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.export_pattern(mission, sanitized, expected_ref="different-sanitizer")
        self.assertEqual("SANITIZED_PATTERN_PRODUCER_MISMATCH", ctx.exception.code)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.export_pattern(mission, sanitized, expected_reviewer="different-reviewer")
        self.assertEqual("SANITIZED_PATTERN_REVIEWER_MISMATCH", ctx.exception.code)

    def test_private_or_undisclosed_material_blocks_reusable_export(self):
        mission = self.mission()
        for field in (
            "target_specific_material_present",
            "credentials_or_tokens_present",
            "private_endpoint_present",
            "undisclosed_exploit_material_present",
            "pii_or_third_party_data_present",
            "private_report_identifier_present",
        ):
            with self.subTest(field=field):
                sanitized = self.sanitized(mission, **{field: True})
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    self.export_pattern(mission, sanitized, expected_digest=sanitized.receipt_digest)
                self.assertEqual("SANITIZED_PATTERN_PRIVATE_STATE_REMAINS", ctx.exception.code)

    def test_incomplete_sanitizer_coverage_and_unknown_destination_fail_closed(self):
        mission = self.mission()
        incomplete = self.sanitized(mission, removed_classes=REMOVED[:-1])
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.export_pattern(mission, incomplete, expected_digest=incomplete.receipt_digest)
        self.assertEqual("SANITIZED_REMOVAL_COVERAGE_INCOMPLETE", ctx.exception.code)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.export_pattern(mission, destination_context="UNREGISTERED_PROFILE")
        self.assertEqual("REUSE_DESTINATION_CONTEXT_NOT_ADMITTED", ctx.exception.code)

    def test_sanitized_pattern_must_bind_exact_cash_mission(self):
        mission = self.mission()
        mismatched = self.sanitized(mission, mission_receipt_digest="0" * 64)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            self.export_pattern(mission, mismatched, expected_digest=mismatched.receipt_digest)
        self.assertEqual("SANITIZED_PATTERN_MISSION_MISMATCH", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
