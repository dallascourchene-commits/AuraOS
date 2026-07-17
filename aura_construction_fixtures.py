"""Deterministic synthetic fixtures for the SCO Construction Intelligence demo.

All organizations, people, costs, schedules, and project conditions in this file
are fictional and derived for software verification. They are not estimates for
a real SCO, PCL, owner, contractor, worker, building, or bid.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
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
from aura_construction_state import ConstructionProjectState, replay_construction_events
from aura_event_contracts import ActorType, MeasurementClass, stable_digest

CONSTRUCTION_FIXTURE_VERSION = "AURA_SCO_CONSTRUCTION_SYNTHETIC_FIXTURE_V1"
PROJECT_ID = "sco-demo-renovation"
LEDGER_ID = f"construction/{PROJECT_ID}"


@dataclass(frozen=True)
class ConstructionDemoFixture:
    state: ConstructionProjectState
    focus_scope: ConstructionScope
    claims: tuple[ConstructionClaim, ...]
    candidates: tuple[ConstructionCoordinationCandidate, ...]
    probabilistic_signals: tuple[ConstructionProbabilisticSignal, ...]
    blocked_clearance_claim_id: str
    version: str = CONSTRUCTION_FIXTURE_VERSION
    synthetic: bool = True
    private_data_used: bool = False
    production_connectors_used: bool = False

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_FIXTURE_VERSION:
            raise ValueError("unsupported Construction fixture version")
        if type(self.state) is not ConstructionProjectState:
            raise ValueError("fixture state must be an exact ConstructionProjectState")
        if type(self.focus_scope) is not ConstructionScope:
            raise ValueError("fixture focus_scope must be an exact ConstructionScope")
        if type(self.claims) is not tuple or not all(
            type(item) is ConstructionClaim for item in self.claims
        ):
            raise ValueError("fixture claims must be exact ConstructionClaim values")
        if type(self.candidates) is not tuple or not all(
            type(item) is ConstructionCoordinationCandidate for item in self.candidates
        ):
            raise ValueError("fixture candidates must be exact candidate values")
        if type(self.probabilistic_signals) is not tuple or not all(
            type(item) is ConstructionProbabilisticSignal
            for item in self.probabilistic_signals
        ):
            raise ValueError("fixture signals must be exact probabilistic signals")
        if self.blocked_clearance_claim_id not in {
            item.claim_id for item in self.claims
        }:
            raise ValueError("blocked clearance claim must exist in fixture claims")
        if (
            self.synthetic is not True
            or self.private_data_used is not False
            or self.production_connectors_used is not False
        ):
            raise ValueError("fixture crossed its synthetic-data boundary")

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "state": self.state.to_dict(),
            "focus_scope": self.focus_scope.to_dict(),
            "claims": [item.to_dict() for item in self.claims],
            "candidates": [item.to_dict() for item in self.candidates],
            "probabilistic_signals": [
                item.to_dict() for item in self.probabilistic_signals
            ],
        }


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
        payload_digest=stable_digest({"synthetic_fixture": payload_label}),
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
        value_digest=stable_digest({"synthetic_fixture": value_label}),
        claimant_id=claimant_id,
        evidence_refs=(evidence.evidence_id,),
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=confidence,
        authority_class=authority_class,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        created_at=created_at,
        expires_at=365.0,
    )


def _event(
    record: ConstructionEvidence | ConstructionClaim,
    *,
    sequence_number: int,
    previous_chain_digest: str,
    parent_event_ids: tuple[str, ...] = (),
) -> ConstructionEvent:
    record_time = (
        record.observed_at if type(record) is ConstructionEvidence else record.created_at
    )
    return ConstructionEvent.create(
        ledger_id=LEDGER_ID,
        sequence_number=sequence_number,
        previous_chain_digest=previous_chain_digest,
        trace_id="sco-synthetic-demo-trace",
        record=record,
        actor_id="synthetic-fixture-author",
        actor_type=ActorType.TOOL,
        parent_event_ids=parent_event_ids,
        created_at=max(float(sequence_number), record_time),
    )


def _signal(
    candidate: ConstructionCoordinationCandidate,
    *,
    specification: float,
    evidence: float,
    schedule: float,
    safety: float,
    variance: float,
    score_margin: float,
    progress_score: float,
    progress_slope: float,
) -> ConstructionProbabilisticSignal:
    criteria = (
        ConstructionCriterionScore.create(
            criterion="evidence quality",
            expected_score=evidence,
            variance=variance,
            repetitions=4,
        ),
        ConstructionCriterionScore.create(
            criterion="safety fit",
            expected_score=safety,
            variance=variance,
            repetitions=4,
        ),
        ConstructionCriterionScore.create(
            criterion="schedule fit",
            expected_score=schedule,
            variance=variance,
            repetitions=4,
        ),
        ConstructionCriterionScore.create(
            criterion="specification fit",
            expected_score=specification,
            variance=variance,
            repetitions=4,
        ),
    )
    return ConstructionProbabilisticSignal.create(
        candidate_id=candidate.candidate_id,
        criteria=criteria,
        score_margin=score_margin,
        progress_score=progress_score,
        progress_slope=progress_slope,
        distance_from_peak=max(0.0, min(1.0, 0.9 - progress_score)),
    )


def build_sco_construction_demo_fixture() -> ConstructionDemoFixture:
    """Build the deterministic Floor-6 conflict and alternative-work fixture."""
    focus = ConstructionScope(PROJECT_ID, "floor-6-east", "vertical-drilling")
    floor5 = ConstructionScope(PROJECT_ID, "floor-5-east", "preparation")
    electrical = ConstructionScope(PROJECT_ID, "floor-4-core", "electrical-isolation")
    logistics = ConstructionScope(PROJECT_ID, "loading-dock", "crane-window")

    sensor = _evidence(
        scope=focus,
        subject_id="floor-6-air",
        evidence_class=ConstructionEvidenceClass.SENSOR,
        source_ref="synthetic:air-sensor-17",
        payload_label="sensor reading below mock threshold",
        observed_at=1.0,
        authority_class=ConstructionAuthorityClass.INFORMATIVE,
        confidence=0.96,
    )
    clearance = _claim(
        scope=focus,
        subject_id="floor-6-air",
        predicate="asbestos_clearance_confirmed",
        value_label="clearance claimed from sensor only",
        claimant_id="synthetic-coordinator",
        evidence=sensor,
        created_at=2.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
        confidence=0.95,
    )

    floor5_document = _evidence(
        scope=floor5,
        subject_id="floor-5-east-zone",
        evidence_class=ConstructionEvidenceClass.OWNER_RECORD,
        source_ref="synthetic:owner-zone-release",
        payload_label="floor 5 east released for preparation",
        observed_at=3.0,
        authority_class=ConstructionAuthorityClass.OWNER,
    )
    floor5_ready = _claim(
        scope=floor5,
        subject_id="floor-5-east-zone",
        predicate="zone_available_for_preparation",
        value_label="floor 5 east available",
        claimant_id="synthetic-owner-representative",
        evidence=floor5_document,
        created_at=4.0,
        authority_class=ConstructionAuthorityClass.OWNER,
    )

    electrical_test = _evidence(
        scope=electrical,
        subject_id="floor-4-electrical-system",
        evidence_class=ConstructionEvidenceClass.TEST_RESULT,
        source_ref="synthetic:electrical-isolation-test",
        payload_label="electrical isolation test passed",
        observed_at=5.0,
        authority_class=ConstructionAuthorityClass.PROFESSIONAL,
    )
    electrical_ready = _claim(
        scope=electrical,
        subject_id="floor-4-electrical-system",
        predicate="electrical_isolation_confirmed",
        value_label="electrical isolation ready for governed review",
        claimant_id="synthetic-qualified-electrician",
        evidence=electrical_test,
        created_at=6.0,
        authority_class=ConstructionAuthorityClass.PROFESSIONAL,
    )

    crane_record = _evidence(
        scope=logistics,
        subject_id="mobile-crane-window",
        evidence_class=ConstructionEvidenceClass.CONTRACTOR_RECORD,
        source_ref="synthetic:crane-booking-record",
        payload_label="mock crane window reserved",
        observed_at=7.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
    )
    crane_ready = _claim(
        scope=logistics,
        subject_id="mobile-crane-window",
        predicate="crane_window_reserved",
        value_label="mock crane slot available",
        claimant_id="synthetic-logistics-supervisor",
        evidence=crane_record,
        created_at=8.0,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
    )

    records: tuple[ConstructionEvidence | ConstructionClaim, ...] = (
        sensor,
        clearance,
        floor5_document,
        floor5_ready,
        electrical_test,
        electrical_ready,
        crane_record,
        crane_ready,
    )
    events: list[ConstructionEvent] = []
    previous = GENESIS_CHAIN_DIGEST
    for sequence, record in enumerate(records, start=1):
        parent_ids = (events[-1].event_id,) if events else ()
        event = _event(
            record,
            sequence_number=sequence,
            previous_chain_digest=previous,
            parent_event_ids=parent_ids,
        )
        events.append(event)
        previous = event.chain_digest
    state = replay_construction_events(tuple(events))

    continue_drilling = ConstructionCoordinationCandidate.create(
        scope=focus,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Continue Floor 6 drilling",
        summary=(
            "Continue the original drilling sequence despite the missing dispositive "
            "clearance record. This route must be hard-blocked."
        ),
        required_claim_ids=(clearance.claim_id,),
        authority_route=ConstructionAuthorityRoute.PROFESSIONAL_REVIEW_REQUIRED,
        projected_time_delta_hours=-16.0,
        projected_cost_delta_cad=-4000.0,
        projected_idle_delta_hours=-40.0,
        safety_risk=0.98,
        deadline_risk=0.10,
        evidence_quality=0.20,
        reversibility=0.05,
    )
    shift_to_floor5 = ConstructionCoordinationCandidate.create(
        scope=focus,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Shift the drilling crew to Floor 5 preparation",
        summary=(
            "Preserve the Floor 6 hold and advance a released preparation package on "
            "Floor 5 while professional clearance evidence is obtained."
        ),
        required_claim_ids=(floor5_ready.claim_id,),
        authority_route=ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED,
        projected_time_delta_hours=-10.0,
        projected_cost_delta_cad=1500.0,
        projected_idle_delta_hours=-32.0,
        safety_risk=0.12,
        deadline_risk=0.18,
        evidence_quality=0.90,
        reversibility=0.92,
    )
    electrical_resequence = ConstructionCoordinationCandidate.create(
        scope=focus,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Advance the Floor 4 electrical isolation package",
        summary=(
            "Resequence a professionally evidenced electrical package and preserve the "
            "blocked Floor 6 work for later review."
        ),
        required_claim_ids=(electrical_ready.claim_id,),
        authority_route=ConstructionAuthorityRoute.PROFESSIONAL_REVIEW_REQUIRED,
        projected_time_delta_hours=-8.0,
        projected_cost_delta_cad=500.0,
        projected_idle_delta_hours=-24.0,
        safety_risk=0.08,
        deadline_risk=0.24,
        evidence_quality=0.94,
        reversibility=0.80,
    )
    crane_and_temp = ConstructionCoordinationCandidate.create(
        scope=focus,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Use the crane window and temporary labour on Floor 5 logistics",
        summary=(
            "Use the synthetic crane reservation and released Floor 5 package to advance "
            "material flow at a higher declared mock cost."
        ),
        required_claim_ids=(crane_ready.claim_id, floor5_ready.claim_id),
        authority_route=ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED,
        projected_time_delta_hours=-14.0,
        projected_cost_delta_cad=9000.0,
        projected_idle_delta_hours=-48.0,
        safety_risk=0.20,
        deadline_risk=0.12,
        evidence_quality=0.87,
        reversibility=0.65,
    )
    candidates = tuple(
        sorted(
            (
                continue_drilling,
                shift_to_floor5,
                electrical_resequence,
                crane_and_temp,
            ),
            key=lambda item: item.candidate_id,
        )
    )

    signals = tuple(
        sorted(
            (
                _signal(
                    continue_drilling,
                    specification=0.99,
                    evidence=0.97,
                    schedule=0.99,
                    safety=0.99,
                    variance=0.0025,
                    score_margin=0.30,
                    progress_score=0.90,
                    progress_slope=0.08,
                ),
                _signal(
                    shift_to_floor5,
                    specification=0.90,
                    evidence=0.91,
                    schedule=0.89,
                    safety=0.94,
                    variance=0.0100,
                    score_margin=0.12,
                    progress_score=0.72,
                    progress_slope=0.05,
                ),
                _signal(
                    electrical_resequence,
                    specification=0.88,
                    evidence=0.95,
                    schedule=0.80,
                    safety=0.96,
                    variance=0.0081,
                    score_margin=0.08,
                    progress_score=0.68,
                    progress_slope=0.04,
                ),
                _signal(
                    crane_and_temp,
                    specification=0.86,
                    evidence=0.88,
                    schedule=0.96,
                    safety=0.84,
                    variance=0.0144,
                    score_margin=0.05,
                    progress_score=0.64,
                    progress_slope=0.03,
                ),
            ),
            key=lambda item: item.candidate_id,
        )
    )
    return ConstructionDemoFixture(
        state=state,
        focus_scope=focus,
        claims=tuple(sorted((clearance, floor5_ready, electrical_ready, crane_ready), key=lambda item: item.claim_id)),
        candidates=candidates,
        probabilistic_signals=signals,
        blocked_clearance_claim_id=clearance.claim_id,
    )


def build_sco_construction_demo_runtime_packet() -> dict[str, Any]:
    fixture = build_sco_construction_demo_fixture()
    return ConstructionArenaAdapter().build_runtime_packet(
        objective=(
            "Protect the schedule without crossing the Floor 6 asbestos evidence and "
            "professional-authority boundary."
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
    "CONSTRUCTION_FIXTURE_VERSION",
    "PROJECT_ID",
    "LEDGER_ID",
    "ConstructionDemoFixture",
    "build_sco_construction_demo_fixture",
    "build_sco_construction_demo_runtime_packet",
]
