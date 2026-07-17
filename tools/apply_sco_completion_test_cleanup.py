"""Correct the exact cross-state evaluation fixture in the one-time test output."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tests/test_aura_construction_human_agent.py"
text = path.read_text(encoding="utf-8")
text = text.replace("from dataclasses import asdict\n\n", "", 1)
old = '''def test_profile_rejects_evaluation_from_another_state():
    fixture, evaluation = _profile_inputs()
    values = asdict(evaluation)
    values.pop("evaluation_id")
    values.pop("evaluation_digest")
    values["state_digest"] = "wrong-state-digest"
    payload = dict(values)
    mismatched = ConstructionCoordinationEvaluation(
        evaluation_id=stable_id("construction-evaluation", payload),
        evaluation_digest=stable_digest(payload),
        **values,
    )

    with pytest.raises(ValueError, match="evaluation does not bind"):
        build_construction_human_agent_profile(
            fixture.state,
            mismatched,
            candidates=fixture.candidates,
        )
'''
new = '''def test_profile_rejects_evaluation_from_another_state():
    fixture, evaluation = _profile_inputs()
    values = {
        "mode": evaluation.mode,
        "lane": evaluation.lane,
        "route_class": evaluation.route_class,
        "state_digest": "wrong-state-digest",
        "evaluated_at": evaluation.evaluated_at,
        "assessments": evaluation.assessments,
        "recommended_candidate_id": evaluation.recommended_candidate_id,
        "option_candidate_ids": evaluation.option_candidate_ids,
        "next_authority_route": evaluation.next_authority_route,
        "version": evaluation.version,
        "proposal_only": evaluation.proposal_only,
        "human_release_required": evaluation.human_release_required,
        "physical_work_authorized": evaluation.physical_work_authorized,
        "payment_released": evaluation.payment_released,
        "access_controlled": evaluation.access_controlled,
        "patch_authority": evaluation.patch_authority,
        "vsa_patch_authority": evaluation.vsa_patch_authority,
    }
    payload = {
        **values,
        "assessments": [item.to_dict() for item in values["assessments"]],
        "option_candidate_ids": list(values["option_candidate_ids"]),
    }
    mismatched = ConstructionCoordinationEvaluation(
        evaluation_id=stable_id("construction-evaluation", payload),
        evaluation_digest=stable_digest(payload),
        **values,
    )

    with pytest.raises(ValueError, match="evaluation does not bind"):
        build_construction_human_agent_profile(
            fixture.state,
            mismatched,
            candidates=fixture.candidates,
        )
'''
if new not in text:
    if text.count(old) != 1:
        raise RuntimeError("expected one generated cross-state test fixture")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
