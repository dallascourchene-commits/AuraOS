from __future__ import annotations

from copy import deepcopy

from aura_civic_planning import inspect_civic_commons_planning_compatibility
from aura_civic_planning_benchmark import build_case_records, run_benchmark
from aura_civic_planning_types import (
    CIVIC_INVENTORY_VERSION,
    CivicCompatibilityStatus,
    CivicPlanningInspection,
    CivicSurfaceEntry,
    CivicSurfaceInventory,
)
from aura_event_contracts import canonical_json


def inventory() -> CivicSurfaceInventory:
    return CivicSurfaceInventory(entries=(CivicSurfaceEntry("fixture.py", "TEST_FIXTURE", (), "0" * 64),), version=CIVIC_INVENTORY_VERSION)


def finding_code(result: CivicPlanningInspection) -> str:
    assert result.report.findings
    return result.report.findings[0].code


def test_input_mutation_is_detected() -> None:
    project, session = build_case_records("mutation", responses=["recorded"])

    class Mutating(dict):
        calls = 0

        def items(self):
            type(self).calls += 1
            if type(self).calls > 1:
                self["state"] = "MUTATED"
            return super().items()

    result = inspect_civic_commons_planning_compatibility(project, Mutating(session), inventory=inventory())
    assert result.report.status is CivicCompatibilityStatus.MISMATCHED
    assert finding_code(result) == "SESSION_CHANGED_DURING_INSPECTION"


def test_record_binding_digest_changes_without_changing_status() -> None:
    project, session = build_case_records("digest-a", responses=["recorded"])
    first = inspect_civic_commons_planning_compatibility(project, session, inventory=inventory())
    changed = deepcopy(session)
    changed["consent_arc"]["responses"].append({"response_type": "another-record", "binding": False})
    second = inspect_civic_commons_planning_compatibility(project, changed, inventory=inventory())
    assert first.bindings is not None and second.bindings is not None
    assert first.bindings.digest != second.bindings.digest
    assert second.report.status is CivicCompatibilityStatus.BLOCKED_BY_GOVERNANCE


def test_benchmark_is_deterministic_and_fully_blocked(monkeypatch) -> None:
    import aura_civic_planning_benchmark as benchmark

    monkeypatch.setattr(benchmark, "build_civic_surface_inventory", lambda _root=None: inventory())
    first = run_benchmark(repeats=3)
    second = run_benchmark(repeats=3)
    assert canonical_json(first) == canonical_json(second)
    assert first["total_cases"] == first["passed_cases"] == 6
    assert first["mapped_actions"] == first["total_workstreams"] == 12
    assert first["all_governance_blocked"] is True
    assert first["gate_passed"] is True
