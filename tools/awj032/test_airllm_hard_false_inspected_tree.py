import unittest

import airllm_hard_false_inspected_tree as tree
from airllm_hard_false_remediation import RemediationError, git_blob_sha1


def make_files(*, nonremote: bool = False) -> dict[str, bytes]:
    setup_extra = b"import os\nos.system('pip install evil')\n" if nonremote else b""
    return {
        "air_llm/setup.py": (
            b"from setuptools import setup\n"
            b"setup(name='airllm', version='3.3.0')\n"
            + setup_extra
        ),
        "air_llm/airllm/auto_model.py": (
            b"def load(model):\n"
            b"    return model.from_pretrained('x', trust_remote_code=True)\n"
        ),
        "air_llm/airllm/airllm_base.py": (
            b"def load(model):\n"
            b"    self.trust_remote_code = True\n"
            b"    return model.from_pretrained('x', trust_remote_code=self.trust_remote_code)\n"
        ),
        "air_llm/airllm/airllm_baichuan.py": (
            b"def load(tok):\n"
            b"    return tok.from_pretrained('x', trust_remote_code=True)\n"
        ),
        "air_llm/airllm/airllm_llama_mlx.py": (
            b"def load(model):\n"
            b"    return model.from_pretrained('x', trust_remote_code=True)\n"
        ),
        "air_llm/airllm/unchanged.py": b"def x():\n    return 1\n",
    }


def manifest(files: dict[str, bytes]) -> dict[str, str]:
    return {path: git_blob_sha1(raw) for path, raw in files.items()}


def specs(files: dict[str, bytes]) -> dict[str, tuple[str, int]]:
    return {
        "air_llm/airllm/auto_model.py": (
            git_blob_sha1(files["air_llm/airllm/auto_model.py"]),
            1,
        ),
        "air_llm/airllm/airllm_base.py": (
            git_blob_sha1(files["air_llm/airllm/airllm_base.py"]),
            2,
        ),
        "air_llm/airllm/airllm_baichuan.py": (
            git_blob_sha1(files["air_llm/airllm/airllm_baichuan.py"]),
            1,
        ),
        "air_llm/airllm/airllm_llama_mlx.py": (
            git_blob_sha1(files["air_llm/airllm/airllm_llama_mlx.py"]),
            1,
        ),
    }


class InspectedTreeTests(unittest.TestCase):
    def _run(self, files: dict[str, bytes]):
        return tree._remediate_inspected_tree(
            files,
            expected_manifest=manifest(files),
            mutation_specs=specs(files),
            upstream_commit="synthetic",
            package_tree="synthetic",
        )

    def test_full_manifest_candidate_passes_existing_gate(self):
        files = make_files()
        outputs, receipt = self._run(files)
        self.assertEqual("PASS_SOURCE_CANDIDATE", receipt.status)
        self.assertEqual("BLOCKED", receipt.input_gate_status)
        self.assertEqual("PASS", receipt.output_gate_status)
        self.assertTrue(receipt.full_gate_consumed_manifest_exact)
        self.assertEqual("FULL_PR311_GATE_CONSUMED_TREE", receipt.source_identity_scope)
        self.assertFalse(receipt.g2_admitted)
        self.assertFalse(receipt.model_executed)
        self.assertEqual(6, receipt.inspected_file_count)
        self.assertNotEqual(receipt.input_manifest_digest, receipt.output_manifest_digest)
        self.assertEqual(
            files["air_llm/airllm/unchanged.py"],
            outputs["air_llm/airllm/unchanged.py"],
        )

    def test_missing_unaffected_file_refuses_commit_identity(self):
        files = make_files()
        expected = manifest(files)
        files.pop("air_llm/airllm/unchanged.py")
        with self.assertRaisesRegex(
            RemediationError, "PINNED_INSPECTED_SOURCE_SET_MISMATCH"
        ):
            tree._remediate_inspected_tree(
                files,
                expected_manifest=expected,
                mutation_specs=specs(make_files()),
                upstream_commit="synthetic",
                package_tree="synthetic",
            )

    def test_extra_file_refuses_commit_identity(self):
        files = make_files()
        expected = manifest(files)
        files["air_llm/airllm/injected.py"] = b"def injected():\n    return 1\n"
        with self.assertRaisesRegex(
            RemediationError, "PINNED_INSPECTED_SOURCE_SET_MISMATCH"
        ):
            tree._remediate_inspected_tree(
                files,
                expected_manifest=expected,
                mutation_specs=specs(make_files()),
                upstream_commit="synthetic",
                package_tree="synthetic",
            )

    def test_unaffected_blob_drift_refuses(self):
        files = make_files()
        expected = manifest(files)
        files["air_llm/airllm/unchanged.py"] = b"def x():\n    return 2\n"
        with self.assertRaisesRegex(
            RemediationError, "PINNED_INSPECTED_SOURCE_BLOB_MISMATCH"
        ):
            tree._remediate_inspected_tree(
                files,
                expected_manifest=expected,
                mutation_specs=specs(make_files()),
                upstream_commit="synthetic",
                package_tree="synthetic",
            )

    def test_nonremote_blocker_is_not_repaired(self):
        files = make_files(nonremote=True)
        with self.assertRaisesRegex(
            RemediationError, "PINNED_INSPECTED_TREE_NONREMOTE_BLOCKER"
        ):
            self._run(files)

    def test_change_set_is_exactly_mutation_specs(self):
        files = make_files()
        outputs, receipt = self._run(files)
        self.assertEqual(set(specs(files)), set(receipt.changed_files))
        for path in files:
            if path not in specs(files):
                self.assertEqual(files[path], outputs[path])

    def test_post_audit_is_authoritative(self):
        files = make_files()
        bad_specs = specs(files)
        bad_specs.pop("air_llm/airllm/airllm_baichuan.py")
        with self.assertRaisesRegex(
            RemediationError, "REMEDIATED_INSPECTED_TREE_POST_AUDIT_BLOCKED"
        ):
            tree._remediate_inspected_tree(
                files,
                expected_manifest=manifest(files),
                mutation_specs=bad_specs,
                upstream_commit="synthetic",
                package_tree="synthetic",
            )


if __name__ == "__main__":
    unittest.main()
