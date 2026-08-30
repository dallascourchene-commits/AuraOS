import unittest

from tools.aura_adopt.android_adaptive_provisioner import (
    AdaptiveProvisioningPlanV1,
    CapabilityRequirementsV1,
    EntrySurface,
    HostKind,
    HostSubstrateWitnessV1,
    PlanStatus,
    ProvisioningPolicyV1,
    ProvisioningProfile,
    compile_adaptive_provisioning_plan,
)

GiB = 1024**3
MiB = 1024**2
CUR = "host-current-1"
POL_CUR = "policy-current-1"


def witness(**kwargs):
    values = dict(
        source_ref="host://witness/1",
        source_generation="g1",
        source_currentness_ref=CUR,
        host_kind=HostKind.ANDROID,
        android_api_level=34,
        free_storage_bytes=8 * GiB,
        ram_bytes=8 * GiB,
        saf_available=True,
        webview_available=True,
        network_available=True,
        native_tts_available=True,
        background_execution_available=True,
        local_model_runtime_available=True,
    )
    values.update(kwargs)
    return HostSubstrateWitnessV1(**values)


def requirements(**kwargs):
    values = dict(capability_ids=("creator.short.card",), working_storage_bytes=50 * MiB, working_ram_bytes=128 * MiB)
    values.update(kwargs)
    return CapabilityRequirementsV1(**values)


def policy(**kwargs):
    values = dict(
        policy_ref="policy://android/1",
        policy_currentness_ref=POL_CUR,
        minimum_android_api_level=26,
        native_shell_bytes=25 * MiB,
        storage_reserve_bytes=100 * MiB,
        micro_model_bytes=700 * MiB,
        micro_model_min_ram_bytes=2 * GiB,
        full_model_bytes=4 * GiB,
        full_model_min_ram_bytes=8 * GiB,
    )
    values.update(kwargs)
    return ProvisioningPolicyV1(**values)


def compile_plan(w=None, req=None, pol=None, surface=EntrySurface.NATIVE_ANDROID_APK, expected_host=CUR, expected_policy=POL_CUR):
    return compile_adaptive_provisioning_plan(
        w or witness(),
        req or requirements(),
        pol or policy(),
        selected_entry_surface=surface,
        expected_witness_currentness_ref=expected_host,
        expected_policy_currentness_ref=expected_policy,
    )


