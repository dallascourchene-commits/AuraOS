"""Deterministic builder for the asset-pack-bound G4 Construction demo fixture."""
from __future__ import annotations

from typing import Any

from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaAdapter,
    ConstructionArenaMode,
    ConstructionAuthorityRoute,
    ConstructionCoordinationCandidate,
    ConstructionCriterionScore,
    ConstructionProbabilisticSignal,
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
from aura_construction_demo_contracts import ConstructionDemoAssetPack, ConstructionDemoStorey
from aura_construction_demo_fixture import (
    ConstructionDemoActivity,
    ConstructionDemoAlternative,
    ConstructionDemoBudgetLine,
    ConstructionDemoHazard,
    ConstructionDemoInspection,
    ConstructionDemoProjectFixture,
    ConstructionDemoRule,
    ConstructionDemoTrade,
    ConstructionDemoWorkPackage,
    ConstructionDemoWorkStatus,
)
from aura_construction_state import replay_construction_events
from aura_event_contracts import ActorType, MeasurementClass, stable_digest

PROJECT_ID = "tuwien-synthetic-construction-demo"
LEDGER_ID = f"construction/{PROJECT_ID}"
TRACE_ID = "tuwien-synthetic-construction-demo-trace"

_TRADE_ROWS = (
    ("trade-asbestos", "asbestos abatement", "subcontractor-horizon-abatement"),
    ("trade-crane", "crane and logistics", "subcontractor-north-lift-logistics"),
    ("trade-demolition", "demolition", "subcontractor-clearpath-demolition"),
    ("trade-electrical", "electrical", "subcontractor-brightline-electrical"),
    ("trade-fire", "fire protection", "subcontractor-sentinel-fire"),
    ("trade-general", "general contractor", "subcontractor-aura-demo-gc"),
    ("trade-inspection", "inspection", "subcontractor-demo-inspection"),
    ("trade-mechanical", "mechanical", "subcontractor-northwind-mechanical"),
    ("trade-plumbing", "plumbing", "subcontractor-bluewater-plumbing"),
    ("trade-roofing", "roofing", "subcontractor-skyline-roofing"),
    ("trade-structural", "structural", "subcontractor-keystone-structural"),
    ("trade-temp", "temporary labour", "subcontractor-flex-labour"),
)


def _zone(storey: ConstructionDemoStorey, role: str) -> str:
    return f"zone-{storey.ordinal:02d}-{role}"


def _scope(storey: ConstructionDemoStorey, role: str, package_id: str) -> ConstructionScope:
    return ConstructionScope(PROJECT_ID, _zone(storey, role), package_id)


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
        expires_at=365.0,
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
        expires_at=365.0,
    )


def _events(records: tuple[ConstructionEvidence | ConstructionClaim, ...]) -> tuple[ConstructionEvent, ...]:
    result: list[ConstructionEvent] = []
    previous = GENESIS_CHAIN_DIGEST
    for sequence, record in enumerate(records, start=1):
        record_time = record.observed_at if type(record) is ConstructionEvidence else record.created_at
        event = ConstructionEvent.create(
            ledger_id=LEDGER_ID,
            sequence_number=sequence,
            previous_chain_digest=previous,
            trace_id=TRACE_ID,
            record=record,
            actor_id="synthetic-fixture-author",
            actor_type=ActorType.TOOL,
            parent_event_ids=(result[-1].event_id,) if result else (),
            created_at=max(float(sequence), record_time),
        )
        result.append(event)
        previous = event.chain_digest
    return tuple(result)


def _candidate(
    *,
    scope: ConstructionScope,
    title: str,
    summary: str,
    required_claim_ids: tuple[str, ...],
    authority_route: ConstructionAuthorityRoute,
    time_delta: float,
    cost_delta: float,
    idle_delta: float,
    safety: float,
    deadline: float,
    evidence: float,
    reversibility: float,
    hard_blockers: tuple[str, ...] = (),
) -> ConstructionCoordinationCandidate:
    return ConstructionCoordinationCandidate.create(
        scope=scope,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title=title,
        summary=summary,
        required_claim_ids=required_claim_ids,
        declared_hard_blockers=hard_blockers,
        authority_route=authority_route,
        projected_time_delta_hours=time_delta,
        projected_cost_delta_cad=cost_delta,
        projected_idle_delta_hours=idle_delta,
        safety_risk=safety,
        deadline_risk=deadline,
        evidence_quality=evidence,
        reversibility=reversibility,
    )


