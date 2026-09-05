from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

from airllm_secure_wrapper import (
    InvalidAllowlistError,
    LoaderSourceIntegrityError,
    ModelIntegrityError,
    RemoteCodeTrustError,
    SecureAirLLMWrapper,
    UnsafeLoadOptionError,
    UnsafeModelArtifactError,
    hard_false_remote_code_membrane,
    normalize_allowlist,
    sha256_loader_source,
    sha256_model_path,
    verify_loader_source,
    verify_model_allowlist,
)


def write_safetensors(path: Path, payload: bytes = b"\x01\x02\x03\x04") -> Path:
    header = {
        "weight": {
            "dtype": "U8",
            "shape": [len(payload)],
            "data_offsets": [0, len(payload)],
        }
    }
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    padding = (-len(raw)) % 8
    raw += b" " * padding
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + payload)
    return path


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


class FakeDynamicModule:
    @staticmethod
    def get_class_from_dynamic_module(*args, **kwargs):
        return "unsafe"


class FakeTransformers:
    AutoConfig = type("AutoConfig", (RecorderBoundary,), {"calls": []})
    AutoTokenizer = type("AutoTokenizer", (RecorderBoundary,), {"calls": []})
    AutoModel = type("AutoModel", (RecorderBoundary,), {"calls": []})
    AutoModelForCausalLM = type("AutoModelForCausalLM", (RecorderBoundary,), {"calls": []})
    dynamic_module_utils = FakeDynamicModule


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


class DynamicModuleLoader:
    calls = []

    @classmethod
    def from_pretrained(cls, path, *args, **kwargs):
        cls.calls.append((path, args, dict(kwargs)))
        return FakeTransformers.dynamic_module_utils.get_class_from_dynamic_module("x")


