import aura_pascal_spatial_presentation_part1 as _p1
from aura_pascal_spatial_presentation_part1 import *  # noqa: F403

@dataclass(frozen=True)
class PascalNodeBinding:
    node_id: str
    node_kind: str
    aura_entity_id: str
    aura_target_ref: str
    storey_id: str
    selectable: bool = True

    def __post_init__(self) -> None:
        for name in ("node_id", "node_kind", "aura_entity_id", "storey_id"):
            object.__setattr__(self, name, _identifier(getattr(self, name), f"node_binding.{name}"))
        object.__setattr__(
            self,
            "aura_target_ref",
            _required_text(self.aura_target_ref, "node_binding.aura_target_ref", maximum=2048),
        )
        if type(self.selectable) is not bool:
            raise PascalPresentationError("node_binding.selectable must be a boolean")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PascalNodeBinding":
        _strict_keys(value, {field.name for field in fields(cls)}, "PascalNodeBinding")
        return cls(**dict(value))


@dataclass(frozen=True)
class PascalSceneArtifactManifest:
    artifact_id: str
    artifact_digest: str
    source_kind: str
    package_lock_digest: str
    scene_json_sha256: str
    root_node_id: str
    storey_ids: tuple[str, ...]
    node_bindings: tuple[PascalNodeBinding, ...]
    repository: str = PASCAL_REPOSITORY
    commit: str = PASCAL_COMMIT
    working_copy_only: bool = True
    persistent_scene_mutation: bool = False
    external_asset_fetch: bool = False
    destroy_on_dissolution: bool = True
    construction_truth: bool = False
    survey_authority: bool = False
    version: str = PASCAL_SCENE_ARTIFACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _identifier(self.artifact_id, "artifact_id"))
        if self.repository != PASCAL_REPOSITORY or self.commit != PASCAL_COMMIT:
            raise PascalPresentationError("artifact must bind the exact approved Pascal source")
        if self.source_kind not in {"PASCAL_BUILD_JSON", "IFC_CONVERTED", "SYNTHETIC_FIXTURE"}:
            raise PascalPresentationError("unsupported Pascal artifact source_kind")
        object.__setattr__(self, "package_lock_digest", _hex64(self.package_lock_digest, "package_lock_digest"))
        object.__setattr__(self, "scene_json_sha256", _hex64(self.scene_json_sha256, "scene_json_sha256"))
        object.__setattr__(self, "root_node_id", _identifier(self.root_node_id, "root_node_id"))
        storeys = tuple(_identifier(item, "storey_ids[]") for item in self.storey_ids)
        if not storeys or len(storeys) != len(set(storeys)):
            raise PascalPresentationError("storey_ids must be unique and non-empty")
        object.__setattr__(self, "storey_ids", storeys)
        if not isinstance(self.node_bindings, tuple) or not self.node_bindings:
            raise PascalPresentationError("node_bindings must be a non-empty tuple")
        if not all(isinstance(item, PascalNodeBinding) for item in self.node_bindings):
            raise PascalPresentationError("node_bindings contains an invalid row")
        node_ids = [item.node_id for item in self.node_bindings]
        entity_ids = [item.aura_entity_id for item in self.node_bindings]
        if len(node_ids) != len(set(node_ids)) or len(entity_ids) != len(set(entity_ids)):
            raise PascalPresentationError("node and Aura entity mappings must be one-to-one")
        if self.root_node_id not in set(node_ids):
            raise PascalPresentationError("root_node_id is not present in node_bindings")
        unknown_storeys = sorted({item.storey_id for item in self.node_bindings} - set(storeys))
        if unknown_storeys:
            raise PascalPresentationError(f"node bindings reference unknown storeys: {unknown_storeys}")
        for name, expected in (
            ("working_copy_only", True),
            ("persistent_scene_mutation", False),
            ("external_asset_fetch", False),
            ("destroy_on_dissolution", True),
            ("construction_truth", False),
            ("survey_authority", False),
        ):
            _strict_bool(getattr(self, name), f"artifact.{name}", expected)
        if self.version != PASCAL_SCENE_ARTIFACT_VERSION:
            raise PascalPresentationError("unsupported Pascal artifact manifest version")
        supplied = _hex64(self.artifact_digest, "artifact_digest")
        expected = _sha256(self._body())
        if supplied != expected:
            raise PascalPresentationError("Pascal artifact digest is invalid")

    def _body(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "source_kind": self.source_kind,
            "package_lock_digest": self.package_lock_digest,
            "scene_json_sha256": self.scene_json_sha256,
            "root_node_id": self.root_node_id,
            "storey_ids": list(self.storey_ids),
            "node_bindings": [asdict(item) for item in self.node_bindings],
            "repository": self.repository,
            "commit": self.commit,
            "working_copy_only": self.working_copy_only,
            "persistent_scene_mutation": self.persistent_scene_mutation,
            "external_asset_fetch": self.external_asset_fetch,
            "destroy_on_dissolution": self.destroy_on_dissolution,
            "construction_truth": self.construction_truth,
            "survey_authority": self.survey_authority,
            "version": self.version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "artifact_digest": self.artifact_digest}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PascalSceneArtifactManifest":
        expected = {
            "artifact_id",
            "artifact_digest",
            "source_kind",
            "package_lock_digest",
            "scene_json_sha256",
            "root_node_id",
            "storey_ids",
            "node_bindings",
            "repository",
            "commit",
            "working_copy_only",
            "persistent_scene_mutation",
            "external_asset_fetch",
            "destroy_on_dissolution",
            "construction_truth",
            "survey_authority",
            "version",
        }
        _strict_keys(value, expected, "PascalSceneArtifactManifest")
        return cls(
            artifact_id=value["artifact_id"],
            artifact_digest=value["artifact_digest"],
            source_kind=value["source_kind"],
            package_lock_digest=value["package_lock_digest"],
            scene_json_sha256=value["scene_json_sha256"],
            root_node_id=value["root_node_id"],
            storey_ids=tuple(value["storey_ids"]),
            node_bindings=tuple(PascalNodeBinding.from_mapping(item) for item in value["node_bindings"]),
            repository=value["repository"],
            commit=value["commit"],
            working_copy_only=value["working_copy_only"],
            persistent_scene_mutation=value["persistent_scene_mutation"],
            external_asset_fetch=value["external_asset_fetch"],
            destroy_on_dissolution=value["destroy_on_dissolution"],
            construction_truth=value["construction_truth"],
            survey_authority=value["survey_authority"],
            version=value["version"],
        )

    def binding_for_node(self, node_id: str) -> PascalNodeBinding:
        selected = _identifier(node_id, "node_id")
        matches = [item for item in self.node_bindings if item.node_id == selected]
        if len(matches) != 1:
            raise PascalPresentationError("Pascal node is not admitted by the artifact manifest")
        return matches[0]

    def root_binding(self) -> PascalNodeBinding:
        return self.binding_for_node(self.root_node_id)


