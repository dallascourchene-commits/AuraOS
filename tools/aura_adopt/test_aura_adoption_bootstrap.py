import unittest

from tools.aura_adopt.aura_adoption_bootstrap import (
    AdoptionRoute,
    CompileError,
    EntryPreference,
    FirstTask,
    HostWitness,
    compile_entry_route,
    friction_receipt,
)


class AdoptionBootstrapTests(unittest.TestCase):
    def creator_task(self):
        return FirstTask(
            task_id="creator.short.local.v1",
            domain="creator-studio",
            browser_supported=True,
            offline_supported=True,
            minimum_storage_mb=32,
        )

    def test_low_storage_phone_gets_zero_install_web_without_key(self):
        host = HostWitness(
            host_class="android-low-storage",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=512,
            ram_mb=2048,
            android=True,
        )
        d = compile_entry_route(host, self.creator_task())
        self.assertEqual(AdoptionRoute.ZERO_INSTALL_WEB_PWA, d.route)
        self.assertEqual((), d.required_actions)
        self.assertIn("MANDATORY_INSTALL", d.avoided_actions)
        self.assertIn("MANDATORY_API_KEY", d.avoided_actions)

    def test_native_required_android_requests_install_and_only_needed_permission(self):
        host = HostWitness(
            host_class="android-capable",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=12000,
            ram_mb=8192,
            android=True,
        )
        task = FirstTask(
            task_id="creator.camera.native.v1",
            domain="creator-studio",
            browser_supported=False,
            native_required=True,
            required_permissions=frozenset({"CAMERA"}),
        )
        d = compile_entry_route(host, task)
        self.assertEqual(AdoptionRoute.NATIVE_ANDROID_APK, d.route)
        self.assertEqual(
            ("INSTALL_NATIVE_ANDROID_SHELL", "GRANT_PERMISSION:CAMERA"),
            d.required_actions,
        )

    def test_developer_explicitly_gets_github_cli(self):
        host = HostWitness(
            host_class="desktop-dev",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=100000,
            ram_mb=32768,
            dev_cli_available=True,
        )
        d = compile_entry_route(host, self.creator_task(), EntryPreference(developer_mode=True))
        self.assertEqual(AdoptionRoute.DEV_CLI_GITHUB, d.route)
        self.assertIn("BINARY_TRUST_REQUIREMENT", d.avoided_actions)

    def test_local_model_avoids_key_when_browser_cannot_satisfy(self):
        host = HostWitness(
            host_class="linux-local",
            browser_available=False,
            browser_wasm=False,
            network_online=False,
            free_storage_mb=20000,
            ram_mb=16384,
            local_runtime_available=True,
            local_model_available=True,
        )
        task = FirstTask(
            task_id="reason.local.v1",
            domain="general",
            browser_supported=False,
            local_model_required=True,
        )
        d = compile_entry_route(host, task)
        self.assertEqual(AdoptionRoute.FULL_LOCAL, d.route)
        self.assertIn("MANDATORY_API_KEY", d.avoided_actions)

    def test_offline_missing_model_fails_degraded_not_fake_ready(self):
        host = HostWitness(
            host_class="offline-phone",
            browser_available=True,
            browser_wasm=True,
            network_online=False,
            free_storage_mb=1000,
            ram_mb=2048,
            android=True,
        )
        task = FirstTask(
            task_id="reason.offline.v1",
            domain="general",
            browser_supported=False,
            local_model_required=True,
            remote_model_allowed=False,
        )
        d = compile_entry_route(host, task)
        self.assertEqual(AdoptionRoute.OFFLINE_DEGRADED, d.route)
        self.assertIn("LOCAL_MODEL_UNAVAILABLE_OFFLINE", d.blockers)

    def test_permission_is_not_requested_for_browser_route(self):
        host = HostWitness(
            host_class="desktop-browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=10000,
            ram_mb=8192,
        )
        task = FirstTask(
            task_id="creator.caption.v1",
            domain="creator-studio",
            browser_supported=True,
            required_permissions=frozenset({"CAMERA"}),
        )
        d = compile_entry_route(host, task)
        self.assertEqual(AdoptionRoute.ZERO_INSTALL_WEB_PWA, d.route)
        self.assertEqual((), d.required_actions)

    def test_unknown_metrics_remain_unknown(self):
        host = HostWitness(
            host_class="browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=None,
            ram_mb=None,
        )
        d = compile_entry_route(host, self.creator_task())
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
        )
        d = compile_entry_route(host, self.creator_task())
        with self.assertRaises(CompileError):
            friction_receipt(d, route_id="r1", build_head="abc", observed={"api_key": "x"})

    def test_receipt_is_nonexecuting(self):
        host = HostWitness(
            host_class="browser",
            browser_available=True,
            browser_wasm=True,
            network_online=True,
            free_storage_mb=2000,
            ram_mb=4096,
        )
        d = compile_entry_route(host, self.creator_task())
        r = friction_receipt(d, route_id="r1", build_head="abc", observed={"steps": 1})
        self.assertFalse(r["effect_authorized"])
        self.assertFalse(r["execution_proven"])


if __name__ == "__main__":
    unittest.main()
