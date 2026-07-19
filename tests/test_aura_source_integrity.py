from __future__ import annotations

import ast
import asyncio
from collections import defaultdict
import copy
from pathlib import Path
import subprocess
from types import SimpleNamespace
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


def test_read_utf8_source_rejects_oversize_before_unbounded_read(
    tmp_path: Path,
) -> None:
    path = tmp_path / "large.py"
    path.write_bytes(b"12345")

    with pytest.raises(SourceIntegrityError) as raised:
        read_utf8_source(path, maximum_bytes=4)

    failure = raised.value.failure
    assert failure.code == "SOURCE_FILE_TOO_LARGE"
    assert failure.file_size == 5
    assert failure.byte_offset == 4


def test_source_tree_scan_is_deterministic_digest_bound_and_non_mutating(
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
    assert len(first["source_digest"]) == 64
    assert first["source_digest_algorithm"].startswith("sha256-")
    assert (tmp_path / "bad.py").read_bytes() == before

    (tmp_path / "ok.py").write_text("value = 2\n", encoding="utf-8")
    changed = scan_utf8_source_tree(tmp_path)
    assert changed["source_digest"] != first["source_digest"]


def test_source_tree_rejects_external_file_symlink(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    external = tmp_path / "external.py"
    external.write_text("secret = True\n", encoding="utf-8")
    link = root / "linked.py"
    try:
        link.symlink_to(external)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    packet = scan_utf8_source_tree(root)

    assert packet["status"] == "FAILED"
    assert packet["checked_file_count"] == 0
    assert {item["code"] for item in packet["failures"]} == {
        "SOURCE_SYMLINK_REJECTED"
    }


def test_source_tree_enforces_file_and_total_byte_ceilings(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b = 2\n", encoding="utf-8")

    count_limited = scan_utf8_source_tree(tmp_path, maximum_files=1)
    assert count_limited["status"] == "FAILED"
    assert count_limited["checked_file_count"] == 1
    assert count_limited["limit_reached"] is True
    assert "SOURCE_FILE_COUNT_LIMIT" in {
        item["code"] for item in count_limited["failures"]
    }

    byte_limited = scan_utf8_source_tree(tmp_path, maximum_total_bytes=7)
    assert byte_limited["status"] == "FAILED"
    assert byte_limited["checked_file_count"] == 1
    assert byte_limited["limit_reached"] is True
    assert "SOURCE_TREE_BYTES_LIMIT" in {
        item["code"] for item in byte_limited["failures"]
    }


def test_source_tree_binds_clean_exact_git_head_and_rejects_dirty_tree(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "module.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "aura@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Aura Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "module.py"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "baseline"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    clean = scan_utf8_source_tree(
        repo,
        expected_repository_head=head,
        require_git_tree=True,
    )
    assert clean["status"] == "PASSED"
    assert clean["git_tree_bound"] is True
    assert clean["repository_head"] == head
    assert len(clean["repository_tree"]) == 40
    assert clean["evidence_scope"] == "git_tree_bound"

    (repo / "module.py").write_text("value = 2\n", encoding="utf-8")
    dirty = scan_utf8_source_tree(
        repo,
        expected_repository_head=head,
        require_git_tree=True,
    )
    assert dirty["status"] == "FAILED"
    assert dirty["git_tree_bound"] is False
    assert "SOURCE_GIT_TREE_UNBOUND" in {
        item["code"] for item in dirty["failures"]
    }


def test_git_binding_rejects_ignored_source_not_present_in_head(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (repo / "module.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "aura@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Aura Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", ".gitignore", "module.py"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "baseline"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (repo / "ignored.py").write_text("hidden = True\n", encoding="utf-8")

    packet = scan_utf8_source_tree(
        repo,
        expected_repository_head=head,
        require_git_tree=True,
    )

    assert packet["status"] == "FAILED"
    assert packet["git_tree_bound"] is False
    assert "SOURCE_GIT_SOURCE_SET_MISMATCH" in {
        item["code"] for item in packet["failures"]
    }


def _load_auditor_source_slice() -> type:
    module = ast.parse((ROOT / "aura_node.py").read_text(encoding="utf-8"))
    auditor_node = next(
        item
        for item in module.body
        if isinstance(item, ast.ClassDef) and item.name == "AuraEcosystemAuditor"
    )
    retained = [
        copy.deepcopy(item)
        for item in auditor_node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name in {"__init__", "_scan_and_stamp_file"}
    ]
    reduced_class = copy.deepcopy(auditor_node)
    reduced_class.body = retained
    reduced_module = ast.Module(body=[reduced_class], type_ignores=[])
    ast.fix_missing_locations(reduced_module)
    namespace = {
        "Any": Any,
        "Path": Path,
        "SourceIntegrityError": SourceIntegrityError,
        "ast": ast,
        "defaultdict": defaultdict,
        "os": __import__("os"),
        "read_utf8_source": read_utf8_source,
    }
    exec(compile(reduced_module, "aura_node.py", "exec"), namespace)
    return namespace["AuraEcosystemAuditor"]


def test_boot_auditor_records_corrupt_source_without_aborting(tmp_path: Path) -> None:
    auditor_type = _load_auditor_source_slice()
    path = tmp_path / "corrupt.py"
    path.write_bytes(b"value = '\xff'\n")
    auditor = auditor_type(SimpleNamespace())

    result = asyncio.run(auditor._scan_and_stamp_file(str(path), "root"))

    assert result is False
    assert auditor.audit_failures[0]["code"] == "SOURCE_UTF8_INVALID"
    assert path.read_bytes() == b"value = '\xff'\n"


def test_repository_python_sources_are_strict_utf8() -> None:
    packet = scan_utf8_source_tree(ROOT)
    assert packet["status"] == "PASSED", packet["failures"]
