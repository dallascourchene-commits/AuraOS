from __future__ import annotations

from pathlib import Path

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


def test_source_tree_scan_is_deterministic_and_non_mutating(
    tmp_path: Path,
) -> None:
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


def test_repository_python_sources_are_strict_utf8() -> None:
    packet = scan_utf8_source_tree(ROOT)
    assert packet["status"] == "PASSED", packet["failures"]
