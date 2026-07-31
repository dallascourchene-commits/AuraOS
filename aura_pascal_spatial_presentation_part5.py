"""Registry and committed-fixture loader for the Pascal presentation organ."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from aura_pascal_spatial_presentation_part1 import (
    BridgeDirection,
    MAX_BRIDGE_DEPTH,
    MAX_BRIDGE_PAYLOAD_BYTES,
    MAX_RETAINED_NONCES,
    MAX_SESSION_MESSAGES,
    PASCAL_APPROVED_LOCK_DIGEST,
    PASCAL_COMMIT,
    PASCAL_COORDINATE_RECEIPT_VERSION,
    PASCAL_LICENSE,
    PASCAL_PRESENTATION_BRIDGE_VERSION,
    PASCAL_PRESENTATION_SESSION_VERSION,
    PASCAL_PRESENTATION_WFST_VERSION,
    PASCAL_REPOSITORY,
    PASCAL_SCENE_ARTIFACT_VERSION,
    PASCAL_SOURCE_LOCK_VERSION,
    PascalBridgeAction,
    PascalPackagePin,
    PascalPresentationError,
    PascalPresentationState,
    PascalSourceLock,
    bridge_sha256,
    canonical_json,
    sha256_digest,
)
from aura_pascal_spatial_presentation_part2 import (
    AuraPascalBridgeMessage,
    AuraPascalCoordinateReceipt,
    PascalNodeBinding,
    PascalSceneArtifactManifest,
)
from aura_pascal_spatial_presentation_part4 import PascalPresentationSession


class PascalPresentationRegistry:
    """Bounded registry for disposable presentation sessions."""

    def __init__(
        self,
        *,
        manifest: PascalSceneArtifactManifest,
        coordinate_receipt: AuraPascalCoordinateReceipt,
        max_sessions: int = 8,
    ) -> None:
        self.manifest = manifest
        self.coordinate_receipt = coordinate_receipt
        self.max_sessions = max(1, min(int(max_sessions), 32))
        self._sessions: OrderedDict[str, PascalPresentationSession] = OrderedDict()

    def create(
        self,
        *,
        spatial_scene_digest: str,
        render_plan_digest: str,
        expected_origin: str,
    ) -> PascalPresentationSession:
        if len(self._sessions) >= self.max_sessions:
            complete = [
                key
                for key, retained in self._sessions.items()
                if retained.status()["dissolution_complete"] is True
            ]
            if not complete:
                raise PascalPresentationError(
                    "active or incompletely dissolved Pascal presentation session ceiling reached"
                )
            self._sessions.pop(complete[0])
        session = PascalPresentationSession(
            manifest=self.manifest,
            coordinate_receipt=self.coordinate_receipt,
            spatial_scene_digest=spatial_scene_digest,
            render_plan_digest=render_plan_digest,
            expected_origin=expected_origin,
        )
        self._sessions[session.session_id] = session
        self._sessions.move_to_end(session.session_id)
        return session

    def get(self, session_id: str) -> PascalPresentationSession:
        from aura_pascal_spatial_presentation_part1 import _identifier

        key = _identifier(session_id, "session_id")
        session = self._sessions.get(key)
        if session is None:
            raise PascalPresentationError(
                "Pascal presentation session is missing or expired"
            )
        self._sessions.move_to_end(key)
        return session

    def dissolve_all(self) -> None:
        self._sessions.clear()

    def status(self) -> dict[str, Any]:
        statuses = [item.status() for item in self._sessions.values()]
        return {
            "active_sessions": sum(
                row["state"] != PascalPresentationState.DISSOLVED.value
                for row in statuses
            ),
            "incomplete_dissolutions": sum(
                row["state"] == PascalPresentationState.DISSOLVED.value
                and row["dissolution_complete"] is not True
                for row in statuses
            ),
            "retained_sessions": len(self._sessions),
            "session_ceiling": self.max_sessions,
            "pascal_artifact_digest": self.manifest.artifact_digest,
            "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            "automatic_execution": False,
        }


def _load_json_object(path: Path, name: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PascalPresentationError(f"{name} must be readable UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise PascalPresentationError(f"{name} must be a JSON object")
    return value


def load_pascal_compatibility_fixture(
    root: str,
) -> tuple[
    PascalSourceLock,
    PascalSceneArtifactManifest,
    AuraPascalCoordinateReceipt,
    dict[str, Any],
]:
    """Load and verify the exact committed lock, scene, artifact, and coordinate packet."""
    base = Path(root).resolve()
    lock_path = base / "third_party/pascal/pascal-lock.json"
    workbench = base / "aura_showcase/pascal-workbench"
    scene_path = workbench / "fixture.json"
    manifest_path = workbench / "artifact-manifest.json"
    coordinate_path = workbench / "coordinate-receipt.json"

    for path in (lock_path, scene_path, manifest_path, coordinate_path):
        if not path.is_file() or path.is_symlink():
            raise PascalPresentationError(
                f"required Pascal fixture asset is unavailable: {path}"
            )

    lock = PascalSourceLock.from_mapping(
        _load_json_object(lock_path, "Pascal source lock")
    )
    if lock.lock_digest != PASCAL_APPROVED_LOCK_DIGEST:
        raise PascalPresentationError(
            "Pascal source lock does not match the trusted runtime digest"
        )

    for relative, expected in lock.local_assets:
        unresolved = base / relative
        if unresolved.is_symlink():
            raise PascalPresentationError(
                f"locked Pascal asset is a symlink: {relative}"
            )
        candidate = unresolved.resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise PascalPresentationError(
                f"locked Pascal asset escapes the repository root: {relative}"
            ) from exc
        if not candidate.is_file():
            raise PascalPresentationError(
                f"locked Pascal asset is unavailable: {relative}"
            )
        if sha256_digest(candidate.read_bytes()) != expected:
            raise PascalPresentationError(
                f"locked Pascal asset digest mismatch: {relative}"
            )

    scene = _load_json_object(scene_path, "Pascal fixture scene")
    manifest = PascalSceneArtifactManifest.from_mapping(
        _load_json_object(manifest_path, "Pascal artifact manifest")
    )
    coordinate = AuraPascalCoordinateReceipt.from_mapping(
        _load_json_object(coordinate_path, "Pascal coordinate receipt")
    )
    if manifest.package_lock_digest != lock.lock_digest:
        raise PascalPresentationError(
            "Pascal artifact does not bind the exact source lock"
        )
    if manifest.scene_json_sha256 != sha256_digest(scene_path.read_bytes()):
        raise PascalPresentationError(
            "Pascal artifact scene digest does not match fixture bytes"
        )
    if coordinate.node_mapping_digest != sha256_digest(
        [asdict(item) for item in manifest.node_bindings]
    ):
        raise PascalPresentationError(
            "coordinate receipt node mapping digest is invalid"
        )
    if coordinate.pascal_artifact_digest != manifest.artifact_digest:
        raise PascalPresentationError(
            "coordinate receipt pascal_artifact_digest does not match manifest artifact_digest"
        )
    return lock, manifest, coordinate, scene


__all__ = [
    "AuraPascalBridgeMessage",
    "AuraPascalCoordinateReceipt",
    "BridgeDirection",
    "MAX_BRIDGE_DEPTH",
    "MAX_BRIDGE_PAYLOAD_BYTES",
    "MAX_RETAINED_NONCES",
    "MAX_SESSION_MESSAGES",
    "PASCAL_APPROVED_LOCK_DIGEST",
    "PASCAL_COMMIT",
    "PASCAL_COORDINATE_RECEIPT_VERSION",
    "PASCAL_LICENSE",
    "PASCAL_PRESENTATION_BRIDGE_VERSION",
    "PASCAL_PRESENTATION_SESSION_VERSION",
    "PASCAL_PRESENTATION_WFST_VERSION",
    "PASCAL_REPOSITORY",
    "PASCAL_SCENE_ARTIFACT_VERSION",
    "PASCAL_SOURCE_LOCK_VERSION",
    "PascalBridgeAction",
    "PascalNodeBinding",
    "PascalPackagePin",
    "PascalPresentationError",
    "PascalPresentationRegistry",
    "PascalPresentationSession",
    "PascalPresentationState",
    "PascalSceneArtifactManifest",
    "PascalSourceLock",
    "bridge_sha256",
    "canonical_json",
    "load_pascal_compatibility_fixture",
    "sha256_digest",
]
