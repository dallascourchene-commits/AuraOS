from __future__ import annotations

import json
from pathlib import Path
import subprocess
import zipfile

import pytest

from scripts.aura_exact_head_transport import (
    assert_exact_clean_head,
    build_atomic_publication_bundle,
    export_exact_head,
    materialize_exact_head,
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Transport Test")
    _git(root, "config", "user.email", "transport@local.invalid")
    (root / "source.py").write_text("value = 1\n", encoding="utf-8")
    (root / "untouched.txt").write_text("stable\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "fixture")
    return root, _git(root, "rev-parse", "HEAD")


def test_export_keeps_clean_checkout_clean_and_external(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    output = tmp_path / "export"
    result = export_exact_head(root, expected_head=head, output_dir=output, diagnostics_dir=tmp_path / "diag")
    assert result["final_clean"] is True
    assert _git(root, "status", "--porcelain=v1", "--untracked-files=all") == ""
    assert not any(path.name.startswith("AuraOS-full") for path in root.rglob("*"))
    with zipfile.ZipFile(output / "AuraOS-full-repository.zip") as archive:
        assert archive.read("AuraOS/source.py") == b"value = 1\n"


def test_dirty_checkout_fails_closed_with_external_paths(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    (root / "source.py").write_text("dirty = True\n", encoding="utf-8")
    diagnostics = tmp_path / "diag"
    with pytest.raises(RuntimeError, match="source.py"):
        assert_exact_clean_head(root, expected_head=head, diagnostics_dir=diagnostics)
    receipt = json.loads((diagnostics / "exact_head_failure.json").read_text())
    assert receipt["dirty_paths"] == ["source.py"]
    assert not (root / "exact_head_failure.json").exists()


def test_materialization_never_adds_checkout_status_entries(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    destination = tmp_path / "materialized"
    materialize_exact_head(root, expected_head=head, destination=destination, diagnostics_dir=tmp_path / "diag")
    assert (destination / "source.py").read_text() == "value = 1\n"
    assert _git(root, "status", "--porcelain=v1", "--untracked-files=all") == ""


def test_bundle_uses_verified_final_whole_file_bytes(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    candidate = tmp_path / "candidate"
    materialize_exact_head(root, expected_head=head, destination=candidate, diagnostics_dir=tmp_path / "diag")
    (candidate / "source.py").write_text("value = (\n    2\n)\n", encoding="utf-8")
    output = tmp_path / "bundle.json"
    bundle = build_atomic_publication_bundle(root, expected_head=head, candidate_root=candidate, allowed_paths=["source.py"], output_path=output, diagnostics_dir=tmp_path / "diag")
    assert bundle["changed_paths"] == ["source.py"]
    assert bundle["partial_publication_allowed"] is False
    assert bundle["formatting_drift_policy"] == "publish_verified_final_whole_file_bytes"
    assert output.is_file()


def test_failed_scope_validation_publishes_nothing(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    candidate = tmp_path / "candidate"
    materialize_exact_head(root, expected_head=head, destination=candidate, diagnostics_dir=tmp_path / "diag")
    (candidate / "source.py").write_text("value = 2\n", encoding="utf-8")
    (candidate / "untouched.txt").write_text("unexpected\n", encoding="utf-8")
    output = tmp_path / "bundle.json"
    with pytest.raises(RuntimeError, match="out-of-scope modification"):
        build_atomic_publication_bundle(root, expected_head=head, candidate_root=candidate, allowed_paths=["source.py"], output_path=output, diagnostics_dir=tmp_path / "diag")
    assert not output.exists()


def test_output_inside_checkout_is_rejected_before_creation(tmp_path: Path) -> None:
    root, head = _repo(tmp_path)
    with pytest.raises(ValueError, match="outside repository"):
        export_exact_head(root, expected_head=head, output_dir=root / "export", diagnostics_dir=tmp_path / "diag")
    assert not (root / "export").exists()
