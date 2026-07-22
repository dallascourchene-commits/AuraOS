"""Deterministic G4 fixture builder bound to an admitted Construction asset pack."""
from __future__ import annotations

from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionAuthorityRoute,
    ConstructionCoordinationCandidate,
)
from aura_construction_contracts import (
    GENESIS_CHAIN_DIGEST,
    ConstructionAuthorityClass,
    ConstructionClaim,
    ConstructionEvent,
    ConstructionEvidence,
    ConstructionEvidenceClass,
    ConstructionPrivacyClass,
    ConstructionScope,
)
from aura_construction_demo_contracts import ConstructionDemoAssetPack
from aura_construction_demo_fixture import (
    CONSTRUCTION_DEMO_REQUIRED_TRADES,
    ConstructionDemoBudgetLine,
    ConstructionDemoProjectFixture,
    ConstructionDemoRule,
    ConstructionDemoTimelineEntry,
    ConstructionDemoTrade,
    ConstructionDemoWorkPackage,
)
from aura_construction_state import replay_construction_events
from aura_event_contracts import ActorType, MeasurementClass, stable_digest

_TRACE_ID = "construction-tuwien-g4-synthetic-fixture"
_ACTOR_ID = "synthetic-construction-demo-builder"


def _evidence(
    *,
    scope: ConstructionScope,
    subject_id: str,
    evidence_class: ConstructionEvidenceClass,
    source_ref: str,
    payload_label: str,
    observed_at: float,
    authority_class: ConstructionAuthorityClass,
    confidence: float = 0.9,
) -> ConstructionEvidence:
    return ConstructionEvidence.create(
        scope=scope,
        subject_id=subject_id,
        evidence_class=evidence_class,
        source_ref=source_ref,
        payload_digest=stable_digest({"synthetic_construction_demo": payload_label}),
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=confidence,
        authority_class=authority_class,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        observed_at=observed_at,
        expires_at=10_000.0,
    )


def _claim(
    *,
    scope: ConstructionScope,
    subject_id: str,
    predicate: str,
    value_label: str,
    claimant_id: str,
    evidence: ConstructionEvidence,
    created_at: float,
    authority_class: ConstructionAuthorityClass,
    confidence: float = 0.85,
) -> ConstructionClaim:
    return ConstructionClaim.create(
        scope=scope,
        subject_id=subject_id,
        predicate=predicate,
        value_digest=stable_digest({"synthetic_construction_demo": value_label}),
        claimant_id=claimant_id,
        evidence_refs=(evidence.evidence_id,),
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=confidence,
        authority_class=authority_class,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        created_at=created_at,
        expires_at=10_000.0,
    )


def _canonical_state(
    asset_pack: ConstructionDemoAssetPack,
    records: tuple[ConstructionEvidence | ConstructionClaim, ...],
):
    ledger_id = f"construction/{asset_pack.building_id}"
    events: list[ConstructionEvent] = []
    previous = GENESIS_CHAIN_DIGEST
    for sequence, record in enumerate(records, start=1):
        record_time = (
            record.observed_at if type(record) is ConstructionEvidence else record.created_at
        )
        event = ConstructionEvent.create(
            ledger_id=ledger_id,
            sequence_number=sequence,
            previous_chain_digest=previous,
            trace_id=_TRACE_ID,
            record=record,
            actor_id=_ACTOR_ID,
            actor_type=ActorType.TOOL,
            parent_event_ids=(events[-1].event_id,) if events else (),
            created_at=max(float(sequence), record_time),
        )
        events.append(event)
        previous = event.chain_digest
    return replay_construction_events(tuple(events))


def _trades() -> tuple[ConstructionDemoTrade, ...]:
    labels = {
        "asbestos-abatement": "Asbestos Abatement",
        "crane-logistics": "Crane and Logistics",
        "demolition": "Demolition",
        "electrical": "Electrical",
        "fire-protection": "Fire Protection",
        "general-contractor": "General Contractor",
        "inspection": "Inspection",
        "mechanical": "Mechanical",
        "plumbing": "Plumbing",
        "roofing": "Roofing",
        "structural": "Structural",
        "temporary-labour": "Temporary Labour",
    }
    return tuple(
        ConstructionDemoTrade(
            trade_id=trade_id,
            subcontractor_id=f"synthetic-{trade_id}-subcontractor",
            label=labels[trade_id],
        )
        for trade_id in sorted(CONSTRUCTION_DEMO_REQUIRED_TRADES)
    )


