from pathlib import Path

from aura_codebase_navigator import DEFAULT_SKIP_DIRS, _iter_repo_files


def test_iter_repo_files_skips_runtime_dependency_dirs(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('aura')\n", encoding="utf-8")
    (tmp_path / ".venv" / "lib" / "python3.12" / "site-packages").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "python3.12" / "site-packages" / "dep.py").write_text("bad = True\n", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "artifact.py").write_text("bad = True\n", encoding="utf-8")
    (tmp_path / "pkg.egg-info").mkdir()
    (tmp_path / "pkg.egg-info" / "PKG-INFO").write_text("bad\n", encoding="utf-8")

    rels = {path.relative_to(tmp_path).as_posix() for path in _iter_repo_files(tmp_path, DEFAULT_SKIP_DIRS)}

    assert rels == {"src/app.py"}
    assert not any(".venv" in rel or "site-packages" in rel or "egg-info" in rel for rel in rels)
