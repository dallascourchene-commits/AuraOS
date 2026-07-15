from __future__ import annotations

from pathlib import Path

import pytest

import aura_civic_runtime as runtime
from aura_civic_guided_project import advance_project, start_project
from aura_civic_planning import inspect_civic_commons_planning_compatibility
from aura_civic_planning_types import CivicCompatibilityStatus
from aura_civic_projects import require_project


@pytest.fixture(autouse=True)
def _isolate_runtime(monkeypatch):
    monkeypatch.setenv("AURA_CIVIC_STORE_BACKEND", "memory")
    monkeypatch.delenv("AURA_CIVIC_STORE_PATH", raising=False)
    runtime.reset_runtime_state()
    yield
    runtime.reset_runtime_state()


def test_real_guided_project_records_project_into_blocked_shadow() -> None:
    guide = start_project("winnipeg_pathways")
    session_id = guide["guide"]["session_id"]

    for _ in range(16):
        if guide["guide"]["current_step"] == "REVIEW_PACKET":
            break
        guide = advance_project(session_id)

    assert guide["guide"]["current_step"] == "REVIEW_PACKET"
    session = runtime.get_session(session_id)["session"]
    project = require_project("winnipeg_pathways").to_dict()

    result = inspect_civic_commons_planning_compatibility(
        project,
        session,
        repo_root=Path(__file__).resolve().parents[1],
    )

    assert result.report.status is CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE
    assert result.report.workstream_count > 0
    assert result.report.mapped_action_count == result.report.workstream_count
    assert result.report.governance_blockers == (
        "human_governance_authorization_contract_absent",
    )
    assert result.board is not None
    assert len(result.board.actions) == len(session["workstreams"])
