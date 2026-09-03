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
    def _codes(self, auto: str) -> set[str]:
        with tempfile.TemporaryDirectory() as d:
            make_tree(Path(d), auto=auto)
            return {f.code for f in a.audit_airllm_source(d).findings}

    def test_hard_false_source_passes(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(Path(d))
            r = a.audit_airllm_source(d)
            self.assertEqual("PASS", r.status)
            self.assertEqual("3.3.0", r.observed_version)
            self.assertEqual([], list(r.findings))

    def test_explicit_true_blocks(self):
        self.assertIn(
            "REMOTE_CODE_TRUE",
            self._codes("def load(f):\n    return f(trust_remote_code=True)\n"),
        )

    def test_dynamic_policy_blocks(self):
        self.assertIn(
            "REMOTE_CODE_DYNAMIC",
            self._codes("def load(f, trust):\n    return f(trust_remote_code=trust)\n"),
        )

    def test_mapping_true_blocks(self):
        self.assertIn(
            "REMOTE_CODE_TRUE",
            self._codes(
                "def load(f):\n"
                "    opts = {'trust_remote_code': True}\n"
                "    return f(**opts)\n"
            ),
        )

    def test_mapping_dynamic_blocks(self):
        self.assertIn(
            "REMOTE_CODE_DYNAMIC",
            self._codes(
                "def load(f, trust):\n"
                "    opts = {'trust_remote_code': trust}\n"
                "    return f(**opts)\n"
            ),
        )

    def test_subscript_assignment_true_blocks(self):
        self.assertIn(
            "REMOTE_CODE_TRUE",
            self._codes(
                "def load(f):\n"
                "    opts = {}\n"
                "    opts['trust_remote_code'] = True\n"
                "    return f(**opts)\n"
            ),
        )

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
            self.assertIn("SOURCE_SYMLINK_FORBIDDEN", {f.code for f in r.findings})

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

    def test_computed_mapping_key_blocks(self):
        self.assertIn(
            "REMOTE_CODE_TRUE",
            self._codes(
                "KEY = 'trust_' + 'remote_code'\n"
                "def load(f):\n"
                "    opts = {KEY: True}\n"
                "    return f(**opts)\n"
            ),
        )

    def test_computed_subscript_key_blocks(self):
        self.assertIn(
            "REMOTE_CODE_TRUE",
            self._codes(
                "KEY = f\"trust_{'remote_code'}\"\n"
                "def load(f):\n"
                "    opts = {}\n"
                "    opts[KEY] = True\n"
                "    return f(**opts)\n"
            ),
        )

    def test_attribute_assignment_blocks(self):
        self.assertIn(
            "REMOTE_CODE_TRUE",
            self._codes(
                "def load(obj):\n"
                "    obj.trust_remote_code = True\n"
                "    return obj\n"
            ),
        )

    def test_setattr_blocks(self):
        self.assertIn(
            "REMOTE_CODE_DYNAMIC",
            self._codes(
                "def load(obj, value):\n"
                "    setattr(obj, 'trust_remote_code', value)\n"
                "    return obj\n"
            ),
        )

    def test_setdefault_blocks(self):
        self.assertIn(
            "REMOTE_CODE_TRUE",
            self._codes(
                "def load(opts):\n"
                "    opts.setdefault('trust_remote_code', True)\n"
                "    return opts\n"
            ),
        )

    def test_loader_opaque_kwargs_fail_closed(self):
        self.assertIn(
            "REMOTE_CODE_OPAQUE_LOADER_KWARGS",
            self._codes(
                "def load(model, opts):\n"
                "    return model.from_pretrained('x', **opts)\n"
            ),
        )

    def test_loader_explicit_false_with_opaque_kwargs_passes(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto=(
                    "def load(model, opts):\n"
                    "    return model.from_pretrained('x', trust_remote_code=False, **opts)\n"
                ),
            )
            self.assertEqual("PASS", a.audit_airllm_source(d).status)

    def test_loader_static_unrelated_mapping_passes(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto=(
                    "def load(model):\n"
                    "    opts = {'revision': 'abc'}\n"
                    "    return model.from_pretrained('x', **opts)\n"
                ),
            )
            self.assertEqual("PASS", a.audit_airllm_source(d).status)

    def test_loader_conflicting_computed_key_assignments_fail_closed(self):
        self.assertIn(
            "REMOTE_CODE_OPAQUE_LOADER_KWARGS",
            self._codes(
                "KEY = 'trust_remote_code'\n"
                "if feature_flag:\n"
                "    KEY = 'revision'\n"
                "opts = {KEY: True}\n"
                "def load(model):\n"
                "    return model.from_pretrained('x', **opts)\n"
            ),
        )

    def test_loader_identical_computed_key_rebinding_remains_foldable(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto=(
                    "KEY = 'revision'\n"
                    "if feature_flag:\n"
                    "    KEY = 'revision'\n"
                    "opts = {KEY: True}\n"
                    "def load(model):\n"
                    "    return model.from_pretrained('x', **opts)\n"
                ),
            )
            self.assertEqual("PASS", a.audit_airllm_source(d).status)

    def test_dict_constructor_pair_blocks(self):
        self.assertIn(
            "REMOTE_CODE_TRUE",
            self._codes(
                "def load(model):\n"
                "    opts = dict([('trust_remote_code', True)])\n"
                "    return model.from_pretrained('x', **opts)\n"
            ),
        )

    def test_generic_opaque_kwargs_not_globally_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d), auto="def load(f, opts):\n    return f(**opts)\n"
            )
            self.assertEqual("PASS", a.audit_airllm_source(d).status)

    def test_loader_dynamic_subscript_mutation_blocks(self):
        self.assertIn(
            "REMOTE_CODE_OPAQUE_LOADER_KWARGS",
            self._codes(
                "def load(model, key):\n"
                "    opts = {}\n"
                "    opts[key] = True\n"
                "    return model.from_pretrained('x', **opts)\n"
            ),
        )

    def test_loader_dynamic_update_mutation_blocks(self):
        self.assertIn(
            "REMOTE_CODE_OPAQUE_LOADER_KWARGS",
            self._codes(
                "def load(model, key):\n"
                "    opts = {}\n"
                "    opts.update({key: True})\n"
                "    return model.from_config(object(), **opts)\n"
            ),
        )

    def test_loader_alias_dynamic_mutation_blocks(self):
        self.assertIn(
            "REMOTE_CODE_OPAQUE_LOADER_KWARGS",
            self._codes(
                "def load(model, key):\n"
                "    opts = {}\n"
                "    alias = opts\n"
                "    alias[key] = True\n"
                "    return model.from_pretrained('x', **opts)\n"
            ),
        )

    def test_loader_dynamic_merge_mutation_blocks(self):
        self.assertIn(
            "REMOTE_CODE_OPAQUE_LOADER_KWARGS",
            self._codes(
                "def load(model, key):\n"
                "    opts = {}\n"
                "    opts |= {key: True}\n"
                "    return model.from_pretrained('x', **opts)\n"
            ),
        )

    def test_loader_explicit_false_dominates_dynamic_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto=(
                    "def load(model, key):\n"
                    "    opts = {}\n"
                    "    opts[key] = True\n"
                    "    return model.from_pretrained(\n"
                    "        'x', trust_remote_code=False, **opts\n"
                    "    )\n"
                ),
            )
            self.assertEqual("PASS", a.audit_airllm_source(d).status)

    def test_generic_dynamic_mutation_not_globally_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            make_tree(
                Path(d),
                auto=(
                    "def load(f, key):\n"
                    "    opts = {}\n"
                    "    opts[key] = True\n"
                    "    return f(**opts)\n"
                ),
            )
            self.assertEqual("PASS", a.audit_airllm_source(d).status)


if __name__ == "__main__":
    unittest.main()
