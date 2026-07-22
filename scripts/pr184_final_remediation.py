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
        '''            add_note = getattr(active_error, "add_note", None)\n            if callable(add_note):\n                add_note(\n                    "IfcConvert temporary cleanup also failed: "\n                    f"{type(cleanup_error).__name__}: {cleanup_error}"\n                )\n''',
    )

    replace_once(
        "scripts/aura_prepare_construction_demo_assets_core.py",
        '''if __name__ == "__main__":\n    raise SystemExit(main())\n''',
        '''if __name__ == "__main__":\n    try:\n        from scripts.aura_prepare_construction_demo_assets import main as _cleanup_aware_main\n    except ModuleNotFoundError:\n        from aura_prepare_construction_demo_assets import main as _cleanup_aware_main\n    raise SystemExit(_cleanup_aware_main())\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        "from aura_spatial_importers.gltf import import_gltf_file\n",
        "from aura_spatial_importers.gltf import MAX_GLTF_SOURCE_BYTES, import_gltf_file\n",
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''def _canonical_mesh_arrays(path: Path) -> tuple[np.ndarray, np.ndarray]:\n    """Flatten scene transforms and deterministically deduplicate mesh positions."""\n\n    vertices, faces, _colors = _mesh_arrays(path)\n    positions = np.asarray(vertices, dtype="<f4")\n    triangles = np.asarray(faces, dtype=np.int64)\n    if positions.ndim != 2 or positions.shape[1] != 3 or not np.isfinite(positions).all():\n        raise ValueError("canonical GLB positions must be finite Nx3 values")\n    if triangles.ndim != 2 or triangles.shape[1] != 3 or len(triangles) == 0:\n        raise ValueError("canonical GLB requires triangle faces")\n    unique_positions, inverse = np.unique(positions, axis=0, return_inverse=True)\n    canonical_faces = inverse[triangles]\n    nondegenerate = (\n        (canonical_faces[:, 0] != canonical_faces[:, 1])\n        & (canonical_faces[:, 1] != canonical_faces[:, 2])\n        & (canonical_faces[:, 0] != canonical_faces[:, 2])\n    )\n    canonical_faces = canonical_faces[nondegenerate]\n    if len(canonical_faces) == 0:\n        raise ValueError("canonical GLB contains no non-degenerate triangles")\n    order = np.lexsort(\n        (canonical_faces[:, 2], canonical_faces[:, 1], canonical_faces[:, 0])\n    )\n    canonical_faces = canonical_faces[order]\n    return np.ascontiguousarray(unique_positions), np.ascontiguousarray(canonical_faces)\n''',
        '''def _canonical_mesh_arrays(\n    path: Path,\n) -> tuple[np.ndarray, np.ndarray, np.ndarray]:\n    """Flatten transforms and deduplicate deterministic position-colour vertices."""\n\n    vertices, faces, colors = _mesh_arrays(path)\n    positions = np.asarray(vertices, dtype="<f4")\n    triangles = np.asarray(faces, dtype=np.int64)\n    face_colors = np.asarray(colors, dtype="<f4")\n    if positions.ndim != 2 or positions.shape[1] != 3 or not np.isfinite(positions).all():\n        raise ValueError("canonical GLB positions must be finite Nx3 values")\n    if triangles.ndim != 2 or triangles.shape[1] != 3 or len(triangles) == 0:\n        raise ValueError("canonical GLB requires triangle faces")\n    if face_colors.shape != (len(triangles), 3) or not np.isfinite(face_colors).all():\n        raise ValueError("canonical GLB colors must be finite Mx3 values")\n\n    corner_positions = positions[triangles].reshape(-1, 3)\n    corner_colors = np.repeat(np.clip(face_colors, 0.0, 1.0), 3, axis=0)\n    position_color_rows = np.concatenate((corner_positions, corner_colors), axis=1)\n    unique_rows, inverse = np.unique(position_color_rows, axis=0, return_inverse=True)\n    canonical_positions = np.asarray(unique_rows[:, :3], dtype="<f4")\n    canonical_colors = np.asarray(unique_rows[:, 3:], dtype="<f4")\n    canonical_faces = inverse.reshape(-1, 3)\n\n    face_positions = canonical_positions[canonical_faces]\n    double_areas = np.linalg.norm(\n        np.cross(\n            face_positions[:, 1] - face_positions[:, 0],\n            face_positions[:, 2] - face_positions[:, 0],\n        ),\n        axis=1,\n    )\n    nondegenerate = np.isfinite(double_areas) & (double_areas > 1e-12)\n    canonical_faces = canonical_faces[nondegenerate]\n    if len(canonical_faces) == 0:\n        raise ValueError("canonical GLB contains no non-degenerate triangles")\n    order = np.lexsort(\n        (canonical_faces[:, 2], canonical_faces[:, 1], canonical_faces[:, 0])\n    )\n    canonical_faces = canonical_faces[order]\n    return (\n        np.ascontiguousarray(canonical_positions),\n        np.ascontiguousarray(canonical_faces),\n        np.ascontiguousarray(canonical_colors),\n    )\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''    positions, faces = _canonical_mesh_arrays(source)\n    if len(positions) > 2_000_000 or faces.size > 6_000_000:\n        raise ValueError("canonical GLB exceeds Aura mesh importer element ceilings")\n\n    index_dtype = "<u2" if len(positions) <= 65_535 else "<u4"\n    component_type = 5123 if index_dtype == "<u2" else 5125\n    indices = np.ascontiguousarray(faces.reshape(-1), dtype=index_dtype)\n    position_bytes = positions.tobytes(order="C")\n    index_bytes = indices.tobytes(order="C")\n    binary_payload = position_bytes + index_bytes\n''',
        '''    positions, faces, vertex_colors = _canonical_mesh_arrays(source)\n    if len(positions) > 2_000_000 or faces.size > 6_000_000:\n        raise ValueError("canonical GLB exceeds Aura mesh importer element ceilings")\n\n    index_dtype = "<u2" if len(positions) <= 65_535 else "<u4"\n    component_type = 5123 if index_dtype == "<u2" else 5125\n    indices = np.ascontiguousarray(faces.reshape(-1), dtype=index_dtype)\n    position_bytes = positions.tobytes(order="C")\n    color_bytes = vertex_colors.tobytes(order="C")\n    index_bytes = indices.tobytes(order="C")\n    if 28 + len(position_bytes) + len(color_bytes) + len(index_bytes) > MAX_GLTF_SOURCE_BYTES:\n        raise ValueError("canonical GLB exceeds Aura mesh importer source-byte ceiling")\n    binary_payload = position_bytes + color_bytes + index_bytes\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''            {\n                "buffer": 0,\n                "byteOffset": len(position_bytes),\n                "byteLength": len(index_bytes),\n                "target": 34963,\n            },\n''',
        '''            {\n                "buffer": 0,\n                "byteOffset": len(position_bytes),\n                "byteLength": len(color_bytes),\n                "target": 34962,\n            },\n            {\n                "buffer": 0,\n                "byteOffset": len(position_bytes) + len(color_bytes),\n                "byteLength": len(index_bytes),\n                "target": 34963,\n            },\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''            {\n                "bufferView": 1,\n                "byteOffset": 0,\n                "componentType": component_type,\n                "count": len(indices),\n                "type": "SCALAR",\n            },\n''',
        '''            {\n                "bufferView": 1,\n                "byteOffset": 0,\n                "componentType": 5126,\n                "count": len(vertex_colors),\n                "type": "VEC3",\n                "min": [float(item) for item in vertex_colors.min(axis=0)],\n                "max": [float(item) for item in vertex_colors.max(axis=0)],\n            },\n            {\n                "bufferView": 2,\n                "byteOffset": 0,\n                "componentType": component_type,\n                "count": len(indices),\n                "type": "SCALAR",\n            },\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''                        "attributes": {"POSITION": 0},\n                        "indices": 1,\n''',
        '''                        "attributes": {"POSITION": 0, "COLOR_0": 1},\n                        "indices": 2,\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''    encoded = struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body\n\n    descriptor, temporary_name = tempfile.mkstemp(\n''',
        '''    encoded = struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body\n    if len(encoded) > MAX_GLTF_SOURCE_BYTES:\n        raise ValueError("canonical GLB exceeds Aura mesh importer source-byte ceiling")\n\n    descriptor, temporary_name = tempfile.mkstemp(\n''',
    )

    replace_once(
        "scripts/aura_mesh_to_gaussian.py",
        '''        "index_component_type": component_type,\n        "bounds_min": [float(item) for item in positions.min(axis=0)],\n''',
        '''        "index_component_type": component_type,\n        "vertex_color_digest": _arrays_digest((vertex_colors,)),\n        "vertex_colors_preserved": True,\n        "bounds_min": [float(item) for item in positions.min(axis=0)],\n''',
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
