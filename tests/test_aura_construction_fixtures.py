from __future__ import annotations

from aura_construction_adapter import ConstructionArenaMode
from aura_construction_fixtures import (
    CONSTRUCTION_FIXTURE_VERSION,
    PROJECT_ID,
    build_sco_construction_demo_fixture,
    build_sco_construction_demo_runtime_packet,
)
from aura_construction_state import query_claim_readiness


def test_fixture_is_synthetic_and_contains_no_production_connectors():
    fixture = build_sco_construction_demo_fixture()
    assert fixture.version == CONSTRUCTION_FIXTURE_VERSION
    assert fixture.synthetic is True
    assert fixture.private_data_used is False
    assert fixture.production_connectors_used is False


def test_fixture_replay_is_deterministic():
    first = build_sco_construction_demo_fixture()
    second = build_sco_construction_demo_fixture()
    assert first.state.state_digest == second.state.state_digest
    assert first.candidates == second.candidates
    assert first.probabilistic_signals == second.probabilistic_signals


def test_fixture_uses_expected_project_and_event_chain():
    fixture = build_sco_construction_demo_fixture()
    assert fixture.state.project_id == PROJECT_ID
    assert len(fixture.state.events) == 8
    assert fixture.state.final_chain_digest == fixture.state.events[-1].chain_digest


def test_sensor_only_clearance_claim_is_not_evidence_ready():
    fixture = build_sco_construction_demo_fixture()
    report = query_claim_readiness(
        fixture.state,
        claim_id=fixture.blocked_clearance_claim_id,
        now=30.0,
    )
    assert report.ready is False
    assert "non_dispositive_evidence_only" in report.blockers
    assert report.physical_work_authorized is False


def test_other_fixture_claims_are_ready_for_authority_review():
    fixture = build_sco_construction_demo_fixture()
    ready = []
    for claim in fixture.claims:
        if claim.claim_id == fixture.blocked_clearance_claim_id:
            continue
        ready.append(
            query_claim_readiness(
                fixture.state,
                claim_id=claim.claim_id,
                now=30.0,
            ).ready
        )
    assert ready and all(ready)


def test_fixture_has_four_materially_different_candidates():
    fixture = build_sco_construction_demo_fixture()
    assert len(fixture.candidates) == 4
    assert len({item.title for item in fixture.candidates}) == 4
    assert len({item.projected_cost_delta_cad for item in fixture.candidates}) == 4
    assert len({item.projected_time_delta_hours for item in fixture.candidates}) == 4


def test_fixture_deliberately_gives_blocked_route_highest_model_score():
    fixture = build_sco_construction_demo_fixture()
    highest = max(fixture.probabilistic_signals, key=lambda item: item.aggregate_score)
    blocked_candidate = next(
        item
        for item in fixture.candidates
        if fixture.blocked_clearance_claim_id in item.required_claim_ids
    )
    assert highest.candidate_id == blocked_candidate.candidate_id


def test_runtime_packet_is_synthetic_and_read_only():
    packet = build_sco_construction_demo_runtime_packet()
    assert packet["ok"] is True
    assert packet["action_capsule"]["target"]["mode"] == ConstructionArenaMode.SYNTHETIC.value
    assert packet["arena_lease"]["mode"] == "read_only"
    assert packet["source_records_mutated"] is False
    assert packet["physical_work_authorized"] is False


def test_runtime_packet_recommends_only_an_admissible_option():
    packet = build_sco_construction_demo_runtime_packet()
    evaluation = packet["evaluation"]
    admissible = {
        item["candidate_id"]
        for item in evaluation["assessments"]
        if item["admissible"]
    }
    assert evaluation["recommended_candidate_id"] in admissible
    assert set(evaluation["option_candidate_ids"]).issubset(admissible)


def test_fixture_serialization_preserves_claim_boundaries():
    payload = build_sco_construction_demo_fixture().to_dict()
    assert payload["synthetic"] is True
    assert payload["private_data_used"] is False
    assert all(item["proposal_only"] for item in payload["candidates"])
    assert all(not item["runtime_authority"] for item in payload["probabilistic_signals"])
