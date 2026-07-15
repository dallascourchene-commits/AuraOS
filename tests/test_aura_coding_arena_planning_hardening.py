from copy import deepcopy

import pytest

from aura_coding_arena_planning import (
    CodingArenaProjectionError,
    inspect_coding_arena_planning_compatibility,
    project_coding_arena_planning_board,
)
from aura_coding_arena_planning_benchmark import default_benchmark_cases
from aura_coding_arena_planning_types import CodingArenaCompatibilityStatus


def _case(case_id):
    return next(case for case in default_benchmark_cases() if case.case_id == case_id)


def _payloads(case_id="grounded_single_file_patch"):
    case = _case(case_id)
    return (
        deepcopy(case.plan),
        deepcopy(list(case.grounding)),
        deepcopy(case.shadow_report),
        deepcopy(case.arena),
    )


def _finding_code(inspection):
    assert len(inspection.report.findings) == 1
    return inspection.report.findings[0].code


def test_missing_input_is_unavailable_not_verified():
    case = _case("grounded_single_file_patch")
    inspection = inspect_coding_arena_planning_compatibility(
        None,
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert inspection.report.status is CodingArenaCompatibilityStatus.UNAVAILABLE
    assert _finding_code(inspection) == "INPUT_UNAVAILABLE"
    assert inspection.board is None


def test_duplicate_grounding_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    grounding.append(deepcopy(grounding[0]))

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert inspection.report.status is CodingArenaCompatibilityStatus.MISMATCHED
    assert _finding_code(inspection) == "DUPLICATE_TASK_EVIDENCE"


def test_reordered_routes_are_rejected_even_when_task_set_matches():
    plan, grounding, shadow, arena = _payloads("grounded_multi_act_patch")
    arena["routing_decisions"].reverse()

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert inspection.report.status is CodingArenaCompatibilityStatus.MISMATCHED
    assert _finding_code(inspection) == "TASK_ORDER_MISMATCH"


def test_substituted_arena_act_capsule_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["agent_capsules"][0]["objective"] = "Substituted objective"

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "ACT_CAPSULE_SUBSTITUTION"


def test_grounding_identity_substitution_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    grounding[0]["target_file"] = "other.py"
    arena["affected_files"] = ["other.py"]

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "GROUNDING_IDENTITY_MISMATCH"


def test_lease_write_scope_expansion_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["agent_leases"][0]["regions"].append(
        {"region_type": "file", "id": "outside.py", "mode": "write"}
    )

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "LEASE_WRITE_SCOPE_MISMATCH"


def test_lease_read_scope_escape_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["agent_leases"][0]["regions"].append(
        {"region_type": "file", "id": "unseen.py", "mode": "read"}
    )

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "LEASE_READ_SCOPE_ESCAPE"


def test_boundary_scope_substitution_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["boundary_contracts"][0]["owned_scope"] = ["outside.py"]

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "BOUNDARY_SCOPE_MISMATCH"


def test_plan_phase_hash_mismatch_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["plan_phase_hash"] = "different-phase"

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "PLAN_PHASE_HASH_MISMATCH"


def test_shadow_phase_hash_substitution_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    shadow["phase_hash"] = "0" * 32
    arena["shadow_report"] = deepcopy(shadow)

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "SHADOW_PHASE_HASH_MISMATCH"


def test_shadow_finding_for_unknown_task_is_rejected_before_projection():
    plan, grounding, shadow, arena = _payloads("warning_missing_test")
    shadow["findings"][0]["task_id"] = "UNKNOWN"
    arena["shadow_report"] = deepcopy(shadow)

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "SHADOW_UNKNOWN_TASK"


def test_affected_files_must_exactly_match_existing_grounded_targets():
    plan, grounding, shadow, arena = _payloads()
    arena["affected_files"] = []

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "AFFECTED_FILES_MISMATCH"


def test_liquid_arena_action_reordering_is_rejected():
    plan, grounding, shadow, arena = _payloads("grounded_multi_act_patch")
    arena["liquid_arena"]["action_capsules"].reverse()

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "LIQUID_ACTION_ORDER_MISMATCH"


@pytest.mark.parametrize(
    "unsafe_path, expected_code",
    [
        ("../escape.py", "UNSAFE_PATH"),
        ("/absolute.py", "UNSAFE_PATH"),
        ("C:/drive.py", "UNSAFE_PATH"),
        ("folder\\windows.py", "NONCANONICAL_PATH"),
    ],
)
def test_unsafe_or_noncanonical_target_paths_are_rejected(unsafe_path, expected_code):
    plan, grounding, shadow, arena = _payloads()
    plan["act_capsules"][0]["target_file"] = unsafe_path
    arena["agent_capsules"][0]["target_file"] = unsafe_path
    grounding[0]["target_file"] = unsafe_path
    arena["routing_decisions"][0]["target_file"] = unsafe_path
    arena["routing_decisions"][0]["frame"]["target_file"] = unsafe_path
    arena["boundary_contracts"][0]["target_file"] = unsafe_path
    arena["boundary_contracts"][0]["owned_scope"] = [unsafe_path]
    arena["agent_leases"][0]["regions"][0]["id"] = unsafe_path
    arena["affected_files"] = [unsafe_path]

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == expected_code


def test_integer_boolean_is_not_accepted_as_legacy_truth():
    plan, grounding, shadow, arena = _payloads()
    grounding[0]["file_exists"] = 1

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "INVALID_BOOLEAN"


def test_non_string_task_identity_is_rejected_instead_of_stringified():
    plan, grounding, shadow, arena = _payloads()
    plan["act_capsules"][0]["task_id"] = 7
    arena["agent_capsules"][0]["task_id"] = 7

    inspection = inspect_coding_arena_planning_compatibility(plan, grounding, shadow, arena)

    assert _finding_code(inspection) == "INVALID_STRING"


def test_generator_grounding_is_rejected_as_nonconcrete():
    case = _case("grounded_single_file_patch")
    grounding = (item for item in case.grounding)

    inspection = inspect_coding_arena_planning_compatibility(
        case.plan,
        grounding,
        case.shadow_report,
        case.arena,
    )

    assert _finding_code(inspection) == "INVALID_SEQUENCE"


class _FlippingPlan:
    def __init__(self, payload):
        self.payload = deepcopy(payload)
        self.calls = 0

    def to_dict(self):
        self.calls += 1
        result = deepcopy(self.payload)
        result["objective"] = f"objective-call-{self.calls}"
        return result


def test_input_mutation_between_projection_reads_is_detected():
    case = _case("grounded_single_file_patch")
    plan = _FlippingPlan(case.plan)

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert inspection.report.status is CodingArenaCompatibilityStatus.MISMATCHED
    assert _finding_code(inspection) == "LEGACY_MUTATION_DETECTED"


def test_strict_projection_raises_stable_error_for_mismatch():
    plan, grounding, shadow, arena = _payloads()
    arena["affected_files"] = []

    with pytest.raises(CodingArenaProjectionError) as exc_info:
        project_coding_arena_planning_board(plan, grounding, shadow, arena)

    assert exc_info.value.code == "AFFECTED_FILES_MISMATCH"
