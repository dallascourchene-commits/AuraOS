from __future__ import annotations

import pytest

from aura_arena_admission import (
    ActionClass,
    ArenaAdmissionContext,
    ArenaAdmissionError,
    ERROR_CODE,
    assert_substantive_allowed,
    evaluate_admission,
    orientation_receipt,
)


def admitted(**overrides) -> ArenaAdmissionContext:
    values = dict(
        worker_id="J-06",
        role="worker",
        capabilities=("reasoning", "drive"),
        effect_ceiling="D0",
        project_coordinate="aura://creator-studio/project/CS-PROJ-001",
        front_door_ref="drive:front",
        collab_board_ref="drive:board",
        mission_ref="front#mission",
        purpose_ref="front#purpose",
        temporary_mission_active=True,
        temporary_mission_ref="drive:CS-HARNESS-001",
        authoritative_head_ref="R8:head",
        currentness_current=True,
        join_record_ref="board:join:J-06",
        claimed_cells=("H-A",),
        sibling_state_ref="board:rev:123",
        sibling_state_digest="sha256:abc",
        route_tier="R1",
        route_reason="stdlib/local deterministic implementation",
    )
    values.update(overrides)
    return ArenaAdmissionContext(**values)


def test_orientation_allowed_before_admission_but_not_substantive():
    ctx = ArenaAdmissionContext()
    orient = evaluate_admission(ctx, ActionClass.ORIENT)
    work = evaluate_admission(ctx, ActionClass.SUBSTANTIVE)
    assert orient.allowed is True
    assert orient.code == ERROR_CODE
    assert work.allowed is False
    assert "ARENA_ENTERED" in work.missing
    assert "ROUTE_BOUND" in work.missing


def test_repair_admission_allowed_while_gate_incomplete():
    decision = evaluate_admission(ArenaAdmissionContext(), ActionClass.REPAIR_ADMISSION)
    assert decision.allowed is True
    assert decision.missing


def test_complete_worker_is_admitted():
    decision = assert_substantive_allowed(admitted())
    assert decision.allowed is True
    assert decision.code == "ADMITTED"
    assert decision.missing == ()


def test_active_temporary_mission_must_be_bound():
    decision = evaluate_admission(admitted(temporary_mission_ref=None))
    assert decision.allowed is False
    assert "MISSION_BOUND" in decision.missing


def test_stale_currentness_fails_closed():
    decision = evaluate_admission(admitted(currentness_current=False))
    assert decision.allowed is False
    assert "CURRENTNESS_BOUND" in decision.missing


def test_worker_requires_exactly_one_claim():
    none = evaluate_admission(admitted(claimed_cells=()))
    two = evaluate_admission(admitted(claimed_cells=("H-A", "H-D")))
    assert "CLAIM_BOUND" in none.missing
    assert "CLAIM_BOUND" in two.missing


def test_explicit_reducer_can_be_claimless():
    decision = evaluate_admission(admitted(role="reducer", claimed_cells=()))
    assert decision.allowed is True
    assert "CLAIM_BOUND" in decision.satisfied


def test_unknown_role_does_not_bypass_claim():
    decision = evaluate_admission(admitted(role="mission-owner-ish", claimed_cells=()))
    assert decision.allowed is False
    assert "CLAIM_BOUND" in decision.missing


def test_sibling_state_requires_reference_and_digest():
    no_ref = evaluate_admission(admitted(sibling_state_ref=None))
    no_digest = evaluate_admission(admitted(sibling_state_digest=None))
    assert "SIBLING_STATE_SEEN" in no_ref.missing
    assert "SIBLING_STATE_SEEN" in no_digest.missing


def test_route_requires_known_tier_and_reason():
    unknown = evaluate_admission(admitted(route_tier="CHEAP"))
    no_reason = evaluate_admission(admitted(route_reason=None))
    assert "ROUTE_BOUND" in unknown.missing
    assert "ROUTE_BOUND" in no_reason.missing


def test_assert_raises_typed_admission_error():
    with pytest.raises(ArenaAdmissionError) as exc:
        assert_substantive_allowed(ArenaAdmissionContext())
    assert exc.value.decision.code == ERROR_CODE
    assert exc.value.decision.allowed is False


def test_receipt_is_deterministic_and_not_execution_proof():
    ctx = admitted()
    first = orientation_receipt(ctx)
    second = orientation_receipt(ctx)
    assert first["receipt_id"] == second["receipt_id"]
    assert first["substantive_allowed"] is True
    assert first["execution_claim"] is False


def test_claim_order_and_duplicates_do_not_change_receipt():
    a = admitted(claimed_cells=("H-D", "H-A", "H-A"))
    b = admitted(claimed_cells=("H-A", "H-D"))
    assert orientation_receipt(a)["receipt_id"] == orientation_receipt(b)["receipt_id"]


def test_unknown_action_class_fails_closed_as_programming_error():
    with pytest.raises(ValueError):
        evaluate_admission(admitted(), "DO_WHATEVER")
