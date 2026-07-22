from __future__ import annotations

from pathlib import Path

import pytest

from scripts import aura_prepare_construction_demo_assets as assets


def test_cleanup_ifcconvert_glb_temps_is_recursive_and_root_confined(tmp_path: Path) -> None:
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


def test_convert_ifc_assets_cleans_temps_after_success_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "generated"
    output.mkdir()
    success_temp = output / ".building-full.ifcconvert.success.glb"
    failure_temp = output / ".building-full.ifcconvert.failure.glb"

    def successful(**kwargs):
        success_temp.write_bytes(b"raw")
        return {"phase": "CONVERT_GLB_SVG"}

    monkeypatch.setattr(assets, "_ORIGINAL_CONVERT_IFC_ASSETS", successful)
    assert assets.convert_ifc_assets(output_dir=output, repo_root=tmp_path) == {
        "phase": "CONVERT_GLB_SVG"
    }
    assert not success_temp.exists()

    def failing(**kwargs):
        failure_temp.write_bytes(b"raw")
        raise RuntimeError("later conversion failed")

    monkeypatch.setattr(assets, "_ORIGINAL_CONVERT_IFC_ASSETS", failing)
    with pytest.raises(RuntimeError, match="later conversion failed"):
        assets.convert_ifc_assets(output_dir=output, repo_root=tmp_path)
    assert not failure_temp.exists()
