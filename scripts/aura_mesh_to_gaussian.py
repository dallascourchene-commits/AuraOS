#!/usr/bin/env python3
"""Deterministically compile validated GLB meshes into degree-0 Gaussian PLY/SPZ."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Sequence

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_event_contracts import stable_digest
from aura_spatial_importers.spz import (
    MAX_SPZ_POINTS,
    MAX_SPZ_RUNTIME_ALLOCATION_BYTES,
    inspect_spz_v4_bytes,
)
from scripts.aura_verify_construction_demo_assets import atomic_json, sha256_file, verify_glb

GAUSSIAN_COMPILER_VERSION = "AURA_CONSTRUCTION_DEMO_GAUSSIAN_COMPILER_V1"
SH_C0 = 0.28209479177387814
DEFAULT_OPACITY = 0.92
MIN_THICKNESS = 0.001
# Aura's SPZ v4 admission gate conservatively estimates degree-0 clouds as
# 20 decoded stream bytes plus 2,304 object bytes and 3 coefficients * 96 bytes.
SPZ_SH0_RUNTIME_BYTES_PER_SPLAT = 20 + 2_304 + 3 * 96
MAX_IMPORTABLE_SH0_SPLATS = min(
    MAX_SPZ_POINTS,
    MAX_SPZ_RUNTIME_ALLOCATION_BYTES // SPZ_SH0_RUNTIME_BYTES_PER_SPLAT,
)
MAX_SPLATS = MAX_IMPORTABLE_SH0_SPLATS
PROFILE_LIMITS = {
    "LOW": {"STOREY": 40_000, "BUILDING": 75_000},
    "STANDARD": {"STOREY": 75_000, "BUILDING": 100_000},
    "VIDEO": {"STOREY": 100_000, "BUILDING": MAX_IMPORTABLE_SH0_SPLATS},
}
GAUSSIAN_SCOPES = ("STOREY", "BUILDING")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class GaussianCloudArrays:
    positions: np.ndarray
    normals: np.ndarray
    colors: np.ndarray
    log_scales: np.ndarray
    rotations_xyzw: np.ndarray
    alpha_logits: np.ndarray
    source_triangle_indices: np.ndarray
    representation_digest: str

    @property
    def count(self) -> int:
        return int(self.positions.shape[0])


def _arrays_digest(arrays: Sequence[np.ndarray]) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array)
        digest.update(str(contiguous.dtype).encode("ascii"))
        digest.update(json.dumps(list(contiguous.shape)).encode("ascii"))
        digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def _seed(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "little")


def _quaternions_from_normals(normals: np.ndarray) -> np.ndarray:
    values = np.asarray(normals, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 3 or not np.isfinite(values).all():
        raise ValueError("normals must be finite Nx3 values")
    result = np.column_stack(
        (-values[:, 1], values[:, 0], np.zeros(len(values)), 1.0 + values[:, 2])
    )
    degenerate = values[:, 2] < -0.999999
    result[degenerate] = (1.0, 0.0, 0.0, 0.0)
    lengths = np.linalg.norm(result, axis=1)
    if not np.isfinite(lengths).all() or np.any(lengths <= 0.0):
        raise ValueError("normal-to-quaternion conversion failed")
    result /= lengths[:, None]
    return result.astype(np.float32)


def _allocate_counts(areas: np.ndarray, target_count: int) -> np.ndarray:
    weights = areas / float(areas.sum())
    raw = weights * target_count
    counts = np.floor(raw).astype(np.int64)
    remainder = target_count - int(counts.sum())
    if remainder:
        order = np.lexsort((np.arange(len(raw)), -(raw - counts)))
        counts[order[:remainder]] += 1
    return counts


def sample_mesh_arrays(
    *,
    vertices: np.ndarray,
    faces: np.ndarray,
    triangle_colors: np.ndarray,
    target_count: int,
    seed: int,
) -> GaussianCloudArrays:
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    triangle_colors = np.asarray(triangle_colors, dtype=np.float64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("vertices must be finite Nx3 values")
    if faces.ndim != 2 or faces.shape[1] != 3 or len(faces) == 0:
        raise ValueError("faces must be a non-empty Mx3 array")
    if faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError("face index exceeds vertex bounds")
    if triangle_colors.shape != (len(faces), 3) or not np.isfinite(triangle_colors).all():
        raise ValueError("triangle_colors must be finite Mx3 values")
    if type(target_count) is not int or target_count < 1 or target_count > MAX_SPLATS:
        raise ValueError(f"target_count must be in [1, {MAX_SPLATS}]")

    triangles = vertices[faces]
    crosses = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    double_areas = np.linalg.norm(crosses, axis=1)
    valid = np.isfinite(double_areas) & (double_areas > 1e-12)
    if not valid.any():
        raise ValueError("mesh contains no finite non-degenerate triangles")
    triangles = triangles[valid]
    crosses = crosses[valid]
    areas = double_areas[valid] * 0.5
    colors = np.clip(triangle_colors[valid], 0.0, 1.0)
    original_indices = np.flatnonzero(valid)
    counts = _allocate_counts(areas, target_count)
    rng = np.random.default_rng(seed)

    positions: list[np.ndarray] = []
    normals: list[np.ndarray] = []
    sampled_colors: list[np.ndarray] = []
    scales: list[np.ndarray] = []
    triangle_indices: list[np.ndarray] = []
    for index, count in enumerate(counts):
        if count <= 0:
            continue
        random_values = rng.random((int(count), 2), dtype=np.float64)
        root = np.sqrt(random_values[:, 0])
        weights = np.column_stack(
            (
                1.0 - root,
                root * (1.0 - random_values[:, 1]),
                root * random_values[:, 1],
            )
        )
        positions.append(weights @ triangles[index])
        normal = crosses[index] / np.linalg.norm(crosses[index])
        normals.append(np.repeat(normal[None, :], int(count), axis=0))
        sampled_colors.append(np.repeat(colors[index][None, :], int(count), axis=0))
        tangent = max(
            math.sqrt(float(areas[index]) / max(int(count), 1)) * 0.75,
            MIN_THICKNESS,
        )
        thickness = max(min(tangent * 0.08, 0.02), MIN_THICKNESS)
        scales.append(np.repeat(np.log([[tangent, tangent, thickness]]), int(count), axis=0))
        triangle_indices.append(np.full(int(count), original_indices[index], dtype=np.int64))

    position_array = np.vstack(positions).astype(np.float32)
    normal_array = np.vstack(normals).astype(np.float32)
    color_array = np.vstack(sampled_colors).astype(np.float32)
    log_scale_array = np.vstack(scales).astype(np.float32)
    triangle_index_array = np.concatenate(triangle_indices)
    order = np.lexsort((np.arange(len(triangle_index_array)), triangle_index_array))
    position_array = position_array[order]
    normal_array = normal_array[order]
    color_array = color_array[order]
    log_scale_array = log_scale_array[order]
    triangle_index_array = triangle_index_array[order]
    rotations = _quaternions_from_normals(normal_array)
    alpha = math.log(DEFAULT_OPACITY / (1.0 - DEFAULT_OPACITY))
    alpha_logits = np.full(len(position_array), alpha, dtype=np.float32)
    representation_digest = _arrays_digest(
        (
            position_array,
            normal_array,
            color_array,
            log_scale_array,
            rotations,
            alpha_logits,
            triangle_index_array,
        )
    )
    return GaussianCloudArrays(
        positions=position_array,
        normals=normal_array,
        colors=color_array,
        log_scales=log_scale_array,
        rotations_xyzw=rotations,
        alpha_logits=alpha_logits,
        source_triangle_indices=triangle_index_array,
        representation_digest=representation_digest,
    )


def _mesh_arrays(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    try:
        import trimesh
    except ImportError as exc:
        raise RuntimeError("trimesh is required for GLB surface sampling") from exc
    loaded = trimesh.load(path, force="scene", process=False)
    instances: list[tuple[str, str, Any]] = []
    if hasattr(loaded, "graph") and hasattr(loaded, "geometry"):
        for node_name in sorted(str(item) for item in loaded.graph.nodes_geometry):
            transform, geometry_name = loaded.graph[node_name]
            mesh = loaded.geometry[geometry_name].copy()
            if not hasattr(mesh, "vertices") or not hasattr(mesh, "faces"):
                continue
            mesh.apply_transform(np.asarray(transform, dtype=np.float64))
            instances.append((node_name, str(geometry_name), mesh))
    else:
        instances.append(("geometry-0", "geometry-0", loaded))

    vertices: list[np.ndarray] = []
    faces: list[np.ndarray] = []
    colors: list[np.ndarray] = []
    offset = 0
    for geometry_index, (_node_name, _geometry_name, mesh) in enumerate(instances):
        mesh_vertices = np.asarray(mesh.vertices, dtype=np.float64)
        mesh_faces = np.asarray(mesh.faces, dtype=np.int64)
        if mesh_vertices.ndim != 2 or mesh_vertices.shape[1] != 3 or len(mesh_faces) == 0:
            continue
        vertices.append(mesh_vertices)
        faces.append(mesh_faces + offset)
        offset += len(mesh_vertices)
        fallback = np.array((0.62, 0.68, 0.75), dtype=np.float64)
        face_colors = getattr(getattr(mesh, "visual", None), "face_colors", None)
        if face_colors is not None and len(face_colors) == len(mesh_faces):
            rgba = np.asarray(face_colors, dtype=np.float64)
            colors.append(np.clip(rgba[:, :3] / 255.0, 0.0, 1.0))
        else:
            adjustment = (geometry_index % 7) * 0.025
            colors.append(
                np.repeat(
                    np.clip(fallback + adjustment, 0.0, 1.0)[None, :],
                    len(mesh_faces),
                    axis=0,
                )
            )
    if not vertices:
        raise ValueError("GLB contains no triangle geometry")
    return np.vstack(vertices), np.vstack(faces), np.vstack(colors)


def _resolve_inside(root: Path, path: Path, *, create_parent: bool = False) -> Path:
    repository = root.expanduser().resolve(strict=True)
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = repository / candidate
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("Gaussian asset path must not be a symlink")
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(repository)
    except ValueError as exc:
        raise ValueError("Gaussian asset path escapes repository root") from exc
    if create_parent:
        candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def _receipt_path(path: Path, root: Path | None) -> str:
    resolved = path.resolve(strict=True)
    if root is None:
        return resolved.as_posix()
    return resolved.relative_to(root.resolve(strict=True)).as_posix()


def write_gaussian_ply(
    path: Path,
    cloud: GaussianCloudArrays,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise ValueError("Gaussian PLY path must not be a symlink")
    fields = [
        ("x", "<f4"),
        ("y", "<f4"),
        ("z", "<f4"),
        ("nx", "<f4"),
        ("ny", "<f4"),
        ("nz", "<f4"),
        ("f_dc_0", "<f4"),
        ("f_dc_1", "<f4"),
        ("f_dc_2", "<f4"),
        ("opacity", "<f4"),
        ("scale_0", "<f4"),
        ("scale_1", "<f4"),
        ("scale_2", "<f4"),
        ("rot_0", "<f4"),
        ("rot_1", "<f4"),
        ("rot_2", "<f4"),
        ("rot_3", "<f4"),
    ]
    records = np.empty(cloud.count, dtype=np.dtype(fields))
    for index, name in enumerate(("x", "y", "z")):
        records[name] = cloud.positions[:, index]
    for index, name in enumerate(("nx", "ny", "nz")):
        records[name] = cloud.normals[:, index]
    dc = (cloud.colors - 0.5) / SH_C0
    for index, name in enumerate(("f_dc_0", "f_dc_1", "f_dc_2")):
        records[name] = dc[:, index]
    records["opacity"] = cloud.alpha_logits
    for index, name in enumerate(("scale_0", "scale_1", "scale_2")):
        records[name] = cloud.log_scales[:, index]
    for index, name in enumerate(("rot_0", "rot_1", "rot_2", "rot_3")):
        records[name] = cloud.rotations_xyzw[:, index]
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {cloud.count}"]
    header.extend(f"property float {name}" for name, _ in fields)
    header.extend(("comment aura_sh_degree 0", "comment aura_coordinate_system LUF", "end_header"))
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with temporary.open("wb") as handle:
            handle.write(("\n".join(header) + "\n").encode("ascii"))
            handle.write(records.tobytes(order="C"))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    payload = {
        "version": GAUSSIAN_COMPILER_VERSION,
        "representation": "GAUSSIAN_PLY",
        "path": _receipt_path(path, repo_root),
        "byte_length": path.stat().st_size,
        "sha256": sha256_file(path),
        "splat_count": cloud.count,
        "sh_degree": 0,
        "coordinate_system": "LUF",
        "representation_digest": cloud.representation_digest,
    }
    return {**payload, "receipt_digest": stable_digest(payload)}


def save_spz_v4(
    path: Path,
    cloud: GaussianCloudArrays,
    *,
    repo_root: Path | None = None,
    spz_module: Any | None = None,
    envelope_validator: Callable[[bytes], Any] = inspect_spz_v4_bytes,
) -> dict[str, Any]:
    if spz_module is None:
        try:
            import spz as spz_module  # type: ignore[no-redef]
        except ImportError as exc:
            raise RuntimeError("Niantic SPZ Python bindings are required for SPZ v4 output") from exc
    gaussian = spz_module.GaussianCloud()
    gaussian.sh_degree = 0
    gaussian.antialiased = False
    gaussian.positions = cloud.positions.reshape(-1)
    gaussian.scales = cloud.log_scales.reshape(-1)
    gaussian.rotations = cloud.rotations_xyzw.reshape(-1)
    gaussian.alphas = cloud.alpha_logits.reshape(-1)
    gaussian.colors = cloud.colors.reshape(-1)
    gaussian.sh = np.empty(0, dtype=np.float32)
    options = spz_module.PackOptions()
    options.from_coord = spz_module.CoordinateSystem.LUF
    if hasattr(options, "version"):
        options.version = 4
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise ValueError("Gaussian SPZ path must not be a symlink")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        spz_module.save_spz(gaussian, options, str(temporary))
        if not temporary.is_file() or temporary.is_symlink() or temporary.stat().st_size == 0:
            raise ValueError("SPZ binding did not produce output")
        source = temporary.read_bytes()
        header, _ = envelope_validator(source)
        if int(header.point_count) != cloud.count or int(header.sh_degree) != 0:
            raise ValueError("SPZ header does not match Gaussian cloud")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    payload = {
        "version": GAUSSIAN_COMPILER_VERSION,
        "representation": "GAUSSIAN_SPZ",
        "path": _receipt_path(path, repo_root),
        "byte_length": path.stat().st_size,
        "sha256": sha256_file(path),
        "splat_count": cloud.count,
        "sh_degree": 0,
        "source_coordinate_system": "LUF",
        "stored_coordinate_system": "RUB",
        "spz_version": 4,
        "representation_digest": cloud.representation_digest,
    }
    return {**payload, "receipt_digest": stable_digest(payload)}


def compile_mesh(
    *,
    repo_root: Path,
    glb_path: Path,
    output_ply: Path,
    output_spz: Path | None,
    profile: str,
    scope: str,
    source_digest: str,
    target_count: int | None = None,
    spz_module: Any | None = None,
    envelope_validator: Callable[[bytes], Any] = inspect_spz_v4_bytes,
) -> dict[str, Any]:
    repository = repo_root.expanduser().resolve(strict=True)
    if profile not in PROFILE_LIMITS:
        raise ValueError("unsupported Gaussian density profile")
    if scope not in GAUSSIAN_SCOPES:
        raise ValueError("unsupported Gaussian asset scope")
    if type(source_digest) is not str or _SHA256.fullmatch(source_digest) is None:
        raise ValueError("source_digest must be a lowercase SHA-256 digest")
    glb = _resolve_inside(repository, glb_path)
    ply = _resolve_inside(repository, output_ply, create_parent=True)
    spz = _resolve_inside(repository, output_spz, create_parent=True) if output_spz is not None else None
    glb_receipt = verify_glb(glb, root=repository)
    if glb_receipt["sha256"] != source_digest:
        raise ValueError("source_digest does not match the validated GLB")
    profile_limit = PROFILE_LIMITS[profile][scope]
    count = target_count or profile_limit
    if type(count) is not int or count < 1 or count > profile_limit:
        raise ValueError("target_count exceeds the selected density profile")
    vertices, faces, colors = _mesh_arrays(glb)
    cloud = sample_mesh_arrays(
        vertices=vertices,
        faces=faces,
        triangle_colors=colors,
        target_count=count,
        seed=_seed(f"{source_digest}:{profile}:{count}"),
    )
    ply_receipt = write_gaussian_ply(ply, cloud, repo_root=repository)
    spz_receipt = (
        save_spz_v4(
            spz,
            cloud,
            repo_root=repository,
            spz_module=spz_module,
            envelope_validator=envelope_validator,
        )
        if spz is not None
        else None
    )
    payload = {
        "version": GAUSSIAN_COMPILER_VERSION,
        "profile": profile,
        "scope": scope,
        "profile_limit": profile_limit,
        "source": glb.relative_to(repository).as_posix(),
        "source_digest": source_digest,
        "source_verification_digest": glb_receipt["verification_digest"],
        "splat_count": cloud.count,
        "representation_digest": cloud.representation_digest,
        "ply": ply_receipt,
        "spz": spz_receipt,
        "source_coordinate_system": "LUF",
        "stored_spz_coordinate_system": "RUB" if spz_receipt is not None else None,
        "survey_authority": False,
        "projection_only": True,
        "production_mutation": False,
    }
    return {**payload, "receipt_digest": stable_digest(payload)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--glb", type=Path, required=True)
    parser.add_argument("--output-ply", type=Path, required=True)
    parser.add_argument("--output-spz", type=Path)
    parser.add_argument("--profile", choices=tuple(PROFILE_LIMITS), default="STANDARD")
    parser.add_argument("--scope", choices=GAUSSIAN_SCOPES, default="STOREY")
    parser.add_argument("--source-digest", required=True)
    parser.add_argument("--target-count", type=int)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = compile_mesh(
        repo_root=args.repo_root,
        glb_path=args.glb,
        output_ply=args.output_ply,
        output_spz=args.output_spz,
        profile=args.profile,
        scope=args.scope,
        source_digest=args.source_digest,
        target_count=args.target_count,
    )
    atomic_json(args.receipt, result)
    print(
        json.dumps(
            {"receipt_digest": result["receipt_digest"], "splat_count": result["splat_count"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
