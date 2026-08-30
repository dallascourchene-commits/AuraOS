import tempfile
from pathlib import Path
import unittest

import airllm_source_admission as a


def make_tree(
    root: Path, *, auto: str = "", setup_extra: str = "", version: str = "3.3.0"
):
    pkg = root / "air_llm" / "airllm"
    pkg.mkdir(parents=True)
    (root / "air_llm" / "setup.py").write_text(
        f"from setuptools import setup\nsetup(name='airllm', version='{version}')\n{setup_extra}",
        encoding="utf-8",
    )
    (pkg / "auto_model.py").write_text(
        auto or "def load(f):\n    return f(trust_remote_code=False)\n",
        encoding="utf-8",
    )
    (pkg / "base.py").write_text("def x():\n    return 1\n", encoding="utf-8")


class GateTests(unittest.TestCase):
    def test_hard_false_source_passes(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(Path(d))
            r = a.audit_airllm_source(d)
            self.assertEqual("PASS", r.status)
            self.assertEqual("3.3.0", r.observed_version)
            self.assertEqual([], list(r.findings))

    def test_explicit_true_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d), auto="def load(f):\n    return f(trust_remote_code=True)\n"
            )
            r = a.audit_airllm_source(d)
            self.assertEqual("BLOCKED", r.status)
            self.assertIn("REMOTE_CODE_TRUE", {f.code for f in r.findings})

    def test_dynamic_policy_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto="def load(f, trust):\n    return f(trust_remote_code=trust)\n",
            )
            r = a.audit_airllm_source(d)
            self.assertIn("REMOTE_CODE_DYNAMIC", {f.code for f in r.findings})

    def test_mapping_true_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto=(
                    "def load(f):\n"
                    "    opts = {'trust_remote_code': True}\n"
                    "    return f(**opts)\n"
                ),
            )
            r = a.audit_airllm_source(d)
            self.assertIn("REMOTE_CODE_TRUE", {f.code for f in r.findings})

    def test_mapping_dynamic_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto=(
                    "def load(f, trust):\n"
                    "    opts = {'trust_remote_code': trust}\n"
                    "    return f(**opts)\n"
                ),
            )
            r = a.audit_airllm_source(d)
            self.assertIn("REMOTE_CODE_DYNAMIC", {f.code for f in r.findings})

    def test_subscript_assignment_true_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto=(
                    "def load(f):\n"
                    "    opts = {}\n"
                    "    opts['trust_remote_code'] = True\n"
                    "    return f(**opts)\n"
                ),
            )
            r = a.audit_airllm_source(d)
            self.assertIn("REMOTE_CODE_TRUE", {f.code for f in r.findings})

    def test_version_drift_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(Path(d), version="3.4.0")
            r = a.audit_airllm_source(d)
            self.assertIn("VERSION_MISMATCH", {f.code for f in r.findings})

    def test_nested_pip_mutation_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                setup_extra="import os\nos.system('pip install -U transformers')\n",
            )
            r = a.audit_airllm_source(d)
            self.assertIn("NESTED_PIP_MUTATION", {f.code for f in r.findings})

    def test_symlinked_source_blocks(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as ext:
            root = Path(d)
            make_tree(root)
            external = Path(ext) / "outside.py"
            external.write_text("def x():\n    return 1\n", encoding="utf-8")
            link = root / "air_llm" / "airllm" / "linked.py"
            try:
                link.symlink_to(external)
            except OSError as exc:
                self.skipTest(f"symlink unsupported in test environment: {exc}")
            r = a.audit_airllm_source(root)
            self.assertIn(
                "SOURCE_SYMLINK_FORBIDDEN", {f.code for f in r.findings}
            )

    def test_digest_changes_with_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_tree(root)
            r1 = a.audit_airllm_source(root)
            (root / "air_llm" / "airllm" / "base.py").write_text(
                "def x():\n    return 2\n", encoding="utf-8"
            )
            r2 = a.audit_airllm_source(root)
            self.assertNotEqual(r1.source_digest, r2.source_digest)

    def test_require_admitted_raises_typed_prefix(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d), auto="def load(f):\n    return f(trust_remote_code=True)\n"
            )
            with self.assertRaisesRegex(
                RuntimeError, "AIRLLM_BLOCKED_DEPENDENCY_SECURITY"
            ):
                a.require_admitted(d)

    def test_missing_root_fails_closed(self):
        r = a.audit_airllm_source("/definitely/not/a/source")
        self.assertEqual("BLOCKED", r.status)
        self.assertEqual("SOURCE_ROOT_MISSING", r.findings[0].code)


if __name__ == "__main__":
    unittest.main()
