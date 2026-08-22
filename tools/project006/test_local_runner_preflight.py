from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools.project006 import local_runner_preflight as p


class LocalRunnerPreflightTests(unittest.TestCase):
    def test_systemd_query_does_not_request_environment_or_credentials(self) -> None:
        seen = []

        def runner(argv):
            seen.extend(argv)
            return (
                0,
                "LoadState=loaded\nActiveState=active\nSubState=running\nMainPID=77\n"
                "FragmentPath=/tmp/aura-project006.service\nRuntimeDirectory=aura-project006\nUser=\n",
                "",
            )

        with mock.patch.object(p, "_file_identity", return_value={"path": "/tmp/unit", "exists": True, "sha256": "a" * 64}):
            result = p._systemd_properties("aura-project006.service", runner)

        rendered = " ".join(seen)
        self.assertNotIn("Environment", rendered)
        self.assertNotIn("API", rendered.upper())
        self.assertEqual(result["active_state"], "active")
        self.assertEqual(result["main_pid"], 77)

    @mock.patch.object(p, "_credential_presence", return_value={"state": "PRESENT", "source_class": "TEST_NONSECRET"})
    @mock.patch.object(p, "_socket_identity", return_value={"path": "/run/user/1000/aura.sock", "exists": True, "is_socket": True, "uid": 1000, "gid": 1000, "mode": "0o600"})
    @mock.patch.object(p, "_discover_socket", return_value="/run/user/1000/aura.sock")
    @mock.patch.object(p, "_file_identity", return_value={"path": "/bounded", "exists": True, "sha256": "b" * 64, "size": 1, "mode": "0o600", "uid": 1000})
    @mock.patch.object(p, "_process_identity", return_value={"pid": 77, "alive": True, "exe": "/usr/bin/python3", "cmdline_sha256": "c" * 64})
    @mock.patch.object(p, "_systemd_properties", return_value={"unit": "aura-project006.service", "query_ok": True, "load_state": "loaded", "active_state": "active", "sub_state": "running", "main_pid": 77, "fragment_path": "/tmp/unit", "runtime_directory": "aura-project006", "service_user": None, "unit_file_identity": {"path": "/tmp/unit", "exists": True, "sha256": "d" * 64}})
    @mock.patch.object(p, "_wsl_identity", return_value={"is_wsl": True, "distro": "Ubuntu", "kernel_release": "test", "machine": "x86_64"})
    def test_local_health_does_not_launder_unknown_source_packages_into_ready(self, *_mocks) -> None:
        receipt = p.collect_preflight(now_ms=1234567890)
        self.assertEqual(receipt["schema"], p.SCHEMA)
        self.assertEqual(receipt["ready_state"], p.BLOCKED_REVIEW)
        self.assertTrue(any(b["code"] == "P4_P10_SOURCE_PACKAGE_NOT_ADMITTED" for b in receipt["blockers"]))
        self.assertTrue(receipt["no_secret_log_attestation"])
        self.assertEqual(len(receipt["receipt_digest"]), 64)

    @mock.patch.object(p, "_credential_presence", return_value={"state": "ABSENT", "source_class": "TEST_NONSECRET"})
    @mock.patch.object(p, "_socket_identity", return_value={"path": "/run/user/1000/aura.sock", "exists": True, "is_socket": True})
    @mock.patch.object(p, "_discover_socket", return_value="/run/user/1000/aura.sock")
    @mock.patch.object(p, "_file_identity", return_value={"path": "/bounded", "exists": True, "sha256": "b" * 64})
    @mock.patch.object(p, "_process_identity", return_value={"pid": 77, "alive": True, "exe": "/usr/bin/python3", "cmdline_sha256": "c" * 64})
    @mock.patch.object(p, "_systemd_properties", return_value={"unit": "aura-project006.service", "query_ok": True, "load_state": "loaded", "active_state": "active", "sub_state": "running", "main_pid": 77, "fragment_path": "/tmp/unit", "runtime_directory": "aura-project006", "service_user": None, "unit_file_identity": None})
    @mock.patch.object(p, "_wsl_identity", return_value={"is_wsl": True, "distro": "Ubuntu", "kernel_release": "test", "machine": "x86_64"})
    def test_missing_deepseek_credential_presence_blocks_provider(self, *_mocks) -> None:
        with tempfile.TemporaryDirectory() as td:
            package_file = Path(td) / "packages.json"
            package_file.write_text(
                json.dumps(
                    {
                        **{f"wp0{i}_identity": f"owner-{i}" for i in (2, 3, 5, 6, 7, 8, 9)},
                        **{f"wp0{i}_state": "PASS" for i in (2, 3, 5, 6, 7, 8, 9)},
                    }
                ),
                encoding="utf-8",
            )
            receipt = p.collect_preflight(package_state_file=str(package_file), now_ms=1234567890)
        self.assertEqual(receipt["ready_state"], p.BLOCKED_PROVIDER)
        self.assertTrue(any(b["code"] == "P3_DEEPSEEK_CREDENTIAL_NOT_PRESENT" for b in receipt["blockers"]))

    def test_package_state_parser_does_not_copy_nested_or_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(
                json.dumps({"wp02_state": "PASS", "api_key": "SHOULD_NOT_COPY", "wp03_state": {"nested": "bad"}}),
                encoding="utf-8",
            )
            result = p._load_package_state(str(path))
        self.assertEqual(result["wp02_state"], "PASS")
        self.assertEqual(result["wp03_state"], "UNKNOWN")
        self.assertNotIn("api_key", result)


if __name__ == "__main__":
    unittest.main()
