from __future__ import annotations

import json

import pytest

from aura_event_contracts import (
    AppendOnlyEventStore,
    MeasurementClass,
    ToolDecisionRecord,
    stable_digest,
)
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


def test_wrapper_rejects_decision_input_mismatch_before_invocation() -> None:
    called = False

    def tool(*, value):
        nonlocal called
        called = True
        return value

    with pytest.raises(ValueError, match="does not match"):
        invoke_tool_shadow(
            tool,
            tool_kwargs={"value": 2},
            decision=_decision({"value": 1}),
            purpose_digest="purpose",
        )
    assert called is False


def test_wrapper_normalizes_lowercase_failure_status() -> None:
    times = iter((2.0, 3.0))
    observed = invoke_tool_shadow(
        lambda **_kwargs: {"status": "failed", "error": "bad result"},
        tool_kwargs={"value": 1},
        decision=_decision({"value": 1}),
        purpose_digest="purpose",
        now=lambda: next(times),
    )
    assert observed.result.status == "FAILED"
    assert observed.result.error_class == "bad result"


def test_wrapper_preserves_exception_and_persists_failed_result(tmp_path) -> None:
    def tool(*, value):
        raise RuntimeError(f"bad:{value}")

    kwargs = {"value": 7}
    store = AppendOnlyEventStore(tmp_path / "events")
    times = iter((2.0, 3.0))
    with pytest.raises(RuntimeError, match="bad:7"):
        invoke_tool_shadow(
            tool,
            tool_kwargs=kwargs,
            decision=_decision(kwargs),
            purpose_digest="purpose",
            store=store,
            now=lambda: next(times),
        )

    events = list(store.iter_events())
    result_event = next(item for item in events if item["event_type"] == "TOOL_RESULT_RECORDED")
    result_payload_path = store.sidecars_dir / f"{result_event['payload_ref']}.json"
    result_payload = json.loads(result_payload_path.read_text(encoding="utf-8"))
    assert result_payload["status"] == "FAILED"
    assert result_payload["error_class"] == "RuntimeError"


def test_observability_failure_does_not_replace_original_tool_exception() -> None:
    class BrokenStore:
        def store_payload(self, *_args, **_kwargs):
            raise OSError("observer unavailable")

    def tool(*, value):
        raise RuntimeError(f"original:{value}")

    kwargs = {"value": 9}
    times = iter((2.0, 3.0))
    with pytest.raises(RuntimeError, match="original:9"):
        invoke_tool_shadow(
            tool,
            tool_kwargs=kwargs,
            decision=_decision(kwargs),
            purpose_digest="purpose",
            store=BrokenStore(),
            now=lambda: next(times),
        )
