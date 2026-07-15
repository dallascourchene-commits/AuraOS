from __future__ import annotations

from aura_civic_planning import inspect_civic_commons_planning_compatibility
from aura_civic_planning_benchmark import build_case_records
from aura_civic_planning_types import (
    CIVIC_INVENTORY_VERSION,
    CivicCompatibilityStatus,
    CivicPlanningInspection,
    CivicSurfaceEntry,
    CivicSurfaceInventory,
)
from aura_planning_board import AuthorityRequirement


def inventory() -> CivicSurfaceInventory:
    return CivicSurfaceInventory(entries=(CivicSurfaceEntry("fixture.py", "TEST_FIXTURE", (), "0" * 64),), version=CIVIC_INVENTORY_VERSION)


def finding_code(result: CivicPlanningInspection) -> str:
    assert result.report.findings
    return result.report.findings[0].code


def test_structural_projection_is_complete_and_blocked() -> None:
    project, session = build_case_records("golden", responses=["recorded-a", "recorded-b"])
    original_project = dict(project)
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert result.report.status is CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE
    assert result.report.mapped_action_count == result.report.workstream_count == 2
    assert result.report.governance_blockers == ("human_governance_authorization_contract_absent",)
    assert result.board is not None
    assert all(action.proposal_only for action in result.board.actions)
    assert all(action.authority_requirement is AuthorityRequirement.HUMAN for action in result.board.actions)
    assert all(not action.verifier_ids for action in result.board.actions)
    assert project == original_project


def test_missing_decision_packet_adds_blocker_without_dropping_mapping() -> None:
    project, session = build_case_records("missing", responses=["recorded"], include_decision_packet=False)
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert result.report.status is CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE
    assert result.report.mapped_action_count == 2
    assert result.report.governance_blockers == ("human_governance_authorization_contract_absent", "decision_packet_absent")


def test_authority_and_lineage_fail_closed() -> None:
    project, session = build_case_records("authority", responses=["recorded"])
    session["vsa_patch_authority"] = True
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert result.report.status is CivicCompatibilityStatus.MISMATCHED
    assert finding_code(result) == "ADVISORY_AUTHORITY_ESCALATION"

    project, session = build_case_records("dependency", responses=["recorded"])
    session["workstreams"][0]["dependencies"] = [session["workstreams"][1]["workstream_id"]]
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert result.report.status is CivicCompatibilityStatus.MISMATCHED
    assert finding_code(result) == "WORKSTREAM_DEPENDENCY_MISMATCH"


def test_profile_digest_and_required_record_substitution_fail_closed() -> None:
    project, session = build_case_records("profile", responses=["recorded"])
    session["profile_set"]["jurisdiction_profile_refs"].append("jurisdiction://substituted")
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert finding_code(result) == "PROFILE_DIGEST_MISMATCH"

    project, session = build_case_records("missing-record", responses=["recorded"])
    session["consent_arc"] = None
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert result.report.status is CivicCompatibilityStatus.UNAVAILABLE
    assert finding_code(result) == "CIVIC_RECORD_UNAVAILABLE"