@dataclass(frozen=True)
class AuraPascalCoordinateReceipt:
    receipt_id: str
    receipt_digest: str
    pascal_artifact_digest: str
    spatial_scene_digest: str
    pascal_frame_id: str
    aura_frame_id: str
    transform_matrix: tuple[float, ...]
    source_unit_meters: float
    destination_unit_meters: float
    node_mapping_digest: str
    visual_alignment_only: bool = True
    verified: bool = True
    survey_authority: bool = False
    construction_truth: bool = False
    version: str = PASCAL_COORDINATE_RECEIPT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _identifier(self.receipt_id, "receipt_id"))
        for name in ("pascal_artifact_digest", "spatial_scene_digest", "node_mapping_digest"):
            object.__setattr__(self, name, _hex64(getattr(self, name), name))
        for name in ("pascal_frame_id", "aura_frame_id"):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        if len(self.transform_matrix) != 16:
            raise PascalPresentationError("transform_matrix must contain 16 values")
        matrix = tuple(float(item) for item in self.transform_matrix)
        if not all(math.isfinite(item) for item in matrix):
            raise PascalPresentationError("transform_matrix must contain finite values")
        object.__setattr__(self, "transform_matrix", matrix)
        for name in ("source_unit_meters", "destination_unit_meters"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0.0:
                raise PascalPresentationError(f"{name} must be positive and finite")
            object.__setattr__(self, name, value)
        for name, expected in (
            ("visual_alignment_only", True),
            ("verified", True),
            ("survey_authority", False),
            ("construction_truth", False),
        ):
            _strict_bool(getattr(self, name), f"coordinate_receipt.{name}", expected)
        if self.version != PASCAL_COORDINATE_RECEIPT_VERSION:
            raise PascalPresentationError("unsupported coordinate receipt version")
        supplied = _hex64(self.receipt_digest, "receipt_digest")
        if supplied != _sha256(self._body()):
            raise PascalPresentationError("coordinate receipt digest is invalid")

    def _body(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "pascal_artifact_digest": self.pascal_artifact_digest,
            "spatial_scene_digest": self.spatial_scene_digest,
            "pascal_frame_id": self.pascal_frame_id,
            "aura_frame_id": self.aura_frame_id,
            "transform_matrix": list(self.transform_matrix),
            "source_unit_meters": self.source_unit_meters,
            "destination_unit_meters": self.destination_unit_meters,
            "node_mapping_digest": self.node_mapping_digest,
            "visual_alignment_only": self.visual_alignment_only,
            "verified": self.verified,
            "survey_authority": self.survey_authority,
            "construction_truth": self.construction_truth,
            "version": self.version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "receipt_digest": self.receipt_digest}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AuraPascalCoordinateReceipt":
        expected = {
            "receipt_id",
            "receipt_digest",
            "pascal_artifact_digest",
            "spatial_scene_digest",
            "pascal_frame_id",
            "aura_frame_id",
            "transform_matrix",
            "source_unit_meters",
            "destination_unit_meters",
            "node_mapping_digest",
            "visual_alignment_only",
            "verified",
            "survey_authority",
            "construction_truth",
            "version",
        }
        _strict_keys(value, expected, "AuraPascalCoordinateReceipt")
        return cls(
            receipt_id=value["receipt_id"],
            receipt_digest=value["receipt_digest"],
            pascal_artifact_digest=value["pascal_artifact_digest"],
            spatial_scene_digest=value["spatial_scene_digest"],
            pascal_frame_id=value["pascal_frame_id"],
            aura_frame_id=value["aura_frame_id"],
            transform_matrix=tuple(value["transform_matrix"]),
            source_unit_meters=value["source_unit_meters"],
            destination_unit_meters=value["destination_unit_meters"],
            node_mapping_digest=value["node_mapping_digest"],
            visual_alignment_only=value["visual_alignment_only"],
            verified=value["verified"],
            survey_authority=value["survey_authority"],
            construction_truth=value["construction_truth"],
            version=value["version"],
        )


@dataclass(frozen=True)
class AuraPascalBridgeMessage:
    message_id: str
    session_id: str
    sequence: int
    nonce: str
    spatial_scene_digest: str
    render_plan_digest: str
    pascal_artifact_digest: str
    coordinate_receipt_digest: str
    state_binding_digest: str
    sent_at: str
    direction: BridgeDirection | str
    action: PascalBridgeAction | str
    payload: Mapping[str, Any]
    message_digest: str
    version: str = PASCAL_PRESENTATION_BRIDGE_VERSION

    def __post_init__(self) -> None:
        for name in ("message_id", "session_id", "nonce"):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        if type(self.sequence) is not int or not 1 <= self.sequence <= 2_147_483_647:
            raise PascalPresentationError("sequence must be an integer in 1..2147483647")
        for name in (
            "spatial_scene_digest",
            "render_plan_digest",
            "pascal_artifact_digest",
            "coordinate_receipt_digest",
            "state_binding_digest",
        ):
            object.__setattr__(self, name, _hex64(getattr(self, name), name))
        object.__setattr__(self, "sent_at", _timestamp(self.sent_at))
        try:
            direction = self.direction if isinstance(self.direction, BridgeDirection) else BridgeDirection(str(self.direction))
            action = self.action if isinstance(self.action, PascalBridgeAction) else PascalBridgeAction(str(self.action))
        except ValueError as exc:
            raise PascalPresentationError("unsupported bridge direction or action") from exc
        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "payload", _clean_payload(self.payload))
        if self.version != PASCAL_PRESENTATION_BRIDGE_VERSION:
            raise PascalPresentationError("unsupported Pascal presentation bridge version")
        supplied = _hex64(self.message_digest, "message_digest")
        if supplied != _sha256(self._body()):
            raise PascalPresentationError("bridge message digest is invalid")

    def _body(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "nonce": self.nonce,
            "spatial_scene_digest": self.spatial_scene_digest,
            "render_plan_digest": self.render_plan_digest,
            "pascal_artifact_digest": self.pascal_artifact_digest,
            "coordinate_receipt_digest": self.coordinate_receipt_digest,
            "state_binding_digest": self.state_binding_digest,
            "sent_at": self.sent_at,
            "direction": self.direction.value if isinstance(self.direction, BridgeDirection) else str(self.direction),
            "action": self.action.value if isinstance(self.action, PascalBridgeAction) else str(self.action),
            "payload": dict(self.payload),
            "version": self.version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "message_digest": self.message_digest}

    @classmethod
    def build(
        cls,
        *,
        session_id: str,
        sequence: int,
        spatial_scene_digest: str,
        render_plan_digest: str,
        pascal_artifact_digest: str,
        coordinate_receipt_digest: str,
        state_binding_digest: str,
        direction: BridgeDirection,
        action: PascalBridgeAction,
        payload: Mapping[str, Any],
        sent_at: str | None = None,
        nonce: str | None = None,
        message_id: str | None = None,
    ) -> "AuraPascalBridgeMessage":
        clean_payload = _clean_payload(payload)
        body = {
            "message_id": message_id or f"PBM-{secrets.token_hex(12)}",
            "session_id": session_id,
            "sequence": sequence,
            "nonce": nonce or f"N-{secrets.token_hex(12)}",
            "spatial_scene_digest": spatial_scene_digest,
            "render_plan_digest": render_plan_digest,
            "pascal_artifact_digest": pascal_artifact_digest,
            "coordinate_receipt_digest": coordinate_receipt_digest,
            "state_binding_digest": state_binding_digest,
            "sent_at": sent_at or _utc_timestamp(),
            "direction": direction.value,
            "action": action.value,
            "payload": clean_payload,
            "version": PASCAL_PRESENTATION_BRIDGE_VERSION,
        }
        return cls(**body, message_digest=_sha256(body))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AuraPascalBridgeMessage":
        expected = {
            "message_id",
            "session_id",
            "sequence",
            "nonce",
            "spatial_scene_digest",
            "render_plan_digest",
            "pascal_artifact_digest",
            "coordinate_receipt_digest",
            "state_binding_digest",
            "sent_at",
            "direction",
            "action",
            "payload",
            "message_digest",
            "version",
        }
        _strict_keys(value, expected, "AuraPascalBridgeMessage")
        return cls(**dict(value))


