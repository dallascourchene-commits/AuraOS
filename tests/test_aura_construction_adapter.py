from __future__ import annotations

from dataclasses import replace

import pytest

from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaAdapter,
    ConstructionArenaMode,
    ConstructionAuthorityRoute,
    ConstructionCoordinationCandidate,
    ConstructionCriterionScore,
    ConstructionProbabilisticSignal,
    ConstructionRouteClass,
    evaluate_construction_candidates,
)
from aura_construction_contracts import ConstructionScope
from aura_construction_fixtures import build_sco_construction_demo_fixture
from aura_event_contracts import MeasurementClass


def fixture():
    return build_sco_construction_demo_fixture()


def evaluate(*, candidates=None, signals=None, mode=ConstructionArenaMode.SYNTHETIC):
    demo = fixture()
    return evaluate_construction_candidates(
        demo.state,
        candidates=demo.candidates if candidates is None else candidates,
        now=30.0,
        mode=mode,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=(
            demo.probabilistic_signals if signals is None else signals
        ),
    )


def test_adapter_is_liquid_planning_domain_adapter():
    adapter = ConstructionArenaAdapter()
    schema = adapter.schema()
    assert adapter.domain == "construction"
    assert schema["proposal_only"] is True
    assert schema["physical_work_authorized"] is False
    assert schema["probabilistic_signals_authoritative"] is False


def test_action_capsule_preserves_forbidden_authority():
    demo = fixture()
    capsule = ConstructionArenaAdapter().action_capsule_from_intent(
        objective="Rank safe alternatives.",
        capsule_id="CAP-1",
        target={
            "project_id": demo.focus_scope.project_id,
            "mode": "SYNTHETIC",
            "lane": "ALTERNATIVE_WORK",
        },
    )
    assert capsule.expected_output == "CONSTRUCTION_COORDINATION_PACKET"
    assert "authorize physical work" in capsule.forbidden_actions
    assert "release payment or transfer funds" in capsule.forbidden_actions
    assert "let a probabilistic score override a failed hard constraint" in capsule.forbidden_actions


def test_boundary_and_lease_are_read_only():
    demo = fixture()
    adapter = ConstructionArenaAdapter()
    capsule = adapter.action_capsule_from_intent(
        objective="Prepare a read-only packet.",
        capsule_id="CAP-2",
        target={
            "project_id": demo.focus_scope.project_id,
            "mode": "OWNER_READ_ONLY",
            "lane": "ALTERNATIVE_WORK",
        },
    )
    boundary = adapter.boundary_contract_for_scope(
        capsule=capsule,
        scope=demo.focus_scope,
        mode=ConstructionArenaMode.OWNER_READ_ONLY,
    )
    lease = adapter.lease_for_capsule(capsule=capsule, scope=demo.focus_scope)
    assert boundary.status == "placeholder"
    assert "no physical work authorization" in boundary.constraints
    assert lease.mode == "read_only"
    assert lease.conflict_policy == "deny_then_escalate"


def test_runtime_packet_does_not_mutate_or_authorize():
    demo = fixture()
    before = demo.state.state_digest
    packet = ConstructionArenaAdapter().build_runtime_packet(
        objective="Find alternate work.",
        state=demo.state,
        scope=demo.focus_scope,
        candidates=demo.candidates,
        now=30.0,
        mode=ConstructionArenaMode.SHADOW,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=demo.probabilistic_signals,
    )
    assert packet["ok"] is True
    assert packet["source_records_mutated"] is False
    assert packet["physical_work_authorized"] is False
    assert packet["payment_released"] is False
    assert demo.state.state_digest == before


def test_unsafe_high_score_candidate_is_hard_blocked():
    demo = fixture()
    evaluation = evaluate()
    highest_signal = max(
        demo.probabilistic_signals,
        key=lambda item: item.aggregate_score,
    )
    assessment = next(
        item
        for item in evaluation.assessments
        if item.candidate_id == highest_signal.candidate_id
    )
    assert assessment.admissible is False
    assert any("non_dispositive_evidence_only" in item for item in assessment.blockers)
    assert evaluation.recommended_candidate_id != highest_signal.candidate_id


