import unittest

from tools.aura_adopt.aura_drive_bootstrap import (
    BootstrapError,
    BootstrapRequest,
    CloudAdmissionEvidence,
    SourceBinding,
    StorageCapabilities,
    StorageIntent,
    compile_bootstrap_plan,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


class BootstrapTests(unittest.TestCase):
    def source(self, ref="source:req", digest=D1, gen="gen-1", current="CURRENT"):
        return SourceBinding(ref, digest, gen, current)

    def caps(self, local="AVAILABLE", portable="AVAILABLE", cloud="AVAILABLE", network="AVAILABLE"):
        return StorageCapabilities(
            source=self.source("source:caps", D2, "gen-2"),
            local_persistence=local,
            portable_file=portable,
            cloud_connector=cloud,
            network=network,
        )

    def request(self, **kwargs):
        return BootstrapRequest(
            request_id="bootstrap:test",
            source=self.source(),
            capabilities=kwargs.pop("capabilities", self.caps()),
            intent=kwargs.pop("intent", StorageIntent()),
            cloud=kwargs.pop("cloud", None),
            policy=kwargs.pop("policy", {}),
            **kwargs,
        )

    def cloud(self, link="NOT_LINKED", current="CURRENT"):
        return CloudAdmissionEvidence(
            "connector:gdrive",
            self.source("connector:gdrive", D3, "cloud-gen", current),
            link,
        )

    def test_default_local_first_has_no_cloud_prompt(self):
        plan = compile_bootstrap_plan(self.request())
        self.assertEqual("LOCAL_PERSISTENT", plan["primary_location"])
        self.assertEqual("PORTABLE_EXPORT_REOPEN", plan["secondary_location"])
        self.assertEqual("READY_FOR_LOCAL_USER_ACTION", plan["status"])
        self.assertFalse(plan["cloud_controls_visible"])
        self.assertFalse(plan["account_link_prompt_visible"])
        self.assertEqual([], plan["required_user_actions"])

    def test_nondefault_mode_requires_explicit_selection(self):
        with self.assertRaisesRegex(BootstrapError, "EXPLICIT_STORAGE_SELECTION_REQUIRED"):
            StorageIntent("CLOUD_BACKED", False)

    def test_portable_fallback_when_local_unavailable(self):
        plan = compile_bootstrap_plan(
            self.request(capabilities=self.caps(local="UNAVAILABLE", portable="AVAILABLE"))
        )
        self.assertEqual("PORTABLE_FILE_ONLY", plan["primary_location"])
        self.assertNotIn("CLOUD_ADMISSION_EVIDENCE_REQUIRED", plan["blockers"])

    def test_no_silent_cloud_fallback(self):
        plan = compile_bootstrap_plan(
            self.request(capabilities=self.caps(local="UNAVAILABLE", portable="UNAVAILABLE"))
        )
        self.assertIn("NO_LOCAL_OR_PORTABLE_STORAGE_PATH", plan["blockers"])
        self.assertFalse(plan["cloud_selected"])

    def test_unknown_local_blocks_default(self):
        plan = compile_bootstrap_plan(self.request(capabilities=self.caps(local="UNKNOWN")))
        self.assertIn("LOCAL_PERSISTENCE_UNKNOWN", plan["blockers"])

    def test_explicit_cloud_needs_admission(self):
        plan = compile_bootstrap_plan(self.request(intent=StorageIntent("CLOUD_BACKED", True)))
        self.assertIn("CLOUD_ADMISSION_EVIDENCE_REQUIRED", plan["blockers"])

    def test_explicit_cloud_not_linked_requests_user_action_only(self):
        plan = compile_bootstrap_plan(
            self.request(intent=StorageIntent("CLOUD_BACKED", True), cloud=self.cloud("NOT_LINKED"))
        )
        self.assertEqual("READY_FOR_STORAGE_AUTHORITY_GATE", plan["status"])
        self.assertIn("USER_LINK_CLOUD_ACCOUNT", plan["required_user_actions"])
        self.assertTrue(plan["account_link_prompt_visible"])
        self.assertFalse(plan["account_link_authorized"])
        self.assertFalse(plan["cloud_write_authorized"])

    def test_linked_cloud_still_requires_scope_confirmation(self):
        plan = compile_bootstrap_plan(
            self.request(intent=StorageIntent("CLOUD_BACKED", True), cloud=self.cloud("LINKED"))
        )
        self.assertIn("USER_CONFIRM_CLOUD_STORAGE_SCOPE", plan["required_user_actions"])
        self.assertFalse(plan["cloud_read_authorized"])

    def test_cloud_account_unknown_blocks(self):
        plan = compile_bootstrap_plan(
            self.request(intent=StorageIntent("CLOUD_BACKED", True), cloud=self.cloud("UNKNOWN"))
        )
        self.assertIn("CLOUD_ACCOUNT_LINK_STATE_UNKNOWN", plan["blockers"])

    def test_cloud_connector_unavailable_blocks(self):
        plan = compile_bootstrap_plan(
            self.request(
                capabilities=self.caps(cloud="UNAVAILABLE"),
                intent=StorageIntent("CLOUD_BACKED", True),
                cloud=self.cloud("LINKED"),
            )
        )
        self.assertIn("CLOUD_CONNECTOR_CAPABILITY_UNAVAILABLE", plan["blockers"])

    def test_network_unknown_blocks_cloud(self):
        plan = compile_bootstrap_plan(
            self.request(
                capabilities=self.caps(network="UNKNOWN"),
                intent=StorageIntent("CLOUD_BACKED", True),
                cloud=self.cloud("LINKED"),
            )
        )
        self.assertIn("NETWORK_CAPABILITY_UNKNOWN", plan["blockers"])

    def test_hybrid_requires_local(self):
        plan = compile_bootstrap_plan(
            self.request(
                capabilities=self.caps(local="UNAVAILABLE"),
                intent=StorageIntent("HYBRID", True),
                cloud=self.cloud("LINKED"),
            )
        )
        self.assertIn("HYBRID_REQUIRES_LOCAL_PERSISTENCE", plan["blockers"])

    def test_stale_request_source_blocks(self):
        request = self.request()
        request = BootstrapRequest(
            request_id=request.request_id,
            source=self.source(current="STALE"),
            capabilities=request.capabilities,
        )
        plan = compile_bootstrap_plan(request)
        self.assertIn("REQUEST_SOURCE_CURRENTNESS_STALE", plan["blockers"])

    def test_stale_cloud_source_blocks(self):
        plan = compile_bootstrap_plan(
            self.request(
                intent=StorageIntent("CLOUD_BACKED", True),
                cloud=self.cloud("LINKED", "STALE"),
            )
        )
        self.assertIn("CLOUD_SOURCE_CURRENTNESS_STALE", plan["blockers"])

    def test_connector_ref_mismatch_blocks(self):
        cloud = CloudAdmissionEvidence(
            "connector:one",
            self.source("connector:two", D3, "cloud-gen", "CURRENT"),
            "LINKED",
        )
        plan = compile_bootstrap_plan(
            self.request(intent=StorageIntent("CLOUD_BACKED", True), cloud=cloud)
        )
        self.assertIn("CLOUD_CONNECTOR_REF_MISMATCH", plan["blockers"])

    def test_secret_policy_rejected(self):
        with self.assertRaisesRegex(BootstrapError, "FORBIDDEN_BOOTSTRAP_FIELD"):
            self.request(policy={"api_key": "nope"})

    def test_remote_endpoint_rejected(self):
        with self.assertRaisesRegex(BootstrapError, "REMOTE_URL_FORBIDDEN"):
            self.request(policy={"link": "https://drive.example/latest"})

    def test_all_effects_hard_false(self):
        plan = compile_bootstrap_plan(self.request())
        for key in (
            "local_write_authorized", "local_read_authorized", "portable_export_authorized",
            "portable_reopen_proven", "cloud_read_authorized", "cloud_write_authorized",
            "cloud_sync_authorized", "account_link_authorized", "network_fetch_authorized",
            "effect_authorized", "execution_proven",
        ):
            self.assertFalse(plan[key])

    def test_plan_digest_is_deterministic(self):
        self.assertEqual(
            compile_bootstrap_plan(self.request())["plan_digest"],
            compile_bootstrap_plan(self.request())["plan_digest"],
        )


if __name__ == "__main__":
    unittest.main()
