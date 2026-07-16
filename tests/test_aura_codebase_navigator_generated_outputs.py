from __future__ import annotations

from pathlib import Path

from aura_codebase_navigator import GENERATED_MAP_FILES, _iter_repo_files


def test_generated_topology_map_is_excluded_from_full_repository_scan(tmp_path: Path) -> None:
    (tmp_path / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "topology_map.json").write_text('{"nodes": []}\n', encoding="utf-8")
    aura_dir = tmp_path / ".aura"
    aura_dir.mkdir()
    (aura_dir / "CODEMAP.json").write_text("{}\n", encoding="utf-8")
    (aura_dir / "CODEMAP.md").write_text("# map\n", encoding="utf-8")

    paths = {
        path.relative_to(tmp_path).as_posix()
        for path in _iter_repo_files(tmp_path, frozenset())
    }

    assert paths == {"source.py"}
    assert "topology_map.json" in GENERATED_MAP_FILES
    assert ".aura/CODEMAP.json" in GENERATED_MAP_FILES
    assert ".aura/CODEMAP.md" in GENERATED_MAP_FILES
