from __future__ import annotations

from pathlib import Path

import pytest

import aura_civic_planning_inventory as module
from aura_civic_planning_inventory import CivicInventoryError, build_civic_surface_inventory


def _write(root: Path, path: str, symbols: tuple[str, ...]) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(f"def {name}():\n    return None" for name in symbols) + "\n", encoding="utf-8")


def test_inventory_is_deterministic_and_source_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(module, "_SURFACE_SPECS", (("a.py", "OWNER", ("owner",)), ("b.py", "CALLER", ())))
    _write(tmp_path, "a.py", ("owner",))
    _write(tmp_path, "b.py", ())
    first = build_civic_surface_inventory(tmp_path)
    second = build_civic_surface_inventory(tmp_path)
    assert first.digest == second.digest
    assert tuple(item.path for item in first.entries) == ("a.py", "b.py")


def test_inventory_fails_on_missing_symbol_and_non_utf8(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(module, "_SURFACE_SPECS", (("a.py", "OWNER", ("owner",)),))
    _write(tmp_path, "a.py", ())
    with pytest.raises(CivicInventoryError, match="missing declared symbols"):
        build_civic_surface_inventory(tmp_path)
    (tmp_path / "a.py").write_bytes(b"\xff")
    with pytest.raises(CivicInventoryError, match="not UTF-8"):
        build_civic_surface_inventory(tmp_path)


def test_inventory_rejects_symlink_escape(tmp_path, monkeypatch) -> None:
    outside = tmp_path.parent / "outside.py"
    outside.write_text("def owner():\n    return None\n", encoding="utf-8")
    link = tmp_path / "a.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    monkeypatch.setattr(module, "_SURFACE_SPECS", (("a.py", "OWNER", ("owner",)),))
    with pytest.raises(CivicInventoryError, match="escapes repository root"):
        build_civic_surface_inventory(tmp_path)
