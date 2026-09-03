import ast
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).parent


def load(name):
    path = ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


r = load("airllm_hard_false_remediation")
gate = load("airllm_source_admission")


class HardFalseRemediationTests(unittest.TestCase):
    def remediate(self, source: str, edits: int):
        raw = source.encode("utf-8")
        return r.remediate_bytes(
            path="air_llm/airllm/example.py",
            raw=raw,
            expected_git_blob_sha1=r.git_blob_sha1(raw),
            expected_edit_count=edits,
        )

    def assert_gate_clean(self, raw: bytes):
        tree = ast.parse(raw.decode("utf-8"))
        findings = gate._scan_trust_remote_code(tree, "air_llm/airllm/example.py")
        self.assertEqual([], findings)

    def test_pinned_production_spec_is_exact_and_totals_thirteen_edits(self):
        self.assertEqual(
            "c92cea691412715a218306acb01fc9c2c681a8f2",
            r.PINNED_UPSTREAM_COMMIT,
        )
        self.assertEqual(
            "bc02aa8f4600c8d34fea4d50c31a79b5bb3497e4",
            r.PINNED_PACKAGE_TREE,
        )
        self.assertEqual(
            {
                "air_llm/airllm/auto_model.py": (
                    "f6608dfdf3edfca5dc827f2a312524e776204d24",
                    2,
                ),
                "air_llm/airllm/airllm_base.py": (
                    "8da7ab91c6f0436054f13d885975fa6eb02ad605",
                    6,
                ),
                "air_llm/airllm/airllm_baichuan.py": (
                    "a151b18b5eca51e72733c895702fd2b75dadecf0",
                    1,
                ),
                "air_llm/airllm/airllm_llama_mlx.py": (
                    "e47a0bd493c693a115f8012fc9ba90209125872f",
                    4,
                ),
            },
            r.PINNED_MUTATION_SPECS,
        )
        self.assertEqual(13, sum(v[1] for v in r.PINNED_MUTATION_SPECS.values()))

    def test_true_dynamic_mapping_and_assignment_forms_become_hard_false(self):
        source = '''\
def load(loader, policy):
    self.trust_remote_code = True
    opts = {"trust_remote_code": policy}
    opts.setdefault("trust_remote_code", True)
    setattr(self, "trust_remote_code", policy)
    return loader.from_pretrained("x", trust_remote_code=policy)
'''
        out, receipt = self.remediate(source, 5)
        self.assertEqual(5, receipt.edit_count)
        self.assertEqual(5, out.count(b"False"))
        self.assert_gate_clean(out)

    def test_dynamic_factory_mapping_and_direct_keyword_are_closed(self):
        source = '''\
def build(cls, config):
    self.trust_remote_code = False
    kwargs = {"attn_implementation": "eager", "trust_remote_code": self.trust_remote_code}
    a = cls.from_config(config, **kwargs)
    b = cls.from_config(config, trust_remote_code=self.trust_remote_code)
    return a, b
'''
        out, receipt = self.remediate(source, 2)
        self.assertEqual(2, receipt.edit_count)
        self.assertIn(b'"trust_remote_code": False', out)
        self.assertIn(b"trust_remote_code=False", out)
        self.assert_gate_clean(out)

    def test_only_expression_bytes_change_and_comment_survives(self):
        source = '''\
# preserve this exact comment
def load(f):
    return f(trust_remote_code=True, token="abc")
'''
        out, _ = self.remediate(source, 1)
        self.assertIn(b"# preserve this exact comment", out)
        self.assertIn(b'token="abc"', out)
        self.assertIn(b"trust_remote_code=False", out)
        self.assert_gate_clean(out)

    def test_blob_drift_fails_before_transformation(self):
        raw = b"def x():\n    return 1\n"
        with self.assertRaises(r.RemediationError) as ctx:
            r.remediate_bytes(
                path="x.py",
                raw=raw,
                expected_git_blob_sha1="0" * 40,
                expected_edit_count=0,
            )
        self.assertEqual("PINNED_SOURCE_BLOB_MISMATCH", ctx.exception.code)

    def test_edit_count_drift_fails_closed(self):
        source = "def load(f):\n    return f(trust_remote_code=True)\n"
        raw = source.encode("utf-8")
        with self.assertRaises(r.RemediationError) as ctx:
            r.remediate_bytes(
                path="x.py",
                raw=raw,
                expected_git_blob_sha1=r.git_blob_sha1(raw),
                expected_edit_count=2,
            )
        self.assertEqual("PINNED_REMEDIATION_EDIT_COUNT_MISMATCH", ctx.exception.code)

    def test_opaque_loader_kwargs_are_not_laundered_by_transformer(self):
        source = '''\
def load(loader, opaque):
    return loader.from_pretrained("x", **opaque)
'''
        out, receipt = self.remediate(source, 0)
        self.assertEqual(0, receipt.edit_count)
        findings = gate._scan_trust_remote_code(
            ast.parse(out.decode("utf-8")), "air_llm/airllm/example.py"
        )
        self.assertIn(
            "REMOTE_CODE_OPAQUE_LOADER_KWARGS", {finding.code for finding in findings}
        )

    def test_missing_production_file_fails_closed(self):
        with self.assertRaises(r.RemediationError) as ctx:
            r.remediate_pinned_policy_files({})
        self.assertEqual("PINNED_MUTATION_FILE_MISSING", ctx.exception.code)

    def test_git_blob_identity_matches_git_object_encoding(self):
        self.assertEqual(
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
            r.git_blob_sha1(b""),
        )


if __name__ == "__main__":
    unittest.main()
