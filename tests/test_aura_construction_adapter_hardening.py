from __future__ import annotations

from dataclasses import replace
import math

import pytest

import aura_construction_adapter as adapter_module
from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaAdapter,
    ConstructionArenaMode,
    ConstructionCoordinationCandidate,
    ConstructionCriterionScore,
    ConstructionProbabilisticSignal,
    evaluate_construction_candidates,
)
from aura_construction_contracts import ConstructionScope
from aura_construction_fixtures import build_sco_construction_demo_fixture


def _evaluation():
    fixture = build_sco_construction_demo_fixture()
    result = evaluate_construction_candidates(
        fixture.state,
        candidates=fixture.candidates,
        now=30.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=fixture.probabilistic_signals,
    )
    return fixture, result


def test_candidate_deserialization_rejects_scalar_collection_attacks():
    fixture = build_sco_construction_demo_fixture()
    payload = fixture.candidates[0].to_dict()
    for field in (
        "required_claim_ids",
        "declared_hard_blockers",
        "assumptions",
    ):
        attacked = dict(payload)
        attacked[field] = "not-a-serialized-array"
        with pytest.raises(ValueError, match="serialized string array"):
            ConstructionCoordinationCandidate.from_dict(attacked)


def test_signal_deserialization_rejects_scalar_criteria_attack():
    fixture = build_sco_construction_demo_fixture()
    payload = fixture.probabilistic_signals[0].to_dict()
    payload["criteria"] = "not-a-serialized-array"
    with pytest.raises(ValueError, match="serialized object array"):
        ConstructionProbabilisticSignal.from_dict(payload)


def test_signal_deserialization_rejects_non_object_criteria_items():
    fixture = build_sco_construction_demo_fixture()
    payload = fixture.probabilistic_signals[0].to_dict()
    payload["criteria"] = ["not-an-object"]
    with pytest.raises(ValueError, match="must contain objects"):
        ConstructionProbabilisticSignal.from_dict(payload)


def test_deserializers_reject_unknown_fields():
    fixture = build_sco_construction_demo_fixture()
    candidate = fixture.candidates[0].to_dict()
    candidate["automatic_work_authority"] = True
    with pytest.raises(ValueError, match="unknown ConstructionCoordinationCandidate"):
        ConstructionCoordinationCandidate.from_dict(candidate)

    signal = fixture.probabilistic_signals[0].to_dict()
    signal["automatic_grammar_promotion"] = True
    with pytest.raises(ValueError, match="unknown ConstructionProbabilisticSignal"):
        ConstructionProbabilisticSignal.from_dict(signal)

    criterion = fixture.probabilistic_signals[0].criteria[0].to_dict()
    criterion["runtime_authority"] = True
    with pytest.raises(ValueError, match="unknown ConstructionCriterionScore"):
        ConstructionCriterionScore.from_dict(criterion)


def test_direct_candidate_requires_canonical_collection_order():
    fixture = build_sco_construction_demo_fixture()
    candidate = next(
        item for item in fixture.candidates if len(item.required_claim_ids) == 2
    )
    with pytest.raises(ValueError, match="required_claim_ids must be canonical"):
        replace(candidate, required_claim_ids=tuple(reversed(candidate.required_claim_ids)))


def test_option_ids_preserve_cheapest_fastest_recommended_safest_roles():
    fixture, evaluation = _evaluation()
    assessments = {item.candidate_id: item for item in evaluation.assessments}
    admissible = [
        item for item in fixture.candidates if assessments[item.candidate_id].admissible
    ]
    ranked = sorted(admissible, key=lambda item: assessments[item.candidate_id].rank_vector)
    selectors = (
        min(admissible, key=lambda item: (item.projected_cost_delta_cad, item.candidate_id)),
        min(admissible, key=lambda item: (item.projected_time_delta_hours, item.candidate_id)),
        ranked[0],
        min(
            admissible,
            key=lambda item: (item.safety_risk, item.deadline_risk, item.candidate_id),
        ),
    )
    expected: list[str] = []
    for item in selectors:
        if item.candidate_id not in expected:
            expected.append(item.candidate_id)
    for item in ranked:
        if item.candidate_id not in expected:
            expected.append(item.candidate_id)
        if len(expected) >= 4:
            break
    assert evaluation.option_candidate_ids == tuple(expected)


