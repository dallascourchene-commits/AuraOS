from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

# Local proof uses an interface-compatible base-wrapper stub; the committed test resolves
# the real sibling airllm_secure_wrapper module in the AuraOS package.
if __name__ == "__main__" or "airllm_secure_wrapper" not in sys.modules:
    here = Path(__file__).resolve().parent
    support = here / "_support_airllm_secure_wrapper.py"
    if support.exists():
        spec = importlib.util.spec_from_file_location("airllm_secure_wrapper", support)
        module = importlib.util.module_from_spec(spec)
        sys.modules["airllm_secure_wrapper"] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

from airllm_manifest_pinned_wrapper import ManifestPinnedSecureAirLLMWrapper
from airllm_source_manifest_guard import build_source_manifest, SourceTreeIntegrityError
from airllm_secure_wrapper import sha256_loader_source, RemoteCodeTrustError, UnsafeLoadOptionError


def write_model(path: Path, payload: bytes = b"m") -> Path:
    header = {
        "weight": {
            "dtype": "U8",
            "shape": [len(payload)],
            "data_offsets": [0, len(payload)],
        }
    }
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((-len(raw)) % 8)
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + payload)
    return path


class RecorderBoundary:
    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        return dict(kwargs)

    @classmethod
    def from_config(cls, *args, **kwargs):
        return dict(kwargs)


class FakeTransformers:
    AutoConfig = type("AutoConfig", (RecorderBoundary,), {})
    AutoTokenizer = type("AutoTokenizer", (RecorderBoundary,), {})
    AutoModel = type("AutoModel", (RecorderBoundary,), {})
    AutoModelForCausalLM = type("AutoModelForCausalLM", (RecorderBoundary,), {})


def make_loader_package(root: Path):
    root.mkdir(parents=True)
    (root / "utils.py").write_text("VALUE = 1\n", encoding="utf-8")
    loader_path = root / "loader_impl.py"
    loader_path.write_text(
        "from pathlib import Path\n"
        "class FakeLoader:\n"
        "    calls=[]\n"
        "    @classmethod\n"
        "    def from_pretrained(cls,path,*args,**kwargs):\n"
        "        cls.calls.append((path,dict(kwargs)))\n"
        "        return 'loaded'\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("fake_airllm_loader", loader_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["fake_airllm_loader"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.FakeLoader


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pkg = self.root / "airllm"
        self.Loader = make_loader_package(self.pkg)
        self.model = write_model(self.root / "model.safetensors", b"model")
        self.model_allow = {"glm": {sha256(self.model.read_bytes()).hexdigest()}}
        self.source_allow = {sha256_loader_source(self.Loader).sha256}
        _, manifest = build_source_manifest(
            self.pkg, required_paths=("loader_impl.py", "utils.py")
        )
        self.manifest_allow = {manifest.sha256}

    def tearDown(self):
        sys.modules.pop("fake_airllm_loader", None)
        self.temp.cleanup()

    def wrapper(self):
        return ManifestPinnedSecureAirLLMWrapper(
            self.model_allow,
            loader_source_allowlist=self.source_allow,
            loader_package_source_allowlist=self.manifest_allow,
            loader_package_required_paths=("loader_impl.py", "utils.py"),
            loader=self.Loader,
            transformers_module=FakeTransformers,
        )

    def test_01_exact_package_generation_loads(self):
        self.assertEqual(self.wrapper().load("glm", self.model), "loaded")
        self.assertEqual(len(self.Loader.calls), 1)

    def test_02_sibling_mutation_fails_even_when_loader_file_hash_is_unchanged(self):
        before = sha256_loader_source(self.Loader)
        (self.pkg / "utils.py").write_text("VALUE = 999\n", encoding="utf-8")
        after = sha256_loader_source(self.Loader)
        self.assertEqual(before, after)
        with self.assertRaises(SourceTreeIntegrityError):
            self.wrapper().load("glm", self.model)
        self.assertEqual(self.Loader.calls, [])

    def test_03_added_source_file_fails_closed(self):
        (self.pkg / "backdoor.py").write_text("OWNED=True\n", encoding="utf-8")
        with self.assertRaises(SourceTreeIntegrityError):
            self.wrapper().load("glm", self.model)

    def test_04_remote_code_widening_is_rejected_before_loader(self):
        with self.assertRaises(RemoteCodeTrustError):
            self.wrapper().load("glm", self.model, trust_remote_code=True)
        self.assertEqual(self.Loader.calls, [])

    def test_05_destructive_option_is_rejected_before_loader(self):
        with self.assertRaises(UnsafeLoadOptionError):
            self.wrapper().load("glm", self.model, delete_original=True)
        self.assertEqual(self.Loader.calls, [])

    def test_06_manifest_allowlist_is_required(self):
        with self.assertRaises(Exception):
            ManifestPinnedSecureAirLLMWrapper(
                self.model_allow,
                loader_source_allowlist=self.source_allow,
                loader_package_source_allowlist=None,
                loader_package_required_paths=("loader_impl.py", "utils.py"),
                loader=self.Loader,
                transformers_module=FakeTransformers,
            )

    def test_07_model_drift_still_fails_closed(self):
        write_model(self.model, b"changed")
        with self.assertRaises(Exception):
            self.wrapper().load("glm", self.model)

    def test_08_manifest_root_is_bound_to_loader_source_parent(self):
        clean = self.root / "clean"
        clean.mkdir()
        (clean / "loader_impl.py").write_text("# clean\n", encoding="utf-8")
        (clean / "utils.py").write_text("VALUE=1\n", encoding="utf-8")
        _, clean_manifest = build_source_manifest(
            clean, required_paths=("loader_impl.py", "utils.py")
        )
        wrapped = ManifestPinnedSecureAirLLMWrapper(
            self.model_allow,
            loader_source_allowlist=self.source_allow,
            loader_package_source_allowlist={clean_manifest.sha256},
            loader_package_required_paths=("loader_impl.py", "utils.py"),
            loader=self.Loader,
            transformers_module=FakeTransformers,
        )
        with self.assertRaises(SourceTreeIntegrityError):
            wrapped.load("glm", self.model)


if __name__ == "__main__":
    unittest.main(verbosity=2)
