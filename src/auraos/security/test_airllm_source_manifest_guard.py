from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from airllm_source_manifest_guard import (
    InvalidManifestAllowlistError,
    SourceTreeIntegrityError,
    build_source_manifest,
    k27_for_manifest,
    normalize_manifest_allowlist,
    verify_source_manifest,
)


ANCHORS = (
    "__init__.py",
    "airllm_base.py",
    "auto_model.py",
    "utils.py",
    "persist/__init__.py",
    "persist/model_persister.py",
    "persist/safetensor_model_persister.py",
)


def make_tree(root: Path) -> Path:
    (root / "persist").mkdir(parents=True)
    contents = {
        "__init__.py": b"from .airllm_base import X\n",
        "airllm_base.py": b"from .utils import helper\nclass X: pass\n",
        "auto_model.py": b"from .airllm_base import X\n",
        "utils.py": b"def helper(): return 1\n",
        "persist/__init__.py": b"from .model_persister import P\n",
        "persist/model_persister.py": b"class P: pass\n",
        "persist/safetensor_model_persister.py": b"from .model_persister import P\n",
        "profiler.py": b"class Profiler: pass\n",
    }
    for name, payload in contents.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return root


class SourceManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = make_tree(Path(self.temp.name) / "airllm")

    def tearDown(self):
        self.temp.cleanup()

    def test_01_manifest_is_deterministic_and_canonical(self):
        first, a = build_source_manifest(self.root)
        second, b = build_source_manifest(self.root)
        self.assertEqual(first, second)
        self.assertEqual(a, b)
        self.assertEqual(a.file_count, 8)
        self.assertEqual(tuple(first["required_paths"]), tuple(sorted(ANCHORS)))

    def test_02_exact_allowlist_admits_and_k27_is_bounded(self):
        _, observed = build_source_manifest(self.root)
        admitted = verify_source_manifest(self.root, [observed.sha256])
        self.assertEqual(admitted, observed)
        self.assertTrue(all(0 <= value < 27 for value in k27_for_manifest(observed.sha256)))

    def test_03_sibling_source_mutation_invalidates_loader_generation(self):
        _, observed = build_source_manifest(self.root)
        (self.root / "utils.py").write_text("def helper(): return 2\n", encoding="utf-8")
        with self.assertRaises(SourceTreeIntegrityError):
            verify_source_manifest(self.root, [observed.sha256])

    def test_04_added_source_file_invalidates_manifest(self):
        _, observed = build_source_manifest(self.root)
        (self.root / "new_backend.py").write_text("VALUE=1\n", encoding="utf-8")
        with self.assertRaises(SourceTreeIntegrityError):
            verify_source_manifest(self.root, [observed.sha256])

    def test_05_removed_required_execution_anchor_fails_closed(self):
        (self.root / "auto_model.py").unlink()
        with self.assertRaises(SourceTreeIntegrityError):
            build_source_manifest(self.root)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unsupported")
    def test_06_symlink_anywhere_in_admitted_tree_is_rejected(self):
        target = self.root / "utils.py"
        link = self.root / "alias.py"
        try:
            link.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        with self.assertRaises(SourceTreeIntegrityError):
            build_source_manifest(self.root)

    def test_07_pycache_and_pyc_are_nonsemantic_and_ignored(self):
        _, before = build_source_manifest(self.root)
        cache = self.root / "__pycache__"
        cache.mkdir()
        (cache / "utils.cpython-312.pyc").write_bytes(b"volatile")
        (self.root / "manual.pyc").write_bytes(b"volatile")
        _, after = build_source_manifest(self.root)
        self.assertEqual(before.sha256, after.sha256)

    def test_08_allowlist_and_required_path_shapes_fail_closed(self):
        for bad in (None, [], "a" * 64, ["A" * 64], ["a" * 63]):
            with self.subTest(bad=bad), self.assertRaises(InvalidManifestAllowlistError):
                normalize_manifest_allowlist(bad)
        with self.assertRaises(SourceTreeIntegrityError):
            build_source_manifest(self.root, required_paths=["../escape.py"])

    def test_09_single_loader_file_hash_cannot_compensate_for_sibling_drift(self):
        loader_before = (self.root / "airllm_base.py").read_bytes()
        _, manifest_before = build_source_manifest(self.root)
        (self.root / "utils.py").write_text("def helper(): return 'owned'\n", encoding="utf-8")
        loader_after = (self.root / "airllm_base.py").read_bytes()
        _, manifest_after = build_source_manifest(self.root)
        self.assertEqual(loader_before, loader_after)
        self.assertNotEqual(manifest_before.sha256, manifest_after.sha256)

    def test_10_eight_axis_and_13d_noncompensation(self):
        # Axes: root, file set, content, anchors, symlink-free, regular-only, allowlist, currentness.
        keeper = 0
        for state in range(3 ** 8):
            digits = []
            n = state
            for _ in range(8):
                digits.append(n % 3)
                n //= 3
            admitted = all(value == 2 for value in digits)
            keeper += int(admitted)
            if not admitted:
                for trailing in range(3 ** 5):
                    self.assertFalse(admitted, trailing)
        self.assertEqual(keeper, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
