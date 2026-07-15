from dataclasses import replace

import pytest

from aura_coding_arena_planning import inspect_coding_arena_planning_compatibility
from aura_coding_arena_planning_benchmark import _case, _grounding, _task, default_benchmark_cases
from aura_coding_arena_planning_types import CodingArenaCompatibilityStatus


def _valid_inspection():
    case = next(
        item
        for item in default_benchmark_cases()
        if item.case_id == "grounded_single_file_patch"
    )
    return inspect_coding_arena_planning_compatibility(
        case.plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )


def test_patch_output_is_blocked_when_legacy_arena_is_not_ready():
    task = _task(
        task_id="NOT-READY-1",
        objective="Preserve a missing target as a blocked patch proposal.",
        target_file="missing_not_ready.py",
    )
    ground = _grounding(
        task,
        file_exists=False,
        codemap_file_hit=False,
        symbol_exists=True,
        test_files=(),
    )
    case = _case(
        case_id="builder_patch_not_ready",
        tasks=(task,),
        grounding=(ground,),
        routes=(("BUILDER_PATCH", "legacy_route_record"),),
        shadow_ok=True,
        ready_for_incubator=False,
    )

    inspection = inspect_coding_arena_planning_compatibility(
        case.plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert inspection.report.status is CodingArenaCompatibilityStatus.BLOCKED_LEGACY
    assert inspection.report.legacy_ready_for_incubator is False
    assert inspection.report.legacy_routes == ("BUILDER_PATCH",)
    assert inspection.board is not None


@pytest.mark.parametrize(
    "field_name, forged_value",
    [
        ("authority_changed", True),
        ("proposal_only", False),
        ("legacy_mutated", True),
        ("mapped_action_count", 0),
    ],
)
def test_verified_report_rejects_contradictory_contract_state(field_name, forged_value):
    inspection = _valid_inspection()

    with pytest.raises(ValueError):
        replace(inspection.report, **{field_name: forged_value})


def test_inspection_rejects_board_digest_substitution():
    inspection = _valid_inspection()
    forged_report = replace(inspection.report, board_digest="0" * 32)

    with pytest.raises(ValueError):
        replace(inspection, report=forged_report)


def test_failed_inspection_cannot_carry_a_verified_board():
    inspection = _valid_inspection()
    failed_report = replace(
        inspection.report,
        status=CodingArenaCompatibilityStatus.MISMATCHED,
        board_digest=None,
        mapped_action_count=0,
        task_order_preserved=False,
        exact_legacy_preserved=False,
        highest_contiguous_level=None,
        continuity_complete=False,
        findings=(
            replace(
                inspection.report.findings[0],
                code="FORGED",
                message="forged",
            )
            if inspection.report.findings
            else __import__(
                "aura_coding_arena_planning_types",
                fromlist=["CodingArenaCompatibilityFinding"],
            ).CodingArenaCompatibilityFinding("FORGED", "forged")
        ,),
    )

    with pytest.raises(ValueError):
        replace(inspection, report=failed_report)
