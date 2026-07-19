"""Immutable scene compilation and verification for Aura's spatial substrate."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
import re
from typing import Any, TypeVar

from aura_event_contracts import stable_digest
from aura_spatial_asset_registry import SpatialAssetRegistry
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialEntity,
    SpatialLink,
    SpatialSceneSnapshot,
)
from aura_spatial_coordinate_frames import validate_coordinate_frames

SPATIAL_SCENE_COMPILER_VERSION = "AURA_SPATIAL_SCENE_COMPILER_V1"
_AUTHORITY_KEYS = frozenset(
    {
        "approval",
        "authorization",
        "authority_decision",
        "automatic_commit",
        "automatic_fix",
        "automatic_merge",
        "automatic_pull_request",
        "automatic_push",
        "capability_lease",
        "execution_authority",
        "lease",
        "lease_id",
        "merge",
        "patch_authority",
        "production_mutation",
        "promotion",
        "render_authority",
        "renderer_authority",
        "renderer_input_is_authority",
        "verifier_receipt",
        "vsa_patch_authority",
    }
)
_RecordT = TypeVar("_RecordT")


@dataclass(frozen=True)
class SpatialSceneVerificationReport:
    ok: bool
    scene_id: str
    scene_digest: str
    findings: tuple[dict[str, Any], ...]
    frame_registry_digest: str
    asset_registry_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "scene_id": self.scene_id,
            "scene_digest": self.scene_digest,
            "findings": [dict(item) for item in self.findings],
            "frame_registry_digest": self.frame_registry_digest,
            "asset_registry_digest": self.asset_registry_digest,
            "version": SPATIAL_SCENE_COMPILER_VERSION,
            "execution_authority": False,
            "patch_authority": False,
        }


def compile_spatial_scene(
    *,
    scene_id: str,
    purpose_digest: str,
    root_frame_id: str,
    frames: Iterable[CoordinateFrame],
    assets: Iterable[SpatialAssetManifest] = (),
    entities: Iterable[SpatialEntity] = (),
    links: Iterable[SpatialLink] = (),
    source_refs: Iterable[str] = (),
    renderer_hints: Mapping[str, Any] | None = None,
) -> SpatialSceneSnapshot:
    """Compile a canonical snapshot after sorting all set-like records."""
    if renderer_hints is not None and not isinstance(renderer_hints, Mapping):
        raise ValueError("renderer_hints must be an object")

    frame_records = _typed_records(frames, CoordinateFrame, "frames")
    asset_records = _typed_records(assets, SpatialAssetManifest, "assets")
    entity_records = _typed_records(entities, SpatialEntity, "entities")
    link_records = _typed_records(links, SpatialLink, "links")

    frame_tuple = tuple(
        sorted(
            (
                replace(
                    item,
                    source_refs=tuple(sorted(set(item.source_refs))),
                )
                for item in frame_records
            ),
            key=lambda item: item.frame_id,
        )
    )
    asset_tuple = tuple(
        sorted(
            (
                replace(
                    item,
                    source_refs=tuple(sorted(set(item.source_refs))),
                )
                for item in asset_records
            ),
            key=lambda item: item.asset_id,
        )
    )
    entity_tuple = tuple(
        sorted(
            (
                replace(
                    item,
                    asset_ids=tuple(sorted(set(item.asset_ids))),
                    source_refs=tuple(sorted(set(item.source_refs))),
                )
                for item in entity_records
            ),
            key=lambda item: item.entity_id,
        )
    )
    link_tuple = tuple(
        sorted(
            (
                replace(
                    item,
                    source_refs=tuple(sorted(set(item.source_refs))),
                )
                for item in link_records
            ),
            key=lambda item: item.link_id,
        )
    )
    refs = tuple(
        sorted(
            {
                str(item).strip()
                for item in source_refs
                if str(item).strip()
            }
        )
    )
    scene = SpatialSceneSnapshot(
        scene_id=scene_id,
        purpose_digest=purpose_digest,
        root_frame_id=root_frame_id,
        frames=frame_tuple,
        assets=asset_tuple,
        entities=entity_tuple,
        links=link_tuple,
        source_refs=refs,
        renderer_hints=dict(renderer_hints or {}),
    )
    report = verify_spatial_scene(scene)
    if not report.ok:
        codes = ", ".join(str(item["code"]) for item in report.findings)
        raise ValueError(f"spatial scene verification failed: {codes}")
    return scene


def verify_spatial_scene(
    scene: SpatialSceneSnapshot,
) -> SpatialSceneVerificationReport:
    if not isinstance(scene, SpatialSceneSnapshot):
        raise ValueError("scene must be a SpatialSceneSnapshot")
    findings: list[dict[str, Any]] = []

    frame_report = validate_coordinate_frames(
        scene.frames,
        root_frame_id=scene.root_frame_id,
    )
    findings.extend(frame_report.findings)
    frame_ids = {frame.frame_id for frame in scene.frames}

    try:
        asset_registry = SpatialAssetRegistry(scene.assets)
        asset_registry_digest = asset_registry.registry_digest
    except ValueError as exc:
        findings.append(
            _finding(
                "INVALID_ASSET_REGISTRY",
                scene.scene_id,
                str(exc),
            )
        )
        asset_registry_digest = SpatialAssetRegistry().registry_digest
    asset_ids = {asset.asset_id for asset in scene.assets}

    entity_ids: set[str] = set()
    for entity in scene.entities:
        if entity.entity_id in entity_ids:
            findings.append(
                _finding(
                    "DUPLICATE_ENTITY_ID",
                    entity.entity_id,
                    "entity identifier is duplicated",
                )
            )
        entity_ids.add(entity.entity_id)
        if entity.frame_id not in frame_ids:
            findings.append(
                _finding(
                    "ENTITY_FRAME_MISSING",
                    entity.entity_id,
                    f"entity references missing frame {entity.frame_id!r}",
                )
            )
        for asset_id in entity.asset_ids:
            if asset_id not in asset_ids:
                findings.append(
                    _finding(
                        "ENTITY_ASSET_MISSING",
                        entity.entity_id,
                        f"entity references missing asset {asset_id!r}",
                    )
                )
        _collect_authority_findings(
            entity.to_dict().get("metadata", {}),
            f"entity:{entity.entity_id}.metadata",
            findings,
        )

    for asset in scene.assets:
        if asset.frame_id not in frame_ids:
            findings.append(
                _finding(
                    "ASSET_FRAME_MISSING",
                    asset.asset_id,
                    f"asset references missing frame {asset.frame_id!r}",
                )
            )
        _collect_authority_findings(
            asset.to_dict().get("metadata", {}),
            f"asset:{asset.asset_id}.metadata",
            findings,
        )

    link_ids: set[str] = set()
    for link in scene.links:
        if link.link_id in link_ids:
            findings.append(
                _finding(
                    "DUPLICATE_LINK_ID",
                    link.link_id,
                    "link identifier is duplicated",
                )
            )
        link_ids.add(link.link_id)
        if link.source_entity_id not in entity_ids:
            findings.append(
                _finding(
                    "LINK_SOURCE_MISSING",
                    link.link_id,
                    f"source entity {link.source_entity_id!r} is absent",
                )
            )
        if link.target_entity_id not in entity_ids:
            findings.append(
                _finding(
                    "LINK_TARGET_MISSING",
                    link.link_id,
                    f"target entity {link.target_entity_id!r} is absent",
                )
            )
        _collect_authority_findings(
            link.to_dict().get("metadata", {}),
            f"link:{link.link_id}.metadata",
            findings,
        )

    _collect_authority_findings(
        scene.to_dict().get("renderer_hints", {}),
        "scene.renderer_hints",
        findings,
    )
    findings = _dedupe_findings(findings)
    return SpatialSceneVerificationReport(
        ok=not findings,
        scene_id=scene.scene_id,
        scene_digest=scene.scene_digest,
        findings=tuple(findings),
        frame_registry_digest=frame_report.registry_digest,
        asset_registry_digest=asset_registry_digest,
    )


def scene_summary(scene: SpatialSceneSnapshot) -> dict[str, Any]:
    report = verify_spatial_scene(scene)
    return {
        "ok": report.ok,
        "scene_id": scene.scene_id,
        "scene_digest": scene.scene_digest,
        "frame_count": len(scene.frames),
        "asset_count": len(scene.assets),
        "entity_count": len(scene.entities),
        "link_count": len(scene.links),
        "truth_policy": scene.truth_policy,
        "patch_authority": scene.patch_authority,
        "vsa_patch_authority": scene.vsa_patch_authority,
        "execution_authority": scene.execution_authority,
        "source_digest": stable_digest(
            sorted(scene.source_refs),
            digest_size=32,
        ),
        "verification": report.to_dict(),
        "version": SPATIAL_SCENE_COMPILER_VERSION,
    }


def _typed_records(
    values: Iterable[_RecordT],
    expected_type: type[_RecordT],
    field_name: str,
) -> tuple[_RecordT, ...]:
    if isinstance(values, (str, bytes, bytearray, Mapping)):
        raise ValueError(f"{field_name} must be an iterable of records")
    try:
        records = tuple(values)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be an iterable of records") from exc
    if not all(isinstance(item, expected_type) for item in records):
        raise ValueError(
            f"{field_name} must contain only {expected_type.__name__} records"
        )
    return records


def _normalize_metadata_key(value: Any) -> str:
    text = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])",
        "_",
        str(value).strip(),
    )
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _collect_authority_findings(
    value: Any,
    path: str,
    findings: list[dict[str, Any]],
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_metadata_key(key)
            child = f"{path}.{key}"
            if normalized in _AUTHORITY_KEYS:
                findings.append(
                    _finding(
                        "AUTHORITY_METADATA_REJECTED",
                        child,
                        (
                            "spatial metadata cannot carry an authority "
                            "field, including a false-valued alias"
                        ),
                    )
                )
            _collect_authority_findings(item, child, findings)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            _collect_authority_findings(
                item,
                f"{path}[{index}]",
                findings,
            )


def _dedupe_findings(
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (
            str(finding.get("code")),
            str(finding.get("subject_id")),
            str(finding.get("message")),
        )
        unique[key] = finding
    return [unique[key] for key in sorted(unique)]


def _finding(
    code: str,
    subject_id: str,
    message: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "subject_id": subject_id,
        "message": message,
        "blocking": True,
    }


__all__ = [
    "SPATIAL_SCENE_COMPILER_VERSION",
    "SpatialSceneVerificationReport",
    "compile_spatial_scene",
    "scene_summary",
    "verify_spatial_scene",
]
