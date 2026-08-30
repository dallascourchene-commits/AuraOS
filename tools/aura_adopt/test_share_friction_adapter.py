from __future__ import annotations

import copy
import unittest

from tools.aura_adopt.adoption_friction_receipt import StageStatus
from tools.aura_adopt.browser_friction_adapter import AcceptanceEvidenceMode
from tools.aura_adopt.test_browser_friction_adapter import (
    decision,
    observation,
    unknown_vector,
    weights,
)
from tools.aura_adopt import share_friction_adapter as bridge


def launch_plan(*, status="READY_FOR_USER_ACTION", blockers=None, **overrides):
    row = {
        "schema": "ShareLaunchPlanV1",
        "capsule_digest": "a" * 64,
        "capsule_id": "share:creator-title-card",
        "preferred_entry_surface": "ZERO_INSTALL_WEB_PWA",
        "next_surface": None,
        "creator_ref": "creator:1",
        "claimed_attribution_refs": ["creator:1"],
        "attribution_evidence_current": True,
        "attribution_identity_proven": False,
        "referral_depth": 0,
        "required_user_actions": [
            "OPEN_ENTRY_SURFACE",
            "REVIEW_PROVENANCE_AND_ATTRIBUTION",
            "CONFIRM_REPRODUCTION_INTENT",
        ],
        "blockers": [] if blockers is None and status == "READY_FOR_USER_ACTION" else (blockers or ["TRUST_EVIDENCE_MISSING"]),
        "status": status,
        "network_fetch_authorized": False,
        "install_authorized": False,
        "execution_authorized": False,
        "execution_proven": False,
        "publication_authorized": False,
        "payment_authorized": False,
        "telemetry_authorized": False,
        "recipient_tracking_authorized": False,
        "provider_call_authorized": False,
        "adoption_success_proven": False,
    }
    row.update(overrides)
    row["plan_digest"] = bridge._digest(row)
    return row


def share_event(projection):
    return next(event for event in projection.stage_events if event.stage == "SHARE_OR_REUSE")


def build_receipt(mode, evidence_ref=""):
    return bridge.build_browser_share_friction_receipt(
        decision(),
        observation(),
        launch_plan(),
        bridge.ShareActionObservationV1(mode, evidence_ref=evidence_ref),
        mission_head="aura-adopt-001:current",
        cohort={"device_class": "desktop-browser"},
        starting_state={"route": "browser", "account": "NONE", "key": "NONE"},
        friction_vector=unknown_vector(),
        weights=weights(),
        weighting_method="UNKNOWN_EMPIRICAL_WEIGHTS_REFERENCE_ONLY",
        reopen_trigger="browser/share/receipt ABI changes",
        invalidators=("PR364_HEAD_CHANGE", "PR367_HEAD_CHANGE"),
    )


