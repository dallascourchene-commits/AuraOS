from __future__ import annotations

import pytest

from aura_event_contracts import AppendOnlyEventStore, MeasurementClass, ToolDecisionRecord, stable_digest
from aura_shadow_tool_observability import invoke_tool_shadow


def _decision(tool_input):
    return ToolDecisionRecord.create(
        trace_id="trace-1",
        tool_id="aura.agent_arena.read_source",
        decision_kind="SELECT",
        decision_rationale="Exact source evidence is required.",
        expected_information="The requested source span.",
        tool_input=tool_input,
        confidence_estimate=0.8,
        confidence_measurement_class=MeasurementClass.DERIVED,
        created_at=1.0,
    )


def test_wrapper_forwards_only_original_tool_arguments(tmp_path) -> None:
    seen = {}

    def tool(*, path, start_line, end_line):
        seen.update(path=path, start_line=start_line, end_line=end_line)
        return {"ok": True, "source_hash": "abc"}

    kwargs = {"path": "aura.py", "start_line": 1, "end_line": 3}
    store = AppendOnlyEventStore(tmp_path / "events")
    times = iter((2.0, 3.0))
    observed = invoke_tool_shadow(
        tool,
        tool_kwargs=kwargs,
        decision=_decision(kwargs),
        purpose_digest="purpose",
        arena_id="coding",
        store=store,
        now=lambda: next(times),
    )

    assert seen == kwargs
    assert observed.value["ok"] is True
    assert observed.result.status == "SUCCEEDED"
    assert observed.result_event.parent_event_ids == (observed.decision_event.event_id,)
    assert observed.decision_event.payload_digest == stable_digest(observed.decision.to_dict())
    assert observed.result_event.payload_digest == stable_digest(observed.result.to_dict())
    assert observed.decision_event.measurement_classes["confidence"] == "DERIVED"
    assert len(observed.persisted_event_ids) == 2


def test_wrapper_preserves_exception_behavior_and_records_no_fake_success() -> None:
    def tool(*, value):
        raise RuntimeError(f"bad:{value}")

    kwargs = {"value": 7}
    times = iter((2.0, 3.0))
    with pytest.raises(RuntimeError, match="bad:7"):
        invoke_tool_shadow(
            tool,
            tool_kwargs=kwargs,
            decision=_decision(kwargs),
            purpose_digest="purpose",
            now=lambda: next(times),
        )