def test_hard_blocker_wins_without_probabilistic_signals():
    demo = fixture()
    evaluation = evaluate(signals=())
    blocked = [item for item in evaluation.assessments if not item.admissible]
    assert len(blocked) == 1
    assert evaluation.recommended_candidate_id
    assert all(item.uncertainty == 1.0 for item in evaluation.assessments)


def test_candidate_order_is_invariant():
    demo = fixture()
    first = evaluate(candidates=demo.candidates)
    second = evaluate(candidates=tuple(reversed(demo.candidates)))
    assert first.evaluation_digest == second.evaluation_digest
    assert first.recommended_candidate_id == second.recommended_candidate_id


def test_signal_order_is_invariant():
    demo = fixture()
    first = evaluate(signals=demo.probabilistic_signals)
    second = evaluate(signals=tuple(reversed(demo.probabilistic_signals)))
    assert first.evaluation_digest == second.evaluation_digest


def test_four_option_pattern_is_bounded_and_admissible():
    evaluation = evaluate()
    admissible = {
        item.candidate_id for item in evaluation.assessments if item.admissible
    }
    assert 1 <= len(evaluation.option_candidate_ids) <= 4
    assert set(evaluation.option_candidate_ids).issubset(admissible)


def test_multiple_admissible_candidates_use_multi_lane_route():
    evaluation = evaluate()
    assert evaluation.route_class == ConstructionRouteClass.MULTI_LANE_COMPARISON.value
    assert evaluation.next_authority_route in {
        ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED.value,
        ConstructionAuthorityRoute.PROFESSIONAL_REVIEW_REQUIRED.value,
    }


def test_empty_candidate_set_fails_closed_without_recommendation():
    demo = fixture()
    evaluation = evaluate_construction_candidates(
        demo.state,
        candidates=(),
        now=30.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
    )
    assert evaluation.route_class == ConstructionRouteClass.OWNER_REVIEW_REQUIRED.value
    assert evaluation.recommended_candidate_id == ""
    assert evaluation.option_candidate_ids == ()


def test_declared_hard_blocker_is_preserved():
    demo = fixture()
    source = next(item for item in demo.candidates if not item.declared_hard_blockers)
    blocked = ConstructionCoordinationCandidate.create(
        scope=source.scope,
        lane=source.lane,
        title="Declared blocked route",
        summary="A synthetic route with an explicit permit blocker.",
        declared_hard_blockers=("missing_permit",),
        authority_route=ConstructionAuthorityRoute.REGULATORY_OR_LEGAL_REVIEW_REQUIRED,
        projected_time_delta_hours=-100.0,
        projected_cost_delta_cad=-100000.0,
        projected_idle_delta_hours=-100.0,
        safety_risk=0.0,
        deadline_risk=0.0,
        evidence_quality=1.0,
        reversibility=1.0,
    )
    evaluation = evaluate(candidates=(blocked,), signals=())
    assessment = evaluation.assessments[0]
    assert assessment.admissible is False
    assert assessment.blockers == ("missing_permit",)


def test_project_scope_mismatch_is_blocked():
    candidate = ConstructionCoordinationCandidate.create(
        scope=ConstructionScope("other-project", "zone", "package"),
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        title="Wrong project route",
        summary="This route belongs to a different project and must be blocked.",
        authority_route=ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED,
        projected_time_delta_hours=0.0,
        projected_cost_delta_cad=0.0,
        projected_idle_delta_hours=0.0,
        safety_risk=0.0,
        deadline_risk=0.0,
        evidence_quality=1.0,
        reversibility=1.0,
    )
    assessment = evaluate(candidates=(candidate,), signals=()).assessments[0]
    assert "candidate_project_scope_mismatch" in assessment.blockers


def test_duplicate_candidate_ids_are_rejected():
    demo = fixture()
    candidate = demo.candidates[0]
    with pytest.raises(ValueError, match="candidate IDs must be unique"):
        evaluate(candidates=(candidate, candidate), signals=())


