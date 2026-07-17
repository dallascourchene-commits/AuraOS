"""Adversarial tests for the Construction Human Agent and Observatory profile."""
from __future__ import annotations

import pytest

from aura_construction_adapter import (
    ConstructionArenaMode,
    ConstructionCoordinationEvaluation,
    evaluate_construction_candidates,
)
from aura_construction_fixtures import build_sco_construction_demo_fixture
from aura_event_contracts import stable_digest, stable_id
from aura_construction_human_agent import (
    ConstructionHumanAgentProfileService,
    build_construction_human_agent_profile,
)


def _profile_inputs():
    fixture = build_sco_construction_demo_fixture()
    evaluation = evaluate_construction_candidates(
        fixture.state,
        candidates=fixture.candidates,
        now=20.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=fixture.candidates[0].lane,
        probabilistic_signals=fixture.probabilistic_signals,
    )
    return fixture, evaluation


def test_profile_is_read_only_proposal_only_and_bound_to_exact_state():
    fixture, evaluation = _profile_inputs()
    profile = build_construction_human_agent_profile(
        fixture.state,
        evaluation,
        candidates=fixture.candidates,
        synthetic=True,
    )
    payload = profile.to_dict()

    assert profile.state_digest == fixture.state.state_digest
    assert profile.evaluation_digest == evaluation.evaluation_digest
    assert profile.recommended_candidate_id == evaluation.recommended_candidate_id
    assert payload["read_only"] is True
    assert payload["proposal_only"] is True
    assert payload["human_review_required"] is True
    assert payload["physical_work_authorized"] is False
    assert payload["payment_released"] is False
    assert payload["access_controlled"] is False
    assert payload["raw_records_included"] is False
    assert payload["vsa_patch_authority"] is False


def test_profile_rejects_evaluation_from_another_state():
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


def test_profile_rejects_missing_or_duplicate_candidate_identity():
    fixture, evaluation = _profile_inputs()

    with pytest.raises(ValueError, match="identities do not match"):
        build_construction_human_agent_profile(
            fixture.state,
            evaluation,
            candidates=fixture.candidates[:-1],
        )
    with pytest.raises(ValueError, match="candidate IDs must be unique"):
        build_construction_human_agent_profile(
            fixture.state,
            evaluation,
            candidates=(*fixture.candidates, fixture.candidates[0]),
        )


def test_profile_does_not_export_raw_evidence_or_source_references():
    service = ConstructionHumanAgentProfileService(demo=True)
    payload = service.get_profile()
    rendered = str(payload).lower()

    assert "source_ref" not in rendered
    assert "payload_digest" not in rendered
    assert "actor_id" not in rendered
    assert "claimant_id" not in rendered
    assert "raw_records_included': true" not in rendered


def test_observatory_projection_omits_narratives_amounts_and_execution_methods():
    service = ConstructionHumanAgentProfileService(demo=True)
    projection = service.get_observatory_projection()
    rendered = str(projection).lower()

    assert projection["read_only"] is True
    assert projection["payload_included"] is False
    assert projection["raw_records_included"] is False
    assert projection["candidate_narratives_included"] is False
    assert projection["execution_methods"] == []
    assert "summary" not in rendered
    assert "projected_cost" not in rendered
    assert "projected_time" not in rendered
    assert "source_ref" not in rendered


def test_blocked_candidate_remains_visible_but_cannot_be_recommended():
    service = ConstructionHumanAgentProfileService(demo=True)
    profile = service.profile
    assert profile is not None
    blocked = next(item for item in profile.candidates if not item.admissible)
    detail = service.get_candidate(blocked.candidate_id)

    assert detail["candidate"]["admissible"] is False
    assert detail["candidate"]["blockers"]
    assert detail["candidate"]["recommended"] is False
    assert detail["physical_work_authorized"] is False
    assert detail["payment_released"] is False


def test_handoff_is_payload_free_and_target_arena_is_not_mutated():
    service = ConstructionHumanAgentProfileService(demo=True)
    packet = service.prepare_handoff("agent_bridge_arena")

    assert packet["digital_baton_only"] is True
    assert packet["payload_included"] is False
    assert packet["raw_records_included"] is False
    assert packet["target_arena_mutated"] is False
    assert packet["human_review_required"] is True
    assert packet["physical_work_authorized"] is False
    assert packet["payment_released"] is False

    with pytest.raises(ValueError, match="unsupported target arena"):
        service.prepare_handoff("physical_site_controller")


def test_non_demo_service_fails_closed_until_exact_state_is_loaded():
    service = ConstructionHumanAgentProfileService(demo=False)

    assert service.status()["available"] is False
    with pytest.raises(KeyError, match="profile is unavailable"):
        service.get_profile()
    with pytest.raises(KeyError, match="profile is unavailable"):
        service.get_observatory_projection()
