#!/usr/bin/env python3
"""Deterministic IFC split and GLB/SVG preparation for the Construction demo.

This build-only orchestrator never runs during Aura startup or demo runtime. It
requires the pinned source manifest and authoritative IfcOpenShell hierarchy,
uses bounded tool invocations, validates every output, and writes receipts.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_construction_demo_contracts import ConstructionDemoSourceManifest
from aura_event_contracts import stable_digest
from scripts.aura_mesh_to_gaussian import PROFILE_LIMITS, compile_mesh
from scripts.aura_verify_construction_demo_assets import (
    atomic_json,
    run_bounded_command,
    sanitize_svg,
    sha256_file,
    verify_glb,
)

ASSET_PREPARATION_VERSION = "AURA_CONSTRUCTION_DEMO_ASSET_PREPARATION_V1"
MAX_WORKERS = 8
DEFAULT_TIMEOUT_SECONDS = 300.0


def _resolve_inside(root: Path, path: Path, *, create: bool = False) -> Path:
    repository = root.expanduser().resolve(strict=True)
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = repository / candidate
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("build path must not be a symlink")
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(repository)
    except ValueError as exc:
        raise ValueError("build path escapes repository root") from exc
    if create:
        candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _load_source_manifest(path: Path) -> ConstructionDemoSourceManifest:
    return ConstructionDemoSourceManifest.from_dict(_load_json(path))


def _load_modules(ifcopenshell_module: Any | None, ifcpatch_module: Any | None) -> tuple[Any, Any]:
    if ifcopenshell_module is None:
        try:
            import ifcopenshell as ifcopenshell_module  # type: ignore[no-redef]
        except ImportError as exc:
            raise RuntimeError("IfcOpenShell is required for storey splitting") from exc
    if ifcpatch_module is None:
        try:
            import ifcpatch as ifcpatch_module  # type: ignore[no-redef]
        except ImportError as exc:
            raise RuntimeError("IfcPatch is required for storey splitting") from exc
    return ifcopenshell_module, ifcpatch_module


def _copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with source.open("rb") as reader, temporary.open("wb") as writer:
        shutil.copyfileobj(reader, writer, length=1024 * 1024)
        writer.flush()
        os.fsync(writer.fileno())
    temporary.replace(destination)


def split_storeys(
    *,
    source: Path,
    hierarchy: Mapping[str, Any],
    output_dir: Path,
    repo_root: Path,
    ifcopenshell_module: Any | None = None,
    ifcpatch_module: Any | None = None,
) -> dict[str, Any]:
    repository = repo_root.expanduser().resolve(strict=True)
    source_path = _resolve_inside(repository, source)
    output = _resolve_inside(repository, output_dir, create=True)
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("source IFC must be a regular non-symlink file")
    if hierarchy.get("source_sha256") != sha256_file(source_path):
        raise ValueError("authoritative hierarchy does not match source IFC")
    if hierarchy.get("ifcopenshell_validated") is not True:
        raise ValueError("storey splitting requires an authoritative IfcOpenShell hierarchy")
    expected_rows = hierarchy.get("storeys")
    if not isinstance(expected_rows, list) or not expected_rows:
        raise ValueError("authoritative hierarchy contains no storeys")
    expected = {str(item["ifc_global_id"]): str(item["storey_id"]) for item in expected_rows}
    if len(expected) != len(expected_rows):
        raise ValueError("authoritative hierarchy contains duplicate storey GlobalIds")

    ifcopenshell, ifcpatch = _load_modules(ifcopenshell_module, ifcpatch_module)
    model = ifcopenshell.open(str(source_path))
    with tempfile.TemporaryDirectory(prefix=".ifc-split-", dir=output) as temporary_name:
        temporary_dir = Path(temporary_name)
        ifcpatch.execute(
            {
                "input": str(source_path),
                "file": model,
                "recipe": "SplitByBuildingStorey",
                "arguments": [str(temporary_dir)],
            }
        )
        candidates = sorted(path for path in temporary_dir.rglob("*.ifc") if path.is_file())
        if not candidates:
            raise ValueError("IfcPatch produced no storey IFC files")
        observed: dict[str, Path] = {}
        for candidate in candidates:
            candidate_model = ifcopenshell.open(str(candidate))
            candidate_storeys = tuple(candidate_model.by_type("IfcBuildingStorey"))
            if len(candidate_storeys) != 1:
                raise ValueError("split IFC must contain exactly one IfcBuildingStorey")
            global_id = str(candidate_storeys[0].GlobalId)
            if global_id not in expected:
                raise ValueError("split IFC references an unknown storey GlobalId")
            if global_id in observed:
                raise ValueError("IfcPatch produced duplicate storey IFC outputs")
            observed[global_id] = candidate
        if set(observed) != set(expected):
            raise ValueError("IfcPatch output does not cover the authoritative storey hierarchy")

        outputs: list[dict[str, Any]] = []
        for global_id, storey_id in sorted(expected.items(), key=lambda item: item[1]):
            destination = output / "storeys" / storey_id / f"{storey_id}.ifc"
            _copy_atomic(observed[global_id], destination)
            outputs.append(
                {
                    "storey_id": storey_id,
                    "ifc_global_id": global_id,
                    "path": destination.relative_to(repository).as_posix(),
                    "byte_length": destination.stat().st_size,
                    "sha256": sha256_file(destination),
                }
            )
    payload = {
        "version": ASSET_PREPARATION_VERSION,
        "phase": "SPLIT_STOREYS",
        "source_sha256": hierarchy["source_sha256"],
        "hierarchy_digest": hierarchy["hierarchy_digest"],
        "outputs": outputs,
        "output_count": len(outputs),
        "production_mutation": False,
        "construction_state_owner": False,
    }
    receipt = {**payload, "receipt_digest": stable_digest(payload)}
    atomic_json(output / "receipts" / "split-storeys.json", receipt)
    return receipt


def _ifcconvert_command(
    executable: Path,
    *,
    source: Path,
    output: Path,
    workers: int,
    svg: bool,
) -> list[str]:
    if type(workers) is not int or workers < 1 or workers > MAX_WORKERS:
        raise ValueError(f"workers must be in [1, {MAX_WORKERS}]")
    if svg:
        return [
            str(executable),
            "-yv",
            "-j",
            str(workers),
            "--exclude",
            "entities",
            "IfcOpeningElement",
            "IfcSpace",
            str(source),
            str(output),
        ]
    return [
        str(executable),
        "--center-model",
        "-j",
        str(workers),
        str(source),
        str(output),
    ]


def convert_ifc_assets(
    *,
    source: Path,
    split_receipt: Mapping[str, Any],
    output_dir: Path,
    repo_root: Path,
    ifcconvert: Path,
    workers: int,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    repository = repo_root.expanduser().resolve(strict=True)
    source_path = _resolve_inside(repository, source)
    output = _resolve_inside(repository, output_dir, create=True)
    executable = ifcconvert.expanduser().resolve(strict=True)
    if not executable.is_file() or executable.is_symlink() or not os.access(executable, os.X_OK):
        raise ValueError("IfcConvert must be an executable regular non-symlink file")
    if split_receipt.get("phase") != "SPLIT_STOREYS" or split_receipt.get("production_mutation") is not False:
        raise ValueError("split receipt is invalid")

    jobs: list[tuple[str, Path, Path, bool]] = [
        ("building-full-glb", source_path, output / "building-full.glb", False)
    ]
    for item in split_receipt.get("outputs", ()):
        storey_id = str(item["storey_id"])
        split_path = _resolve_inside(repository, Path(str(item["path"])))
        if sha256_file(split_path) != item["sha256"]:
            raise ValueError("split IFC digest drifted before conversion")
        storey_dir = output / "storeys" / storey_id
        jobs.extend(
            (
                (f"{storey_id}-glb", split_path, storey_dir / f"{storey_id}.glb", False),
                (f"{storey_id}-svg", split_path, storey_dir / f"{storey_id}.svg", True),
            )
        )

    outputs: list[dict[str, Any]] = []
    for job_id, job_source, job_output, is_svg in jobs:
        job_output.parent.mkdir(parents=True, exist_ok=True)
        temporary = job_output.with_suffix(job_output.suffix + ".partial")
        temporary.unlink(missing_ok=True)
        command = _ifcconvert_command(
            executable,
            source=job_source,
            output=temporary,
            workers=workers,
            svg=is_svg,
        )
        try:
            command_receipt = run_bounded_command(
                command,
                cwd=repository,
                timeout_seconds=timeout_seconds,
            )
            if not temporary.is_file() or temporary.is_symlink() or temporary.stat().st_size == 0:
                raise ValueError("IfcConvert did not produce a complete regular output file")
            temporary.replace(job_output)
            verification = (
                sanitize_svg(job_output, root=repository)
                if is_svg
                else verify_glb(job_output, root=repository)
            )
        except Exception:
            temporary.unlink(missing_ok=True)
            job_output.unlink(missing_ok=True)
            raise
        job_receipt = {
            "version": ASSET_PREPARATION_VERSION,
            "job_id": job_id,
            "source": job_source.relative_to(repository).as_posix(),
            "source_sha256": sha256_file(job_source),
            "output": job_output.relative_to(repository).as_posix(),
            "output_sha256": sha256_file(job_output),
            "output_byte_length": job_output.stat().st_size,
            "representation": "FLOOR_PLAN_SVG" if is_svg else "MESH_GLB",
            "coordinate_system": "RIGHT_HANDED_Y_UP_METERS",
            "unit_scale_meters": 1.0,
            "command_receipt": command_receipt.to_dict(),
            "verification": verification,
            "survey_authority": False,
            "production_mutation": False,
        }
        job_receipt["receipt_digest"] = stable_digest(job_receipt)
        atomic_json(output / "receipts" / f"{job_id}.json", job_receipt)
        outputs.append(job_receipt)

    payload = {
        "version": ASSET_PREPARATION_VERSION,
        "phase": "CONVERT_GLB_SVG",
        "split_receipt_digest": split_receipt["receipt_digest"],
        "outputs": outputs,
        "output_count": len(outputs),
        "external_resource_fetch": False,
        "survey_authority": False,
        "production_mutation": False,
    }
    receipt = {**payload, "receipt_digest": stable_digest(payload)}
    atomic_json(output / "receipts" / "convert-glb-svg.json", receipt)
    return receipt


def compile_gaussian_assets(
    *,
    conversion_receipt: Mapping[str, Any],
    output_dir: Path,
    repo_root: Path,
    profile: str,
    storey_target_count: int | None = None,
    building_target_count: int | None = None,
    mesh_compiler: Callable[..., dict[str, Any]] = compile_mesh,
    spz_module: Any | None = None,
) -> dict[str, Any]:
    repository = repo_root.expanduser().resolve(strict=True)
    output = _resolve_inside(repository, output_dir, create=True)
    if profile not in PROFILE_LIMITS:
        raise ValueError("unsupported Gaussian density profile")
    if conversion_receipt.get("phase") != "CONVERT_GLB_SVG":
        raise ValueError("Gaussian compilation requires a GLB/SVG conversion receipt")
    if conversion_receipt.get("production_mutation") is not False:
        raise ValueError("conversion receipt violates the production-mutation boundary")
    source_rows = [
        item
        for item in conversion_receipt.get("outputs", ())
        if item.get("representation") == "MESH_GLB"
    ]
    if not source_rows:
        raise ValueError("conversion receipt contains no GLB meshes")
    job_ids = [str(item.get("job_id") or "") for item in source_rows]
    if len(job_ids) != len(set(job_ids)) or "building-full-glb" not in job_ids:
        raise ValueError("conversion receipt must contain unique mesh jobs and one full building")

    compiled: list[dict[str, Any]] = []
    for item in sorted(source_rows, key=lambda row: str(row["job_id"])):
        source = _resolve_inside(repository, Path(str(item["output"])))
        source_sha256 = sha256_file(source)
        if source_sha256 != item.get("output_sha256"):
            raise ValueError("validated GLB digest drifted before Gaussian compilation")
        scope = "BUILDING" if item["job_id"] == "building-full-glb" else "STOREY"
        target_count = building_target_count if scope == "BUILDING" else storey_target_count
        base_name = source.stem
        ply = source.with_name(f"{base_name}.gaussian.ply")
        spz = source.with_name(f"{base_name}.spz")
        result = mesh_compiler(
            repo_root=repository,
            glb_path=source,
            output_ply=ply,
            output_spz=spz,
            profile=profile,
            scope=scope,
            source_digest=source_sha256,
            target_count=target_count,
            spz_module=spz_module,
        )
        if result.get("source_digest") != source_sha256 or result.get("scope") != scope:
            raise ValueError("Gaussian compiler receipt does not match its source or scope")
        if not isinstance(result.get("ply"), Mapping) or not isinstance(result.get("spz"), Mapping):
            raise ValueError("Gaussian compiler must emit both PLY and SPZ receipts")
        compiled.append(
            {
                "job_id": str(item["job_id"]),
                "scope": scope,
                "source_glb_receipt_digest": item["receipt_digest"],
                "gaussian_receipt": result,
            }
        )

    payload = {
        "version": ASSET_PREPARATION_VERSION,
        "phase": "SAMPLE_GAUSSIANS_WRITE_SPZ",
        "conversion_receipt_digest": conversion_receipt["receipt_digest"],
        "profile": profile,
        "profile_limits": PROFILE_LIMITS[profile],
        "storey_target_count": storey_target_count,
        "building_target_count": building_target_count,
        "outputs": compiled,
        "output_count": len(compiled),
        "source_coordinate_system": "LUF",
        "stored_spz_coordinate_system": "RUB",
        "survey_authority": False,
        "projection_only": True,
        "production_mutation": False,
    }
    receipt = {**payload, "receipt_digest": stable_digest(payload)}
    atomic_json(output / "receipts" / "compile-gaussians.json", receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--hierarchy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ifcconvert", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--profile", choices=tuple(PROFILE_LIMITS), default="STANDARD")
    parser.add_argument("--storey-target-count", type=int)
    parser.add_argument("--building-target-count", type=int)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--phase",
        choices=("split", "convert", "gaussian", "all"),
        default="all",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = args.repo_root.expanduser().resolve(strict=True)
    source = _resolve_inside(repository, args.source)
    manifest = _load_source_manifest(_resolve_inside(repository, args.source_manifest))
    if manifest.observed_sha256 != sha256_file(source):
        raise ValueError("source bytes do not match source manifest")
    hierarchy = _load_json(_resolve_inside(repository, args.hierarchy))
    output = _resolve_inside(repository, args.output, create=True)
    split_receipt_path = output / "receipts" / "split-storeys.json"
    if args.phase in {"split", "all"}:
        split_receipt = split_storeys(
            source=source,
            hierarchy=hierarchy,
            output_dir=output,
            repo_root=repository,
        )
    else:
        split_receipt = _load_json(split_receipt_path)
    result: Mapping[str, Any] = split_receipt
    conversion_receipt_path = output / "receipts" / "convert-glb-svg.json"
    if args.phase in {"convert", "all"}:
        if args.ifcconvert is None:
            raise ValueError("--ifcconvert is required for conversion")
        conversion_receipt = convert_ifc_assets(
            source=source,
            split_receipt=split_receipt,
            output_dir=output,
            repo_root=repository,
            ifcconvert=args.ifcconvert,
            workers=args.workers,
            timeout_seconds=args.timeout_seconds,
        )
        result = conversion_receipt
    else:
        conversion_receipt = _load_json(conversion_receipt_path) if args.phase == "gaussian" else None
    if args.phase in {"gaussian", "all"}:
        if conversion_receipt is None:
            raise ValueError("Gaussian compilation requires a conversion receipt")
        result = compile_gaussian_assets(
            conversion_receipt=conversion_receipt,
            output_dir=output,
            repo_root=repository,
            profile=args.profile,
            storey_target_count=args.storey_target_count,
            building_target_count=args.building_target_count,
        )
    print(json.dumps({"phase": result["phase"], "receipt_digest": result["receipt_digest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
