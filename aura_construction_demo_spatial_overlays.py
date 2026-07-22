"""Privacy-minimized G5 Construction overlays for canonical Spatial scenes."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aura_construction_demo_fixture import ConstructionDemoProjectFixture
from aura_construction_runtime_binding import require_canonical_construction_runtime_packet
from aura_event_contracts import stable_digest
from aura_spatial_contracts import (
    SpatialEntity,
    SpatialEntityType,
    SpatialLink,
    SpatialTruthClass,
)

CONSTRUCTION_DEMO_SPATIAL_OVERLAYS_VERSION = "AURA_CONSTRUCTION_DEMO_SPATIAL_OVERLAYS_V1"


def _id(prefix: str, value: object) -> str:
    return f"{prefix}-{stable_digest(value, digest_size=16)}"


def _building_entity_id(fixture: ConstructionDemoProjectFixture) -> str:
    return _id("construction-building", fixture.asset_pack.building_id)


def _storey_entity_id(storey_id: str) -> str:
    return _id("construction-storey", storey_id)


def _link(
    source: str,
    target: str,
    relation: str,
    fixture: ConstructionDemoProjectFixture,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> SpatialLink:
    return SpatialLink(
        link_id=_id(
            "construction-link",
            {"source": source, "target": target, "relation": relation},
        ),
        source_entity_id=source,
        target_entity_id=target,
        relation=relation,
        source_refs=(f"construction-demo-fixture:{fixture.fixture_digest}",),
        truth_class=SpatialTruthClass.DERIVED,
        metadata=dict(metadata or {"projection_only": True}),
    )


def project_construction_demo_overlays(
    fixture: ConstructionDemoProjectFixture,
    runtime_packet: Mapping[str, Any],
) -> tuple[tuple[SpatialEntity, ...], tuple[SpatialLink, ...]]:
    """Project project-state summaries without copying raw events or person data."""
    if type(fixture) is not ConstructionDemoProjectFixture:
        raise ValueError("fixture must be an exact ConstructionDemoProjectFixture")
    fixture.__post_init__()
    if not isinstance(runtime_packet, Mapping):
        raise ValueError("runtime_packet must be a mapping")
    packet = dict(runtime_packet)
    require_canonical_construction_runtime_packet(
        packet,
        state_digest=fixture.state.state_digest,
    )
    evaluation = packet.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise ValueError("runtime_packet evaluation must be a mapping")
    assessments_raw = evaluation.get("assessments")
    if type(assessments_raw) not in {list, tuple} or not all(
        isinstance(item, Mapping) for item in assessments_raw
    ):
        raise ValueError("runtime_packet assessments must be a bounded sequence of mappings")
    assessments = {
        str(item.get("candidate_id") or ""): dict(item) for item in assessments_raw
    }
    if set(assessments) != {item.candidate_id for item in fixture.candidates}:
        raise ValueError("runtime_packet assessments do not match fixture candidates")

    building_entity_id = _building_entity_id(fixture)
    storey_by_id = {item.storey_id: item for item in fixture.asset_pack.storeys}
    package_by_id = {item.package_id: item for item in fixture.work_packages}
    candidate_by_id = {item.candidate_id: item for item in fixture.candidates}

    entities: list[SpatialEntity] = []
    links: list[SpatialLink] = []

    zone_entities: dict[str, str] = {}
    for storey in sorted(fixture.asset_pack.storeys, key=lambda item: item.storey_id):
        entity_id = _id("construction-zone", storey.storey_id)
        zone_entities[storey.storey_id] = entity_id
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.REGION,
                label=f"{storey.name} work zone",
                frame_id=storey.frame_id,
                source_refs=(
                    f"construction-demo-fixture:{fixture.fixture_digest}",
                    f"construction-storey:{storey.storey_digest}",
                ),
                truth_class=SpatialTruthClass.PRESENTATION,
                metadata={
                    "storey_ref": stable_digest(storey.storey_id, digest_size=16),
                    "source_geometry_mutated": False,
                    "status_overlay_separate": True,
                    "survey_authority": False,
                    "person_level_data_included": False,
                    "projection_only": True,
                },
            )
        )
        links.append(
            _link(
                building_entity_id,
                entity_id,
                "CONTAINS_ZONE",
                fixture,
            )
        )

    trade_entities: dict[str, str] = {}
    for index, trade in enumerate(fixture.trades):
        entity_id = _id("construction-trade", trade.trade_id)
        trade_entities[trade.trade_id] = entity_id
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=trade.label,
                frame_id=fixture.asset_pack.building_frame_id,
                source_refs=(f"construction-demo-fixture:{fixture.fixture_digest}",),
                position=(float(index % 6) * 2.0, 0.0, -4.0 - float(index // 6) * 2.0),
                truth_class=SpatialTruthClass.DERIVED,
                metadata={
                    "trade_ref": stable_digest(trade.trade_id, digest_size=16),
                    "subcontractor_ref": stable_digest(trade.subcontractor_id, digest_size=16),
                    "synthetic": True,
                    "person_level_data_included": False,
                    "projection_only": True,
                },
            )
        )

    package_entities: dict[str, str] = {}
    for index, package in enumerate(fixture.work_packages):
        storey = storey_by_id[package.scope.zone_id]
        entity_id = _id("construction-work-package", package.package_id)
        package_entities[package.package_id] = entity_id
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=package.title,
                frame_id=storey.frame_id,
                source_refs=(
                    f"construction-demo-fixture:{fixture.fixture_digest}",
                    f"construction-state:{fixture.state.state_digest}",
                ),
                position=(float(index % 4) * 1.5, 0.25, float(index // 4) * 1.5),
                truth_class=SpatialTruthClass.DERIVED,
                metadata={
                    "package_ref": stable_digest(package.package_id, digest_size=16),
                    "status": package.status,
                    "trade_ref": stable_digest(package.trade_id, digest_size=16),
                    "required_evidence_label": package.required_evidence_label,
                    "inspection_required": package.inspection_required,
                    "professional_release_required": package.professional_release_required,
                    "crane_window_required": package.crane_window_required,
                    "status_overlay": True,
                    "base_geometry_mutated": False,
                    "physical_work_authorized": False,
                    "payment_released": False,
                    "access_controlled": False,
                    "person_level_data_included": False,
                    "projection_only": True,
                },
            )
        )
        links.extend(
            (
                _link(
                    zone_entities[package.scope.zone_id],
                    entity_id,
                    "HAS_WORK_PACKAGE",
                    fixture,
                ),
                _link(
                    entity_id,
                    _storey_entity_id(package.scope.zone_id),
                    "LOCATED_ON_STOREY",
                    fixture,
                ),
                _link(
                    entity_id,
                    trade_entities[package.trade_id],
                    "VISITED_BY_TRADE",
                    fixture,
                ),
            )
        )

    for package in fixture.work_packages:
        package_entity_id = package_entities[package.package_id]
        for dependency_id in package.dependency_package_ids:
            links.append(
                _link(
                    package_entity_id,
                    package_entities[dependency_id],
                    "DEPENDS_ON",
                    fixture,
                )
            )

        if package.status == "BLOCKED":
            blocker_id = _id("construction-blocker", package.package_id)
            entities.append(
                SpatialEntity(
                    entity_id=blocker_id,
                    entity_type=SpatialEntityType.DOMAIN_NODE,
                    label=f"Evidence blocker for {package.title}",
                    frame_id=storey_by_id[package.scope.zone_id].frame_id,
                    source_refs=(f"construction-state:{fixture.state.state_digest}",),
                    position=(0.0, 1.0, 0.0),
                    truth_class=SpatialTruthClass.DERIVED,
                    metadata={
                        "required_evidence_label": package.required_evidence_label,
                        "raw_evidence_payload_included": False,
                        "dispositive_release_present": False,
                        "physical_work_authorized": False,
                        "projection_only": True,
                    },
                )
            )
            links.append(_link(package_entity_id, blocker_id, "BLOCKED_BY", fixture))
            links.append(_link(package_entity_id, blocker_id, "REQUIRES_EVIDENCE", fixture))

        if package.inspection_required:
            inspection_id = _id("construction-inspection", package.package_id)
            entities.append(
                SpatialEntity(
                    entity_id=inspection_id,
                    entity_type=SpatialEntityType.DOMAIN_NODE,
                    label=f"Inspection gate for {package.title}",
                    frame_id=storey_by_id[package.scope.zone_id].frame_id,
                    source_refs=(f"construction-demo-fixture:{fixture.fixture_digest}",),
                    truth_class=SpatialTruthClass.DERIVED,
                    metadata={
                        "inspection_status": "SYNTHETIC_AWAITING_REVIEW",
                        "inspection_authority_claimed": False,
                        "projection_only": True,
                    },
                )
            )
            links.append(
                _link(package_entity_id, inspection_id, "REQUIRES_INSPECTION", fixture)
            )

        if package.professional_release_required:
            release_id = _id("construction-professional-release", package.package_id)
            entities.append(
                SpatialEntity(
                    entity_id=release_id,
                    entity_type=SpatialEntityType.DOMAIN_NODE,
                    label=f"Professional review gate for {package.title}",
                    frame_id=storey_by_id[package.scope.zone_id].frame_id,
                    source_refs=(f"construction-state:{fixture.state.state_digest}",),
                    truth_class=SpatialTruthClass.DERIVED,
                    metadata={
                        "release_status": "HUMAN_REVIEW_REQUIRED",
                        "professional_certification_claimed": False,
                        "projection_only": True,
                    },
                )
            )
            links.append(
                _link(
                    package_entity_id,
                    release_id,
                    "REQUIRES_PROFESSIONAL_RELEASE",
                    fixture,
                )
            )

    crane_package = next(
        (item for item in fixture.work_packages if item.crane_window_required and item.status == "ACTIVE"),
        None,
    )
    if crane_package is not None:
        for package in fixture.work_packages:
            if package.crane_window_required and package.package_id != crane_package.package_id:
                links.append(
                    _link(
                        package_entities[package.package_id],
                        package_entities[crane_package.package_id],
                        "USES_CRANE_WINDOW",
                        fixture,
                    )
                )

    timeline_entities: dict[str, str] = {}
    for entry in fixture.timeline:
        entity_id = _id("construction-timeline", entry.timeline_id)
        timeline_entities[entry.package_id] = entity_id
        package = package_by_id[entry.package_id]
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=f"Timeline: {package.title}",
                frame_id=fixture.asset_pack.building_frame_id,
                source_refs=(f"construction-demo-fixture:{fixture.fixture_digest}",),
                truth_class=SpatialTruthClass.DERIVED,
                metadata={
                    "start_hour": entry.start_hour,
                    "end_hour": entry.end_hour,
                    "status": entry.status,
                    "synthetic_projection": True,
                    "schedule_truth_owner": False,
                    "projection_only": True,
                },
            )
        )
        links.append(
            _link(
                package_entities[entry.package_id],
                entity_id,
                "AFFECTS_SCHEDULE",
                fixture,
            )
        )
        if entry.status == "COMPLETED":
            links.append(
                _link(
                    package_entities[entry.package_id],
                    entity_id,
                    "COMPLETED_IN",
                    fixture,
                )
            )

    budget_entities: dict[str, str] = {}
    for line in fixture.budget_lines:
        entity_id = _id("construction-budget", line.budget_line_id)
        budget_entities[line.package_id] = entity_id
        package = package_by_id[line.package_id]
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=f"Budget: {package.title}",
                frame_id=fixture.asset_pack.building_frame_id,
                source_refs=(f"construction-demo-fixture:{fixture.fixture_digest}",),
                truth_class=SpatialTruthClass.DERIVED,
                metadata={
                    "baseline_cad": line.baseline_cad,
                    "projected_cad": line.projected_cad,
                    "currency": line.currency,
                    "synthetic_projection": True,
                    "payment_released": False,
                    "financial_truth_owner": False,
                    "projection_only": True,
                },
            )
        )
        links.append(
            _link(
                package_entities[line.package_id],
                entity_id,
                "AFFECTS_BUDGET",
                fixture,
            )
        )

    for rule in fixture.rules:
        entity_id = _id("construction-rule", rule.rule_id)
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=rule.label,
                frame_id=fixture.asset_pack.building_frame_id,
                source_refs=(f"construction-demo-fixture:{fixture.fixture_digest}",),
                truth_class=SpatialTruthClass.HYPOTHESIS,
                metadata={
                    "truth_class": rule.truth_class,
                    "legal_authority": False,
                    "regulatory_authority": False,
                    "jurisdiction_claimed": "none",
                    "projection_only": True,
                },
            )
        )
        for package_id in rule.package_ids:
            links.append(
                _link(
                    package_entities[package_id],
                    entity_id,
                    "REQUIRES_SYNTHETIC_RULE",
                    fixture,
                )
            )

    blocked_package_entity_id = package_entities[fixture.blocked_package_id]
    for candidate_id, candidate in sorted(candidate_by_id.items()):
        assessment = assessments[candidate_id]
        entity_id = _id("construction-proposal", candidate_id)
        admissible = assessment.get("admissible") is True
        entities.append(
            SpatialEntity(
                entity_id=entity_id,
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label=("Proposal option: " if admissible else "Blocked proposal: ") + candidate.title,
                frame_id=fixture.asset_pack.building_frame_id,
                source_refs=(
                    f"construction-evaluation:{evaluation.get('evaluation_digest')}",
                    f"construction-demo-fixture:{fixture.fixture_digest}",
                ),
                truth_class=SpatialTruthClass.HYPOTHESIS,
                metadata={
                    "candidate_ref": stable_digest(candidate_id, digest_size=16),
                    "admissible": admissible,
                    "blocker_count": len(tuple(assessment.get("blockers") or ())),
                    "balanced_score": assessment.get("balanced_score"),
                    "uncertainty": assessment.get("uncertainty"),
                    "projected_time_delta_hours": candidate.projected_time_delta_hours,
                    "projected_cost_delta_cad": candidate.projected_cost_delta_cad,
                    "projected_idle_delta_hours": candidate.projected_idle_delta_hours,
                    "human_release_required": True,
                    "physical_work_authorized": False,
                    "probabilistic_signal_authoritative": False,
                    "projection_only": True,
                },
            )
        )
        links.append(
            _link(
                blocked_package_entity_id,
                entity_id,
                "HAS_PROPOSAL_OPTION" if admissible else "HAS_BLOCKED_PROPOSAL",
                fixture,
            )
        )
        links.append(
            _link(
                entity_id,
                timeline_entities[fixture.blocked_package_id],
                "AFFECTS_SCHEDULE",
                fixture,
            )
        )
        links.append(
            _link(
                entity_id,
                budget_entities[fixture.blocked_package_id],
                "AFFECTS_BUDGET",
                fixture,
            )
        )

    return (
        tuple(sorted(entities, key=lambda item: item.entity_id)),
        tuple(sorted(links, key=lambda item: item.link_id)),
    )


__all__ = [
    "CONSTRUCTION_DEMO_SPATIAL_OVERLAYS_VERSION",
    "project_construction_demo_overlays",
]
