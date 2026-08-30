from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from tools.bughound.authority_registry import (
    LIVE_EFFECT_PLANE,
    authority_registry_receipt,
    resolve_authority_producer,
    AuthorityRegistryError,
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
LIVE_PRODUCER_CURRENTNESS = "live-effect-owner-current-1"
SANITIZER_PRODUCER_REF = "sanitizer-service-v2"
SANITIZER_PRODUCER_GENERATION = "sanitizer-service-gen-2"
SANITIZER_PRODUCER_CURRENTNESS = "sanitizer-service-current-2"
SANITIZER_REVIEWER_REF = "independent-reviewer-v2"
SANITIZER_REVIEWER_GENERATION = "independent-reviewer-gen-2"
SANITIZER_REVIEWER_CURRENTNESS = "independent-reviewer-current-2"


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
            scope_rules_digest=mission.scope_rules_digest,
            scope_currentness_ref="scope-current-9",
            source_currentness_ref=mission.source_currentness_ref,
            target_currentness_ref="target-current-42",
            effect_class=LIVE_EFFECT_CLASS,
            network_origin="https://asset.example",
            network_allowlist=("https://asset.example",),
            credential_aliases=("program-test-token",),
            human_authorization_ref="human-gate-9",
            human_authorization_generation="human-gate-gen-9",
            human_authorization_currentness_ref="human-gate-current-9",
            human_authorization_expires_at="2026-08-31T23:59:59-04:00",
            human_authorization_not_expired=True,
            human_authorization_revocation_currentness_ref="human-revocation-current-9",
            human_authorization_not_revoked=True,
            revocation_currentness_ref="grant-revocation-current-9",
            disclosure_policy_ref="program-disclosure-4",
            producer_ref=LIVE_PRODUCER_REF,
            producer_generation=LIVE_PRODUCER_GENERATION,
            producer_currentness_ref=LIVE_PRODUCER_CURRENTNESS,
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
            reviewer_generation=SANITIZER_REVIEWER_GENERATION,
            reviewer_currentness_ref=SANITIZER_REVIEWER_CURRENTNESS,
            producer_ref=SANITIZER_PRODUCER_REF,
            producer_generation=SANITIZER_PRODUCER_GENERATION,
            producer_currentness_ref=SANITIZER_PRODUCER_CURRENTNESS,
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

    def test_cash_mission_receipt_retains_bindings_and_grants_no_live_effect(self):
        mission = self.mission()
        self.assertEqual(mission.payout_rules_digest, "payout-digest-v3")
        self.assertEqual(mission.scope_rules_digest, "scope-digest-v7")
        self.assertEqual(mission.source_currentness_ref, "source-current-42")
        self.assertFalse(mission.live_target_testing_authorized)
        self.assertFalse(mission.credential_use_authorized)
        self.assertFalse(mission.submission_authorized)
        self.assertFalse(mission.claim_or_payment_authorized)
        self.assertFalse(mission.external_effect)

    def test_shared_local_tool_remains_reusable_without_cross_profile_authority(self):
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

    def test_canonical_authority_registry_is_an_explicit_zero_record_hold(self):
        registry = authority_registry_receipt()
        self.assertEqual(registry.live_effect_producer_count, 0)
        self.assertEqual(registry.sanitizer_producer_count, 0)
        self.assertFalse(registry.authority)
        self.assertFalse(registry.external_effect)

    def test_live_effect_api_accepts_no_caller_expectation_or_registry(self):
        names = set(inspect.signature(admit_live_effect).parameters)
        self.assertEqual(names, {"receipt", "grant"})
        for forbidden in (
            "expected_grant_digest",
            "expected_producer_ref",
            "expected_producer_generation",
            "registry",
            "registry_lookup",
        ):
            self.assertNotIn(forbidden, names)

    def test_self_consistent_live_grant_cannot_promote_without_registry_artifact(self):
        mission = self.mission()
        grant = self.live_grant(mission)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, grant)
        self.assertEqual("LIVE_EFFECT_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)

    def test_copying_registered_looking_producer_identity_is_not_authentication(self):
        grant = self.live_grant(self.mission())
        with self.assertRaises(AuthorityRegistryError) as ctx:
            resolve_authority_producer(
                proof_plane=LIVE_EFFECT_PLANE,
                artifact_digest=grant.grant_digest,
                producer_ref=LIVE_PRODUCER_REF,
                producer_generation=LIVE_PRODUCER_GENERATION,
                producer_currentness_ref=LIVE_PRODUCER_CURRENTNESS,
            )
        self.assertEqual("LIVE_EFFECT_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)

    def test_human_authorization_is_required_before_registry_resolution(self):
        mission = self.mission()
        grant = self.live_grant(mission, human_authorization_ref=None)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, grant)
        self.assertEqual("LIVE_GRANT_HUMAN_AUTHORIZATION_REQUIRED", ctx.exception.code)

    def test_human_authorization_expiry_and_revocation_fail_closed(self):
        mission = self.mission()
        for field, code in (
            ("human_authorization_not_expired", "LIVE_GRANT_HUMAN_AUTHORIZATION_EXPIRED"),
            ("human_authorization_not_revoked", "LIVE_GRANT_HUMAN_AUTHORIZATION_REVOKED"),
        ):
            with self.subTest(field=field):
                grant = self.live_grant(mission, **{field: False})
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    admit_live_effect(mission, grant)
                self.assertEqual(code, ctx.exception.code)

    def test_live_grant_scope_must_equal_exact_mission_scope(self):
        mission = self.mission()
        grant = self.live_grant(mission, scope_rules_digest="scope-digest-other")
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, grant)
        self.assertEqual("LIVE_GRANT_SCOPE_MISMATCH", ctx.exception.code)

    def test_live_grant_source_currentness_must_equal_exact_mission_source(self):
        mission = self.mission()
        grant = self.live_grant(mission, source_currentness_ref="source-current-old")
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, grant)
        self.assertEqual("LIVE_GRANT_SOURCE_CURRENTNESS_MISMATCH", ctx.exception.code)

    def test_live_grant_program_target_profile_and_policy_still_fail_closed(self):
        mission = self.mission()
        cases = (
            (dict(profile_id=AURAOS_HARDENING_PROFILE_ID), "LIVE_GRANT_NON_CASH_PROFILE"),
            (dict(program_ref="program:other"), "LIVE_GRANT_PROGRAM_MISMATCH"),
            (dict(target_generation="deploy-old"), "LIVE_GRANT_TARGET_MISMATCH"),
            (dict(program_policy_current=False), "LIVE_GRANT_PROGRAM_POLICY_STALE"),
        )
        for changes, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    admit_live_effect(mission, self.live_grant(mission, **changes))
                self.assertEqual(code, ctx.exception.code)

    def test_live_grant_origin_must_be_allowlisted_before_trust_resolution(self):
        mission = self.mission()
        grant = self.live_grant(mission, network_allowlist=("https://other.example",))
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            admit_live_effect(mission, grant)
        self.assertEqual("LIVE_GRANT_ORIGIN_NOT_ALLOWLISTED", ctx.exception.code)

    def test_sanitized_export_api_accepts_no_caller_expectation_or_registry(self):
        names = set(inspect.signature(export_sanitized_pattern).parameters)
        self.assertEqual(names, {"receipt", "sanitized", "destination_context"})
        for forbidden in (
            "expected_sanitized_receipt_digest",
            "expected_producer_ref",
            "expected_producer_generation",
            "expected_reviewer_ref",
            "registry",
            "registry_lookup",
        ):
            self.assertNotIn(forbidden, names)

    def test_clean_sanitized_pattern_remains_held_without_registered_artifact(self):
        mission = self.mission()
        sanitized = self.sanitized(mission)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                sanitized,
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
        self.assertEqual("SANITIZER_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)

    def test_private_or_undisclosed_material_blocks_before_registry_resolution(self):
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
                    export_sanitized_pattern(
                        mission,
                        sanitized,
                        destination_context=AURAOS_HARDENING_PROFILE_ID,
                    )
                self.assertEqual("SANITIZED_PATTERN_PRIVATE_STATE_REMAINS", ctx.exception.code)

    def test_incomplete_sanitizer_coverage_fails_before_registry_resolution(self):
        mission = self.mission()
        sanitized = self.sanitized(mission, removed_classes=REMOVED[:-1])
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                sanitized,
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
        self.assertEqual("SANITIZED_REMOVAL_COVERAGE_INCOMPLETE", ctx.exception.code)

    def test_sanitizer_reviewer_generation_and_currentness_are_required(self):
        mission = self.mission()
        cases = (
            (dict(reviewer_generation=""), "SANITIZER_REVIEWER_GENERATION_REQUIRED"),
            (dict(reviewer_currentness_ref=""), "SANITIZER_REVIEWER_CURRENTNESS_REQUIRED"),
        )
        for changes, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(CashEffectBoundaryError) as ctx:
                    export_sanitized_pattern(
                        mission,
                        self.sanitized(mission, **changes),
                        destination_context=AURAOS_HARDENING_PROFILE_ID,
                    )
                self.assertEqual(code, ctx.exception.code)

    def test_unknown_reuse_destination_and_mission_mismatch_fail_closed(self):
        mission = self.mission()
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                self.sanitized(mission),
                destination_context="UNREGISTERED_PROFILE",
            )
        self.assertEqual("REUSE_DESTINATION_CONTEXT_NOT_ADMITTED", ctx.exception.code)

        mismatched = self.sanitized(mission, mission_receipt_digest="0" * 64)
        with self.assertRaises(CashEffectBoundaryError) as ctx:
            export_sanitized_pattern(
                mission,
                mismatched,
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
        self.assertEqual("SANITIZED_PATTERN_MISSION_MISMATCH", ctx.exception.code)

    def test_authority_artifact_digest_changes_with_human_or_pattern_content(self):
        mission = self.mission()
        a = self.live_grant(mission)
        b = self.live_grant(mission, human_authorization_generation="human-gate-gen-10")
        self.assertNotEqual(a.grant_digest, b.grant_digest)
        x = self.sanitized(mission)
        y = self.sanitized(
            mission, retained_abstract_pattern_ref="pattern:different-abstraction"
        )
        self.assertNotEqual(x.receipt_digest, y.receipt_digest)


if __name__ == "__main__":
    unittest.main()
