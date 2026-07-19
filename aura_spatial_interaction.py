"""Fail-closed compilation of spatial UI actions into six-slot Aura intents."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any

from aura_event_contracts import canonical_json, sanitize_payload, stable_digest
from aura_spatial_contracts import (
    SpatialInteractionAction,
    SpatialInteractionIntent,
    SpatialSceneSnapshot,
)

SPATIAL_INTERACTION_VERSION = "AURA_SPATIAL_INTERACTION_V1"
MAX_INTERACTION_METADATA_BYTES = 65_536
MAX_INTERACTION_EVIDENCE_BYTES = 262_144
_ACTOR_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
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
_AUTHORITY_KEY_TOKENS = frozenset(re.sub(r"[^a-z0-9]+", "", key.lower()) for key in _AUTHORITY_KEYS)

_ACTION_SLOTS: dict[SpatialInteractionAction, dict[str, str]] = {
    SpatialInteractionAction.SELECT: {
        "DIR": "scene",
        "ASP": "inspect",
        "CLASS": "spatial_selection",
        "SUBJ": "domain_projection",
        "VOICE": "select",
        "STEM": "bind_selection",
    },
    SpatialInteractionAction.DESELECT: {
        "DIR": "scene",
        "ASP": "inspect",
        "CLASS": "spatial_selection",
        "SUBJ": "domain_projection",
        "VOICE": "deselect",
        "STEM": "release_selection",
    },
    SpatialInteractionAction.EXPAND: {
        "DIR": "scene",
        "ASP": "navigate",
        "CLASS": "bounded_projection",
        "SUBJ": "domain_neighborhood",
        "VOICE": "expand",
        "STEM": "request_neighborhood",
    },
    SpatialInteractionAction.CONTRACT: {
        "DIR": "scene",
        "ASP": "navigate",
        "CLASS": "bounded_projection",
        "SUBJ": "domain_neighborhood",
        "VOICE": "contract",
        "STEM": "reduce_neighborhood",
    },
    SpatialInteractionAction.FOCUS: {
        "DIR": "scene",
        "ASP": "navigate",
        "CLASS": "spatial_focus",
        "SUBJ": "domain_projection",
        "VOICE": "focus",
        "STEM": "center_view",
    },
    SpatialInteractionAction.OPEN_SOURCE: {
        "DIR": "repository",
        "ASP": "inspect",
        "CLASS": "exact_source_navigation",
        "SUBJ": "selected_entity_source",
        "VOICE": "open",
        "STEM": "resolve_source_anchor",
    },
    SpatialInteractionAction.PREPARE_REPAIR_REQUEST: {
        "DIR": "forge",
        "ASP": "prepare",
        "CLASS": "governed_repair_request",
        "SUBJ": "selected_entity_source",
        "VOICE": "propose",
        "STEM": "compile_review_handoff",
    },
}


def compile_spatial_interaction(
    scene: SpatialSceneSnapshot,
    *,
    action: SpatialInteractionAction | str,
    target_entity_ids: Iterable[str],
    actor_ref: str = "human:local",
    metadata: Mapping[str, Any] | None = None,
) -> SpatialInteractionIntent:
    if not isinstance(scene, SpatialSceneSnapshot):
        raise ValueError("scene must be a SpatialSceneSnapshot")
    try:
        action_value = action if isinstance(action, SpatialInteractionAction) else SpatialInteractionAction(str(action))
    except ValueError as exc:
        raise ValueError(f"unsupported spatial interaction action: {action}") from exc

    actor = str(actor_ref or "human:local").strip()
    if not _ACTOR_REF.fullmatch(actor):
        raise ValueError("actor_ref contains unsupported characters")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise ValueError("metadata must be an object")
    supplied_metadata = dict(metadata or {})
    authority_path = _find_authority_key(supplied_metadata)
    if authority_path is not None:
        raise ValueError(f"interaction metadata cannot supply authority field: {authority_path}")
    sanitized_metadata = sanitize_payload(supplied_metadata)
    if not isinstance(sanitized_metadata, Mapping):
        raise ValueError("sanitized interaction metadata must remain an object")
    sanitized_metadata = dict(sanitized_metadata)
    metadata_bytes = canonical_json(sanitized_metadata).encode("utf-8")
    if len(metadata_bytes) > MAX_INTERACTION_METADATA_BYTES:
        raise ValueError("interaction metadata exceeds the bounded payload limit")

    if isinstance(target_entity_ids, (str, bytes, bytearray)):
        raise ValueError("target_entity_ids must be an iterable of identifiers")
    targets = tuple(sorted({str(item).strip() for item in target_entity_ids if str(item).strip()}))
    if not targets:
        raise ValueError("target_entity_ids must not be empty")
    if len(targets) > 128:
        raise ValueError("target_entity_ids exceeds the spatial interaction cap")
    entity_by_id = {entity.entity_id: entity for entity in scene.entities}
    missing = [item for item in targets if item not in entity_by_id]
    if missing:
        raise ValueError(f"unknown scene entities: {missing}")

    source_refs = {
        f"scene:{scene.scene_id}#{scene.scene_digest}",
        f"actor:{actor}",
    }
    for target in targets:
        source_refs.update(entity_by_id[target].source_refs)
    ordered_refs = tuple(sorted(source_refs))
    if len(ordered_refs) > 1024:
        raise ValueError("interaction source references exceed the bounded evidence cap")
    evidence_bytes = canonical_json(
        {
            "target_entity_ids": list(targets),
            "source_refs": list(ordered_refs),
        }
    ).encode("utf-8")
    if len(evidence_bytes) > MAX_INTERACTION_EVIDENCE_BYTES:
        raise ValueError("interaction evidence exceeds the bounded payload limit")

    requires_forge = action_value is SpatialInteractionAction.PREPARE_REPAIR_REQUEST
    protected_metadata = {
        **sanitized_metadata,
        "actor_ref": actor,
        "renderer_input_is_authority": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "production_mutation": False,
    }
    body = {
        "scene_id": scene.scene_id,
        "scene_digest": scene.scene_digest,
        "action": action_value.value,
        "targets": list(targets),
        "actor_ref": actor,
        "source_refs": list(ordered_refs),
        "metadata": protected_metadata,
    }
    return SpatialInteractionIntent(
        interaction_id=("spatial-interaction:" + stable_digest(body, digest_size=12)),
        scene_id=scene.scene_id,
        scene_digest=scene.scene_digest,
        action=action_value,
        target_entity_ids=targets,
        intent_slots=_ACTION_SLOTS[action_value],
        source_refs=ordered_refs,
        review_only=True,
        requires_forge=requires_forge,
        execution_authority=False,
        patch_authority=False,
        metadata=protected_metadata,
    )


def compile_hotswap_request_guard(
    scene: SpatialSceneSnapshot,
    *,
    target_entity_ids: Iterable[str],
    proposed_change_digest: str,
    actor_ref: str = "human:local",
) -> dict[str, Any]:
    """Compile a review-only Forge handoff; never report execution success."""
    digest = str(proposed_change_digest or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("proposed_change_digest must be a 64-character lowercase hex digest")
    intent = compile_spatial_interaction(
        scene,
        action=SpatialInteractionAction.PREPARE_REPAIR_REQUEST,
        target_entity_ids=target_entity_ids,
        actor_ref=actor_ref,
        metadata={
            "proposed_change_digest": digest,
            "legacy_message_type": "HOTSWAP_REQUEST",
        },
    )
    return {
        "ok": False,
        "status": "REQUIRES_GOVERNED_REPAIR_HANDOFF",
        "error": "spatial_hotswap_has_no_direct_execution_authority",
        "intent": intent.to_dict(),
        "next_owner": "aura_forge",
        "required_next_steps": [
            "resolve_exact_source_spans_and_hashes",
            "compile_forge_evidence_contract",
            "stage_candidate_in_isolation",
            "run_declared_verifiers",
            "stop_for_human_review",
        ],
        "queued": False,
        "success": False,
        "production_mutation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "version": SPATIAL_INTERACTION_VERSION,
    }


_BROWSER_INTERACTION_KEYS = frozenset(
    {
        "version",
        "session_id",
        "scene_id",
        "scene_digest",
        "action",
        "target_entity_ids",
        "actor_ref",
        "input_source",
        "intent_slots",
        "metadata",
        "review_only",
        "requires_forge",
        "projection_only",
        "renderer_authority",
        "execution_authority",
        "patch_authority",
        "production_mutation",
        "automatic_merge",
        "human_review_required",
    }
)
_BROWSER_INPUT_SOURCES = frozenset({"MOUSE", "TOUCH", "KEYBOARD", "RAY", "CONTROLLER"})


def compile_browser_spatial_interaction(
    scene: SpatialSceneSnapshot,
    packet: Mapping[str, Any],
) -> SpatialInteractionIntent:
    """Validate a browser selection packet and compile the retained six-slot intent."""

    if not isinstance(packet, Mapping):
        raise ValueError("browser interaction packet must be an object")
    supplied = set(packet)
    if supplied != _BROWSER_INTERACTION_KEYS:
        raise ValueError(
            "browser interaction keys mismatch: "
            f"missing={sorted(_BROWSER_INTERACTION_KEYS - supplied)}, "
            f"extra={sorted(supplied - _BROWSER_INTERACTION_KEYS)}"
        )
    if packet["version"] != "AURA_SPATIAL_BROWSER_INTERACTION_V1":
        raise ValueError("unsupported browser interaction version")
    if packet["scene_id"] != scene.scene_id or packet["scene_digest"] != scene.scene_digest:
        raise ValueError("browser interaction is stale for the supplied scene")
    if packet["input_source"] not in _BROWSER_INPUT_SOURCES:
        raise ValueError("unsupported browser input source")
    for key, required in (
        ("review_only", True),
        ("projection_only", True),
        ("human_review_required", True),
        ("renderer_authority", False),
        ("execution_authority", False),
        ("patch_authority", False),
        ("production_mutation", False),
        ("automatic_merge", False),
    ):
        if packet[key] is not required:
            raise ValueError(f"browser interaction {key} boundary is invalid")
    metadata = packet["metadata"]
    if not isinstance(metadata, Mapping):
        raise ValueError("browser interaction metadata must be an object")
    authority_path = _find_authority_key(metadata)
    if authority_path is not None and authority_path != "metadata.renderer_input_is_authority":
        raise ValueError(f"browser interaction metadata cannot supply authority field: {authority_path}")
    expected_slots = _ACTION_SLOTS[SpatialInteractionAction(str(packet["action"]))]
    if dict(packet["intent_slots"]) != expected_slots:
        raise ValueError("browser interaction six-slot intent does not match action")
    protected_metadata = {
        **dict(metadata),
        "input_source": packet["input_source"],
        "browser_session_id": str(packet["session_id"]),
    }
    protected_metadata.pop("renderer_input_is_authority", None)
    return compile_spatial_interaction(
        scene,
        action=packet["action"],
        target_entity_ids=packet["target_entity_ids"],
        actor_ref=packet["actor_ref"],
        metadata=protected_metadata,
    )


def _normalize_metadata_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _find_authority_key(value: Any, path: str = "metadata") -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_metadata_key(key)
            child = f"{path}.{key}"
            if normalized in _AUTHORITY_KEY_TOKENS:
                return child
            finding = _find_authority_key(item, child)
            if finding is not None:
                return finding
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            finding = _find_authority_key(item, f"{path}[{index}]")
            if finding is not None:
                return finding
    return None


__all__ = [
    "MAX_INTERACTION_EVIDENCE_BYTES",
    "MAX_INTERACTION_METADATA_BYTES",
    "SPATIAL_INTERACTION_VERSION",
    "compile_browser_spatial_interaction",
    "compile_hotswap_request_guard",
    "compile_spatial_interaction",
]
