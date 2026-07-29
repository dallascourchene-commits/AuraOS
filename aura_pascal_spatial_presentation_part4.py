"""Exact same-origin Pascal presentation session protocol."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import secrets
from typing import Any

from aura_spatial_interaction import compile_spatial_interaction

from aura_pascal_spatial_presentation_part1 import (
    BridgeDirection,
    MAX_SESSION_MESSAGES,
    PASCAL_PRESENTATION_BRIDGE_VERSION,
    PASCAL_PRESENTATION_SESSION_VERSION,
    PASCAL_PRESENTATION_WFST_VERSION,
    PascalBridgeAction,
    PascalPresentationError,
    PascalPresentationState,
    _ORIGIN,
    _hex64,
    _identifier,
    _required_text,
    bridge_sha256,
    sha256_digest,
)
from aura_pascal_spatial_presentation_part2 import (
    ACTION_STATE,
    CHILD_ACTIONS,
    PARENT_ACTIONS,
    PENDING_RECEIPT_ACTION,
    SPATIAL_ACTION_MAP,
    AuraPascalBridgeMessage,
    AuraPascalCoordinateReceipt,
    PascalSceneArtifactManifest,
)
from aura_pascal_spatial_presentation_part3 import (
    build_spatial_scene,
    target_entity_ids,
)


@dataclass(frozen=True)
class _PendingParentCommand:
    message: AuraPascalBridgeMessage
    interaction: Mapping[str, Any]

    @property
    def action(self) -> PascalBridgeAction:
        return self.message.action

    @property
    def payload(self) -> Mapping[str, Any]:
        return self.message.payload


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
            raise PascalPresentationError(
                "coordinate receipt belongs to another Pascal artifact"
            )
        scene_digest = _hex64(spatial_scene_digest, "spatial_scene_digest")
        if coordinate_receipt.spatial_scene_digest != scene_digest:
            raise PascalPresentationError(
                "coordinate receipt belongs to another Spatial scene"
            )
        origin = _required_text(expected_origin, "expected_origin", maximum=256)
        if not _ORIGIN.fullmatch(origin):
            raise PascalPresentationError(
                "Pascal iframe origin must be an exact loopback HTTP(S) origin"
            )

        self.manifest = manifest
        self.coordinate_receipt = coordinate_receipt
        self.spatial_scene_digest = scene_digest
        self.render_plan_digest = _hex64(render_plan_digest, "render_plan_digest")
        self.expected_origin = origin
        self.session_id = _identifier(
            session_id or f"PPS-{secrets.token_hex(12)}",
            "session_id",
        )
        self.interaction_compiler = interaction_compiler
        self.scene = build_spatial_scene(manifest, coordinate_receipt)
        if self.scene.scene_digest != scene_digest:
            raise PascalPresentationError(
                "coordinate receipt Spatial scene digest differs from the canonical compatibility scene"
            )

        self.state = PascalPresentationState.CREATED
        self._next_sequence = {
            BridgeDirection.PARENT_TO_PASCAL: 1,
            BridgeDirection.PASCAL_TO_PARENT: 1,
        }
        self._seen_nonces: set[str] = set()
        self._message_count = 0
        self.active_view = "UNSET"
        self.selected_storey = manifest.storey_ids[0]
        self.selected_node_id = manifest.root_node_id
        self.dimensions_visible = True
        self.dissolution_receipt: dict[str, Any] | None = None
        self._pending_parent_command: _PendingParentCommand | None = None
        self._last_acknowledged_parent_digest = ""

    @property
    def state_binding_digest(self) -> str:
        return bridge_sha256(
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

    def transition_projection(
        self,
        action: PascalBridgeAction | str,
    ) -> dict[str, Any]:
        action_value = (
            action
            if isinstance(action, PascalBridgeAction)
            else PascalBridgeAction(str(action))
        )
        allowed, next_state = ACTION_STATE[action_value]
        admitted = (
            self.state in allowed
            and self.state is not PascalPresentationState.DISSOLVED
        )
        if action_value in PARENT_ACTIONS and self._pending_parent_command is not None:
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
                if action_value in PARENT_ACTIONS
                and self._pending_parent_command is not None
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

    def _assert_message_identity(
        self,
        message: AuraPascalBridgeMessage,
        origin: str,
    ) -> None:
        if origin != self.expected_origin:
            raise PascalPresentationError(
                "bridge message origin differs from the exact same-origin session"
            )
        if message.session_id != self.session_id:
            raise PascalPresentationError("bridge message belongs to another session")
        if message.spatial_scene_digest != self.spatial_scene_digest:
            raise PascalPresentationError(
                "bridge message has a stale Spatial scene digest"
            )
        if message.render_plan_digest != self.render_plan_digest:
            raise PascalPresentationError("bridge message has a stale render-plan digest")
        if message.pascal_artifact_digest != self.manifest.artifact_digest:
            raise PascalPresentationError(
                "bridge message has a stale Pascal artifact digest"
            )
        if (
            message.coordinate_receipt_digest
            != self.coordinate_receipt.receipt_digest
        ):
            raise PascalPresentationError(
                "bridge message has a stale coordinate receipt"
            )
        if message.state_binding_digest != self.state_binding_digest:
            raise PascalPresentationError(
                "bridge message has a stale presentation-state binding"
            )
        expected_sequence = self._next_sequence[message.direction]
        if message.sequence != expected_sequence:
            raise PascalPresentationError(
                f"bridge sequence must be exactly {expected_sequence} "
                f"for {message.direction.value}"
            )
        if message.nonce in self._seen_nonces:
            raise PascalPresentationError("bridge nonce replay detected")
        if self._message_count >= MAX_SESSION_MESSAGES:
            raise PascalPresentationError(
                "Pascal presentation session message ceiling reached"
            )

    def _record_message(self, message: AuraPascalBridgeMessage) -> None:
        if message.nonce in self._seen_nonces:
            raise PascalPresentationError("bridge nonce replay detected")
        if self._message_count >= MAX_SESSION_MESSAGES:
            raise PascalPresentationError(
                "Pascal presentation session message ceiling reached"
            )
        self._seen_nonces.add(message.nonce)
        self._message_count += 1

    def _compile_interaction(
        self,
        message: AuraPascalBridgeMessage,
    ) -> dict[str, Any]:
        targets = target_entity_ids(self.manifest, message.action, message.payload)
        intent = self.interaction_compiler(
            self.scene,
            action=SPATIAL_ACTION_MAP[message.action],
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
        if not isinstance(slots, Mapping) or set(slots) != {
            "DIR",
            "ASP",
            "CLASS",
            "SUBJ",
            "VOICE",
            "STEM",
        }:
            raise PascalPresentationError(
                "canonical Spatial interaction compiler did not return six exact slots"
            )
        if (
            result.get("execution_authority") is not False
            or result.get("patch_authority") is not False
        ):
            raise PascalPresentationError(
                "compiled Spatial interaction grants forbidden authority"
            )
        return result

    def _validate_parent_command(
        self,
        action: PascalBridgeAction,
        payload: Mapping[str, Any],
    ) -> None:
        if action is PascalBridgeAction.LOAD_ARTIFACT:
            scene = payload.get("scene")
            manifest = payload.get("artifact_manifest")
            if not isinstance(scene, Mapping) or not isinstance(manifest, Mapping):
                raise PascalPresentationError(
                    "LOAD_ARTIFACT requires exact scene and artifact_manifest objects"
                )
            if manifest.get("artifact_digest") != self.manifest.artifact_digest:
                raise PascalPresentationError(
                    "LOAD_ARTIFACT manifest differs from the session artifact"
                )
            initial_view = str(payload.get("initial_view") or "2D")
            if initial_view not in {"2D", "3D"}:
                raise PascalPresentationError("initial_view must be 2D or 3D")
            if not isinstance(payload.get("dimensions_visible", True), bool):
                raise PascalPresentationError(
                    "dimensions_visible must be a boolean"
                )
        elif action is PascalBridgeAction.SET_STOREY:
            storey = _identifier(payload.get("storey_id"), "payload.storey_id")
            if storey not in self.manifest.storey_ids:
                raise PascalPresentationError("requested storey is not admitted")
        elif action is PascalBridgeAction.SET_SELECTION:
            binding = self.manifest.binding_for_node(payload.get("node_id"))
            if not binding.selectable or binding.storey_id != self.selected_storey:
                raise PascalPresentationError(
                    "unadmitted or hidden Pascal selection"
                )
        elif action is PascalBridgeAction.SET_DIMENSIONS:
            if not isinstance(payload.get("visible"), bool):
                raise PascalPresentationError(
                    "dimension visibility must be a boolean"
                )
        elif action in {
            PascalBridgeAction.SET_VIEW_2D,
            PascalBridgeAction.SET_VIEW_3D,
            PascalBridgeAction.RESET_CAMERA,
            PascalBridgeAction.DISSOLVE,
        }:
            if payload:
                raise PascalPresentationError(
                    f"{action.value} does not accept payload fields"
                )

    def _validate_pending_postcondition(
        self,
        message: AuraPascalBridgeMessage,
    ) -> None:
        pending = self._pending_parent_command
        if pending is None:
            raise PascalPresentationError(
                "child receipt has no exact pending parent command"
            )
        action = pending.action
        payload = message.payload
        expected_action = PENDING_RECEIPT_ACTION[action]
        if message.action is not expected_action:
            raise PascalPresentationError(
                f"pending {action.value} requires {expected_action.value}, "
                f"not {message.action.value}"
            )
        supplied = _hex64(
            payload.get("command_message_digest"),
            "payload.command_message_digest",
        )
        if supplied != pending.message.message_digest:
            raise PascalPresentationError(
                "child receipt belongs to another parent command"
            )

        command_payload = pending.payload
        if action is PascalBridgeAction.LOAD_ARTIFACT:
            if payload.get("loaded") is not True:
                raise PascalPresentationError("load receipt must report loaded=true")
            expected_view = str(command_payload.get("initial_view") or "2D")
            if payload.get("view") != expected_view:
                raise PascalPresentationError(
                    "load receipt view differs from the issued command"
                )
            if payload.get("node_count") != len(self.manifest.node_bindings):
                raise PascalPresentationError(
                    "load receipt node_count differs from the exact manifest"
                )
            if payload.get("storey_id") != self.manifest.storey_ids[0]:
                raise PascalPresentationError(
                    "load receipt storey differs from the exact initial storey"
                )
            if payload.get("node_id") != self.manifest.root_node_id:
                raise PascalPresentationError(
                    "load receipt node differs from the exact initial selection"
                )
            if (
                payload.get("dimensions_visible")
                is not command_payload.get("dimensions_visible", True)
            ):
                raise PascalPresentationError(
                    "load receipt dimension state differs from the issued command"
                )
        elif action is PascalBridgeAction.SET_VIEW_2D:
            if payload.get("view") != "2D":
                raise PascalPresentationError(
                    "SET_VIEW_2D receipt must report view=2D"
                )
        elif action is PascalBridgeAction.SET_VIEW_3D:
            if payload.get("view") != "3D":
                raise PascalPresentationError(
                    "SET_VIEW_3D receipt must report view=3D"
                )
        elif action is PascalBridgeAction.SET_STOREY:
            if payload.get("storey_id") != command_payload.get("storey_id"):
                raise PascalPresentationError(
                    "storey receipt differs from the issued storey"
                )
        elif action is PascalBridgeAction.SET_SELECTION:
            if payload.get("node_id") != command_payload.get("node_id"):
                raise PascalPresentationError(
                    "selection receipt differs from the issued node"
                )
        elif action is PascalBridgeAction.SET_DIMENSIONS:
            if payload.get("dimensions_visible") is not command_payload.get("visible"):
                raise PascalPresentationError(
                    "dimension receipt differs from the issued visibility"
                )
        elif action is PascalBridgeAction.RESET_CAMERA:
            if payload.get("camera_reset") is not True:
                raise PascalPresentationError(
                    "camera reset receipt must report camera_reset=true"
                )

    def _assert_child_receipt_binding(
        self,
        message: AuraPascalBridgeMessage,
    ) -> str:
        """Return how the pending parent sequence should be advanced."""
        if message.action is PascalBridgeAction.READY:
            if self._pending_parent_command is not None:
                raise PascalPresentationError(
                    "READY cannot satisfy a pending parent command"
                )
            return "none"
        if message.action is PascalBridgeAction.RENDER_RECEIPT:
            supplied = _hex64(
                message.payload.get("command_message_digest"),
                "payload.command_message_digest",
            )
            if supplied != self._last_acknowledged_parent_digest:
                raise PascalPresentationError(
                    "render receipt is not bound to the last acknowledged command"
                )
            return "none"
        if message.action is PascalBridgeAction.PRESENTATION_ERROR:
            pending = self._pending_parent_command
            if pending is None:
                raise PascalPresentationError(
                    "presentation error has no pending parent command"
                )
            validated = message.payload.get("validated_command")
            if not isinstance(validated, bool):
                raise PascalPresentationError(
                    "presentation error validated_command must be a boolean"
                )
            if validated:
                supplied = _hex64(
                    message.payload.get("command_message_digest"),
                    "payload.command_message_digest",
                )
                if supplied != pending.message.message_digest:
                    raise PascalPresentationError(
                        "presentation error belongs to another command"
                    )
                return "advance"
            rejected_sequence = message.payload.get("rejected_sequence")
            if rejected_sequence != pending.message.sequence:
                raise PascalPresentationError(
                    "presentation error rejected_sequence differs from the pending command"
                )
            if "command_message_digest" in message.payload:
                raise PascalPresentationError(
                    "unvalidated presentation error cannot claim a command digest"
                )
            return "retry"

        self._validate_pending_postcondition(message)
        return "advance"

    def _apply_payload(self, message: AuraPascalBridgeMessage) -> None:
        payload = message.payload
        if message.action is PascalBridgeAction.LOAD_RECEIPT:
            if payload.get("external_requests") != 0:
                raise PascalPresentationError(
                    "load receipt must report zero external requests"
                )
            self.active_view = str(payload["view"])
            self.selected_storey = _identifier(
                payload.get("storey_id"),
                "payload.storey_id",
            )
            self.selected_node_id = self.manifest.binding_for_node(
                payload.get("node_id")
            ).node_id
            if not isinstance(payload.get("dimensions_visible"), bool):
                raise PascalPresentationError(
                    "load receipt dimensions_visible must be a boolean"
                )
            self.dimensions_visible = payload["dimensions_visible"]
        elif message.action is PascalBridgeAction.VIEW_STATE:
            view = str(payload.get("view") or "")
            if view not in {"2D", "3D"}:
                raise PascalPresentationError(
                    "view receipt must report 2D or 3D"
                )
            storey = _identifier(payload.get("storey_id"), "payload.storey_id")
            if storey not in self.manifest.storey_ids:
                raise PascalPresentationError(
                    "view receipt references an unadmitted storey"
                )
            binding = self.manifest.binding_for_node(payload.get("node_id"))
            if (
                binding.storey_id != storey
                and binding.node_id != self.manifest.root_node_id
            ):
                raise PascalPresentationError(
                    "view receipt selection is hidden by its storey"
                )
            if not isinstance(payload.get("dimensions_visible"), bool):
                raise PascalPresentationError(
                    "view receipt dimensions_visible must be a boolean"
                )
            self.active_view = view
            self.selected_storey = storey
            self.selected_node_id = binding.node_id
            self.dimensions_visible = payload["dimensions_visible"]
        elif message.action is PascalBridgeAction.SELECTION_CHANGED:
            binding = self.manifest.binding_for_node(payload.get("node_id"))
            if not binding.selectable:
                raise PascalPresentationError("requested node is not selectable")
            if binding.storey_id != self.selected_storey:
                raise PascalPresentationError(
                    "hidden-storey selection is rejected"
                )
            self.selected_node_id = binding.node_id
        elif message.action is PascalBridgeAction.RENDER_RECEIPT:
            _hex64(payload.get("frame_digest"), "payload.frame_digest")
            if payload.get("external_requests") != 0:
                raise PascalPresentationError(
                    "render receipt must report zero external requests"
                )
        elif message.action is PascalBridgeAction.DISSOLUTION_RECEIPT:
            required = {
                "command_message_digest",
                "renderer_released",
                "listeners_released",
                "timers_released",
                "buffers_cleared",
                "indexeddb_deleted",
                "network_guards_restored",
                "external_requests",
            }
            if set(payload) != required:
                raise PascalPresentationError(
                    "dissolution receipt fields are incomplete or unknown"
                )
            for name in (
                "renderer_released",
                "listeners_released",
                "timers_released",
                "buffers_cleared",
                "indexeddb_deleted",
                "network_guards_restored",
            ):
                if payload.get(name) is not True:
                    raise PascalPresentationError(
                        f"dissolution receipt {name} must be true"
                    )
            if payload.get("external_requests") != 0:
                raise PascalPresentationError(
                    "dissolution receipt must report zero external requests"
                )
            receipt = {
                **dict(payload),
                "iframe_removed": False,
                "iframe_removed_verified": False,
                "evidence_class": "CHILD_AND_PARENT_REPORTED",
                "session_id": self.session_id,
                "pascal_artifact_digest": self.manifest.artifact_digest,
                "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            }
            receipt["receipt_digest"] = sha256_digest(receipt)
            self.dissolution_receipt = receipt

    def accept(
        self,
        value: AuraPascalBridgeMessage | Mapping[str, Any],
        *,
        origin: str,
    ) -> dict[str, Any]:
        """Accept one child-to-parent event after exact identity and receipt checks."""
        message = (
            value
            if isinstance(value, AuraPascalBridgeMessage)
            else AuraPascalBridgeMessage.from_mapping(value)
        )
        if self.state is PascalPresentationState.DISSOLVED:
            raise PascalPresentationError(
                "post-dissolution bridge messages are rejected"
            )
        if (
            message.direction is not BridgeDirection.PASCAL_TO_PARENT
            or message.action not in CHILD_ACTIONS
        ):
            raise PascalPresentationError(
                "only admitted Pascal-to-parent events may be accepted"
            )
        projection = self.transition_projection(message.action)
        if projection["admitted"] is not True:
            raise PascalPresentationError(str(projection["blocked_reason"]))
        self._assert_message_identity(message, origin)
        parent_sequence_effect = self._assert_child_receipt_binding(message)
        interaction = self._compile_interaction(message)
        self._apply_payload(message)

        _allowed, next_state = ACTION_STATE[message.action]
        if next_state is not None:
            self.state = next_state
        self._next_sequence[BridgeDirection.PASCAL_TO_PARENT] += 1
        self._record_message(message)

        if parent_sequence_effect in {"advance", "retry"}:
            pending = self._pending_parent_command
            if pending is None:
                raise PascalPresentationError(
                    "pending parent command disappeared during receipt acceptance"
                )
            if parent_sequence_effect == "advance":
                self._next_sequence[BridgeDirection.PARENT_TO_PASCAL] += 1
                self._last_acknowledged_parent_digest = pending.message.message_digest
            self._pending_parent_command = None

        return {
            "ok": True,
            "accepted_message_digest": message.message_digest,
            "action": message.action.value,
            "state": self.state.value,
            "state_binding_digest": self.state_binding_digest,
            "pending_parent_message_digest": (
                self._pending_parent_command.message.message_digest
                if self._pending_parent_command
                else ""
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
        """Issue but do not acknowledge one parent command.

        Parent sequence advancement occurs only after an exact child receipt or a
        command-bound presentation error is retained.
        """
        action_value = (
            action
            if isinstance(action, PascalBridgeAction)
            else PascalBridgeAction(str(action))
        )
        if action_value not in PARENT_ACTIONS:
            raise PascalPresentationError(
                "only parent-to-Pascal commands may be issued by the server"
            )
        projection = self.transition_projection(action_value)
        if projection["admitted"] is not True:
            raise PascalPresentationError(str(projection["blocked_reason"]))
        clean_payload = dict(payload or {})
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
            payload=clean_payload,
        )
        self._validate_parent_command(action_value, message.payload)
        interaction = self._compile_interaction(message)
        self._record_message(message)
        self._pending_parent_command = _PendingParentCommand(
            message=message,
            interaction=interaction,
        )
        return message

    def mark_iframe_removed(self) -> dict[str, Any]:
        """Retain the same-origin parent observation after the child dissolves."""
        if (
            self.state is not PascalPresentationState.DISSOLVED
            or self.dissolution_receipt is None
        ):
            raise PascalPresentationError(
                "iframe removal can only follow a retained child dissolution receipt"
            )
        receipt = {
            key: value
            for key, value in self.dissolution_receipt.items()
            if key != "receipt_digest"
        }
        receipt["iframe_removed"] = True
        receipt["iframe_removed_verified"] = False
        receipt["receipt_digest"] = sha256_digest(receipt)
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
            "message_count": self._message_count,
            "pending_parent_message_digest": (
                self._pending_parent_command.message.message_digest
                if self._pending_parent_command
                else ""
            ),
            "last_acknowledged_parent_digest": self._last_acknowledged_parent_digest,
            "dissolution_receipt": self.dissolution_receipt,
            "dissolution_complete": bool(
                self.dissolution_receipt
                and self.dissolution_receipt.get("iframe_removed") is True
            ),
        }


__all__ = ["PascalPresentationSession"]
