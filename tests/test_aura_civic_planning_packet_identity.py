from __future__ import annotations

from copy import deepcopy

from aura_civic_planning import inspect_civic_commons_planning_compatibility
from aura_civic_planning_benchmark import build_case_records
from aura_civic_planning_types import (
    CIVIC_INVENTORY_VERSION,
    CivicCompatibilityStatus,
    CivicPlanningInspection,
    CivicSurfaceEntry,
    CivicSurfaceInventory,
)


def inventory() -> CivicSurfaceInventory:
    return CivicSurfaceInventory(
        entries=(CivicSurfaceEntry("fixture.py", "TEST_FIXTURE", (), "0" * 64),),
        version=CIVIC_INVENTORY_VERSION,
    )


def finding_code(result: CivicPlanningInspection) -> str:
    assert result.report.findings
    return result.report.findings[0].code


def test_stale_decision_packet_is_rejected_before_mapping() -> None:
    project, session = build_case_records("stale-packet", responses=["recorded"])
    session["decision_packet"]["workstreams"] = []

    result = inspect_civic_commons_planning_compatibility(
        project,
        session,
        inventory=inventory(),
    )

    assert result.report.status is CivicCompatibilityStatus.MISMATCHED
    assert finding_code(result) == "DECISION_PACKET_IDENTITY_MISMATCH"
    assert result.report.mapped_action_count == 0
    assert result.board is None


def test_synchronized_packet_copy_remains_structurally_valid() -> None:
    project, session = build_case_records("packet-sync", responses=["recorded"])
    changed = deepcopy(session)
    new_response = {"response_type": "another-record", "binding": False}
    changed["consent_arc"]["responses"].append(dict(new_response))
    changed["decision_packet"]["consent_arc"]["responses"].append(dict(new_response))

    result = inspect_civic_commons_planning_compatibility(
        project,
        changed,
        inventory=inventory(),
    )

    assert result.report.status is CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE
    assert result.report.mapped_action_count == result.report.workstream_count == 2
