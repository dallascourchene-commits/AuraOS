from __future__ import annotations

import copy
import unittest

import accessible_onboarding as onboarding
import accessible_android_provisioning_bridge as bridge


def needs(**overrides):
    values = dict(
        source_ref="user:access-needs",
        source_currentness_ref="needs:1",
        preference_source=onboarding.PreferenceSource.USER_SELECTED,
        keyboard_required=False,
        screen_reader_required=False,
        high_contrast_required=False,
        reduced_motion_required=False,
        captions_required=False,
        voice_input_requested=False,
        touch_input_requested=True,
        simplified_guidance_requested=True,
    )
    values.update(overrides)
    return onboarding.AccessNeedsV1(**values)


def capabilities(**overrides):
    values = dict(
        source_ref="android:onboarding-surface",
        source_currentness_ref="surface:1",
        keyboard_operable=True,
        screen_reader_semantics=True,
        high_contrast_mode=True,
        reduced_motion_mode=True,
        captions_available=True,
        voice_input_available=True,
        touch_operable=True,
        local_file_picker_available=True,
        canvas_render_available=True,
        local_download_available=True,
    )
    values.update(overrides)
    return onboarding.OnboardingSurfaceCapabilitiesV1(**values)


def onboarding_plan(*, n=None, c=None, evidence=None):
    return onboarding.compile_accessible_onboarding_plan(
        n or needs(),
        c or capabilities(),
        evidence or onboarding.FirstValueEvidenceV1(),
        expected_needs_currentness_ref="needs:1",
        expected_capabilities_currentness_ref="surface:1",
    )


def provisioning_plan(**overrides):
    row = {
        "selected_entry_surface": "NATIVE_ANDROID_APK",
        "status": "READY_BOUNDED",
        "profile": "DETERMINISTIC_NATIVE",
        "blockers": [],
        "unknowns": [],
        "required_actions": ["APK_INSTALL"],
        "avoided_actions": ["DEVELOPER_CLI", "MODEL_DOWNLOAD", "PROVIDER_KEY"],
        "estimated_download_bytes": 12_000_000,
        "estimated_peak_storage_bytes": 64_000_000,
        "install_authorized": False,
        "install_performed": False,
        "download_authorized": False,
        "download_performed": False,
        "permission_grant_authorized": False,
        "permission_granted": False,
        "credential_requested": False,
        "provider_effect_authorized": False,
        "provider_effect_performed": False,
        "execution_proven": False,
    }
    row.update(overrides)
    return row


