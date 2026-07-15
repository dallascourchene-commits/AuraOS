from __future__ import annotations

from dataclasses import replace

import pytest

from aura_civic_planning import inspect_civic_commons_planning_compatibility
from aura_civic_planning_benchmark import build_case_records
from aura_civic_planning_types import CIVIC_INVENTORY_VERSION, CivicSurfaceEntry, CivicSurfaceInventory


def inventory() -> CivicSurfaceInventory:
    return CivicSurfaceInventory(entries=(CivicSurfaceEntry("fixture.py", "TEST_FIXTURE", (), "0" * 64),), version=CIVIC_INVENTORY_VERSION)


def test_inspection_rejects_inconsistent_board_shape() -> None:
    project, session = build_case_records("shape-binding", responses=["recorded"])
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert result.board is not None

    with pytest.raises(ValueError):
        replace(result, board=replace(result.board, board_id="other-board"))

    changed_action = replace(result.board.actions[0], domain="other-domain")
    with pytest.raises(ValueError):
        replace(result, board=replace(result.board, actions=(changed_action, *result.board.actions[1:])))

    changed_goal = replace(result.board.goal, goal_id="other-goal")
    with pytest.raises(ValueError):
        replace(result, board=replace(result.board, goal=changed_goal))

    with pytest.raises(ValueError):
        replace(result.report, governance_blockers=("unsupported",))
