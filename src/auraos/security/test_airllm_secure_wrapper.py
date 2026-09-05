from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from airllm_secure_wrapper import (
    InvalidAllowlistError,
    ModelIntegrityError,
    RemoteCodeTrustError,
    SecureAirLLMWrapper,
    UnsafeLoadOptionError,
    hard_false_remote_code_membrane,
    normalize_allowlist,
    sha256_model_path,
    verify_model_allowlist,
)


class RecorderBoundary:
    calls = []

    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        cls.calls.append(("from_pretrained", args, dict(kwargs)))
        return dict(kwargs)

    @classmethod
    def from_config(cls, *args, **kwargs):
        cls.calls.append(("from_config", args, dict(kwargs)))
        return dict(kwargs)


class FakeTransformers:
    AutoConfig = type("AutoConfig", (RecorderBoundary,), {"calls": []})
    AutoTokenizer = type("AutoTokenizer", (RecorderBoundary,), {"calls": []})
    AutoModel = type("AutoModel", (RecorderBoundary,), {"calls": []})
    AutoModelForCausalLM = type("AutoModelForCausalLM", (RecorderBoundary,), {"calls": []})


class OmittedTrustLoader:
    calls = []

    @classmethod
    def from_pretrained(cls, path, *args, **kwargs):
        cls.calls.append((path, args, dict(kwargs)))
        FakeTransformers.AutoConfig.from_pretrained(path)
        FakeTransformers.AutoTokenizer.from_pretrained(path)
        FakeTransformers.AutoModelForCausalLM.from_config(object())
        return "loaded"


class UnsafeInternalLoader:
    calls = []

    @classmethod
    def from_pretrained(cls, path, *args, **kwargs):
        cls.calls.append((path, args, dict(kwargs)))
        return FakeTransformers.AutoConfig.from_pretrained(path, trust_remote_code=True)


