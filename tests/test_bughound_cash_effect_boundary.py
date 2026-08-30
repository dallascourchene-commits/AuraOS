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


REMOVED = (
    "target_specific_material",
    "credentials_or_tokens",
    "private_endpoint",
    "undisclosed_exploit_material",
    "pii_or_third_party_data",
    "private_report_identifier",
)


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
        )
        values.update(changes)
        return BountyLiveEffectGrantV1(**values)

    def sanitized(self, mission, **changes):
        values = dict(
            mission_receipt_digest=mission.receipt_digest,
            disclosure_state_ref="private-undisclosed-candidate",
            reusable_memory_policy_ref="bughound-sanitized-pattern-v1",
            sanitizer_generation="sanitizer-v2",
            reviewer_ref="independent-reviewer-v2",
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

    def test_cash_mission_receipt_itself_grants_no_live_effect(self):
        mission = self.mission()
        self.assertTrue(mission.cash_bounty_mission_admitted)
        self.assertFalse(mission.live_target_testing_authorized)
        self.assertFalse(mission.credential_use_authorized)
        self.assertFalse(mission.submission_authorized)
        self.assertFalse(mission.claim_or_payment_authorized)
        self.assertFalse(mission.external_effect)

    def test_shared_local_tool_is_capability_not_mission_or_authority(self):
        mission = self.mission()
        tool = SharedSecurityToolCapabilityV1(
            capability_id="SOURCE_GRAPH_ADAPTER@v2",
            contexts=(CANONICAL_PROFILE_ID, "AURAOS_SECURITY_HARDENING_REUSE"),
        )
        self.assertTrue(admit_shared_tool_for_cash_research(mission, tool))
        self.assertIn("AURAOS_SECURITY_HARDENING_REUSE", tool.contexts)
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

    def test_exact_current_live_grant_admits_only_named_test_authority(self):
        mission = self.mission()
        admission = admit_live_effect(mission, self.live_grant(mission))
        self.assertTrue(admission.live_effect_authorized)
        self.assertEqual("EXACT_NAMED_LIVE_TEST_ONLY", admission.authority_scope)
        self.assertFalse(admission.submission_authorized)
        self.assertFalse(admission.claim_or_payment_authorized)
        self.assertFalse(admission.external_effect_executed)

    def test_live_grant_must_bind_exact_mission_program_target_and_origin(self):
        mission = self.mission()
        cases = (
            ("mission_receipt_digest", "0" * 64, "LIVE_GRANT_MISSION_RECEIPT_MISMATCH"),
            ("program_ref", "program:other", "LIVE_GRANT_PROGRAM_MISMATCH"),
            ("target_generation", "deploy-41", "LIVE_GRANT_TARGET_MISMATCH"),
            ("network_origin", "https://third-party.example", "LIVE_GRANT_ORIGIN_NOT_ALLOWLISTED"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    admit_live_effect(mission, self.live_grant(mission, **{field: value}))
                self.assertEqual(code, ctx.exception.code)

    def test_stale_program_policy_and_noncanonical_profile_fail_closed(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, self.live_grant(mission, program_policy_current=False))
        self.assertEqual("LIVE_GRANT_PROGRAM_POLICY_STALE", ctx.exception.code)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, self.live_grant(mission, profile_id="AURAOS_INTERNAL"))
        self.assertEqual("LIVE_GRANT_NONCANONICAL_PROFILE", ctx.exception.code)

    def test_sanitized_pattern_can_leave_bughound_only_as_authority_free_abstraction(self):
        mission = self.mission()
        export = export_sanitized_pattern(
            mission,
            self.sanitized(mission),
            destination_context="AURAOS_SECURITY_HARDENING_REUSE",
        )
        self.assertIn(export.destination_context, GENERIC_REUSE_CONTEXTS)
        self.assertFalse(export.bughound_mission_state_exported)
        self.assertFalse(export.payout_state_exported)
        self.assertFalse(export.scope_authority_exported)
        self.assertFalse(export.live_effect_authority_exported)
        self.assertFalse(export.disclosure_authority_exported)
        self.assertFalse(export.credential_state_exported)
        self.assertFalse(export.authority)
        self.assertFalse(export.external_effect)

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
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    export_sanitized_pattern(
                        mission,
                        self.sanitized(mission, **{field: True}),
                        destination_context="GENERIC_SECURITY_TOOL_FOUNDRY",
                    )
                self.assertEqual("SANITIZED_PATTERN_PRIVATE_STATE_REMAINS", ctx.exception.code)

    def test_incomplete_sanitizer_coverage_and_unknown_destination_fail_closed(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                self.sanitized(mission, removed_classes=REMOVED[:-1]),
                destination_context="GENERIC_SECURITY_TOOL_FOUNDRY",
            )
        self.assertEqual("SANITIZED_REMOVAL_COVERAGE_INCOMPLETE", ctx.exception.code)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                self.sanitized(mission),
                destination_context="BUGHOUND_AURAOS_PROFILE",
            )
        self.assertEqual("REUSE_DESTINATION_CONTEXT_NOT_ADMITTED", ctx.exception.code)

    def test_sanitized_pattern_must_bind_exact_cash_mission(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                self.sanitized(mission, mission_receipt_digest="0" * 64),
                destination_context="GENERIC_SECURITY_TOOL_FOUNDRY",
            )
        self.assertEqual("SANITIZED_PATTERN_MISSION_MISMATCH", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