class ShareFrictionAdapterTests(unittest.TestCase):
    def test_ready_share_capsule_is_unknown_not_completed(self):
        projection = bridge.project_share_into_browser_friction(
            browser_observation=observation(),
            share_launch_plan=launch_plan(),
            share_observation=bridge.ShareActionObservationV1(bridge.ShareActionMode.READY_ONLY),
        )
        event = share_event(projection)
        self.assertEqual(StageStatus.UNKNOWN, event.status)
        self.assertIn("no bounded user", event.reason)
        self.assertFalse(projection.adoption_success_proven)
        self.assertFalse(projection.publication_authorized)
        self.assertFalse(projection.recipient_tracking_authorized)

    def test_observed_user_share_completes_exact_canonical_stage(self):
        projection = bridge.project_share_into_browser_friction(
            browser_observation=observation(),
            share_launch_plan=launch_plan(),
            share_observation=bridge.ShareActionObservationV1(
                bridge.ShareActionMode.USER_SHARE_OBSERVED,
                evidence_ref="share:event:local-export-1",
            ),
        )
        event = share_event(projection)
        self.assertEqual(StageStatus.COMPLETED, event.status)
        self.assertIn("user share observed", event.reason)
        self.assertEqual(13, len(projection.stage_events))

    def test_observed_user_reuse_completes_without_adoption_success_claim(self):
        projection = bridge.project_share_into_browser_friction(
            browser_observation=observation(),
            share_launch_plan=launch_plan(),
            share_observation=bridge.ShareActionObservationV1(
                bridge.ShareActionMode.USER_REUSE_OBSERVED,
                evidence_ref="reuse:event:remix-open-1",
            ),
        )
        self.assertEqual(StageStatus.COMPLETED, share_event(projection).status)
        self.assertFalse(projection.adoption_success_proven)

    def test_failed_attempt_is_blocked_with_typed_failure(self):
        projection = bridge.project_share_into_browser_friction(
            browser_observation=observation(),
            share_launch_plan=launch_plan(),
            share_observation=bridge.ShareActionObservationV1(
                bridge.ShareActionMode.ATTEMPT_FAILED,
                evidence_ref="share:event:failure-1",
                failure_code="LOCAL_EXPORT_FAILED",
            ),
        )
        event = share_event(projection)
        self.assertEqual(StageStatus.BLOCKED, event.status)
        self.assertEqual("LOCAL_EXPORT_FAILED", event.failure_code)

    def test_nonready_launch_is_blocked_not_unknown_success(self):
        projection = bridge.project_share_into_browser_friction(
            browser_observation=observation(),
            share_launch_plan=launch_plan(status="EVIDENCE_REQUIRED"),
            share_observation=bridge.ShareActionObservationV1(bridge.ShareActionMode.UNKNOWN),
        )
        event = share_event(projection)
        self.assertEqual(StageStatus.BLOCKED, event.status)
        self.assertEqual("SHARE_LAUNCH_NOT_READY", event.failure_code)

    def test_nonready_launch_cannot_claim_observed_share(self):
        with self.assertRaises(bridge.ShareFrictionError) as ctx:
            bridge.project_share_into_browser_friction(
                browser_observation=observation(),
                share_launch_plan=launch_plan(status="EVIDENCE_REQUIRED"),
                share_observation=bridge.ShareActionObservationV1(
                    bridge.ShareActionMode.USER_SHARE_OBSERVED,
                    evidence_ref="share:event:impossible",
                ),
            )
        self.assertEqual("SHARE_ACTION_OBSERVED_FROM_NONREADY_PLAN", ctx.exception.code)

    def test_synthetic_acceptance_cannot_be_laundered_into_share_action(self):
        obs = observation(
            acceptance_mode=AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL,
            acceptance_evidence_ref="",
        )
        with self.assertRaises(bridge.ShareFrictionError) as ctx:
            bridge.project_share_into_browser_friction(
                browser_observation=obs,
                share_launch_plan=launch_plan(),
                share_observation=bridge.ShareActionObservationV1(
                    bridge.ShareActionMode.USER_REUSE_OBSERVED,
                    evidence_ref="reuse:event:should-not-pass",
                ),
            )
        self.assertEqual("SHARE_ACTION_REQUIRES_USER_EXPLICIT_ACCEPTANCE", ctx.exception.code)

    def test_forged_share_plan_digest_fails_closed(self):
        plan = launch_plan()
        plan["capsule_id"] = "share:tampered"
        with self.assertRaises(bridge.ShareFrictionError) as ctx:
            bridge.validate_share_launch_plan(plan)
        self.assertEqual("SHARE_LAUNCH_PLAN_DIGEST_MISMATCH", ctx.exception.code)

    def test_share_plan_authority_laundering_fails_closed(self):
        for field in (
            "network_fetch_authorized",
            "publication_authorized",
            "payment_authorized",
            "telemetry_authorized",
            "recipient_tracking_authorized",
            "provider_call_authorized",
            "adoption_success_proven",
        ):
            plan = launch_plan(**{field: True})
            # Recompute digest so the failure is authority, not integrity.
            logical = dict(plan)
            logical.pop("plan_digest")
            plan["plan_digest"] = bridge._digest(logical)
            with self.assertRaises(bridge.ShareFrictionError) as ctx:
                bridge.validate_share_launch_plan(plan)
            self.assertEqual("SHARE_LAUNCH_AUTHORITY_WIDENING", ctx.exception.code)

    def test_recipient_or_private_evidence_is_forbidden(self):
        with self.assertRaises(bridge.ShareFrictionError) as ctx:
            bridge.ShareActionObservationV1(
                bridge.ShareActionMode.USER_SHARE_OBSERVED,
                evidence_ref="share:event:recipient=user@example.test",
            )
        self.assertEqual("RECIPIENT_OR_PRIVATE_EVIDENCE_FORBIDDEN", ctx.exception.code)

    def test_final_receipt_identity_remains_canonical_zf00(self):
        receipt = build_receipt(
            bridge.ShareActionMode.USER_SHARE_OBSERVED,
            evidence_ref="share:event:canonical-1",
        )
        self.assertTrue(receipt.logical_id.startswith("afr-"))
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.execution_proven)
        event = next(e for e in receipt.stage_events if e.stage == "SHARE_OR_REUSE")
        self.assertEqual(StageStatus.COMPLETED, event.status)
        self.assertTrue(any(ref.startswith("share-launch:") for ref in receipt.build_refs))
        self.assertTrue(any(ref.startswith("share-capsule:") for ref in receipt.build_refs))

    def test_ready_only_receipt_preserves_unknown_share_stage(self):
        receipt = build_receipt(bridge.ShareActionMode.READY_ONLY)
        event = next(e for e in receipt.stage_events if e.stage == "SHARE_OR_REUSE")
        self.assertEqual(StageStatus.UNKNOWN, event.status)

    def test_plan_digest_is_replay_stable(self):
        a = launch_plan()
        b = launch_plan()
        self.assertEqual(a["plan_digest"], b["plan_digest"])
        self.assertEqual(a["plan_digest"], bridge.validate_share_launch_plan(a)["plan_digest"])


if __name__ == "__main__":
    unittest.main()
