from __future__ import annotations

from dataclasses import replace
from unittest import mock
import unittest

import tools.bughound.authority_registry as registry_mod
from tools.bughound.authority_registry import (
    LIVE_EFFECT_PLANE,
    SANITIZER_PLANE,
    AuthorityProducerRecordV2,
)
from tools.bughound.bounty_mission import (
    CANONICAL_PROFILE_ID,
    BugHoundCashMissionInputV1,
    admit_cash_bounty_mission,
)
from tools.bughound.cash_effect_boundary import (
    BountyLiveEffectGrantV1,
    CashEffectBoundaryError,
    LIVE_EFFECT_CLASS,
    SanitizedPatternReceiptV1,
    admit_live_effect,
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


class AuthorityArtifactBindingTests(unittest.TestCase):
    def mission(self):
        return admit_cash_bounty_mission(
            BugHoundCashMissionInputV1(
                profile_id=CANONICAL_PROFILE_ID,
                program_ref="program:test",
                target_ref="asset.test",
                target_generation="deploy-1",
                program_state="ACTIVE",
                cash_reward_state="VERIFIED_CURRENT_CASH_REWARD",
                reward_currency="USD",
                reward_floor_minor=10000,
                reward_ceiling_minor=50000,
                payout_rules_digest="payout-v1",
                scope_state="CURRENT_SCOPE_BOUND",
                scope_rules_digest="scope-v1",
                source_state="CURRENT_SOURCE_BOUND",
                source_currentness_ref="source-v1",
                testing_ceiling="LOCAL_RESEARCH_ONLY",
            )
        )

    def grant(self, mission):
        return BountyLiveEffectGrantV1(
            profile_id=CANONICAL_PROFILE_ID,
            mission_receipt_digest=mission.receipt_digest,
            program_ref=mission.program_ref,
            target_ref=mission.target_ref,
            target_generation=mission.target_generation,
            payout_rules_digest=mission.payout_rules_digest,
            scope_rules_digest=mission.scope_rules_digest,
            source_currentness_ref=mission.source_currentness_ref,
            program_policy_snapshot_digest="policy-v1",
            program_policy_generation="policy-gen-1",
            program_policy_current=True,
            scope_currentness_ref="scope-current-1",
            target_currentness_ref="target-current-1",
            effect_class=LIVE_EFFECT_CLASS,
            network_origin="https://asset.test",
            network_allowlist=("https://asset.test",),
            credential_aliases=("test-token",),
            human_authorization_ref="human-gate-1",
            human_authorization_generation="human-gen-1",
            human_authorization_currentness_ref="human-current-1",
            human_authorization_expiry_ref="expiry-current-1",
            human_authorization_revocation_currentness_ref="human-revoke-current-1",
            revocation_currentness_ref="grant-revoke-current-1",
            disclosure_policy_ref="disclosure-v1",
            producer_ref="live-owner-v1",
            producer_generation="live-owner-gen-1",
            producer_run_ref="live-run-1",
            producer_currentness_ref="live-owner-current-1",
        )

    def sanitized(self, mission):
        return SanitizedPatternReceiptV1(
            mission_receipt_digest=mission.receipt_digest,
            disclosure_state_ref="private-candidate-1",
            reusable_memory_policy_ref="sanitized-policy-v1",
            sanitizer_generation="sanitizer-v1",
            reviewer_ref="reviewer-v1",
            reviewer_generation="reviewer-gen-1",
            reviewer_currentness_ref="reviewer-current-1",
            producer_ref="sanitizer-owner-v1",
            producer_generation="sanitizer-owner-gen-1",
            producer_run_ref="sanitizer-run-1",
            producer_currentness_ref="sanitizer-owner-current-1",
            removed_classes=REMOVED,
            retained_abstract_pattern_ref="pattern:abstract-v1",
            target_specific_material_present=False,
            credentials_or_tokens_present=False,
            private_endpoint_present=False,
            undisclosed_exploit_material_present=False,
            pii_or_third_party_data_present=False,
            private_report_identifier_present=False,
        )

    def test_registry_record_digest_changes_with_artifact_digest(self):
        base = AuthorityProducerRecordV2(
            proof_plane=LIVE_EFFECT_PLANE,
            artifact_digest="artifact-a",
            producer_ref="owner",
            producer_generation="gen",
            producer_currentness_ref="current",
        )
        changed = replace(base, artifact_digest="artifact-b")
        self.assertNotEqual(base.record_digest, changed.record_digest)

    def test_live_effect_consumer_requires_exact_registered_grant_artifact(self):
        mission = self.mission()
        grant = self.grant(mission)
        record = AuthorityProducerRecordV2(
            proof_plane=LIVE_EFFECT_PLANE,
            artifact_digest=grant.grant_digest,
            producer_ref=grant.producer_ref,
            producer_generation=grant.producer_generation,
            producer_currentness_ref=grant.producer_currentness_ref,
        )
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            admitted = admit_live_effect(mission, grant)
            self.assertTrue(admitted.live_effect_authorized)
            self.assertEqual(record.record_digest, admitted.authority_record_digest)

            forged = replace(
                grant,
                network_allowlist=("https://asset.test", "https://extra.test"),
            )
            self.assertNotEqual(grant.grant_digest, forged.grant_digest)
            with self.assertRaises(CashEffectBoundaryError) as ctx:
                admit_live_effect(mission, forged)
            self.assertEqual("LIVE_EFFECT_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)

    def test_sanitized_export_requires_exact_registered_pattern_artifact(self):
        mission = self.mission()
        sanitized = self.sanitized(mission)
        record = AuthorityProducerRecordV2(
            proof_plane=SANITIZER_PLANE,
            artifact_digest=sanitized.receipt_digest,
            producer_ref=sanitized.producer_ref,
            producer_generation=sanitized.producer_generation,
            producer_currentness_ref=sanitized.producer_currentness_ref,
            reviewer_ref=sanitized.reviewer_ref,
            reviewer_generation=sanitized.reviewer_generation,
            reviewer_currentness_ref=sanitized.reviewer_currentness_ref,
        )
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            export = export_sanitized_pattern(
                mission,
                sanitized,
                destination_context=AURAOS_HARDENING_PROFILE_ID,
            )
            self.assertTrue(export.cross_profile_reuse)
            self.assertEqual(record.record_digest, export.authority_record_digest)
            self.assertFalse(export.authority)
            self.assertFalse(export.external_effect)

            forged = replace(
                sanitized,
                retained_abstract_pattern_ref="pattern:broader-self-authored",
            )
            self.assertNotEqual(sanitized.receipt_digest, forged.receipt_digest)
            with self.assertRaises(CashEffectBoundaryError) as ctx:
                export_sanitized_pattern(
                    mission,
                    forged,
                    destination_context=AURAOS_HARDENING_PROFILE_ID,
                )
            self.assertEqual("SANITIZER_PRODUCER_TRUST_UNPROVEN", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