class AndroidAdaptiveProvisioningTests(unittest.TestCase):
    def assertNoEffects(self, plan: AdaptiveProvisioningPlanV1):
        self.assertFalse(plan.install_authorized)
        self.assertFalse(plan.install_performed)
        self.assertFalse(plan.download_authorized)
        self.assertFalse(plan.download_performed)
        self.assertFalse(plan.permission_grant_authorized)
        self.assertFalse(plan.permission_granted)
        self.assertFalse(plan.credential_requested)
        self.assertFalse(plan.provider_effect_authorized)
        self.assertFalse(plan.provider_effect_performed)
        self.assertFalse(plan.execution_proven)

    def test_01_minimal_native_plan_is_ready_without_model(self):
        plan = compile_plan()
        self.assertEqual(PlanStatus.READY_BOUNDED, plan.status)
        self.assertEqual(ProvisioningProfile.DETERMINISTIC_NATIVE, plan.profile)
        self.assertIn("MODEL_DOWNLOAD", plan.avoided_actions)
        self.assertIn("PROVIDER_KEY", plan.avoided_actions)
        self.assertNoEffects(plan)

    def test_02_non_android_is_blocked_for_native_surface(self):
        plan = compile_plan(w=witness(host_kind=HostKind.NON_ANDROID))
        self.assertEqual(PlanStatus.BLOCKED, plan.status)
        self.assertIn("ANDROID_HOST_REQUIRED", plan.blockers)

    def test_03_unknown_host_kind_is_partial_not_zero(self):
        plan = compile_plan(w=witness(host_kind=HostKind.UNKNOWN))
        self.assertEqual(PlanStatus.PARTIAL, plan.status)
        self.assertIn("HOST_KIND_UNKNOWN", plan.unknowns)

    def test_04_stale_witness_rebases(self):
        plan = compile_plan(expected_host="host-current-2")
        self.assertEqual(PlanStatus.REBASE_REQUIRED, plan.status)
        self.assertIn("CURRENTNESS_MISMATCH", plan.blockers)

    def test_05_stale_policy_rebases(self):
        plan = compile_plan(expected_policy="policy-current-2")
        self.assertEqual(PlanStatus.REBASE_REQUIRED, plan.status)

    def test_06_other_surface_is_not_applicable_and_does_not_install(self):
        plan = compile_plan(surface=EntrySurface.ZERO_INSTALL_WEB_PWA)
        self.assertEqual(PlanStatus.NOT_APPLICABLE, plan.status)
        self.assertEqual(ProvisioningProfile.NOT_APPLICABLE, plan.profile)
        self.assertNoEffects(plan)

    def test_07_unknown_api_level_is_partial(self):
        plan = compile_plan(w=witness(android_api_level=None))
        self.assertEqual(PlanStatus.PARTIAL, plan.status)
        self.assertIn("ANDROID_API_LEVEL_UNKNOWN", plan.unknowns)

    def test_08_old_api_level_blocks(self):
        plan = compile_plan(w=witness(android_api_level=23))
        self.assertIn("ANDROID_API_LEVEL_UNSUPPORTED", plan.blockers)

    def test_09_saf_unknown_is_partial(self):
        plan = compile_plan(w=witness(saf_available=None))
        self.assertIn("SAF_AVAILABILITY_UNKNOWN", plan.unknowns)

    def test_10_saf_false_blocks(self):
        plan = compile_plan(w=witness(saf_available=False))
        self.assertIn("SAF_REQUIRED", plan.blockers)

    def test_11_unknown_storage_is_partial_not_assumed_free(self):
        plan = compile_plan(w=witness(free_storage_bytes=None))
        self.assertEqual(PlanStatus.PARTIAL, plan.status)
        self.assertIn("FREE_STORAGE_UNKNOWN", plan.unknowns)

    def test_12_insufficient_shell_storage_blocks(self):
        plan = compile_plan(w=witness(free_storage_bytes=10 * MiB))
        self.assertIn("INSUFFICIENT_STORAGE_FOR_NATIVE_SHELL", plan.blockers)

    def test_13_unknown_ram_for_working_set_is_partial(self):
        plan = compile_plan(w=witness(ram_bytes=None))
        self.assertIn("RAM_UNKNOWN", plan.unknowns)

    def test_14_insufficient_working_ram_blocks(self):
        plan = compile_plan(w=witness(ram_bytes=64 * MiB))
        self.assertIn("INSUFFICIENT_RAM_FOR_CAPABILITY", plan.blockers)

    def test_15_background_not_requested_is_avoided(self):
        plan = compile_plan(req=requirements(requires_background=False))
        self.assertIn("BACKGROUND_PERMISSION", plan.avoided_actions)

    def test_16_background_unknown_is_partial(self):
        plan = compile_plan(w=witness(background_execution_available=None), req=requirements(requires_background=True))
        self.assertIn("BACKGROUND_EXECUTION_UNKNOWN", plan.unknowns)

    def test_17_background_unavailable_blocks(self):
        plan = compile_plan(w=witness(background_execution_available=False), req=requirements(requires_background=True))
        self.assertIn("BACKGROUND_EXECUTION_UNAVAILABLE", plan.blockers)

    def test_18_native_tts_requirement_fails_closed(self):
        plan = compile_plan(w=witness(native_tts_available=False), req=requirements(requires_native_tts=True))
        self.assertIn("NATIVE_TTS_UNAVAILABLE", plan.blockers)

    def test_19_local_inference_uses_smallest_adequate_model(self):
        plan = compile_plan(req=requirements(requires_local_inference=True))
        self.assertEqual(ProvisioningProfile.MICRO_LOCAL_MODEL_ELIGIBLE, plan.profile)
        self.assertEqual(PlanStatus.READY_BOUNDED, plan.status)
        self.assertIn("MODEL_DOWNLOAD", plan.required_actions)
        self.assertEqual(25 * MiB + 700 * MiB, plan.estimated_download_bytes)
        self.assertNoEffects(plan)

    def test_20_missing_micro_model_policy_remains_partial(self):
        plan = compile_plan(req=requirements(requires_local_inference=True), pol=policy(micro_model_bytes=None))
        self.assertEqual(PlanStatus.PARTIAL, plan.status)
        self.assertIn("MICRO_MODEL_POLICY_UNKNOWN", plan.unknowns)

    def test_21_remote_residual_requires_separate_admission(self):
        plan = compile_plan(
            w=witness(local_model_runtime_available=False, network_available=True),
            req=requirements(requires_local_inference=True, remote_inference_acceptable=True),
        )
        self.assertEqual(ProvisioningProfile.HYBRID_REMOTE_ADMISSION_REQUIRED, plan.profile)
        self.assertIn("REMOTE_ROUTE_ADMISSION", plan.required_actions)
        self.assertFalse(plan.provider_effect_authorized)

    def test_22_offline_requirement_blocks_remote_substitution(self):
        plan = compile_plan(
            w=witness(local_model_runtime_available=False),
            req=requirements(requires_local_inference=True, remote_inference_acceptable=True, requires_offline=True),
        )
        self.assertIn("OFFLINE_LOCAL_INFERENCE_UNAVAILABLE", plan.blockers)

    def test_23_remote_network_unknown_is_partial(self):
        plan = compile_plan(
            w=witness(local_model_runtime_available=False, network_available=None),
            req=requirements(requires_local_inference=True, remote_inference_acceptable=True),
        )
        self.assertIn("NETWORK_AVAILABILITY_UNKNOWN", plan.unknowns)

    def test_24_remote_network_false_blocks(self):
        plan = compile_plan(
            w=witness(local_model_runtime_available=False, network_available=False),
            req=requirements(requires_local_inference=True, remote_inference_acceptable=True),
        )
        self.assertIn("NETWORK_UNAVAILABLE_FOR_REMOTE_RESIDUAL", plan.blockers)

    def test_25_local_runtime_required_if_remote_not_acceptable(self):
        plan = compile_plan(
            w=witness(local_model_runtime_available=False),
            req=requirements(requires_local_inference=True, remote_inference_acceptable=False),
        )
        self.assertIn("LOCAL_MODEL_RUNTIME_REQUIRED", plan.blockers)

    def test_26_full_model_is_not_chosen_when_micro_is_adequate(self):
        plan = compile_plan(req=requirements(requires_local_inference=True))
        self.assertNotEqual(ProvisioningProfile.FULL_LOCAL_MODEL_ELIGIBLE, plan.profile)

    def test_27_strict_host_integer_validation(self):
        with self.assertRaisesRegex(ValueError, "INVALID_FREE_STORAGE_BYTES"):
            witness(free_storage_bytes=-1)

    def test_28_capability_identity_dedup(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CAPABILITY_ID"):
            CapabilityRequirementsV1(capability_ids=("a", "a"))


if __name__ == "__main__":
    unittest.main()
