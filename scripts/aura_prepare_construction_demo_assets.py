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
import re
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
IFCCONVERT_IDENTITY_VERSION = "AURA_IFCCONVERT_IDENTITY_V1"
_STOREY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
PINNED_SOURCE_IDENTITY = {
    "source_id": "tuwien-custom-escape-route-ifc-v2",
    "title": "Custom Test Model for Escape Route Analysis in IFC format",
    "creators": (
        "Christian Schranz",
        "Daniel Pfeiffer",
        "Harald Urban",
        "Sebastian Zdanowicz",
        "Simon Fischer",
    ),
    "publisher": "TU Wien",
    "doi": "10.48436/a185k-86v39",
    "source_filename": "CustomTestModel-EscapeRouteAnalysis-ZDB-v2.ifc",
    "source_byte_length": 7_404_420,
    "published_md5": "58a6e009b16bd3808cacd72b11fcf216",
    "observed_sha256": "29945f654c636d758a95b66eb0e107ec35afc7e1c7857a7ff652586e7728ba29",
    "license_id": "CC-BY-4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "source_manifest_digest": "22bd970d5babc6ad2d6a22ca2c278738",
}


def _canonical_storey_id(value: Any) -> str:
    if type(value) is not str or _STOREY_ID.fullmatch(value) is None:
        raise ValueError("storey_id must be a canonical bounded identifier")
    return value


def _validate_pinned_source_manifest(manifest: ConstructionDemoSourceManifest) -> None:
    observed = {
        "source_id": manifest.source_id,
        "title": manifest.title,
        "creators": manifest.creators,
        "publisher": manifest.publisher,
        "doi": manifest.doi,
        "source_filename": manifest.source_filename,
        "source_byte_length": manifest.source_byte_length,
        "published_md5": manifest.published_md5,
        "observed_sha256": manifest.observed_sha256,
        "license_id": manifest.license_id,
        "license_url": manifest.license_url,
        "source_manifest_digest": manifest.source_manifest_digest,
    }
    if observed != PINNED_SOURCE_IDENTITY:
        raise ValueError("source manifest does not match the canonical TU Wien Construction demo pin")


def _validate_digest_record(record: Mapping[str, Any], digest_field: str = "receipt_digest") -> None:
    body = dict(record)
    digest = body.pop(digest_field, None)
    if type(digest) is not str or digest != stable_digest(body):
        raise ValueError(f"{digest_field} does not authenticate its record")


def _validate_hierarchy(hierarchy: Mapping[str, Any]) -> None:
    _validate_digest_record(hierarchy, "hierarchy_digest")
    if hierarchy.get("ifcopenshell_validated") is not True:
        raise ValueError("storey splitting requires an authoritative IfcOpenShell hierarchy")


def _secure_copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.is_symlink():
        raise ValueError("copy destination must not be a symlink")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as reader, os.fdopen(descriptor, "wb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_split_receipt(
    receipt: Mapping[str, Any],
    *,
    repository: Path,
    output: Path,
    source_sha256: str,
    source_manifest_digest: str,
    hierarchy_digest: str,
) -> tuple[Mapping[str, Any], ...]:
    _validate_digest_record(receipt)
    if (
        receipt.get("version") != ASSET_PREPARATION_VERSION
        or receipt.get("phase") != "SPLIT_STOREYS"
        or receipt.get("production_mutation") is not False
        or receipt.get("construction_state_owner") is not False
    ):
        raise ValueError("split receipt is invalid")
    if receipt.get("source_sha256") != source_sha256:
        raise ValueError("split receipt source lineage does not match")
    if receipt.get("source_manifest_digest") != source_manifest_digest:
        raise ValueError("split receipt source-manifest lineage does not match")
    if receipt.get("hierarchy_digest") != hierarchy_digest:
        raise ValueError("split receipt hierarchy lineage does not match")
    rows = receipt.get("outputs")
    if not isinstance(rows, list) or receipt.get("output_count") != len(rows) or not rows:
        raise ValueError("split receipt outputs are invalid")
    storey_ids: set[str] = set()
    global_ids: set[str] = set()
    validated: list[Mapping[str, Any]] = []
    for item in rows:
        if not isinstance(item, Mapping):
            raise ValueError("split receipt output must be an object")
        storey_id = _canonical_storey_id(item.get("storey_id"))
        global_id = item.get("ifc_global_id")
        if type(global_id) is not str or not global_id:
            raise ValueError("split receipt GlobalId is invalid")
        if storey_id in storey_ids or global_id in global_ids:
            raise ValueError("split receipt contains duplicate storey identity")
        storey_ids.add(storey_id)
        global_ids.add(global_id)
        path = _resolve_inside(repository, Path(str(item.get("path"))))
        expected = (output / "storeys" / storey_id / f"{storey_id}.ifc").resolve(strict=False)
        if path != expected or not path.is_file() or path.is_symlink():
            raise ValueError("split receipt output path is not canonical")
        if item.get("byte_length") != path.stat().st_size or item.get("sha256") != sha256_file(path):
            raise ValueError("split IFC digest drifted before conversion")
        validated.append(item)
    return tuple(validated)




