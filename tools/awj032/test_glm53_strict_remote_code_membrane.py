import importlib.util
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).with_name("glm53_strict_remote_code_membrane.py")
SPEC = importlib.util.spec_from_file_location("glm53_strict_remote_code_membrane", PATH)
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
assert SPEC.loader is not None
SPEC.loader.exec_module(m)


class StrictRemoteCodeMembraneTests(unittest.TestCase):
    def codes(self, src):
        return {item.code for item in m.scan_source("x.py", src)}

    def test_explicit_false_only_is_hard_false(self):
        src = (
            "x = AutoConfig.from_pretrained(path, trust_remote_code=False)\n"
            "y = AutoTokenizer.from_pretrained(path, trust_remote_code=False)"
        )
        self.assertTrue(m.hard_false_proven([("x.py", src)]))
        self.assertEqual((), m.scan_source("x.py", src))

    def test_literal_true_blocks(self):
        self.assertIn(
            "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
            self.codes("x=F.from_pretrained(p, trust_remote_code=True)"),
        )

    def test_variable_blocks(self):
        self.assertIn(
            "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
            self.codes("x=F.from_pretrained(p, trust_remote_code=flag)"),
        )

    def test_expression_blocks(self):
        self.assertIn(
            "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
            self.codes("x=F.from_pretrained(p, trust_remote_code=not safe)"),
        )

    def test_omitted_keyword_blocks(self):
        self.assertIn(
            "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
            self.codes("x=F.from_pretrained(p)"),
        )

    def test_kwargs_blocks(self):
        self.assertIn(
            "AIRLLM_REMOTE_CODE_SECURITY_BLOCK",
            self.codes("x=F.from_pretrained(p, **kwargs)"),
        )

    def test_parse_failure_blocks(self):
        self.assertIn("AIRLLM_REMOTE_CODE_SECURITY_BLOCK", self.codes("def broken(:"))

    def test_no_relevant_call_is_unproven_not_safe(self):
        self.assertIn("AIRLLM_REMOTE_CODE_POLICY_UNPROVEN", self.codes("x = 1"))
        self.assertFalse(m.hard_false_proven([("x.py", "x=1")]))


if __name__ == "__main__":
    unittest.main()
