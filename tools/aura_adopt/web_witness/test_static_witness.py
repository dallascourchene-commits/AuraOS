from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
STAGES = (
    "DISCOVER", "TRUST", "OPEN_INSTALL", "PERMISSION", "STORAGE_CHOICE",
    "OPTIONAL_ACCOUNT", "OPTIONAL_KEY", "INPUT", "CAPABILITY_RESOLVE",
    "EXECUTE", "VERIFY_ACCEPT", "SAVE_REOPEN", "SHARE_OR_REUSE",
)
RECIPE_SHA256 = "a95b233ff6019fa6a32cc72715c2ba528b80d7d97258e8e6087948d426d3449d"


class ZeroInstallStaticWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = (HERE / "index.html").read_text(encoding="utf-8")
        cls.app = (HERE / "app.js").read_text(encoding="utf-8")
        cls.style = (HERE / "style.css").read_text(encoding="utf-8")
        cls.manifest = json.loads((HERE / "route_manifest.json").read_text(encoding="utf-8"))
        cls.recipe_bytes = (HERE / "recipe_v1.json").read_bytes()
        cls.recipe = json.loads(cls.recipe_bytes)

    def test_route_is_zero_install_and_provider_free(self) -> None:
        m = self.manifest
        self.assertEqual("AuraAdoptWebRouteV1", m["schema"])
        self.assertEqual("ZERO_INSTALL_WEB_PWA", m["entry_surface"])
        self.assertFalse(m["mandatory_install"])
        self.assertFalse(m["mandatory_account"])
        self.assertFalse(m["mandatory_api_key"])
        self.assertFalse(m["mandatory_model"])
        self.assertFalse(m["mandatory_provider_call"])
        self.assertEqual([], m["remote_dependencies"])
        self.assertEqual("OFF", m["telemetry_default"])

    def test_csp_denies_connect_and_page_has_no_remote_script_or_stylesheet(self) -> None:
        self.assertIn("connect-src 'none'", self.index)
        self.assertNotRegex(self.index, r'<script[^>]+src=["\']https?://')
        self.assertNotRegex(self.index, r'<link[^>]+href=["\']https?://')
        self.assertNotIn("fetch(", self.app)
        self.assertNotIn("XMLHttpRequest", self.app)
        self.assertNotIn("WebSocket", self.app)

    def test_only_thin_browser_capabilities_are_required(self) -> None:
        self.assertEqual(
            ["File API", "Blob/Object URL", "Canvas 2D", "download attribute"],
            self.manifest["required_browser_capabilities"],
        )
        forbidden = ("Pyodide", "WebLLM", "ffmpeg.wasm", "WebGPU", "Google OAuth")
        combined = self.index + self.app + self.style
        for token in forbidden:
            self.assertNotIn(token, combined)

    def test_recipe_digest_and_manifest_binding_are_exact(self) -> None:
        canonical = json.dumps(
            self.recipe, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        self.assertEqual(RECIPE_SHA256, digest)
        self.assertIn(RECIPE_SHA256, self.manifest["recipe_ref"])
        self.assertIn(RECIPE_SHA256, self.index)
        self.assertIn(RECIPE_SHA256, self.app)

    def test_recipe_has_no_external_authority_dependency(self) -> None:
        authority = self.recipe["authority"]
        self.assertEqual(
            {
                "network_required": False,
                "upload_required": False,
                "account_required": False,
                "api_key_required": False,
                "provider_call_required": False,
            },
            authority,
        )
        self.assertEqual("image/png", self.recipe["output"]["mime_type"])
        self.assertEqual((1280, 720), (self.recipe["output"]["width"], self.recipe["output"]["height"]))

    def test_all_consequence_stages_are_explicit_in_client(self) -> None:
        for stage in STAGES:
            self.assertIn(f'"{stage}"', self.app)
        self.assertIn('schema: "AdoptionFrictionReceiptV1"', self.app)
        self.assertIn("PROVISIONAL_ZF01_SUPERSET_AWAIT_ZF00B_REDUCER", self.app)
        self.assertIn("accepted_value_criterion", self.app)

    def test_burden_omission_cannot_masquerade_as_zero_install(self) -> None:
        required_receipt_terms = (
            "install_actions", "mandatory_account", "mandatory_api_key",
            "downloaded_dependency_bytes", "permissions_requested", "provider_cost_microunits",
        )
        for term in required_receipt_terms:
            self.assertIn(term, self.app)
        self.assertIn("LOCAL_ONLY_NO_TELEMETRY_NO_CONTENT_IN_RECEIPT", self.app)

    def test_capability_failure_has_typed_next_route(self) -> None:
        failures = self.manifest["failure_routes"]
        self.assertEqual("DOWNLOAD_APP_OR_ASSISTED_PATH", failures["BROWSER_CAPABILITY_UNAVAILABLE"])
        self.assertIn("BROWSER_CAPABILITY_UNAVAILABLE", self.app)
        self.assertIn("DOWNLOAD_APP_OR_ASSISTED_PATH", self.app)

    def test_user_acceptance_precedes_download_and_receipt(self) -> None:
        self.assertIn('id="accept-output"', self.index)
        self.assertIn('id="download-button" type="button" disabled', self.index)
        self.assertIn('id="receipt-button" type="button" disabled', self.index)
        self.assertIn("downloadButton.disabled = !state.accepted", self.app)
        self.assertIn("receiptButton.disabled = !(state.accepted && state.saved)", self.app)

    def test_static_asset_inventory_is_closed(self) -> None:
        paths = [row["path"] for row in self.manifest["required_assets"]]
        self.assertEqual(["index.html", "style.css", "app.js"], paths)
        for path in paths:
            self.assertTrue((HERE / path).is_file())

    def test_selftest_path_exercises_real_canvas_encode(self) -> None:
        self.assertIn('get("selftest") === "1"', self.app)
        self.assertIn('document.body.dataset.selftest = "PASS"', self.app)
        self.assertIn("await canvasBlob()", self.app)
        self.assertIn("state.renderedBlob.size > 0", self.app)


if __name__ == "__main__":
    unittest.main()
