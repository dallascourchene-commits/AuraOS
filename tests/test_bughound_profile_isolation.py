import unittest

from tools.bughound.profile_isolation import (
    NETWORK_ALLOWLIST,
    NETWORK_OFF,
    PROFILE_AURAOS,
    PROFILE_BOUNTY,
    BountyLiveEffectGrantV1,
    BugHoundProfileEnvelopeV1,
    BugHoundToolAdapterPolicyV1,
    BugHypothesisProfileBindingV1,
    ProfileIsolationError,
    SanitizedPatternReceiptV1,
    admit_bounty_live_effect,
    admit_hypothesis,
    admit_sanitized_pattern,
    admit_tool,
    compile_profile,
)


SENSITIVE_CLASSES = (
    "target_specific_material",
    "credentials_or_tokens",
    "private_endpoint",
    "undisclosed_exploit_material",
    "pii_or_third_party_data",
    "private_report_identifier",
)


class ProfileIsolationContractTests(unittest.TestCase):
    def bounty_envelope(self, *, live=False, **changes):
        values = dict(
            profile_id=PROFILE_BOUNTY,
            target_owner="program-owner",
            target_ref="asset.example",
            target_generation="deploy-20260830.1",
            source_currentness_ref="program-snapshot-current",
            scope_policy_ref="program-scope-v7",
            allowed_effect_classes=(
                "LOCAL_ANALYSIS",
                "LOCAL_REPRODUCTION",
                *(("BOUNTY_LIVE_NETWORK_TEST",) if live else ()),
            ),
            forbidden_effect_classes=("AURAOS_REPO_MUTATION",),
            network_policy=NETWORK_ALLOWLIST if live else NETWORK_OFF,
            network_allowlist=("https://asset.example",) if live else (),
            credential_aliases=("bounty-test-token",) if live else (),
            disclosure_policy_ref="program-disclosure-v3",
            money_policy_ref="program-payout-v4",
            result_sink_ref="private-bounty-vault",
            reusable_memory_policy_ref="sanitized-pattern-v1",
        )
        values.update(changes)
        return BugHoundProfileEnvelopeV1(**values)

    def aura_envelope(self, **changes):
        values = dict(
            profile_id=PROFILE_AURAOS,
            target_owner="aura-owner",
            target_ref="dallascourchene-commits/AuraOS",
            target_generation="head-abc123",
            source_currentness_ref="git-head-current",
            scope_policy_ref="aura-internal-hardening-v1",
            allowed_effect_classes=(
                "LOCAL_ANALYSIS",
                "LOCAL_REPRODUCTION",
                "AURAOS_ISSUE_OR_PR_HANDOFF",
            ),
            forbidden_effect_classes=(
                "BOUNTY_LIVE_NETWORK_TEST",
                "BOUNTY_SUBMISSION",
                "BOUNTY_PAYOUT_CLAIM",
            ),
            network_policy=NETWORK_OFF,
            network_allowlist=(),
            credential_aliases=(),
            disclosure_policy_ref="aura-internal-only",
            money_policy_ref=None,
            result_sink_ref="aura-internal-arena",
            reusable_memory_policy_ref="sanitized-pattern-v1",
        )
        values.update(changes)
        return BugHoundProfileEnvelopeV1(**values)

    def clean_pattern(self, source_profile=PROFILE_BOUNTY, **changes):
        values = dict(
            source_profile_id=source_profile,
            reusable_memory_policy_ref="sanitized-pattern-v1",
            sanitizer_generation="sanitizer-v1",
            reviewer_ref="independent-review-v1",
            removed_classes=SENSITIVE_CLASSES,
            retained_pattern_ref="pattern:identity-currentness-mismatch",
            target_specific_material_present=False,
            credentials_or_tokens_present=False,
            private_endpoint_present=False,
            undisclosed_exploit_material_present=False,
            pii_or_third_party_data_present=False,
            private_report_identifier_present=False,
        )
        values.update(changes)
        return SanitizedPatternReceiptV1(**values)

    def test_bounty_and_aura_compile_to_distinct_non_authoritative_policies(self):
        bounty = compile_profile(self.bounty_envelope())
        aura = compile_profile(self.aura_envelope())
        self.assertNotEqual(bounty.policy_digest, aura.policy_digest)
        self.assertEqual(PROFILE_BOUNTY, bounty.profile_id)
        self.assertEqual(PROFILE_AURAOS, aura.profile_id)
        self.assertFalse(bounty.authority or bounty.external_effect)
        self.assertFalse(aura.authority or aura.external_effect)

    def test_bounty_requires_money_policy(self):
        with self.assertRaises(ProfileIsolationError) as ctx:
            compile_profile(self.bounty_envelope(money_policy_ref=None))
        self.assertEqual("BOUNTY_MONEY_POLICY_REQUIRED", ctx.exception.code)

    def test_aura_cannot_import_bounty_money_or_live_effect_authority(self):
        with self.assertRaises(ProfileIsolationError) as ctx:
            compile_profile(self.aura_envelope(money_policy_ref="payout-v1"))
        self.assertEqual("AURAOS_CANNOT_IMPORT_BOUNTY_MONEY_POLICY", ctx.exception.code)
        with self.assertRaises(ProfileIsolationError) as ctx:
            compile_profile(
                self.aura_envelope(
                    allowed_effect_classes=("LOCAL_ANALYSIS", "BOUNTY_LIVE_NETWORK_TEST")
                )
            )
        self.assertEqual("AURAOS_CANNOT_IMPORT_BOUNTY_AUTHORITY", ctx.exception.code)

    def test_bounty_cannot_import_auraos_repo_authority(self):
        with self.assertRaises(ProfileIsolationError) as ctx:
            compile_profile(
                self.bounty_envelope(
                    allowed_effect_classes=("LOCAL_ANALYSIS", "AURAOS_REPO_MUTATION")
                )
            )
        self.assertEqual("BOUNTY_CANNOT_IMPORT_AURAOS_AUTHORITY", ctx.exception.code)

    def test_hypothesis_profile_cast_and_effect_widening_fail_closed(self):
        policy = compile_profile(self.bounty_envelope())
        good = BugHypothesisProfileBindingV1(
            profile_id=PROFILE_BOUNTY,
            target_ref=policy.target_ref,
            target_generation=policy.target_generation,
            hypothesis_id="h1",
            effect_ceiling=("LOCAL_ANALYSIS",),
        )
        self.assertTrue(admit_hypothesis(policy, good))
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_hypothesis(
                policy,
                BugHypothesisProfileBindingV1(
                    profile_id=PROFILE_AURAOS,
                    target_ref=policy.target_ref,
                    target_generation=policy.target_generation,
                    hypothesis_id="h2",
                    effect_ceiling=("LOCAL_ANALYSIS",),
                ),
            )
        self.assertEqual("HYPOTHESIS_PROFILE_CAST_FORBIDDEN", ctx.exception.code)
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_hypothesis(
                policy,
                BugHypothesisProfileBindingV1(
                    profile_id=PROFILE_BOUNTY,
                    target_ref=policy.target_ref,
                    target_generation=policy.target_generation,
                    hypothesis_id="h3",
                    effect_ceiling=("BOUNTY_SUBMISSION",),
                ),
            )
        self.assertEqual("HYPOTHESIS_EFFECT_CEILING_WIDENS_PROFILE", ctx.exception.code)

    def test_shared_local_tool_is_capability_not_authority(self):
        tool = BugHoundToolAdapterPolicyV1(
            adapter_id="SOURCE_GRAPH_ADAPTER@v2",
            supported_profiles=(PROFILE_BOUNTY, PROFILE_AURAOS),
            required_effect_classes=("LOCAL_ANALYSIS",),
        )
        self.assertTrue(admit_tool(compile_profile(self.bounty_envelope()), tool))
        self.assertTrue(admit_tool(compile_profile(self.aura_envelope()), tool))
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_tool(
                compile_profile(self.aura_envelope()),
                BugHoundToolAdapterPolicyV1(
                    adapter_id="bad-authority-tool",
                    supported_profiles=(PROFILE_AURAOS,),
                    required_effect_classes=("LOCAL_ANALYSIS",),
                    authority=True,
                ),
            )
        self.assertEqual("TOOL_CAPABILITY_CANNOT_SELF_GRANT_AUTHORITY", ctx.exception.code)

    def test_network_tool_requires_bounty_allowlist_policy(self):
        tool = BugHoundToolAdapterPolicyV1(
            adapter_id="WEB_PROTOCOL_ADAPTER@v2",
            supported_profiles=(PROFILE_BOUNTY,),
            required_effect_classes=("BOUNTY_LIVE_NETWORK_TEST",),
            network_required=True,
            credential_aliases_required=("bounty-test-token",),
        )
        self.assertTrue(admit_tool(compile_profile(self.bounty_envelope(live=True)), tool))
        with self.assertRaises(ProfileIsolationError):
            admit_tool(compile_profile(self.bounty_envelope(live=False)), tool)
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_tool(compile_profile(self.aura_envelope()), tool)
        self.assertEqual("TOOL_PROFILE_UNSUPPORTED", ctx.exception.code)

    def test_bounty_live_effect_requires_exact_profile_target_scope_origin_and_credentials(self):
        policy = compile_profile(self.bounty_envelope(live=True))
        grant = BountyLiveEffectGrantV1(
            profile_id=PROFILE_BOUNTY,
            target_ref=policy.target_ref,
            target_generation=policy.target_generation,
            scope_policy_ref=policy.scope_policy_ref,
            program_policy_currentness_ref="program-policy-current-42",
            effect_class="BOUNTY_LIVE_NETWORK_TEST",
            network_origin="https://asset.example",
            credential_aliases=("bounty-test-token",),
            human_authorization_ref="human-gate-42",
        )
        self.assertTrue(admit_bounty_live_effect(policy, grant))
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_bounty_live_effect(
                policy,
                BountyLiveEffectGrantV1(
                    **{**grant.__dict__, "network_origin": "https://third-party.example"}
                ),
            )
        self.assertEqual("BOUNTY_LIVE_NETWORK_ORIGIN_NOT_ALLOWED", ctx.exception.code)
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_bounty_live_effect(compile_profile(self.aura_envelope()), grant)
        self.assertEqual("BOUNTY_LIVE_EFFECT_PROFILE_REQUIRED", ctx.exception.code)

    def test_network_off_cannot_smuggle_allowlist(self):
        with self.assertRaises(ProfileIsolationError) as ctx:
            compile_profile(
                self.bounty_envelope(
                    network_policy=NETWORK_OFF,
                    network_allowlist=("https://asset.example",),
                )
            )
        self.assertEqual("NETWORK_OFF_REQUIRES_EMPTY_ALLOWLIST", ctx.exception.code)

    def test_sanitized_pattern_can_cross_profiles_only_after_full_declassification(self):
        bounty = compile_profile(self.bounty_envelope())
        receipt = self.clean_pattern()
        self.assertTrue(
            admit_sanitized_pattern(
                bounty,
                receipt,
                destination_profile_id=PROFILE_AURAOS,
            )
        )
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_sanitized_pattern(
                bounty,
                self.clean_pattern(undisclosed_exploit_material_present=True),
                destination_profile_id=PROFILE_AURAOS,
            )
        self.assertEqual("SANITIZED_PATTERN_STILL_CONTAINS_PRIVATE_STATE", ctx.exception.code)

    def test_sanitized_pattern_requires_complete_removal_coverage(self):
        bounty = compile_profile(self.bounty_envelope())
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_sanitized_pattern(
                bounty,
                self.clean_pattern(removed_classes=SENSITIVE_CLASSES[:-1]),
                destination_profile_id=PROFILE_AURAOS,
            )
        self.assertEqual("SANITIZED_PATTERN_REMOVAL_COVERAGE_INCOMPLETE", ctx.exception.code)

    def test_source_profile_and_memory_policy_remain_bound_during_cross_profile_reuse(self):
        bounty = compile_profile(self.bounty_envelope())
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_sanitized_pattern(
                bounty,
                self.clean_pattern(source_profile=PROFILE_AURAOS),
                destination_profile_id=PROFILE_AURAOS,
            )
        self.assertEqual("SANITIZED_PATTERN_SOURCE_PROFILE_MISMATCH", ctx.exception.code)
        with self.assertRaises(ProfileIsolationError) as ctx:
            admit_sanitized_pattern(
                bounty,
                self.clean_pattern(reusable_memory_policy_ref="different-policy"),
                destination_profile_id=PROFILE_AURAOS,
            )
        self.assertEqual("SANITIZED_PATTERN_MEMORY_POLICY_MISMATCH", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