class SecureWrapperTests(unittest.TestCase):
    def setUp(self):
        for cls in (
            FakeTransformers.AutoConfig,
            FakeTransformers.AutoTokenizer,
            FakeTransformers.AutoModel,
            FakeTransformers.AutoModelForCausalLM,
            OmittedTrustLoader,
            UnsafeInternalLoader,
            DynamicModuleLoader,
        ):
            cls.calls = []
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _file(self, name="model.safetensors", payload=b"\x01\x02\x03\x04"):
        return write_safetensors(self.root / name, payload)

    def _allow(self, model_id, path):
        digest, _ = sha256_model_path(path)
        return {model_id: {digest}}

    def _source_allow(self, loader=OmittedTrustLoader):
        return {sha256_loader_source(loader).sha256}

    def _wrapper(self, model_id, path, loader=OmittedTrustLoader):
        return SecureAirLLMWrapper(
            self._allow(model_id, path),
            loader_source_allowlist=self._source_allow(loader),
            loader=loader,
            transformers_module=FakeTransformers,
        )

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
        write_safetensors(model / "b.safetensors", b"B")
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
        real = write_safetensors(model / "real.safetensors")
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
        with self.assertRaises(UnsafeModelArtifactError):
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
        wrapper = self._wrapper("glm", path)
        self.assertEqual(wrapper.load("glm", path), "loaded")
        self.assertEqual(len(OmittedTrustLoader.calls), 1)
        self.assertIs(OmittedTrustLoader.calls[0][2]["delete_original"], False)
        for boundary in (FakeTransformers.AutoConfig, FakeTransformers.AutoTokenizer, FakeTransformers.AutoModelForCausalLM):
            self.assertTrue(boundary.calls)
            self.assertIs(boundary.calls[-1][2]["trust_remote_code"], False)

    def test_12_wrapper_rejects_caller_remote_code_widening_before_loader(self):
        path = self._file()
        wrapper = self._wrapper("glm", path)
        with self.assertRaises(RemoteCodeTrustError):
            wrapper.load("glm", path, trust_remote_code=True)
        self.assertEqual(OmittedTrustLoader.calls, [])

    def test_13_wrapper_blocks_stock_style_internal_true_fallback(self):
        path = self._file()
        wrapper = self._wrapper("glm", path, UnsafeInternalLoader)
        with self.assertRaises(RemoteCodeTrustError):
            wrapper.load("glm", path)
        self.assertEqual(len(UnsafeInternalLoader.calls), 1)

    def test_14_wrapper_rejects_destructive_delete_original(self):
        path = self._file()
        wrapper = self._wrapper("glm", path)
        with self.assertRaises(UnsafeLoadOptionError):
            wrapper.load("glm", path, delete_original=True)
        self.assertEqual(OmittedTrustLoader.calls, [])

    def test_15_digest_change_after_allowlist_creation_is_rejected(self):
        path = self._file(payload=b"\x01")
        allowlist = self._allow("glm", path)
        write_safetensors(path, b"\x02")
        wrapper = SecureAirLLMWrapper(
            allowlist,
            loader_source_allowlist=self._source_allow(),
            loader=OmittedTrustLoader,
            transformers_module=FakeTransformers,
        )
        with self.assertRaises(ModelIntegrityError):
            wrapper.load("glm", path)
        self.assertEqual(OmittedTrustLoader.calls, [])

    def test_16_five_original_hard_admission_axes_remain_noncompensatory(self):
        path = self._file()
        digest, _ = sha256_model_path(path)
        source = self._source_allow()
        for local_ok in (False, True):
            for id_ok in (False, True):
                for digest_ok in (False, True):
                    for hard_false in (False, True):
                        for nondestructive in (False, True):
                            expected = local_ok and id_ok and digest_ok and hard_false and nondestructive
                            model_path = path if local_ok else self.root / "missing"
                            model_id = "glm" if id_ok else "other"
                            allow = {"glm": [digest if digest_ok else "0" * 64]}
                            wrapper = SecureAirLLMWrapper(
                                allow,
                                loader_source_allowlist=source,
                                loader=OmittedTrustLoader,
                                transformers_module=FakeTransformers,
                            )
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
                            self.assertEqual(admitted, expected)

    def test_17_pickle_family_weights_are_rejected_even_if_hashable(self):
        for name in ("pytorch_model.bin", "model.pt", "model.pth", "model.ckpt", "model.pkl"):
            model = self.root / name.replace(".", "_")
            model.mkdir()
            write_safetensors(model / "safe.safetensors")
            (model / name).write_bytes(b"not-even-real-pickle")
            with self.subTest(name=name), self.assertRaises(UnsafeModelArtifactError):
                sha256_model_path(model)

    def test_18_executable_payloads_are_rejected_from_model_tree(self):
        for name in ("modeling_custom.py", "hook.sh", "native.so", "run.exe"):
            model = self.root / name.replace(".", "_")
            model.mkdir()
            write_safetensors(model / "safe.safetensors")
            (model / name).write_bytes(b"x")
            with self.subTest(name=name), self.assertRaises(UnsafeModelArtifactError):
                sha256_model_path(model)

    def test_19_renamed_random_payload_is_not_safetensors(self):
        path = self.root / "fake.safetensors"
        path.write_bytes(b"this is not safetensors")
        with self.assertRaises(UnsafeModelArtifactError):
            sha256_model_path(path)

    def test_20_out_of_bounds_safetensors_offsets_are_rejected(self):
        path = self.root / "bad.safetensors"
        header = {"w": {"dtype": "U8", "shape": [1], "data_offsets": [0, 99]}}
        raw = json.dumps(header, separators=(",", ":")).encode()
        path.write_bytes(struct.pack("<Q", len(raw)) + raw + b"x")
        with self.assertRaises(UnsafeModelArtifactError):
            sha256_model_path(path)

    def test_21_loader_source_requires_exact_sha256(self):
        verified = sha256_loader_source(OmittedTrustLoader)
        self.assertEqual(
            verify_loader_source(OmittedTrustLoader, [verified.sha256]),
            verified,
        )
        with self.assertRaises(LoaderSourceIntegrityError):
            verify_loader_source(OmittedTrustLoader, ["0" * 64])

    def test_22_wrapper_requires_nonempty_loader_source_allowlist(self):
        path = self._file()
        with self.assertRaises(InvalidAllowlistError):
            SecureAirLLMWrapper(
                self._allow("glm", path),
                loader_source_allowlist=None,
                loader=OmittedTrustLoader,
                transformers_module=FakeTransformers,
            )

    def test_23_dynamic_module_resolution_is_denied(self):
        path = self._file()
        wrapper = self._wrapper("glm", path, DynamicModuleLoader)
        with self.assertRaises(RemoteCodeTrustError):
            wrapper.load("glm", path)
        self.assertEqual(len(DynamicModuleLoader.calls), 1)

    def test_24_dynamic_module_resolver_is_restored(self):
        original = FakeTransformers.dynamic_module_utils.get_class_from_dynamic_module
        with hard_false_remote_code_membrane(FakeTransformers):
            with self.assertRaises(RemoteCodeTrustError):
                FakeTransformers.dynamic_module_utils.get_class_from_dynamic_module("x")
        self.assertIs(FakeTransformers.dynamic_module_utils.get_class_from_dynamic_module, original)

    def test_25_model_mutation_during_loader_resolution_is_caught(self):
        path = self._file(payload=b"\x01")
        allow = self._allow("glm", path)

        class MutatingWrapper(SecureAirLLMWrapper):
            def _resolve_loader(inner_self):
                write_safetensors(path, b"\x02")
                return OmittedTrustLoader

        wrapper = MutatingWrapper(
            allow,
            loader_source_allowlist=self._source_allow(),
            loader=OmittedTrustLoader,
            transformers_module=FakeTransformers,
        )
        with self.assertRaises(ModelIntegrityError):
            wrapper.load("glm", path)
        self.assertEqual(OmittedTrustLoader.calls, [])

    def test_26_loader_source_change_before_invocation_is_caught_by_second_check(self):
        path = self._file()
        wrapper = self._wrapper("glm", path)
        wrapper._loader_source_allowlist = frozenset({"0" * 64})
        with self.assertRaises(LoaderSourceIntegrityError):
            wrapper.load("glm", path)
        self.assertEqual(OmittedTrustLoader.calls, [])


if __name__ == "__main__":
    unittest.main()
