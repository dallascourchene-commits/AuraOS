"""Privacy-minimized Construction Arena projection into Aura Spatial scenes.

Construction state and authority remain owned by the existing Construction Arena.
This adapter emits immutable digest-bound representations only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import math
from pathlib import PurePosixPath
import re
from typing import Any
from urllib.parse import unquote, urlsplit

from aura_construction_runtime_binding import require_canonical_construction_runtime_packet
from aura_construction_state import ConstructionProjectState
from aura_event_contracts import canonical_json, stable_digest
from aura_spatial_arena import SpatialPrivacyClass
from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialAssetManifest,
    SpatialAssetType,
    SpatialEntity,
    SpatialEntityType,
    SpatialLink,
    SpatialSceneSnapshot,
    SpatialTruthClass,
)
from aura_spatial_scene import compile_spatial_scene

SPATIAL_CONSTRUCTION_VERSION = "AURA_SPATIAL_CONSTRUCTION_PROJECTION_V1"
MAX_CONSTRUCTION_SPATIAL_CANDIDATES = 64
MAX_CONSTRUCTION_FLOOR_PLAN_ASSETS = 32
MAX_CONSTRUCTION_PROJECTION_BYTES = 262_144
MAX_CONSTRUCTION_BLOCKERS_PER_CANDIDATE = 256
MAX_CONSTRUCTION_PUBLIC_IDENTIFIER_BYTES = 256
_MAX_CONSTRUCTION_ASSET_URI_BYTES = 4096
_PRIVACY_RANK = {"PUBLIC": 0, "PROJECT": 1, "RESTRICTED": 2, "SENSITIVE": 3}


def project_construction_state_to_scene(
    state: ConstructionProjectState,
    runtime_packet: Mapping[str, Any],
    *,
    purpose_digest: str,
    privacy_class: SpatialPrivacyClass | str = SpatialPrivacyClass.PROJECT,
    scene_id: str = "construction-spatial-scene",
    floor_plan_assets: Iterable[SpatialAssetManifest] = (),
) -> SpatialSceneSnapshot:
    """Project exact Construction digests, abstract scopes, and proposal status.

    No event records, evidence payloads, actor identities, claimant identities,
    consent references, sensor values, or survey-authoritative coordinates are copied.
    """

    if type(state) is not ConstructionProjectState:
        raise ValueError("state must be an exact ConstructionProjectState")
    state.__post_init__()
    if not isinstance(runtime_packet, Mapping):
        raise ValueError("runtime_packet must be a mapping")
    packet = dict(runtime_packet)
    _validate_runtime_packet(packet, state)
    privacy = (
        privacy_class if isinstance(privacy_class, SpatialPrivacyClass) else SpatialPrivacyClass(str(privacy_class))
    )
    purpose = _digest(purpose_digest, "purpose_digest")
    evaluation = dict(packet["evaluation"])
    raw_assessments = evaluation.get("assessments", ())
    if not isinstance(raw_assessments, (list, tuple)):
        raise ValueError("Construction assessments must be a bounded sequence")
    if len(raw_assessments) > MAX_CONSTRUCTION_SPATIAL_CANDIDATES:
        raise ValueError("Construction candidate projection exceeds its cap")
    if not all(isinstance(item, Mapping) for item in raw_assessments):
        raise ValueError("Construction assessments must contain mappings")
    assessments = tuple(dict(item) for item in raw_assessments)

    supplied_assets = _bounded_floor_plan_assets(floor_plan_assets)
    if not all(isinstance(item, SpatialAssetManifest) for item in supplied_assets):
        raise ValueError("floor_plan_assets must contain SpatialAssetManifest records")
    if privacy in {SpatialPrivacyClass.RESTRICTED, SpatialPrivacyClass.SENSITIVE} and supplied_assets:
        raise ValueError("restricted or sensitive Construction scenes cannot expose floor-plan geometry")
    for asset in supplied_assets:
        _validate_floor_plan_asset(asset, privacy)

    action = dict(packet["action_capsule"])
    target = dict(action.get("target") or {})
    scope_key = "/".join(str(target.get(key) or "") for key in ("project_id", "zone_id", "work_package_id"))
    public_scope = _scope_label(scope_key, privacy)
    safe_assessments = [
        _assessment_summary(item, privacy)
        for item in sorted(assessments, key=lambda item: str(item.get("candidate_id") or ""))
    ]
    require_canonical_construction_runtime_packet(packet, state_digest=state.state_digest)
    projection_payload = {
        "version": SPATIAL_CONSTRUCTION_VERSION,
        "project_ref": _project_ref(state.project_id, privacy),
        "state_digest": state.state_digest,
        "final_chain_digest": state.final_chain_digest,
        "scope_ref": public_scope,
        "evaluation_digest": str(evaluation.get("evaluation_digest") or ""),
        "route_class": str(evaluation.get("route_class") or ""),
        "recommended_candidate_ref": _candidate_ref(evaluation.get("recommended_candidate_id"), privacy),
        "next_authority_route": str(evaluation.get("next_authority_route") or ""),
        "active_event_count": len(state.active_event_ids),
        "conflict_count": len(state.conflicts),
        "candidate_summaries": safe_assessments,
        "precision_class": "ABSTRACT_NON_SURVEY",
        "event_records_included": False,
        "evidence_payloads_included": False,
        "person_level_data_included": False,
        "source_coordinates_included": False,
        "proposal_only": True,
        "human_release_required": True,
        "physical_work_authorized": False,
        "payment_released": False,
        "access_controlled": False,
    }
    encoded = canonical_json(projection_payload).encode("utf-8")
    if len(encoded) > MAX_CONSTRUCTION_PROJECTION_BYTES:
        raise ValueError("Construction spatial projection exceeds its byte cap")
    projection_digest = stable_digest(projection_payload, digest_size=32)

    root = CoordinateFrame(
        frame_id="construction-spatial-root",
        source_refs=("owner:aura_construction_state.ConstructionProjectState",),
        truth_class=SpatialTruthClass.DERIVED,
    )
    frame = CoordinateFrame(
        frame_id="construction-abstract-project",
        parent_frame_id=root.frame_id,
        source_refs=(f"construction-state:{state.state_digest}",),
        truth_class=SpatialTruthClass.PRESENTATION,
    )

    project_entity_id = _id("construction-project", projection_payload["project_ref"])
    scope_entity_id = _id("construction-scope", public_scope)
    entities: list[SpatialEntity] = [
        SpatialEntity(
            entity_id=project_entity_id,
            entity_type=SpatialEntityType.REGION,
            label=f"Construction project {projection_payload['project_ref']}",
            frame_id=frame.frame_id,
            source_refs=(f"construction-state:{state.state_digest}",),
            position=(0.0, 0.0, 0.0),
            truth_class=SpatialTruthClass.DERIVED,
            metadata={
                "domain_owner": "aura_construction_state",
                "state_digest": state.state_digest,
                "final_chain_digest": state.final_chain_digest,
                "active_event_count": len(state.active_event_ids),
                "conflict_count": len(state.conflicts),
                "privacy_class": privacy.value,
                "precision_class": "ABSTRACT_NON_SURVEY",
                "person_level_data_included": False,
                "proposal_only": True,
            },
        ),
        SpatialEntity(
            entity_id=scope_entity_id,
            entity_type=SpatialEntityType.REGION,
            label=f"Work scope {public_scope}",
            frame_id=frame.frame_id,
            source_refs=(f"construction-evaluation:{evaluation.get('evaluation_digest')}",),
            position=(0.0, 0.0, 2.0),
            truth_class=SpatialTruthClass.PRESENTATION,
            metadata={
                "domain_owner": "aura_construction_adapter",
                "scope_ref": public_scope,
                "route_class": str(evaluation.get("route_class") or ""),
                "next_authority_route": str(evaluation.get("next_authority_route") or ""),
                "human_release_required": True,
                "physical_work_authorized": False,
                "payment_released": False,
                "access_controlled": False,
                "source_coordinates_included": False,
            },
        ),
    ]
    links: list[SpatialLink] = [
        SpatialLink(
            link_id=_id("construction-link", {"project": project_entity_id, "scope": scope_entity_id}),
            source_entity_id=project_entity_id,
            target_entity_id=scope_entity_id,
            relation="CONTAINS_ABSTRACT_SCOPE",
            source_refs=(f"construction-state:{state.state_digest}",),
            truth_class=SpatialTruthClass.DERIVED,
        )
    ]

    for index, assessment in enumerate(safe_assessments):
        candidate_id = _id("construction-candidate", assessment["candidate_ref"])
        entities.append(
            SpatialEntity(
                entity_id=candidate_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=("Admissible proposal " if assessment["admissible"] else "Blocked proposal ")
                + assessment["candidate_ref"],
                frame_id=frame.frame_id,
                source_refs=(f"construction-evaluation:{evaluation.get('evaluation_digest')}",),
                position=((index % 8) * 2.0 - 7.0, 0.0, 5.0 + (index // 8) * 2.0),
                truth_class=SpatialTruthClass.DERIVED,
                metadata={
                    "domain_owner": "aura_construction_adapter",
                    **assessment,
                    "proposal_only": True,
                    "human_release_required": True,
                    "physical_work_authorized": False,
                    "probabilistic_signal_authoritative": False,
                },
            )
        )
        links.append(
            SpatialLink(
                link_id=_id("construction-link", {"scope": scope_entity_id, "candidate": candidate_id}),
                source_entity_id=scope_entity_id,
                target_entity_id=candidate_id,
                relation="HAS_PROPOSAL_OPTION" if assessment["admissible"] else "HAS_BLOCKED_PROPOSAL",
                source_refs=(f"construction-evaluation:{evaluation.get('evaluation_digest')}",),
                truth_class=SpatialTruthClass.DERIVED,
            )
        )

    summary_asset = SpatialAssetManifest(
        asset_id=_id("construction-projection-asset", projection_payload),
        asset_type=SpatialAssetType.ANNOTATION,
        uri=f"aura://construction/projection/{projection_digest[:32]}",
        media_type="application/vnd.aura.construction-spatial-summary+json",
        content_digest="sha256:" + hashlib.sha256(encoded).hexdigest(),
        byte_length=len(encoded),
        frame_id=frame.frame_id,
        bounds_min=(-8.0, 0.0, 0.0),
        bounds_max=(8.0, 0.0, max(6.0, 6.0 + (len(safe_assessments) // 8) * 2.0)),
        source_refs=(f"construction-state:{state.state_digest}", f"construction-projection:{projection_digest}"),
        truth_class=SpatialTruthClass.DERIVED,
        metadata={
            "embedded_payload": False,
            "projection_digest": projection_digest,
            "privacy_class": privacy.value,
            "precision_class": "ABSTRACT_NON_SURVEY",
            "event_records_included": False,
            "evidence_payloads_included": False,
            "person_level_data_included": False,
            "survey_authority": False,
        },
    )
    assets = (summary_asset, *supplied_assets)
    return compile_spatial_scene(
        scene_id=_id("scene", scene_id),
        purpose_digest=purpose,
        root_frame_id=root.frame_id,
        frames=(root, frame),
        assets=assets,
        entities=entities,
        links=links,
        source_refs=(
            "owner:aura_construction_state.ConstructionProjectState",
            "owner:aura_construction_adapter.ConstructionArenaAdapter",
            "projection:aura_spatial_construction.project_construction_state_to_scene",
            f"domain-state:{state.state_digest}",
            f"construction-evaluation:{evaluation.get('evaluation_digest')}",
        ),
        renderer_hints={
            "preferred_representation": "CONSTRUCTION_PROJECT_COORDINATION",
            "mandatory_fallback": "ACCESSIBLE_2D",
            "renderer_is_replaceable": True,
            "geometry_is_non_survey": True,
            "domain_owner_external": True,
            "version": SPATIAL_CONSTRUCTION_VERSION,
        },
    )


def _validate_runtime_packet(packet: dict[str, Any], state: ConstructionProjectState) -> None:
    required = {"action_capsule", "boundary_contract", "arena_lease", "evaluation", "state_digest"}
    if not required.issubset(packet):
        raise ValueError(f"Construction runtime packet missing keys: {sorted(required - set(packet))}")
    if packet["state_digest"] != state.state_digest:
        raise ValueError("Construction runtime packet is stale for the supplied state")
    for key, expected in (
        ("source_records_mutated", False),
        ("proposal_only", True),
        ("human_release_required", True),
        ("physical_work_authorized", False),
        ("payment_released", False),
        ("access_controlled", False),
        ("vsa_patch_authority", False),
    ):
        if packet.get(key) is not expected:
            raise ValueError(f"Construction runtime packet crossed boundary: {key}")
    action = packet["action_capsule"]
    boundary = packet["boundary_contract"]
    lease = packet["arena_lease"]
    evaluation = packet["evaluation"]
    if not all(isinstance(item, Mapping) for item in (action, boundary, lease, evaluation)):
        raise ValueError("Construction runtime contracts must be mappings")
    action_target = dict(action.get("target") or {})
    action_metadata = dict(action.get("metadata") or {})
    if (
        action.get("domain") != "construction"
        or action_target.get("state_digest") != state.state_digest
        or action_metadata.get("proposal_only") is not True
        or action_metadata.get("vsa_patch_authority") is not False
        or action_metadata.get("patch_authority") != "exact_source_spans_and_hashes_only"
    ):
        raise ValueError("Construction action capsule crossed its proposal boundary")
    forbidden = set(action.get("forbidden_actions") or ())
    for required_forbidden in (
        "authorize physical work",
        "release payment or transfer funds",
        "control physical access",
        "mutate authoritative project records",
    ):
        if required_forbidden not in forbidden:
            raise ValueError("Construction action capsule omitted a required authority prohibition")
    boundary_metadata = dict(boundary.get("metadata") or {})
    if (
        boundary.get("capsule_id") != action.get("capsule_id")
        or boundary_metadata.get("proposal_only") is not True
        or boundary_metadata.get("human_release_required") is not True
        or "authorized people govern" not in str(boundary.get("invariant") or "")
    ):
        raise ValueError("Construction boundary contract is stale or authority-crossing")
    lease_metadata = dict(lease.get("metadata") or {})
    if (
        lease.get("capsule_id") != action.get("capsule_id")
        or lease.get("mode") != "read_only"
        or lease.get("status") != "active"
        or lease_metadata.get("proposal_only") is not True
        or lease_metadata.get("human_release_required") is not True
    ):
        raise ValueError("Construction Arena lease is stale or authority-crossing")
    if evaluation.get("state_digest") != state.state_digest:
        raise ValueError("Construction evaluation is stale or malformed")
    if (
        evaluation.get("proposal_only") is not True
        or evaluation.get("human_release_required") is not True
        or evaluation.get("physical_work_authorized") is not False
        or evaluation.get("payment_released") is not False
        or evaluation.get("access_controlled") is not False
        or evaluation.get("vsa_patch_authority") is not False
    ):
        raise ValueError("Construction evaluation crossed its proposal boundary")
    evaluation_payload = dict(evaluation)
    observed_evaluation_digest = str(evaluation_payload.pop("evaluation_digest", ""))
    evaluation_payload.pop("evaluation_id", None)
    if observed_evaluation_digest != stable_digest(evaluation_payload):
        raise ValueError("Construction evaluation digest does not match its content")


def _assessment_summary(item: Mapping[str, Any], privacy: SpatialPrivacyClass) -> dict[str, Any]:
    blockers = item.get("blockers") or ()
    if not isinstance(blockers, (list, tuple)):
        raise ValueError("Construction candidate blockers must be a bounded sequence")
    if len(blockers) > MAX_CONSTRUCTION_BLOCKERS_PER_CANDIDATE:
        raise ValueError("Construction candidate blocker count exceeds its cap")
    return {
        "candidate_ref": _candidate_ref(item.get("candidate_id"), privacy),
        "admissible": item.get("admissible") is True,
        "blocker_count": len(blockers),
        "uncertainty_class": _uncertainty_class(item.get("uncertainty")),
    }


def _bounded_floor_plan_assets(values: Iterable[SpatialAssetManifest]) -> tuple[SpatialAssetManifest, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError("floor_plan_assets must be an iterable of manifests")
    result: list[SpatialAssetManifest] = []
    for item in values:
        result.append(item)
        if len(result) > MAX_CONSTRUCTION_FLOOR_PLAN_ASSETS:
            raise ValueError("floor_plan_assets exceeds the bounded asset cap")
    return tuple(result)


def _validate_local_asset_uri(value: Any) -> str:
    if type(value) is not str:
        raise ValueError("Construction floor-plan asset URI must be a string")
    uri = value.strip()
    if uri != value or not uri or len(uri.encode("utf-8")) > _MAX_CONSTRUCTION_ASSET_URI_BYTES:
        raise ValueError("Construction floor-plan asset URI is empty, padded, or oversized")
    if any(ord(char) < 32 or ord(char) == 127 for char in uri):
        raise ValueError("Construction floor-plan asset URI contains control characters")
    lowered = uri.casefold()
    if "\\" in uri or re.search(r"%(?:2f|5c)", lowered):
        raise ValueError("Construction floor-plan asset URI contains an encoded or aliased separator")
    decoded = unquote(uri)
    if decoded.count("/") != uri.count("/") or decoded.count("\\") != uri.count("\\"):
        raise ValueError("Construction floor-plan asset URI changes separators when decoded")
    parsed = urlsplit(uri)
    if parsed.scheme not in {"aura", "file"}:
        raise ValueError("Construction floor-plan assets must be local or Aura-addressed")
    scheme, separator, remainder = uri.partition(":")
    if separator != ":" or scheme != parsed.scheme or not remainder.startswith("//"):
        raise ValueError("Construction floor-plan asset URI must use a canonical hierarchical scheme")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError("Construction floor-plan asset URI cannot contain credentials, query, or fragment")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Construction floor-plan asset URI contains a malformed authority") from exc
    if port is not None:
        raise ValueError("Construction floor-plan asset URI cannot contain a port")
    if parsed.scheme == "aura":
        if not parsed.netloc or parsed.netloc != parsed.netloc.casefold():
            raise ValueError("Aura asset URI requires a canonical lowercase authority")
    elif parsed.netloc not in {"", "localhost"}:
        raise ValueError("file asset URI cannot name a remote host")
    path = parsed.path
    if not path.startswith("/") or "//" in path or (len(path) > 1 and path.endswith("/")):
        raise ValueError("Construction floor-plan asset URI path is not canonical")
    if any(part in {".", ".."} for part in PurePosixPath(path).parts):
        raise ValueError("Construction floor-plan asset URI path contains a dot segment")
    return uri


def _validate_floor_plan_asset(asset: SpatialAssetManifest, privacy: SpatialPrivacyClass) -> None:
    if asset.asset_type not in {
        SpatialAssetType.MESH,
        SpatialAssetType.POINT_CLOUD,
        SpatialAssetType.GAUSSIAN_SPLAT,
        SpatialAssetType.PLANE,
        SpatialAssetType.ANNOTATION,
    }:
        raise ValueError("unsupported Construction floor-plan asset type")
    _validate_local_asset_uri(asset.uri)
    metadata = dict(asset.metadata)
    asset_privacy = str(metadata.get("spatial_privacy_class") or "PROJECT")
    if asset_privacy not in _PRIVACY_RANK:
        raise ValueError("floor-plan asset has an unknown privacy class")
    if _PRIVACY_RANK[asset_privacy] > _PRIVACY_RANK[privacy.value]:
        raise ValueError("floor-plan asset privacy exceeds the Spatial Arena purpose")
    if metadata.get("survey_authority") is not False:
        raise ValueError("floor-plan assets must explicitly deny survey authority")
    if metadata.get("person_level_data_included") is not False:
        raise ValueError("floor-plan assets cannot include person-level data")


def _scope_label(scope_key: str, privacy: SpatialPrivacyClass) -> str:
    text = _bounded_identifier_text(scope_key, "Construction scope")
    return text if privacy is SpatialPrivacyClass.PROJECT else "scope:" + stable_digest(text, digest_size=8)


def _project_ref(project_id: str, privacy: SpatialPrivacyClass) -> str:
    text = _bounded_identifier_text(project_id, "Construction project_id")
    return text if privacy is SpatialPrivacyClass.PROJECT else "project:" + stable_digest(text, digest_size=8)


def _candidate_ref(value: Any, privacy: SpatialPrivacyClass) -> str:
    text = str(value or "")
    if not text:
        return ""
    text = _bounded_identifier_text(text, "Construction candidate_id")
    return text if privacy is SpatialPrivacyClass.PROJECT else "candidate:" + stable_digest(text, digest_size=8)


def _uncertainty_class(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if not math.isfinite(number):
        return "UNKNOWN"
    if number <= 0.2:
        return "LOW"
    if number <= 0.5:
        return "MEDIUM"
    return "HIGH"


def _bounded_identifier_text(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text or len(text.encode("utf-8")) > MAX_CONSTRUCTION_PUBLIC_IDENTIFIER_BYTES:
        raise ValueError(f"{name} is empty or exceeds its byte cap")
    return text


def _digest(value: Any, name: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{name} must be a 64-character lowercase digest")
    return text


def _id(prefix: str, value: Any) -> str:
    return f"{prefix}:{stable_digest(value, digest_size=12)}"


__all__ = [
    "SPATIAL_CONSTRUCTION_VERSION",
    "project_construction_state_to_scene",
]