def test_signal_for_unknown_candidate_is_rejected():
    demo = fixture()
    criterion = ConstructionCriterionScore.create(
        criterion="specification",
        expected_score=0.5,
        variance=0.1,
        repetitions=1,
    )
    unknown = ConstructionProbabilisticSignal.create(
        candidate_id="unknown-candidate",
        criteria=(criterion,),
    )
    with pytest.raises(ValueError, match="unknown candidates"):
        evaluate(signals=(unknown,))


def test_duplicate_signals_are_rejected():
    demo = fixture()
    signal = demo.probabilistic_signals[0]
    with pytest.raises(ValueError, match="at most one"):
        evaluate(signals=(signal, signal))


def test_lane_mismatch_is_rejected():
    demo = fixture()
    source = demo.candidates[0]
    candidate = ConstructionCoordinationCandidate.create(
        scope=source.scope,
        lane=ConstructionAdvisoryLane.PAYMENT_READINESS,
        title="Payment readiness route",
        summary="A proposal-only payment-readiness explanation.",
        authority_route=ConstructionAuthorityRoute.OWNER_REVIEW_REQUIRED,
        projected_time_delta_hours=0.0,
        projected_cost_delta_cad=0.0,
        projected_idle_delta_hours=0.0,
        safety_risk=0.0,
        deadline_risk=0.0,
        evidence_quality=1.0,
        reversibility=1.0,
    )
    with pytest.raises(ValueError, match="requested advisory lane"):
        evaluate(candidates=(candidate,), signals=())


def test_invalid_mode_fails_closed():
    with pytest.raises(ValueError, match="unknown mode"):
        evaluate(mode="LIVE_AUTONOMOUS")


def test_candidate_round_trip_revalidates_identity():
    demo = fixture()
    candidate = demo.candidates[0]
    assert ConstructionCoordinationCandidate.from_dict(candidate.to_dict()) == candidate
    payload = candidate.to_dict()
    payload["physical_work_authorized"] = True
    with pytest.raises(ValueError, match="authority boundary"):
        ConstructionCoordinationCandidate.from_dict(payload)


def test_probabilistic_signal_round_trip_and_tamper_detection():
    demo = fixture()
    signal = demo.probabilistic_signals[0]
    assert ConstructionProbabilisticSignal.from_dict(signal.to_dict()) == signal
    with pytest.raises(ValueError, match="digest"):
        replace(signal, aggregate_score=0.0)


def test_probabilistic_signal_cannot_gain_runtime_authority():
    demo = fixture()
    with pytest.raises(ValueError, match="authority boundary"):
        replace(demo.probabilistic_signals[0], runtime_authority=True)


def test_criteria_require_canonical_floats_and_measurement_class():
    with pytest.raises(ValueError, match="canonical float"):
        ConstructionCriterionScore(
            criterion="test",
            expected_score=1,
            variance=0.1,
            repetitions=1,
        )
    criterion = ConstructionCriterionScore.create(
        criterion="test",
        expected_score=1,
        variance=0,
        repetitions=1,
        measurement_class=MeasurementClass.VERIFIER_BACKED,
    )
    assert criterion.expected_score == 1.0
    assert criterion.measurement_class == "VERIFIER_BACKED"


def test_signal_uncertainty_is_derived_from_variance():
    criteria = (
        ConstructionCriterionScore.create(
            criterion="a", expected_score=0.8, variance=0.04, repetitions=2
        ),
        ConstructionCriterionScore.create(
            criterion="b", expected_score=0.6, variance=0.04, repetitions=2
        ),
    )
    signal = ConstructionProbabilisticSignal.create(
        candidate_id="candidate",
        criteria=criteria,
    )
    assert signal.aggregate_score == pytest.approx(0.7)
    assert signal.uncertainty == pytest.approx(0.2)


def test_evaluation_authority_boundary_is_explicit():
    evaluation = evaluate()
    assert evaluation.proposal_only is True
    assert evaluation.human_release_required is True
    assert evaluation.physical_work_authorized is False
    assert evaluation.payment_released is False
    assert evaluation.access_controlled is False
