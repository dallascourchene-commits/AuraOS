import inspect
import unittest

from tools.bughound.authority_registry import (
    REGISTRY_GENERATION,
    authority_registry_receipt,
)
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
    validate_live_effect_request,
    validate_sanitized_pattern,
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
                duplicate_pressure_state="LOW",
            )
        )

    def live_grant(self, mission, **changes):
        values = dict(
            profile_id=CANONICAL_PROFILE_ID,
            mission_receipt_digest=mission.receipt_digest,
            program_ref=mission.program_ref,
            target_ref=mission.target_ref,
            target_generation=mission.target_generation,
            payout_rules_digest=mission.payout_rules_digest,
            scope_rules_digest=mission.scope_rules_digest,
            source_currentness_ref=mission.source_currentness_ref,
            program_policy_snapshot_digest="program-policy-digest-9",
            program_policy_generation="program-policy-gen-9",
            program_policy_current=True,
            scope_currentness_ref="scope-current-9",
            target_currentness_ref="target-current-42",
            effect_class=LIVE_EFFECT_CLASS,
            network_origin="https://asset.example",
            network_allowlist=("https://asset.example",),
            credential_aliases=("program-test-token",),
            human_authorization_ref="human-gate-9",
            human_authorization_generation="human-auth-gen-9",
            human_authorization_currentness_ref="human-auth-current-9",
            human_authorization_expiry_ref="expires-2026-08-31T00:00:00Z",
            human_authorization_revocation_currentness_ref="human-auth-revocation-current-9",
            revocation_currentness_ref="program-revocation-current-9",
            disclosure_policy_ref="program-disclosure-4",
            producer_ref=LIVE_PRODUCER_REF,
            producer_generation=LIVE_PRODUCER_GENERATION,
            producer_run_ref="live-effect-run-1",
            producer_currentness_ref="live-effect-owner-current-1",
        )
        values.update(changes)
        return BountyLiveEffectGrantV1(**values)

    def sanitized(self, mission, **changes):
        values = dict(
            mission_receipt_digest=mission.receipt_digest,
            disclosure_state_ref="private-undisclosed-candidate",
            reusable_memory_policy_ref="bughound-sanitized-pattern-v1",
            sanitizer_generation="sanitizer-v2",
            reviewer_ref=SANITIZER_REVIEWER_REF,
            reviewer_generation="reviewer-gen-2",
            reviewer_currentness_ref="reviewer-current-2",
            producer_ref=SANITIZER_PRODUCER_REF,
            producer_generation=SANITIZER_PRODUCER_GENERATION,
            producer_run_ref="sanitizer-run-2",
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

    def test_cash_mission_retains_exact_bindings_but_grants_no_live_effect(self):
        mission = self.mission()
        self.assertEqual("payout-digest-v3", mission.payout_rules_digest)
        self.assertEqual("scope-digest-v7", mission.scope_rules_digest)
        self.assertEqual("source-current-42", mission.source_currentness_ref)
        self.assertEqual("USD", mission.reward_currency)
        self.assertEqual("LOW", mission.duplicate_pressure_state)
        self.assertTrue(mission.cash_bounty_mission_admitted)
        self.assertFalse(mission.live_target_testing_authorized)
        self.assertFalse(mission.credential_use_authorized)
        self.assertFalse(mission.submission_authorized)
        self.assertFalse(mission.claim_or_payment_authorized)
        self.assertFalse(mission.external_effect)

    def test_authority_registry_is_source_owned_hold_with_zero_producers(self):
        registry = authority_registry_receipt()
        self.assertEqual(REGISTRY_GENERATION, registry.registry_generation)
        self.assertEqual(0, registry.live_effect_producer_count)
        self.assertEqual(0, registry.sanitizer_producer_count)
        self.assertEqual((), registry.record_digests)
        self.assertFalse(registry.authority)
        self.assertFalse(registry.external_effect)

    def test_canonical_apis_have_no_caller_expected_or_registry_override_parameters(self):
        live_params = inspect.signature(admit_live_effect).parameters
        export_params = inspect.signature(export_sanitized_pattern).parameters
        for name in live_params:
            self.assertFalse(name.startswith("expected_"), name)
            self.assertNotIn("registry", name)
        for name in export_params:
            self.assertFalse(name.startswith("expected_"), name)
            self.assertNotIn("registry", name)

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

    def test_valid_live_request_stays_lower_plane_until_registry_trust_exists(self):
        mission = self.mission()
        grant = self.live_grant(mission)
        validated = validate_live_effect_request(mission, grant)
        self.assertTrue(validated.mission_scope_bound)
        self.assertTrue(validated.mission_source_bound)
        self.assertTrue(validated.mission_payout_policy_bound)
        self.assertTrue(validated.human_authorization_shape_current)
        self.assertFalse(validated.producer_trust_proven)
        self.assertFalse(validated.live_effect_authorized)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, grant)
        self.assertEqual("LIVE_EFFECT_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)

    def test_self_consistent_caller_grant_cannot_create_registry_trust(self):
        mission = self.mission()
        forged = self.live_grant(
            mission,
            producer_ref="caller-chosen-owner",
            producer_generation="caller-chosen-generation",
            producer_run_ref="caller-run",
            producer_currentness_ref="caller-current",
        )
        self.assertTrue(forged.grant_digest)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, forged)
        self.assertEqual("LIVE_EFFECT_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)

    def test_human_authorization_is_mandatory_before_registry_resolution(self):
        mission = self.mission()
        fields = (
            ("human_authorization_ref", "", "LIVE_GRANT_HUMAN_AUTHORIZATION_REQUIRED"),
            ("human_authorization_generation", "", "LIVE_GRANT_HUMAN_AUTH_GENERATION_REQUIRED"),
            ("human_authorization_currentness_ref", "", "LIVE_GRANT_HUMAN_AUTH_CURRENTNESS_REQUIRED"),
            ("human_authorization_expiry_ref", "", "LIVE_GRANT_HUMAN_AUTH_EXPIRY_REQUIRED"),
            (
                "human_authorization_revocation_currentness_ref",
                "",
                "LIVE_GRANT_HUMAN_AUTH_REVOCATION_REQUIRED",
            ),
        )
        for field, value, code in fields:
            with self.subTest(field=field):
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    validate_live_effect_request(mission, self.live_grant(mission, **{field: value}))
                self.assertEqual(code, ctx.exception.code)

    def test_live_grant_must_equal_exact_mission_scope_source_and_payout_bindings(self):
        mission = self.mission()
        cases = (
            ("payout_rules_digest", "payout-digest-other", "LIVE_GRANT_PAYOUT_POLICY_MISMATCH"),
            ("scope_rules_digest", "scope-digest-other", "LIVE_GRANT_SCOPE_RULES_MISMATCH"),
            (
                "source_currentness_ref",
                "source-current-other",
                "LIVE_GRANT_SOURCE_CURRENTNESS_MISMATCH",
            ),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    validate_live_effect_request(mission, self.live_grant(mission, **{field: value}))
                self.assertEqual(code, ctx.exception.code)

    def test_live_grant_must_bind_exact_mission_program_target_and_profile(self):
        mission = self.mission()
        cases = (
            ("mission_receipt_digest", "0" * 64, "LIVE_GRANT_MISSION_RECEIPT_MISMATCH"),
            ("program_ref", "program:other", "LIVE_GRANT_PROGRAM_MISMATCH"),
            ("target_generation", "deploy-41", "LIVE_GRANT_TARGET_MISMATCH"),
            ("profile_id", AURAOS_HARDENING_PROFILE_ID, "LIVE_GRANT_NON_CASH_PROFILE"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    validate_live_effect_request(mission, self.live_grant(mission, **{field: value}))
                self.assertEqual(code, ctx.exception.code)

    def test_stale_policy_and_wrong_origin_fail_before_registry_resolution(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            validate_live_effect_request(
                mission,
                self.live_grant(mission, program_policy_current=False),
            )
        self.assertEqual("LIVE_GRANT_PROGRAM_POLICY_STALE", ctx.exception.code)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            validate_live_effect_request(
                mission,
                self.live_grant(mission, network_origin="https://third-party.example"),
            )
        self.assertEqual("LIVE_GRANT_ORIGIN_NOT_ALLOWLISTED", ctx.exception.code)

    def test_clean_sanitized_pattern_validates_but_cannot_export_without_registry_trust(self):
        mission = self.mission()
        sanitized = self.sanitized(mission)
        validated = validate_sanitized_pattern(
            mission,
            sanitized,
            destination_context=AURAOS_HARDENING_PROFILE_ID,
        )
        self.assertTrue(validated.private_state_removed)
        self.assertTrue(validated.removal_coverage_complete)
        self.assertFalse(validated.producer_trust_proven)
        self.assertFalse(validated.cross_profile_export_authorized)
        self.assertIn(validated.destination_context, GENERIC_REUSE_CONTEXTS)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                sanitized,
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
        self.assertEqual("SANITIZER_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)

    def test_self_consistent_caller_sanitizer_cannot_create_registry_trust(self):
        mission = self.mission()
        sanitized = self.sanitized(
            mission,
            producer_ref="caller-sanitizer",
            producer_generation="caller-generation",
            reviewer_ref="caller-reviewer",
            reviewer_generation="caller-reviewer-generation",
        )
        self.assertTrue(sanitized.receipt_digest)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                sanitized,
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
        self.assertEqual("SANITIZER_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)

    def test_private_or_undisclosed_material_blocks_even_lower_plane_validation(self):
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
                    validate_sanitized_pattern(
                        mission,
                        self.sanitized(mission, **{field: True}),
                        destination_context=AURAOS_HARDENING_PROFILE_ID,
                    )
                self.assertEqual("SANITIZED_PATTERN_PRIVATE_STATE_REMAINS", ctx.exception.code)

    def test_incomplete_sanitizer_coverage_and_unknown_destination_fail_closed(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            validate_sanitized_pattern(
                mission,
                self.sanitized(mission, removed_classes=REMOVED[:-1]),
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
        self.assertEqual("SANITIZED_REMOVAL_COVERAGE_INCOMPLETE", ctx.exception.code)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            validate_sanitized_pattern(
                mission,
                self.sanitized(mission),
                destination_context="UNREGISTERED_PROFILE",
            )
        self.assertEqual("REUSE_DESTINATION_CONTEXT_NOT_ADMITTED", ctx.exception.code)

    def test_sanitized_pattern_must_bind_exact_cash_mission_and_current_reviewer_shape(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            validate_sanitized_pattern(
                mission,
                self.sanitized(mission, mission_receipt_digest="0" * 64),
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
        self.assertEqual("SANITIZED_PATTERN_MISSION_MISMATCH", ctx.exception.code)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            validate_sanitized_pattern(
                mission,
                self.sanitized(mission, reviewer_currentness_ref=""),
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
        self.assertEqual("SANITIZER_REVIEWER_CURRENTNESS_REQUIRED", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
