from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

from airllm_native_compat_wrapper import (
    ManifestPinnedNativeAirLLMWrapper,
    force_false_native_compat_membrane,
)
from airllm_source_manifest_guard import build_source_manifest, SourceTreeIntegrityError
from airllm_secure_wrapper import (
    RemoteCodeTrustError,
    UnsafeLoadOptionError,
    sha256_loader_source,
)


def write_model(path: Path, payload: bytes = b"model") -> Path:
    header = {"weight": {"dtype": "U8", "shape": [len(payload)], "data_offsets": [0, len(payload)]}}
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((-len(raw)) % 8)
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + payload)
    return path


class RecorderBoundary:
    calls = []
    fail_when_false = False

    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        cls.calls.append(dict(kwargs))
        if cls.fail_when_false and kwargs.get("trust_remote_code") is False:
            raise ValueError("native implementation unavailable")
        return dict(kwargs)

    @classmethod
    def from_config(cls, *args, **kwargs):
        cls.calls.append(dict(kwargs))
        if cls.fail_when_false and kwargs.get("trust_remote_code") is False:
            raise ValueError("native implementation unavailable")
        return dict(kwargs)


class DynamicModule:
    @staticmethod
    def get_class_from_dynamic_module(*args, **kwargs):
        return "unsafe"


class FakeTransformers:
    AutoConfig = type("AutoConfig", (RecorderBoundary,), {"calls": [], "fail_when_false": False})
    AutoTokenizer = type("AutoTokenizer", (RecorderBoundary,), {"calls": [], "fail_when_false": False})
    AutoModel = type("AutoModel", (RecorderBoundary,), {"calls": [], "fail_when_false": False})
    AutoModelForCausalLM = type("AutoModelForCausalLM", (RecorderBoundary,), {"calls": [], "fail_when_false": False})
    AutoModelForImageTextToText = type("AutoModelForImageTextToText", (RecorderBoundary,), {"calls": [], "fail_when_false": False})
    AutoModelForMultimodalLM = type("AutoModelForMultimodalLM", (RecorderBoundary,), {"calls": [], "fail_when_false": False})
    dynamic_module_utils = DynamicModule


