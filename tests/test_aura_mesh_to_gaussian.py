from __future__ import annotations

import hashlib
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import trimesh

from scripts.aura_mesh_to_gaussian import (
    _mesh_arrays,
    compile_mesh,
    sample_mesh_arrays,
    save_spz_v4,
    write_gaussian_ply,
)


def _triangle_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.array(
            [
                [0.0, 0.0, 0.0],
                [2.0, 0.0, 0.0],
                [0.0, 2.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        ),
        np.array([[0, 1, 2], [0, 1, 3]], dtype=np.int64),
        np.array([[0.2, 0.4, 0.8], [0.8, 0.3, 0.1]], dtype=np.float64),
    )


def _cloud(*, seed: int = 7, count: int = 64):
    vertices, faces, colors = _triangle_inputs()
    return sample_mesh_arrays(
        vertices=vertices,
        faces=faces,
        triangle_colors=colors,
        target_count=count,
        seed=seed,
    )


def test_sampling_is_deterministic_and_seed_sensitive() -> None:
    first = _cloud(seed=11)
    repeated = _cloud(seed=11)
    changed = _cloud(seed=12)

    assert first.representation_digest == repeated.representation_digest
    assert np.array_equal(first.positions, repeated.positions)
    assert first.representation_digest != changed.representation_digest
    assert not np.array_equal(first.positions, changed.positions)


def test_sampling_outputs_are_finite_normalized_and_bounded() -> None:
    cloud = _cloud(count=101)

    assert cloud.count == 101
    assert np.isfinite(cloud.positions).all()
    assert np.isfinite(cloud.normals).all()
    assert np.isfinite(cloud.log_scales).all()
    assert np.isfinite(cloud.rotations_xyzw).all()
    assert np.allclose(np.linalg.norm(cloud.normals, axis=1), 1.0, atol=1e-6)
    assert np.allclose(np.linalg.norm(cloud.rotations_xyzw, axis=1), 1.0, atol=1e-6)
    assert (np.exp(cloud.log_scales) > 0.0).all()
    opacity = 1.0 / (1.0 + np.exp(-cloud.alpha_logits))
    assert (opacity > 0.0).all() and (opacity < 1.0).all()
    assert (cloud.colors >= 0.0).all() and (cloud.colors <= 1.0).all()
    assert np.all(cloud.source_triangle_indices[:-1] <= cloud.source_triangle_indices[1:])


def test_sampling_rejects_nonfinite_and_fully_degenerate_meshes() -> None:
    vertices, faces, colors = _triangle_inputs()
    vertices[0, 0] = math.nan
    with pytest.raises(ValueError, match="finite Nx3"):
        sample_mesh_arrays(
            vertices=vertices,
            faces=faces,
            triangle_colors=colors,
            target_count=8,
            seed=1,
        )

    with pytest.raises(ValueError, match="no finite non-degenerate"):
        sample_mesh_arrays(
            vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
            faces=np.array([[0, 1, 2]]),
            triangle_colors=np.array([[0.5, 0.5, 0.5]]),
            target_count=8,
            seed=1,
        )


def test_mesh_loader_bakes_scene_transforms_in_stable_order(tmp_path: Path) -> None:
    mesh = trimesh.Trimesh(
        vertices=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        faces=[[0, 1, 2]],
        process=False,
    )
    scene = trimesh.Scene()
    scene.add_geometry(
        mesh,
        geom_name="translated-x",
        node_name="node-b",
        transform=trimesh.transformations.translation_matrix([10.0, 0.0, 0.0]),
    )
    scene.add_geometry(
        mesh,
        geom_name="translated-y",
        node_name="node-a",
        transform=trimesh.transformations.translation_matrix([0.0, 5.0, 0.0]),
    )
    path = tmp_path / "scene.glb"
    path.write_bytes(scene.export(file_type="glb"))

    vertices, faces, colors = _mesh_arrays(path)

    assert faces.shape == (2, 3)
    assert colors.shape == (2, 3)
    assert np.isclose(vertices[:, 0].max(), 11.0)
    assert np.isclose(vertices[:, 1].max(), 6.0)
    assert np.allclose(vertices[:3].min(axis=0), [0.0, 5.0, 0.0])


def test_gaussian_ply_is_binary_deterministic_and_repo_relative(tmp_path: Path) -> None:
    first = tmp_path / "generated" / "first.ply"
    second = tmp_path / "generated" / "second.ply"
    cloud = _cloud(count=12)

    receipt = write_gaussian_ply(first, cloud, repo_root=tmp_path)
    write_gaussian_ply(second, cloud, repo_root=tmp_path)

    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().startswith(b"ply\nformat binary_little_endian 1.0\n")
    assert b"element vertex 12\n" in first.read_bytes()[:1024]
    assert b"comment aura_sh_degree 0\n" in first.read_bytes()[:1024]
    assert receipt["path"] == "generated/first.ply"
    assert receipt["sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()
    assert receipt["representation_digest"] == cloud.representation_digest
    assert not first.with_suffix(".ply.tmp").exists()


class FakeGaussianCloud:
    pass


class FakePackOptions:
    def __init__(self) -> None:
        self.from_coord = None
        self.version = None


class FakeCoordinateSystem:
    LUF = object()


class FakeSpz:
    GaussianCloud = FakeGaussianCloud
    PackOptions = FakePackOptions
    CoordinateSystem = FakeCoordinateSystem
    last_cloud = None
    last_options = None

    @classmethod
    def save_spz(cls, cloud: FakeGaussianCloud, options: FakePackOptions, path: str) -> None:
        cls.last_cloud = cloud
        cls.last_options = options
        Path(path).write_bytes(b"fake-spz-v4")


def test_spz_bridge_sets_degree_zero_arrays_and_explicit_coordinates(tmp_path: Path) -> None:
    cloud = _cloud(count=9)
    output = tmp_path / "generated" / "cloud.spz"

    def validator(source: bytes):
        assert source == b"fake-spz-v4"
        return SimpleNamespace(point_count=9, sh_degree=0), ()

    receipt = save_spz_v4(
        output,
        cloud,
        repo_root=tmp_path,
        spz_module=FakeSpz,
        envelope_validator=validator,
    )

    saved = FakeSpz.last_cloud
    assert saved.sh_degree == 0
    assert saved.antialiased is False
    assert np.array_equal(saved.positions, cloud.positions.reshape(-1))
    assert np.array_equal(saved.scales, cloud.log_scales.reshape(-1))
    assert np.array_equal(saved.rotations, cloud.rotations_xyzw.reshape(-1))
    assert np.array_equal(saved.alphas, cloud.alpha_logits.reshape(-1))
    assert np.array_equal(saved.colors, cloud.colors.reshape(-1))
    assert saved.sh.size == 0
    assert FakeSpz.last_options.from_coord is FakeCoordinateSystem.LUF
    assert FakeSpz.last_options.version == 4
    assert receipt["source_coordinate_system"] == "LUF"
    assert receipt["stored_coordinate_system"] == "RUB"
    assert receipt["spz_version"] == 4
    assert receipt["path"] == "generated/cloud.spz"


def test_spz_header_mismatch_fails_closed_and_removes_temporary(tmp_path: Path) -> None:
    output = tmp_path / "cloud.spz"

    with pytest.raises(ValueError, match="does not match"):
        save_spz_v4(
            output,
            _cloud(count=5),
            repo_root=tmp_path,
            spz_module=FakeSpz,
            envelope_validator=lambda _source: (SimpleNamespace(point_count=4, sh_degree=0), ()),
        )

    assert not output.exists()
    assert not output.with_suffix(".spz.tmp").exists()


def test_compile_mesh_validates_source_digest_and_emits_ply(tmp_path: Path) -> None:
    mesh = trimesh.Trimesh(
        vertices=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        faces=[[0, 1, 2]],
        process=False,
    )
    glb = tmp_path / "source.glb"
    glb.write_bytes(trimesh.Scene(mesh).export(file_type="glb"))
    source_digest = hashlib.sha256(glb.read_bytes()).hexdigest()

    receipt = compile_mesh(
        repo_root=tmp_path,
        glb_path=Path("source.glb"),
        output_ply=Path("generated/source.ply"),
        output_spz=None,
        profile="LOW",
        source_digest=source_digest,
        target_count=32,
    )

    assert receipt["splat_count"] == 32
    assert receipt["source"] == "source.glb"
    assert receipt["source_coordinate_system"] == "LUF"
    assert receipt["stored_spz_coordinate_system"] is None
    assert receipt["projection_only"] is True
    assert (tmp_path / "generated/source.ply").is_file()

    with pytest.raises(ValueError, match="does not match"):
        compile_mesh(
            repo_root=tmp_path,
            glb_path=Path("source.glb"),
            output_ply=Path("generated/other.ply"),
            output_spz=None,
            profile="LOW",
            source_digest="0" * 64,
            target_count=8,
        )


def test_compile_mesh_rejects_output_escape(tmp_path: Path) -> None:
    mesh = trimesh.Trimesh(
        vertices=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        faces=[[0, 1, 2]],
        process=False,
    )
    glb = tmp_path / "source.glb"
    glb.write_bytes(trimesh.Scene(mesh).export(file_type="glb"))
    digest = hashlib.sha256(glb.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="escapes repository root"):
        compile_mesh(
            repo_root=tmp_path,
            glb_path=glb,
            output_ply=tmp_path.parent / "outside.ply",
            output_spz=None,
            profile="LOW",
            source_digest=digest,
            target_count=8,
        )
