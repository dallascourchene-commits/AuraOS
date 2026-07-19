"""Fail-closed compilation of spatial UI actions into six-slot Aura intents."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any

from aura_event_contracts import stable_digest
from aura_spatial_contracts import (
    SpatialInteractionAction,
    SpatialInteractionIntent,
    SpatialSceneSnapshot,
)

SPATIAL_INTERACTION_VERSION = "AURA_SPATIAL_INTERACTION_V1"
_ACTOR_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_AUTHORITY_KEYS = frozenset(
    {
        "approval",
        "authorization",
        "authority_decision",
        "automatic_commit",
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
        "renderer_input_is_authority",
        "verifier_receipt",
    }
)

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
        action_value = (
            action
            if isinstance(action, SpatialInteractionAction)
            else SpatialInteractionAction(str(action))
        )
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

    targets = tuple(
        sorted(
            {
                str(item).strip()
                for item in target_entity_ids
                if str(item).strip()
            }
        )
    )
    if not targets:
        raise ValueError("target_entity_ids must not be empty")
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

    requires_forge = action_value is SpatialInteractionAction.PREPARE_REPAIR_REQUEST
    body = {
        "scene_id": scene.scene_id,
        "scene_digest": scene.scene_digest,
        "action": action_value.value,
        "targets": list(targets),
        "actor_ref": actor,
        "source_refs": list(ordered_refs),
    }
    protected_metadata = {
        **supplied_metadata,
        "actor_ref": actor,
        "renderer_input_is_authority": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "production_mutation": False,
    }
    return SpatialInteractionIntent(
        interaction_id=(
            "spatial-interaction:" + stable_digest(body, digest_size=12)
        ),
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
        raise ValueError(
            "proposed_change_digest must be a 64-character lowercase hex digest"
        )
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


def _find_authority_key(value: Any, path: str = "metadata") -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            child = f"{path}.{key}"
            if normalized in _AUTHORITY_KEYS:
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
    "SPATIAL_INTERACTION_VERSION",
    "compile_hotswap_request_guard",
    "compile_spatial_interaction",
]
