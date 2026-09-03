import json
from pathlib import Path
import tempfile
import unittest

import airllm_fixture_scope_adjudication as s


def make_tree(root: Path, source: str) -> tuple[Path, Path]:
    path = root / s.TARGET_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = source.encode("utf-8")
    path.write_bytes(raw)
    receipt = {
        "schema": "AuraAirLLMHardFalseRemediationV1",
        "remote_code_policy": "HARD_FALSE",
        "files": [
            {
                "path": s.TARGET_PATH,
                "remediated_git_blob_sha1": s.git_blob_sha1(raw),
            }
        ],
    }
    receipt_path = root / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return root, receipt_path


def fixture(
    mapping: str = '{"trust_remote_code": False, "attn": attn}',
    middle: str = "pass",
    fallback: str = "trust_remote_code=False",
    sibling: str = "",
) -> str:
    return (
        "class AirLLMBaseModel:\n"
        "    def _instantiate_on_meta(self, attn, policy=None, other=None):\n"
        f"        kwargs = {mapping}\n"
        f"        {middle}\n"
        "        model = cls.from_config(self.config, **kwargs)\n"
        f"        model2 = cls.from_config(self.config, {fallback})\n"
        f"{sibling}\n"
    )


class ScopeAdjudicationTests(unittest.TestCase):
    def _adjudicate(self, source: str):
        with tempfile.TemporaryDirectory() as directory:
            root, receipt = make_tree(Path(directory), source)
            return s.adjudicate(root, receipt)

    def _blocked(self, source: str, code: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, receipt = make_tree(Path(directory), source)
            with self.assertRaisesRegex(s.ScopeAdjudicationError, code):
                s.adjudicate(root, receipt)

    def test_literal_hard_false_mapping_passes(self):
        self.assertEqual("FALSE", self._adjudicate(fixture()).trust_remote_code_state)

    def test_sibling_kwargs_binding_does_not_pollute_target_scope(self):
        sibling = (
            "    def sibling(self):\n"
            "        kwargs = {'trust_remote_code': True}\n"
            "        return kwargs"
        )
        self.assertEqual("PASS", self._adjudicate(fixture(sibling=sibling)).status)

    def test_true_mapping_blocks(self):
        self._blocked(fixture('{"trust_remote_code": True}'), "HARD_FALSE")

    def test_dynamic_mapping_blocks(self):
        self._blocked(fixture('{"trust_remote_code": policy}'), "HARD_FALSE")

    def test_second_mapping_assignment_blocks(self):
        self._blocked(
            fixture(middle='kwargs = {"trust_remote_code": False}'),
            "SINGLE_ASSIGNMENT",
        )

    def test_subscript_mutation_blocks(self):
        self._blocked(fixture(middle='kwargs["x"] = 1'), "SUBSCRIPT_MUTATION")

    def test_update_mutation_blocks(self):
        self._blocked(fixture(middle="kwargs.update(other)"), "METHOD_MUTATION")

    def test_fallback_without_explicit_false_blocks(self):
        self._blocked(fixture(fallback="other=True"), "FALLBACK_HARD_FALSE")

    def test_other_expansion_blocks(self):
        self._blocked(
            fixture().replace("**kwargs", "**other", 1),
            "UNBOUND_FROM_CONFIG_EXPANSION",
        )

    def test_remediated_blob_drift_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root, receipt = make_tree(Path(directory), fixture())
            path = root / s.TARGET_PATH
            path.write_text(fixture() + "# drift\n", encoding="utf-8")
            with self.assertRaisesRegex(s.ScopeAdjudicationError, "BLOB_MISMATCH"):
                s.adjudicate(root, receipt)


if __name__ == "__main__":
    unittest.main()
