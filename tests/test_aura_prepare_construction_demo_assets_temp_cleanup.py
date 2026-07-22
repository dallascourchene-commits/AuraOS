from __future__ import annotations

from pathlib import Path

import pytest

from scripts import aura_prepare_construction_demo_assets as assets


def test_cleanup_is_recursive_and_root_confined(tmp_path: Path) -> None:
    output = tmp_path / "generated"
    storey = output / "storeys" / "storey-a"
    storey.mkdir(parents=True)
    canonical = storey / "storey-a.glb"
    raw_building = output / ".building-full.ifcconvert.abc.glb"
    raw_storey = storey / ".storey-a.ifcconvert.xyz.glb"
    canonical.write_bytes(b"canonical")
    raw_building.write_bytes(b"raw")
    raw_storey.write_bytes(b"raw")

    assets._cleanup_ifcconvert_glb_temps(repo_root=tmp_path, output_dir=output)

    assert canonical.read_bytes() == b"canonical"
    assert not raw_building.exists()
    assert not raw_storey.exists()


def test_preserves_conversion_failure_when_cleanup_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def conversion(**kwargs):
        raise RuntimeError("conversion failed")

    def cleanup(**kwargs):
        raise PermissionError("cleanup denied")

    monkeypatch.setattr(assets, "_ORIGINAL_CONVERT_IFC_ASSETS", conversion)
    monkeypatch.setattr(assets, "_cleanup_ifcconvert_glb_temps", cleanup)
    with pytest.raises(RuntimeError, match="conversion failed") as caught:
        assets.convert_ifc_assets(output_dir=tmp_path, repo_root=tmp_path)
    assert any("cleanup denied" in note for note in getattr(caught.value, "__notes__", ()))


def test_cleanup_failure_surfaces_after_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assets, "_ORIGINAL_CONVERT_IFC_ASSETS", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(
        assets,
        "_cleanup_ifcconvert_glb_temps",
        lambda **kwargs: (_ for _ in ()).throw(PermissionError("cleanup denied")),
    )
    with pytest.raises(PermissionError, match="cleanup denied"):
        assets.convert_ifc_assets(output_dir=tmp_path, repo_root=tmp_path)
