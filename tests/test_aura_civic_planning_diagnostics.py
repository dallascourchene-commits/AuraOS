from __future__ import annotations

from aura_civic_planning import inspect_civic_commons_planning_compatibility
from aura_civic_planning_benchmark import build_case_records
from aura_civic_planning_types import CIVIC_INVENTORY_VERSION, CivicSurfaceEntry, CivicSurfaceInventory


def inventory() -> CivicSurfaceInventory:
    return CivicSurfaceInventory(entries=(CivicSurfaceEntry("fixture.py", "TEST_FIXTURE", (), "0" * 64),), version=CIVIC_INVENTORY_VERSION)


def test_boundary_diagnostics_match_findings() -> None:
    project, session = build_case_records("boundary-diagnostic", responses=["recorded"])
    session["vsa_patch_authority"] = True
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert result.report.authority_changed is True
    assert result.report.source_mutated is False


def test_source_change_diagnostic_is_true() -> None:
    project, session = build_case_records("source-diagnostic", responses=["recorded"])

    class Changing(dict):
        calls = 0

        def items(self):
            type(self).calls += 1
            if type(self).calls > 1:
                self["state"] = "CHANGED"
            return super().items()

    result = inspect_civic_commons_planning_compatibility(project, Changing(session), inventory=inventory())
    assert result.report.source_mutated is True
    assert result.report.authority_changed is False