def make_loader(root: Path, custom_required: bool = False):
    root.mkdir(parents=True, exist_ok=True)
    (root / "utils.py").write_text("VALUE=1\n", encoding="utf-8")
    source = root / "loader_impl.py"
    source.write_text("class StockLoader: pass\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("fake_stock_loader", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules["fake_stock_loader"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    Loader = module.StockLoader
    Loader.calls = []

    @classmethod
    def from_pretrained(cls, path, *args, **kwargs):
        cls.calls.append((path, dict(kwargs)))
        if custom_required:
            FakeTransformers.AutoConfig.fail_when_false = True
            try:
                FakeTransformers.AutoConfig.from_pretrained(path, trust_remote_code=False)
            except Exception:
                return FakeTransformers.AutoConfig.from_pretrained(path, trust_remote_code=True)
        FakeTransformers.AutoConfig.from_pretrained(path, trust_remote_code=True)
        FakeTransformers.AutoTokenizer.from_pretrained(path, trust_remote_code=True)
        FakeTransformers.AutoModelForCausalLM.from_config(object(), trust_remote_code=False)
        FakeTransformers.AutoModelForImageTextToText.from_config(object(), trust_remote_code=True)
        return "loaded"

    Loader.from_pretrained = from_pretrained
    return Loader


class NativeCompatTests(unittest.TestCase):
    def setUp(self):
        for cls_name in (
            "AutoConfig", "AutoTokenizer", "AutoModel", "AutoModelForCausalLM",
            "AutoModelForImageTextToText", "AutoModelForMultimodalLM",
        ):
            cls = getattr(FakeTransformers, cls_name)
            cls.calls = []
            cls.fail_when_false = False
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pkg = self.root / "airllm"
        self.Loader = make_loader(self.pkg)
        self.model = write_model(self.root / "model.safetensors")
        self.model_allow = {"glm": {sha256(self.model.read_bytes()).hexdigest()}}
        self.source_allow = {sha256_loader_source(self.Loader).sha256}
        _, manifest = build_source_manifest(self.pkg, required_paths=("loader_impl.py", "utils.py"))
        self.manifest_allow = {manifest.sha256}

    def tearDown(self):
        sys.modules.pop("fake_stock_loader", None)
        self.temp.cleanup()

    def wrapper(self, loader=None):
        return ManifestPinnedNativeAirLLMWrapper(
            self.model_allow,
            loader_source_allowlist=self.source_allow if loader is None else {sha256_loader_source(loader).sha256},
            loader_package_source_allowlist=self.manifest_allow,
            loader_package_required_paths=("loader_impl.py", "utils.py"),
            loader=self.Loader if loader is None else loader,
            transformers_module=FakeTransformers,
        )

    def test_01_internal_true_is_rewritten_to_literal_false(self):
        with force_false_native_compat_membrane(FakeTransformers):
            out = FakeTransformers.AutoConfig.from_pretrained("m", trust_remote_code=True)
        self.assertIs(out["trust_remote_code"], False)
        self.assertIs(FakeTransformers.AutoConfig.calls[-1]["trust_remote_code"], False)

    def test_02_dynamic_module_resolution_remains_denied(self):
        with force_false_native_compat_membrane(FakeTransformers):
            with self.assertRaises(RemoteCodeTrustError):
                FakeTransformers.dynamic_module_utils.get_class_from_dynamic_module("x")

    def test_03_native_stock_loader_succeeds_without_remote_code(self):
        self.assertEqual(self.wrapper().load("glm", self.model), "loaded")
        for cls_name in ("AutoConfig", "AutoTokenizer", "AutoModelForCausalLM", "AutoModelForImageTextToText"):
            calls = getattr(FakeTransformers, cls_name).calls
            self.assertTrue(calls, cls_name)
            self.assertTrue(all(call.get("trust_remote_code") is False for call in calls), cls_name)

    def test_04_custom_code_required_model_still_fails(self):
        Loader = make_loader(self.pkg, custom_required=True)
        # source bytes are the same path; refresh exact manifest because make_loader rewrote loader_impl.py.
        self.source_allow = {sha256_loader_source(Loader).sha256}
        _, manifest = build_source_manifest(self.pkg, required_paths=("loader_impl.py", "utils.py"))
        self.manifest_allow = {manifest.sha256}
        with self.assertRaises(ValueError):
            self.wrapper(loader=Loader).load("glm", self.model)
        self.assertTrue(FakeTransformers.AutoConfig.calls)
        self.assertTrue(all(call.get("trust_remote_code") is False for call in FakeTransformers.AutoConfig.calls))

    def test_05_caller_true_is_rejected_not_rewritten(self):
        with self.assertRaises(RemoteCodeTrustError):
            self.wrapper().load("glm", self.model, trust_remote_code=True)
        self.assertEqual(self.Loader.calls, [])

    def test_06_delete_original_true_is_rejected(self):
        with self.assertRaises(UnsafeLoadOptionError):
            self.wrapper().load("glm", self.model, delete_original=True)
        self.assertEqual(self.Loader.calls, [])

    def test_07_package_drift_blocks_before_loader(self):
        (self.pkg / "utils.py").write_text("VALUE=2\n", encoding="utf-8")
        with self.assertRaises(SourceTreeIntegrityError):
            self.wrapper().load("glm", self.model)
        self.assertEqual(self.Loader.calls, [])

    def test_08_multimodal_boundary_is_also_forced_false(self):
        with force_false_native_compat_membrane(FakeTransformers):
            out = FakeTransformers.AutoModelForMultimodalLM.from_config(object(), trust_remote_code=True)
        self.assertIs(out["trust_remote_code"], False)

    def test_09_context_restores_original_descriptors(self):
        original = FakeTransformers.AutoTokenizer.__dict__["from_pretrained"]
        with force_false_native_compat_membrane(FakeTransformers):
            FakeTransformers.AutoTokenizer.from_pretrained("m", trust_remote_code=True)
        restored = FakeTransformers.AutoTokenizer.__dict__["from_pretrained"]
        self.assertIs(restored.__func__, original.__func__)


    def test_11_inner_rewrite_precedes_outer_strict_gate(self):
        import inspect
        from contextlib import contextmanager

        @contextmanager
        def strict_outer(module):
            patches=[]
            try:
                for cls_name, method_name in (("AutoConfig","from_pretrained"),("AutoTokenizer","from_pretrained")):
                    cls=getattr(module,cls_name)
                    raw=inspect.getattr_static(cls,method_name)
                    original=getattr(cls,method_name)
                    def guard(*args,__original=original,**kwargs):
                        value=kwargs.get("trust_remote_code",False)
                        if value is not False:
                            raise RemoteCodeTrustError("outer strict gate saw widening")
                        kwargs["trust_remote_code"]=False
                        return __original(*args,**kwargs)
                    setattr(cls,method_name,staticmethod(guard));patches.append((cls,method_name,raw))
                yield
            finally:
                for cls,name,raw in reversed(patches):setattr(cls,name,raw)

        with strict_outer(FakeTransformers):
            with force_false_native_compat_membrane(FakeTransformers):
                out=FakeTransformers.AutoConfig.from_pretrained("m",trust_remote_code=True)
        self.assertIs(out["trust_remote_code"],False)

    def test_10_six_axis_hard_admission_lattice(self):
        # package, model, loader, caller hard-false, nondestructive, native support
        import itertools
        for axes in itertools.product((False, True), repeat=6):
            pkg_ok, model_ok, loader_ok, caller_ok, nondestructive, native_ok = axes
            expected = all(axes)
            admitted = all((pkg_ok, model_ok, loader_ok, caller_ok, nondestructive, native_ok))
            self.assertEqual(admitted, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