_PARENT_ACTIONS = frozenset(
    {
        PascalBridgeAction.LOAD_ARTIFACT,
        PascalBridgeAction.SET_VIEW_2D,
        PascalBridgeAction.SET_VIEW_3D,
        PascalBridgeAction.SET_STOREY,
        PascalBridgeAction.SET_SELECTION,
        PascalBridgeAction.SET_DIMENSIONS,
        PascalBridgeAction.RESET_CAMERA,
        PascalBridgeAction.DISSOLVE,
    }
)
_CHILD_ACTIONS = frozenset(
    {
        PascalBridgeAction.READY,
        PascalBridgeAction.LOAD_RECEIPT,
        PascalBridgeAction.VIEW_STATE,
        PascalBridgeAction.SELECTION_CHANGED,
        PascalBridgeAction.RENDER_RECEIPT,
        PascalBridgeAction.PRESENTATION_ERROR,
        PascalBridgeAction.DISSOLUTION_RECEIPT,
    }
)
_ACTION_STATE = {
    PascalBridgeAction.READY: ({PascalPresentationState.CREATED}, PascalPresentationState.READY),
    PascalBridgeAction.LOAD_ARTIFACT: ({PascalPresentationState.READY}, None),
    PascalBridgeAction.LOAD_RECEIPT: ({PascalPresentationState.READY}, PascalPresentationState.ACTIVE),
    PascalBridgeAction.SET_VIEW_2D: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.SET_VIEW_3D: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.SET_STOREY: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.SET_SELECTION: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.SET_DIMENSIONS: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.RESET_CAMERA: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.VIEW_STATE: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.SELECTION_CHANGED: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.RENDER_RECEIPT: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.PRESENTATION_ERROR: (
        {PascalPresentationState.READY, PascalPresentationState.ACTIVE},
        None,
    ),
    PascalBridgeAction.DISSOLVE: ({PascalPresentationState.ACTIVE}, None),
    PascalBridgeAction.DISSOLUTION_RECEIPT: (
        {PascalPresentationState.ACTIVE},
        PascalPresentationState.DISSOLVED,
    ),
}
_PENDING_RECEIPT_ACTION = {
    PascalBridgeAction.LOAD_ARTIFACT: PascalBridgeAction.LOAD_RECEIPT,
    PascalBridgeAction.SET_VIEW_2D: PascalBridgeAction.VIEW_STATE,
    PascalBridgeAction.SET_VIEW_3D: PascalBridgeAction.VIEW_STATE,
    PascalBridgeAction.SET_STOREY: PascalBridgeAction.VIEW_STATE,
    PascalBridgeAction.SET_SELECTION: PascalBridgeAction.SELECTION_CHANGED,
    PascalBridgeAction.SET_DIMENSIONS: PascalBridgeAction.VIEW_STATE,
    PascalBridgeAction.RESET_CAMERA: PascalBridgeAction.VIEW_STATE,
    PascalBridgeAction.DISSOLVE: PascalBridgeAction.DISSOLUTION_RECEIPT,
}
_SPATIAL_ACTION_MAP = {
    PascalBridgeAction.LOAD_ARTIFACT: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.SET_VIEW_2D: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.SET_VIEW_3D: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.SET_STOREY: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.SET_SELECTION: SpatialInteractionAction.SELECT,
    PascalBridgeAction.SET_DIMENSIONS: SpatialInteractionAction.EXPAND,
    PascalBridgeAction.RESET_CAMERA: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.DISSOLVE: SpatialInteractionAction.DESELECT,
    PascalBridgeAction.READY: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.LOAD_RECEIPT: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.VIEW_STATE: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.SELECTION_CHANGED: SpatialInteractionAction.SELECT,
    PascalBridgeAction.RENDER_RECEIPT: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.PRESENTATION_ERROR: SpatialInteractionAction.FOCUS,
    PascalBridgeAction.DISSOLUTION_RECEIPT: SpatialInteractionAction.DESELECT,
}

__all__ = _p1.__all__ + ['AuraPascalBridgeMessage', 'AuraPascalCoordinateReceipt', 'PascalNodeBinding', 'PascalSceneArtifactManifest', '_ACTION_STATE', '_CHILD_ACTIONS', '_PARENT_ACTIONS', '_PENDING_RECEIPT_ACTION', '_SPATIAL_ACTION_MAP']
