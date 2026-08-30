import dataclasses
import unittest

import aura_adoption_bootstrap as a


def source_binding(gen="main@d0d1965", host_digest="host-digest"):
    return a.SourceBindingV1(
        source_generation=gen,
        currentness_ref="arena-currentness-ref",
        host_evidence_ref="host-discovery-ref",
        host_evidence_digest=host_digest,
    )


def projection(**overrides):
    values = dict(
        source=source_binding(),
        user_mode=a.UserMode.ORDINARY,
        platform_class=a.PlatformClass.ANDROID,
        browser_available=True,
        native_install_available=True,
        cli_available=False,
        offline_required=False,
        background_required=False,
        local_compute_class=a.LocalComputeClass.NONE,
        storage_class=a.StorageClass.LOW,
        network_state=a.NetworkState.ONLINE,
        free_remote_route_available=True,
        provider_credential_present=False,
        desired_first_capability="CREATOR_STUDIO",
    )
    values.update(overrides)
    return a.BootstrapProjectionV1(**values)


class AuraAdoptionBootstrapTests(unittest.TestCase):
    def test_low_storage_ordinary_phone_prefers_zero_install_free_first(self):
        receipt = a.compile_entry_route(projection())
        self.assertEqual(a.EntrySurface.ZERO_INSTALL_WEB_PWA, receipt.surface)
        self.assertEqual(a.ComputeProfile.REMOTE_FREE_FIRST, receipt.compute_profile)
        self.assertIn("OPEN_AURA_WEB_ENTRY", receipt.required_actions)
        self.assertIn("INSTALL_ANDROID_APK", receipt.avoided_actions)
        self.assertIn("DOWNLOAD_LOCAL_MODEL", receipt.avoided_actions)
        self.assertIn("ENTER_PROVIDER_KEY", receipt.avoided_actions)
        self.assertEqual(0, receipt.friction.install_actions_required)
        self.assertEqual(0, receipt.friction.credential_actions_required)
        self.assertEqual(0, receipt.friction.model_download_actions_required)

    def test_capable_android_offline_background_prefers_apk_and_local(self):
        p = projection(
            offline_required=True,
            background_required=True,
            local_compute_class=a.LocalComputeClass.CAPABLE,
            storage_class=a.StorageClass.NORMAL,
            network_state=a.NetworkState.OFFLINE,
            free_remote_route_available=False,
        )
        receipt = a.compile_entry_route(p)
        self.assertEqual(a.EntrySurface.NATIVE_ANDROID_APK, receipt.surface)
        self.assertEqual(a.ComputeProfile.FULL_LOCAL, receipt.compute_profile)
        self.assertIn("INSTALL_AURA_ANDROID_APP", receipt.required_actions)
        self.assertIn(
            "REQUEST_BACKGROUND_CAPABILITY_IF_PLATFORM_REQUIRES",
            receipt.required_actions,
        )
        self.assertNotIn("ENTER_PROVIDER_KEY", receipt.required_actions)
        self.assertEqual(1, receipt.friction.install_actions_required)
        self.assertEqual(1, receipt.friction.permission_actions_required)

    def test_developer_desktop_prefers_cli_without_creator_lock_in(self):
        p = projection(
            user_mode=a.UserMode.DEVELOPER,
            platform_class=a.PlatformClass.DESKTOP,
            cli_available=True,
            browser_available=True,
            native_install_available=False,
            local_compute_class=a.LocalComputeClass.CAPABLE,
            storage_class=a.StorageClass.NORMAL,
            desired_first_capability="BUGHOUND",
        )
        receipt = a.compile_entry_route(p)
        self.assertEqual(a.EntrySurface.DEV_CLI_GITHUB, receipt.surface)
        self.assertEqual(a.ComputeProfile.FULL_LOCAL, receipt.compute_profile)
        self.assertEqual("BUGHOUND", receipt.first_use_capability)
        self.assertIn("OPEN_GITHUB_OR_AURA_CLI", receipt.required_actions)

    def test_unsupported_unknown_surface_fails_closed(self):
        p = projection(
            platform_class=a.PlatformClass.UNKNOWN,
            browser_available=False,
            native_install_available=False,
            cli_available=False,
            local_compute_class=a.LocalComputeClass.UNKNOWN,
            storage_class=a.StorageClass.UNKNOWN,
            network_state=a.NetworkState.UNKNOWN,
            free_remote_route_available=False,
        )
        receipt = a.compile_entry_route(p)
        self.assertEqual(a.EntrySurface.NO_SUPPORTED_SURFACE, receipt.surface)
        self.assertEqual(a.ComputeProfile.OFFLINE_DEGRADED, receipt.compute_profile)
        self.assertIn("NO_SUPPORTED_ENTRY_SURFACE_PROVEN", receipt.blockers)
        self.assertIn("LOCAL_COMPUTE_CAPABILITY_UNKNOWN", receipt.blockers)
        self.assertIn("LOCAL_STORAGE_CAPACITY_UNKNOWN", receipt.blockers)
        self.assertIn("NETWORK_STATE_UNKNOWN", receipt.blockers)
        self.assertGreaterEqual(receipt.friction.unsupported_unknown_count, 3)

    def test_constrained_local_does_not_ask_for_key_when_none_is_present(self):
        p = projection(
            local_compute_class=a.LocalComputeClass.CONSTRAINED,
            storage_class=a.StorageClass.NORMAL,
            free_remote_route_available=False,
            provider_credential_present=False,
        )
        receipt = a.compile_entry_route(p)
        self.assertEqual(a.ComputeProfile.CONSTRAINED_LOCAL, receipt.compute_profile)
        self.assertNotIn("ENTER_PROVIDER_KEY", receipt.required_actions)
        self.assertIn("ENTER_PROVIDER_KEY", receipt.avoided_actions)

    def test_existing_credential_can_enable_hybrid_without_storing_it(self):
        p = projection(
            local_compute_class=a.LocalComputeClass.CONSTRAINED,
            storage_class=a.StorageClass.NORMAL,
            free_remote_route_available=False,
            provider_credential_present=True,
        )
        receipt = a.compile_entry_route(p)
        self.assertEqual(a.ComputeProfile.HYBRID_LOCAL_REMOTE, receipt.compute_profile)
        self.assertIn(
            "USE_EXISTING_PROVIDER_CREDENTIAL_WITHOUT_RESTORING_IT",
            receipt.required_actions,
        )
        self.assertFalse(receipt.credential_stored)

    def test_all_effect_flags_remain_false(self):
        receipt = a.compile_entry_route(projection())
        self.assertFalse(receipt.installation_performed)
        self.assertFalse(receipt.permission_granted)
        self.assertFalse(receipt.provider_call_made)
        self.assertFalse(receipt.credential_stored)
        self.assertFalse(receipt.public_deployment_performed)
        self.assertFalse(receipt.binary_distributed)
        self.assertIn("NO_INSTALL_PERMISSION_PROVIDER_DEPLOYMENT_EFFECT", receipt.claim_ceiling)

    def test_projection_and_receipt_identity_bind_upstream_source(self):
        p1 = projection(source=source_binding(gen="g1", host_digest="h1"))
        p2 = projection(source=source_binding(gen="g2", host_digest="h2"))
        r1 = a.compile_entry_route(p1)
        r2 = a.compile_entry_route(p2)
        self.assertNotEqual(p1.digest, p2.digest)
        self.assertNotEqual(r1.digest, r2.digest)
        self.assertNotEqual(r1.source_binding_digest, r2.source_binding_digest)

    def test_receipt_is_deterministic_for_same_projection(self):
        p = projection(desired_first_capability="AURA_DRIVE")
        r1 = a.compile_entry_route(p)
        r2 = a.compile_entry_route(p)
        self.assertEqual(r1, r2)
        self.assertEqual(r1.digest, r2.digest)

    def test_capability_binding_must_be_complete_pair(self):
        with self.assertRaises(a.BootstrapError) as ctx:
            a.SourceBindingV1(
                source_generation="g",
                currentness_ref="c",
                host_evidence_ref="h",
                host_evidence_digest="hd",
                capability_evidence_ref="cap-ref",
                capability_evidence_digest=None,
            )
        self.assertEqual("CAPABILITY_EVIDENCE_BINDING_INCOMPLETE", ctx.exception.code)

    def test_bool_inputs_are_type_strict(self):
        with self.assertRaises(a.BootstrapError) as ctx:
            projection(browser_available=1)
        self.assertEqual("BOOL_REQUIRED", ctx.exception.code)

    def test_frozen_projection_rejects_direct_mutation(self):
        p = projection()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            p.browser_available = False

    def test_web_fallback_exposes_requirement_mismatch_instead_of_hiding_it(self):
        p = projection(
            platform_class=a.PlatformClass.WEB_ONLY,
            native_install_available=False,
            offline_required=True,
            browser_available=True,
            local_compute_class=a.LocalComputeClass.NONE,
            network_state=a.NetworkState.OFFLINE,
            free_remote_route_available=False,
        )
        receipt = a.compile_entry_route(p)
        self.assertEqual(a.EntrySurface.ZERO_INSTALL_WEB_PWA, receipt.surface)
        self.assertIn(
            "WEB_SURFACE_MAY_NOT_SATISFY_OFFLINE_OR_BACKGROUND_REQUIREMENT",
            receipt.blockers,
        )
        self.assertEqual(a.ComputeProfile.OFFLINE_DEGRADED, receipt.compute_profile)


if __name__ == "__main__":
    unittest.main()
