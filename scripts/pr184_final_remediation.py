#!/usr/bin/env python3
"""Apply the exact reviewed PR #184 remediation spans and nothing else."""
from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one source span, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> int:
    replace_once(
        "scripts/aura_architecture_harness_core.py",
        '''    payload = process.stdout.read(max_bytes + 1)\n    stderr = process.stderr.read(COMMAND_OUTPUT_MAX_BYTES + 1) if process.stderr else b""\n    returncode = process.wait()\n    if returncode:\n        raise RuntimeError(\n            "git cat-file failed: "\n            + stderr[:COMMAND_OUTPUT_MAX_BYTES].decode("utf-8", errors="replace")\n        )\n    if len(payload) > max_bytes:\n        raise RuntimeError("Git blob exceeded its admitted source-review ceiling")\n    return payload\n''',
        '''    payload = process.stdout.read(max_bytes + 1)\n    if len(payload) > max_bytes:\n        process.kill()\n        process.wait()\n        raise RuntimeError("Git blob exceeded its admitted source-review ceiling")\n    stderr = process.stderr.read(COMMAND_OUTPUT_MAX_BYTES + 1) if process.stderr else b""\n    returncode = process.wait()\n    if returncode:\n        raise RuntimeError(\n            "git cat-file failed: "\n            + stderr[:COMMAND_OUTPUT_MAX_BYTES].decode("utf-8", errors="replace")\n        )\n    return payload\n''',
    )

    replace_once(
        "scripts/aura_architecture_harness.py",
        '''    result = _ORIGINAL_CREATE_AI_HANDOFF(\n        root,\n''',
        '''    # Preserve the PR #182 compatibility seam: callers and tests may\n    # monkeypatch the wrapper helper while the original function resolves it\n    # from the core module's globals.\n    _core._read_git_blob = _read_git_blob\n    result = _ORIGINAL_CREATE_AI_HANDOFF(\n        root,\n''',
    )

    replace_once(
        "scripts/aura_prepare_construction_demo_assets.py",
        '''            active_error.add_note(\n                "IfcConvert temporary cleanup also failed: "\n                f"{type(cleanup_error).__name__}: {cleanup_error}"\n            )\n''',
        '''            message = (\n                "IfcConvert temporary cleanup also failed: "\n                f"{type(cleanup_error).__name__}: {cleanup_error}"\n            )\n            add_note = getattr(active_error, "add_note", None)\n            if callable(add_note):\n                add_note(message)\n            else:\n                notes = list(getattr(active_error, "__notes__", ()))\n                notes.append(message)\n                try:\n                    setattr(active_error, "__notes__", notes)\n                except (AttributeError, TypeError):\n                    pass\n''',
    )

    replace_once(
        "scripts/aura_prepare_construction_demo_assets_core.py",
        '''if __name__ == "__main__":\n    raise SystemExit(main())\n''',
        '''if __name__ == "__main__":\n    try:\n        from scripts.aura_prepare_construction_demo_assets import main as _cleanup_aware_main\n    except ModuleNotFoundError:\n        from aura_prepare_construction_demo_assets import main as _cleanup_aware_main\n    raise SystemExit(_cleanup_aware_main())\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        "from typing import Any, Callable, Sequence\n",
        "from typing import Any, Callable, Mapping, Sequence\n",
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        "from aura_spatial_importers.gltf import import_gltf_file\n",
        "from aura_spatial_importers.gltf import MAX_GLTF_SOURCE_BYTES, import_gltf_file\n",
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''_SHA256 = re.compile(r"^[0-9a-f]{64}$")\n''',
        '''_SHA256 = re.compile(r"^[0-9a-f]{64}$")\nCANONICAL_FACE_COLOR_VERSION = "AURA_CONSTRUCTION_CANONICAL_FACE_COLORS_V1"\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''def _canonical_mesh_arrays(path: Path) -> tuple[np.ndarray, np.ndarray]:\n    """Flatten scene transforms and deterministically deduplicate mesh positions."""\n\n    vertices, faces, _colors = _mesh_arrays(path)\n    positions = np.asarray(vertices, dtype="<f4")\n    triangles = np.asarray(faces, dtype=np.int64)\n    if positions.ndim != 2 or positions.shape[1] != 3 or not np.isfinite(positions).all():\n        raise ValueError("canonical GLB positions must be finite Nx3 values")\n    if triangles.ndim != 2 or triangles.shape[1] != 3 or len(triangles) == 0:\n        raise ValueError("canonical GLB requires triangle faces")\n    unique_positions, inverse = np.unique(positions, axis=0, return_inverse=True)\n    canonical_faces = inverse[triangles]\n    nondegenerate = (\n        (canonical_faces[:, 0] != canonical_faces[:, 1])\n        & (canonical_faces[:, 1] != canonical_faces[:, 2])\n        & (canonical_faces[:, 0] != canonical_faces[:, 2])\n    )\n    canonical_faces = canonical_faces[nondegenerate]\n    if len(canonical_faces) == 0:\n        raise ValueError("canonical GLB contains no non-degenerate triangles")\n    order = np.lexsort(\n        (canonical_faces[:, 2], canonical_faces[:, 1], canonical_faces[:, 0])\n    )\n    canonical_faces = canonical_faces[order]\n    return np.ascontiguousarray(unique_positions), np.ascontiguousarray(canonical_faces)\n''',
        '''def _canonical_mesh_arrays(\n    path: Path,\n) -> tuple[np.ndarray, np.ndarray, np.ndarray]:\n    """Flatten transforms and preserve colors through deterministic face ordering."""\n\n    vertices, faces, colors = _mesh_arrays(path)\n    positions = np.asarray(vertices, dtype="<f4")\n    triangles = np.asarray(faces, dtype=np.int64)\n    face_colors = np.asarray(colors, dtype="<f4")\n    if positions.ndim != 2 or positions.shape[1] != 3 or not np.isfinite(positions).all():\n        raise ValueError("canonical GLB positions must be finite Nx3 values")\n    if triangles.ndim != 2 or triangles.shape[1] != 3 or len(triangles) == 0:\n        raise ValueError("canonical GLB requires triangle faces")\n    if face_colors.shape != (len(triangles), 3) or not np.isfinite(face_colors).all():\n        raise ValueError("canonical GLB colors must be finite Mx3 values")\n    unique_positions, inverse = np.unique(positions, axis=0, return_inverse=True)\n    canonical_faces = inverse[triangles]\n    nondegenerate = (\n        (canonical_faces[:, 0] != canonical_faces[:, 1])\n        & (canonical_faces[:, 1] != canonical_faces[:, 2])\n        & (canonical_faces[:, 0] != canonical_faces[:, 2])\n    )\n    canonical_faces = canonical_faces[nondegenerate]\n    canonical_colors = np.clip(face_colors[nondegenerate], 0.0, 1.0)\n    if len(canonical_faces) == 0:\n        raise ValueError("canonical GLB contains no non-degenerate triangles")\n    order = np.lexsort(\n        (canonical_faces[:, 2], canonical_faces[:, 1], canonical_faces[:, 0])\n    )\n    canonical_faces = canonical_faces[order]\n    canonical_colors = canonical_colors[order]\n    return (\n        np.ascontiguousarray(unique_positions),\n        np.ascontiguousarray(canonical_faces),\n        np.ascontiguousarray(canonical_colors, dtype="<f4"),\n    )\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''def canonicalize_glb_for_aura(\n''',
        '''def _write_face_color_asset(\n    output: Path, face_colors: np.ndarray, *, repo_root: Path\n) -> dict[str, Any]:\n    repository = repo_root.expanduser().resolve(strict=True)\n    colors = np.ascontiguousarray(face_colors, dtype="<f4")\n    if colors.ndim != 2 or colors.shape[1] != 3 or not np.isfinite(colors).all():\n        raise ValueError("canonical face colors must be finite Mx3 values")\n    path = _resolve_inside(\n        repository, output.with_name(f"{output.name}.face-colors.bin"), create_parent=True\n    )\n    descriptor, temporary_name = tempfile.mkstemp(\n        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent\n    )\n    temporary = Path(temporary_name)\n    try:\n        with os.fdopen(descriptor, "wb") as handle:\n            handle.write(colors.tobytes(order="C"))\n            handle.flush()\n            os.fsync(handle.fileno())\n        os.replace(temporary, path)\n    finally:\n        temporary.unlink(missing_ok=True)\n    body = {\n        "version": CANONICAL_FACE_COLOR_VERSION,\n        "path": path.relative_to(repository).as_posix(),\n        "byte_length": path.stat().st_size,\n        "sha256": sha256_file(path),\n        "triangle_count": len(colors),\n        "components": 3,\n        "dtype": "float32-le",\n        "build_only": True,\n        "runtime_asset": False,\n    }\n    return {**body, "receipt_digest": stable_digest(body)}\n\n\ndef load_face_color_asset(\n    asset: Mapping[str, Any], *, repo_root: Path\n) -> np.ndarray:\n    body = dict(asset)\n    digest = body.pop("receipt_digest", None)\n    if digest != stable_digest(body):\n        raise ValueError("face-color receipt does not authenticate its record")\n    count = body.get("triangle_count")\n    if (\n        body.get("version") != CANONICAL_FACE_COLOR_VERSION\n        or body.get("components") != 3\n        or body.get("dtype") != "float32-le"\n        or body.get("build_only") is not True\n        or body.get("runtime_asset") is not False\n        or type(count) is not int\n        or count < 1\n    ):\n        raise ValueError("face-color asset contract is invalid")\n    repository = repo_root.expanduser().resolve(strict=True)\n    path = _resolve_inside(repository, Path(str(body.get("path"))))\n    expected_bytes = count * 3 * 4\n    if (\n        not path.is_file()\n        or path.is_symlink()\n        or body.get("byte_length") != expected_bytes\n        or path.stat().st_size != expected_bytes\n        or body.get("sha256") != sha256_file(path)\n    ):\n        raise ValueError("face-color asset bytes do not match their receipt")\n    colors = np.frombuffer(path.read_bytes(), dtype="<f4").copy().reshape(count, 3)\n    if not np.isfinite(colors).all() or np.any(colors < 0.0) or np.any(colors > 1.0):\n        raise ValueError("face-color asset contains invalid values")\n    return colors\n\n\ndef canonicalize_glb_for_aura(\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''    positions, faces = _canonical_mesh_arrays(source)\n''',
        '''    positions, faces, face_colors = _canonical_mesh_arrays(source)\n''',
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''    binary_payload = position_bytes + index_bytes\n    document = {\n''',
        '''    binary_payload = position_bytes + index_bytes\n    if 28 + len(binary_payload) > MAX_GLTF_SOURCE_BYTES:\n        raise ValueError("canonical GLB exceeds Aura mesh importer source-byte ceiling")\n    document = {\n''',
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''    encoded = struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body\n\n    descriptor, temporary_name = tempfile.mkstemp(\n''',
        '''    encoded = struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body\n    if len(encoded) > MAX_GLTF_SOURCE_BYTES:\n        raise ValueError("canonical GLB exceeds Aura mesh importer source-byte ceiling")\n\n    descriptor, temporary_name = tempfile.mkstemp(\n''',
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''    import_receipt = imported.receipt.to_dict()\n    payload = {\n''',
        '''    import_receipt = imported.receipt.to_dict()\n    face_color_asset = _write_face_color_asset(\n        output, face_colors, repo_root=repository\n    )\n    payload = {\n''',
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''        "index_component_type": component_type,\n        "bounds_min": [float(item) for item in positions.min(axis=0)],\n''',
        '''        "index_component_type": component_type,\n        "face_color_asset": face_color_asset,\n        "face_colors_preserved": True,\n        "bounds_min": [float(item) for item in positions.min(axis=0)],\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''    target_count: int | None = None,\n    spz_module: Any | None = None,\n''',
        '''    target_count: int | None = None,\n    triangle_colors: np.ndarray | None = None,\n    triangle_color_digest: str | None = None,\n    spz_module: Any | None = None,\n''',
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''    vertices, faces, colors = _mesh_arrays(glb)\n    cloud = sample_mesh_arrays(\n''',
        '''    vertices, faces, embedded_colors = _mesh_arrays(glb)\n    if triangle_colors is None:\n        colors = embedded_colors\n        color_source = "GLB_VISUAL_OR_FALLBACK"\n        if triangle_color_digest is not None:\n            raise ValueError("triangle_color_digest requires explicit triangle_colors")\n    else:\n        colors = np.asarray(triangle_colors, dtype=np.float64)\n        if colors.shape != (len(faces), 3) or not np.isfinite(colors).all():\n            raise ValueError("triangle_colors must align with the validated GLB faces")\n        if type(triangle_color_digest) is not str or _SHA256.fullmatch(triangle_color_digest) is None:\n            raise ValueError("triangle_color_digest must authenticate explicit colors")\n        color_source = "CANONICAL_FACE_COLOR_ASSET"\n    cloud = sample_mesh_arrays(\n''',
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''        seed=_seed(f"{source_digest}:{profile}:{count}"),\n''',
        '''        seed=_seed(\n            f"{source_digest}:{triangle_color_digest or 'embedded'}:{profile}:{count}"\n        ),\n''',
    )
    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''        "source_verification_digest": glb_receipt["verification_digest"],\n        "splat_count": cloud.count,\n''',
        '''        "source_verification_digest": glb_receipt["verification_digest"],\n        "triangle_color_source": color_source,\n        "triangle_color_digest": triangle_color_digest,\n        "splat_count": cloud.count,\n''',
    )

    replace_once(
        "scripts/aura_prepare_construction_demo_assets_core.py",
        '''    canonicalize_glb_for_aura,\n    compile_mesh,\n''',
        '''    canonicalize_glb_for_aura,\n    compile_mesh,\n    load_face_color_asset,\n''',
    )
    replace_once(
        "scripts/aura_prepare_construction_demo_assets_core.py",
        '''            if (\n                canonicalization.get("output") != item.get("output")\n                or canonicalization.get("output_sha256") != item.get("output_sha256")\n                or canonicalization.get("runtime_admitted") is not True\n                or canonicalization.get("import_receipt_digest") != runtime_digest\n            ):\n                raise ValueError("canonical GLB evidence does not match conversion output")\n''',
        '''            if (\n                canonicalization.get("output") != item.get("output")\n                or canonicalization.get("output_sha256") != item.get("output_sha256")\n                or canonicalization.get("runtime_admitted") is not True\n                or canonicalization.get("import_receipt_digest") != runtime_digest\n                or canonicalization.get("face_colors_preserved") is not True\n            ):\n                raise ValueError("canonical GLB evidence does not match conversion output")\n            colors = load_face_color_asset(\n                canonicalization.get("face_color_asset"), repo_root=repository\n            )\n            if len(colors) != canonicalization.get("triangle_count"):\n                raise ValueError("face-color asset does not cover canonical triangles")\n''',
    )
    replace_once(
        "scripts/aura_prepare_construction_demo_assets_core.py",
        '''        except Exception:\n            temporary.unlink(missing_ok=True)\n            job_output.unlink(missing_ok=True)\n            raise\n''',
        '''        except Exception:\n            temporary.unlink(missing_ok=True)\n            job_output.unlink(missing_ok=True)\n            job_output.with_name(f"{job_output.name}.face-colors.bin").unlink(\n                missing_ok=True\n            )\n            raise\n''',
    )
    replace_once(
        "scripts/aura_prepare_construction_demo_assets_core.py",
        '''        result = mesh_compiler(\n            repo_root=repository,\n''',
        '''        canonicalization = item.get("canonicalization")\n        if not isinstance(canonicalization, Mapping):\n            raise ValueError("Gaussian compilation requires canonicalization evidence")\n        color_asset = canonicalization.get("face_color_asset")\n        if not isinstance(color_asset, Mapping):\n            raise ValueError("Gaussian compilation requires face-color evidence")\n        face_colors = load_face_color_asset(color_asset, repo_root=repository)\n        result = mesh_compiler(\n            repo_root=repository,\n''',
    )
    replace_once(
        "scripts/aura_prepare_construction_demo_assets_core.py",
        '''            target_count=target_count,\n            spz_module=spz_module,\n''',
        '''            target_count=target_count,\n            triangle_colors=face_colors,\n            triangle_color_digest=str(color_asset["sha256"]),\n            spz_module=spz_module,\n''',
    )

    replace_once(
        "tests/test_aura_mesh_to_gaussian.py",
        '''    canonicalize_glb_for_aura,\n    compile_mesh,\n''',
        '''    canonicalize_glb_for_aura,\n    compile_mesh,\n    load_face_color_asset,\n''',
    )
    replace_once(
        "tests/test_aura_mesh_to_gaussian.py",
        '''    assert receipt["output_sha256"] == repeated["output_sha256"]\n    assert first.stat().st_size < 16 * 1024 * 1024\n''',
        '''    assert receipt["output_sha256"] == repeated["output_sha256"]\n    colors = load_face_color_asset(receipt["face_color_asset"], repo_root=tmp_path)\n    assert colors.shape == (1, 3)\n    assert receipt["face_colors_preserved"] is True\n    assert first.stat().st_size < 16 * 1024 * 1024\n''',
    )
    replace_once(
        "tests/test_aura_prepare_construction_demo_assets.py",
        '''    assert all(item["canonicalization"]["output"] == item["output"] for item in glb_rows)\n''',
        '''    assert all(item["canonicalization"]["output"] == item["output"] for item in glb_rows)\n    assert all(item["canonicalization"]["face_colors_preserved"] is True for item in glb_rows)\n    assert all(\n        (tmp_path / item["canonicalization"]["face_color_asset"]["path"]).is_file()\n        for item in glb_rows\n    )\n''',
    )
    replace_once(
        "tests/test_aura_prepare_construction_demo_assets.py",
        '''    assert [(call["scope"], call["target_count"]) for call in calls] == [\n''',
        '''    assert all(call["triangle_colors"].shape == (1, 3) for call in calls)\n    assert all(len(str(call["triangle_color_digest"])) == 64 for call in calls)\n    assert [(call["scope"], call["target_count"]) for call in calls] == [\n''',
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
