import aura_pascal_spatial_presentation_part1 as _p1
from aura_pascal_spatial_presentation_part1 import *  # noqa: F403
import aura_pascal_spatial_presentation_part2 as _p2
from aura_pascal_spatial_presentation_part2 import *  # noqa: F403
import aura_pascal_spatial_presentation_part3 as _p3
from aura_pascal_spatial_presentation_part3 import *  # noqa: F403

class PascalPresentationSession:
    """One exact, same-origin, disposable Pascal presentation session."""

    def __init__(
        self,
        *,
        manifest: PascalSceneArtifactManifest,
        coordinate_receipt: AuraPascalCoordinateReceipt,
        spatial_scene_digest: str,
        render_plan_digest: str,
        expected_origin: str,
        session_id: str | None = None,
        interaction_compiler: Callable[..., Any] = compile_spatial_interaction,
    ) -> None:
        if coordinate_receipt.pascal_artifact_digest != manifest.artifact_digest:
            raise PascalPresentationError("coordinate receipt belongs to another Pascal artifact")
        scene_digest = _hex64(spatial_scene_digest, "spatial_scene_digest")
        if coordinate_receipt.spatial_scene_digest != scene_digest:
            raise PascalPresentationError("coordinate receipt belongs to another Spatial scene")
        origin = _required_text(expected_origin, "expected_origin", maximum=256)
        if not _ORIGIN.fullmatch(origin):
            raise PascalPresentationError("Pascal iframe origin must be an exact loopback HTTP(S) origin")
        self.manifest = manifest
        self.coordinate_receipt = coordinate_receipt
        self.spatial_scene_digest = scene_digest
        self.render_plan_digest = _hex64(render_plan_digest, "render_plan_digest")
        self.expected_origin = origin
        self.session_id = _identifier(session_id or f"PPS-{secrets.token_hex(12)}", "session_id")
        self.interaction_compiler = interaction_compiler
        self.scene = _build_spatial_scene(manifest, coordinate_receipt)
        if self.scene.scene_digest != scene_digest:
            raise PascalPresentationError(
                "coordinate receipt Spatial scene digest differs from the canonical compatibility scene"
            )
        self.state = PascalPresentationState.CREATED
        self._next_sequence = {
            BridgeDirection.PARENT_TO_PASCAL: 1,
            BridgeDirection.PASCAL_TO_PARENT: 1,
        }
        self._seen_nonces: OrderedDict[str, None] = OrderedDict()
        self.active_view = "UNSET"
        self.selected_storey = manifest.storey_ids[0]
        self.selected_node_id = manifest.root_node_id
        self.dimensions_visible = True
        self.dissolution_receipt: dict[str, Any] | None = None
        self._pending_parent_message: tuple[str, PascalBridgeAction] | None = None
        self._last_acknowledged_parent_digest = ""

    @property
    def state_binding_digest(self) -> str:
        return _sha256(
            {
                "grammar_version": PASCAL_PRESENTATION_WFST_VERSION,
                "session_version": PASCAL_PRESENTATION_SESSION_VERSION,
                "session_id": self.session_id,
                "state": self.state.value,
                "spatial_scene_digest": self.spatial_scene_digest,
                "render_plan_digest": self.render_plan_digest,
                "pascal_artifact_digest": self.manifest.artifact_digest,
                "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
                "expected_origin": self.expected_origin,
                "projection_only": True,
                "execution_authority": False,
                "construction_truth": False,
            }
        )

    def transition_projection(self, action: PascalBridgeAction | str) -> dict[str, Any]:
        action_value = action if isinstance(action, PascalBridgeAction) else PascalBridgeAction(str(action))
        allowed, next_state = _ACTION_STATE[action_value]
        admitted = self.state in allowed and self.state is not PascalPresentationState.DISSOLVED
        if action_value in _PARENT_ACTIONS and self._pending_parent_message is not None:
            admitted = False
        return {
            "grammar_version": PASCAL_PRESENTATION_WFST_VERSION,
            "base_owner": "aura_spatial_interaction.compile_spatial_interaction",
            "arena_id": "construction",
            "session_id": self.session_id,
            "current_state": self.state.value,
            "action": action_value.value,
            "admitted": admitted,
            "blocked_reason": (
                ""
                if admitted
                else "pending_parent_command_requires_exact_child_receipt"
                if action_value in _PARENT_ACTIONS and self._pending_parent_message is not None
                else "action_not_admitted_for_current_session_state"
            ),
            "next_state": (next_state or self.state).value,
            "state_binding_digest": self.state_binding_digest,
            "projection_only": True,
            "state_mutation": False,
            "execution_authority": False,
            "construction_truth": False,
            "human_review_required": True,
        }

    def _assert_message_identity(self, message: AuraPascalBridgeMessage, origin: str) -> None:
        if origin != self.expected_origin:
            raise PascalPresentationError("bridge message origin differs from the exact same-origin session")
        if message.session_id != self.session_id:
            raise PascalPresentationError("bridge message belongs to another session")
        if message.spatial_scene_digest != self.spatial_scene_digest:
            raise PascalPresentationError("bridge message has a stale Spatial scene digest")
        if message.render_plan_digest != self.render_plan_digest:
            raise PascalPresentationError("bridge message has a stale render-plan digest")
        if message.pascal_artifact_digest != self.manifest.artifact_digest:
            raise PascalPresentationError("bridge message has a stale Pascal artifact digest")
        if message.coordinate_receipt_digest != self.coordinate_receipt.receipt_digest:
            raise PascalPresentationError("bridge message has a stale coordinate receipt")
        if message.state_binding_digest != self.state_binding_digest:
            raise PascalPresentationError("bridge message has a stale presentation-state binding")
        expected_sequence = self._next_sequence[message.direction]
        if message.sequence != expected_sequence:
            raise PascalPresentationError(
                f"bridge sequence must be exactly {expected_sequence} for {message.direction.value}"
            )
        if message.nonce in self._seen_nonces:
            raise PascalPresentationError("bridge nonce replay detected")

    def _compile_interaction(self, message: AuraPascalBridgeMessage) -> dict[str, Any]:
        targets = _target_entity_ids(self.manifest, message.action, message.payload)
        intent = self.interaction_compiler(
            self.scene,
            action=_SPATIAL_ACTION_MAP[message.action],
            target_entity_ids=targets,
            actor_ref=(
                "presentation:pascal-parent"
                if message.direction is BridgeDirection.PARENT_TO_PASCAL
                else "presentation:pascal-workbench"
            ),
            metadata={
                "pascal_bridge_version": PASCAL_PRESENTATION_BRIDGE_VERSION,
                "pascal_bridge_action": message.action.value,
                "pascal_bridge_direction": message.direction.value,
                "pascal_message_digest": message.message_digest,
                "pascal_state_binding_digest": message.state_binding_digest,
                "working_copy_only": True,
                "external_asset_fetch": False,
                "persistent_canonical_storage": False,
            },
        )
        result = intent.to_dict() if hasattr(intent, "to_dict") else dict(intent)
        slots = result.get("intent_slots")
        if not isinstance(slots, Mapping) or set(slots) != {"DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"}:
            raise PascalPresentationError("canonical Spatial interaction compiler did not return six exact slots")
        if result.get("execution_authority") is not False or result.get("patch_authority") is not False:
            raise PascalPresentationError("compiled Spatial interaction grants forbidden authority")
        return result

    def _apply_payload(self, message: AuraPascalBridgeMessage) -> None:
        payload = message.payload
        if message.direction is BridgeDirection.PARENT_TO_PASCAL:
            return
        if message.action is PascalBridgeAction.LOAD_RECEIPT:
            if payload.get("loaded") is not True:
                raise PascalPresentationError("load receipt must report loaded=true")
            if payload.get("external_requests") != 0:
                raise PascalPresentationError("load receipt must report zero external requests")
            self.active_view = str(payload.get("view") or "2D")
            if self.active_view not in {"2D", "3D"}:
                raise PascalPresentationError("load receipt view must be 2D or 3D")
        elif message.action is PascalBridgeAction.VIEW_STATE:
            view = str(payload.get("view") or "")
            if view not in {"2D", "3D"}:
                raise PascalPresentationError("view receipt must report 2D or 3D")
            storey = _identifier(payload.get("storey_id"), "payload.storey_id")
            if storey not in self.manifest.storey_ids:
                raise PascalPresentationError("view receipt references an unadmitted storey")
            binding = self.manifest.binding_for_node(payload.get("node_id"))
            if binding.storey_id != storey and binding.node_id != self.manifest.root_node_id:
                raise PascalPresentationError("view receipt selection is hidden by its storey")
            if type(payload.get("dimensions_visible")) is not bool:
                raise PascalPresentationError("view receipt dimensions_visible must be a boolean")
            self.active_view = view
            self.selected_storey = storey
            self.selected_node_id = binding.node_id
            self.dimensions_visible = payload["dimensions_visible"]
        elif message.action is PascalBridgeAction.SELECTION_CHANGED:
            binding = self.manifest.binding_for_node(payload.get("node_id"))
            if not binding.selectable:
                raise PascalPresentationError("requested node is not selectable")
            if binding.storey_id != self.selected_storey:
                raise PascalPresentationError("hidden-storey selection is rejected")
            self.selected_node_id = binding.node_id
        elif message.action is PascalBridgeAction.RENDER_RECEIPT:
            _hex64(payload.get("frame_digest"), "payload.frame_digest")
            if payload.get("external_requests") != 0:
                raise PascalPresentationError("render receipt must report zero external requests")
        elif message.action is PascalBridgeAction.DISSOLUTION_RECEIPT:
            required = {
                "command_message_digest",
                "renderer_released",
                "listeners_released",
                "timers_released",
                "buffers_cleared",
                "indexeddb_deleted",
                "external_requests",
            }
            if set(payload) != required:
                raise PascalPresentationError("dissolution receipt fields are incomplete or unknown")
            for name in (
                "renderer_released",
                "listeners_released",
                "timers_released",
                "buffers_cleared",
                "indexeddb_deleted",
            ):
                if payload.get(name) is not True:
                    raise PascalPresentationError(f"dissolution receipt {name} must be true")
            if payload.get("external_requests") != 0:
                raise PascalPresentationError("dissolution receipt must report zero external requests")
            self.dissolution_receipt = {
                **dict(payload),
                "iframe_removed": False,
                "iframe_removed_verified": False,
                "evidence_class": "CLIENT_REPORTED",
                "session_id": self.session_id,
                "pascal_artifact_digest": self.manifest.artifact_digest,
                "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            }
            self.dissolution_receipt["receipt_digest"] = _sha256(self.dissolution_receipt)

    def _assert_child_receipt_binding(self, message: AuraPascalBridgeMessage) -> None:
        if message.action is PascalBridgeAction.READY:
            if self._pending_parent_message is not None:
                raise PascalPresentationError("READY cannot satisfy a pending parent command")
            return
        if message.action is PascalBridgeAction.RENDER_RECEIPT:
            supplied = _hex64(
                message.payload.get("command_message_digest"),
                "payload.command_message_digest",
            )
            if supplied != self._last_acknowledged_parent_digest:
                raise PascalPresentationError("render receipt is not bound to the last acknowledged command")
            return
        if message.action is PascalBridgeAction.PRESENTATION_ERROR:
            if self._pending_parent_message is None:
                return
            supplied = _hex64(
                message.payload.get("command_message_digest"),
                "payload.command_message_digest",
            )
            if supplied != self._pending_parent_message[0]:
                raise PascalPresentationError("presentation error belongs to another command")
            return
        if self._pending_parent_message is None:
            raise PascalPresentationError("child receipt has no exact pending parent command")
        pending_digest, pending_action = self._pending_parent_message
        expected_action = _PENDING_RECEIPT_ACTION[pending_action]
        if message.action is not expected_action:
            raise PascalPresentationError(
                f"pending {pending_action.value} requires {expected_action.value}, not {message.action.value}"
            )
        supplied = _hex64(
            message.payload.get("command_message_digest"),
            "payload.command_message_digest",
        )
        if supplied != pending_digest:
            raise PascalPresentationError("child receipt belongs to another parent command")

    def accept(self, value: AuraPascalBridgeMessage | Mapping[str, Any], *, origin: str) -> dict[str, Any]:
        message = value if isinstance(value, AuraPascalBridgeMessage) else AuraPascalBridgeMessage.from_mapping(value)
        if self.state is PascalPresentationState.DISSOLVED:
            raise PascalPresentationError("post-dissolution bridge messages are rejected")
        if (
            message.direction is BridgeDirection.PARENT_TO_PASCAL
            and message.action not in _PARENT_ACTIONS
        ) or (
            message.direction is BridgeDirection.PASCAL_TO_PARENT
            and message.action not in _CHILD_ACTIONS
        ):
            raise PascalPresentationError("bridge action is invalid for its direction")
        projection = self.transition_projection(message.action)
        if projection["admitted"] is not True:
            raise PascalPresentationError(str(projection["blocked_reason"]))
        self._assert_message_identity(message, origin)
        if message.direction is BridgeDirection.PASCAL_TO_PARENT:
            self._assert_child_receipt_binding(message)
        interaction = self._compile_interaction(message)
        self._apply_payload(message)
        allowed, next_state = _ACTION_STATE[message.action]
        del allowed
        if next_state is not None:
            self.state = next_state
        self._next_sequence[message.direction] += 1
        self._seen_nonces[message.nonce] = None
        self._seen_nonces.move_to_end(message.nonce)
        while len(self._seen_nonces) > MAX_RETAINED_NONCES:
            self._seen_nonces.popitem(last=False)
        if message.direction is BridgeDirection.PARENT_TO_PASCAL:
            self._pending_parent_message = (message.message_digest, message.action)
        elif message.action is PascalBridgeAction.PRESENTATION_ERROR:
            if self._pending_parent_message is not None:
                self._last_acknowledged_parent_digest = self._pending_parent_message[0]
                self._pending_parent_message = None
        elif message.action in _PENDING_RECEIPT_ACTION.values():
            assert self._pending_parent_message is not None
            self._last_acknowledged_parent_digest = self._pending_parent_message[0]
            self._pending_parent_message = None
        return {
            "ok": True,
            "accepted_message_digest": message.message_digest,
            "action": message.action.value,
            "state": self.state.value,
            "state_binding_digest": self.state_binding_digest,
            "pending_parent_message_digest": (
                self._pending_parent_message[0] if self._pending_parent_message else ""
            ),
            "spatial_interaction": interaction,
            "projection_only": True,
            "execution_authority": False,
            "construction_truth": False,
            "human_review_required": True,
            "dissolution_receipt": self.dissolution_receipt,
        }

    def issue_parent_message(
        self,
        action: PascalBridgeAction | str,
        payload: Mapping[str, Any] | None = None,
    ) -> AuraPascalBridgeMessage:
        action_value = action if isinstance(action, PascalBridgeAction) else PascalBridgeAction(str(action))
        if action_value not in _PARENT_ACTIONS:
            raise PascalPresentationError("only parent-to-Pascal commands may be issued by the server")
        projection = self.transition_projection(action_value)
        if projection["admitted"] is not True:
            raise PascalPresentationError(str(projection["blocked_reason"]))
        message = AuraPascalBridgeMessage.build(
            session_id=self.session_id,
            sequence=self._next_sequence[BridgeDirection.PARENT_TO_PASCAL],
            spatial_scene_digest=self.spatial_scene_digest,
            render_plan_digest=self.render_plan_digest,
            pascal_artifact_digest=self.manifest.artifact_digest,
            coordinate_receipt_digest=self.coordinate_receipt.receipt_digest,
            state_binding_digest=self.state_binding_digest,
            direction=BridgeDirection.PARENT_TO_PASCAL,
            action=action_value,
            payload=dict(payload or {}),
        )
        self.accept(message, origin=self.expected_origin)
        return message


    def mark_iframe_removed(self) -> dict[str, Any]:
        """Retain the same-origin parent observation after the child dissolves."""

        if self.state is not PascalPresentationState.DISSOLVED or self.dissolution_receipt is None:
            raise PascalPresentationError("iframe removal can only follow a retained child dissolution receipt")
        receipt = {
            key: value
            for key, value in self.dissolution_receipt.items()
            if key != "receipt_digest"
        }
        receipt["iframe_removed"] = True
        receipt["iframe_removed_verified"] = False
        receipt["evidence_class"] = "CLIENT_REPORTED"
        receipt["receipt_digest"] = _sha256(receipt)
        self.dissolution_receipt = receipt
        return dict(receipt)

    def status(self) -> dict[str, Any]:
        return {
            "version": PASCAL_PRESENTATION_SESSION_VERSION,
            "session_id": self.session_id,
            "state": self.state.value,
            "state_binding_digest": self.state_binding_digest,
            "active_view": self.active_view,
            "selected_storey": self.selected_storey,
            "selected_node_id": self.selected_node_id,
            "dimensions_visible": self.dimensions_visible,
            "pascal_artifact_digest": self.manifest.artifact_digest,
            "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            "spatial_scene_digest": self.spatial_scene_digest,
            "render_plan_digest": self.render_plan_digest,
            "expected_origin": self.expected_origin,
            "working_copy_only": True,
            "external_asset_fetch": False,
            "persistent_canonical_storage": False,
            "destroy_on_dissolution": True,
            "projection_only": True,
            "execution_authority": False,
            "construction_truth": False,
            "human_review_required": True,
            "pending_parent_message_digest": (
                self._pending_parent_message[0] if self._pending_parent_message else ""
            ),
            "last_acknowledged_parent_digest": self._last_acknowledged_parent_digest,
            "dissolution_receipt": self.dissolution_receipt,
            "dissolution_complete": bool(
                self.dissolution_receipt
                and self.dissolution_receipt.get("iframe_removed") is True
            ),
        }

__all__ = _p1.__all__ + _p2.__all__ + _p3.__all__ + ['PascalPresentationSession']
