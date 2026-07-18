from __future__ import annotations

import base64
from pathlib import Path

import tests.test_zzz_pr157_patch_materializer as materializer


def test_materialize_final_coderabbit_files(record_property) -> None:
    original_replace_once = materializer._replace_once

    def deterministic_replace(text: str, old: str, new: str, label: str) -> str:
        count = text.count(old)
        if label in {"participant metadata freeze", "participant metadata thaw"}:
            assert count == 2, f"{label}: expected two initial sites, found {count}"
            return text.replace(old, new, 1)
        return original_replace_once(text, old, new, label)

    materializer._replace_once = deterministic_replace
    try:
        module = materializer._patch_module(
            Path("aura_relational_synthesis.py").read_text(encoding="utf-8")
        )
    finally:
        materializer._replace_once = original_replace_once

    tests = materializer._patch_tests(
        Path("tests/test_aura_relational_synthesis.py").read_text(encoding="utf-8")
    )
    compile(module, "aura_relational_synthesis.py", "exec")
    compile(tests, "tests/test_aura_relational_synthesis.py", "exec")
    record_property(
        "aura_relational_synthesis_py_b64",
        base64.b64encode(module.encode()).decode(),
    )
    record_property(
        "test_aura_relational_synthesis_py_b64",
        base64.b64encode(tests.encode()).decode(),
    )
