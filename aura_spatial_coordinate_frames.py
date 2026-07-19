"""Deterministic coordinate-frame validation and transform resolution."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable

from aura_event_contracts import stable_digest
from aura_spatial_contracts import CoordinateFrame, SpatialSceneSnapshot

COORDINATE_FRAME_VERSION = "AURA_SPATIAL_COORDINATE_FRAMES_V1"


@dataclass(frozen=True)
class ResolvedTransform:
    frame_id: str
    translation: tuple[float, float, float]
    rotation_xyzw: tuple[float, float, float, float]
    scale: tuple[float, float, float]
    chain: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "translation": list(self.translation),
            "rotation_xyzw": list(self.rotation_xyzw),
            "scale": list(self.scale),
            "chain": list(self.chain),
            "version": COORDINATE_FRAME_VERSION,
        }


@dataclass(frozen=True)
class CoordinateFrameValidationReport:
    ok: bool
    root_frame_id: str
    frame_count: int
    ordered_frame_ids: tuple[str, ...]
    findings: tuple[dict[str, Any], ...]
    registry_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "root_frame_id": self.root_frame_id,
            "frame_count": self.frame_count,
            "ordered_frame_ids": list(self.ordered_frame_ids),
            "findings": [dict(item) for item in self.findings],
            "registry_digest": self.registry_digest,
            "version": COORDINATE_FRAME_VERSION,
        }


def validate_coordinate_frames(
    frames: Iterable[CoordinateFrame],
    *,
    root_frame_id: str,
) -> CoordinateFrameValidationReport:
    frame_list = tuple(frames)
    findings: list[dict[str, Any]] = []
    by_id: dict[str, CoordinateFrame] = {}
    for frame in frame_list:
        if not isinstance(frame, CoordinateFrame):
            raise ValueError("frames must contain CoordinateFrame records")
        if frame.frame_id in by_id:
            findings.append(
                _finding(
                    "DUPLICATE_FRAME_ID",
                    frame.frame_id,
                    "frame identifier is duplicated",
                )
            )
        else:
            by_id[frame.frame_id] = frame

    if root_frame_id not in by_id:
        findings.append(
            _finding(
                "ROOT_FRAME_MISSING",
                root_frame_id,
                "declared root frame is absent",
            )
        )
    elif by_id[root_frame_id].parent_frame_id is not None:
        findings.append(
            _finding(
                "ROOT_FRAME_HAS_PARENT",
                root_frame_id,
                "declared root frame must not have a parent",
            )
        )

    for frame in by_id.values():
        parent_id = frame.parent_frame_id
        if parent_id is not None and parent_id not in by_id:
            findings.append(
                _finding(
                    "MISSING_PARENT_FRAME",
                    frame.frame_id,
                    f"parent frame {parent_id!r} is absent",
                )
            )
        elif parent_id is not None:
            parent = by_id[parent_id]
            if frame.handedness != parent.handedness or frame.up_axis != parent.up_axis:
                findings.append(
                    _finding(
                        "FRAME_BASIS_CONVERSION_UNSUPPORTED",
                        frame.frame_id,
                        (
                            "mixed handedness or up-axis requires an explicit "
                            "conversion transform"
                        ),
                    )
                )

    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(frame_id: str, path: tuple[str, ...]) -> None:
        if frame_id in visited:
            return
        if frame_id in visiting:
            cycle_start = path.index(frame_id) if frame_id in path else 0
            cycle = (*path[cycle_start:], frame_id)
            findings.append(
                _finding(
                    "FRAME_CYCLE",
                    frame_id,
                    "coordinate frame cycle detected",
                    cycle=list(cycle),
                )
            )
            return
        visiting.add(frame_id)
        frame = by_id[frame_id]
        parent = frame.parent_frame_id
        if parent is not None and parent in by_id:
            visit(parent, (*path, frame_id))
        visiting.discard(frame_id)
        if frame_id not in visited:
            visited.add(frame_id)
            ordered.append(frame_id)

    for frame_id in sorted(by_id):
        visit(frame_id, ())

    if root_frame_id in by_id:
        rooted: set[str] = set()
        for frame_id in by_id:
            cursor = frame_id
            seen: set[str] = set()
            while cursor in by_id and cursor not in seen:
                seen.add(cursor)
                if cursor == root_frame_id:
                    rooted.add(frame_id)
                    break
                parent = by_id[cursor].parent_frame_id
                if parent is None:
                    break
                cursor = parent
        for frame_id in sorted(set(by_id) - rooted):
            findings.append(
                _finding(
                    "FRAME_NOT_ROOTED",
                    frame_id,
                    "frame does not resolve to the declared root",
                )
            )

    findings = _dedupe_findings(findings)
    digest = stable_digest(
        {
            "root_frame_id": root_frame_id,
            "frames": [by_id[key].to_dict() for key in sorted(by_id)],
        },
        digest_size=32,
    )
    return CoordinateFrameValidationReport(
        ok=not findings,
        root_frame_id=root_frame_id,
        frame_count=len(frame_list),
        ordered_frame_ids=tuple(ordered),
        findings=tuple(findings),
        registry_digest=digest,
    )


def require_valid_coordinate_frames(
    frames: Iterable[CoordinateFrame],
    *,
    root_frame_id: str,
) -> CoordinateFrameValidationReport:
    report = validate_coordinate_frames(frames, root_frame_id=root_frame_id)
    if not report.ok:
        codes = ", ".join(str(item["code"]) for item in report.findings)
        raise ValueError(f"invalid coordinate frame graph: {codes}")
    return report


def resolve_world_transform(
    frames: Iterable[CoordinateFrame],
    *,
    root_frame_id: str,
    frame_id: str,
) -> ResolvedTransform:
    frame_list = tuple(frames)
    require_valid_coordinate_frames(frame_list, root_frame_id=root_frame_id)
    by_id = {frame.frame_id: frame for frame in frame_list}
    if frame_id not in by_id:
        raise KeyError(f"unknown coordinate frame: {frame_id}")

    chain: list[CoordinateFrame] = []
    cursor: CoordinateFrame | None = by_id[frame_id]
    while cursor is not None:
        chain.append(cursor)
        cursor = by_id.get(cursor.parent_frame_id) if cursor.parent_frame_id else None
    chain.reverse()

    translation = (0.0, 0.0, 0.0)
    rotation = (0.0, 0.0, 0.0, 1.0)
    scale = (1.0, 1.0, 1.0)
    chain_ids: list[str] = []
    for frame in chain:
        chain_ids.append(frame.frame_id)
        local_translation = tuple(
            item * frame.unit_scale_meters for item in frame.translation
        )
        scaled_local = tuple(
            local_translation[index] * scale[index] for index in range(3)
        )
        rotated_local = _rotate_vector(rotation, scaled_local)
        translation = tuple(
            translation[index] + rotated_local[index] for index in range(3)
        )
        rotation = _normalize_quaternion(
            _multiply_quaternion(rotation, frame.rotation_xyzw)
        )
        local_scale = tuple(
            frame.scale[index] * frame.unit_scale_meters for index in range(3)
        )
        scale = tuple(scale[index] * local_scale[index] for index in range(3))

    if not all(math.isfinite(item) for item in (*translation, *rotation, *scale)):
        raise ValueError("resolved world transform contains non-finite values")
    return ResolvedTransform(
        frame_id=frame_id,
        translation=translation,
        rotation_xyzw=rotation,
        scale=scale,
        chain=tuple(chain_ids),
    )


def validate_scene_coordinate_frames(
    scene: SpatialSceneSnapshot,
) -> CoordinateFrameValidationReport:
    if not isinstance(scene, SpatialSceneSnapshot):
        raise ValueError("scene must be a SpatialSceneSnapshot")
    return validate_coordinate_frames(scene.frames, root_frame_id=scene.root_frame_id)


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (
            str(finding["code"]),
            str(finding["subject_id"]),
            str(finding["message"]),
        )
        unique[key] = finding
    return [unique[key] for key in sorted(unique)]


def _finding(
    code: str,
    subject_id: str,
    message: str,
    **details: Any,
) -> dict[str, Any]:
    return {
        "code": code,
        "subject_id": subject_id,
        "message": message,
        "blocking": True,
        "details": details,
    }


def _multiply_quaternion(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return (
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    )


def _normalize_quaternion(
    value: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    norm = math.sqrt(sum(item * item for item in value))
    if norm <= 1e-12:
        raise ValueError("cannot normalize zero quaternion")
    result = tuple(item / norm for item in value)
    return (result[0], result[1], result[2], result[3])


def _rotate_vector(
    quaternion: tuple[float, float, float, float],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    qx, qy, qz, qw = quaternion
    vx, vy, vz = vector
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    return (
        vx + qw * tx + (qy * tz - qz * ty),
        vy + qw * ty + (qz * tx - qx * tz),
        vz + qw * tz + (qx * ty - qy * tx),
    )


__all__ = [
    "COORDINATE_FRAME_VERSION",
    "CoordinateFrameValidationReport",
    "ResolvedTransform",
    "require_valid_coordinate_frames",
    "resolve_world_transform",
    "validate_coordinate_frames",
    "validate_scene_coordinate_frames",
]
