import unittest

from tools.aura_adopt.accessible_onboarding import (
    AcceptanceMode,
    AccessNeedsV1,
    FirstValueEvidenceV1,
    OnboardingSurfaceCapabilitiesV1,
    PlanStatus,
    PreferenceSource,
    SaveEvidenceMode,
    compile_accessible_onboarding_plan,
)

CUR_N = "needs-current-1"
CUR_C = "caps-current-1"


def needs(**kwargs):
    values = dict(
        source_ref="user://explicit-access-needs/1",
        source_currentness_ref=CUR_N,
        preference_source=PreferenceSource.USER_SELECTED,
    )
    values.update(kwargs)
    return AccessNeedsV1(**values)


def caps(**kwargs):
    values = dict(
        source_ref="browser://capabilities/1",
        source_currentness_ref=CUR_C,
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
    values.update(kwargs)
    return OnboardingSurfaceCapabilitiesV1(**values)


def evidence(**kwargs):
    return FirstValueEvidenceV1(**kwargs)


def plan(n=None, c=None, e=None, expected_n=CUR_N, expected_c=CUR_C):
    return compile_accessible_onboarding_plan(
        n or needs(),
        c or caps(),
        e or evidence(),
        expected_needs_currentness_ref=expected_n,
        expected_capabilities_currentness_ref=expected_c,
    )


class AccessibleOnboardingTests(unittest.TestCase):
    def test_01_default_guided_path_is_ready(self):
        p = plan()
        self.assertEqual(PlanStatus.READY_BOUNDED, p.status)
        self.assertEqual(("OPEN", "GUIDED_PICK_INPUT", "APPLY_RECIPE", "PREVIEW", "USER_EXPLICIT_ACCEPT", "SAVE_LOCAL"), p.steps)
        self.assertFalse(p.user_explicit_acceptance_proven)

    def test_02_advanced_surfaces_hidden_by_default(self):
        p = plan()
        self.assertIn("API_KEYS", p.advanced_surfaces_hidden)
        self.assertIn("MODEL_DOWNLOADS", p.advanced_surfaces_hidden)
        self.assertIn("PROVIDER_SETTINGS", p.advanced_surfaces_hidden)
        self.assertIn("DEVELOPER_CLI", p.advanced_surfaces_hidden)

    def test_03_no_telemetry_or_effect_authority(self):
        p = plan()
        self.assertFalse(p.telemetry_authorized)
        self.assertFalse(p.telemetry_performed)
        self.assertFalse(p.install_authorized)
        self.assertFalse(p.credential_request_authorized)
        self.assertFalse(p.provider_effect_authorized)
        self.assertFalse(p.execution_proven)

    def test_04_stale_needs_rebases(self):
        self.assertEqual(PlanStatus.REBASE_REQUIRED, plan(expected_n="new").status)

    def test_05_stale_capabilities_rebases(self):
        self.assertEqual(PlanStatus.REBASE_REQUIRED, plan(expected_c="new").status)

    def test_06_keyboard_required_and_available(self):
        p = plan(n=needs(keyboard_required=True))
        self.assertEqual(PlanStatus.READY_BOUNDED, p.status)

    def test_07_keyboard_unavailable_requires_assisted_fallback(self):
        p = plan(n=needs(keyboard_required=True), c=caps(keyboard_operable=False))
        self.assertEqual(PlanStatus.ASSISTED_FALLBACK_REQUIRED, p.status)
        self.assertIn("KEYBOARD_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_08_keyboard_unknown_is_partial(self):
        p = plan(n=needs(keyboard_required=True), c=caps(keyboard_operable=None))
        self.assertEqual(PlanStatus.PARTIAL, p.status)
        self.assertIn("KEYBOARD_CAPABILITY_UNKNOWN", p.unknowns)

    def test_09_screen_reader_requirement_checked(self):
        p = plan(n=needs(screen_reader_required=True), c=caps(screen_reader_semantics=False))
        self.assertIn("SCREEN_READER_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_10_high_contrast_requirement_checked(self):
        p = plan(n=needs(high_contrast_required=True), c=caps(high_contrast_mode=False))
        self.assertIn("HIGH_CONTRAST_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_11_reduced_motion_requirement_checked(self):
        p = plan(n=needs(reduced_motion_required=True), c=caps(reduced_motion_mode=False))
        self.assertIn("REDUCED_MOTION_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_12_captions_requirement_checked(self):
        p = plan(n=needs(captions_required=True), c=caps(captions_available=False))
        self.assertIn("CAPTIONS_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_13_voice_request_checked(self):
        p = plan(n=needs(voice_input_requested=True), c=caps(voice_input_available=False))
        self.assertIn("VOICE_INPUT_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_14_touch_request_checked(self):
        p = plan(n=needs(touch_input_requested=True), c=caps(touch_operable=False))
        self.assertIn("TOUCH_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_15_local_file_picker_is_required_for_witness(self):
        p = plan(c=caps(local_file_picker_available=False))
        self.assertIn("LOCAL_FILE_PICKER_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_16_canvas_is_required_for_current_witness(self):
        p = plan(c=caps(canvas_render_available=False))
        self.assertIn("CANVAS_RENDER_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_17_local_download_is_required_for_current_witness(self):
        p = plan(c=caps(local_download_available=False))
        self.assertIn("LOCAL_DOWNLOAD_UNAVAILABLE", p.assisted_fallback_reasons)

    def test_18_synthetic_technical_acceptance_is_not_user_value(self):
        p = plan(e=evidence(acceptance_mode=AcceptanceMode.SYNTHETIC_TECHNICAL, acceptance_ref="ci://png-output"))
        self.assertFalse(p.user_explicit_acceptance_proven)

    def test_19_user_explicit_acceptance_requires_reference(self):
        with self.assertRaisesRegex(ValueError, "USER_ACCEPTANCE_REF_REQUIRED"):
            evidence(acceptance_mode=AcceptanceMode.USER_EXPLICIT)

    def test_20_user_explicit_acceptance_is_proven_only_by_typed_mode(self):
        p = plan(e=evidence(acceptance_mode=AcceptanceMode.USER_EXPLICIT, acceptance_ref="user://accept/1"))
        self.assertTrue(p.user_explicit_acceptance_proven)

    def test_21_simulated_save_is_not_save_proof(self):
        p = plan(e=evidence(save_evidence_mode=SaveEvidenceMode.SIMULATED))
        self.assertFalse(p.save_observed)
        self.assertFalse(p.reopen_observed)

    def test_22_download_initiated_is_not_save_observed(self):
        p = plan(e=evidence(save_evidence_mode=SaveEvidenceMode.DOWNLOAD_INITIATED))
        self.assertFalse(p.save_observed)

    def test_23_save_observed_requires_reference_and_not_reopen(self):
        with self.assertRaisesRegex(ValueError, "SAVE_EVIDENCE_REF_REQUIRED"):
            evidence(save_evidence_mode=SaveEvidenceMode.SAVE_OBSERVED)
        p = plan(e=evidence(save_evidence_mode=SaveEvidenceMode.SAVE_OBSERVED, save_evidence_ref="host://save/1"))
        self.assertTrue(p.save_observed)
        self.assertFalse(p.reopen_observed)

    def test_24_reopen_observed_is_strongest_save_state(self):
        p = plan(e=evidence(save_evidence_mode=SaveEvidenceMode.REOPEN_OBSERVED, save_evidence_ref="host://reopen/1"))
        self.assertTrue(p.save_observed)
        self.assertTrue(p.reopen_observed)

    def test_25_unguided_path_removes_guided_step(self):
        p = plan(n=needs(simplified_guidance_requested=False))
        self.assertIn("PICK_INPUT", p.steps)
        self.assertNotIn("GUIDED_PICK_INPUT", p.steps)

    def test_26_platform_exposed_preference_is_accepted_but_not_inferred(self):
        p = plan(n=needs(preference_source=PreferenceSource.PLATFORM_EXPOSED, reduced_motion_required=True))
        self.assertEqual(PlanStatus.READY_BOUNDED, p.status)


if __name__ == "__main__":
    unittest.main()
