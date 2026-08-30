import unittest

from tools.aura_adopt.aura_adoption_bootstrap import (
    CompileError,
    ComputeProfile,
    EntryPreference,
    EntrySurface,
    EvidenceBinding,
    FirstTask,
    HostWitness,
    compile_entry_route,
    friction_receipt,
)


EVIDENCE = EvidenceBinding("drive:host-witness", "a" * 64, "gen-1")


class AdoptionBootstrapTests(unittest.TestCase):
    def deterministic_creator_task(self):
        return FirstTask(
            task_id="creator.short.deterministic.v1",
            domain="creator-studio",
            browser_supported=True,
            offline_supported=True,
            minimum_storage_mb=32,
        )

    def model_creator_task(self):
        return FirstTask(
            task_id="creator.script.reason.v1",
            domain="creator-studio",
            browser_supported=True,
            model_inference_required=True,
            minimum_storage_mb=32,
        )

    def test_low_storage_phone_separates_web_surface_from_remote_free_compute(self):
        host = HostWitness(
            host_class="android-low-storage",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=512,
            ram_mb=2048,
            android=True,
            local_compute_class="CONSTRAINED",
            free_remote_route_available=True,
        )
        d = compile_entry_route(host, self.model_creator_task(), EVIDENCE)
        self.assertEqual(EntrySurface.ZERO_INSTALL_WEB_PWA, d.entry_surface)
        self.assertEqual(ComputeProfile.REMOTE_FREE_FIRST, d.compute_profile)
        self.assertEqual((), d.required_actions)
        self.assertIn("MANDATORY_INSTALL", d.avoided_actions)
        self.assertIn("MANDATORY_LOCAL_MODEL_DOWNLOAD", d.avoided_actions)

    def test_native_required_android_is_surface_independent_of_compute(self):
        host = HostWitness(
            host_class="android-capable",
            browser_available=True,
            browser_wasm=True,
            network_online=False,
            free_storage_mb=4096,
            ram_mb=4096,
            android=True,
            native_shell_installed=False,
            native_install_available=True,
            local_runtime_available=True,
            local_model_available=True,
            local_compute_class="CONSTRAINED",
        )
        task = FirstTask(
            task_id="creator.camera.offline.v1",
            domain="creator-studio",
            browser_supported=False,
            native_required=True,
            model_inference_required=True,
            required_permissions=frozenset({"CAMERA"}),
        )
        d = compile_entry_route(host, task, EVIDENCE)
        self.assertEqual(EntrySurface.NATIVE_ANDROID_APK, d.entry_surface)
        self.assertEqual(ComputeProfile.CONSTRAINED_LOCAL, d.compute_profile)
        self.assertEqual(
            ("INSTALL_NATIVE_ANDROID_SHELL", "GRANT_PERMISSION:CAMERA"),
            d.required_actions,
        )

    def test_developer_surface_can_pair_with_full_local_compute(self):
        host = HostWitness(
            host_class="desktop-dev",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=100000,
            ram_mb=32768,
            dev_cli_available=True,
            local_runtime_available=True,
            local_model_available=True,
            local_compute_class="FULL",
        )
        d = compile_entry_route(
            host,
            self.model_creator_task(),
            EVIDENCE,
            EntryPreference(developer_mode=True),
        )
        self.assertEqual(EntrySurface.DEV_CLI_GITHUB, d.entry_surface)
        self.assertEqual(ComputeProfile.FULL_LOCAL, d.compute_profile)

    def test_unknown_surface_fails_closed(self):
        host = HostWitness(
            host_class="unknown-device",
            browser_available=None,
            browser_wasm=None,
            network_online=None,
            free_storage_mb=None,
            ram_mb=None,
            android=None,
            dev_cli_available=None,
            local_compute_class="UNKNOWN",
        )
        d = compile_entry_route(host, self.deterministic_creator_task(), EVIDENCE)
        self.assertEqual(EntrySurface.NO_SUPPORTED_SURFACE, d.entry_surface)
        self.assertIn("NO_SUPPORTED_OR_PROVEN_ENTRY_SURFACE", d.blockers)

    def test_creator_domain_is_not_required(self):
        host = HostWitness(
            host_class="desktop-browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=5000,
            ram_mb=8192,
            local_compute_class="CONSTRAINED",
        )
        task = FirstTask(task_id="notes.local.v1", domain="knowledge", browser_supported=True)
        d = compile_entry_route(host, task, EVIDENCE)
        self.assertEqual("knowledge", d.domain)
        self.assertEqual(EntrySurface.ZERO_INSTALL_WEB_PWA, d.entry_surface)

    def test_permission_is_deferred_for_browser_path(self):
        host = HostWitness(
            host_class="desktop-browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=10000,
            ram_mb=8192,
            local_compute_class="CONSTRAINED",
        )
        task = FirstTask(
            task_id="creator.caption.v1",
            domain="creator-studio",
            browser_supported=True,
            required_permissions=frozenset({"CAMERA"}),
        )
        d = compile_entry_route(host, task, EVIDENCE)
        self.assertEqual(EntrySurface.ZERO_INSTALL_WEB_PWA, d.entry_surface)
        self.assertEqual((), d.required_actions)

    def test_no_free_or_credentialed_remote_route_does_not_pretend_free(self):
        host = HostWitness(
            host_class="thin-browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=512,
            ram_mb=1024,
            local_runtime_available=False,
            local_model_available=False,
            local_compute_class="NONE",
            free_remote_route_available=False,
        )
        d = compile_entry_route(host, self.model_creator_task(), EVIDENCE)
        self.assertEqual(ComputeProfile.OFFLINE_DEGRADED, d.compute_profile)
        self.assertIn("NO_CURRENT_REMOTE_ROUTE_EVIDENCE", d.blockers)
        self.assertIn("SELECT_OR_ADD_REMOTE_ROUTE_IF_REQUIRED", d.required_actions)

    def test_offline_preference_prevents_remote_escalation(self):
        host = HostWitness(
            host_class="phone",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=1000,
            ram_mb=2048,
            local_compute_class="CONSTRAINED",
            free_remote_route_available=True,
        )
        d = compile_entry_route(
            host,
            self.model_creator_task(),
            EVIDENCE,
            EntryPreference(prefer_offline=True),
        )
        self.assertEqual(ComputeProfile.OFFLINE_DEGRADED, d.compute_profile)
        self.assertIn(
            "MODEL_TASK_LOCAL_CAPABILITY_INSUFFICIENT_FOR_OFFLINE_PREFERENCE",
            d.blockers,
        )

    def test_unknown_metrics_remain_unknown(self):
        host = HostWitness(
            host_class="browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=None,
            ram_mb=None,
            local_compute_class="UNKNOWN",
        )
        d = compile_entry_route(host, self.deterministic_creator_task(), EVIDENCE)
        self.assertIsNone(d.friction_components["downloaded_bytes"])
        self.assertIsNone(d.friction_components["time_to_first_accepted_value_ms"])
        self.assertIsNone(d.friction_components["monetary_cost_microunits"])

    def test_receipt_rejects_secret_values(self):
        host = HostWitness(
            host_class="browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=2000,
            ram_mb=4096,
            local_compute_class="CONSTRAINED",
        )
        d = compile_entry_route(host, self.deterministic_creator_task(), EVIDENCE)
        with self.assertRaises(CompileError):
            friction_receipt(
                d, route_id="r1", build_head="abc", observed={"api_key": "x"}
            )

    def test_receipt_effect_fields_are_hard_false(self):
        host = HostWitness(
            host_class="browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=2000,
            ram_mb=4096,
            local_compute_class="CONSTRAINED",
        )
        d = compile_entry_route(host, self.deterministic_creator_task(), EVIDENCE)
        r = friction_receipt(
            d, route_id="r1", build_head="abc", observed={"steps": 1}
        )
        for key in (
            "installation_performed",
            "permission_granted",
            "provider_call_made",
            "credential_stored",
            "public_deployment",
            "binary_distributed",
            "effect_authorized",
            "execution_proven",
        ):
            self.assertFalse(r[key])

    def test_evidence_binding_is_part_of_decision_identity(self):
        host = HostWitness(
            host_class="browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=2000,
            ram_mb=4096,
            local_compute_class="CONSTRAINED",
        )
        d1 = compile_entry_route(host, self.deterministic_creator_task(), EVIDENCE)
        d2 = compile_entry_route(
            host,
            self.deterministic_creator_task(),
            EvidenceBinding("drive:host-witness", "b" * 64, "gen-2"),
        )
        self.assertNotEqual(d1.decision_digest, d2.decision_digest)


if __name__ == "__main__":
    unittest.main()
