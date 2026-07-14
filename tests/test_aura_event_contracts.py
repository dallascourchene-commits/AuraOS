from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json

import pytest

from aura_event_contracts import (
    ActorType,
    AppendOnlyEventStore,
    AuraEventEnvelope,
    DecisionKind,
    DIKWPStage,
    MeasurementClass,
    ToolDecisionRecord,
    ToolResultRecord,
    canonical_json,
    sanitize_payload,
)


def test_tool_decision_is_bounded_hashed_and_redacts_secrets() -> None:
    decision = ToolDecisionRecord.create(
        trace_id="trace-1",
        tool_id="aura.repo.read",
        decision_kind=DecisionKind.SELECT,
        decision_rationale="Exact source is required before proposing a patch.",
        expected_information="The current source span and hash.",
        tool_input={"path": "aura.py", "api_key": "sk-abcdefghijklmnopqrstuvwxyz"},
        alternatives_considered=("semantic-only lookup",),
        confidence_estimate=0.9,
        confidence_measurement_class=MeasurementClass.DERIVED,
        expected_latency_ms=10,
        created_at=10.0,
    )
    encoded = canonical_json(decision.to_dict())
    assert decision.decision_id.startswith("tool-decision_")
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in encoded
    assert decision.tool_input_digest
    assert decision.confidence_measurement_class == "DERIVED"


def test_private_chain_of_thought_fields_are_rejected_in_snake_and_camel_case() -> None:
    for field_name in ("chain_of_thought", "chainOfThought", "hiddenReasoning"):
        with pytest.raises(ValueError, match="private reasoning"):
            ToolDecisionRecord.create(
                trace_id="trace-1",
                tool_id="tool",
                decision_kind="SELECT",
                decision_rationale="Use the exact tool.",
                expected_information="Exact data.",
                tool_input={field_name: "hidden"},
            )


def test_generic_token_fields_are_redacted_in_snake_and_camel_case() -> None:
    sanitized = sanitize_payload(
        {
            "refresh_token": "refresh-secret",
            "githubToken": "github-secret",
            "nested": {"session_token": "session-secret"},
        }
    )
    assert sanitized == {
        "refresh_token": "[REDACTED]",
        "githubToken": "[REDACTED]",
        "nested": {"session_token": "[REDACTED]"},
    }


def test_confidence_and_alternative_limits_fail_closed() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        ToolDecisionRecord.create(
            trace_id="trace-1",
            tool_id="tool",
            decision_kind="SELECT",
            decision_rationale="reason",
            expected_information="data",
            tool_input={},
            confidence_estimate=1.1,
            confidence_measurement_class=MeasurementClass.DERIVED,
        )
    with pytest.raises(ValueError, match="measurement_class"):
        ToolDecisionRecord.create(
            trace_id="trace-1",
            tool_id="tool",
            decision_kind="SELECT",
            decision_rationale="reason",
            expected_information="data",
            tool_input={},
            confidence_estimate=0.5,
        )
    with pytest.raises(ValueError, match="capped"):
        ToolDecisionRecord.create(
            trace_id="trace-1",
            tool_id="tool",
            decision_kind="SELECT",
            decision_rationale="reason",
            expected_information="data",
            tool_input={},
            alternatives_considered=("a", "b", "c", "d"),
        )


def test_event_envelope_validates_measurement_classes_and_authority() -> None:
    event = AuraEventEnvelope.create(
        trace_id="trace-1",
        event_type="TOOL_DECISION_RECORDED",
        actor_id="aura",
        actor_type=ActorType.AURA,
        purpose_digest="purpose",
        dikwp_stage=DIKWPStage.INFORMATION,
        payload_ref="payload-1",
        payload_digest="digest-1",
        measurement_classes={"confidence": MeasurementClass.DERIVED},
        confidence=0.7,
        created_at=10.0,
    )
    assert event.proposal_only is True
    assert event.patch_authority == "exact_source_spans_and_hashes_only"
    assert event.vsa_patch_authority is False
    with pytest.raises(ValueError, match="measurement class"):
        AuraEventEnvelope.create(
            trace_id="trace-1",
            event_type="event",
            actor_id="aura",
            actor_type="AURA",
            purpose_digest="purpose",
            dikwp_stage="DATA",
            payload_ref="ref",
            payload_digest="digest",
            measurement_classes={"confidence": "CERTAIN"},
        )


def test_tool_result_hashes_sanitized_output_and_validates_time() -> None:
    result = ToolResultRecord.create(
        decision_id="decision",
        tool_id="tool",
        status="succeeded",
        output={"password": "secret-value", "value": 3},
        started_at=10,
        finished_at=11,
    )
    assert result.status == "SUCCEEDED"
    assert result.output_digest
    assert result.output_digest == ToolResultRecord.create(
        decision_id="decision",
        tool_id="tool",
        status="succeeded",
        output={"password": "different-secret", "value": 3},
        started_at=10,
        finished_at=11,
    ).output_digest
    with pytest.raises(ValueError, match="finished_at"):
        ToolResultRecord.create(
            decision_id="decision",
            tool_id="tool",
            status="FAILED",
            output={},
            started_at=11,
            finished_at=10,
        )


def test_sidecar_redaction_tracking_accepts_custom_objects(tmp_path) -> None:
    class CustomPayload:
        def __str__(self) -> str:
            return "custom-payload"

    store = AppendOnlyEventStore(tmp_path / "events")
    ref = store.store_payload(CustomPayload(), kind="custom", created_at=1.0)
    assert ref.redacted is True
    assert json.loads((store.root / ref.path).read_text(encoding="utf-8")) == "custom-payload"


def _event(payload_digest: str = "digest") -> AuraEventEnvelope:
    return AuraEventEnvelope.create(
        trace_id="trace",
        event_type="EVENT",
        actor_id="aura",
        actor_type="AURA",
        purpose_digest="purpose",
        dikwp_stage="DATA",
        payload_ref="payload",
        payload_digest=payload_digest,
        created_at=2.0,
    )


def test_append_only_store_is_idempotent_and_uses_exact_redacted_sidecars(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    ref = store.store_payload(
        {"value": 1, "authorization": "Bearer abc.def.ghi"},
        kind="tool-result",
        created_at=1.0,
    )
    stored = json.loads((store.root / ref.path).read_text(encoding="utf-8"))
    assert stored["value"] == 1
    assert "abc.def.ghi" not in json.dumps(stored)
    assert ref.redacted is True

    event = _event(ref.payload_digest)
    assert store.append(event) is True
    assert store.append(event) is False
    assert [item["event_id"] for item in store.iter_events()] == [event.event_id]


def test_independent_stores_serialize_duplicate_detection(tmp_path) -> None:
    root = tmp_path / "events"
    first = AppendOnlyEventStore(root)
    second = AppendOnlyEventStore(root)
    event = _event()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda store: store.append(event), (first, second)))

    assert sorted(results) == [False, True]
    assert len(list(first.iter_events())) == 1


def test_conflicting_duplicate_fails_closed_after_reloading_persisted_state(tmp_path) -> None:
    root = tmp_path / "events"
    first = AppendOnlyEventStore(root)
    event = _event()
    assert first.append(event) is True

    conflicting = replace(event, payload_digest="different")
    second = AppendOnlyEventStore(root)
    with pytest.raises(ValueError, match="event ID collision"):
        second.append(conflicting)
