from __future__ import annotations

from itertools import product

from aura_civic_planning import inspect_civic_commons_planning_compatibility
from aura_civic_planning_benchmark import build_case_records
from aura_civic_planning_types import CIVIC_INVENTORY_VERSION, CivicCompatibilityStatus, CivicSurfaceEntry, CivicSurfaceInventory


def _inventory() -> CivicSurfaceInventory:
    return CivicSurfaceInventory(entries=(CivicSurfaceEntry("fixture.py", "TEST_FIXTURE", (), "0" * 64),), version=CIVIC_INVENTORY_VERSION)


def test_opaque_record_combinations_are_bound_without_interpretation() -> None:
    labels = tuple(f"record-{index}" for index in range(8))
    checked = 0
    for length in (1, 2, 3):
        for values in product(labels, repeat=length):
            project, session = build_case_records(f"combo-{checked}", responses=list(values))
            result = inspect_civic_commons_planning_compatibility(project, session, inventory=_inventory())
            assert result.report.status is CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE
            assert result.report.governance_blockers == ("human_governance_authorization_contract_absent",)
            checked += 1
    assert checked == 584