def _package(
    project_id: str,
    storey_id: str,
    package_id: str,
    trade_id: str,
    title: str,
    status: str,
    *,
    dependencies: tuple[str, ...] = (),
    evidence: str = "Synthetic project record",
    inspection: bool = False,
    professional_release: bool = False,
    crane: bool = False,
    alternatives: tuple[str, ...] = (),
) -> ConstructionDemoWorkPackage:
    return ConstructionDemoWorkPackage(
        package_id=package_id,
        scope=ConstructionScope(project_id, storey_id, package_id),
        trade_id=trade_id,
        title=title,
        status=status,
        dependency_package_ids=tuple(sorted(dependencies)),
        required_evidence_label=evidence,
        inspection_required=inspection,
        professional_release_required=professional_release,
        crane_window_required=crane,
        alternative_package_ids=tuple(sorted(alternatives)),
    )


def build_construction_demo_project_fixture(
    asset_pack: ConstructionDemoAssetPack,
) -> ConstructionDemoProjectFixture:
    """Build the complete fictional G4 scenario against discovered storey IDs."""
    if type(asset_pack) is not ConstructionDemoAssetPack:
        raise ValueError("asset_pack must be an exact ConstructionDemoAssetPack")
    asset_pack.__post_init__()
    storeys = tuple(sorted(asset_pack.storeys, key=lambda item: (item.ordinal, item.storey_id)))
    if len(storeys) < 4:
        raise ValueError("G4 fixture requires at least four discovered storeys")

    project_id = asset_pack.building_id
    logistics_storey = storeys[0].storey_id
    electrical_storey = storeys[-3].storey_id
    alternate_storey = storeys[-2].storey_id
    blocked_storey = storeys[-1].storey_id

    blocked_scope = ConstructionScope(project_id, blocked_storey, "upper-drilling")
    alternate_scope = ConstructionScope(project_id, alternate_storey, "released-preparation")
    electrical_scope = ConstructionScope(project_id, electrical_storey, "electrical-isolation")
    logistics_scope = ConstructionScope(project_id, logistics_storey, "crane-window")

    asbestos_sensor = _evidence(
        scope=blocked_scope,
        subject_id="upper-drilling-asbestos-boundary",
        evidence_class=ConstructionEvidenceClass.SENSOR,
        source_ref="synthetic:asbestos-screening-signal",
        payload_label="informative sensor signal without dispositive clearance",
        observed_at=1.0,
        authority_class=ConstructionAuthorityClass.INFORMATIVE,
        confidence=0.96,
    )
    asbestos_clearance_claim = _claim(
        scope=blocked_scope,
        subject_id="upper-drilling-asbestos-boundary",
        predicate="asbestos_clearance_confirmed",
        value_label="unsupported clearance claim from informative signal",
        claimant_id="synthetic-general-contractor",
        evidence=asbestos_sensor,
        created_at=2.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
        confidence=0.95,
    )
    alternate_release = _evidence(
        scope=alternate_scope,
        subject_id="released-preparation-zone",
        evidence_class=ConstructionEvidenceClass.OWNER_RECORD,
        source_ref="synthetic:owner-preparation-release",
        payload_label="alternate storey released for preparation",
        observed_at=3.0,
        authority_class=ConstructionAuthorityClass.OWNER,
    )
    alternate_ready_claim = _claim(
        scope=alternate_scope,
        subject_id="released-preparation-zone",
        predicate="zone_available_for_preparation",
        value_label="alternate preparation package ready for review",
        claimant_id="synthetic-owner-representative",
        evidence=alternate_release,
        created_at=4.0,
        authority_class=ConstructionAuthorityClass.OWNER,
    )
    electrical_test = _evidence(
        scope=electrical_scope,
        subject_id="electrical-isolation-package",
        evidence_class=ConstructionEvidenceClass.TEST_RESULT,
        source_ref="synthetic:electrical-isolation-test",
        payload_label="electrical isolation professionally evidenced",
        observed_at=5.0,
        authority_class=ConstructionAuthorityClass.PROFESSIONAL,
    )
    electrical_ready_claim = _claim(
        scope=electrical_scope,
        subject_id="electrical-isolation-package",
        predicate="electrical_isolation_confirmed",
        value_label="electrical package ready for governed review",
        claimant_id="synthetic-qualified-electrician",
        evidence=electrical_test,
        created_at=6.0,
        authority_class=ConstructionAuthorityClass.PROFESSIONAL,
    )
    crane_record = _evidence(
        scope=logistics_scope,
        subject_id="synthetic-crane-window",
        evidence_class=ConstructionEvidenceClass.CONTRACTOR_RECORD,
        source_ref="synthetic:crane-booking-window",
        payload_label="crane window available for demonstration",
        observed_at=7.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
    )
    crane_ready_claim = _claim(
        scope=logistics_scope,
        subject_id="synthetic-crane-window",
        predicate="crane_window_reserved",
        value_label="synthetic crane slot available",
        claimant_id="synthetic-logistics-supervisor",
        evidence=crane_record,
        created_at=8.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
    )

    records: tuple[ConstructionEvidence | ConstructionClaim, ...] = (
        asbestos_sensor,
        asbestos_clearance_claim,
        alternate_release,
        alternate_ready_claim,
        electrical_test,
        electrical_ready_claim,
        crane_record,
        crane_ready_claim,
    )
    state = _canonical_state(asset_pack, records)

    unsafe = ConstructionCoordinationCandidate.create(
        scope=blocked_scope,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Continue blocked upper-storey drilling",
        summary="Continue drilling without dispositive asbestos evidence; this option must remain hard-blocked.",
        required_claim_ids=(asbestos_clearance_claim.claim_id,),
        authority_route=ConstructionAuthorityRoute.PROFESSIONAL_REVIEW_REQUIRED,
        projected_time_delta_hours=-16.0,
        projected_cost_delta_cad=-4000.0,
        projected_idle_delta_hours=-40.0,
        safety_risk=0.98,
        deadline_risk=0.10,
        evidence_quality=0.20,
        reversibility=0.05,
    )
    safe = ConstructionCoordinationCandidate.create(
        scope=blocked_scope,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Resequence crew to released preparation",
        summary="Preserve the drilling hold and advance the released preparation package for human review.",
        required_claim_ids=(alternate_ready_claim.claim_id,),
        authority_route=ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED,
        projected_time_delta_hours=-10.0,
        projected_cost_delta_cad=1500.0,
        projected_idle_delta_hours=-32.0,
        safety_risk=0.12,
        deadline_risk=0.18,
        evidence_quality=0.90,
        reversibility=0.92,
    )
    electrical = ConstructionCoordinationCandidate.create(
        scope=blocked_scope,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Advance professionally evidenced electrical isolation",
        summary="Advance the electrical package while retaining the drilling hold and professional review boundary.",
        required_claim_ids=(electrical_ready_claim.claim_id,),
        authority_route=ConstructionAuthorityRoute.PROFESSIONAL_REVIEW_REQUIRED,
        projected_time_delta_hours=-8.0,
        projected_cost_delta_cad=500.0,
        projected_idle_delta_hours=-24.0,
        safety_risk=0.08,
        deadline_risk=0.24,
        evidence_quality=0.94,
        reversibility=0.80,
    )
    crane_temp = ConstructionCoordinationCandidate.create(
        scope=blocked_scope,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Use crane window and temporary labour",
        summary="Use the synthetic crane reservation and temporary labour on released logistics work at a declared mock cost.",
        required_claim_ids=(alternate_ready_claim.claim_id, crane_ready_claim.claim_id),
        authority_route=ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED,
        projected_time_delta_hours=-14.0,
        projected_cost_delta_cad=9000.0,
        projected_idle_delta_hours=-48.0,
        safety_risk=0.20,
        deadline_risk=0.12,
        evidence_quality=0.87,
        reversibility=0.65,
    )
    candidates = tuple(sorted((unsafe, safe, electrical, crane_temp), key=lambda item: item.candidate_id))

    ids = {
        "blocked": "wp-upper-drilling-blocked",
        "ready": "wp-released-preparation",
        "electrical": "wp-electrical-professional-release",
        "crane": "wp-crane-window-active",
        "inspection": "wp-inspection-awaiting",
        "completed": "wp-demolition-completed",
        "rework": "wp-fire-protection-rework",
        "delayed": "wp-plumbing-delayed",
        "not_started": "wp-roofing-not-started",
    }
    work_packages = tuple(
        sorted(
            (
                _package(project_id, blocked_storey, ids["blocked"], "asbestos-abatement", "Upper-storey drilling", "BLOCKED", evidence="Dispositive asbestos clearance", professional_release=True, alternatives=(ids["ready"], ids["electrical"], ids["crane"])),
                _package(project_id, alternate_storey, ids["ready"], "general-contractor", "Released preparation", "READY_FOR_REVIEW", evidence="Synthetic owner release"),
                _package(project_id, electrical_storey, ids["electrical"], "electrical", "Electrical isolation", "AWAITING_PROFESSIONAL_RELEASE", evidence="Professional electrical test", professional_release=True),
                _package(project_id, logistics_storey, ids["crane"], "crane-logistics", "Crane and material window", "ACTIVE", dependencies=(ids["ready"],), evidence="Synthetic crane reservation", crane=True),
                _package(project_id, alternate_storey, ids["inspection"], "inspection", "Preparation inspection", "AWAITING_INSPECTION", dependencies=(ids["ready"],), inspection=True),
                _package(project_id, storeys[0].storey_id, ids["completed"], "demolition", "Completed selective demolition", "COMPLETED"),
                _package(project_id, storeys[1].storey_id, ids["rework"], "fire-protection", "Fire stopping rework", "REWORK_REQUIRED", inspection=True),
                _package(project_id, storeys[2].storey_id, ids["delayed"], "plumbing", "Plumbing rough-in", "DELAYED", dependencies=(ids["completed"],)),
                _package(project_id, blocked_storey, ids["not_started"], "roofing", "Roof protection", "NOT_STARTED", dependencies=(ids["crane"],), crane=True),
            ),
            key=lambda item: item.package_id,
        )
    )
    timeline = tuple(
        ConstructionDemoTimelineEntry(
            timeline_id=f"timeline-{index:02d}-{package.package_id}",
            package_id=package.package_id,
            start_hour=float((index - 1) * 24),
            end_hour=float(index * 24),
            status=package.status,
        )
        for index, package in enumerate(work_packages, start=1)
    )
    budget_lines = tuple(
        ConstructionDemoBudgetLine(
            budget_line_id=f"budget-{package.package_id}",
            package_id=package.package_id,
            baseline_cad=float(index * 25_000),
            projected_cad=float(index * 25_000 + (9_000 if package.package_id == ids["crane"] else 0)),
        )
        for index, package in enumerate(work_packages, start=1)
    )
    rules = tuple(
        sorted(
            (
                ConstructionDemoRule(rule_id="rule-asbestos-evidence-gate", label="Synthetic asbestos evidence gate", package_ids=(ids["blocked"],)),
                ConstructionDemoRule(rule_id="rule-crane-window", label="Synthetic crane-window coordination rule", package_ids=tuple(sorted((ids["crane"], ids["not_started"])))),
                ConstructionDemoRule(rule_id="rule-inspection-release", label="Synthetic inspection release gate", package_ids=(ids["inspection"],)),
            ),
            key=lambda item: item.rule_id,
        )
    )
    claims = tuple(sorted((asbestos_clearance_claim, alternate_ready_claim, electrical_ready_claim, crane_ready_claim), key=lambda item: item.claim_id))
    return ConstructionDemoProjectFixture(
        asset_pack=asset_pack,
        state=state,
        trades=_trades(),
        work_packages=work_packages,
        timeline=timeline,
        budget_lines=budget_lines,
        rules=rules,
        claims=claims,
        candidates=candidates,
        blocked_package_id=ids["blocked"],
        recommended_candidate_id=safe.candidate_id,
    )


__all__ = ["build_construction_demo_project_fixture"]