def test_runtime_packet_rejects_malformed_candidate_before_attribute_access():
    fixture = build_sco_construction_demo_fixture()
    with pytest.raises(ValueError, match="exact ConstructionCoordinationCandidate"):
        ConstructionArenaAdapter().build_runtime_packet(
            objective="Reject malformed candidate input.",
            state=fixture.state,
            scope=fixture.focus_scope,
            candidates=({"candidate_id": "forged"},),
            now=30.0,
            mode=ConstructionArenaMode.SYNTHETIC,
            lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        )


def test_runtime_packet_rejects_scope_state_project_mismatch():
    fixture = build_sco_construction_demo_fixture()
    with pytest.raises(ValueError, match="scope project must match"):
        ConstructionArenaAdapter().build_runtime_packet(
            objective="Reject cross-project packet.",
            state=fixture.state,
            scope=ConstructionScope("other-project", "zone", "package"),
            candidates=fixture.candidates,
            now=30.0,
            mode=ConstructionArenaMode.SYNTHETIC,
            lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
            probabilistic_signals=fixture.probabilistic_signals,
        )


def test_evaluator_rejects_scalar_candidate_and_signal_inputs():
    fixture = build_sco_construction_demo_fixture()
    with pytest.raises(ValueError, match="exact ConstructionCoordinationCandidate"):
        evaluate_construction_candidates(
            fixture.state,
            candidates="candidate",
            now=30.0,
            mode=ConstructionArenaMode.SYNTHETIC,
            lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        )
    with pytest.raises(ValueError, match="exact signal values"):
        evaluate_construction_candidates(
            fixture.state,
            candidates=fixture.candidates,
            now=30.0,
            mode=ConstructionArenaMode.SYNTHETIC,
            lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
            probabilistic_signals="signal",
        )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "must be a string"),
        ("   ", "must not be empty"),
    ],
)
def test_text_validation_fails_closed(value, message):
    with pytest.raises(ValueError, match=message):
        adapter_module._text(value, "field")


def test_numeric_validation_rejects_wrong_nonfinite_and_unbounded_values():
    with pytest.raises(ValueError, match="must be numeric"):
        adapter_module._finite("1", "score")
    with pytest.raises(ValueError, match="must be finite"):
        adapter_module._finite(math.inf, "score")
    with pytest.raises(ValueError, match="between zero and one"):
        adapter_module._bounded(-0.01, "score")


def test_string_collection_validation_rejects_scalars_duplicates_and_empty_required():
    with pytest.raises(ValueError, match="iterable of strings"):
        adapter_module._strings("abc", "items")
    with pytest.raises(ValueError, match="must not contain duplicates"):
        adapter_module._strings(("a", "a"), "items")
    with pytest.raises(ValueError, match="must not be empty"):
        adapter_module._strings((), "items", allow_empty=False)


def test_serialized_object_and_measurement_validation_fail_closed():
    with pytest.raises(ValueError, match="serialized object array"):
        adapter_module._serialized_objects({}, "objects")
    with pytest.raises(ValueError, match="must contain objects"):
        adapter_module._serialized_objects([1], "objects")
    with pytest.raises(ValueError, match="unknown measurement"):
        adapter_module._measurement("INVENTED", "measurement")
    assert adapter_module._normalize(7.0, 2.0, 2.0) == 0.0


def test_criterion_contract_rejects_noncanonical_and_invalid_direct_values():
    with pytest.raises(ValueError, match="criterion score must be an object"):
        ConstructionCriterionScore.from_dict("not-an-object")
    with pytest.raises(ValueError, match="variance must be a canonical float"):
        ConstructionCriterionScore(
            criterion="criterion",
            expected_score=0.5,
            variance=1,
            repetitions=1,
        )
    with pytest.raises(ValueError, match="positive integer"):
        ConstructionCriterionScore(
            criterion="criterion",
            expected_score=0.5,
            variance=0.1,
            repetitions=0,
        )
    with pytest.raises(ValueError, match="unknown criterion.measurement_class"):
        ConstructionCriterionScore(
            criterion="criterion",
            expected_score=0.5,
            variance=0.1,
            repetitions=1,
            measurement_class="INVENTED",
        )
