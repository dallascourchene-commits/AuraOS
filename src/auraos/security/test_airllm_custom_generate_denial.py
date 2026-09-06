from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from airllm_native_compat_wrapper import install_custom_generate_denial
from airllm_secure_wrapper import RemoteCodeTrustError


class VulnerableGenerationModel:
    """Models CVE-2026-80047 ordering: cache write occurs before trust resolution."""

    def __init__(self, marker: Path):
        self.marker = marker

    def load_custom_generate(self, repo, trust_remote_code=None, **kwargs):
        self.marker.write_text("remote python cached", encoding="utf-8")
        if trust_remote_code is not True:
            raise RemoteCodeTrustError("consent denied after cache write")
        return "remote"

    def generate(self, *args, custom_generate=None, trust_remote_code=False, **kwargs):
        if custom_generate is None:
            return "native"
        return self.load_custom_generate(
            custom_generate,
            trust_remote_code=trust_remote_code,
        )


class AirLLMGenerateDelegate:
    def __init__(self, inner):
        self.model = inner

    def generate(self, *args, **kwargs):
        return self.model.generate(*args, **kwargs)


class UnguardableGenerativeModel:
    def generate(self, *args, **kwargs):
        return "unknown"


class NonGenerativeResult:
    pass


class CustomGenerateDenialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_airllm_delegate_blocks_preconsent_cache_write(self):
        marker = self.root / "delegate.py"
        loaded = AirLLMGenerateDelegate(VulnerableGenerationModel(marker))
        self.assertIs(install_custom_generate_denial(loaded), loaded)
        with self.assertRaises(RemoteCodeTrustError):
            loaded.generate(custom_generate="attacker/repo", trust_remote_code=False)
        self.assertFalse(marker.exists())

    def test_direct_inner_generate_is_also_blocked_before_write(self):
        marker = self.root / "direct.py"
        loaded = AirLLMGenerateDelegate(VulnerableGenerationModel(marker))
        install_custom_generate_denial(loaded)
        with self.assertRaises(RemoteCodeTrustError):
            loaded.model.generate(custom_generate="attacker/repo", trust_remote_code=True)
        self.assertFalse(marker.exists())

    def test_native_generation_remains_available(self):
        marker = self.root / "native.py"
        loaded = AirLLMGenerateDelegate(VulnerableGenerationModel(marker))
        install_custom_generate_denial(loaded)
        self.assertEqual(loaded.generate(), "native")
        self.assertFalse(marker.exists())

    def test_unguardable_generative_target_fails_closed(self):
        with self.assertRaises(RemoteCodeTrustError):
            install_custom_generate_denial(UnguardableGenerativeModel())

    def test_non_generative_result_is_unchanged(self):
        result = NonGenerativeResult()
        self.assertIs(install_custom_generate_denial(result), result)

    def test_installation_is_idempotent(self):
        marker = self.root / "repeat.py"
        loaded = AirLLMGenerateDelegate(VulnerableGenerationModel(marker))
        self.assertIs(install_custom_generate_denial(loaded), loaded)
        self.assertIs(install_custom_generate_denial(loaded), loaded)
        with self.assertRaises(RemoteCodeTrustError):
            loaded.generate(custom_generate="attacker/repo")
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
