import json
import os
import pathlib
import unittest
from unittest import mock

from tools.project006 import creator_media_nono_runner as runner


class NonoRunnerTests(unittest.TestCase):
    def test_accepts_phantom_with_loopback_https_proxy(self):
        with mock.patch.dict(
            os.environ,
            {
                "HIGGSFIELD_API_CREDENTIAL": "nono_test_phantom",
                "HTTPS_PROXY": "http://nono:session@127.0.0.1:43210",
            },
            clear=True,
        ):
            self.assertEqual(runner._nono_phantom_credential(), "nono_test_phantom")

    def test_rejects_raw_higgsfield_id_secret_shape(self):
        with mock.patch.dict(
            os.environ,
            {
                "HIGGSFIELD_API_CREDENTIAL": "id-value:secret-value",
                "HTTPS_PROXY": "http://nono:session@127.0.0.1:43210",
            },
            clear=True,
        ):
            self.assertIsNone(runner._nono_phantom_credential())

    def test_rejects_non_loopback_proxy(self):
        with mock.patch.dict(
            os.environ,
            {
                "HIGGSFIELD_API_CREDENTIAL": "nono_test_phantom",
                "HTTPS_PROXY": "http://proxy.example:8080",
            },
            clear=True,
        ):
            self.assertIsNone(runner._nono_phantom_credential())

    def test_rejects_missing_proxy(self):
        with mock.patch.dict(
            os.environ,
            {"HIGGSFIELD_API_CREDENTIAL": "nono_test_phantom"},
            clear=True,
        ):
            self.assertIsNone(runner._nono_phantom_credential())

    def test_nono_profile_has_fixed_windows_capture_and_no_secret_value(self):
        profile_path = pathlib.Path(__file__).parent / "nono_profiles" / "creator-studio-higgsfield.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        network = profile["network"]
        route = network["custom_credentials"]["higgsfield"]
        capture = profile["credential_capture"]["higgsfield-windows-user-env"]

        self.assertIn("higgsfield", network["credentials"])
        self.assertEqual(route["upstream"], "https://platform.higgsfield.ai")
        self.assertEqual(route["credential_key"], "cmd://higgsfield-windows-user-env")
        self.assertEqual(route["env_var"], "HIGGSFIELD_API_CREDENTIAL")
        self.assertEqual(route["credential_format"], "Key {}")
        self.assertIn("HIGGSFIELD_API_CREDENTIAL", profile["environment"]["deny_vars"])

        command = capture["command"]
        self.assertEqual(
            command[0],
            "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
        )
        self.assertIn("GetEnvironmentVariable('HIGGSFIELD_API_CREDENTIAL','User')", command[-1])
        serialized = json.dumps(profile)
        self.assertNotIn("id-value:secret-value", serialized)

        endpoint_pairs = {
            (entry["method"], entry["path"])
            for entry in route["endpoint_rules"]
        }
        self.assertIn(("POST", "/kling-video/v3.0/std/text-to-video"), endpoint_pairs)
        self.assertIn(("GET", "/requests/**"), endpoint_pairs)


if __name__ == "__main__":
    unittest.main()