class SecureWrapperTests(unittest.TestCase):
    def setUp(self):
        for cls in (
            FakeTransformers.AutoConfig,
            FakeTransformers.AutoTokenizer,
            FakeTransformers.AutoModel,
            FakeTransformers.AutoModelForCausalLM,
            OmittedTrustLoader,
            UnsafeInternalLoader,
        ):
            cls.calls = []
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _file(self, name="model.safetensors", payload=b"safe-model"):
        path = self.root / name
        path.write_bytes(payload)
        return path

    def _allow(self, model_id, path):
        digest, _ = sha256_model_path(path)
        return {model_id: {digest}}

    def test_01_allowlist_requires_exact_lowercase_sha256(self):
        good = "a" * 64
        self.assertEqual(normalize_allowlist({"m": [good]}), {"m": frozenset({good})})
        for bad in ("A" * 64, "a" * 63, "g" * 64, " sha", ""):
            with self.subTest(bad=bad), self.assertRaises(InvalidAllowlistError):
                normalize_allowlist({"m": [bad]})

    def test_02_allowlist_rejects_ambiguous_shapes(self):
        with self.assertRaises(InvalidAllowlistError):
            normalize_allowlist({})
        with self.assertRaises(InvalidAllowlistError):
            normalize_allowlist({"m": "a" * 64})
        with self.assertRaises(InvalidAllowlistError):
            normalize_allowlist({" m": ["a" * 64]})
        with self.assertRaises(InvalidAllowlistError):
            normalize_allowlist({"m": []})

    def test_03_exact_file_sha256_is_admitted(self):
        path = self._file()
        digest = sha256(path.read_bytes()).hexdigest()
        verified = verify_model_allowlist("glm", path, {"glm": [digest]})
        self.assertEqual((verified.sha256, verified.kind), (digest, "file"))
        self.assertEqual(Path(verified.path), path)

    def test_04_unknown_model_and_digest_mismatch_fail_closed(self):
        path = self._file()
        digest = sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ModelIntegrityError):
            verify_model_allowlist("other", path, {"glm": [digest]})
        with self.assertRaises(ModelIntegrityError):
            verify_model_allowlist("glm", path, {"glm": ["0" * 64]})

    def test_05_directory_digest_is_canonical_and_mutation_sensitive(self):
        model = self.root / "model"
        model.mkdir()
        (model / "b.safetensors").write_bytes(b"B")
        (model / "a.json").write_text('{"x":1}', encoding="utf-8")
        first, kind = sha256_model_path(model)
        second, _ = sha256_model_path(model)
        self.assertEqual(kind, "directory")
        self.assertEqual(first, second)
        (model / "a.json").write_text('{"x":2}', encoding="utf-8")
        changed, _ = sha256_model_path(model)
        self.assertNotEqual(first, changed)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unsupported")
    def test_06_symlinks_are_rejected_in_model_tree(self):
        model = self.root / "model"
        model.mkdir()
        real = model / "real.safetensors"
        real.write_bytes(b"x")
        link = model / "alias.safetensors"
        try:
            link.symlink_to(real)
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        with self.assertRaises(ModelIntegrityError):
            sha256_model_path(model)

    def test_07_empty_directory_and_missing_path_are_rejected(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(ModelIntegrityError):
            sha256_model_path(empty)
        with self.assertRaises(ModelIntegrityError):
            sha256_model_path(self.root / "missing")

    def test_08_membrane_injects_literal_false_when_omitted(self):
        with hard_false_remote_code_membrane(FakeTransformers):
            result = FakeTransformers.AutoConfig.from_pretrained("model")
            self.assertIs(result["trust_remote_code"], False)
            result = FakeTransformers.AutoModelForCausalLM.from_config(object())
            self.assertIs(result["trust_remote_code"], False)

    def test_09_membrane_rejects_remote_code_true(self):
        with hard_false_remote_code_membrane(FakeTransformers):
            with self.assertRaises(RemoteCodeTrustError):
                FakeTransformers.AutoTokenizer.from_pretrained("model", trust_remote_code=True)

    def test_10_membrane_restores_boundaries_after_exception(self):
        original = FakeTransformers.AutoConfig.__dict__["from_pretrained"]
        with self.assertRaises(RemoteCodeTrustError):
            with hard_false_remote_code_membrane(FakeTransformers):
                FakeTransformers.AutoConfig.from_pretrained("model", trust_remote_code=None)
        restored = FakeTransformers.AutoConfig.__dict__["from_pretrained"]
        self.assertIs(restored.__func__, original.__func__)

    def test_11_wrapper_verifies_then_loads_with_hard_false_membrane(self):
        path = self._file()
        wrapper = SecureAirLLMWrapper(
            self._allow("glm", path),
            loader=OmittedTrustLoader,
            transformers_module=FakeTransformers,
        )
        self.assertEqual(wrapper.load("glm", path), "loaded")
        self.assertEqual(len(OmittedTrustLoader.calls), 1)
        self.assertIs(OmittedTrustLoader.calls[0][2]["delete_original"], False)
        for boundary in (FakeTransformers.AutoConfig, FakeTransformers.AutoTokenizer, FakeTransformers.AutoModelForCausalLM):
            self.assertTrue(boundary.calls)
            self.assertIs(boundary.calls[-1][2]["trust_remote_code"], False)

    def test_12_wrapper_rejects_caller_remote_code_widening_before_loader(self):
        path = self._file()
        wrapper = SecureAirLLMWrapper(
            self._allow("glm", path),
            loader=OmittedTrustLoader,
            transformers_module=FakeTransformers,
        )
        with self.assertRaises(RemoteCodeTrustError):
            wrapper.load("glm", path, trust_remote_code=True)
        self.assertEqual(OmittedTrustLoader.calls, [])

    def test_13_wrapper_blocks_stock_style_internal_true_fallback(self):
        path = self._file()
        wrapper = SecureAirLLMWrapper(
            self._allow("glm", path),
            loader=UnsafeInternalLoader,
            transformers_module=FakeTransformers,
        )
        with self.assertRaises(RemoteCodeTrustError):
            wrapper.load("glm", path)
        self.assertEqual(len(UnsafeInternalLoader.calls), 1)

    def test_14_wrapper_rejects_destructive_delete_original(self):
        path = self._file()
        wrapper = SecureAirLLMWrapper(
            self._allow("glm", path),
            loader=OmittedTrustLoader,
            transformers_module=FakeTransformers,
        )
        with self.assertRaises(UnsafeLoadOptionError):
            wrapper.load("glm", path, delete_original=True)
        self.assertEqual(OmittedTrustLoader.calls, [])

    def test_15_digest_change_after_allowlist_creation_is_rejected(self):
        path = self._file(payload=b"v1")
        allowlist = self._allow("glm", path)
        path.write_bytes(b"v2")
        wrapper = SecureAirLLMWrapper(allowlist, loader=OmittedTrustLoader, transformers_module=FakeTransformers)
        with self.assertRaises(ModelIntegrityError):
            wrapper.load("glm", path)
        self.assertEqual(OmittedTrustLoader.calls, [])

    def test_16_all_five_hard_admission_axes_are_noncompensatory(self):
        # Finite 2^5 proof of the wrapper's admission law: local path, exact id,
        # exact digest, hard-false remote-code request, non-destructive load.
        path = self._file()
        digest, _ = sha256_model_path(path)
        for local_ok in (False, True):
            for id_ok in (False, True):
                for digest_ok in (False, True):
                    for hard_false in (False, True):
                        for nondestructive in (False, True):
                            expected = local_ok and id_ok and digest_ok and hard_false and nondestructive
                            model_path = path if local_ok else self.root / "missing"
                            model_id = "glm" if id_ok else "other"
                            allow = {"glm": [digest if digest_ok else "0" * 64]}
                            wrapper = SecureAirLLMWrapper(allow, loader=OmittedTrustLoader, transformers_module=FakeTransformers)
                            admitted = False
                            try:
                                wrapper.load(
                                    model_id,
                                    model_path,
                                    trust_remote_code=False if hard_false else True,
                                    delete_original=False if nondestructive else True,
                                )
                                admitted = True
                            except (ModelIntegrityError, RemoteCodeTrustError, UnsafeLoadOptionError):
                                admitted = False
                            self.assertEqual(admitted, expected, (local_ok, id_ok, digest_ok, hard_false, nondestructive))


if __name__ == "__main__":
    unittest.main()
