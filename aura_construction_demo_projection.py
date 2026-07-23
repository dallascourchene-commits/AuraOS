"""Immutable G5 spatial projection for the asset-bound Construction demo.

The canonical Construction state and adapter remain the domain owners.  This
module first executes Aura's existing Construction projection, then expands that
verified projection with local asset-pack geometry and synthetic demo overlays.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aura_construction_demo_contracts import (
    ConstructionDemoAssetBinding,
    ConstructionDemoRepresentation,
)
from aura_construction_demo_fixture import ConstructionDemoProjectFixture
from aura_construction_runtime_binding import require_canonical_construction_runtime_packet
from aura_event_contracts import stable_digest
from aura_spatial_arena import SpatialPrivacyClass
from aura_spatial_construction import project_construction_state_to_scene
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
from aura_spatial_importers.contracts import GAUSSIAN_REPRESENTATION_DIGEST_VERSION
from aura_spatial_scene import compile_spatial_scene

CONSTRUCTION_DEMO_PROJECTION_VERSION = "AURA_CONSTRUCTION_DEMO_PROJECTION_V2"
MAX_DEMO_PROJECTION_ENTITIES = 512
MAX_DEMO_PROJECTION_LINKS = 2048
MAX_DEMO_PROJECTION_ASSETS = 256

_ASSET_TYPES = {
    ConstructionDemoRepresentation.IFC_SOURCE.value: SpatialAssetType.MESH,
    ConstructionDemoRepresentation.MESH_GLB.value: SpatialAssetType.MESH,
    ConstructionDemoRepresentation.FLOOR_PLAN_SVG.value: SpatialAssetType.PLANE,
    ConstructionDemoRepresentation.GAUSSIAN_PLY.value: SpatialAssetType.POINT_CLOUD,
    ConstructionDemoRepresentation.GAUSSIAN_SPZ.value: SpatialAssetType.GAUSSIAN_SPLAT,
}


def _id(prefix: str, payload: Any) -> str:
    return f"{prefix}-{stable_digest(payload)[:24]}"


def _privacy(value: SpatialPrivacyClass | str) -> SpatialPrivacyClass:
    return value if isinstance(value, SpatialPrivacyClass) else SpatialPrivacyClass(str(value))


def _ref(
    value: str,
    privacy: SpatialPrivacyClass,
    export_scope: str | None = None,
) -> str:
    if privacy is SpatialPrivacyClass.PROJECT:
        return value
    if export_scope is not None:
        return _export_ref(value, export_scope)
    return stable_digest({"construction_demo_public_ref": value})[:16]


def _export_digest(value: str, export_scope: str) -> str:
    return stable_digest(
        {
            "construction_demo_public_export_scope": export_scope,
            "value": value,
        },
        digest_size=32,
    )


def _export_ref(value: str, export_scope: str) -> str:
    return _export_digest(value, export_scope)[:16]


def _projected_asset_id(
    asset_id: str,
    privacy: SpatialPrivacyClass,
    export_scope: str,
) -> str:
    if privacy is SpatialPrivacyClass.PROJECT:
        return asset_id
    return f"public-asset-{_export_digest(f'asset:{asset_id}', export_scope)[:24]}"


def _asset_manifest(
    binding: ConstructionDemoAssetBinding,
    *,
    frame_id: str,
    projected_asset_id: str,
    privacy: SpatialPrivacyClass,
    export_scope: str,
) -> SpatialAssetManifest:
    project_visible = privacy is SpatialPrivacyClass.PROJECT
    representation_digest = (
        binding.representation_digest
        if project_visible
        else _export_digest(f"representation:{binding.representation_digest}", export_scope)
    )
    import_receipt_digest = (
        binding.import_receipt_digest
        if project_visible
        else _export_digest(f"import-receipt:{binding.import_receipt_digest}", export_scope)
    )
    content_digest = (
        binding.content_digest if project_visible else _export_digest(f"content:{binding.content_digest}", export_scope)
    )
    metadata: dict[str, Any] = {
        "representation": binding.representation,
        "representation_digest": representation_digest,
        "import_receipt_digest": import_receipt_digest,
        "coordinate_system": binding.coordinate_system,
        "unit_scale_meters": binding.unit_scale_meters,
        "survey_authority": False,
        "person_level_data_included": False,
        "projection_only": True,
        "source_transform": {
            "translation": [0.0, 0.0, 0.0],
            "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
            "scale": [1.0, 1.0, 1.0],
        },
        "presentation_transform": {
            "translation": [0.0, 0.0, 0.0],
            "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
            "scale": [1.0, 1.0, 1.0],
        },
    }
    if binding.representation == ConstructionDemoRepresentation.GAUSSIAN_SPZ.value:
        metadata.update(
            {
                "representation_digest_version": GAUSSIAN_REPRESENTATION_DIGEST_VERSION,
                "representation_bytes_per_splat": 60,
                "sh_degree": 0,
                "gaussian_sh_degree": 0,
                "gaussian_color_space": "SPZ_INTERNAL_WIDE_RGB",
            }
        )
    source_refs = (
        tuple(
            sorted(
                set(
                    (
                        *(_export_ref(ref, export_scope) for ref in binding.source_refs),
                        _export_ref(f"construction-demo-asset:{binding.asset_id}", export_scope),
                        _export_ref(
                            f"representation:{binding.representation_digest}",
                            export_scope,
                        ),
                        _export_ref(
                            f"import-receipt:{binding.import_receipt_digest}",
                            export_scope,
                        ),
                    )
                )
            )
        )
        if not project_visible
        else tuple(
            sorted(
                set(
                    (
                        *binding.source_refs,
                        f"construction-demo-asset:{binding.asset_id}",
                        f"representation:{binding.representation_digest}",
                        f"import-receipt:{binding.import_receipt_digest}",
                    )
                )
            )
        )
    )
    return SpatialAssetManifest(
        asset_id=projected_asset_id,
        asset_type=_ASSET_TYPES[binding.representation],
        uri=(binding.uri if project_visible else f"aura://public/{projected_asset_id}"),
        media_type=binding.media_type,
        content_digest=f"sha256:{content_digest}",
        byte_length=binding.byte_length,
        frame_id=frame_id,
        bounds_min=binding.bounds_min,
        bounds_max=binding.bounds_max,
        source_refs=source_refs,
        truth_class=SpatialTruthClass.PRESENTATION,
        metadata=metadata,
    )


def _entity(
    entity_id: str,
    entity_type: SpatialEntityType,
    label: str,
    frame_id: str,
    *,
    source_refs: tuple[str, ...],
    metadata: Mapping[str, Any],
    asset_ids: tuple[str, ...] = (),
    position: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> SpatialEntity:
    return SpatialEntity(
        entity_id=entity_id,
        entity_type=entity_type,
        label=label,
        frame_id=frame_id,
        asset_ids=asset_ids,
        source_refs=source_refs,
        position=position,
        truth_class=SpatialTruthClass.PRESENTATION,
        metadata=dict(metadata),
    )


def _link(
    source: str,
    target: str,
    relation: str,
    *,
    source_refs: tuple[str, ...],
    metadata: Mapping[str, Any] | None = None,
) -> SpatialLink:
    return SpatialLink(
        link_id=_id("construction-demo-link", {"source": source, "target": target, "relation": relation}),
        source_entity_id=source,
        target_entity_id=target,
        relation=relation,
        source_refs=source_refs,
        truth_class=SpatialTruthClass.PRESENTATION,
        metadata=dict(metadata or {}),
    )


def project_construction_demo_to_scene(
    fixture: ConstructionDemoProjectFixture,
    runtime_packet: Mapping[str, Any],
    *,
    purpose_digest: str,
    privacy_class: SpatialPrivacyClass | str = SpatialPrivacyClass.PROJECT,
    scene_id: str = "construction-demo-spatial-scene-v2",
) -> SpatialSceneSnapshot:
    """Compose the complete immutable G5 scene from canonical G4 inputs."""

    if type(fixture) is not ConstructionDemoProjectFixture:
        raise ValueError("fixture must be an exact ConstructionDemoProjectFixture")
    fixture.__post_init__()
    if not isinstance(runtime_packet, Mapping):
        raise ValueError("runtime_packet must be a mapping")
    packet = dict(runtime_packet)
    require_canonical_construction_runtime_packet(packet, state_digest=fixture.state.state_digest)
    privacy = _privacy(privacy_class)
    if privacy in {SpatialPrivacyClass.RESTRICTED, SpatialPrivacyClass.SENSITIVE}:
        raise ValueError("restricted or sensitive Construction demo scenes cannot expose geometry")
    public_export_scope = stable_digest(
        {
            "projection_version": CONSTRUCTION_DEMO_PROJECTION_VERSION,
            "scene_id": scene_id,
            "purpose_digest": purpose_digest,
        },
        digest_size=32,
    )

    def graph_id(prefix: str, payload: Any) -> str:
        if privacy is SpatialPrivacyClass.PROJECT:
            return _id(prefix, payload)
        return _id(
            f"public-{prefix}",
            {"export_scope": public_export_scope, "payload": payload},
        )

    def graph_frame_id(kind: str, value: str) -> str:
        if privacy is SpatialPrivacyClass.PROJECT:
            return value
        return _id(
            f"public-{kind}-frame",
            {"export_scope": public_export_scope, "value": value},
        )

    def public_text(value: str, generic: str) -> str:
        return value if privacy is SpatialPrivacyClass.PROJECT else generic

    baseline = project_construction_state_to_scene(
        fixture.state,
        packet,
        purpose_digest=purpose_digest,
        privacy_class=privacy,
        scene_id=f"{scene_id}-canonical-base",
    )
    asset_pack = fixture.asset_pack
    projected_asset_ids = {
        binding.asset_id: _projected_asset_id(
            binding.asset_id,
            privacy,
            public_export_scope,
        )
        for binding in asset_pack.assets
    }
    storeys = tuple(sorted(asset_pack.storeys, key=lambda item: (item.ordinal, item.storey_id)))
    assets_by_storey: dict[str, list[ConstructionDemoAssetBinding]] = {item.storey_id: [] for item in storeys}
    for binding in asset_pack.assets:
        assets_by_storey[binding.storey_id].append(binding)

    root_frame_id = graph_frame_id("site-root", "construction-site-root")
    building_frame_id = graph_frame_id("building", asset_pack.building_frame_id)
    storey_frame_ids = {item.storey_id: graph_frame_id("storey", item.frame_id) for item in storeys}
    frames: list[CoordinateFrame] = [
        CoordinateFrame(
            frame_id=root_frame_id,
            source_refs=(_ref(f"construction-state:{fixture.state.state_digest}", privacy, public_export_scope),)
            if privacy is not SpatialPrivacyClass.PROJECT
            else (f"construction-state:{fixture.state.state_digest}",),
            truth_class=SpatialTruthClass.DERIVED,
        ),
        CoordinateFrame(
            frame_id=building_frame_id,
            parent_frame_id=root_frame_id,
            source_refs=tuple(
                _ref(ref, privacy, public_export_scope)
                for ref in (
                    f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
                    f"source-manifest:{asset_pack.source_manifest.source_manifest_digest}",
                )
            )
            if privacy is not SpatialPrivacyClass.PROJECT
            else (
                f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
                f"source-manifest:{asset_pack.source_manifest.source_manifest_digest}",
            ),
            truth_class=SpatialTruthClass.PRESENTATION,
        ),
    ]
    for storey in storeys:
        frames.append(
            CoordinateFrame(
                frame_id=storey_frame_ids[storey.storey_id],
                parent_frame_id=building_frame_id,
                translation=(0.0, float(storey.elevation_m), 0.0),
                source_refs=tuple(
                    _ref(ref, privacy, public_export_scope)
                    for ref in (
                        f"construction-demo-storey:{storey.storey_digest}",
                        *storey.source_refs,
                    )
                )
                if privacy is not SpatialPrivacyClass.PROJECT
                else (
                    f"construction-demo-storey:{storey.storey_digest}",
                    *storey.source_refs,
                ),
                truth_class=SpatialTruthClass.PRESENTATION,
            )
        )

    spatial_assets = tuple(
        _asset_manifest(
            binding,
            frame_id=storey_frame_ids[binding.storey_id],
            projected_asset_id=projected_asset_ids[binding.asset_id],
            privacy=privacy,
            export_scope=public_export_scope,
        )
        for binding in asset_pack.assets
    )
    if len(spatial_assets) > MAX_DEMO_PROJECTION_ASSETS:
        raise ValueError("Construction demo projection exceeds its asset cap")

    entities: list[SpatialEntity] = []
    links: list[SpatialLink] = []
    building_entity_id = graph_id("construction-building", asset_pack.building_id)
    entities.append(
        _entity(
            building_entity_id,
            SpatialEntityType.REGION,
            public_text(f"Construction building {asset_pack.building_id}", "Construction building"),
            building_frame_id,
            source_refs=tuple(
                _ref(ref, privacy, public_export_scope)
                for ref in (
                    f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
                    f"construction-state:{fixture.state.state_digest}",
                )
            )
            if privacy is not SpatialPrivacyClass.PROJECT
            else (
                f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
                f"construction-state:{fixture.state.state_digest}",
            ),
            metadata={
                "building_ref": _ref(asset_pack.building_id, privacy, public_export_scope),
                "storey_count": len(storeys),
                "asset_pack_digest": (
                    asset_pack.asset_pack_digest
                    if privacy is SpatialPrivacyClass.PROJECT
                    else _export_digest(
                        f"asset-pack:{asset_pack.asset_pack_digest}",
                        public_export_scope,
                    )
                ),
                "state_digest": (
                    fixture.state.state_digest
                    if privacy is SpatialPrivacyClass.PROJECT
                    else _export_digest(
                        f"state:{fixture.state.state_digest}",
                        public_export_scope,
                    )
                ),
                "precision_class": "NON_SURVEY_PRESENTATION",
                "person_level_data_included": False,
                "projection_only": True,
            },
        )
    )

    storey_entities: dict[str, str] = {}
    for storey in storeys:
        entity_id = graph_id("construction-storey", storey.storey_id)
        storey_entities[storey.storey_id] = entity_id
        storey_asset_ids = tuple(
            sorted(projected_asset_ids[item.asset_id] for item in assets_by_storey[storey.storey_id])
        )
        entities.append(
            _entity(
                entity_id,
                SpatialEntityType.ASSET_INSTANCE,
                (storey.name if privacy is SpatialPrivacyClass.PROJECT else f"Storey {storey.ordinal + 1}"),
                storey_frame_ids[storey.storey_id],
                asset_ids=storey_asset_ids,
                source_refs=(_ref(f"construction-demo-storey:{storey.storey_digest}", privacy, public_export_scope),)
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-storey:{storey.storey_digest}",),
                metadata={
                    "storey_ref": _ref(storey.storey_id, privacy, public_export_scope),
                    "ordinal": storey.ordinal,
                    "source_elevation_m": storey.elevation_m,
                    "asset_ids": list(storey_asset_ids),
                    "survey_authority": False,
                    "projection_only": True,
                    "source_transform": {
                        "translation": [0.0, storey.elevation_m, 0.0],
                        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                        "scale": [1.0, 1.0, 1.0],
                    },
                    "presentation_transform": {
                        "translation": [0.0, 0.0, 0.0],
                        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                        "scale": [1.0, 1.0, 1.0],
                    },
                },
            )
        )
        links.append(
            _link(
                building_entity_id,
                entity_id,
                "CONTAINS_STOREY",
                source_refs=(_ref(f"construction-demo-storey:{storey.storey_digest}", privacy, public_export_scope),)
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-storey:{storey.storey_digest}",),
            )
        )

    zone_entities: dict[str, str] = {}
    package_entities: dict[str, str] = {}
    package_frames: dict[str, str] = {}
    for package in fixture.work_packages:
        storey_entity_id = storey_entities[package.storey_id]
        package_frame_id = storey_frame_ids[package.storey_id]
        package_frames[package.work_package_id] = package_frame_id
        zone_entity_id = zone_entities.get(package.zone_id)
        if zone_entity_id is None:
            zone_entity_id = graph_id("construction-zone", package.zone_id)
            zone_entities[package.zone_id] = zone_entity_id
            entities.append(
                _entity(
                    zone_entity_id,
                    SpatialEntityType.REGION,
                    public_text(f"Zone {package.zone_id}", "Zone"),
                    package_frame_id,
                    source_refs=(_ref(f"construction-scope:{package.scope.scope_key}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-scope:{package.scope.scope_key}",),
                    metadata={
                        "zone_ref": _ref(package.zone_id, privacy, public_export_scope),
                        "storey_ref": _ref(package.storey_id, privacy, public_export_scope),
                        "projection_only": True,
                    },
                )
            )
            links.append(
                _link(
                    storey_entity_id,
                    zone_entity_id,
                    "CONTAINS_ZONE",
                    source_refs=(_ref(f"construction-scope:{package.scope.scope_key}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-scope:{package.scope.scope_key}",),
                )
            )
        package_entity_id = graph_id("construction-work-package", package.work_package_id)
        package_entities[package.work_package_id] = package_entity_id
        entities.append(
            _entity(
                package_entity_id,
                SpatialEntityType.DOMAIN_NODE,
                public_text(package.title, "Work package"),
                package_frame_id,
                source_refs=tuple(
                    _ref(ref, privacy, public_export_scope)
                    for ref in (
                        f"construction-scope:{package.scope.scope_key}",
                        f"construction-state:{fixture.state.state_digest}",
                    )
                )
                if privacy is not SpatialPrivacyClass.PROJECT
                else (
                    f"construction-scope:{package.scope.scope_key}",
                    f"construction-state:{fixture.state.state_digest}",
                ),
                metadata={
                    "work_package_ref": _ref(package.work_package_id, privacy, public_export_scope),
                    "storey_ref": _ref(package.storey_id, privacy, public_export_scope),
                    "zone_ref": _ref(package.zone_id, privacy, public_export_scope),
                    "trade_ref": _ref(package.trade_id, privacy, public_export_scope),
                    "status_overlay": package.status,
                    "planned_start_day": package.planned_start_day,
                    "planned_finish_day": package.planned_finish_day,
                    "professional_release_required": package.professional_release_required,
                    "geometry_mutated_by_status": False,
                    "projection_only": True,
                },
            )
        )
        links.extend(
            (
                _link(
                    zone_entity_id,
                    package_entity_id,
                    "HAS_WORK_PACKAGE",
                    source_refs=(_ref(f"construction-scope:{package.scope.scope_key}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-scope:{package.scope.scope_key}",),
                ),
                _link(
                    package_entity_id,
                    storey_entity_id,
                    "LOCATED_ON_STOREY",
                    source_refs=(_ref(f"construction-scope:{package.scope.scope_key}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-scope:{package.scope.scope_key}",),
                ),
            )
        )

    for package in fixture.work_packages:
        source_entity = package_entities[package.work_package_id]
        for dependency_id in package.dependency_ids:
            links.append(
                _link(
                    source_entity,
                    package_entities[dependency_id],
                    "DEPENDS_ON",
                    source_refs=(_ref(f"construction-schedule:{fixture.fixture_digest}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-schedule:{fixture.fixture_digest}",),
                )
            )

    evidence_entities: dict[str, str] = {}
    for package in fixture.work_packages:
        for evidence_ref in package.evidence_refs:
            evidence_entity_id = evidence_entities.get(evidence_ref)
            if evidence_entity_id is None:
                evidence_entity_id = graph_id("construction-evidence-requirement", evidence_ref)
                evidence_entities[evidence_ref] = evidence_entity_id
                entities.append(
                    _entity(
                        evidence_entity_id,
                        SpatialEntityType.LABEL,
                        public_text(f"Evidence requirement {evidence_ref}", "Evidence requirement"),
                        building_frame_id,
                        source_refs=(_ref(f"construction-evidence:{evidence_ref}", privacy, public_export_scope),)
                        if privacy is not SpatialPrivacyClass.PROJECT
                        else (f"construction-evidence:{evidence_ref}",),
                        metadata={
                            "evidence_ref": _ref(evidence_ref, privacy, public_export_scope),
                            "payload_included": False,
                            "person_level_data_included": False,
                            "projection_only": True,
                        },
                    )
                )
            links.append(
                _link(
                    package_entities[package.work_package_id],
                    evidence_entity_id,
                    "REQUIRES_EVIDENCE",
                    source_refs=(_ref(f"construction-evidence:{evidence_ref}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-evidence:{evidence_ref}",),
                )
            )

    trade_entities: dict[str, str] = {}
    for trade in fixture.trades:
        entity_id = graph_id("construction-trade", trade.trade_id)
        trade_entities[trade.trade_id] = entity_id
        entities.append(
            _entity(
                entity_id,
                SpatialEntityType.LABEL,
                public_text(trade.name.title(), "Trade"),
                building_frame_id,
                source_refs=(_ref(f"construction-demo-trade:{trade.trade_id}", privacy, public_export_scope),)
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-trade:{trade.trade_id}",),
                metadata={
                    "overlay_kind": "TRADE",
                    "trade_ref": _ref(trade.trade_id, privacy, public_export_scope),
                    "subcontractor_ref": _ref(trade.subcontractor_id, privacy, public_export_scope),
                    "person_level_data_included": False,
                    "projection_only": True,
                },
            )
        )
    for activity in fixture.work_history:
        activity_entity_id = graph_id("construction-activity", activity.activity_id)
        package_entity_id = package_entities[activity.work_package_id]
        entities.append(
            _entity(
                activity_entity_id,
                SpatialEntityType.DOMAIN_NODE,
                public_text(activity.note, "Work activity"),
                package_frames[activity.work_package_id],
                source_refs=(_ref(f"construction-demo-activity:{activity.activity_id}", privacy, public_export_scope),)
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-activity:{activity.activity_id}",),
                metadata={
                    "activity_ref": _ref(activity.activity_id, privacy, public_export_scope),
                    "day": activity.day,
                    "status_overlay": activity.status,
                    "person_level_data_included": False,
                    "projection_only": True,
                },
            )
        )
        links.extend(
            (
                _link(
                    package_entity_id,
                    activity_entity_id,
                    "COMPLETED_IN",
                    source_refs=(
                        _ref(f"construction-demo-activity:{activity.activity_id}", privacy, public_export_scope),
                    )
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-demo-activity:{activity.activity_id}",),
                ),
                _link(
                    package_entity_id,
                    trade_entities[activity.trade_id],
                    "VISITED_BY_TRADE",
                    source_refs=(
                        _ref(f"construction-demo-activity:{activity.activity_id}", privacy, public_export_scope),
                    )
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-demo-activity:{activity.activity_id}",),
                    metadata={"exact_worker_location_included": False},
                ),
            )
        )

    for budget in fixture.budget_lines:
        entity_id = graph_id("construction-budget", budget.budget_line_id)
        entities.append(
            _entity(
                entity_id,
                SpatialEntityType.DOMAIN_NODE,
                public_text(budget.description, "Budget line"),
                package_frames[budget.work_package_id],
                source_refs=(_ref(f"construction-demo-budget:{budget.budget_line_id}", privacy, public_export_scope),)
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-budget:{budget.budget_line_id}",),
                metadata={
                    "overlay_kind": "BUDGET",
                    "budget_line_ref": _ref(budget.budget_line_id, privacy, public_export_scope),
                    "committed_cad": budget.committed_cad,
                    "forecast_cad": budget.forecast_cad,
                    "actual_cad": budget.actual_cad,
                    "truth_class": budget.truth_class,
                    "projection_only": True,
                },
            )
        )
        links.append(
            _link(
                package_entities[budget.work_package_id],
                entity_id,
                "AFFECTS_BUDGET",
                source_refs=(_ref(f"construction-demo-budget:{budget.budget_line_id}", privacy, public_export_scope),)
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-budget:{budget.budget_line_id}",),
            )
        )

    for rule in fixture.rules:
        for package_id in rule.applies_to_work_package_ids:
            entity_id = graph_id(
                "construction-rule",
                {"rule_id": rule.rule_id, "work_package_id": package_id},
            )
            entities.append(
                _entity(
                    entity_id,
                    SpatialEntityType.DOMAIN_NODE,
                    public_text(rule.title, "Synthetic rule"),
                    package_frames[package_id],
                    source_refs=(_ref(f"construction-demo-rule:{rule.rule_id}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-demo-rule:{rule.rule_id}",),
                    metadata={
                        "overlay_kind": "SYNTHETIC_RULE",
                        "rule_ref": _ref(rule.rule_id, privacy, public_export_scope),
                        "work_package_ref": _ref(package_id, privacy, public_export_scope),
                        "requirement": public_text(rule.requirement, ""),
                        "truth_class": rule.truth_class,
                        "legal_authority": False,
                        "regulatory_authority": False,
                        "jurisdiction_claimed": "none",
                        "projection_only": True,
                    },
                )
            )
            links.append(
                _link(
                    package_entities[package_id],
                    entity_id,
                    "REQUIRES_SYNTHETIC_RULE",
                    source_refs=(_ref(f"construction-demo-rule:{rule.rule_id}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-demo-rule:{rule.rule_id}",),
                )
            )

    for inspection in fixture.inspections:
        entity_id = graph_id("construction-inspection", inspection.inspection_id)
        entities.append(
            _entity(
                entity_id,
                SpatialEntityType.DOMAIN_NODE,
                public_text(inspection.title, "Inspection"),
                package_frames[inspection.work_package_id],
                source_refs=(
                    _ref(f"construction-demo-inspection:{inspection.inspection_id}", privacy, public_export_scope),
                )
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-inspection:{inspection.inspection_id}",),
                metadata={
                    "overlay_kind": "INSPECTION",
                    "inspection_ref": _ref(inspection.inspection_id, privacy, public_export_scope),
                    "status_overlay": inspection.status,
                    "scheduled_day": inspection.scheduled_day,
                    "truth_class": inspection.truth_class,
                    "projection_only": True,
                },
            )
        )
        links.append(
            _link(
                package_entities[inspection.work_package_id],
                entity_id,
                "REQUIRES_INSPECTION",
                source_refs=(
                    _ref(f"construction-demo-inspection:{inspection.inspection_id}", privacy, public_export_scope),
                )
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-inspection:{inspection.inspection_id}",),
            )
        )

    for hazard in fixture.hazards:
        entity_id = graph_id("construction-hazard", hazard.hazard_id)
        entities.append(
            _entity(
                entity_id,
                SpatialEntityType.DOMAIN_NODE,
                public_text(hazard.title, "Hazard"),
                package_frames[hazard.work_package_id],
                source_refs=(_ref(f"construction-demo-hazard:{hazard.hazard_id}", privacy, public_export_scope),)
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-hazard:{hazard.hazard_id}",),
                metadata={
                    "hazard_ref": _ref(hazard.hazard_id, privacy, public_export_scope),
                    "severity": hazard.severity,
                    "active": hazard.active,
                    "truth_class": hazard.truth_class,
                    "projection_only": True,
                },
            )
        )
        links.append(
            _link(
                package_entities[hazard.work_package_id],
                entity_id,
                "BLOCKED_BY",
                source_refs=(_ref(f"construction-demo-hazard:{hazard.hazard_id}", privacy, public_export_scope),)
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-hazard:{hazard.hazard_id}",),
            )
        )

    crane_entity_id = graph_id("construction-crane-window", "crane-window-01")
    entities.append(
        _entity(
            crane_entity_id,
            SpatialEntityType.DOMAIN_NODE,
            "Synthetic crane window",
            building_frame_id,
            source_refs=(_ref("construction-demo-logistics:crane-window-01", privacy, public_export_scope),)
            if privacy is not SpatialPrivacyClass.PROJECT
            else ("construction-demo-logistics:crane-window-01",),
            metadata={
                "crane_window_ref": _ref("crane-window-01", privacy, public_export_scope),
                "available": True,
                "truth_class": "SYNTHETIC_DEMO_SCHEDULE",
                "projection_only": True,
            },
        )
    )
    for package in fixture.work_packages:
        if package.crane_window_id:
            links.append(
                _link(
                    package_entities[package.work_package_id],
                    crane_entity_id,
                    "USES_CRANE_WINDOW",
                    source_refs=(_ref("construction-demo-logistics:crane-window-01", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else ("construction-demo-logistics:crane-window-01",),
                )
            )

    for alternative in fixture.alternatives:
        entity_id = graph_id("construction-alternative", alternative.alternative_id)
        entities.append(
            _entity(
                entity_id,
                SpatialEntityType.DOMAIN_NODE,
                public_text(alternative.title, "Review alternative"),
                building_frame_id,
                source_refs=(
                    _ref(f"construction-demo-alternative:{alternative.alternative_id}", privacy, public_export_scope),
                )
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-alternative:{alternative.alternative_id}",),
                metadata={
                    "alternative_ref": _ref(alternative.alternative_id, privacy, public_export_scope),
                    "admissible": alternative.admissible,
                    "blocker_codes": (
                        list(alternative.blocker_codes) if privacy is SpatialPrivacyClass.PROJECT else []
                    ),
                    "recommended_for_human_review": alternative.recommended_for_human_review,
                    "projected_time_delta_hours": alternative.projected_time_delta_hours,
                    "projected_cost_delta_cad": alternative.projected_cost_delta_cad,
                    "projected_idle_delta_hours": alternative.projected_idle_delta_hours,
                    "automatic_execution": False,
                    "projection_only": True,
                },
            )
        )
        relation = "HAS_PROPOSAL_OPTION" if alternative.admissible else "HAS_BLOCKED_PROPOSAL"
        links.append(
            _link(
                package_entities[alternative.source_work_package_id],
                entity_id,
                relation,
                source_refs=(
                    _ref(f"construction-demo-alternative:{alternative.alternative_id}", privacy, public_export_scope),
                )
                if privacy is not SpatialPrivacyClass.PROJECT
                else (f"construction-demo-alternative:{alternative.alternative_id}",),
            )
        )
        for target_id in alternative.target_work_package_ids:
            links.extend(
                (
                    _link(
                        entity_id,
                        package_entities[target_id],
                        "AFFECTS_SCHEDULE",
                        source_refs=(
                            _ref(
                                f"construction-demo-alternative:{alternative.alternative_id}",
                                privacy,
                                public_export_scope,
                            ),
                        )
                        if privacy is not SpatialPrivacyClass.PROJECT
                        else (f"construction-demo-alternative:{alternative.alternative_id}",),
                    ),
                    _link(
                        entity_id,
                        package_entities[target_id],
                        "AFFECTS_BUDGET",
                        source_refs=(
                            _ref(
                                f"construction-demo-alternative:{alternative.alternative_id}",
                                privacy,
                                public_export_scope,
                            ),
                        )
                        if privacy is not SpatialPrivacyClass.PROJECT
                        else (f"construction-demo-alternative:{alternative.alternative_id}",),
                    ),
                )
            )

    for package in fixture.work_packages:
        if package.professional_release_required:
            links.append(
                _link(
                    package_entities[package.work_package_id],
                    building_entity_id,
                    "REQUIRES_PROFESSIONAL_RELEASE",
                    source_refs=(_ref(f"construction-scope:{package.scope.scope_key}", privacy, public_export_scope),)
                    if privacy is not SpatialPrivacyClass.PROJECT
                    else (f"construction-scope:{package.scope.scope_key}",),
                    metadata={"human_review_required": True},
                )
            )

    if len(entities) > MAX_DEMO_PROJECTION_ENTITIES:
        raise ValueError("Construction demo projection exceeds its entity cap")
    if len(links) > MAX_DEMO_PROJECTION_LINKS:
        raise ValueError("Construction demo projection exceeds its link cap")

    scene_source_refs = (
        "owner:aura_construction_state.ConstructionProjectState",
        "owner:aura_construction_adapter.ConstructionArenaAdapter",
        "owner:aura_construction_demo_contracts.ConstructionDemoAssetPack",
        "projection:aura_spatial_construction.project_construction_state_to_scene",
        "projection:aura_construction_demo_projection.project_construction_demo_to_scene",
        f"canonical-base-scene:{baseline.scene_digest}",
        f"construction-state:{fixture.state.state_digest}",
        f"construction-runtime:{packet['evaluation']['evaluation_digest']}",
        f"construction-demo-fixture:{fixture.fixture_digest}",
        f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
    )
    if privacy is not SpatialPrivacyClass.PROJECT:
        scene_source_refs = tuple(_ref(ref, privacy, public_export_scope) for ref in scene_source_refs)

    return compile_spatial_scene(
        scene_id=graph_id("construction-demo-scene-v2", scene_id),
        purpose_digest=purpose_digest,
        root_frame_id=root_frame_id,
        frames=frames,
        assets=spatial_assets,
        entities=entities,
        links=links,
        source_refs=scene_source_refs,
        renderer_hints={
            "version": CONSTRUCTION_DEMO_PROJECTION_VERSION,
            "preferred_representation": "HYBRID_MESH_GAUSSIAN",
            "mandatory_fallback": "ACCESSIBLE_2D",
            "mesh_pass": True,
            "degree_zero_gaussian_pass": True,
            "floor_plan_overlay": True,
            "work_status_overlay": True,
            "timeline_projection": True,
            "budget_projection": True,
            "synthetic_rule_projection": True,
            "exploded_view_is_presentation_only": True,
            "source_asset_coordinates_immutable": True,
            "renderer_is_replaceable": True,
            "external_network_required": False,
            "person_level_data_included": False,
            "survey_authority": False,
        },
    )


__all__ = [
    "CONSTRUCTION_DEMO_PROJECTION_VERSION",
    "MAX_DEMO_PROJECTION_ASSETS",
    "MAX_DEMO_PROJECTION_ENTITIES",
    "MAX_DEMO_PROJECTION_LINKS",
    "project_construction_demo_to_scene",
]