def _signal(
    candidate: ConstructionCoordinationCandidate,
    *,
    specification: float,
    evidence: float,
    schedule: float,
    safety: float,
    variance: float,
    margin: float,
) -> ConstructionProbabilisticSignal:
    criteria = tuple(
        ConstructionCriterionScore.create(
            criterion=name,
            expected_score=value,
            variance=variance,
            repetitions=4,
        )
        for name, value in sorted(
            {
                "evidence quality": evidence,
                "safety fit": safety,
                "schedule fit": schedule,
                "specification fit": specification,
            }.items()
        )
    )
    return ConstructionProbabilisticSignal.create(
        candidate_id=candidate.candidate_id,
        criteria=criteria,
        score_margin=margin,
        progress_score=0.70,
        progress_slope=0.04,
        distance_from_peak=0.20,
    )


def _ordered_storeys(asset_pack: ConstructionDemoAssetPack) -> tuple[ConstructionDemoStorey, ...]:
    if type(asset_pack) is not ConstructionDemoAssetPack:
        raise ValueError("asset_pack must be an exact ConstructionDemoAssetPack")
    asset_pack.__post_init__()
    storeys = tuple(sorted(asset_pack.storeys, key=lambda item: (item.ordinal, item.storey_id)))
    if len(storeys) < 5:
        raise ValueError("G4 requires at least five admitted storeys")
    return storeys


