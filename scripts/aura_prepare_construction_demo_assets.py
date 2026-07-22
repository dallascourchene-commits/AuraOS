#!/usr/bin/env python3
"""Construction demo asset preparation with guaranteed IfcConvert temp cleanup.

The reviewed implementation is preserved in
``scripts.aura_prepare_construction_demo_assets_core``. This stable public
entrypoint exports its complete compatibility surface and overrides only the
conversion boundary so raw ``.ifcconvert.*.glb`` transport files cannot survive
successful canonicalization or a later job failure.
"""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from scripts import aura_prepare_construction_demo_assets_core as _core
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    import aura_prepare_construction_demo_assets_core as _core  # type: ignore[no-redef]

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_ORIGINAL_CONVERT_IFC_ASSETS = _core.convert_ifc_assets


def _cleanup_ifcconvert_glb_temps(*, repo_root: Path, output_dir: Path) -> None:
    """Remove only root-confined raw GLB transport files left by IfcConvert."""

    repository = repo_root.expanduser().resolve(strict=True)
    try:
        output = _core._resolve_inside(repository, output_dir)
    except (FileNotFoundError, ValueError):
        return
    if not output.exists():
        return
    for temporary in output.rglob(".*.ifcconvert.*.glb"):
        if temporary.is_file() or temporary.is_symlink():
            temporary.unlink(missing_ok=True)


def convert_ifc_assets(*, output_dir: Path, repo_root: Path, **kwargs: Any) -> dict[str, Any]:
    """Run canonical conversion and always remove raw IfcConvert GLB transports."""

    try:
        return _ORIGINAL_CONVERT_IFC_ASSETS(
            output_dir=output_dir,
            repo_root=repo_root,
            **kwargs,
        )
    finally:
        _cleanup_ifcconvert_glb_temps(repo_root=repo_root, output_dir=output_dir)


# The core CLI resolves this function from its own module globals.
_core.convert_ifc_assets = convert_ifc_assets


def main(argv: Any = None) -> int:
    return _core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
