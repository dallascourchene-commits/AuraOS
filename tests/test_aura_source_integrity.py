from __future__ import annotations

import ast
import asyncio
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from aura_source_integrity import (
    SourceIntegrityError,
    read_utf8_source,
    scan_utf8_source_tree,
)

ROOT = Path(__file__).resolve().parents[1]


def test_read_utf8_source_reports_exact_invalid_byte(tmp_path: Path) -> None:
    path = tmp_path / "broken.py"
    path.write_bytes(b"print('ok')\n\xb0broken\n")

    with pytest.raises(SourceIntegrityError) as raised:
        read_utf8_source(path)

    failure = raised.value.failure
    assert failure.code == "SOURCE_UTF8_INVALID"
    assert failure.byte_offset == 12
    assert failure.offending_bytes_hex == "b0"
    assert failure.file_size == path.stat().st_size


def test_source_tree_scan_is_deterministic_and_non_mutating(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "bad.py").write_bytes(b"value = '\xff'\n")
    before = (tmp_path / "bad.py").read_bytes()

    first = scan_utf8_source_tree(tmp_path)
    second = scan_utf8_source_tree(tmp_path)

    assert first == second
    assert first["status"] == "FAILED"
    assert first["checked_file_count"] == 2
    assert first["failure_count"] == 1
    assert first["failures"][0]["path"] == "bad.py"
    assert (tmp_path / "bad.py").read_bytes() == before


def _isolated_auditor_class() -> type:
    source = (ROOT / "aura_node.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    original = next(
        item
        for item in tree.body
        if isinstance(item, ast.ClassDef)
        and item.name == "AuraEcosystemAuditor"
    )
    retained = [
        item
        for item in original.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name in {"__init__", "_scan_and_stamp_file"}
    ]
    isolated = ast.ClassDef(
        name=original.name,
        bases=[],
        keywords=[],
        body=retained,
        decorator_list=[],
    )
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            isolated,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace: dict[str, Any] = {
        "Any": Any,
        "ast": ast,
        "defaultdict": defaultdict,
        "os": __import__("os"),
        "SourceIntegrityError": SourceIntegrityError,
        "read_utf8_source": read_utf8_source,
    }
    exec(compile(module, "<isolated-auditor>", "exec"), namespace)
    return namespace["AuraEcosystemAuditor"]


def test_boot_auditor_skips_corrupt_source_instead_of_crashing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "corrupt.py"
    path.write_bytes(b"valid = 1\n\xb0")
    auditor = _isolated_auditor_class()(None)

    result = asyncio.run(
        auditor._scan_and_stamp_file(str(path), "q-root")
    )

    assert result["ok"] is False
    assert result["status"] == "SOURCE_UTF8_INVALID"
    assert result["byte_offset"] == 10
    assert auditor.source_integrity_failures == [
        {
            "path": path.as_posix(),
            "code": "SOURCE_UTF8_INVALID",
            "message": result["message"],
            "byte_offset": 10,
            "offending_bytes_hex": "b0",
            "file_size": 11,
        }
    ]


def test_repository_python_sources_are_strict_utf8() -> None:
    packet = scan_utf8_source_tree(ROOT)
    assert packet["status"] == "PASSED", packet["failures"]
