from copy import deepcopy

from aura_coding_arena_planning import (
    inspect_coding_arena_planning_compatibility,
    project_coding_arena_planning_board,
)
from aura_coding_arena_planning_benchmark import default_benchmark_cases
from aura_coding_arena_planning_types import CodingArenaCompatibilityStatus
from aura_planning_board import AuthorityRequirement, BoardContinuityLevel


def _case(case_id):
    return next(case for case in default_benchmark_cases() if case.case_id == case_id)


def test_grounded_single_file_projection_reaches_bc3_without_authority():
    case = _case("grounded_single_file_patch")

    inspection = project_coding_arena_planning_board(
        case.plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert inspection.report.status is CodingArenaCompatibilityStatus.VERIFIED_SHADOW
    assert inspection.report.task_count == 1
    assert inspection.report.mapped_action_count == 1
    assert inspection.report.highest_contiguous_level == BoardContinuityLevel.BC3_GROUNDED.value
    assert inspection.report.continuity_complete is False
    assert inspection.board is not None
    assert inspection.continuity is not None
    assert inspection.continuity.highest_contiguous_level is BoardContinuityLevel.BC3_GROUNDED
    action = inspection.board.actions[0]
    assert action.proposal_only is True
    assert action.authority_requirement is AuthorityRequirement.HUMAN
    assert action.verifier_ids == (
        "test:tests/test_aura_parser.py",
        "shadow:ALLOW_BUILDER",
        "route:BUILDER_PATCH",
    )
    assert inspection.action_evidence[0].authority_decision_ids == ()
    assert inspection.action_evidence[0].verifier_receipts == ()


def test_blocked_legacy_work_still_projects_without_elevating_authority():
    case = _case("blocked_missing_file")

    inspection = inspect_coding_arena_planning_compatibility(
        case.plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert inspection.report.status is CodingArenaCompatibilityStatus.BLOCKED_LEGACY
    assert inspection.report.legacy_ready_for_incubator is False
    assert inspection.report.legacy_shadow_gate == "BLOCK_BUILDER"
    assert inspection.report.highest_contiguous_level == BoardContinuityLevel.BC2_CONSTRAINED.value
    assert inspection.board is not None
    assert inspection.action_evidence[0].grounded_evidence_refs == ()
    assert inspection.report.authority_changed is False
    assert inspection.report.proposal_only is True


def test_non_builder_patch_route_remains_blocked_with_exact_route_preserved():
    case = _case("grounded_single_file_patch")
    plan = deepcopy(case.plan)
    grounding = deepcopy(list(case.grounding))
    shadow_report = deepcopy(case.shadow_report)
    arena = deepcopy(case.arena)
    arena["routing_decisions"][0]["route"] = "TEST_GAP_FILL"
    arena["routing_decisions"][0]["symbol_output"] = "TEST_GAP_FILL"
    arena["ready_for_incubator"] = False

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow_report,
        arena,
    )

    assert inspection.report.status is CodingArenaCompatibilityStatus.BLOCKED_LEGACY
    assert inspection.report.legacy_routes == ("TEST_GAP_FILL",)
    assert inspection.mappings[0].route == "TEST_GAP_FILL"
    assert inspection.mappings[0].expected_output == "UNIFIED_DIFF"
    assert inspection.board is not None
    assert inspection.report.authority_changed is False


def test_inspect_only_route_is_verified_but_preserves_not_ready_legacy_state():
    case = _case("inspect_only_route")

    inspection = inspect_coding_arena_planning_compatibility(
        case.plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert inspection.report.status is CodingArenaCompatibilityStatus.VERIFIED_SHADOW
    assert inspection.report.legacy_ready_for_incubator is False
    assert inspection.report.legacy_routes == ("RESEARCH_DECOMPOSE",)
    assert inspection.mappings[0].expected_output == "TEXT"
    assert inspection.board.actions[0].output_ports[0].name == "candidate_analysis"


def test_multi_act_projection_preserves_task_order_and_one_to_one_mapping():
    case = _case("grounded_multi_act_patch")

    inspection = project_coding_arena_planning_board(
        case.plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert [item.task_id for item in inspection.mappings] == ["MULTI-1", "MULTI-2"]
    assert [item.action_id for item in inspection.mappings] == [
        action.action_id for action in inspection.board.actions
    ]
    assert inspection.report.task_order_preserved is True
    assert inspection.report.exact_legacy_preserved is True
    assert inspection.report.legacy_mutated is False


def test_projection_is_deterministic_for_identical_legacy_records():
    case = _case("warning_missing_test")

    first = inspect_coding_arena_planning_compatibility(
        case.plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )
    second = inspect_coding_arena_planning_compatibility(
        case.plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert first.digest == second.digest
    assert first.board.digest == second.board.digest
    assert first.report.digest == second.report.digest