class AccessibleAndroidProvisioningBridgeTests(unittest.TestCase):
    def compile(self, *, op=None, pp=None):
        return bridge.compile_accessible_android_provisioning_decision(
            onboarding_plan=op or onboarding_plan(),
            provisioning_plan=pp or provisioning_plan(),
        )

    def test_ready_native_plan_preserves_first_value_and_zero_authority(self):
        result = self.compile()
        self.assertEqual("READY_FOR_USER_REVIEW", result.status)
        self.assertEqual(("OPEN", "GUIDED_PICK_INPUT", "APPLY_RECIPE", "PREVIEW", "USER_EXPLICIT_ACCEPT", "SAVE_LOCAL"), result.first_value_steps)
        self.assertEqual(("APK_INSTALL",), result.ordinary_future_actions)
        self.assertEqual((), result.deferred_actions)
        self.assertFalse(result.install_authorized)
        self.assertFalse(result.download_authorized)
        self.assertFalse(result.permission_grant_authorized)
        self.assertFalse(result.provider_effect_authorized)
        self.assertFalse(result.execution_proven)

    def test_local_model_download_is_deferred_from_first_value_path(self):
        pp = provisioning_plan(
            profile="MICRO_LOCAL_MODEL_ELIGIBLE",
            required_actions=["APK_INSTALL", "MODEL_DOWNLOAD"],
            estimated_download_bytes=850_000_000,
            estimated_peak_storage_bytes=1_100_000_000,
        )
        result = self.compile(pp=pp)
        self.assertEqual("READY_FOR_USER_REVIEW", result.status)
        self.assertEqual(("MODEL_DOWNLOAD",), result.deferred_actions)
        self.assertEqual(("APK_INSTALL",), result.ordinary_future_actions)
        self.assertFalse(result.download_authorized)

    def test_remote_route_is_deferred_and_never_provider_authority(self):
        pp = provisioning_plan(
            profile="HYBRID_REMOTE_ADMISSION_REQUIRED",
            required_actions=["APK_INSTALL", "REMOTE_ROUTE_ADMISSION"],
        )
        result = self.compile(pp=pp)
        self.assertEqual(("REMOTE_ROUTE_ADMISSION",), result.deferred_actions)
        self.assertFalse(result.provider_effect_authorized)

    def test_background_permission_review_is_deferred(self):
        pp = provisioning_plan(required_actions=["APK_INSTALL", "BACKGROUND_PERMISSION_REVIEW"])
        result = self.compile(pp=pp)
        self.assertEqual(("BACKGROUND_PERMISSION_REVIEW",), result.deferred_actions)
        self.assertFalse(result.permission_grant_authorized)

    def test_accessibility_fallback_outranks_host_readiness(self):
        op = onboarding_plan(
            n=needs(screen_reader_required=True),
            c=capabilities(screen_reader_semantics=False),
        )
        self.assertEqual(onboarding.PlanStatus.ASSISTED_FALLBACK_REQUIRED, op.status)
        result = self.compile(op=op)
        self.assertEqual("ASSISTED_FALLBACK_REQUIRED", result.status)
        self.assertIn("SCREEN_READER_UNAVAILABLE", result.assisted_fallback_reasons)

    def test_unknown_accessibility_or_host_evidence_stays_partial(self):
        op = onboarding_plan(c=capabilities(voice_input_available=None), n=needs(voice_input_requested=True))
        result = self.compile(op=op)
        self.assertEqual("PARTIAL", result.status)
        self.assertIn("VOICE_INPUT_CAPABILITY_UNKNOWN", result.unknowns)

        pp = provisioning_plan(status="PARTIAL", unknowns=["RAM_UNKNOWN_FOR_MICRO_MODEL"])
        result = self.compile(pp=pp)
        self.assertEqual("PARTIAL", result.status)
        self.assertIn("RAM_UNKNOWN_FOR_MICRO_MODEL", result.unknowns)

    def test_resource_block_is_not_laundered_by_accessible_ready_state(self):
        pp = provisioning_plan(
            status="BLOCKED",
            profile="BLOCKED",
            blockers=["INSUFFICIENT_STORAGE_FOR_NATIVE_SHELL"],
        )
        result = self.compile(pp=pp)
        self.assertEqual("BLOCKED_RESOURCE", result.status)
        self.assertIn("INSUFFICIENT_STORAGE_FOR_NATIVE_SHELL", result.blockers)

    def test_rebase_required_outranks_everything(self):
        stale_needs = needs(source_currentness_ref="needs:old")
        op = onboarding.compile_accessible_onboarding_plan(
            stale_needs,
            capabilities(),
            onboarding.FirstValueEvidenceV1(),
            expected_needs_currentness_ref="needs:1",
            expected_capabilities_currentness_ref="surface:1",
        )
        result = self.compile(op=op)
        self.assertEqual("REBASE_REQUIRED", result.status)

        pp = provisioning_plan(status="REBASE_REQUIRED", profile="BLOCKED", blockers=["CURRENTNESS_MISMATCH"])
        result = self.compile(pp=pp)
        self.assertEqual("REBASE_REQUIRED", result.status)

    def test_model_download_requires_explicit_nonzero_size(self):
        pp = provisioning_plan(
            profile="MICRO_LOCAL_MODEL_ELIGIBLE",
            required_actions=["APK_INSTALL", "MODEL_DOWNLOAD"],
            estimated_download_bytes=0,
        )
        with self.assertRaises(bridge.AccessibleProvisioningError) as ctx:
            self.compile(pp=pp)
        self.assertEqual("MODEL_DOWNLOAD_BYTES_REQUIRED", ctx.exception.code)

    def test_progressive_disclosure_contract_cannot_be_silently_weakened(self):
        op = onboarding_plan()
        raw = dict(op.__dict__)
        raw["advanced_surfaces_hidden"] = tuple(
            item for item in op.advanced_surfaces_hidden if item != "MODEL_DOWNLOADS"
        )
        # Reconstructing a sibling-owned plan with weakened hidden surfaces is not
        # allowed by this bridge; use an object-shaped fake to exercise the view.
        class FakePlan:
            pass
        fake = FakePlan()
        for key, value in raw.items():
            setattr(fake, key, value)
        with self.assertRaises(bridge.AccessibleProvisioningError):
            bridge.compile_accessible_android_provisioning_decision(
                onboarding_plan=fake,
                provisioning_plan=provisioning_plan(required_actions=["APK_INSTALL", "MODEL_DOWNLOAD"], estimated_download_bytes=10),
            )

    def test_authority_laundering_fails_closed(self):
        for field in (
            "install_authorized",
            "download_authorized",
            "permission_grant_authorized",
            "provider_effect_authorized",
            "execution_proven",
        ):
            pp = provisioning_plan(**{field: True})
            with self.assertRaises(bridge.AccessibleProvisioningError) as ctx:
                self.compile(pp=pp)
            self.assertEqual("PROVISIONING_AUTHORITY_WIDENING", ctx.exception.code)

    def test_user_acceptance_is_evidence_not_effect_authority(self):
        evidence = onboarding.FirstValueEvidenceV1(
            acceptance_mode=onboarding.AcceptanceMode.USER_EXPLICIT,
            acceptance_ref="user-evidence:accepted",
            save_evidence_mode=onboarding.SaveEvidenceMode.REOPEN_OBSERVED,
            save_evidence_ref="user-evidence:reopened",
        )
        result = self.compile(op=onboarding_plan(evidence=evidence))
        self.assertTrue(result.user_explicit_acceptance_proven)
        self.assertTrue(result.save_observed)
        self.assertTrue(result.reopen_observed)
        self.assertFalse(result.install_authorized)
        self.assertFalse(result.download_authorized)
        self.assertFalse(result.provider_effect_authorized)

    def test_non_android_surface_cannot_cross_native_bridge(self):
        pp = provisioning_plan(selected_entry_surface="ZERO_INSTALL_WEB_PWA", status="NOT_APPLICABLE", profile="NOT_APPLICABLE")
        with self.assertRaises(bridge.AccessibleProvisioningError) as ctx:
            self.compile(pp=pp)
        self.assertEqual("ANDROID_NATIVE_SURFACE_REQUIRED", ctx.exception.code)

    def test_decision_identity_is_replay_stable(self):
        a = self.compile()
        b = self.compile()
        self.assertEqual(a.decision_digest, b.decision_digest)


if __name__ == "__main__":
    unittest.main()
