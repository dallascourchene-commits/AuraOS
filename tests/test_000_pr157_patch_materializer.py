from __future__ import annotations

import base64
from pathlib import Path

from tests.test_zzz_pr157_patch_materializer import _patch_module, _patch_tests


def test_materialize_final_coderabbit_files(record_property) -> None:
    module = _patch_module(
        Path("aura_relational_synthesis.py").read_text(encoding="utf-8")
    )
    tests = _patch_tests(
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