def build_construction_demo_project_fixture(
    asset_pack: ConstructionDemoAssetPack,
) -> ConstructionDemoProjectFixture:
    """Build the complete deterministic G4 fixture against admitted storey IDs."""

    storeys = _ordered_storeys(asset_pack)
    logistics_storey, service_storey, electrical_storey, released_storey, blocked_storey = (
        storeys[0],
        storeys[1],
        storeys[len(storeys) // 2],
        storeys[-2],
        storeys[-1],
    )

    package_specs = (
        ("wp-asbestos-abatement", blocked_storey, "abatement", "trade-asbestos", ConstructionDemoWorkStatus.AWAITING_PROFESSIONAL_RELEASE),
        ("wp-crane-logistics", logistics_storey, "logistics", "trade-crane", ConstructionDemoWorkStatus.ACTIVE),
        ("wp-demolition", released_storey, "preparation", "trade-demolition", ConstructionDemoWorkStatus.COMPLETED),
        ("wp-electrical-isolation", electrical_storey, "core", "trade-electrical", ConstructionDemoWorkStatus.READY_FOR_REVIEW),
        ("wp-fire-protection", service_storey, "life-safety", "trade-fire", ConstructionDemoWorkStatus.NOT_STARTED),
        ("wp-upper-drilling", blocked_storey, "drilling", "trade-general", ConstructionDemoWorkStatus.BLOCKED),
        ("wp-inspection-release", electrical_storey, "inspection", "trade-inspection", ConstructionDemoWorkStatus.COMPLETED),
        ("wp-mechanical-roughin", service_storey, "mechanical", "trade-mechanical", ConstructionDemoWorkStatus.ACTIVE),
        ("wp-plumbing-riser", service_storey, "plumbing", "trade-plumbing", ConstructionDemoWorkStatus.DELAYED),
        ("wp-roofing-repair", blocked_storey, "roof", "trade-roofing", ConstructionDemoWorkStatus.REWORK_REQUIRED),
        ("wp-structural-review", released_storey, "structure", "trade-structural", ConstructionDemoWorkStatus.AWAITING_INSPECTION),
        ("wp-temporary-preparation", released_storey, "preparation", "trade-temp", ConstructionDemoWorkStatus.READY_FOR_REVIEW),
    )
    scopes = {
        package_id: _scope(storey, role, package_id)
        for package_id, storey, role, _trade, _status in package_specs
    }

    asbestos_sensor = _evidence(
        scope=scopes["wp-upper-drilling"],
        subject_id="upper-floor-air-clearance",
        evidence_class=ConstructionEvidenceClass.SENSOR,
        source_ref="synthetic:air-sensor-reading",
        payload_label="sensor below mock threshold but not dispositive clearance",
        observed_at=1.0,
        authority_class=ConstructionAuthorityClass.INFORMATIVE,
        confidence=0.96,
    )
    asbestos_clearance = _claim(
        scope=scopes["wp-upper-drilling"],
        subject_id="upper-floor-air-clearance",
        predicate="asbestos_clearance_confirmed",
        value_label="clearance claimed from non-dispositive sensor only",
        claimant_id="synthetic-coordinator",
        evidence=asbestos_sensor,
        created_at=2.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
        confidence=0.95,
    )
    release_record = _evidence(
        scope=scopes["wp-temporary-preparation"],
        subject_id="released-preparation-zone",
        evidence_class=ConstructionEvidenceClass.OWNER_RECORD,
        source_ref="synthetic:owner-zone-release",
        payload_label="alternate storey released for preparation",
        observed_at=3.0,
        authority_class=ConstructionAuthorityClass.OWNER,
    )
    release_claim = _claim(
        scope=scopes["wp-temporary-preparation"],
        subject_id="released-preparation-zone",
        predicate="zone_available_for_preparation",
        value_label="alternate preparation zone released",
        claimant_id="synthetic-owner-representative",
        evidence=release_record,
        created_at=4.0,
        authority_class=ConstructionAuthorityClass.OWNER,
    )
    electrical_test = _evidence(
        scope=scopes["wp-electrical-isolation"],
        subject_id="electrical-isolation-system",
        evidence_class=ConstructionEvidenceClass.TEST_RESULT,
        source_ref="synthetic:electrical-isolation-test",
        payload_label="electrical isolation test passed",
        observed_at=5.0,
        authority_class=ConstructionAuthorityClass.PROFESSIONAL,
    )
    electrical_claim = _claim(
        scope=scopes["wp-electrical-isolation"],
        subject_id="electrical-isolation-system",
        predicate="electrical_isolation_confirmed",
        value_label="electrical isolation ready for governed review",
        claimant_id="synthetic-qualified-electrician",
        evidence=electrical_test,
        created_at=6.0,
        authority_class=ConstructionAuthorityClass.PROFESSIONAL,
    )
    crane_record = _evidence(
        scope=scopes["wp-crane-logistics"],
        subject_id="mobile-crane-window",
        evidence_class=ConstructionEvidenceClass.CONTRACTOR_RECORD,
        source_ref="synthetic:crane-booking-record",
        payload_label="mock crane window reserved",
        observed_at=7.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
    )
    crane_claim = _claim(
        scope=scopes["wp-crane-logistics"],
        subject_id="mobile-crane-window",
        predicate="crane_window_reserved",
        value_label="mock crane slot available",
        claimant_id="synthetic-logistics-supervisor",
        evidence=crane_record,
        created_at=8.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
    )
    state = replay_construction_events(
        _events(
            (
                asbestos_sensor,
                asbestos_clearance,
                release_record,
                release_claim,
                electrical_test,
                electrical_claim,
                crane_record,
                crane_claim,
            )
        )
    )

    unsafe = _candidate(
        scope=scopes["wp-upper-drilling"],
        title="Continue upper-floor drilling",
        summary="Continue drilling despite missing dispositive asbestos clearance evidence.",
        required_claim_ids=(asbestos_clearance.claim_id,),
        declared_hard_blockers=("missing_dispositive_asbestos_clearance",),
        authority_route=ConstructionAuthorityRoute.PROFESSIONAL_REVIEW_REQUIRED,
        time_delta=-16.0,
        cost_delta=-4000.0,
        idle_delta=-40.0,
        safety=0.98,
        deadline=0.10,
        evidence=0.20,
        reversibility=0.05,
    )
    shift = _candidate(
        scope=scopes["wp-upper-drilling"],
        title="Shift crew to released preparation work",
        summary="Preserve the drilling hold and advance released preparation work on another storey.",
        required_claim_ids=(release_claim.claim_id,),
        authority_route=ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED,
        time_delta=-10.0,
        cost_delta=1500.0,
        idle_delta=-32.0,
        safety=0.12,
        deadline=0.18,
        evidence=0.90,
        reversibility=0.92,
    )
    electrical = _candidate(
        scope=scopes["wp-upper-drilling"],
        title="Advance electrical isolation package",
        summary="Resequence professionally evidenced electrical isolation while preserving the drilling hold.",
        required_claim_ids=(electrical_claim.claim_id,),
        authority_route=ConstructionAuthorityRoute.PROFESSIONAL_REVIEW_REQUIRED,
        time_delta=-8.0,
        cost_delta=500.0,
        idle_delta=-24.0,
        safety=0.08,
        deadline=0.24,
        evidence=0.94,
        reversibility=0.80,
    )
    crane_temp = _candidate(
        scope=scopes["wp-upper-drilling"],
        title="Use crane window and temporary labour",
        summary="Use the synthetic crane reservation and released preparation zone at a higher mock cost.",
        required_claim_ids=tuple(sorted((crane_claim.claim_id, release_claim.claim_id))),
        authority_route=ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED,
        time_delta=-14.0,
        cost_delta=9000.0,
        idle_delta=-48.0,
        safety=0.20,
        deadline=0.12,
        evidence=0.87,
        reversibility=0.65,
    )
    candidates = tuple(sorted((unsafe, shift, electrical, crane_temp), key=lambda item: item.candidate_id))
    signals = tuple(
        sorted(
            (
                _signal(unsafe, specification=0.99, evidence=0.20, schedule=0.99, safety=0.02, variance=0.0025, margin=0.30),
                _signal(shift, specification=0.90, evidence=0.91, schedule=0.89, safety=0.94, variance=0.0100, margin=0.12),
                _signal(electrical, specification=0.88, evidence=0.95, schedule=0.80, safety=0.96, variance=0.0081, margin=0.08),
                _signal(crane_temp, specification=0.86, evidence=0.88, schedule=0.96, safety=0.84, variance=0.0144, margin=0.05),
            ),
            key=lambda item: item.candidate_id,
        )
    )

    trades = tuple(ConstructionDemoTrade(*row) for row in _TRADE_ROWS)
    trades = tuple(sorted(trades, key=lambda item: item.trade_id))
    rules = tuple(
        sorted(
            (
                ConstructionDemoRule(
                    "rule-asbestos-clearance",
                    "Synthetic hazardous-material clearance gate",
                    ("wp-asbestos-abatement", "wp-upper-drilling"),
                    "Dispositive documentary or professional evidence is required before release review.",
                ),
                ConstructionDemoRule(
                    "rule-crane-window",
                    "Synthetic crane logistics gate",
                    ("wp-crane-logistics", "wp-temporary-preparation"),
                    "The mock crane window and exclusion-zone review must be visible before coordination review.",
                ),
                ConstructionDemoRule(
                    "rule-inspection-release",
                    "Synthetic inspection release gate",
                    ("wp-electrical-isolation", "wp-structural-review"),
                    "Inspection and professional review remain external human authority gates.",
                ),
            ),
            key=lambda item: item.rule_id,
        )
    )
    inspections = tuple(
        sorted(
            (
                ConstructionDemoInspection("inspection-electrical", "wp-electrical-isolation", "Electrical isolation review", "AWAITING_REVIEW", 12.0),
                ConstructionDemoInspection("inspection-structural", "wp-structural-review", "Structural opening inspection", "SCHEDULED", 16.0),
                ConstructionDemoInspection("inspection-workflow", "wp-inspection-release", "Completed mock coordination inspection", "PASSED", 8.0),
            ),
            key=lambda item: item.inspection_id,
        )
    )
    hazards = tuple(
        sorted(
            (
                ConstructionDemoHazard(
                    "hazard-asbestos",
                    "wp-upper-drilling",
                    "Potential asbestos disturbance without dispositive clearance",
                    "CRITICAL",
                    True,
                    (asbestos_sensor.evidence_id,),
                ),
                ConstructionDemoHazard(
                    "hazard-crane-exclusion",
                    "wp-crane-logistics",
                    "Synthetic crane exclusion-zone coordination",
                    "HIGH",
                    True,
                    (crane_record.evidence_id,),
                ),
            ),
            key=lambda item: item.hazard_id,
        )
    )
    rule_by_package = {
        "wp-asbestos-abatement": ("rule-asbestos-clearance",),
        "wp-upper-drilling": ("rule-asbestos-clearance",),
        "wp-crane-logistics": ("rule-crane-window",),
        "wp-temporary-preparation": ("rule-crane-window",),
        "wp-electrical-isolation": ("rule-inspection-release",),
        "wp-structural-review": ("rule-inspection-release",),
    }
    inspection_by_package = {
        "wp-electrical-isolation": ("inspection-electrical",),
        "wp-structural-review": ("inspection-structural",),
        "wp-inspection-release": ("inspection-workflow",),
    }
    hazard_by_package = {
        "wp-upper-drilling": ("hazard-asbestos",),
        "wp-crane-logistics": ("hazard-crane-exclusion",),
    }
    evidence_by_package = {
        "wp-upper-drilling": (asbestos_sensor.evidence_id,),
        "wp-electrical-isolation": (electrical_test.evidence_id,),
        "wp-temporary-preparation": (release_record.evidence_id,),
        "wp-crane-logistics": (crane_record.evidence_id,),
    }
    dependency_by_package = {
        "wp-upper-drilling": ("wp-asbestos-abatement", "wp-electrical-isolation"),
        "wp-temporary-preparation": ("wp-demolition",),
        "wp-fire-protection": ("wp-mechanical-roughin",),
        "wp-inspection-release": ("wp-electrical-isolation",),
        "wp-roofing-repair": ("wp-structural-review",),
    }
    title_by_package = {
        package_id: package_id.removeprefix("wp-").replace("-", " ").title()
        for package_id, *_rest in package_specs
    }
    work_packages = tuple(
        sorted(
            (
                ConstructionDemoWorkPackage(
                    work_package_id=package_id,
                    storey_id=storey.storey_id,
                    zone_id=scopes[package_id].zone_id,
                    title=title_by_package[package_id],
                    trade_id=trade_id,
                    status=status.value,
                    scope=scopes[package_id],
                    planned_start_day=float(index * 2),
                    planned_finish_day=float(index * 2 + 5),
                    dependency_ids=tuple(sorted(dependency_by_package.get(package_id, ()))),
                    evidence_refs=tuple(sorted(evidence_by_package.get(package_id, ()))),
                    inspection_ids=tuple(sorted(inspection_by_package.get(package_id, ()))),
                    hazard_ids=tuple(sorted(hazard_by_package.get(package_id, ()))),
                    rule_ids=tuple(sorted(rule_by_package.get(package_id, ()))),
                    crane_window_id="crane-window-01" if package_id in {"wp-crane-logistics", "wp-temporary-preparation"} else None,
                    professional_release_required=package_id in {"wp-asbestos-abatement", "wp-upper-drilling", "wp-electrical-isolation", "wp-structural-review"},
                )
                for index, (package_id, storey, _role, trade_id, status) in enumerate(package_specs)
            ),
            key=lambda item: item.work_package_id,
        )
    )
    budget_lines = tuple(
        ConstructionDemoBudgetLine(
            budget_line_id=f"budget-{package.work_package_id.removeprefix('wp-')}",
            work_package_id=package.work_package_id,
            description=f"Synthetic budget for {package.title}",
            committed_cad=float(20_000 + index * 7_500),
            forecast_cad=float(21_000 + index * 7_750),
            actual_cad=float(5_000 + index * 2_250),
        )
        for index, package in enumerate(work_packages)
    )
    budget_lines = tuple(sorted(budget_lines, key=lambda item: item.budget_line_id))
    history = tuple(
        sorted(
            (
                ConstructionDemoActivity("activity-demolition-complete", "wp-demolition", "trade-demolition", 5.0, "COMPLETED", "Synthetic demolition package completed."),
                ConstructionDemoActivity("activity-electrical-review", "wp-electrical-isolation", "trade-electrical", 8.0, "READY_FOR_REVIEW", "Synthetic electrical evidence assembled for review."),
                ConstructionDemoActivity("activity-mechanical-active", "wp-mechanical-roughin", "trade-mechanical", 9.0, "ACTIVE", "Synthetic mechanical rough-in underway."),
                ConstructionDemoActivity("activity-drilling-blocked", "wp-upper-drilling", "trade-general", 10.0, "BLOCKED", "Drilling remains blocked by missing dispositive asbestos evidence."),
                ConstructionDemoActivity("activity-temp-ready", "wp-temporary-preparation", "trade-temp", 11.0, "READY_FOR_REVIEW", "Temporary labour option is prepared for human review."),
            ),
            key=lambda item: item.activity_id,
        )
    )
    alternatives = tuple(
        sorted(
            (
                ConstructionDemoAlternative(
                    "alternative-continue-drilling",
                    "Continue upper-floor drilling",
                    "wp-upper-drilling",
                    ("wp-upper-drilling",),
                    -16.0,
                    -4000.0,
                    -40.0,
                    False,
                    ("missing_dispositive_asbestos_clearance",),
                ),
                ConstructionDemoAlternative(
                    "alternative-shift-preparation",
                    "Shift crew to released preparation work",
                    "wp-upper-drilling",
                    ("wp-temporary-preparation",),
                    -10.0,
                    1500.0,
                    -32.0,
                    True,
                    (),
                    True,
                ),
                ConstructionDemoAlternative(
                    "alternative-electrical",
                    "Advance electrical isolation package",
                    "wp-upper-drilling",
                    ("wp-electrical-isolation",),
                    -8.0,
                    500.0,
                    -24.0,
                    True,
                ),
                ConstructionDemoAlternative(
                    "alternative-crane-temp",
                    "Use crane window and temporary labour",
                    "wp-upper-drilling",
                    ("wp-crane-logistics", "wp-temporary-preparation"),
                    -14.0,
                    9000.0,
                    -48.0,
                    True,
                ),
            ),
            key=lambda item: item.alternative_id,
        )
    )

    return ConstructionDemoProjectFixture(
        asset_pack=asset_pack,
        state=state,
        focus_scope=scopes["wp-upper-drilling"],
        trades=trades,
        work_packages=work_packages,
        budget_lines=budget_lines,
        rules=rules,
        inspections=inspections,
        hazards=hazards,
        work_history=history,
        alternatives=alternatives,
        candidates=candidates,
        probabilistic_signals=signals,
        blocked_clearance_claim_id=asbestos_clearance.claim_id,
    )


def build_construction_demo_runtime_packet(
    fixture: ConstructionDemoProjectFixture,
) -> dict[str, Any]:
    if type(fixture) is not ConstructionDemoProjectFixture:
        raise ValueError("fixture must be an exact ConstructionDemoProjectFixture")
    fixture.__post_init__()
    return ConstructionArenaAdapter().build_runtime_packet(
        objective=(
            "Protect the synthetic schedule without crossing the blocked asbestos-evidence "
            "or professional-authority boundary."
        ),
        state=fixture.state,
        scope=fixture.focus_scope,
        candidates=fixture.candidates,
        now=30.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=fixture.probabilistic_signals,
    )


__all__ = [
    "PROJECT_ID",
    "LEDGER_ID",
    "TRACE_ID",
    "build_construction_demo_project_fixture",
    "build_construction_demo_runtime_packet",
]
