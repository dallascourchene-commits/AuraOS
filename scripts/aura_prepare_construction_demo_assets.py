#!/usr/bin/env python3
"""Construction demo asset preparation with guaranteed IfcConvert temp cleanup."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from scripts import aura_prepare_construction_demo_assets_core as _core
except ModuleNotFoundError:
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
    """Run conversion, preserving its failure if cleanup independently fails."""

    active_error: BaseException | None = None
    try:
        return _ORIGINAL_CONVERT_IFC_ASSETS(
            output_dir=output_dir,
            repo_root=repo_root,
            **kwargs,
        )
    except BaseException as exc:
        active_error = exc
        raise
    finally:
        try:
            _cleanup_ifcconvert_glb_temps(repo_root=repo_root, output_dir=output_dir)
        except Exception as cleanup_error:
            if active_error is None:
                raise
            active_error.add_note(
                "IfcConvert temporary cleanup also failed: "
                f"{type(cleanup_error).__name__}: {cleanup_error}"
            )


_core.convert_ifc_assets = convert_ifc_assets


def main(argv: Any = None) -> int:
    return _core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