def _validate_ifcconvert_identity(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("IfcConvert identity is missing")
    _validate_digest_record(value, "identity_digest")
    sha256 = value.get("sha256")
    if (
        value.get("version") != IFCCONVERT_IDENTITY_VERSION
        or type(value.get("executable_name")) is not str
        or not value.get("executable_name")
        or type(value.get("byte_length")) is not int
        or value.get("byte_length", 0) <= 0
        or type(sha256) is not str
        or len(sha256) != 64
        or any(character not in "0123456789abcdef" for character in sha256)
        or type(value.get("version_text")) is not str
        or not value.get("version_text")
    ):
        raise ValueError("IfcConvert identity is invalid")
    return value


def _capture_ifcconvert_identity(
    executable: Path,
    *,
    repository: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    version_receipt = run_bounded_command(
        [str(executable), "--version"],
        cwd=repository,
        timeout_seconds=min(timeout_seconds, 30.0),
    )
    version_text = (version_receipt.stdout.strip() or version_receipt.stderr.strip())
    if not version_text or len(version_text.encode("utf-8")) > 4096:
        raise ValueError("IfcConvert --version must emit bounded identity text")
    body = {
        "version": IFCCONVERT_IDENTITY_VERSION,
        "executable_name": executable.name,
        "byte_length": executable.stat().st_size,
        "sha256": sha256_file(executable),
        "version_text": version_text,
    }
    return {**body, "identity_digest": stable_digest(body)}


def _validate_command_receipt(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("command receipt is missing")
    _validate_digest_record(value)
    if (
        value.get("returncode") != 0
        or value.get("timed_out") is not False
        or value.get("output_limit_exceeded", False) is not False
    ):
        raise ValueError("command receipt is not successful")


def _validate_verification_receipt(value: Any, *, path: Path, repository: Path) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("verification receipt is missing")
    _validate_digest_record(value, "verification_digest")
    if value.get("path") != path.relative_to(repository).as_posix():
        raise ValueError("verification receipt path does not match output")
    if value.get("sha256") != sha256_file(path) or value.get("byte_length") != path.stat().st_size:
        raise ValueError("verification receipt does not match output bytes")


def _validate_conversion_receipt(
    receipt: Mapping[str, Any],
    *,
    repository: Path,
    output: Path,
    source_sha256: str,
    source_manifest_digest: str,
    hierarchy_digest: str,
    split_receipt_digest: str,
) -> tuple[Mapping[str, Any], ...]:
    _validate_digest_record(receipt)
    if (
        receipt.get("version") != ASSET_PREPARATION_VERSION
        or receipt.get("phase") != "CONVERT_GLB_SVG"
        or receipt.get("production_mutation") is not False
        or receipt.get("external_resource_fetch") is not False
        or receipt.get("survey_authority") is not False
    ):
        raise ValueError("conversion receipt is invalid")
    identity = _validate_ifcconvert_identity(receipt.get("ifcconvert_identity"))
    expected_lineage = {
        "source_sha256": source_sha256,
        "source_manifest_digest": source_manifest_digest,
        "hierarchy_digest": hierarchy_digest,
        "split_receipt_digest": split_receipt_digest,
    }
    if any(receipt.get(key) != value for key, value in expected_lineage.items()):
        raise ValueError("conversion receipt lineage does not match canonical inputs")
    rows = receipt.get("outputs")
    if not isinstance(rows, list) or receipt.get("output_count") != len(rows) or not rows:
        raise ValueError("conversion receipt outputs are invalid")
    job_ids: set[str] = set()
    validated: list[Mapping[str, Any]] = []
    for item in rows:
        if not isinstance(item, Mapping):
            raise ValueError("conversion job receipt must be an object")
        _validate_digest_record(item)
        job_id = item.get("job_id")
        if type(job_id) is not str or not job_id or job_id in job_ids:
            raise ValueError("conversion receipt contains duplicate or invalid jobs")
        job_ids.add(job_id)
        if item.get("split_receipt_digest") != split_receipt_digest:
            raise ValueError("conversion job lineage does not match split receipt")
        if item.get("ifcconvert_identity_digest") != identity["identity_digest"]:
            raise ValueError("conversion job does not match the recorded IfcConvert identity")
        source = _resolve_inside(repository, Path(str(item.get("source"))))
        target = _resolve_inside(repository, Path(str(item.get("output"))))
        try:
            target.relative_to(output)
        except ValueError as exc:
            raise ValueError("conversion output escapes its generated root") from exc
        if not source.is_file() or source.is_symlink() or item.get("source_sha256") != sha256_file(source):
            raise ValueError("conversion source receipt does not match bytes")
        if not target.is_file() or target.is_symlink():
            raise ValueError("conversion output is not a regular file")
        if item.get("output_sha256") != sha256_file(target) or item.get("output_byte_length") != target.stat().st_size:
            raise ValueError("validated conversion output digest drifted")
        representation = item.get("representation")
        if representation not in {"MESH_GLB", "FLOOR_PLAN_SVG"}:
            raise ValueError("conversion representation is invalid")
        _validate_command_receipt(item.get("command_receipt"))
        _validate_verification_receipt(item.get("verification"), path=target, repository=repository)
        validated.append(item)
    if "building-full-glb" not in job_ids:
        raise ValueError("conversion receipt is missing the full-building mesh")
    return tuple(validated)


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



def split_storeys(
    *,
    source: Path,
    hierarchy: Mapping[str, Any],
    output_dir: Path,
    repo_root: Path,
    source_manifest_digest: str,
    ifcopenshell_module: Any | None = None,
    ifcpatch_module: Any | None = None,
) -> dict[str, Any]:
    repository = repo_root.expanduser().resolve(strict=True)
    source_path = _resolve_inside(repository, source)
    output = _resolve_inside(repository, output_dir, create=True)
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("source IFC must be a regular non-symlink file")
    _validate_hierarchy(hierarchy)
    if hierarchy.get("source_sha256") != sha256_file(source_path):
        raise ValueError("authoritative hierarchy does not match source IFC")
    if type(source_manifest_digest) is not str or not source_manifest_digest:
        raise ValueError("source_manifest_digest is required")
    expected_rows = hierarchy.get("storeys")
    if not isinstance(expected_rows, list) or not expected_rows:
        raise ValueError("authoritative hierarchy contains no storeys")
    expected: dict[str, str] = {}
    storey_ids: set[str] = set()
    for item in expected_rows:
        if not isinstance(item, Mapping):
            raise ValueError("authoritative hierarchy storey must be an object")
        global_id = item.get("ifc_global_id")
        if type(global_id) is not str or not global_id or global_id in expected:
            raise ValueError("authoritative hierarchy contains duplicate or invalid storey GlobalIds")
        storey_id = _canonical_storey_id(item.get("storey_id"))
        if storey_id in storey_ids:
            raise ValueError("authoritative hierarchy contains duplicate storey ids")
        expected[global_id] = storey_id
        storey_ids.add(storey_id)

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
            destination = _resolve_inside(
                repository,
                output / "storeys" / storey_id / f"{storey_id}.ifc",
            )
            try:
                destination.relative_to(output)
            except ValueError as exc:
                raise ValueError("storey output escapes generated root") from exc
            _secure_copy_atomic(observed[global_id], destination)
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
        "source_manifest_digest": source_manifest_digest,
        "hierarchy_digest": hierarchy["hierarchy_digest"],
        "outputs": outputs,
        "output_count": len(outputs),
        "production_mutation": False,
        "construction_state_owner": False,
    }
    receipt = {**payload, "receipt_digest": stable_digest(payload)}
    atomic_json(output / "receipts" / "split-storeys.json", receipt, root=output)
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
    source_manifest_digest: str,
    hierarchy_digest: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    repository = repo_root.expanduser().resolve(strict=True)
    source_path = _resolve_inside(repository, source)
    output = _resolve_inside(repository, output_dir, create=True)
    executable = ifcconvert.expanduser().resolve(strict=True)
    if not executable.is_file() or executable.is_symlink() or not os.access(executable, os.X_OK):
        raise ValueError("IfcConvert must be an executable regular non-symlink file")
    source_sha256 = sha256_file(source_path)
    ifcconvert_identity = _capture_ifcconvert_identity(
        executable,
        repository=repository,
        timeout_seconds=timeout_seconds,
    )
    split_rows = _validate_split_receipt(
        split_receipt,
        repository=repository,
        output=output,
        source_sha256=source_sha256,
        source_manifest_digest=source_manifest_digest,
        hierarchy_digest=hierarchy_digest,
    )

    jobs: list[tuple[str, Path, Path, bool]] = [
        ("building-full-glb", source_path, output / "building-full.glb", False)
    ]
    for item in split_rows:
        storey_id = _canonical_storey_id(item["storey_id"])
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
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{job_output.name}.", suffix=".partial", dir=job_output.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
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
            os.replace(temporary, job_output)
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
            "source_manifest_digest": source_manifest_digest,
            "hierarchy_digest": hierarchy_digest,
            "split_receipt_digest": split_receipt["receipt_digest"],
            "output": job_output.relative_to(repository).as_posix(),
            "output_sha256": sha256_file(job_output),
            "output_byte_length": job_output.stat().st_size,
            "representation": "FLOOR_PLAN_SVG" if is_svg else "MESH_GLB",
            "coordinate_system": "RIGHT_HANDED_Y_UP_METERS",
            "unit_scale_meters": 1.0,
            "command_receipt": command_receipt.to_content_dict(),
            "ifcconvert_identity_digest": ifcconvert_identity["identity_digest"],
            "verification": verification,
            "survey_authority": False,
            "production_mutation": False,
        }
        job_receipt["receipt_digest"] = stable_digest(job_receipt)
        atomic_json(output / "receipts" / f"{job_id}.json", job_receipt, root=output)
        outputs.append(job_receipt)

    payload = {
        "version": ASSET_PREPARATION_VERSION,
        "phase": "CONVERT_GLB_SVG",
        "source_sha256": source_sha256,
        "source_manifest_digest": source_manifest_digest,
        "hierarchy_digest": hierarchy_digest,
        "split_receipt_digest": split_receipt["receipt_digest"],
        "ifcconvert_identity": ifcconvert_identity,
        "outputs": outputs,
        "output_count": len(outputs),
        "external_resource_fetch": False,
        "survey_authority": False,
        "production_mutation": False,
    }
    receipt = {**payload, "receipt_digest": stable_digest(payload)}
    atomic_json(output / "receipts" / "convert-glb-svg.json", receipt, root=output)
    return receipt


def compile_gaussian_assets(
    *,
    conversion_receipt: Mapping[str, Any],
    split_receipt: Mapping[str, Any],
    output_dir: Path,
    repo_root: Path,
    source_sha256: str,
    source_manifest_digest: str,
    hierarchy_digest: str,
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
    split_rows = _validate_split_receipt(
        split_receipt,
        repository=repository,
        output=output,
        source_sha256=source_sha256,
        source_manifest_digest=source_manifest_digest,
        hierarchy_digest=hierarchy_digest,
    )
    conversion_rows = _validate_conversion_receipt(
        conversion_receipt,
        repository=repository,
        output=output,
        source_sha256=source_sha256,
        source_manifest_digest=source_manifest_digest,
        hierarchy_digest=hierarchy_digest,
        split_receipt_digest=str(split_receipt["receipt_digest"]),
    )
    source_rows = [
        item for item in conversion_rows if item.get("representation") == "MESH_GLB"
    ]
    if not source_rows:
        raise ValueError("conversion receipt contains no GLB meshes")
    job_ids = [str(item.get("job_id") or "") for item in source_rows]
    expected_mesh_jobs = {"building-full-glb"} | {
        f"{_canonical_storey_id(item.get('storey_id'))}-glb" for item in split_rows
    }
    if len(job_ids) != len(set(job_ids)) or set(job_ids) != expected_mesh_jobs:
        raise ValueError("conversion receipt must contain the exact full-building and storey GLB jobs")
    split_by_storey = {
        _canonical_storey_id(item.get("storey_id")): item for item in split_rows
    }
    for item in source_rows:
        job_id = str(item["job_id"])
        if job_id == "building-full-glb":
            expected_output = (output / "building-full.glb").relative_to(repository).as_posix()
            if item.get("output") != expected_output or item.get("source_sha256") != source_sha256:
                raise ValueError("full-building GLB job does not match canonical source and output")
            continue
        storey_id = job_id.removesuffix("-glb")
        split_item = split_by_storey[storey_id]
        expected_output = (
            output / "storeys" / storey_id / f"{storey_id}.glb"
        ).relative_to(repository).as_posix()
        if item.get("source") != split_item.get("path") or item.get("output") != expected_output:
            raise ValueError("storey GLB job does not match its canonical split source and output")

    compiled: list[dict[str, Any]] = []
    for item in sorted(source_rows, key=lambda row: str(row["job_id"])):
        source = _resolve_inside(repository, Path(str(item["output"])))
        glb_sha256 = sha256_file(source)
        if glb_sha256 != item.get("output_sha256"):
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
            source_digest=glb_sha256,
            target_count=target_count,
            spz_module=spz_module,
        )
        _validate_digest_record(result)
        if result.get("source_digest") != glb_sha256 or result.get("scope") != scope:
            raise ValueError("Gaussian compiler receipt does not match its source or scope")
        ply_receipt = result.get("ply")
        spz_receipt = result.get("spz")
        if not isinstance(ply_receipt, Mapping) or not isinstance(spz_receipt, Mapping):
            raise ValueError("Gaussian compiler must emit both PLY and SPZ receipts")
        for representation_receipt in (ply_receipt, spz_receipt):
            _validate_digest_record(representation_receipt)
            representation_path = _resolve_inside(
                repository, Path(str(representation_receipt.get("path")))
            )
            if (
                not representation_path.is_file()
                or representation_path.is_symlink()
                or representation_receipt.get("sha256") != sha256_file(representation_path)
                or representation_receipt.get("byte_length") != representation_path.stat().st_size
            ):
                raise ValueError("Gaussian representation receipt does not match output bytes")
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
        "source_sha256": source_sha256,
        "source_manifest_digest": source_manifest_digest,
        "hierarchy_digest": hierarchy_digest,
        "split_receipt_digest": split_receipt["receipt_digest"],
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
    atomic_json(output / "receipts" / "compile-gaussians.json", receipt, root=output)
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
    _validate_pinned_source_manifest(manifest)
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
            source_manifest_digest=manifest.source_manifest_digest,
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
            source_manifest_digest=manifest.source_manifest_digest,
            hierarchy_digest=str(hierarchy["hierarchy_digest"]),
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
            split_receipt=split_receipt,
            output_dir=output,
            repo_root=repository,
            source_sha256=manifest.observed_sha256,
            source_manifest_digest=manifest.source_manifest_digest,
            hierarchy_digest=str(hierarchy["hierarchy_digest"]),
            profile=args.profile,
            storey_target_count=args.storey_target_count,
            building_target_count=args.building_target_count,
        )
    print(json.dumps({"phase": result["phase"], "receipt_digest": result["receipt_digest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
