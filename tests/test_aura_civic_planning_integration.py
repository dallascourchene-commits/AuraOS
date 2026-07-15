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
    monkeypatch.setattr(runtime, "_store_instance", "IN_MEMORY_ONLY")
    monkeypatch.setattr(runtime, "_ephemeral_store_instance", "IN_MEMORY_ONLY")
    runtime._sessions.clear()
    yield
    runtime._sessions.clear()


def test_real_guided_project_records_project_into_blocked_shadow() -> None:
    guide = start_project("winnipeg_pathways")
    assert guide["ok"] is True
    session_id = guide["session"]["session_id"]

    for _ in range(16):
        if guide["current_step"]["step_id"] == "REVIEW_PACKET":
            break
        assert guide["can_advance"] is True
        guide = advance_project(session_id)
        assert guide["ok"] is True

    assert guide["current_step"]["step_id"] == "REVIEW_PACKET"
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
