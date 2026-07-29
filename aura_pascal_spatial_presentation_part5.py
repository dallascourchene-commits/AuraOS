import aura_pascal_spatial_presentation_part1 as _p1
from aura_pascal_spatial_presentation_part1 import *  # noqa: F403
import aura_pascal_spatial_presentation_part2 as _p2
from aura_pascal_spatial_presentation_part2 import *  # noqa: F403
import aura_pascal_spatial_presentation_part3 as _p3
from aura_pascal_spatial_presentation_part3 import *  # noqa: F403
import aura_pascal_spatial_presentation_part4 as _p4
from aura_pascal_spatial_presentation_part4 import *  # noqa: F403

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
        session = PascalPresentationSession(
            manifest=self.manifest,
            coordinate_receipt=self.coordinate_receipt,
            spatial_scene_digest=spatial_scene_digest,
            render_plan_digest=render_plan_digest,
            expected_origin=expected_origin,
        )
        if len(self._sessions) >= self.max_sessions:
            dissolved = [
                key
                for key, retained in self._sessions.items()
                if retained.state is PascalPresentationState.DISSOLVED
            ]
            if not dissolved:
                raise PascalPresentationError("active Pascal presentation session ceiling reached")
            self._sessions.pop(dissolved[0])
        self._sessions[session.session_id] = session
        self._sessions.move_to_end(session.session_id)
        return session

    def get(self, session_id: str) -> PascalPresentationSession:
        key = _identifier(session_id, "session_id")
        session = self._sessions.get(key)
        if session is None:
            raise PascalPresentationError("Pascal presentation session is missing or expired")
        self._sessions.move_to_end(key)
        return session

    def dissolve_all(self) -> None:
        self._sessions.clear()

    def status(self) -> dict[str, Any]:
        return {
            "active_sessions": sum(
                item.state is not PascalPresentationState.DISSOLVED for item in self._sessions.values()
            ),
            "retained_sessions": len(self._sessions),
            "session_ceiling": self.max_sessions,
            "pascal_artifact_digest": self.manifest.artifact_digest,
            "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            "automatic_execution": False,
        }


def load_pascal_compatibility_fixture(
    root: str,
) -> tuple[PascalSourceLock, PascalSceneArtifactManifest, AuraPascalCoordinateReceipt, dict[str, Any]]:
    """Load and verify the exact committed lock, scene, artifact, and coordinate packet."""

    from pathlib import Path

    base = Path(root)
    lock_path = base / "third_party/pascal/pascal-lock.json"
    workbench = base / "aura_showcase/pascal-workbench"
    scene_path = workbench / "fixture.json"
    manifest_path = workbench / "artifact-manifest.json"
    coordinate_path = workbench / "coordinate-receipt.json"
    for path in (lock_path, scene_path, manifest_path, coordinate_path):
        if not path.is_file() or path.is_symlink():
            raise PascalPresentationError(f"required Pascal fixture asset is unavailable: {path}")
    lock = PascalSourceLock.from_mapping(json.loads(lock_path.read_text(encoding="utf-8")))
    for relative, expected in lock.local_assets:
        path = base / relative
        if not path.is_file() or path.is_symlink():
            raise PascalPresentationError(f"locked Pascal asset is unavailable: {relative}")
        if _sha256(path.read_bytes()) != expected:
            raise PascalPresentationError(f"locked Pascal asset digest mismatch: {relative}")
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    if not isinstance(scene, dict):
        raise PascalPresentationError("Pascal fixture scene must be a JSON object")
    manifest = PascalSceneArtifactManifest.from_mapping(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    coordinate = AuraPascalCoordinateReceipt.from_mapping(
        json.loads(coordinate_path.read_text(encoding="utf-8"))
    )
    if manifest.package_lock_digest != lock.lock_digest:
        raise PascalPresentationError("Pascal artifact does not bind the exact source lock")
    if manifest.scene_json_sha256 != _sha256(scene_path.read_bytes()):
        raise PascalPresentationError("Pascal artifact scene digest does not match fixture bytes")
    if coordinate.node_mapping_digest != _sha256(
        [asdict(item) for item in manifest.node_bindings]
    ):
        raise PascalPresentationError("coordinate receipt node mapping digest is invalid")
    return lock, manifest, coordinate, scene


__all__ = [
    "AuraPascalBridgeMessage",
    "AuraPascalCoordinateReceipt",
    "BridgeDirection",
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
    "load_pascal_compatibility_fixture",
]

__all__ = _p1.__all__ + _p2.__all__ + _p3.__all__ + _p4.__all__ + ['PascalPresentationRegistry', '__all__', 'load_pascal_compatibility_fixture']
