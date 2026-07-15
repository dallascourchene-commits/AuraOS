from copy import deepcopy

from aura_coding_arena_planning import inspect_coding_arena_planning_compatibility
from aura_coding_arena_planning_benchmark import default_benchmark_cases
from aura_coding_arena_planning_types import CodingArenaCompatibilityStatus


def _case(case_id="grounded_single_file_patch"):
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
    assert inspection.report.status in {
        CodingArenaCompatibilityStatus.MISMATCHED,
        CodingArenaCompatibilityStatus.UNAVAILABLE,
    }
    assert len(inspection.report.findings) == 1
    return inspection.report.findings[0].code


def test_top_level_symbol_lease_substitution_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["agent_leases"] = deepcopy(arena["agent_leases"])
    symbol_region = arena["agent_leases"][0]["regions"][-1]
    assert symbol_region["region_type"] == "symbol"
    symbol_region["id"] = "other_symbol"

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "TOP_LEVEL_LEASE_SUBSTITUTION"


def test_unknown_lease_region_type_is_rejected_before_projection():
    plan, grounding, shadow, arena = _payloads()
    arena["agent_leases"][0]["regions"].append(
        {"region_type": "directory", "id": "tests", "mode": "write"}
    )

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "UNKNOWN_LEASE_REGION_TYPE"


def test_liquid_action_hash_or_payload_substitution_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["liquid_arena"]["action_capsules"][0]["phase_hash"] = "0" * 32

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "LIQUID_ACTION_DERIVATION_MISMATCH"


def test_liquid_boundary_substitution_is_rejected_even_if_top_copy_is_unchanged():
    plan, grounding, shadow, arena = _payloads()
    arena["liquid_arena"]["boundary_contracts"][0]["invariant"] = "weakened"

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "BOUNDARY_DERIVATION_MISMATCH"


def test_liquid_arena_phase_hash_substitution_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["liquid_arena"]["phase_hash"] = "0" * 32

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "LIQUID_ARENA_PHASE_HASH_MISMATCH"


def test_liquid_adapter_authority_invariant_substitution_is_rejected():
    plan, grounding, shadow, arena = _payloads()
    arena["liquid_arena"]["adapter"]["invariant"] = "models execute autonomously"

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "LIQUID_ADAPTER_MISMATCH"


def test_ready_for_incubator_must_match_shadow_grounding_and_routes():
    plan, grounding, shadow, arena = _payloads("inspect_only_route")
    arena["ready_for_incubator"] = True

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "READY_FOR_INCUBATOR_MISMATCH"


def test_boundary_metadata_task_id_is_not_string_coerced():
    plan, grounding, shadow, arena = _payloads()
    arena["boundary_contracts"][0]["metadata"]["task_id"] = 7

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "INVALID_STRING"


def test_route_reason_is_required_as_a_string():
    plan, grounding, shadow, arena = _payloads()
    arena["routing_decisions"][0]["reason"] = 7

    inspection = inspect_coding_arena_planning_compatibility(
        plan,
        grounding,
        shadow,
        arena,
    )

    assert _finding_code(inspection) == "INVALID_STRING"


class _BrokenRecord:
    def to_dict(self):
        raise RuntimeError("snapshot exploded")


def test_snapshot_exceptions_become_unavailable_findings():
    case = _case()

    inspection = inspect_coding_arena_planning_compatibility(
        _BrokenRecord(),
        case.grounding,
        case.shadow_report,
        case.arena,
    )

    assert inspection.report.status is CodingArenaCompatibilityStatus.UNAVAILABLE
    assert _finding_code(inspection) == "INPUT_SNAPSHOT_FAILED"
