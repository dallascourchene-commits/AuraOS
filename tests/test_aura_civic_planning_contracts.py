from __future__ import annotations

from dataclasses import replace

import pytest

from aura_civic_planning import inspect_civic_commons_planning_compatibility
from aura_civic_planning_benchmark import build_case_records
from aura_civic_planning_types import (
    CIVIC_INVENTORY_VERSION,
    CivicRecordBindings,
    CivicSurfaceEntry,
    CivicSurfaceInventory,
)


def inventory() -> CivicSurfaceInventory:
    return CivicSurfaceInventory(entries=(CivicSurfaceEntry("fixture.py", "TEST_FIXTURE", (), "0" * 64),), version=CIVIC_INVENTORY_VERSION)


def test_contract_rejects_inconsistent_external_evidence() -> None:
    project, session = build_case_records("inconsistent-evidence", responses=["recorded"])
    result = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    assert result.bindings is not None
    with pytest.raises(ValueError):
        replace(result.bindings, authorization_contract_present=True)
    changed = replace(result.mappings[0], evidence_refs=("x", *result.mappings[0].evidence_refs[1:]))
    with pytest.raises(ValueError):
        replace(result, mappings=(changed, *result.mappings[1:]))
    changed_evidence = replace(result.action_evidence[0], authority_decision_ids=("unexpected",))
    with pytest.raises(ValueError):
        replace(result, action_evidence=(changed_evidence, *result.action_evidence[1:]))


def test_record_binding_constructor_requires_exact_presence() -> None:
    with pytest.raises(ValueError, match="presence and digest disagree"):
        CivicRecordBindings("0" * 32, "1" * 32, "2" * 32, None, True)
